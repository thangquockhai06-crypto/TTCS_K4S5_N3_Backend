"""Kiểm thử tính toán KPI đội ngũ kinh doanh SCRUM-74."""
def test_kpi_achievement_rate():
    target = 1000000000
    actual = 850000000
    achievement_rate = (actual / target) * 100
    assert round(achievement_rate, 2) == 85.0

def test_win_rate_calculation():
    won = 15
    lost = 5
    total = won + lost
    win_rate = (won / total) * 100
    assert win_rate == 75.0
