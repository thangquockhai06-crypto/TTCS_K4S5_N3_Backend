from app.core.utils.vietnamese_humanizer import format_duration_vietnamese


def test_format_duration_vietnamese():
    assert format_duration_vietnamese(0) == "vừa xong"
    assert format_duration_vietnamese(60) == "1 phút"
    assert format_duration_vietnamese(3600) == "1 giờ"
    assert format_duration_vietnamese(3660) == "1 giờ 1 phút"
    assert format_duration_vietnamese(86400) == "1 ngày"
    assert format_duration_vietnamese(90000) == "1 ngày 1 giờ"
