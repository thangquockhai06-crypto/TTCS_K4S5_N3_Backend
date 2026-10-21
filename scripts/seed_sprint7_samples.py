"""Script nạp dữ liệu thử nghiệm cho module Báo giá, Hợp đồng và Tự động hóa."""
def get_sample_quotations():
    return [
        {
            "quote_number": "Q-2026-0001",
            "customer_id": 1,
            "subtotal": 120000000,
            "tax_amount": 12000000,
            "total_amount": 132000000,
            "status": "ACCEPTED"
        },
        {
            "quote_number": "Q-2026-0002",
            "customer_id": 2,
            "subtotal": 450000000,
            "tax_amount": 45000000,
            "total_amount": 495000000,
            "status": "SENT"
        }
    ]

if __name__ == "__main__":
    quotes = get_sample_quotations()
    print(f"Sample sprint 7 records ready: {len(quotes)} quotations.")
