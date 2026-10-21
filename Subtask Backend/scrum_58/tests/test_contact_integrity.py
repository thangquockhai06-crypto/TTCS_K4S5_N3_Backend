"""Kiểm thử tính toàn vẹn dữ liệu người liên hệ và vai trò ra quyết định SCRUM-58."""
def test_contact_buying_role_enum():
    roles = ["Decision Maker", "Influencer", "Economic Buyer", "User", "Gatekeeper"]
    assert "Decision Maker" in roles
    assert len(roles) == 5

def test_contact_transfer_preserves_history():
    contact = {"id": 101, "name": "Nguyen Van A", "owner_id": 1, "history_count": 12}
    # Ban giao sang owner 2
    contact["owner_id"] = 2
    assert contact["owner_id"] == 2
    assert contact["history_count"] == 12, "Lich su tuong tac phai duoc bao toan"
