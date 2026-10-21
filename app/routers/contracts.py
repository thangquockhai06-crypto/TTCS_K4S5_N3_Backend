from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.contract import ContractDTO, CreateContractDTO, ContractRenewalDTO
from app.schemas.deal import DealDTO
from app.services.contract_service import ContractService
from app.services.deal_service import DealService
from app.services.pdf_template_service import PdfTemplateService
from app.core.export import export_to_excel

router = APIRouter(prefix="/contracts", tags=["Contracts Management (S7-04 & S7-07)"])


@router.get("", response_model=List[ContractDTO], summary="Lấy danh sách hợp đồng & cảnh báo hết hạn (S7-07)")
def get_contracts(
    search: Optional[str] = Query(None, description="Tìm theo số hợp đồng hoặc tiêu đề"),
    status: Optional[str] = Query(None, description="Lọc theo trạng thái: active, expiring_soon, expired, renewed"),
    customerId: Optional[str] = Query(None, description="Lọc theo khách hàng"),
    expiringWithinDays: Optional[int] = Query(None, description="Lọc hợp đồng sắp hết hạn trong N ngày tới"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[ContractDTO]:
    contracts, _ = ContractService.get_contracts(
        db=db,
        user=current_user,
        search=search,
        status=status,
        customer_id=customerId,
        expiring_within_days=expiringWithinDays,
        skip=skip,
        limit=limit,
    )
    return contracts


@router.post("", response_model=ContractDTO, status_code=status.HTTP_201_CREATED, summary="Tạo mới hợp đồng từ báo giá (S7-04)")
def create_contract(
    dto: CreateContractDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ContractDTO:
    return ContractService.convert_quotation_to_contract(db=db, dto=dto, user=current_user)


@router.get("/export", summary="Xuất danh sách hợp đồng ra Excel (.xlsx)")
def export_contracts(
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    contracts, _ = ContractService.get_contracts(
        db=db,
        user=current_user,
        search=search,
        status=status,
        skip=0,
        limit=1000,
    )
    headers = ["Số Hợp Đồng", "Tiêu đề", "Khách hàng", "Doanh nghiệp", "Tổng giá trị (VNĐ)", "Ngày ký", "Ngày hiệu lực", "Ngày hết hạn", "Số ngày còn lại", "Trạng thái"]
    rows = [
        [
            c.contractNumber,
            c.title,
            c.customerName or "",
            c.customerCompany or "",
            c.totalValue,
            c.signingDate,
            c.effectiveDate,
            c.expiryDate,
            c.remainingDays,
            c.status,
        ]
        for c in contracts
    ]
    return export_to_excel(
        sheet_title="HopDong",
        headers=headers,
        rows=rows,
        filename="danh_sach_hop_dong.xlsx",
    )


@router.get("/{contract_id}", response_model=ContractDTO, summary="Xem chi tiết hợp đồng (S7-04, S7-07)")
def get_contract_detail(
    contract_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ContractDTO:
    return ContractService.get_contract_by_id(db=db, contract_id=contract_id, user=current_user)


@router.post("/{contract_id}/renew", response_model=DealDTO, summary="Tạo cơ hội tái ký hợp đồng từ hợp đồng sắp hết hạn (S7-07)")
def renew_contract(
    contract_id: str,
    dto: ContractRenewalDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DealDTO:
    new_deal = ContractService.create_renewal_opportunity(db=db, contract_id=contract_id, dto=dto, user=current_user)
    return DealService.map_to_dto(new_deal)


@router.get("/{contract_id}/pdf", response_class=HTMLResponse, summary="Xuất hợp đồng ra PDF/HTML theo mẫu doanh nghiệp (S7-05)")
def export_contract_pdf(
    contract_id: str,
    templateId: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    S7-05: Xuất hợp đồng ra HTML/PDF với mẫu doanh nghiệp cấu hình được.
    Bao gồm logo, thông tin 2 bên, điều khoản, dòng sản phẩm, tổng tiền bằng số và bằng chữ.
    """
    contract = ContractService.get_contract_by_id(db=db, contract_id=contract_id, user=current_user)
    tpl = None
    if templateId or contract.templateId:
        tpl = PdfTemplateService.get_template_by_id(db, templateId or contract.templateId)
    if not tpl:
        tpl = PdfTemplateService.get_default_template(db, template_type="contract")

    logo_html = f'<img src="{tpl.logo_url}" alt="Logo" style="height: 55px; object-fit: contain;" />' if tpl and tpl.logo_url else '<div style="font-size: 24px; font-weight: bold; color: #1e3a8a;">NEXUS CRM</div>'
    comp_name = tpl.company_name if tpl else "CÔNG TY CỔ PHẦN CÔNG NGHỆ NEXUS VIỆT NAM"
    comp_addr = tpl.company_address if tpl else "Tòa nhà Nexus Tower, 180 Cầu Giấy, Hà Nội"
    comp_tax = tpl.company_tax_code if tpl else "0108889999"
    comp_phone = tpl.company_phone if tpl else "1900 6868"
    terms = tpl.terms_and_conditions if tpl and tpl.terms_and_conditions else "Hai bên cam kết thực hiện đầy đủ các quyền và nghĩa vụ quy định trong hợp đồng."

    items_rows = ""
    for idx, it in enumerate(contract.items, 1):
        items_rows += f"""
        <tr>
            <td style="text-align: center; padding: 10px; border: 1px solid #e2e8f0;">{idx}</td>
            <td style="padding: 10px; border: 1px solid #e2e8f0;"><strong>{it.productName}</strong></td>
            <td style="text-align: center; padding: 10px; border: 1px solid #e2e8f0;">{it.unit}</td>
            <td style="text-align: center; padding: 10px; border: 1px solid #e2e8f0;">{it.quantity}</td>
            <td style="text-align: right; padding: 10px; border: 1px solid #e2e8f0;">{it.unitPrice:,.0f} đ</td>
            <td style="text-align: right; padding: 10px; border: 1px solid #e2e8f0;">{it.discountAmount:,.0f} đ</td>
            <td style="text-align: right; padding: 10px; border: 1px solid #e2e8f0; font-weight: 600;">{it.lineTotal:,.0f} đ</td>
        </tr>
        """

    html = f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <title>Hợp đồng {contract.contractNumber} - NexusCRM</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif; color: #1e293b; margin: 0; padding: 40px; background: #fff; line-height: 1.6; font-size: 14px; }}
        .national-header {{ text-align: center; margin-bottom: 25px; }}
        .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #3b82f6; padding-bottom: 15px; margin-bottom: 25px; }}
        .title {{ text-align: center; margin: 25px 0 10px; text-transform: uppercase; color: #1e3a8a; font-size: 22px; }}
        .parties {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 24px; }}
        .party-box {{ background: #f8fafc; border: 1px solid #e2e8f0; padding: 16px; border-radius: 8px; }}
        table {{ width: 100%; border-collapse: collapse; margin-bottom: 24px; }}
        th {{ background: #f1f5f9; color: #334155; padding: 10px; border: 1px solid #cbd5e1; text-align: left; }}
        .words-block {{ background: #eff6ff; border-left: 4px solid #3b82f6; padding: 12px 16px; margin-bottom: 24px; font-style: italic; }}
        .signatures {{ display: flex; justify-content: space-between; margin-top: 60px; text-align: center; }}
        @media print {{ body {{ padding: 0; }} }}
    </style>
</head>
<body>
    <div class="national-header">
        <strong style="font-size: 15px;">CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM</strong><br>
        <strong>Độc lập - Tự do - Hạnh phúc</strong><br>
        <span>---o0o---</span>
    </div>

    <div class="header">
        <div>
            {logo_html}
        </div>
        <div style="text-align: right;">
            <div style="font-size: 16px; font-weight: bold; color: #1e3a8a;">SỐ HỢP ĐỒNG: {contract.contractNumber}</div>
            <div style="color: #64748b; font-size: 13px;">Ngày ký: {contract.signingDate}</div>
            <div style="color: #10b981; font-weight: 600; font-size: 13px;">Hiệu lực: {contract.effectiveDate} đến {contract.expiryDate}</div>
        </div>
    </div>

    <h1 class="title">{contract.title}</h1>

    <div class="parties">
        <div class="party-box">
            <strong style="color: #1e3a8a;">BÊN A (BÊN SỬ DỤNG DỊCH VỤ):</strong><br>
            <strong>{contract.customerCompany or contract.customerName}</strong><br>
            Người đại diện: {contract.customerName}<br>
            Mã số thuế: {contract.customerTaxCode or 'Chưa cập nhật'}<br>
            Điều khoản thanh toán: {contract.paymentTerms or 'Theo thỏa thuận'}
        </div>
        <div class="party-box">
            <strong style="color: #1e3a8a;">BÊN B (BÊN CUNG CẤP DỊCH VỤ):</strong><br>
            <strong>{comp_name}</strong><br>
            Người đại diện: {contract.ownerName or 'Tổng Giám Đốc'}<br>
            Mã số thuế: {comp_tax}<br>
            Địa chỉ: {comp_addr}<br>
            Hotline: {comp_phone}
        </div>
    </div>

    <p>Hai bên cùng thống nhất ký kết hợp đồng kinh tế với các điều khoản và danh mục dịch vụ dưới đây:</p>

    <table>
        <thead>
            <tr>
                <th style="width: 40px; text-align: center;">STT</th>
                <th>Sản phẩm / Dịch vụ</th>
                <th style="width: 70px; text-align: center;">ĐVT</th>
                <th style="width: 60px; text-align: center;">SL</th>
                <th style="width: 120px; text-align: right;">Đơn giá</th>
                <th style="width: 110px; text-align: right;">Chiết khấu</th>
                <th style="width: 130px; text-align: right;">Thành tiền</th>
            </tr>
        </thead>
        <tbody>
            {items_rows}
        </tbody>
    </table>

    <div style="text-align: right; font-size: 17px; font-weight: bold; color: #1d4ed8; margin-bottom: 12px;">
        TỔNG GIÁ TRỊ HỢP ĐỒNG: {contract.totalValue:,.0f} VNĐ
    </div>

    <div class="words-block">
        <strong>Bằng chữ:</strong> {contract.totalInWords}
    </div>

    <div style="margin-bottom: 30px; font-size: 13px; color: #475569; white-space: pre-line;">
        <strong>ĐIỀU KHOẢN CHUNG VÀ CAM KẾT:</strong><br>
        {terms}
    </div>

    <div class="signatures">
        <div style="width: 250px;">
            <strong>ĐẠI DIỆN BÊN A</strong><br>
            <span style="font-size: 12px; color: #64748b;">(Ký, ghi rõ họ tên và đóng dấu)</span>
            <div style="height: 90px;"></div>
            <strong>{contract.customerName}</strong>
        </div>
        <div style="width: 250px;">
            <strong>ĐẠI DIỆN BÊN B</strong><br>
            <span style="font-size: 12px; color: #64748b;">(Ký, ghi rõ họ tên và đóng dấu)</span>
            <div style="height: 90px;"></div>
            <strong>{comp_name}</strong>
        </div>
    </div>
</body>
</html>
    """
    return HTMLResponse(content=html)
