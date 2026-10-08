"""Kiểm thử tính toán lợi nhuận và biên độ tài chính SCRUM-75."""
def test_gross_profit_calculation():
    revenue = 2000000000
    cost = 1400000000
    gross_profit = revenue - cost
    assert gross_profit == 600000000
    margin = (gross_profit / revenue) * 100
    assert margin == 30.0
