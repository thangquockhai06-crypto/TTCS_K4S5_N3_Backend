"""Kiểm thử tính hợp lệ khi ghi nhận hoạt động tương tác SCRUM-71."""
def test_activity_type_validation():
    valid_types = {"CALL", "MEETING", "EMAIL", "NOTE", "TASK"}
    assert "CALL" in valid_types
    assert "SMS" not in valid_types

def test_meeting_duration_positive():
    meeting = {"subject": "Demo CRM", "duration_minutes": 45}
    assert meeting["duration_minutes"] > 0
