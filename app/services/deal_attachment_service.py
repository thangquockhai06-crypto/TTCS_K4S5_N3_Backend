import json
import os
import uuid
from datetime import datetime
from typing import List, Optional, Tuple

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.config import settings
from app.models.audit_log import AuditLog
from app.models.deal import Deal
from app.models.deal_attachment import DealAttachment
from app.models.deal_history import DealHistory
from app.models.user import User
from app.schemas.deal_attachment import (
    DealAttachmentListResponse,
    DealAttachmentResponse,
    UploaderInfoSchema,
    format_file_size,
)
from app.services.deal_member_service import DealMemberService

CHUNK_SIZE = 1024 * 1024  # 1MB chunk size


class DealAttachmentService:
    """Service xử lý đính kèm và quản lý tài liệu trong Cơ hội bán hàng (SCRUM-208)."""

    def __init__(self, db: Session):
        self.db = db

    def _to_dto(self, item: DealAttachment) -> DealAttachmentResponse:
        uploader_info = None
        if item.uploader:
            uploader_info = UploaderInfoSchema(
                id=item.uploader.id,
                full_name=item.uploader.full_name,
                email=item.uploader.email,
            )
        return DealAttachmentResponse(
            id=item.id,
            deal_id=item.deal_id,
            original_filename=item.original_filename,
            content_type=item.content_type,
            file_size=item.file_size,
            file_size_formatted=format_file_size(item.file_size),
            uploaded_by=item.uploaded_by,
            uploader=uploader_info,
            created_at=item.created_at,
            download_url=f"/api/v1/deals/{item.deal_id}/attachments/{item.id}/download",
        )

    async def upload_attachments(
        self, deal_id: str, files: List[UploadFile], current_user: User
    ) -> List[DealAttachmentResponse]:
        """
        Tải lên đồng thời một hoặc nhiều tệp tài liệu vào Cơ hội bán hàng.
        - Giới hạn tối đa 20MB/tệp.
        - Đọc theo chunk (1MB) tránh tràn bộ nhớ.
        - Nếu bất kỳ tệp nào vi phạm (>20MB hoặc 0 byte), hủy toàn bộ tệp tạm và raise HTTP 400.
        """
        deal = self.db.query(Deal).filter(Deal.id == deal_id).first()
        if not deal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy cơ hội bán hàng.",
            )

        if not DealMemberService.can_view_deal(deal, current_user, self.db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền truy cập hoặc tải lên tài liệu của thương vụ này.",
            )

        if not files:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Danh sách tệp tải lên không được rỗng.",
            )

        max_bytes = settings.MAX_DEAL_ATTACHMENT_BYTES
        deal_dir = os.path.join(settings.DEAL_ATTACHMENTS_DIR, deal_id)
        os.makedirs(deal_dir, exist_ok=True)

        created_disk_files: List[str] = []
        new_attachments: List[DealAttachment] = []

        try:
            for file in files:
                orig_filename = os.path.basename(file.filename or "attachment")
                file_ext = os.path.splitext(orig_filename)[1].lower()
                stored_filename = f"{uuid.uuid4().hex}{file_ext}"
                abs_path = os.path.join(deal_dir, stored_filename)
                rel_path = f"uploads/deals/{deal_id}/{stored_filename}"

                file_size = 0
                try:
                    with open(abs_path, "wb") as f_out:
                        while chunk := await file.read(CHUNK_SIZE):
                            file_size += len(chunk)
                            if file_size > max_bytes:
                                f_out.close()
                                if os.path.exists(abs_path):
                                    os.remove(abs_path)
                                self._cleanup_files(created_disk_files)
                                raise HTTPException(
                                    status_code=status.HTTP_400_BAD_REQUEST,
                                    detail=f"Tệp '{orig_filename}' vượt quá dung lượng tối đa 20MB.",
                                )
                            f_out.write(chunk)
                finally:
                    await file.close()

                if file_size == 0:
                    if os.path.exists(abs_path):
                        os.remove(abs_path)
                    self._cleanup_files(created_disk_files)
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Tệp '{orig_filename}' rỗng (0 byte).",
                    )

                created_disk_files.append(abs_path)

                attachment = DealAttachment(
                    id=str(uuid.uuid4()),
                    deal_id=deal.id,
                    original_filename=orig_filename,
                    stored_filename=stored_filename,
                    file_path=rel_path,
                    content_type=file.content_type,
                    file_size=file_size,
                    uploaded_by=current_user.id,
                    created_at=datetime.utcnow(),
                )
                new_attachments.append(attachment)

            now = datetime.utcnow()
            for att in new_attachments:
                self.db.add(att)
                # Ghi lịch sử hoạt động vào bảng deal_histories (SCRUM-91)
                self.db.add(
                    DealHistory(
                        id=str(uuid.uuid4()),
                        deal_id=deal.id,
                        field_name="attachment",
                        old_value=None,
                        new_value=f"Đính kèm tệp: {att.original_filename} ({format_file_size(att.file_size)})",
                        changed_by=current_user.id,
                        changed_at=now,
                    )
                )

            # Ghi nhật ký vào AuditLog
            self.db.add(
                AuditLog(
                    user_id=current_user.id,
                    performed_by=current_user.id,
                    user_name=current_user.full_name,
                    user_email=current_user.email,
                    action="DEAL_ATTACHMENTS_UPLOADED",
                    target_type="opportunity",
                    target_id=deal.id,
                    details=json.dumps(
                        {
                            "count": len(new_attachments),
                            "files": [a.original_filename for a in new_attachments],
                        },
                        ensure_ascii=False,
                    ),
                )
            )

            self.db.commit()
            for att in new_attachments:
                self.db.refresh(att)

            return [self._to_dto(att) for att in new_attachments]

        except HTTPException:
            self._cleanup_files(created_disk_files)
            raise
        except Exception as exc:
            self.db.rollback()
            self._cleanup_files(created_disk_files)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Lỗi hệ thống khi lưu tệp đính kèm: {str(exc)}",
            )

    def get_attachments(self, deal_id: str, current_user: User) -> DealAttachmentListResponse:
        """Lấy danh sách toàn bộ tài liệu đính kèm của cơ hội bán hàng."""
        deal = self.db.query(Deal).filter(Deal.id == deal_id).first()
        if not deal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy cơ hội bán hàng.",
            )

        if not DealMemberService.can_view_deal(deal, current_user, self.db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền truy cập hoặc xem tài liệu của thương vụ này.",
            )

        attachments = (
            self.db.query(DealAttachment)
            .filter(DealAttachment.deal_id == deal_id)
            .order_by(DealAttachment.created_at.desc())
            .all()
        )

        total_files = len(attachments)
        total_size_bytes = sum(a.file_size for a in attachments)

        return DealAttachmentListResponse(
            deal_id=deal_id,
            total_files=total_files,
            total_size_bytes=total_size_bytes,
            items=[self._to_dto(a) for a in attachments],
        )

    def download_attachment(
        self, deal_id: str, attachment_id: str, current_user: User
    ) -> Tuple[str, str, Optional[str]]:
        """
        Xác thực quyền tải xuống và trả về thông tin đường dẫn tệp vật lý.
        Quyền hạn: Chỉ Owner, Collaborators, Team Lead nhóm, Director/Admin.
        """
        attachment = (
            self.db.query(DealAttachment)
            .filter(DealAttachment.id == attachment_id, DealAttachment.deal_id == deal_id)
            .first()
        )
        if not attachment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy tài liệu đính kèm.",
            )

        deal = self.db.query(Deal).filter(Deal.id == deal_id).first()
        if not deal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy cơ hội bán hàng.",
            )

        if not DealMemberService.can_view_deal(deal, current_user, self.db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền truy cập hoặc tải xuống tài liệu của thương vụ này.",
            )

        abs_path = os.path.join(settings.DEAL_ATTACHMENTS_DIR, deal_id, attachment.stored_filename)
        if not os.path.exists(abs_path):
            server_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            candidate = os.path.join(server_dir, attachment.file_path)
            if os.path.exists(candidate):
                abs_path = candidate
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Tệp tài liệu vật lý không tồn tại trên hệ thống lưu trữ.",
                )

        return abs_path, attachment.original_filename, attachment.content_type

    def delete_attachment(self, deal_id: str, attachment_id: str, current_user: User) -> None:
        """
        Xóa tài liệu đính kèm khỏi cơ hội và đĩa cứng.
        Quyền hạn: Chỉ Owner, người tải lên (uploaded_by), Team Lead, Director/Admin.
        """
        attachment = (
            self.db.query(DealAttachment)
            .filter(DealAttachment.id == attachment_id, DealAttachment.deal_id == deal_id)
            .first()
        )
        if not attachment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy tài liệu đính kèm.",
            )

        deal = self.db.query(Deal).filter(Deal.id == deal_id).first()
        if not deal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy cơ hội bán hàng.",
            )

        is_owner_or_manager = DealMemberService.can_manage_deal(deal, current_user, self.db)
        is_uploader = attachment.uploaded_by == current_user.id
        if not (is_owner_or_manager or is_uploader):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền xóa tài liệu đính kèm này.",
            )

        abs_path = os.path.join(settings.DEAL_ATTACHMENTS_DIR, deal_id, attachment.stored_filename)
        if os.path.exists(abs_path):
            try:
                os.remove(abs_path)
            except Exception:
                pass

        now = datetime.utcnow()
        self.db.add(
            DealHistory(
                id=str(uuid.uuid4()),
                deal_id=deal.id,
                field_name="attachment",
                old_value=f"Xóa tệp: {attachment.original_filename}",
                new_value=None,
                changed_by=current_user.id,
                changed_at=now,
            )
        )
        self.db.add(
            AuditLog(
                user_id=current_user.id,
                performed_by=current_user.id,
                user_name=current_user.full_name,
                user_email=current_user.email,
                action="DEAL_ATTACHMENT_DELETED",
                target_type="opportunity",
                target_id=deal.id,
                details=json.dumps(
                    {
                        "attachment_id": attachment.id,
                        "filename": attachment.original_filename,
                    },
                    ensure_ascii=False,
                ),
            )
        )

        self.db.delete(attachment)
        self.db.commit()

    @staticmethod
    def _cleanup_files(file_paths: List[str]) -> None:
        """Dọn dẹp các tệp tạm trên đĩa khi xảy ra lỗi."""
        for path in file_paths:
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass
