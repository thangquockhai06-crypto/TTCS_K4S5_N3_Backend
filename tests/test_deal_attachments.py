import io
import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import settings
from app.models.deal import Deal
from app.models.deal_attachment import DealAttachment
from app.models.deal_history import DealHistory
from app.models.deal_member import DealMember


@pytest.fixture(autouse=True)
def deal_attachments_dir(monkeypatch, tmp_path):
    storage_dir = tmp_path / "uploads" / "deals"
    storage_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "DEAL_ATTACHMENTS_DIR", str(storage_dir))
    return storage_dir


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class TestDealAttachments:
    """Bộ kiểm thử tính năng Đính kèm và Quản lý Tài liệu trong Cơ hội bán hàng (SCRUM-208)."""

    def test_upload_single_valid_file_by_owner(
        self, client: TestClient, seed_data: dict, db_session: Session
    ):
        """Owner tải lên 1 tệp hợp lệ thành công và trả về đầy đủ metadata."""
        token_a = seed_data["tokens"]["emp_a"]
        deal_a = seed_data["deals"]["deal_a"]
        user_a = seed_data["users"]["emp_a"]

        file_content = b"%PDF-1.4 Mock proposal content for Deal A"
        files = [
            ("files", ("Ho_so_thau_v1.pdf", io.BytesIO(file_content), "application/pdf"))
        ]

        res = client.post(
            f"/api/v1/deals/{deal_a.id}/attachments",
            headers=auth_header(token_a),
            files=files,
        )

        assert res.status_code == 201
        data = res.json()
        assert isinstance(data, list)
        assert len(data) == 1

        att = data[0]
        assert att["deal_id"] == deal_a.id
        assert att["original_filename"] == "Ho_so_thau_v1.pdf"
        assert att["content_type"] == "application/pdf"
        assert att["file_size"] == len(file_content)
        assert "B" in att["file_size_formatted"] or "KB" in att["file_size_formatted"]
        assert att["uploaded_by"] == user_a.id
        assert att["uploader"] is not None
        assert att["uploader"]["id"] == user_a.id
        assert att["uploader"]["full_name"] == user_a.full_name
        assert att["uploader"]["email"] == user_a.email
        assert f"/api/v1/deals/{deal_a.id}/attachments/{att['id']}/download" in att["download_url"]

        # Kiểm tra bản ghi trong DB
        db_att = db_session.query(DealAttachment).filter(DealAttachment.id == att["id"]).first()
        assert db_att is not None
        assert db_att.original_filename == "Ho_so_thau_v1.pdf"

        # Kiểm tra ghi lịch sử DealHistory
        history = (
            db_session.query(DealHistory)
            .filter(DealHistory.deal_id == deal_a.id, DealHistory.field_name == "attachment")
            .first()
        )
        assert history is not None
        assert "Ho_so_thau_v1.pdf" in history.new_value

    def test_upload_multiple_valid_files(
        self, client: TestClient, seed_data: dict, db_session: Session
    ):
        """Tải lên đồng thời nhiều tệp hợp lệ trong 1 request multipart/form-data."""
        token_a = seed_data["tokens"]["emp_a"]
        deal_a = seed_data["deals"]["deal_a"]

        files = [
            ("files", ("Doc1.pdf", io.BytesIO(b"Content PDF 1"), "application/pdf")),
            ("files", ("Bao_gia.xlsx", io.BytesIO(b"Content Excel 2"), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")),
            ("files", ("Bien_ban.docx", io.BytesIO(b"Content Word 3"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")),
        ]

        res = client.post(
            f"/api/v1/deals/{deal_a.id}/attachments",
            headers=auth_header(token_a),
            files=files,
        )

        assert res.status_code == 201
        data = res.json()
        assert len(data) == 3
        filenames = [item["original_filename"] for item in data]
        assert "Doc1.pdf" in filenames
        assert "Bao_gia.xlsx" in filenames
        assert "Bien_ban.docx" in filenames

    def test_collaborator_can_upload_attachment(
        self, client: TestClient, seed_data: dict, db_session: Session
    ):
        """Thành viên phối hợp (Collaborator) có quyền upload tài liệu vào cơ hội."""
        token_b = seed_data["tokens"]["emp_b"]
        deal_a = seed_data["deals"]["deal_a"]
        user_b = seed_data["users"]["emp_b"]
        user_a = seed_data["users"]["emp_a"]

        # Thêm emp_b làm Collaborator của deal_a
        member = DealMember(
            deal_id=deal_a.id,
            user_id=user_b.id,
            role_in_deal="COLLABORATOR",
            added_by=user_a.id,
        )
        db_session.add(member)
        db_session.commit()

        file_content = b"Technical spec from collaborator"
        files = [
            ("files", ("Tech_Spec.pdf", io.BytesIO(file_content), "application/pdf"))
        ]

        res = client.post(
            f"/api/v1/deals/{deal_a.id}/attachments",
            headers=auth_header(token_b),
            files=files,
        )

        assert res.status_code == 201
        data = res.json()
        assert data[0]["uploaded_by"] == user_b.id
        assert data[0]["uploader"]["full_name"] == user_b.full_name

    def test_unauthorized_user_cannot_upload(
        self, client: TestClient, seed_data: dict
    ):
        """Người không sở hữu và không được chia sẻ cơ hội bị chặn 403 Forbidden khi upload."""
        token_beta = seed_data["tokens"]["emp_beta"]
        deal_a = seed_data["deals"]["deal_a"]

        files = [
            ("files", ("hacker_file.pdf", io.BytesIO(b"malicious content"), "application/pdf"))
        ]

        res = client.post(
            f"/api/v1/deals/{deal_a.id}/attachments",
            headers=auth_header(token_beta),
            files=files,
        )

        assert res.status_code == 403
        assert "không có quyền" in res.json()["detail"].lower()

    def test_upload_file_exceeds_20mb_rejected_and_cleaned(
        self, client: TestClient, seed_data: dict, deal_attachments_dir: Path
    ):
        """Tệp vượt quá 20MB bị từ chối 400 Bad Request và dọn dẹp sạch sẽ tệp trên đĩa."""
        token_a = seed_data["tokens"]["emp_a"]
        deal_a = seed_data["deals"]["deal_a"]

        # 20MB + 1024 bytes
        oversized_bytes = 20 * 1024 * 1024 + 1024
        # Tạo generator/fake stream để không tốn RAM
        class ChunkReader:
            def __init__(self, size):
                self.size = size
                self.read_so_far = 0

            def read(self, n=-1):
                if self.read_so_far >= self.size:
                    return b""
                chunk_len = min(n if n > 0 else 1024 * 1024, self.size - self.read_so_far)
                self.read_so_far += chunk_len
                return b"A" * chunk_len

        files = [
            ("files", ("Huge_Archive.zip", ChunkReader(oversized_bytes), "application/zip"))
        ]

        res = client.post(
            f"/api/v1/deals/{deal_a.id}/attachments",
            headers=auth_header(token_a),
            files=files,
        )

        assert res.status_code == 400
        detail = res.json()["detail"]
        assert "Huge_Archive.zip" in detail
        assert "20MB" in detail

        # Kiểm tra không lưu rác trên đĩa
        deal_folder = deal_attachments_dir / deal_a.id
        if deal_folder.exists():
            assert len(list(deal_folder.iterdir())) == 0

    def test_upload_empty_file_rejected(
        self, client: TestClient, seed_data: dict, deal_attachments_dir: Path
    ):
        """Tệp rỗng (0 byte) bị từ chối 400 Bad Request và dọn dẹp đĩa."""
        token_a = seed_data["tokens"]["emp_a"]
        deal_a = seed_data["deals"]["deal_a"]

        files = [
            ("files", ("Empty.pdf", io.BytesIO(b""), "application/pdf"))
        ]

        res = client.post(
            f"/api/v1/deals/{deal_a.id}/attachments",
            headers=auth_header(token_a),
            files=files,
        )

        assert res.status_code == 400
        assert "0 byte" in res.json()["detail"] or "rỗng" in res.json()["detail"]

        deal_folder = deal_attachments_dir / deal_a.id
        if deal_folder.exists():
            assert len(list(deal_folder.iterdir())) == 0

    def test_upload_multiple_one_invalid_rollbacks_all(
        self, client: TestClient, seed_data: dict, deal_attachments_dir: Path, db_session: Session
    ):
        """Nếu 1 trong các tệp tải lên bị lỗi (0 byte hoặc >20MB), toàn bộ tệp khác phải bị rollback."""
        token_a = seed_data["tokens"]["emp_a"]
        deal_a = seed_data["deals"]["deal_a"]

        files = [
            ("files", ("Valid_Part.pdf", io.BytesIO(b"Valid content 123"), "application/pdf")),
            ("files", ("Broken_Empty.docx", io.BytesIO(b""), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")),
        ]

        res = client.post(
            f"/api/v1/deals/{deal_a.id}/attachments",
            headers=auth_header(token_a),
            files=files,
        )

        assert res.status_code == 400

        # Kiểm tra không có tệp nào lưu trong DB
        db_items = db_session.query(DealAttachment).filter(DealAttachment.deal_id == deal_a.id).all()
        assert len(db_items) == 0

        # Kiểm tra không còn tệp nào trên đĩa
        deal_folder = deal_attachments_dir / deal_a.id
        if deal_folder.exists():
            assert len(list(deal_folder.iterdir())) == 0

    def test_get_attachments_list(
        self, client: TestClient, seed_data: dict
    ):
        """Lấy danh sách tệp đính kèm sắp xếp mới nhất trước và hiển thị tổng dung lượng."""
        token_a = seed_data["tokens"]["emp_a"]
        deal_a = seed_data["deals"]["deal_a"]

        # Tải 2 tệp
        files = [
            ("files", ("File_A.pdf", io.BytesIO(b"1234567890"), "application/pdf")),
            ("files", ("File_B.pdf", io.BytesIO(b"ABCDEFGH"), "application/pdf")),
        ]
        client.post(
            f"/api/v1/deals/{deal_a.id}/attachments",
            headers=auth_header(token_a),
            files=files,
        )

        res = client.get(
            f"/api/v1/deals/{deal_a.id}/attachments",
            headers=auth_header(token_a),
        )

        assert res.status_code == 200
        data = res.json()
        assert data["deal_id"] == deal_a.id
        assert data["total_files"] == 2
        assert data["total_size_bytes"] == 18
        assert len(data["items"]) == 2

    def test_download_attachment_security(
        self, client: TestClient, seed_data: dict, db_session: Session
    ):
        """Kiểm soát chặt chẽ quyền tải xuống (Owner, Collaborator, Manager OK; Outsider 403)."""
        token_a = seed_data["tokens"]["emp_a"]
        token_b = seed_data["tokens"]["emp_b"]
        token_lead = seed_data["tokens"]["team_leader"]
        token_director = seed_data["tokens"]["sales_director"]
        token_beta = seed_data["tokens"]["emp_beta"]

        deal_a = seed_data["deals"]["deal_a"]
        user_a = seed_data["users"]["emp_a"]
        user_b = seed_data["users"]["emp_b"]

        # 1. Upload 1 file
        content = b"Secured confidential deal quotation contract"
        upload_res = client.post(
            f"/api/v1/deals/{deal_a.id}/attachments",
            headers=auth_header(token_a),
            files=[("files", ("Contract_Final.pdf", io.BytesIO(content), "application/pdf"))],
        )
        att_id = upload_res.json()[0]["id"]

        # 2. Owner tải xuống -> 200 OK
        dl_owner = client.get(
            f"/api/v1/deals/{deal_a.id}/attachments/{att_id}/download",
            headers=auth_header(token_a),
        )
        assert dl_owner.status_code == 200
        assert dl_owner.content == content
        assert "Contract_Final.pdf" in dl_owner.headers.get("content-disposition", "")

        # 3. Outsider (emp_beta) tải xuống -> 403 Forbidden
        dl_outsider = client.get(
            f"/api/v1/deals/{deal_a.id}/attachments/{att_id}/download",
            headers=auth_header(token_beta),
        )
        assert dl_outsider.status_code == 403
        assert "không có quyền" in dl_outsider.json()["detail"].lower()

        # 4. Collaborator (emp_b) chưa được add -> 403
        dl_not_yet_member = client.get(
            f"/api/v1/deals/{deal_a.id}/attachments/{att_id}/download",
            headers=auth_header(token_b),
        )
        assert dl_not_yet_member.status_code == 403

        # 5. Thêm emp_b vào Collaborators -> Tải xuống thành công 200 OK
        db_session.add(
            DealMember(
                deal_id=deal_a.id,
                user_id=user_b.id,
                role_in_deal="COLLABORATOR",
                added_by=user_a.id,
            )
        )
        db_session.commit()

        dl_collab = client.get(
            f"/api/v1/deals/{deal_a.id}/attachments/{att_id}/download",
            headers=auth_header(token_b),
        )
        assert dl_collab.status_code == 200
        assert dl_collab.content == content

        # 6. Team Leader quản lý -> 200 OK
        dl_lead = client.get(
            f"/api/v1/deals/{deal_a.id}/attachments/{att_id}/download",
            headers=auth_header(token_lead),
        )
        assert dl_lead.status_code == 200

        # 7. Sales Director -> 200 OK
        dl_dir = client.get(
            f"/api/v1/deals/{deal_a.id}/attachments/{att_id}/download",
            headers=auth_header(token_director),
        )
        assert dl_dir.status_code == 200

    def test_delete_attachment_permissions_and_history(
        self, client: TestClient, seed_data: dict, db_session: Session, deal_attachments_dir: Path
    ):
        """Kiểm tra phân quyền xóa tài liệu và tự động ghi log vào DealHistory."""
        token_a = seed_data["tokens"]["emp_a"]
        token_b = seed_data["tokens"]["emp_b"]
        token_lead = seed_data["tokens"]["team_leader"]
        token_beta = seed_data["tokens"]["emp_beta"]

        deal_a = seed_data["deals"]["deal_a"]
        user_a = seed_data["users"]["emp_a"]
        user_b = seed_data["users"]["emp_b"]

        # Add emp_b làm Collaborator
        db_session.add(
            DealMember(
                deal_id=deal_a.id,
                user_id=user_b.id,
                role_in_deal="COLLABORATOR",
                added_by=user_a.id,
            )
        )
        db_session.commit()

        # 1. emp_b (Collaborator) tải lên 1 tệp
        up_res = client.post(
            f"/api/v1/deals/{deal_a.id}/attachments",
            headers=auth_header(token_b),
            files=[("files", ("Collab_Note.txt", io.BytesIO(b"Meeting note"), "text/plain"))],
        )
        att_id = up_res.json()[0]["id"]

        # 2. Người ngoài (emp_beta) không được phép xóa -> 403
        del_outsider = client.delete(
            f"/api/v1/deals/{deal_a.id}/attachments/{att_id}",
            headers=auth_header(token_beta),
        )
        assert del_outsider.status_code == 403

        # 3. Chính người upload (emp_b) xóa -> 200 OK
        del_uploader = client.delete(
            f"/api/v1/deals/{deal_a.id}/attachments/{att_id}",
            headers=auth_header(token_b),
        )
        assert del_uploader.status_code == 200

        # Kiểm tra đã bị xóa trong DB
        assert db_session.query(DealAttachment).filter(DealAttachment.id == att_id).first() is None

        # 4. emp_a (Owner) upload 1 tệp mới
        up_res2 = client.post(
            f"/api/v1/deals/{deal_a.id}/attachments",
            headers=auth_header(token_a),
            files=[("files", ("Owner_Doc.pdf", io.BytesIO(b"Owner file"), "application/pdf"))],
        )
        att_id_2 = up_res2.json()[0]["id"]

        # Collaborator emp_b (không phải người upload tệp này) thử xóa -> 403 Forbidden
        del_by_non_uploader_collab = client.delete(
            f"/api/v1/deals/{deal_a.id}/attachments/{att_id_2}",
            headers=auth_header(token_b),
        )
        assert del_by_non_uploader_collab.status_code == 403

        # Team Leader (Quản lý) xóa được -> 200 OK
        del_lead = client.delete(
            f"/api/v1/deals/{deal_a.id}/attachments/{att_id_2}",
            headers=auth_header(token_lead),
        )
        assert del_lead.status_code == 200

        # Kiểm tra DealHistory ghi nhận sự kiện xóa
        del_history = (
            db_session.query(DealHistory)
            .filter(DealHistory.deal_id == deal_a.id, DealHistory.field_name == "attachment")
            .order_by(DealHistory.changed_at.desc())
            .first()
        )
        assert del_history is not None
        assert "Xóa tệp" in (del_history.old_value or "")

    def test_static_url_access_strictly_forbidden(
        self, client: TestClient, seed_data: dict
    ):
        """Tuyệt đối không public thư mục chứa tệp đính kèm qua Static URL."""
        res = client.get("/media/deals/deal-123/malicious_file.pdf")
        assert res.status_code == 403
        assert "Không được phép" in res.json()["detail"]
