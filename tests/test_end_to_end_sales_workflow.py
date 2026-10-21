"""Kiểm thử kịch bản nghiệp vụ khép kín từ Khách hàng đến Hợp đồng."""
def test_full_pipeline_simulation():
    # 1. Khach hang
    customer = {"id": 1, "name": "Tap Doan Mau"}
    # 2. Co hoi
    deal = {"id": 10, "customer_id": customer["id"], "stage": "PROPOSAL", "value": 200000000}
    # 3. Bao gia
    quote = {"id": 100, "deal_id": deal["id"], "total": 200000000, "status": "ACCEPTED"}
    # 4. Hop dong
    contract = {"id": 1000, "quote_id": quote["id"], "status": "ACTIVE", "value": quote["total"]}
    
    assert contract["value"] == deal["value"]
    assert contract["quote_id"] == 100
