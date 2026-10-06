from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.user import User
from app.schemas.customer_hierarchy import (
    AssignParentRequest,
    AssignParentResponse,
    SubsidiaryItemResponse,
    GroupSummaryResponse,
)
from app.repositories.customer_hierarchy_repository import CustomerHierarchyRepository


class CustomerHierarchyService:
    """
    Tầng Service xử lý nghiệp vụ Cây phân cấp Tập đoàn (Công ty Mẹ - Con) - SCRUM-63.
    Bao gồm kiểm tra tính hợp lệ quan hệ, ngăn chặn chu trình lặp (Circular Hierarchy),
    và tổng hợp giá trị doanh số/hợp đồng toàn tập đoàn (Group Valuation Rollup).
    """

    @staticmethod
    def assign_parent(
        db: Session,
        customer_id: str,
        request: AssignParentRequest,
        user: User,
    ) -> AssignParentResponse:
        """
        Thiết lập hoặc gỡ bỏ quan hệ công ty mẹ cho khách hàng:
        1. Kiểm tra tồn tại của customer_id (HTTP 404).
        2. Kiểm tra quyền truy cập bản ghi theo Data Scope (HTTP 403).
        3. Nếu có parent_id:
           - Kiểm tra không tự gán chính mình (HTTP 400).
           - Kiểm tra công ty mẹ tồn tại (HTTP 404).
           - Duyệt đệ quy lên cây để chặn chu trình lặp A -> B -> A hoặc đa cấp (HTTP 400).
        4. Cập nhật parent_id và lưu CSDL.
        """
        # 1. Kiểm tra tồn tại trong DB trước
        customer_raw = CustomerHierarchyRepository.get_by_id(db, customer_id)
        if not customer_raw:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Khách hàng không tồn tại",
            )

        # 2. Kiểm tra quyền truy cập theo Data Scope
        customer = CustomerHierarchyRepository.get_scoped_by_id(db, customer_id, user)

        target_parent_id: Optional[str] = None
        if request.parent_id is not None and str(request.parent_id).strip():
            target_parent_id = str(request.parent_id).strip()

        # 3. Xử lý khi có gán công ty mẹ
        if target_parent_id is not None:
            # Chặn tự gán chính mình
            if str(customer_id) == target_parent_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Một công ty không thể tự làm công ty mẹ của chính mình",
                )

            # Kiểm tra công ty mẹ tồn tại
            parent = CustomerHierarchyRepository.get_by_id(db, target_parent_id)
            if not parent:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Công ty mẹ không tồn tại",
                )

            # Chặn chu trình lặp (Circular Dependency Prevention)
            # Truy ngược danh sách các tổ tiên của target_parent_id
            curr: Optional[Customer] = parent
            visited_ancestor_ids = set()
            while curr is not None:
                if str(curr.id) == str(customer_id):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Phát hiện chu trình lặp: Không thể gán công ty con làm công ty mẹ",
                    )
                if curr.id in visited_ancestor_ids:
                    break
                visited_ancestor_ids.add(curr.id)

                if not curr.parent_id:
                    break
                curr = CustomerHierarchyRepository.get_by_id(db, str(curr.parent_id))

        # 4. Cập nhật và lưu thay đổi
        CustomerHierarchyRepository.assign_parent(db, customer, target_parent_id)

        msg = (
            "Gán công ty mẹ thành công"
            if target_parent_id is not None
            else "Gỡ bỏ công ty mẹ thành công"
        )
        return AssignParentResponse(
            message=msg,
            customer_id=customer.id,
            parent_id=customer.parent_id,
        )

    @staticmethod
    def get_subsidiaries(
        db: Session,
        customer_id: str,
        user: User,
    ) -> List[SubsidiaryItemResponse]:
        """
        Lấy danh sách các công ty con trực tiếp của một công ty:
        - Kiểm tra quyền truy cập bản ghi công ty mẹ.
        - Lấy danh sách công ty con (parent_id == customer_id).
        - Tổng hợp số lượng deals và giá trị giao dịch của từng công ty con.
        """
        customer_raw = CustomerHierarchyRepository.get_by_id(db, customer_id)
        if not customer_raw:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Khách hàng không tồn tại",
            )

        customer = CustomerHierarchyRepository.get_scoped_by_id(db, customer_id, user)
        subsidiaries = CustomerHierarchyRepository.get_subsidiaries(db, customer.id)

        items: List[SubsidiaryItemResponse] = []
        for sub in subsidiaries:
            deals = CustomerHierarchyRepository.get_customer_deals(db, sub.id)
            deals_count = len(deals)
            total_deal_val = float(sum(d.value or 0.0 for d in deals))
            company_name = (
                sub.company.strip()
                if (sub.company and sub.company.strip())
                else sub.full_name
            )
            assigned_name = (
                sub.assigned_user.full_name if sub.assigned_user else None
            )

            items.append(
                SubsidiaryItemResponse(
                    id=sub.id,
                    name=company_name,
                    tax_code=getattr(sub, "tax_code", None),
                    status=sub.status,
                    assigned_to_name=assigned_name,
                    deals_count=deals_count,
                    total_deal_value=total_deal_val,
                )
            )

        return items

    @staticmethod
    def get_group_summary(
        db: Session,
        customer_id: str,
        user: User,
    ) -> GroupSummaryResponse:
        """
        Tổng hợp báo cáo giá trị toàn bộ nhóm / tập đoàn (Group Valuation Rollup):
        - Giá trị riêng của công ty mẹ (own_deal_value).
        - Danh sách chi tiết và tổng giá trị các công ty con (subsidiaries_deal_value).
        - Tổng giá trị toàn tập đoàn (total_group_value = own + subsidiaries).
        """
        customer_raw = CustomerHierarchyRepository.get_by_id(db, customer_id)
        if not customer_raw:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Khách hàng không tồn tại",
            )

        customer = CustomerHierarchyRepository.get_scoped_by_id(db, customer_id, user)

        # 1. Giá trị giao dịch của công ty mẹ
        parent_deals = CustomerHierarchyRepository.get_customer_deals(db, customer.id)
        own_deal_value = float(sum(d.value or 0.0 for d in parent_deals))

        # 2. Chi tiết và giá trị các công ty con
        subsidiary_items = CustomerHierarchyService.get_subsidiaries(db, customer.id, user)
        subsidiaries_deal_value = float(
            sum(sub.total_deal_value for sub in subsidiary_items)
        )

        total_group_value = own_deal_value + subsidiaries_deal_value
        parent_name = (
            customer.company.strip()
            if (customer.company and customer.company.strip())
            else customer.full_name
        )

        return GroupSummaryResponse(
            parent_company_id=customer.id,
            parent_company_name=parent_name,
            total_subsidiaries=len(subsidiary_items),
            own_deal_value=own_deal_value,
            subsidiaries_deal_value=subsidiaries_deal_value,
            total_group_value=total_group_value,
            subsidiaries=subsidiary_items,
        )
