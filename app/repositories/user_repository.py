import uuid
from typing import Optional, List, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.user import User
from app.models.role import Role, user_roles
from app.models.team import Team, user_teams
from app.models.customer import Customer
from app.models.deal import Deal
from app.models.quotation import Quotation
from app.models.audit_log import AuditLog
from app.repositories.token_repository import TokenRepository


class UserRepository:
    """
    Tầng Repository xử lý truy vấn CSDL cho bảng User, Role, Team và Chuyển giao dữ liệu.
    Tuân thủ Clean Layered Architecture & 100% Type Hints.
    """

    @staticmethod
    def get_all(
        db: Session,
        search: Optional[str] = None,
        role: Optional[str] = None,
        team: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[User], int]:
        """
        Lấy danh sách người dùng với tìm kiếm, lọc theo vai trò, nhóm, trạng thái ở cấp độ CSDL.
        """
        query = db.query(User)

        # 1. Tìm kiếm theo họ tên hoặc email
        if search and search.strip():
            search_pattern = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    User.full_name.ilike(search_pattern),
                    User.email.ilike(search_pattern),
                )
            )

        # 2. Lọc theo vai trò (Role)
        if role and role.strip() and role.lower() != "all":
            query = query.filter(User.role.ilike(f"%{role.strip()}%"))

        # 3. Lọc theo nhóm (Team ID hoặc Name)
        if team and team.strip() and team.lower() != "all":
            query = query.filter(User.team_id == team.strip())

        # 4. Lọc theo trạng thái tài khoản
        if status and status.strip() and status.lower() != "all":
            query = query.filter(User.status == status.strip().lower())

        total = query.count()
        users = query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()
        return users, total

    @staticmethod
    def get_by_id(db: Session, user_id: str) -> Optional[User]:
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def get_by_email(db: Session, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email.strip().lower()).first()

    @staticmethod
    def create(db: Session, user: User) -> User:
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def update(db: Session, user: User) -> User:
        user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def delete(db: Session, user: User, soft_delete: bool = True) -> None:
        """
        Xóa người dùng.
        Mặc định sử dụng Soft-Delete (chuyển status='inactive') để không làm đứt gãy lịch sử dữ liệu.
        """
        if soft_delete:
            user.status = "inactive"
            db.commit()
            db.refresh(user)
        else:
            db.delete(user)
            db.commit()

    # --- Role & Team Repository Methods ---

    @staticmethod
    def get_role_by_id(db: Session, role_id: str) -> Optional[Role]:
        return db.query(Role).filter(Role.id == role_id).first()

    @staticmethod
    def get_role_by_name(db: Session, role_name: str) -> Optional[Role]:
        return db.query(Role).filter(Role.name.ilike(role_name.strip())).first()

    @staticmethod
    def get_or_create_role(db: Session, role_name: str, description: Optional[str] = None) -> Role:
        role = UserRepository.get_role_by_name(db, role_name)
        if not role:
            role = Role(
                id=str(uuid.uuid4()),
                name=role_name.strip(),
                description=description or f"Vai trò {role_name}",
            )
            db.add(role)
            db.commit()
            db.refresh(role)
        return role

    @staticmethod
    def get_team_by_id(db: Session, team_id: str) -> Optional[Team]:
        return db.query(Team).filter(Team.id == team_id).first()

    @staticmethod
    def get_team_by_name(db: Session, team_name: str) -> Optional[Team]:
        return db.query(Team).filter(Team.name.ilike(team_name.strip())).first()

    @staticmethod
    def get_or_create_team(db: Session, team_name: str, team_id: Optional[str] = None) -> Team:
        team = UserRepository.get_team_by_name(db, team_name)
        if not team:
            team = Team(
                id=team_id or str(uuid.uuid4()),
                name=team_name.strip(),
                description=f"Nhóm kinh doanh {team_name}",
            )
            db.add(team)
            db.commit()
            db.refresh(team)
        return team

    @staticmethod
    def assign_role_to_user(db: Session, user: User, role: Role) -> None:
        """Gán vai trò cho người dùng thông qua bảng trung gian user_roles."""
        if role not in user.roles:
            user.roles.append(role)
        user.role = role.name
        db.commit()
        db.refresh(user)

    @staticmethod
    def assign_team_to_user(db: Session, user: User, team: Team) -> None:
        """Gán nhóm cho người dùng thông qua bảng trung gian user_teams."""
        if team not in user.teams:
            user.teams.append(team)
        user.team_id = team.id
        db.commit()
        db.refresh(user)

    @staticmethod
    def user_has_any_team(db: Session, user: User) -> bool:
        """Kiểm tra người dùng có thuộc bất kỳ nhóm nào trong user_teams hoặc team_id hay không."""
        if user.teams and len(user.teams) > 0:
            return True
        if user.team_id and str(user.team_id).strip():
            return True
        return False

    # --- Transactional Handover & Deactivation ---

    @staticmethod
    def execute_deactivation_and_handover(
        db: Session,
        target_user: User,
        successor_user: User,
        reason: Optional[str] = None,
        performed_by_id: Optional[str] = None,
    ) -> Tuple[int, int]:
        """
        Thực hiện giao dịch chuyển giao dữ liệu và vô hiệu hóa tài khoản (Atomic Transaction).
        - Chuyển giao toàn bộ Khách hàng (Customer.assigned_user_id) sang người kế thừa.
        - Chuyển giao toàn bộ Cơ hội (Deal.owner_id) sang người kế thừa.
        - Chuyển giao toàn bộ Báo giá (Quotation.owner_id) sang người kế thừa.
        - Cập nhật trạng thái người dùng thành 'inactive'.
        - Hủy toàn bộ Refresh Token của người dùng bị vô hiệu hóa.
        - Ghi vết Audit Log.
        - Đảm bảo tính nguyên tử (Rollback toàn bộ nếu có lỗi).
        """
        try:
            # 1. Chuyển quyền Khách hàng
            transferred_customers: int = db.query(Customer).filter(
                Customer.assigned_user_id == target_user.id
            ).update(
                {Customer.assigned_user_id: successor_user.id},
                synchronize_session=False,
            )

            # 2. Chuyển quyền Deals
            transferred_deals: int = db.query(Deal).filter(
                Deal.owner_id == target_user.id
            ).update(
                {Deal.owner_id: successor_user.id},
                synchronize_session=False,
            )

            # 3. Chuyển quyền Quotations (nếu có)
            db.query(Quotation).filter(
                Quotation.owner_id == target_user.id
            ).update(
                {Quotation.owner_id: successor_user.id},
                synchronize_session=False,
            )

            # 4. Vô hiệu hóa tài khoản
            target_user.status = "inactive"

            # 5. Hủy phiên đăng nhập của người dùng
            TokenRepository.revoke_all_user_tokens(db, target_user.id)

            # 6. Ghi nhật ký Audit Log
            audit = AuditLog(
                id=str(uuid.uuid4()),
                user_id=target_user.id,
                action="USER_DEACTIVATED_DATA_HANDOVER",
                details=(
                    f"Vô hiệu hóa tài khoản {target_user.email}. "
                    f"Bàn giao {transferred_customers} khách hàng và {transferred_deals} cơ hội bán hàng "
                    f"cho {successor_user.email}. Lý do: {reason or 'Không có'}"
                ),
                performed_by=performed_by_id,
            )
            db.add(audit)

            db.commit()
            db.refresh(target_user)
            return transferred_customers, transferred_deals
        except Exception:
            db.rollback()
            raise

    # --- Brute-force & Login attempts ---

    @staticmethod
    def increment_failed_attempts(db: Session, user: User) -> int:
        user.failed_attempts += 1
        db.commit()
        db.refresh(user)
        return user.failed_attempts

    @staticmethod
    def lock_user(db: Session, user: User, lockout_until: datetime) -> None:
        user.lockout_until = lockout_until
        db.commit()
        db.refresh(user)

    @staticmethod
    def reset_failed_attempts(db: Session, user: User) -> None:
        user.failed_attempts = 0
        user.lockout_until = None
        db.commit()
        db.refresh(user)

    @staticmethod
    def count_all(db: Session) -> int:
        return db.query(User).count()
