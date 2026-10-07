from typing import Optional, List, Dict, Any, Set
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.customer import Customer
from app.models.user import User
from app.repositories.customer_repository import CustomerRepository
from app.schemas.customer import CustomerHierarchyDTO


class CorporateHierarchyService:
    """
    Service quản lý Cấu trúc Công ty Mẹ - Con (Corporate Hierarchy) S3-05.
    - Xây dựng cây phân cấp doanh nghiệp (Parent - Child Corporate Tree).
    - Tính toán giá trị doanh thu / hợp đồng tổng hợp toàn tập đoàn (Aggregated Contract Value).
    - Ngăn chặn vòng lặp cha - con (Circular Reference Prevention) & công ty tự làm mẹ của chính mình.
    """

    @staticmethod
    def get_hierarchy(
        db: Session,
        customer_id: str,
        user: User,
    ) -> CustomerHierarchyDTO:
        """
        Lấy cây phân cấp doanh nghiệp bắt đầu từ công ty gốc (Root Parent)
        hoặc chính khách hàng này, kèm tổng giá trị hợp đồng lũy kế toàn tập đoàn.
        """
        # Kiểm tra quyền truy cập vào khách hàng hiện tại
        customer = CustomerRepository.get_scoped_by_id(db, customer_id, user)

        # 1. Tìm công ty gốc cao nhất (Root Parent)
        curr = customer
        visited: Set[str] = {curr.id}
        while curr.parent_customer_id:
            parent = CustomerRepository.get_by_id(db, curr.parent_customer_id)
            if not parent or parent.id in visited:
                break
            curr = parent
            visited.add(curr.id)

        root = curr

        # 2. Đệ quy xây dựng cây phân cấp và tính tổng doanh số toàn tập đoàn
        return CorporateHierarchyService._build_node(db, root)

    @staticmethod
    def _build_node(db: Session, customer: Customer) -> CustomerHierarchyDTO:
        individual_val = float(customer.total_contract_value or 0.0)
        children_records = CustomerRepository.get_children(db, customer.id)

        children_dtos: List[CustomerHierarchyDTO] = []
        children_total_val = 0.0

        for child in children_records:
            child_dto = CorporateHierarchyService._build_node(db, child)
            children_dtos.append(child_dto)
            children_total_val += child_dto.groupContractValue

        group_total = individual_val + children_total_val

        return CustomerHierarchyDTO(
            id=customer.id,
            fullName=customer.full_name,
            company=customer.company or customer.full_name,
            taxCode=customer.tax_code,
            tier=customer.tier,
            status=customer.status,
            totalContractValue=individual_val,
            groupContractValue=group_total,
            children=children_dtos,
        )

    @staticmethod
    def set_parent(
        db: Session,
        customer_id: str,
        parent_id: Optional[str],
        user: User,
    ) -> Customer:
        """
        Thiết lập hoặc hủy công ty mẹ cho một khách hàng.
        Bảo đảm:
        - Không thể tự làm mẹ chính mình (customer_id == parent_id).
        - Không tạo vòng lặp (parent_id không được là con/cháu của customer_id).
        - Phân quyền hợp lệ trên cả 2 khách hàng.
        """
        customer = CustomerRepository.get_scoped_by_id(db, customer_id, user)

        if not parent_id or not str(parent_id).strip():
            # Hủy liên kết mẹ - con
            customer.parent_customer_id = None
            db.commit()
            db.refresh(customer)
            return customer

        parent_id_clean = str(parent_id).strip()

        if customer_id == parent_id_clean:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Doanh nghiệp không thể làm công ty mẹ của chính mình.",
            )

        parent = CustomerRepository.get_scoped_by_id(db, parent_id_clean, user)

        # Kiểm tra vòng lặp: parent_id không được là hậu duệ của customer_id
        if CustomerRepository.is_descendant(db, root_id=customer_id, target_id=parent_id_clean):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Không thể gán '{parent.company or parent.full_name}' làm công ty mẹ vì sẽ tạo thành vòng lặp tham chiếu (Circular Dependency).",
            )

        customer.parent_customer_id = parent.id
        db.commit()
        db.refresh(customer)
        return customer
