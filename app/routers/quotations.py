from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.quotation import (
    QuotationDTO,
    CreateQuotationDTO,
    UpdateQuotationDTO,
    QuoteApprovalDecisionDTO,
    QuoteCompareDTO,
)
from app.schemas.contract import CreateContractDTO, ContractDTO
from app.services.quotation_service import QuotationService
from app.services.contract_service import ContractService
from app.services.pdf_template_service import PdfTemplateService
from app.core.export import export_to_excel

router = APIRouter(prefix="/quotations", tags=["Quotations Management"])


@router.get("", response_model=List[QuotationDTO], summary="Lấy danh sách các báo giá (S7-01 -> S7-03)")
def get_quotations(
    search: Optional[str] = Query(None, description="Tìm kiếm theo tiêu đề hoặc mã báo giá"),
    status: Optional[str] = Query(None, description="Lọc theo trạng thái: draft, pending_approval, approved, sent, accepted, rejected, expired"),
    customerId: Optional[str] = Query(None, description="Lọc theo khách hàng"),
    dealId: Optional[str] = Query(None, description="Lọc theo cơ hội bán hàng"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[QuotationDTO]:
    quotations, _ = QuotationService.get_quotations(
        db=db,
        user=current_user,
        search=search,
        status=status,
        customer_id=customerId,
        deal_id=dealId,
        skip=skip,
        limit=limit,
    )
    return quotations


@router.get("/export", summary="Xuất danh sách báo giá ra Excel (.xlsx)")
def export_quotations(
    search: Optional[str] = Query(None, description="Tìm kiếm theo tiêu đề hoặc mã báo giá"),
    status: Optional[str] = Query(None, description="Lọc theo trạng thái"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Xuất danh sách báo giá ra Excel tuân thủ Data Scope."""
    quotes, _ = QuotationService.get_quotations(
        db=db,
        user=current_user,
        search=search,
        status=status,
        skip=0,
        limit=1000,
    )
    headers = ["Số Báo Giá", "Phiên bản", "Tiêu đề", "Khách hàng", "Doanh nghiệp", "Tổng tiền (VNĐ)", "Chiết khấu (%)", "Trạng thái", "Hạn hiệu lực", "Ngày tạo"]
    rows = [
        [
            q.quoteNumber,
            f"v{q.version}",
            q.title,
            q.customerName or "",
            q.customerCompany or "",
            q.grandTotal,
            q.totalDiscountPercent,
            q.status,
            q.validUntil or "",
            q.createdAt or "",
        ]
        for q in quotes
    ]
    return export_to_excel(
        sheet_title="BaoGia",
        headers=headers,
        rows=rows,
        filename="danh_sach_bao_gia.xlsx",
    )


@router.post("", response_model=QuotationDTO, status_code=status.HTTP_201_CREATED, summary="Tạo mới báo giá từ Cơ hội bán hàng (S7-01)")
def create_quotation(
    dto: CreateQuotationDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> QuotationDTO:
    return QuotationService.create_quotation(db=db, dto=dto, user=current_user)


@router.get("/{quotation_id}", response_model=QuotationDTO, summary="Xem chi tiết báo giá đầy đủ (S7-01, S7-02)")
def get_quotation_detail(
    quotation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> QuotationDTO:
    return QuotationService.get_quotation_by_id(db=db, quotation_id=quotation_id, user=current_user)


@router.put("/{quotation_id}", response_model=QuotationDTO, summary="Cập nhật bản nháp hoặc tạo Version mới nếu đã gửi (S7-01 & S7-03)")
def update_quotation(
    quotation_id: str,
    dto: UpdateQuotationDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> QuotationDTO:
    return QuotationService.update_quotation(db=db, quotation_id=quotation_id, dto=dto, user=current_user)


@router.post("/{quotation_id}/submit", response_model=QuotationDTO, summary="Đệ trình báo giá để phê duyệt hoặc tự động duyệt (S7-01, S7-02)")
def submit_quotation(
    quotation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> QuotationDTO:
    return QuotationService.submit_for_approval(db=db, quote_id=quotation_id, user=current_user)


@router.post("/{quotation_id}/approval", response_model=QuotationDTO, summary="Phê duyệt, Từ chối hoặc Yêu cầu sửa đổi báo giá (S7-02)")
def decide_approval(
    quotation_id: str,
    decision: QuoteApprovalDecisionDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> QuotationDTO:
    return QuotationService.decide_approval(
        db=db,
        quote_id=quotation_id,
        action=decision.action,
        comment=decision.comment,
        user=current_user,
    )


@router.post("/{quotation_id}/send", response_model=QuotationDTO, summary="Gửi báo giá đã được phê duyệt cho khách hàng (S7-02, S7-06)")
def send_quotation(
    quotation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> QuotationDTO:
    return QuotationService.send_quotation(db=db, quote_id=quotation_id, user=current_user)


@router.get("/{quotation_id}/compare/{target_id}", response_model=QuoteCompareDTO, summary="So sánh trực quan Side-by-side giữa 2 phiên bản (S7-03)")
def compare_versions(
    quotation_id: str,
    target_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> QuoteCompareDTO:
    return QuotationService.compare_versions(
        db=db,
        quote_id_a=quotation_id,
        quote_id_b=target_id,
        user=current_user,
    )


@router.post("/{quotation_id}/convert-to-contract", response_model=ContractDTO, summary="Chuyển đổi Báo giá được chấp thuận sang Hợp đồng (S7-04)")
def convert_to_contract(
    quotation_id: str,
    dto: CreateContractDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ContractDTO:
    dto.quotationId = quotation_id
    return ContractService.convert_quotation_to_contract(db=db, dto=dto, user=current_user)


@router.get("/{quotation_id}/pdf", response_class=HTMLResponse, summary="Xuất báo giá ra tài liệu PDF / bản in theo mẫu cấu hình (S7-05)")
def export_quotation_pdf(
    quotation_id: str,
    templateId: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    S7-05: Xuất Báo giá ra HTML/PDF với mẫu doanh nghiệp cấu hình được.
    Bao gồm logo, thông tin doanh nghiệp, dòng sản phẩm, tổng tiền bằng số và bằng chữ.
    """
    quote = QuotationService.get_quotation_by_id(db=db, quotation_id=quotation_id, user=current_user)
    tpl = None
    if templateId or quote.templateId:
        tpl = PdfTemplateService.get_template_by_id(db, templateId or quote.templateId)
    if not tpl:
        tpl = PdfTemplateService.get_default_template(db, template_type="quotation")

    logo_html = f'<img src="{tpl.logo_url}" alt="Logo" style="height: 55px; object-fit: contain;" />' if tpl and tpl.logo_url else '<div style="font-size: 24px; font-weight: bold; color: #1e3a8a;">NEXUS CRM</div>'
    comp_name = tpl.company_name if tpl else "CÔNG TY CỔ PHẦN CÔNG NGHỆ NEXUS VIỆT NAM"
    comp_addr = tpl.company_address if tpl else "Tòa nhà Nexus Tower, 180 Cầu Giấy, Hà Nội"
    comp_tax = tpl.company_tax_code if tpl else "0108889999"
    comp_phone = tpl.company_phone if tpl else "1900 6868"
    terms = tpl.terms_and_conditions if tpl and tpl.terms_and_conditions else (quote.notes or "Điều khoản chuẩn áp dụng theo quy định của Nexus.")

    items_rows = ""
    for idx, it in enumerate(quote.items, 1):
        items_rows += f"""
        <tr>
            <td style="text-align: center; padding: 10px; border: 1px solid #e2e8f0;">{idx}</td>
            <td style="padding: 10px; border: 1px solid #e2e8f0;"><strong>{it.productName}</strong><br><small style="color: #64748b;">{it.description or ''}</small></td>
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
    <title>Báo giá {quote.quoteNumber} - NexusCRM</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif; color: #1e293b; margin: 0; padding: 40px; background: #fff; line-height: 1.5; }}
        .header {{ display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 2px solid #3b82f6; padding-bottom: 20px; }}
        .title {{ text-align: center; margin: 30px 0 20px; text-transform: uppercase; color: #1e3a8a; }}
        .meta-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 28px; background: #f8fafc; padding: 20px; border-radius: 8px; border: 1px solid #e2e8f0; }}
        table {{ width: 100%; border-collapse: collapse; margin-bottom: 24px; font-size: 14px; }}
        th {{ background: #f1f5f9; color: #334155; padding: 12px 10px; border: 1px solid #cbd5e1; text-align: left; }}
        .totals-block {{ margin-left: auto; width: 380px; margin-bottom: 24px; }}
        .totals-row {{ display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px dashed #e2e8f0; }}
        .grand-total {{ font-size: 18px; font-weight: bold; color: #1d4ed8; border-bottom: 2px solid #1d4ed8; padding-top: 8px; }}
        .words-block {{ background: #eff6ff; border-left: 4px solid #3b82f6; padding: 12px 16px; margin-bottom: 28px; font-style: italic; }}
        .signatures {{ display: flex; justify-content: space-between; margin-top: 50px; text-align: center; }}
        @media print {{ body {{ padding: 0; }} }}
    </style>
</head>
<body>
    <div class="header">
        <div>
            {logo_html}
            <div style="font-weight: bold; margin-top: 10px; font-size: 15px;">{comp_name}</div>
            <div style="font-size: 13px; color: #64748b;">MST: {comp_tax} | Hotline: {comp_phone}</div>
            <div style="font-size: 13px; color: #64748b;">Địa chỉ: {comp_addr}</div>
        </div>
        <div style="text-align: right;">
            <div style="font-size: 18px; font-weight: bold; color: #1e3a8a;">SỐ: {quote.quoteNumber}</div>
            <div style="font-size: 13px; color: #64748b;">Phiên bản: v{quote.version}</div>
            <div style="font-size: 13px; color: #64748b;">Ngày tạo: {quote.createdAt[:10] if quote.createdAt else ''}</div>
            <div style="font-size: 13px; color: #dc2626; font-weight: 600;">Hiệu lực đến: {quote.validUntil or '30 ngày'}</div>
        </div>
    </div>

    <h1 class="title">{quote.title}</h1>

    <div class="meta-grid">
        <div>
            <div style="font-weight: bold; color: #475569; margin-bottom: 6px; font-size: 13px; text-transform: uppercase;">Thông tin Khách hàng:</div>
            <div><strong>{quote.customerCompany or quote.customerName}</strong></div>
            <div>Người liên hệ: {quote.customerName}</div>
            <div>Điện thoại: {quote.customerPhone or 'N/A'} | Email: {quote.customerEmail or 'N/A'}</div>
            <div>Mã số thuế: {quote.customerTaxCode or 'Chưa cập nhật'}</div>
            <div>Địa chỉ: {quote.customerAddress or 'Toàn quốc'}</div>
        </div>
        <div>
            <div style="font-weight: bold; color: #475569; margin-bottom: 6px; font-size: 13px; text-transform: uppercase;">Đơn vị cung cấp giải pháp:</div>
            <div><strong>{comp_name}</strong></div>
            <div>Chuyên viên tư vấn: {quote.ownerName or 'Chuyên viên Kinh doanh'}</div>
            <div>Điều khoản thanh toán: {quote.paymentTerms or 'Theo thỏa thuận'}</div>
            <div>Điều khoản giao hàng: {quote.deliveryTerms or 'Theo quy chuẩn SaaS'}</div>
        </div>
    </div>

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

    <div class="totals-block">
        <div class="totals-row">
            <span>Tổng cộng tiền hàng:</span>
            <span>{quote.subtotal:,.0f} đ</span>
        </div>
        <div class="totals-row">
            <span>Tổng mức chiết khấu ({quote.totalDiscountPercent:.1f}%):</span>
            <span style="color: #dc2626;">- {quote.totalDiscountAmount:,.0f} đ</span>
        </div>
        <div class="totals-row">
            <span>Thuế GTGT (VAT):</span>
            <span>{quote.vatAmount:,.0f} đ</span>
        </div>
        <div class="totals-row grand-total">
            <span>TỔNG THANH TOÁN:</span>
            <span>{quote.grandTotal:,.0f} VNĐ</span>
        </div>
    </div>

    <div class="words-block">
        <strong>Bằng chữ:</strong> {quote.totalInWords}
    </div>

    <div style="margin-bottom: 24px; font-size: 13px; color: #475569; white-space: pre-line;">
        <strong>ĐIỀU KHOẢN VÀ ĐIỀU KIỆN ÁP DỤNG:</strong><br>
        {terms}
    </div>

    <div class="signatures">
        <div style="width: 250px;">
            <strong>ĐẠI DIỆN KHÁCH HÀNG</strong><br>
            <span style="font-size: 12px; color: #64748b;">(Ký, ghi rõ họ tên và đóng dấu)</span>
            <div style="height: 80px;"></div>
        </div>
        <div style="width: 250px;">
            <strong>ĐẠI DIỆN NEXUS CRM</strong><br>
            <span style="font-size: 12px; color: #64748b;">(Ký, ghi rõ họ tên và đóng dấu)</span>
            <div style="height: 80px;"></div>
            <strong>{quote.ownerName or 'Đại diện có thẩm quyền'}</strong>
        </div>
    </div>
</body>
</html>
    """
    return HTMLResponse(content=html)
