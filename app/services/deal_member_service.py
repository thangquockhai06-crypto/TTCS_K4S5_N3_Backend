import json
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.scope import DataScope, get_user_data_scope
from app.models.activity import Activity
from app.models.audit_log import AuditLog
from app.models.deal import Deal
from app.models.deal_history import DealHistory
from app.models.deal_member import DealMember
from app.models.user import User
from app.schemas.deal_member import (
    DealActivityCreateDTO,
    DealHistoryResponse,
    DealMemberCreate,
    DealMemberResponse,
    DealTransferOwnerRequest,
)
from app.services.deal_service import _get_team_member_ids


class DealMemberService:
    """Service xử lý cộng tác cơ hội (Deal Collaboration) và chuyển quyền sở hữu (SCRUM-207)."""

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def can_manage_deal(deal: Deal, user: User, db: Session) -> bool:
        """
        Kiểm tra người dùng có quyền quản trị Deal hay không:
        1. Chính người sở hữu Deal (owner_id).
        2. Giám đốc / Admin (DataScope.ALL hoặc role Giám đốc).
        3. Trưởng nhóm (TEAM_LEAD) quản lý nhóm của người sở hữu Deal.
        """
        if deal.owner_id == user.id:
            return True
        scope = get_user_data_scope(user)
        if scope == DataScope.ALL:
            return True
        role = (user.role or "").strip().lower().replace("_", " ")
        if role in {"director", "sales director", "admin", "super admin", "vp of sales", "giám đốc kinh doanh", "quản trị viên"}:
            return True
        if scope == DataScope.TEAM or role in {"team lead", "team leader", "sales leader", "sales manager", "manager", "lead", "revops lead", "trưởng nhóm", "trưởng phòng"}:
            lead_member_ids = _get_team_member_ids(db, user)
            if deal.owner_id in lead_member_ids:
                return True
        return False

    @staticmethod
    def can_view_deal(deal: Deal, user: User, db: Session) -> bool:
        """
        Kiểm tra người dùng có quyền xem Deal:
        - Quản lý deal (Owner, Team Lead, Director) HOẶC là thành viên tham gia (Collaborator).
        """
        if DealMemberService.can_manage_deal(deal, user, db):
            return True
        for m in deal.members:
            if m.user_id == user.id:
                return True
        return False

    def get_members(self, deal_id: str, current_user: User) -> List[DealMemberResponse]:
        """Lấy danh sách thành viên phối hợp của Deal."""
        deal = self.db.query(Deal).filter(Deal.id == deal_id).first()
        if not deal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy cơ hội bán hàng.",
            )
        if not self.can_view_deal(deal, current_user, self.db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền xem thông tin cơ hội này.",
            )

        members = (
            self.db.query(DealMember)
            .filter(DealMember.deal_id == deal_id)
            .order_by(DealMember.created_at.asc())
            .all()
        )
        return [
            DealMemberResponse(
                id=m.id,
                deal_id=m.deal_id,
                user_id=m.user_id,
                user_name=m.user.full_name if m.user else "N/A",
                user_email=m.user.email if m.user else "N/A",
                role_in_deal=m.role_in_deal,
                added_by_name=m.added_by_user.full_name if m.added_by_user else "Hệ thống",
                created_at=m.created_at,
            )
            for m in members
        ]

    def add_member(
        self, deal_id: str, dto: DealMemberCreate, current_user: User
    ) -> DealMemberResponse:
        """Thêm thành viên vào danh sách phối hợp theo dõi Deal."""
        deal = self.db.query(Deal).filter(Deal.id == deal_id).first()
        if not deal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy cơ hội bán hàng.",
            )

        # Quyền hạn: Chỉ Owner, Team Lead quản lý owner, hoặc Director
        if not self.can_manage_deal(deal, current_user, self.db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Chỉ người sở hữu cơ hội hoặc cấp quản lý mới có quyền thêm thành viên.",
            )

        # Không cho phép thêm chính người sở hữu
        if dto.user_id == deal.owner_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Không thể thêm chính người sở hữu làm thành viên phối hợp.",
            )

        # Kiểm tra tồn tại của user mục tiêu
        target_user = self.db.query(User).filter(User.id == dto.user_id).first()
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy nhân viên được chỉ định.",
            )

        # Ngăn chặn trùng lặp thành viên
        existing = (
            self.db.query(DealMember)
            .filter(DealMember.deal_id == deal_id, DealMember.user_id == dto.user_id)
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nhân viên này đã là thành viên phối hợp của cơ hội.",
            )

        new_member = DealMember(
            id=str(uuid.uuid4()),
            deal_id=deal.id,
            user_id=target_user.id,
            role_in_deal=dto.role_in_deal or "COLLABORATOR",
            added_by=current_user.id,
            created_at=datetime.utcnow(),
        )
        self.db.add(new_member)
        self.db.commit()
        self.db.refresh(new_member)

        return DealMemberResponse(
            id=new_member.id,
            deal_id=new_member.deal_id,
            user_id=new_member.user_id,
            user_name=target_user.full_name,
            user_email=target_user.email,
            role_in_deal=new_member.role_in_deal,
            added_by_name=current_user.full_name,
            created_at=new_member.created_at,
        )

    def remove_member(self, deal_id: str, user_id: str, current_user: User) -> None:
        """Xóa thành viên khỏi cơ hội (hoặc tự rời khỏi cơ hội)."""
        deal = self.db.query(Deal).filter(Deal.id == deal_id).first()
        if not deal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy cơ hội bán hàng.",
            )

        is_self_leaving = current_user.id == user_id
        is_manager = self.can_manage_deal(deal, current_user, self.db)
        if not (is_self_leaving or is_manager):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền xóa thành viên khỏi cơ hội này.",
            )

        member = (
            self.db.query(DealMember)
            .filter(DealMember.deal_id == deal_id, DealMember.user_id == user_id)
            .first()
        )
        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Thành viên không tồn tại trong cơ hội bán hàng này.",
            )

        self.db.delete(member)
        self.db.commit()

    def transfer_owner(
        self, deal_id: str, request: DealTransferOwnerRequest, current_user: User
    ) -> Deal:
        """Chuyển quyền sở hữu cơ hội và tự động ghi nhật ký vào deal_histories."""
        deal = self.db.query(Deal).filter(Deal.id == deal_id).first()
        if not deal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy cơ hội bán hàng.",
            )

        # Kiểm tra quyền: Chỉ Owner, Team Lead quản lý owner, hoặc Director
        if not self.can_manage_deal(deal, current_user, self.db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Chỉ người sở hữu cơ hội hoặc cấp quản lý mới có quyền chuyển quyền sở hữu.",
            )

        # Không cho phép chuyển cho chính người đang sở hữu
        if request.new_owner_id == deal.owner_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Người nhận mới không được trùng với người sở hữu hiện tại.",
            )

        new_owner = self.db.query(User).filter(User.id == request.new_owner_id).first()
        if not new_owner:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy người nhận bàn giao.",
            )

        old_owner = deal.owner or self.db.query(User).filter(User.id == deal.owner_id).first()
        old_owner_id = deal.owner_id
        old_owner_name = old_owner.full_name if old_owner else old_owner_id

        # 1. Cập nhật owner_id mới
        deal.owner_id = new_owner.id
        deal.updated_at = datetime.utcnow()

        # 2. Nếu người mới trước đó đang là thành viên -> Xóa khỏi deal_members
        self.db.query(DealMember).filter(
            DealMember.deal_id == deal.id,
            DealMember.user_id == new_owner.id,
        ).delete()

        # 3. Tùy chọn hạ cấp: Người sở hữu cũ trở thành thành viên tham gia
        if request.keep_old_owner_as_member:
            already_member = (
                self.db.query(DealMember)
                .filter(DealMember.deal_id == deal.id, DealMember.user_id == old_owner_id)
                .first()
            )
            if not already_member:
                self.db.add(
                    DealMember(
                        id=str(uuid.uuid4()),
                        deal_id=deal.id,
                        user_id=old_owner_id,
                        role_in_deal="COLLABORATOR",
                        added_by=current_user.id,
                        created_at=datetime.utcnow(),
                    )
                )

        # 4. Bắt buộc ghi nhật ký vào bảng deal_histories
        now = datetime.utcnow()
        history = DealHistory(
            id=str(uuid.uuid4()),
            deal_id=deal.id,
            field_name="owner_id",
            old_value=old_owner_name,
            new_value=new_owner.full_name,
            changed_by=current_user.id,
            changed_at=now,
        )
        self.db.add(history)

        # 5. Ghi nhật ký vào AuditLog hệ thống
        self.db.add(
            AuditLog(
                user_id=current_user.id,
                performed_by=current_user.id,
                user_name=current_user.full_name,
                user_email=current_user.email,
                action="DEAL_OWNERSHIP_TRANSFERRED",
                target_type="opportunity",
                target_id=deal.id,
                details=json.dumps(
                    {
                        "old_owner_id": old_owner_id,
                        "old_owner_name": old_owner_name,
                        "new_owner_id": new_owner.id,
                        "new_owner_name": new_owner.full_name,
                        "keep_old_owner_as_member": request.keep_old_owner_as_member,
                        "reason": request.reason,
                    },
                    ensure_ascii=False,
                ),
            )
        )

        self.db.commit()
        self.db.refresh(deal)
        return deal

    def create_deal_activity(
        self, deal_id: str, dto: DealActivityCreateDTO, current_user: User
    ) -> Activity:
        """
        Ghi nhận hoạt động tương tác liên quan đến Deal (SCRUM-207).
        Chấp thuận: Deal Owner, Collaborators (deal_members), Team Lead, Director.
        """
        deal = self.db.query(Deal).filter(Deal.id == deal_id).first()
        if not deal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy cơ hội bán hàng.",
            )

        if not self.can_view_deal(deal, current_user, self.db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền ghi hoạt động cho cơ hội bán hàng này.",
            )

        customer_id = dto.customerId or deal.customer_id
        new_activity = Activity(
            id=str(uuid.uuid4()),
            customer_id=customer_id,
            user_id=current_user.id,
            type=dto.type,
            title=dto.title,
            description=dto.description or "",
            created_at=datetime.utcnow(),
        )
        self.db.add(new_activity)
        self.db.commit()
        self.db.refresh(new_activity)
        return new_activity

    def get_deal_activities(self, deal_id: str, current_user: User) -> List[Activity]:
        """Lấy danh sách hoạt động liên quan đến Deal."""
        deal = self.db.query(Deal).filter(Deal.id == deal_id).first()
        if not deal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy cơ hội bán hàng.",
            )

        if not self.can_view_deal(deal, current_user, self.db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền xem thông tin cơ hội này.",
            )

        return (
            self.db.query(Activity)
            .filter(Activity.customer_id == deal.customer_id)
            .order_by(Activity.created_at.desc())
            .all()
        )

    def get_deal_history(self, deal_id: str, current_user: User) -> List[DealHistoryResponse]:
        """Lấy lịch sử thay đổi của cơ hội (SCRUM-207: DealHistory)."""
        deal = self.db.query(Deal).filter(Deal.id == deal_id).first()
        if not deal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy cơ hội bán hàng.",
            )

        if not self.can_view_deal(deal, current_user, self.db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền xem thông tin cơ hội này.",
            )

        histories = (
            self.db.query(DealHistory)
            .filter(DealHistory.deal_id == deal_id)
            .order_by(DealHistory.changed_at.desc())
            .all()
        )
        return [
            DealHistoryResponse(
                id=h.id,
                deal_id=h.deal_id,
                field_name=h.field_name,
                old_value=h.old_value,
                new_value=h.new_value,
                changed_by=h.changed_by,
                changed_by_name=h.user.full_name if h.user else h.changed_by,
                changed_at=h.changed_at,
            )
            for h in histories
        ]

    def delete_deal(self, deal_id: str, current_user: User) -> None:
        """
        Xóa cơ hội bán hàng.
        Tuyệt đối ngăn chặn thành viên phối hợp (Collaborator) xóa deal (HTTP 403 Forbidden).
        """
        deal = self.db.query(Deal).filter(Deal.id == deal_id).first()
        if not deal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy cơ hội bán hàng.",
            )

        if not self.can_manage_deal(deal, current_user, self.db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Thành viên phối hợp không được phép xóa cơ hội bán hàng.",
            )

        self.db.delete(deal)
        self.db.commit()
