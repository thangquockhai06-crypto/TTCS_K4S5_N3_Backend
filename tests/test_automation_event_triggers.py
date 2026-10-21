"""Kiểm thử cơ chế đối sánh điều kiện kích hoạt tự động hóa."""
def test_event_matching_trigger():
    rule = {"trigger_event": "DEAL_WON", "action_type": "CREATE_CONTRACT"}
    event = "DEAL_WON"
    
    should_execute = (rule["trigger_event"] == event)
    assert should_execute is True
