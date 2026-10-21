from app.core.utils.color_generator import get_priority_color
def test_color():
    assert get_priority_color('urgent') == '#EF4444'
