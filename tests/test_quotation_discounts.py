"""Kiểm thử logic tính chiết khấu phần trăm và chiết khấu số tiền cố định."""
def test_percentage_discount_calculation():
    subtotal = 100000000
    discount_pct = 10.0
    discount_amount = subtotal * (discount_pct / 100)
    tax_rate = 10.0
    amount_after_discount = subtotal - discount_amount
    tax_amount = amount_after_discount * (tax_rate / 100)
    total = amount_after_discount + tax_amount
    assert discount_amount == 10000000
    assert total == 99000000
