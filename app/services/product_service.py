from typing import List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.product import Product, PriceList
from app.repositories.product_repository import ProductRepository
from app.schemas.product import (
    ProductDTO,
    CreateProductDTO,
    UpdateProductDTO,
    PriceListDTO,
    CreatePriceListDTO,
)

DIRECTOR_ROLES = {"super admin", "admin", "quản trị viên", "sales director", "director", "vp of sales", "giám đốc kinh doanh"}


def is_director_or_admin(user: User) -> bool:
    role = (user.role or "").strip().lower()
    return role in DIRECTOR_ROLES or "director" in role or "admin" in role


class ProductService:
    def __init__(self, db: Session) -> None:
        self.repo = ProductRepository(db)

    def get_products(
        self,
        current_user: User,
        search: Optional[str] = None,
        category: Optional[str] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[ProductDTO], int]:
        records, total = self.repo.get_products(
            search=search, category=category, is_active=is_active, skip=skip, limit=limit
        )

        # Nếu CSDL chưa có sản phẩm nào, tự động nạp danh mục sản phẩm tiêu chuẩn vào CSDL
        if total == 0 and not search and (not category or category == "all"):
            sample_products = [
                Product(
                    code="CRM-ENT-YEAR",
                    name="Gói NexusCRM Doanh Nghiệp (Enterprise 50 Users)",
                    category="Phần mềm CRM",
                    unit="Gói/Năm",
                    selling_price=120000000.0,
                    cost_price=65000000.0,
                    description="Bản quyền 50 tài khoản, tích hợp VoIP, API và luồng phê duyệt đa cấp",
                    is_active=True,
                ),
                Product(
                    code="CRM-PRO-YEAR",
                    name="Gói NexusCRM Chuyên Nghiệp (Pro 20 Users)",
                    category="Phần mềm CRM",
                    unit="Gói/Năm",
                    selling_price=48000000.0,
                    cost_price=22000000.0,
                    description="Bản quyền 20 tài khoản, phân hệ Bán hàng & Chăm sóc khách hàng",
                    is_active=True,
                ),
                Product(
                    code="ONBOARD-IMPL",
                    name="Dịch vụ Đào tạo & Chuyển giao Hệ thống Onboarding",
                    category="Dịch vụ Đào tạo & Onboarding",
                    unit="Gói",
                    selling_price=25000000.0,
                    cost_price=12000000.0,
                    description="Đào tạo trực tiếp 05 buổi cho toàn bộ phòng kinh doanh & hỗ trợ cấu hình dữ liệu",
                    is_active=True,
                ),
                Product(
                    code="CLOUD-DEDICATED",
                    name="Hạ tầng Cloud Server Riêng & Backup Hàng Ngày",
                    category="Gói Hạ tầng",
                    unit="Năm",
                    selling_price=36000000.0,
                    cost_price=18000000.0,
                    description="Máy chủ đám mây độc lập tốc độ cao, SLA 99.99%, sao lưu tự động",
                    is_active=True,
                ),
            ]
            for p in sample_products:
                self.repo.create(p)
            records, total = self.repo.get_products(
                search=search, category=category, is_active=is_active, skip=skip, limit=limit
            )

        can_view_cost = is_director_or_admin(current_user)

        dtos = [
            ProductDTO(
                id=p.id,
                code=p.code,
                sku=p.code,
                name=p.name,
                category=p.category,
                unit=p.unit,
                selling_price=float(p.selling_price),
                cost_price=float(p.cost_price) if can_view_cost else None,
                description=p.description,
                is_active=p.is_active,
                quote_count=self.repo.count_quotes(p.id, p.name),
                created_at=p.created_at,
            )
            for p in records
        ]
        return dtos, total

    def create_product(self, dto: CreateProductDTO, current_user: User) -> ProductDTO:
        code = (dto.code or dto.sku or "").strip()
        if not code:
            import time
            code = f"PRD-{int(time.time()) % 100000:05d}"

        existing = self.repo.get_by_code(code)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Mã sản phẩm '{code}' đã tồn tại trong hệ thống.",
            )

        can_view_cost = is_director_or_admin(current_user)
        cost_price_val = dto.cost_price if (dto.cost_price is not None and can_view_cost) else 0.0

        product = Product(
            code=code.upper(),
            name=dto.name.strip(),
            category=dto.category.strip() if dto.category else "Phần mềm CRM",
            unit=dto.unit.strip() if dto.unit else "Gói/Năm",
            selling_price=dto.selling_price or 0.0,
            cost_price=cost_price_val,
            description=dto.description,
            is_active=dto.is_active,
        )
        saved = self.repo.create(product)

        return ProductDTO(
            id=saved.id,
            code=saved.code,
            sku=saved.code,
            name=saved.name,
            category=saved.category,
            unit=saved.unit,
            selling_price=float(saved.selling_price),
            cost_price=float(saved.cost_price) if can_view_cost else None,
            description=saved.description,
            is_active=saved.is_active,
            quote_count=0,
            created_at=saved.created_at,
        )

    def update_product(
        self, product_id: str, dto: UpdateProductDTO, current_user: User
    ) -> ProductDTO:
        product = self.repo.get_by_id(product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy sản phẩm yêu cầu.",
            )

        if dto.name is not None:
            product.name = dto.name.strip()
        if dto.category is not None:
            product.category = dto.category.strip()
        if dto.unit is not None:
            product.unit = dto.unit.strip()
        if dto.selling_price is not None:
            product.selling_price = dto.selling_price
        if dto.cost_price is not None:
            if not is_director_or_admin(current_user):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Chỉ Giám đốc (Director) mới có quyền chỉnh sửa Giá vốn sản phẩm.",
                )
            product.cost_price = dto.cost_price
        if dto.description is not None:
            product.description = dto.description
        if dto.is_active is not None:
            product.is_active = dto.is_active

        saved = self.repo.update(product)
        can_view_cost = is_director_or_admin(current_user)

        return ProductDTO(
            id=saved.id,
            code=saved.code,
            sku=saved.code,
            name=saved.name,
            category=saved.category,
            unit=saved.unit,
            selling_price=float(saved.selling_price),
            cost_price=float(saved.cost_price) if can_view_cost else None,
            description=saved.description,
            is_active=saved.is_active,
            quote_count=self.repo.count_quotes(saved.id, saved.name),
            created_at=saved.created_at,
        )

    def delete_product(self, product_id: str) -> None:
        product = self.repo.get_by_id(product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy sản phẩm yêu cầu.",
            )

        # QUY TẮC AN NINH S2-05: Ngăn chặn xóa sản phẩm đã có báo giá tham chiếu
        if self.repo.is_referenced_by_quotes(product_id, product.name):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Không thể xóa sản phẩm '{product.name}' vì đang được tham chiếu trong Báo giá.",
            )

        self.repo.delete(product)

    # Price Lists
    def get_price_lists(self) -> List[PriceListDTO]:
        records = self.repo.get_price_lists()
        if not records:
            default_lists = [
                PriceList(
                    name="Bảng giá Tiêu chuẩn 2026",
                    code="PL-STANDARD-2026",
                    currency="VND",
                    discount_percent=0.0,
                    is_default=True,
                    description="Giá bán niêm yết chuẩn áp dụng cho tất cả khách hàng mới",
                ),
                PriceList(
                    name="Bảng giá Khách hàng Doanh nghiệp VIP (Tier 1)",
                    code="PL-ENTERPRISE-VIP",
                    currency="VND",
                    discount_percent=15.0,
                    is_default=False,
                    description="Chiết khấu 15% cho doanh nghiệp ký hợp đồng từ 100 triệu trở lên",
                ),
                PriceList(
                    name="Bảng giá Đối tác & Đại lý (Channel Partner)",
                    code="PL-PARTNER-CHANNEL",
                    currency="VND",
                    discount_percent=25.0,
                    is_default=False,
                    description="Chính sách chiết khấu 25% cho các đơn vị tích hợp hệ thống",
                ),
            ]
            for pl in default_lists:
                self.repo.create_price_list(pl)
            records = self.repo.get_price_lists()

        return [
            PriceListDTO(
                id=p.id,
                name=p.name,
                code=p.code,
                currency=p.currency,
                discount_percent=float(p.discount_percent),
                multiplier=round(1.0 - (float(p.discount_percent) / 100.0), 4),
                is_default=p.is_default,
                is_active=True,
                description=p.description,
                created_at=p.created_at,
            )
            for p in records
        ]

    def create_price_list(self, dto: CreatePriceListDTO) -> PriceListDTO:
        existing = self.repo.db.query(PriceList).filter(PriceList.code == dto.code.strip().upper()).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Mã bảng giá '{dto.code}' đã tồn tại trong hệ thống.",
            )

        discount_val = dto.discount_percent or 0.0
        if (discount_val == 0.0) and dto.multiplier is not None and dto.multiplier != 1.0:
            discount_val = round((1.0 - dto.multiplier) * 100.0, 2)

        pl = PriceList(
            name=dto.name.strip(),
            code=dto.code.strip().upper(),
            currency=dto.currency,
            discount_percent=discount_val,
            is_default=dto.is_default,
            description=dto.description,
        )
        saved = self.repo.create_price_list(pl)
        return PriceListDTO(
            id=saved.id,
            name=saved.name,
            code=saved.code,
            currency=saved.currency,
            discount_percent=float(saved.discount_percent),
            multiplier=round(1.0 - (float(saved.discount_percent) / 100.0), 4),
            is_default=saved.is_default,
            is_active=True,
            description=saved.description,
            created_at=saved.created_at,
        )
