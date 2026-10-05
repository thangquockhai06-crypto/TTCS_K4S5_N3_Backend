import uuid
from datetime import datetime
from typing import List, Optional, Set
from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.customer_search import (
    calculate_company_similarity,
    normalize_company_name,
    normalize_phone,
    normalize_tax_code,
    normalize_text,
    normalize_website,
)
from app.core.scope import DataScope, get_user_data_scope
from app.models.activity import Activity, Note
from app.models.customer import Contact, Customer
from app.models.deal import Deal
from app.models.quotation import Quotation
from app.models.user import User
from app.schemas.customer_merge import (
    CustomerCompareDetailsDTO,
    CustomerCompareResponse,
    CustomerMergeRequest,
    CustomerMergeResponse,
    DuplicateCheckRequest,
    DuplicateMatchItem,
)


class CustomerMergeService:
    """
    Tầng Service phụ trách toàn bộ nghiệp vụ Cảnh báo trùng lặp, So sánh cạnh nhau
    và Gộp khách hàng an toàn (ACID Transaction).
    Tuân thủ Clean Layered Architecture, Data Scope Security & 100% Type Hints.
    """

    @staticmethod
    def scan_duplicates(
        db: Session,
        request: DuplicateCheckRequest,
        current_user: User,
    ) -> List[DuplicateMatchItem]:
        """
        Phát hiện các khách hàng trùng lặp dựa trên 3 tiêu chí:
        1. Mã số thuế (tax_code): So khớp chính xác sau chuẩn hóa.
        2. Website (website): So khớp chính xác domain sau chuẩn hóa.
        3. Tên công ty / Họ tên (name): So khớp tương đồng chuỗi >= 80%.
        4. Số điện thoại: So khớp chính xác theo số chuẩn hóa.
        """
        target_customer: Optional[Customer] = None
        chk_tax = request.tax_code
        chk_web = request.website
        chk_name = request.name
        chk_phone = request.phone
        exclude_id = None

        if request.customer_id:
            target_customer = (
                db.query(Customer)
                .filter(
                    Customer.id == request.customer_id,
                    or_(Customer.is_deleted == False, Customer.is_deleted.is_(None)),
                )
                .first()
            )
            if not target_customer:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Không tìm thấy khách hàng yêu cầu kiểm tra trùng lặp.",
                )
            chk_tax = chk_tax or target_customer.tax_code
            chk_web = chk_web or target_customer.website
            chk_name = chk_name or target_customer.company or target_customer.full_name
            chk_phone = chk_phone or target_customer.phone
            exclude_id = target_customer.id

        norm_tax = normalize_tax_code(chk_tax or "")
        norm_web = normalize_website(chk_web or "")
        norm_name = normalize_company_name(chk_name or "")
        norm_phone = normalize_phone(chk_phone or "")

        # Nếu không có tiêu chí nào được cung cấp để quét
        if not norm_tax and not norm_web and not norm_name and not norm_phone:
            return []

        # Truy vấn các bản ghi khách hàng đang hoạt động trong hệ thống
        query = (
            db.query(Customer)
            .options(
                joinedload(Customer.assigned_user),
                selectinload(Customer.contacts),
            )
            .filter(
                or_(Customer.is_deleted == False, Customer.is_deleted.is_(None)),
                Customer.merged_into_id.is_(None),
            )
        )
        if exclude_id:
            query = query.filter(Customer.id != exclude_id)

        candidates = query.all()
        results: List[DuplicateMatchItem] = []

        for cand in candidates:
            match_reasons: List[str] = []
            score = 0.0

            # 1. Kiểm tra trùng Mã số thuế
            if norm_tax:
                cand_tax = normalize_tax_code(cand.tax_code or "")
                if cand_tax and cand_tax == norm_tax:
                    match_reasons.append(f"Trùng mã số thuế: {cand.tax_code}")
                    score = max(score, 1.0)

            # 2. Kiểm tra trùng Website domain
            if norm_web:
                cand_web = normalize_website(cand.website or "")
                if cand_web and cand_web == norm_web:
                    match_reasons.append(f"Trùng tên miền website: {cand.website}")
                    score = max(score, 1.0)

            # 3. Kiểm tra trùng Tên công ty / Họ tên đại diện (Fuzzy matching)
            if norm_name:
                cand_company = cand.company or ""
                cand_full_name = cand.full_name or ""
                sim_company = calculate_company_similarity(chk_name, cand_company) if cand_company else 0.0
                sim_full_name = calculate_company_similarity(chk_name, cand_full_name) if cand_full_name else 0.0
                best_sim = max(sim_company, sim_full_name)
                if best_sim >= 0.8:
                    matched_label = cand_company if sim_company >= sim_full_name else cand_full_name
                    pct = int(round(best_sim * 100))
                    match_reasons.append(f"Tên công ty tương đồng {pct}% ('{chk_name}' ~ '{matched_label}')")
                    score = max(score, round(best_sim, 2))

            # 4. Kiểm tra trùng Số điện thoại
            if norm_phone:
                cand_phone = normalize_phone(cand.phone or "")
                contact_phones = {normalize_phone(c.phone) for c in cand.contacts if c.phone}
                if (cand_phone and cand_phone == norm_phone) or (norm_phone in contact_phones):
                    match_reasons.append(f"Trùng số điện thoại liên hệ: {cand.phone}")
                    score = max(score, 0.95)

            if match_reasons:
                assigned_name = cand.assigned_user.full_name if cand.assigned_user else "Chưa phân công"
                display_name = cand.company or cand.full_name
                results.append(
                    DuplicateMatchItem(
                        id=cand.id,
                        name=display_name,
                        full_name=cand.full_name,
                        company=cand.company,
                        tax_code=cand.tax_code,
                        website=cand.website,
                        phone=cand.phone,
                        email=cand.email,
                        assigned_to_id=cand.assigned_user_id,
                        assigned_to_name=assigned_name,
                        status=cand.status,
                        match_reasons=match_reasons,
                        similarity_score=score,
                        created_at=cand.created_at.isoformat() if cand.created_at else None,
                    )
                )

        # Sắp xếp kết quả theo độ tương đồng giảm dần
        results.sort(key=lambda x: (x.similarity_score, x.created_at or ""), reverse=True)
        return results

    @staticmethod
    def compare_customers(
        db: Session,
        primary_id: str,
        duplicate_id: str,
        current_user: User,
    ) -> CustomerCompareResponse:
        """
        Lấy thông tin chi tiết đầy đủ của hai khách hàng cạnh nhau để so sánh hai cột.
        """
        if primary_id == duplicate_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Không thể so sánh khách hàng với chính nó.",
            )

        primary = (
            db.query(Customer)
            .options(
                joinedload(Customer.assigned_user),
                selectinload(Customer.contacts),
                selectinload(Customer.deals),
                selectinload(Customer.activities),
                selectinload(Customer.notes),
            )
            .filter(Customer.id == primary_id)
            .first()
        )
        if not primary or primary.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy khách hàng chính với ID '{primary_id}'.",
            )

        duplicate = (
            db.query(Customer)
            .options(
                joinedload(Customer.assigned_user),
                selectinload(Customer.contacts),
                selectinload(Customer.deals),
                selectinload(Customer.activities),
                selectinload(Customer.notes),
            )
            .filter(Customer.id == duplicate_id)
            .first()
        )
        if not duplicate or duplicate.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy khách hàng phụ với ID '{duplicate_id}'.",
            )

        def to_compare_dto(c: Customer) -> CustomerCompareDetailsDTO:
            assigned_name = c.assigned_user.full_name if c.assigned_user else None
            contacts_list = [
                {
                    "id": ct.id,
                    "fullName": ct.full_name,
                    "phone": ct.phone,
                    "email": ct.email,
                    "isPrimary": bool(ct.is_primary),
                }
                for ct in c.contacts
            ]
            deals_list = [
                {
                    "id": d.id,
                    "title": d.title,
                    "value": float(d.value) if d.value else 0.0,
                    "stage": d.stage,
                    "probability": d.probability,
                }
                for d in c.deals
            ]
            acts_list = [
                {
                    "id": a.id,
                    "type": a.type,
                    "title": a.title,
                    "description": a.description,
                    "createdAt": a.created_at.isoformat() if a.created_at else None,
                }
                for a in c.activities
            ]
            return CustomerCompareDetailsDTO(
                id=c.id,
                fullName=c.full_name,
                company=c.company,
                email=c.email,
                phone=c.phone,
                website=c.website,
                taxCode=c.tax_code,
                status=c.status,
                healthScore=c.health_score,
                industry=c.industry,
                companySize=c.company_size,
                region=c.region,
                assignedUserId=c.assigned_user_id,
                assignedUserName=assigned_name,
                contactsCount=len(c.contacts),
                dealsCount=len(c.deals),
                activitiesCount=len(c.activities) + len(c.notes),
                contacts=contacts_list,
                deals=deals_list,
                activities=acts_list,
                createdAt=c.created_at.isoformat() if c.created_at else None,
            )

        p_dto = to_compare_dto(primary)
        d_dto = to_compare_dto(duplicate)

        # Liệt kê các trường có dữ liệu khác biệt
        diffs: List[str] = []
        fields_to_check = [
            ("fullName", p_dto.fullName, d_dto.fullName),
            ("company", p_dto.company, d_dto.company),
            ("email", p_dto.email, d_dto.email),
            ("phone", p_dto.phone, d_dto.phone),
            ("website", p_dto.website, d_dto.website),
            ("taxCode", p_dto.taxCode, d_dto.taxCode),
            ("status", p_dto.status, d_dto.status),
            ("industry", p_dto.industry, d_dto.industry),
            ("region", p_dto.region, d_dto.region),
            ("assignedUserId", p_dto.assignedUserId, d_dto.assignedUserId),
        ]
        for field_name, val_p, val_d in fields_to_check:
            if (val_p or "") != (val_d or ""):
                diffs.append(field_name)

        return CustomerCompareResponse(
            primary_customer=p_dto,
            duplicate_customer=d_dto,
            field_differences=diffs,
        )

    @staticmethod
    def merge_customers(
        db: Session,
        request: CustomerMergeRequest,
        current_user: User,
    ) -> CustomerMergeResponse:
        """
        Thực hiện gộp khách hàng trong một Database Transaction toàn vẹn (ACID):
        1. Kiểm tra quyền sở hữu dữ liệu theo DataScope.
        2. Chuyển toàn bộ contacts, deals, activities, notes sang khách hàng chính.
        3. Cập nhật thông tin khách hàng chính (nếu có override).
        4. Đánh dấu khách hàng phụ là đã gộp (is_deleted=True, merged_into_id=target_id).
        5. Ghi nhận Activity hệ thống trên khách hàng chính.
        """
        target_id = request.target_customer_id
        source_id = request.source_customer_id

        if target_id == source_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Không thể gộp một khách hàng vào chính nó.",
            )

        target = db.query(Customer).filter(Customer.id == target_id).first()
        if not target or target.is_deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy khách hàng chính với ID '{target_id}' (hoặc đã bị xóa/gộp).",
            )

        source = db.query(Customer).filter(Customer.id == source_id).first()
        if not source:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy khách hàng phụ với ID '{source_id}'.",
            )
        if source.is_deleted or source.merged_into_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Khách hàng phụ '{source.full_name}' đã được gộp vào khách hàng khác hoặc đã bị xóa.",
            )

        # Kiểm tra DataScope phân quyền cho TEAM_LEAD
        scope = get_user_data_scope(current_user)
        if scope == DataScope.TEAM:
            team_id = getattr(current_user, "team_id", None)
            if not team_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Tài khoản Trưởng nhóm chưa được gán vào nhóm kinh doanh nào.",
                )
            team_member_ids: Set[str] = {
                row[0] for row in db.query(User.id).filter(User.team_id == team_id).all()
            }
            if target.assigned_user_id and target.assigned_user_id not in team_member_ids:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Khách hàng chính '{target.full_name}' không thuộc quyền quản lý của nhóm bạn.",
                )
            if source.assigned_user_id and source.assigned_user_id not in team_member_ids:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Khách hàng phụ '{source.full_name}' không thuộc quyền quản lý của nhóm bạn.",
                )

        try:
            # 1. Đếm số lượng bản ghi phụ thuộc cần chuyển
            transferred_contacts = (
                db.query(Contact).filter(Contact.customer_id == source.id).count()
            )
            transferred_deals = (
                db.query(Deal).filter(Deal.customer_id == source.id).count()
            )
            transferred_activities = (
                db.query(Activity).filter(Activity.customer_id == source.id).count()
            )
            transferred_notes = (
                db.query(Note).filter(Note.customer_id == source.id).count()
            )

            # 2. Cập nhật khóa ngoại customer_id sang target_id
            db.query(Contact).filter(Contact.customer_id == source.id).update(
                {Contact.customer_id: target.id},
                synchronize_session=False,
            )
            db.query(Deal).filter(Deal.customer_id == source.id).update(
                {Deal.customer_id: target.id},
                synchronize_session=False,
            )
            db.query(Quotation).filter(Quotation.customer_id == source.id).update(
                {Quotation.customer_id: target.id},
                synchronize_session=False,
            )
            db.query(Activity).filter(Activity.customer_id == source.id).update(
                {Activity.customer_id: target.id},
                synchronize_session=False,
            )
            db.query(Note).filter(Note.customer_id == source.id).update(
                {Note.customer_id: target.id},
                synchronize_session=False,
            )

            # 3. Cập nhật dữ liệu override nếu có chỉ định từ người dùng
            if request.merged_data:
                md = request.merged_data
                if md.full_name:
                    target.full_name = md.full_name
                if md.company is not None:
                    target.company = md.company
                if md.email:
                    target.email = md.email
                if md.phone:
                    target.phone = md.phone
                if md.website is not None:
                    target.website = md.website
                if md.tax_code is not None:
                    target.tax_code = md.tax_code
                if md.industry is not None:
                    target.industry = md.industry
                if md.region is not None:
                    target.region = md.region
                if md.status is not None:
                    target.status = md.status
            else:
                # Tự động điền các trường còn thiếu trên target nếu source có dữ liệu
                if not target.website and source.website:
                    target.website = source.website
                if not target.tax_code and source.tax_code:
                    target.tax_code = source.tax_code
                if not target.company and source.company:
                    target.company = source.company

            # Đồng bộ các cột tìm kiếm chuẩn hóa
            target.normalized_name = normalize_text(f"{target.full_name or ''} {target.company or ''}")
            target.normalized_tax_code = normalize_tax_code(target.tax_code or "")
            target.normalized_phone = normalize_phone(target.phone or "")
            target.updated_at = datetime.utcnow()

            # 4. Đánh dấu bản ghi phụ là đã gộp
            source.is_deleted = True
            source.merged_into_id = target.id
            source.updated_at = datetime.utcnow()

            # 5. Ghi nhận Activity vào lịch sử hoạt động của khách hàng chính
            source_display = source.company or source.full_name or source.id
            audit_activity = Activity(
                id=str(uuid.uuid4()),
                customer_id=target.id,
                user_id=current_user.id,
                type="status_change",
                title="Gộp khách hàng trùng lặp",
                description=(
                    f"Đã gộp khách hàng '{source.full_name}' ({source_display}) vào khách hàng này bởi {current_user.full_name}. "
                    f"Đã chuyển giao: {transferred_contacts} người liên hệ, {transferred_deals} cơ hội bán hàng, "
                    f"{transferred_activities + transferred_notes} hoạt động & ghi chú."
                ),
                created_at=datetime.utcnow(),
            )
            db.add(audit_activity)

            db.commit()
            db.refresh(target)

            total_transferred_acts = transferred_activities + transferred_notes
            return CustomerMergeResponse(
                success=True,
                message=f"Đã gộp thành công khách hàng '{source.full_name}' vào '{target.full_name}'.",
                target_customer_id=target.id,
                source_customer_id=source.id,
                transferred_contacts_count=transferred_contacts,
                transferred_deals_count=transferred_deals,
                transferred_activities_count=total_transferred_acts,
                merged_at=datetime.utcnow().isoformat(),
            )
        except HTTPException:
            db.rollback()
            raise
        except Exception as exc:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Quá trình gộp khách hàng thất bại và đã được khôi phục giao dịch (rollback): {str(exc)}",
            )
