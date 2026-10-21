import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.deal import Deal
from app.models.deal_history import DealHistory
from app.models.deal_member import DealMember
from app.models.activity import Activity


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class TestDealCollaborationAndMembers:
    """Kiểm thử thêm / xóa thành viên phối hợp cơ hội bán hàng (SCRUM-207)."""

    def test_add_member_success_by_owner(self, client: TestClient, seed_data: dict):
        token_a = seed_data["tokens"]["emp_a"]
        deal_a = seed_data["deals"]["deal_a"]
        emp_b = seed_data["users"]["emp_b"]

        res = client.post(
            f"/api/v1/deals/{deal_a.id}/members",
            headers=auth_header(token_a),
            json={"user_id": emp_b.id, "role_in_deal": "SUPPORT"},
        )
        assert res.status_code == 201
        data = res.json()
        assert data["deal_id"] == deal_a.id
        assert data["user_id"] == emp_b.id
        assert data["role_in_deal"] == "SUPPORT"
        assert data["user_name"] == emp_b.full_name

    def test_add_member_prevent_adding_owner(self, client: TestClient, seed_data: dict):
        token_a = seed_data["tokens"]["emp_a"]
        deal_a = seed_data["deals"]["deal_a"]
        emp_a = seed_data["users"]["emp_a"]

        res = client.post(
            f"/api/v1/deals/{deal_a.id}/members",
            headers=auth_header(token_a),
            json={"user_id": emp_a.id, "role_in_deal": "COLLABORATOR"},
        )
        assert res.status_code == 400
        assert "chính người sở hữu" in res.json()["detail"]

    def test_add_member_duplicate_prevention(self, client: TestClient, seed_data: dict):
        token_a = seed_data["tokens"]["emp_a"]
        deal_a = seed_data["deals"]["deal_a"]
        emp_b = seed_data["users"]["emp_b"]

        # Thêm lần 1
        res1 = client.post(
            f"/api/v1/deals/{deal_a.id}/members",
            headers=auth_header(token_a),
            json={"user_id": emp_b.id, "role_in_deal": "COLLABORATOR"},
        )
        assert res1.status_code == 201

        # Thêm lần 2 -> 400 Bad Request
        res2 = client.post(
            f"/api/v1/deals/{deal_a.id}/members",
            headers=auth_header(token_a),
            json={"user_id": emp_b.id, "role_in_deal": "SUPPORT"},
        )
        assert res2.status_code == 400
        assert "đã là thành viên" in res2.json()["detail"]

    def test_add_member_forbidden_for_unauthorized_rep(self, client: TestClient, seed_data: dict):
        token_beta = seed_data["tokens"]["emp_beta"]
        deal_a = seed_data["deals"]["deal_a"]
        emp_b = seed_data["users"]["emp_b"]

        res = client.post(
            f"/api/v1/deals/{deal_a.id}/members",
            headers=auth_header(token_beta),
            json={"user_id": emp_b.id, "role_in_deal": "SUPPORT"},
        )
        assert res.status_code == 403

    def test_add_member_allowed_for_team_lead_and_director(self, client: TestClient, seed_data: dict):
        token_lead = seed_data["tokens"]["team_leader"]
        token_dir = seed_data["tokens"]["sales_director"]
        deal_a = seed_data["deals"]["deal_a"]
        emp_b = seed_data["users"]["emp_b"]
        emp_beta = seed_data["users"]["emp_beta"]

        # Team leader quản lý nhóm của emp_a thêm emp_b
        res1 = client.post(
            f"/api/v1/deals/{deal_a.id}/members",
            headers=auth_header(token_lead),
            json={"user_id": emp_b.id, "role_in_deal": "CO_SALES"},
        )
        assert res1.status_code == 201

        # Director thêm emp_beta
        res2 = client.post(
            f"/api/v1/deals/{deal_a.id}/members",
            headers=auth_header(token_dir),
            json={"user_id": emp_beta.id, "role_in_deal": "PRE_SALES"},
        )
        assert res2.status_code == 201

    def test_get_members_list(self, client: TestClient, seed_data: dict):
        token_a = seed_data["tokens"]["emp_a"]
        deal_a = seed_data["deals"]["deal_a"]
        emp_b = seed_data["users"]["emp_b"]

        client.post(
            f"/api/v1/deals/{deal_a.id}/members",
            headers=auth_header(token_a),
            json={"user_id": emp_b.id, "role_in_deal": "SUPPORT"},
        )

        res = client.get(f"/api/v1/deals/{deal_a.id}/members", headers=auth_header(token_a))
        assert res.status_code == 200
        members = res.json()
        assert len(members) == 1
        assert members[0]["user_id"] == emp_b.id

    def test_remove_member_by_owner(self, client: TestClient, seed_data: dict):
        token_a = seed_data["tokens"]["emp_a"]
        deal_a = seed_data["deals"]["deal_a"]
        emp_b = seed_data["users"]["emp_b"]

        client.post(
            f"/api/v1/deals/{deal_a.id}/members",
            headers=auth_header(token_a),
            json={"user_id": emp_b.id, "role_in_deal": "SUPPORT"},
        )

        res = client.delete(
            f"/api/v1/deals/{deal_a.id}/members/{emp_b.id}",
            headers=auth_header(token_a),
        )
        assert res.status_code == 204

        # Kiểm tra danh sách rỗng sau khi xóa
        get_res = client.get(f"/api/v1/deals/{deal_a.id}/members", headers=auth_header(token_a))
        assert len(get_res.json()) == 0

    def test_remove_member_self_leaving(self, client: TestClient, seed_data: dict):
        token_a = seed_data["tokens"]["emp_a"]
        token_b = seed_data["tokens"]["emp_b"]
        deal_a = seed_data["deals"]["deal_a"]
        emp_b = seed_data["users"]["emp_b"]

        # Owner add emp_b
        client.post(
            f"/api/v1/deals/{deal_a.id}/members",
            headers=auth_header(token_a),
            json={"user_id": emp_b.id, "role_in_deal": "SUPPORT"},
        )

        # emp_b tự rời khỏi deal
        res = client.delete(
            f"/api/v1/deals/{deal_a.id}/members/{emp_b.id}",
            headers=auth_header(token_b),
        )
        assert res.status_code == 204


class TestCollaboratorPermissions:
    """Kiểm thử phân quyền chi tiết cho thành viên phối hợp (SCRUM-207)."""

    def test_collaborator_can_view_deal_and_filter(self, client: TestClient, seed_data: dict):
        token_a = seed_data["tokens"]["emp_a"]
        token_beta = seed_data["tokens"]["emp_beta"]
        deal_a = seed_data["deals"]["deal_a"]
        emp_beta = seed_data["users"]["emp_beta"]

        # Trước khi được add: emp_beta không thể xem deal_a (403 Forbidden)
        res_before = client.get(f"/api/v1/deals/{deal_a.id}", headers=auth_header(token_beta))
        assert res_before.status_code == 403

        # Owner thêm emp_beta làm collaborator
        client.post(
            f"/api/v1/deals/{deal_a.id}/members",
            headers=auth_header(token_a),
            json={"user_id": emp_beta.id, "role_in_deal": "COLLABORATOR"},
        )

        # Sau khi được add: emp_beta xem chi tiết Deal thành công
        res_after = client.get(f"/api/v1/deals/{deal_a.id}", headers=auth_header(token_beta))
        assert res_after.status_code == 200
        assert res_after.json()["id"] == deal_a.id

        # emp_beta lấy danh sách deals của mình -> deal_a xuất hiện
        res_list = client.get("/api/v1/deals", headers=auth_header(token_beta))
        assert res_list.status_code == 200
        deal_ids = [d["id"] for d in res_list.json()]
        assert deal_a.id in deal_ids

    def test_collaborator_can_record_activity(self, client: TestClient, seed_data: dict):
        token_a = seed_data["tokens"]["emp_a"]
        token_beta = seed_data["tokens"]["emp_beta"]
        deal_a = seed_data["deals"]["deal_a"]
        emp_beta = seed_data["users"]["emp_beta"]

        # Add emp_beta
        client.post(
            f"/api/v1/deals/{deal_a.id}/members",
            headers=auth_header(token_a),
            json={"user_id": emp_beta.id, "role_in_deal": "COLLABORATOR"},
        )

        # emp_beta ghi nhận hoạt động cho deal
        res = client.post(
            f"/api/v1/deals/{deal_a.id}/activities",
            headers=auth_header(token_beta),
            json={
                "type": "call",
                "title": "Gọi tư vấn kỹ thuật sơ bộ",
                "description": "Trao đổi về kiến trúc hệ thống CRM và giải đáp thắc mắc",
            },
        )
        assert res.status_code == 201
        data = res.json()
        assert data["userId"] == emp_beta.id
        assert data["title"] == "Gọi tư vấn kỹ thuật sơ bộ"

        # Lấy danh sách hoạt động của deal
        res_acts = client.get(f"/api/v1/deals/{deal_a.id}/activities", headers=auth_header(token_beta))
        assert res_acts.status_code == 200
        assert len(res_acts.json()) >= 1

    def test_collaborator_cannot_change_owner(self, client: TestClient, seed_data: dict):
        token_a = seed_data["tokens"]["emp_a"]
        token_beta = seed_data["tokens"]["emp_beta"]
        deal_a = seed_data["deals"]["deal_a"]
        emp_beta = seed_data["users"]["emp_beta"]
        emp_b = seed_data["users"]["emp_b"]

        client.post(
            f"/api/v1/deals/{deal_a.id}/members",
            headers=auth_header(token_a),
            json={"user_id": emp_beta.id, "role_in_deal": "COLLABORATOR"},
        )

        # Collaborator cố tình sửa owner_id qua PATCH /deals/{id} -> 403 Forbidden
        res_patch = client.patch(
            f"/api/v1/deals/{deal_a.id}",
            headers=auth_header(token_beta),
            json={"owner_id": emp_b.id},
        )
        assert res_patch.status_code == 403
        assert "không được phép thay đổi người sở hữu" in res_patch.json()["detail"]

    def test_collaborator_cannot_transfer_owner(self, client: TestClient, seed_data: dict):
        token_a = seed_data["tokens"]["emp_a"]
        token_beta = seed_data["tokens"]["emp_beta"]
        deal_a = seed_data["deals"]["deal_a"]
        emp_beta = seed_data["users"]["emp_beta"]
        emp_b = seed_data["users"]["emp_b"]

        client.post(
            f"/api/v1/deals/{deal_a.id}/members",
            headers=auth_header(token_a),
            json={"user_id": emp_beta.id, "role_in_deal": "COLLABORATOR"},
        )

        # Collaborator cố gọi endpoint transfer-owner -> 403 Forbidden
        res_transfer = client.post(
            f"/api/v1/deals/{deal_a.id}/transfer-owner",
            headers=auth_header(token_beta),
            json={"new_owner_id": emp_b.id, "keep_old_owner_as_member": True},
        )
        assert res_transfer.status_code == 403

    def test_collaborator_cannot_delete_deal(self, client: TestClient, seed_data: dict):
        token_a = seed_data["tokens"]["emp_a"]
        token_beta = seed_data["tokens"]["emp_beta"]
        deal_a = seed_data["deals"]["deal_a"]
        emp_beta = seed_data["users"]["emp_beta"]

        client.post(
            f"/api/v1/deals/{deal_a.id}/members",
            headers=auth_header(token_a),
            json={"user_id": emp_beta.id, "role_in_deal": "COLLABORATOR"},
        )

        # Collaborator cố xóa Deal -> 403 Forbidden
        res_del = client.delete(f"/api/v1/deals/{deal_a.id}", headers=auth_header(token_beta))
        assert res_del.status_code == 403


class TestTransferOwnershipWithAuditLog:
    """Kiểm thử bàn giao cơ hội bán hàng và ghi nhật ký bắt buộc vào deal_histories (SCRUM-207)."""

    def test_transfer_ownership_success_with_history_and_keep_old_owner(
        self, client: TestClient, seed_data: dict, db_session: Session
    ):
        token_a = seed_data["tokens"]["emp_a"]
        deal_a = seed_data["deals"]["deal_a"]
        emp_a = seed_data["users"]["emp_a"]
        emp_b = seed_data["users"]["emp_b"]

        # 1. Bàn giao từ emp_a sang emp_b, giữ emp_a làm member
        res = client.post(
            f"/api/v1/deals/{deal_a.id}/transfer-owner",
            headers=auth_header(token_a),
            json={
                "new_owner_id": emp_b.id,
                "keep_old_owner_as_member": True,
                "reason": "Bàn giao cơ hội để phối hợp bán hàng liên ngành",
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["ownerId"] == emp_b.id

        # 2. Kiểm tra bản ghi trong bảng deal_histories
        histories = (
            db_session.query(DealHistory)
            .filter(DealHistory.deal_id == deal_a.id, DealHistory.field_name == "owner_id")
            .all()
        )
        assert len(histories) == 1
        history = histories[0]
        assert history.field_name == "owner_id"
        assert history.old_value == emp_a.full_name
        assert history.new_value == emp_b.full_name
        assert history.changed_by == emp_a.id

        # 3. Kiểm tra endpoint audit-history
        res_history = client.get(f"/api/v1/deals/{deal_a.id}/audit-history", headers=auth_header(token_a))
        assert res_history.status_code == 200
        hist_list = res_history.json()
        assert len(hist_list) >= 1
        assert hist_list[0]["field_name"] == "owner_id"

        # 4. Kiểm tra emp_a đã được chuyển thành DealMember
        members = (
            db_session.query(DealMember)
            .filter(DealMember.deal_id == deal_a.id, DealMember.user_id == emp_a.id)
            .all()
        )
        assert len(members) == 1
        assert members[0].role_in_deal == "COLLABORATOR"

    def test_transfer_ownership_removes_new_owner_from_members(
        self, client: TestClient, seed_data: dict, db_session: Session
    ):
        token_a = seed_data["tokens"]["emp_a"]
        deal_a = seed_data["deals"]["deal_a"]
        emp_b = seed_data["users"]["emp_b"]

        # Trước tiên thêm emp_b làm member
        client.post(
            f"/api/v1/deals/{deal_a.id}/members",
            headers=auth_header(token_a),
            json={"user_id": emp_b.id, "role_in_deal": "SUPPORT"},
        )

        # Chuyển quyền sở hữu cho emp_b
        res = client.post(
            f"/api/v1/deals/{deal_a.id}/transfer-owner",
            headers=auth_header(token_a),
            json={"new_owner_id": emp_b.id, "keep_old_owner_as_member": False},
        )
        assert res.status_code == 200

        # Kiểm tra emp_b KHÔNG còn trong deal_members
        b_as_member = (
            db_session.query(DealMember)
            .filter(DealMember.deal_id == deal_a.id, DealMember.user_id == emp_b.id)
            .first()
        )
        assert b_as_member is None

    def test_transfer_to_same_owner_fails(self, client: TestClient, seed_data: dict):
        token_a = seed_data["tokens"]["emp_a"]
        deal_a = seed_data["deals"]["deal_a"]
        emp_a = seed_data["users"]["emp_a"]

        res = client.post(
            f"/api/v1/deals/{deal_a.id}/transfer-owner",
            headers=auth_header(token_a),
            json={"new_owner_id": emp_a.id, "keep_old_owner_as_member": True},
        )
        assert res.status_code == 400
        assert "trùng với người sở hữu hiện tại" in res.json()["detail"]

    def test_unrelated_sales_rep_forbidden_access(self, client: TestClient, seed_data: dict):
        token_beta = seed_data["tokens"]["emp_beta"]
        deal_a = seed_data["deals"]["deal_a"]

        # emp_beta không phải owner, không phải member -> không thể xem chi tiết
        res = client.get(f"/api/v1/deals/{deal_a.id}", headers=auth_header(token_beta))
        assert res.status_code == 403

        # emp_beta không thể ghi hoạt động
        res_act = client.post(
            f"/api/v1/deals/{deal_a.id}/activities",
            headers=auth_header(token_beta),
            json={"type": "call", "title": "Gọi trộm"},
        )
        assert res_act.status_code == 403
