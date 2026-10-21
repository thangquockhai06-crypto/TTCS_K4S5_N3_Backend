import uuid
from datetime import datetime
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select, func, desc, or_, and_, false
from fastapi import HTTPException, status

from app.models.customer import Customer, Contact
from app.models.deal import Deal
from app.models.activity import Activity, Note
from app.models.user import User
from app.core.scope import DataScope, get_user_data_scope
from app.schemas.customer_care import (
    CustomerCareFilterParams,
    CustomerCareItemResponse,
    CustomerCareListResponse,
    QuickContactRequest,
    QuickContactResponse,
)


class CustomerCareService:
    """
    Tầng Service xử lý nghiệp vụ Chăm sóc khách hàng định kỳ (SCRUM-67).
    Tuân thủ Clean Layered Architecture, SQLAlchemy 2.0, Data Scope RBAC & 100% Type Hints.
    """

    @staticmethod
    def _is_all_scope_role(user: User, scope: DataScope) -> bool:
        if scope == DataScope.ALL:
            return True
        user_role = (getattr(user, "role", "") or "").strip().lower().replace("_", " ")
        all_roles = {
            "cs", "customer care", "customer success", "chăm sóc khách hàng", "csm",
            "director", "sales director", "vp of sales", "admin", "super admin",
            "quản trị viên", "giám đốc kinh doanh"
        }
        return user_role in all_roles

    @staticmethod
    def _is_team_scope_role(user: User, scope: DataScope) -> bool:
        if scope == DataScope.TEAM:
            return True
        user_role = (getattr(user, "role", "") or "").strip().lower().replace("_", " ")
        team_roles = {
            "team lead", "team leader", "lead", "sales leader", "sales manager",
            "manager", "trưởng nhóm", "trưởng phòng", "revops lead"
        }
        return user_role in team_roles

    @classmethod
    def get_overdue_followups(
        cls,
        db: Session,
        current_user: User,
        filter_params: CustomerCareFilterParams,
    ) -> CustomerCareListResponse:
        """
        Lấy danh sách khách hàng đã ký hợp đồng nhưng chưa tương tác trong N ngày (N động).
        Sắp xếp theo tổng giá trị hợp đồng giảm dần (total_contract_value DESC, days_without_contact DESC).
        Tuân thủ Data Scope RBAC:
        - CS / Director / Admin: Toàn hệ thống.
        - Team Lead: Các khách hàng thuộc team.
        - Sales Rep / Nhân viên: Chỉ khách hàng do mình phụ trách.
        """
        # 1. Subquery: Lấy thời điểm tương tác gần nhất từ bảng activities
        last_act_subq = (
            select(
                Activity.customer_id.label("customer_id"),
                func.max(Activity.created_at).label("last_activity_date"),
            )
            .group_by(Activity.customer_id)
            .subquery("last_act")
        )

        # 2. Subquery: Tính tổng giá trị hợp đồng đã ký (stage = 'won' hoặc 'WON') từ bảng deals
        won_deals_subq = (
            select(
                Deal.customer_id.label("customer_id"),
                func.coalesce(func.sum(Deal.value), 0.0).label("total_contract_value"),
            )
            .where(func.lower(Deal.stage) == "won")
            .group_by(Deal.customer_id)
            .subquery("won_deals")
        )

        # 3. Biểu thức tính toán số ngày chưa tương tác
        effective_date = func.coalesce(last_act_subq.c.last_activity_date, Customer.created_at)
        days_without_contact_expr = func.datediff(func.now(), effective_date)
        total_contract_value_expr = func.coalesce(won_deals_subq.c.total_contract_value, 0.0)

        # 4. Xây dựng câu truy vấn chính
        base_query = (
            select(
                Customer,
                User.full_name.label("assigned_to_name"),
                total_contract_value_expr.label("total_contract_value"),
                last_act_subq.c.last_activity_date.label("last_activity_date"),
                days_without_contact_expr.label("days_without_contact"),
            )
            .outerjoin(User, Customer.assigned_user_id == User.id)
            .outerjoin(won_deals_subq, Customer.id == won_deals_subq.c.customer_id)
            .outerjoin(last_act_subq, Customer.id == last_act_subq.c.customer_id)
        )

        # Điều kiện: Chưa bị soft-delete
        base_query = base_query.where(
            Customer.is_deleted == False,
            func.coalesce(Customer.status, "") != "MERGED",
        )

        # Điều kiện: Khách hàng đã phát sinh hợp đồng / giao dịch thành công (status = 'CUSTOMER'/'active' HOẶC total_contract_value > 0)
        customer_target_cond = or_(
            func.lower(Customer.status).in_(["customer", "active"]),
            total_contract_value_expr > 0,
        )
        base_query = base_query.where(customer_target_cond)

        # Điều kiện: Chưa tương tác trong N ngày (N động)
        inactive_cond = days_without_contact_expr >= filter_params.days_inactive
        base_query = base_query.where(inactive_cond)

        # 5. Phân quyền Data Scope RBAC
        scope = get_user_data_scope(current_user)
        if cls._is_all_scope_role(current_user, scope):
            pass  # Xem toàn bộ
        elif cls._is_team_scope_role(current_user, scope):
            team_id = getattr(current_user, "team_id", None)
            if not team_id or not str(team_id).strip():
                # Fail-closed: Chưa thuộc team nào
                return CustomerCareListResponse(
                    total_items=0,
                    page=filter_params.page,
                    page_size=filter_params.page_size,
                    days_inactive_threshold=filter_params.days_inactive,
                    items=[],
                )
            team_users_subq = select(User.id).where(User.team_id == team_id).scalar_subquery()
            base_query = base_query.where(Customer.assigned_user_id.in_(team_users_subq))
        else:
            # OWN Scope (SALES_REP, Employee...)
            base_query = base_query.where(Customer.assigned_user_id == current_user.id)

        # 6. Tìm kiếm theo từ khóa (Tên khách hàng, Tên công ty, Mã số thuế, SĐT)
        if filter_params.search and filter_params.search.strip():
            kw = f"%{filter_params.search.strip()}%"
            base_query = base_query.where(
                or_(
                    Customer.full_name.ilike(kw),
                    Customer.company.ilike(kw),
                    Customer.tax_code.ilike(kw),
                    Customer.phone.ilike(kw),
                )
            )

        # 7. Tính tổng số lượng bản ghi (Total count)
        count_stmt = select(func.count()).select_from(base_query.order_by(None).subquery())
        total_items = db.scalar(count_stmt) or 0

        # 8. Sắp xếp: Ưu tiên giá trị hợp đồng giảm dần, sau đó số ngày không tương tác giảm dần
        base_query = base_query.order_by(
            desc(total_contract_value_expr),
            desc(days_without_contact_expr),
            Customer.created_at.desc(),
        )

        # 9. Phân trang & Nạp quan hệ contacts
        offset = (filter_params.page - 1) * filter_params.page_size
        paginated_stmt = (
            base_query.offset(offset)
            .limit(filter_params.page_size)
            .options(selectinload(Customer.contacts))
        )

        rows = db.execute(paginated_stmt).all()

        items: List[CustomerCareItemResponse] = []
        for row in rows:
            cust: Customer = row[0]
            assigned_name: Optional[str] = row[1]
            tot_val: float = float(row[2] or 0.0)
            last_date: Optional[datetime] = row[3]
            days_inactive_calc: int = int(row[4] or 0)

            # Xác định người liên hệ chính (nếu có trong contacts)
            contact_person = None
            if cust.contacts:
                contact_person = cust.contacts[0].full_name
            if not contact_person:
                contact_person = cust.full_name

            items.append(
                CustomerCareItemResponse(
                    customer_id=cust.id,
                    customer_name=cust.company or cust.full_name,
                    contact_person_name=contact_person,
                    phone=cust.phone,
                    email=cust.email,
                    assigned_to_name=assigned_name,
                    total_contract_value=tot_val,
                    last_activity_date=last_date,
                    days_without_contact=max(0, days_inactive_calc),
                    status=cust.status,
                )
            )

        return CustomerCareListResponse(
            total_items=total_items,
            page=filter_params.page,
            page_size=filter_params.page_size,
            days_inactive_threshold=filter_params.days_inactive,
            items=items,
        )

    @classmethod
    def record_quick_contact(
        cls,
        db: Session,
        current_user: User,
        customer_id: str,
        request: QuickContactRequest,
    ) -> QuickContactResponse:
        """
        Đánh dấu đã liên hệ nhanh ngay trên danh sách:
        1. Kiểm tra tồn tại và quyền truy cập của user.
        2. Tạo Activity mới loại CALL/MEETING/NOTE/EMAIL gắn với current_user.
        3. Cập nhật mốc tương tác, đưa khách hàng ra khỏi danh sách chăm sóc định kỳ.
        """
        # 1. Kiểm tra khách hàng tồn tại
        customer = (
            db.query(Customer)
            .filter(Customer.id == customer_id, Customer.is_deleted == False)
            .first()
        )
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy khách hàng.",
            )

        # 2. Kiểm tra quyền thao tác (Data Scope)
        scope = get_user_data_scope(current_user)
        if not cls._is_all_scope_role(current_user, scope):
            if cls._is_team_scope_role(current_user, scope):
                if not current_user.team_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Bạn không có quyền thao tác trên khách hàng này.",
                    )
                if customer.assigned_user_id:
                    assigned_user = (
                        db.query(User).filter(User.id == customer.assigned_user_id).first()
                    )
                    if not assigned_user or assigned_user.team_id != current_user.team_id:
                        raise HTTPException(
                            status_code=status.HTTP_403_FORBIDDEN,
                            detail="Bạn không có quyền thao tác trên khách hàng này.",
                        )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Bạn không có quyền thao tác trên khách hàng này.",
                    )
            else:
                # OWN Scope
                if customer.assigned_user_id != current_user.id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Bạn không có quyền thao tác trên khách hàng này.",
                    )

        # 3. Tạo Activity mới
        type_mapping = {
            "CALL": "call",
            "MEETING": "meeting",
            "EMAIL": "email",
            "NOTE": "call",
        }
        act_type = type_mapping.get(request.activity_type.upper(), "call")
        now = datetime.utcnow()

        new_activity = Activity(
            id=str(uuid.uuid4()),
            customer_id=customer.id,
            user_id=current_user.id,
            type=act_type,
            title=f"Liên hệ chăm sóc định kỳ ({request.activity_type.upper()})",
            description=request.notes or "Đã liên hệ chăm sóc định kỳ",
            created_at=now,
        )
        db.add(new_activity)

        # Nếu là loại NOTE, tạo đồng thời trong bảng notes để hiển thị trên tab Ghi chú
        if request.activity_type.upper() == "NOTE":
            new_note = Note(
                id=str(uuid.uuid4()),
                customer_id=customer.id,
                author_id=current_user.id,
                content=request.notes or "Đã liên hệ chăm sóc định kỳ",
                created_at=now,
            )
            db.add(new_note)

        db.commit()

        return QuickContactResponse(
            message="Đã ghi nhận tương tác thành công",
            last_contacted_at=now,
        )
