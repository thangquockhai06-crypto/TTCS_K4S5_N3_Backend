"""Kiểm thử máy trạng thái hợp đồng (Draft -> Pending -> Active -> Terminated)."""
def test_valid_contract_transitions():
    allowed_transitions = {
        "DRAFT": ["PENDING", "CANCELLED"],
        "PENDING": ["ACTIVE", "REJECTED"],
        "ACTIVE": ["EXPIRED", "TERMINATED", "RENEWED"],
        "TERMINATED": [],
        "EXPIRED": ["RENEWED"]
    }
    
    def can_transition(current, target):
        return target in allowed_transitions.get(current, [])
        
    assert can_transition("DRAFT", "PENDING") is True
    assert can_transition("DRAFT", "TERMINATED") is False
    assert can_transition("ACTIVE", "EXPIRED") is True
