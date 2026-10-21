from app.core.utils.math_utils import calculate_percentage
def test_pct():
    assert calculate_percentage(5, 10) == 50.0
    assert calculate_percentage(0, 0) == 0.0
