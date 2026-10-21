"""Tiện ích tạo mẫu tài liệu PDF thử nghiệm cho báo giá và hợp đồng."""
def build_html_preview(quote_number: str, customer_name: str, total_vnd: str) -> str:
    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"><title>Báo giá {quote_number}</title></head>
    <body style="font-family: Arial, sans-serif; padding: 30px;">
        <h2>BÁO GIÁ DỊCH VỤ - {quote_number}</h2>
        <p><strong>Khách hàng:</strong> {customer_name}</p>
        <p><strong>Tổng giá trị:</strong> {total_vnd} VNĐ</p>
    </body>
    </html>
    """

if __name__ == "__main__":
    html = build_html_preview("Q-2026-DEMO", "Cong Ty TNHH Giai Phap So", "150,000,000")
    print("Sample PDF HTML template generated.")
