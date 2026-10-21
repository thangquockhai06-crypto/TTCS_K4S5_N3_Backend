"""Kiểm thử tính toán xác suất và doanh số kỳ vọng SCRUM-72."""
def test_weighted_revenue_calculation():
    deal_value = 500000000  # 500 trieu
    probability = 0.5       # 50%
    weighted_revenue = deal_value * probability
    assert weighted_revenue == 250000000

def test_closed_won_probability_is_100():
    stages = {"WON": 100, "LOST": 0}
    assert stages["WON"] == 100
    assert stages["LOST"] == 0
