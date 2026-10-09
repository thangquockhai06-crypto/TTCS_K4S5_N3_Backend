"""Kiểm thử quy tắc giá và thẩm quyền duyệt chiết khấu SCRUM-80."""
def test_discount_approval_thresholds():
    def get_approver(discount_pct):
        if discount_pct <= 5:
            return "SALES_REP"
        elif discount_pct <= 15:
            return "SALES_MANAGER"
        return "DIRECTOR"
    
    assert get_approver(3) == "SALES_REP"
    assert get_approver(10) == "SALES_MANAGER"
    assert get_approver(20) == "DIRECTOR"
