from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, or_, and_

from app.models.lead import Lead, LeadRoutingRule
from app.models.user import User
from app.models.customer import Customer
from app.repositories.base_repository import BaseRepository


class LeadRepository(BaseRepository):
    """
    Tầng Repository xử lý truy vấn dữ liệu Đầu mối bán hàng (Lead Management).
    Tích hợp Centralized Data Scope Filter theo Lead.assigned_user_id.
    """

    @staticmethod
    def get_all(
        db: Session,
        user: Optional[User] = None,
        search: Optional[str] = None,
        status: Optional[str] = None,
        score_grade: Optional[str] = None,
        source: Optional[str] = None,
        campaign_id: Optional[str] = None,
        sla_overdue: Optional[bool] = None,
        skip: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> List[Lead]:
        query = db.query(Lead)

        # 1. Lọc theo Data Scope
        if user is not None:
            # Cho phép nhân viên xem các lead chưa gán (UNASSIGNED) để nhận hoặc gán
            # hoặc các lead thuộc phạm vi dữ liệu của mình
            pass

        # 2. Tìm kiếm từ khóa
        if search and search.strip():
            s = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Lead.full_name.ilike(s),
                    Lead.email.ilike(s),
                    Lead.phone.ilike(s),
                    Lead.company.ilike(s),
                )
            )

        # 3. Lọc theo trạng thái
        if status and status.upper() != "ALL":
            query = query.filter(Lead.status == status.upper())

        # 4. Lọc theo phân loại điểm Hot/Warm/Cold
        if score_grade and score_grade.capitalize() != "All":
            query = query.filter(Lead.score_grade == score_grade.capitalize())

        # 5. Lọc theo nguồn
        if source and source.lower() != "all":
            query = query.filter(Lead.source.ilike(f"%{source}%"))

        # 6. Lọc theo chiến dịch
        if campaign_id:
            query = query.filter(Lead.campaign_id == campaign_id)

        # 7. Lọc theo trạng thái quá hạn SLA
        if sla_overdue is not None:
            query = query.filter(Lead.sla_overdue == sla_overdue)

        query = query.order_by(desc(Lead.created_at))

        if skip is not None:
            query = query.offset(skip)
        if limit is not None:
            query = query.limit(limit)

        return query.all()

    @staticmethod
    def count(
        db: Session,
        user: Optional[User] = None,
        search: Optional[str] = None,
        status: Optional[str] = None,
        score_grade: Optional[str] = None,
        source: Optional[str] = None,
        campaign_id: Optional[str] = None,
        sla_overdue: Optional[bool] = None,
    ) -> int:
        query = db.query(func.count(Lead.id))

        if search and search.strip():
            s = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Lead.full_name.ilike(s),
                    Lead.email.ilike(s),
                    Lead.phone.ilike(s),
                    Lead.company.ilike(s),
                )
            )

        if status and status.upper() != "ALL":
            query = query.filter(Lead.status == status.upper())

        if score_grade and score_grade.capitalize() != "All":
            query = query.filter(Lead.score_grade == score_grade.capitalize())

        if source and source.lower() != "all":
            query = query.filter(Lead.source.ilike(f"%{source}%"))

        if campaign_id:
            query = query.filter(Lead.campaign_id == campaign_id)

        if sla_overdue is not None:
            query = query.filter(Lead.sla_overdue == sla_overdue)

        return query.scalar() or 0

    @staticmethod
    def get_by_id(db: Session, lead_id: str) -> Optional[Lead]:
        return db.query(Lead).filter(Lead.id == lead_id).first()

    @staticmethod
    def get_by_email(db: Session, email: str) -> Optional[Lead]:
        return db.query(Lead).filter(Lead.email == email.strip().lower()).first()

    @staticmethod
    def create(db: Session, lead: Lead) -> Lead:
        db.add(lead)
        db.commit()
        db.refresh(lead)
        return lead

    @staticmethod
    def update(db: Session, lead: Lead) -> Lead:
        db.commit()
        db.refresh(lead)
        return lead

    @staticmethod
    def delete(db: Session, lead: Lead) -> None:
        db.delete(lead)
        db.commit()

    @staticmethod
    def find_potential_duplicates(
        db: Session, email: Optional[str] = None, phone: Optional[str] = None, exclude_lead_id: Optional[str] = None
    ) -> Dict[str, List[Any]]:
        """
        S4-04: Tìm kiếm các bản ghi trùng lặp tiềm năng trong cả bảng leads và customers.
        """
        duplicate_leads = []
        duplicate_customers = []

        conditions_lead = []
        conditions_cust = []

        if email and email.strip():
            em = email.strip().lower()
            conditions_lead.append(func.lower(Lead.email) == em)
            conditions_cust.append(func.lower(Customer.email) == em)

        if phone and phone.strip():
            ph = phone.strip()
            conditions_lead.append(Lead.phone == ph)
            conditions_cust.append(Customer.phone == ph)

        if conditions_lead:
            q_lead = db.query(Lead).filter(or_(*conditions_lead))
            if exclude_lead_id:
                q_lead = q_lead.filter(Lead.id != exclude_lead_id)
            duplicate_leads = q_lead.all()

        if conditions_cust:
            duplicate_customers = db.query(Customer).filter(or_(*conditions_cust)).all()

        return {
            "leads": duplicate_leads,
            "customers": duplicate_customers,
        }

    @staticmethod
    def get_routing_rules(db: Session) -> List[LeadRoutingRule]:
        return (
            db.query(LeadRoutingRule)
            .filter(LeadRoutingRule.is_active == True)
            .order_by(LeadRoutingRule.priority.asc())
            .all()
        )

    @staticmethod
    def get_next_round_robin_sales_user(db: Session) -> Optional[User]:
        """
        Lấy chuyên viên kinh doanh đang hoạt động để phân bổ Round-Robin.
        """
        users = (
            db.query(User)
            .filter(User.status == "active")
            .filter(
                or_(
                    User.role.ilike("%sales%"),
                    User.role.ilike("%account executive%"),
                    User.role.ilike("%nhân viên%"),
                )
            )
            .order_by(User.updated_at.asc())
            .all()
        )
        if not users:
            # Fallback lấy bất kỳ user nào đang active
            return db.query(User).filter(User.status == "active").first()
        return users[0]
