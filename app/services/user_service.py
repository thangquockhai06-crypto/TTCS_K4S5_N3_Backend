"""
Tầng Service xử lý toàn bộ Business Logic Quản lý Tài khoản (User Management CRUD),
Phân quyền Vai trò & Nhóm (Role & Team), và Vô hiệu hóa kèm Chuyển giao dữ liệu (Handover).
Tuân thủ Clean Layered Architecture, PEP 8 và 100% Type Hints.
"""
import uuid
import secrets
import string
from typing import Optional, List, Tuple, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.user import User
from app.models.role import Role
from app.models.team import Team
from app.models.customer import Customer
from app.models.deal import Deal
from app.repositories.user_repository import UserRepository
from app.services.email_service import EmailService
from app.core.security import hash_password
from app.schemas.user import (
    UserCreateSchema,
    UserUpdateSchema,
    UserDeactivateSchema,
    RoleAssignSchema,
    TeamAssignSchema,
)

ADMIN_ROLES = {"super admin", "admin", "quản trị viên", "sales director"}
LEADER_ROLES = {"team leader", "sales leader", "trưởng nhóm", "revops lead"}


def generate_temporary_password(length: int = 12) -> str:
    """Sinh mật khẩu tạm thời ngẫu nhiên an toàn cao bằng thư viện secrets."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    pwd = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
        secrets.choice("!@#$%^&*"),
    ]
    pwd += [secrets.choice(alphabet) for _ in range(max(0, length - 4))]
    secrets.SystemRandom().shuffle(pwd)
    return "".join(pwd)


class UserService:
    """
    Tầng Service điều phối nghiệp vụ Quản lý người dùng.
    """

    @staticmethod
    def list_users(
        db: Session,
        search: Optional[str] = None,
        role: Optional[str] = None,
        team: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[User], int]:
        """Lấy danh sách người dùng với các tiêu chí tìm kiếm và lọc."""
        return UserRepository.get_all(
            db=db,
            search=search,
            role=role,
            team=team,
            status=status,
            skip=skip,
            limit=limit,
        )

    @staticmethod
    def get_user_by_id(db: Session, user_id: str) -> User:
        """Lấy thông tin người dùng theo ID, ném lỗi 404 nếu không tồn tại."""
        user = UserRepository.get_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Người dùng có ID '{user_id}' không tồn tại.",
            )
        return user

    @staticmethod
    def create_user(
        db: Session,
        payload: UserCreateSchema,
        current_user: Optional[User] = None,
    ) -> User:
        """
        Tạo tài khoản người dùng mới:
        - Kiểm tra tính duy nhất của email ở tầng ứng dụng và CSDL.
        - Tự động sinh mật khẩu tạm thời an toàn.
        - Băm mật khẩu (bcrypt) trước khi lưu, không bao giờ lưu plaintext.
        - Gửi thông tin kích hoạt và mật khẩu tạm thời qua EmailService.
        - Kiểm tra tính hợp lệ của vai trò và nhóm (Trưởng nhóm bắt buộc phải có nhóm).
        """
        # 0. Kiem tra quyen quan tri
        if current_user and current_user.role.strip().lower() not in ADMIN_ROLES:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền thực hiện thao tác quản trị này.",
            )

        # 1. Kiểm tra tính duy nhất của Email
        normalized_email: str = payload.email.strip().lower()
        existing_user = UserRepository.get_by_email(db, normalized_email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Địa chỉ email '{normalized_email}' đã được sử dụng. Vui lòng chọn email khác.",
            )

        # 2. Xác định vai trò (Role)
        role_name: str = payload.role.strip() if payload.role else "Account Executive"
        if payload.role_id:
            role_obj = UserRepository.get_role_by_id(db, payload.role_id)
            if not role_obj:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Vai trò có ID '{payload.role_id}' không tồn tại.",
                )
            role_name = role_obj.name
        else:
            role_obj = UserRepository.get_or_create_role(db, role_name)

        # 3. Quy tắc: Trưởng nhóm (Leader) bắt buộc phải có nhóm (Team)
        if role_name.strip().lower() in LEADER_ROLES:
            if not payload.team_id or not str(payload.team_id).strip():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Trưởng nhóm phải được gán vào ít nhất một nhóm kinh doanh.",
                )

        # 4. Xác định nhóm (Team) nếu có
        team_id: Optional[str] = payload.team_id.strip() if payload.team_id else None
        team_obj: Optional[Team] = None
        if team_id:
            team_obj = UserRepository.get_team_by_id(db, team_id)
            if not team_obj:
                team_obj = UserRepository.get_or_create_team(db, team_name=team_id, team_id=team_id)

        # 5. Tự động sinh mật khẩu tạm thời và băm mật khẩu
        temporary_password: str = generate_temporary_password(12)
        password_hash_str: str = hash_password(temporary_password)

        new_user = User(
            id=str(uuid.uuid4()),
            email=normalized_email,
            password_hash=password_hash_str,
            full_name=payload.full_name.strip(),
            role=role_name,
            team_id=team_id,
            title=payload.title or "Nhân viên kinh doanh",
            department=payload.department or "Phòng Kinh Doanh",
            status=payload.status or "active",
            avatar_url=f"https://api.dicebear.com/7.x/initials/svg?seed={payload.full_name}",
        )
        saved_user = UserRepository.create(db, new_user)

        # 6. Gán vai trò và nhóm vào bảng trung gian user_roles và user_teams
        if role_obj:
            UserRepository.assign_role_to_user(db, saved_user, role_obj)
        if team_obj:
            UserRepository.assign_team_to_user(db, saved_user, team_obj)

        # 7. Gửi email kích hoạt tài khoản bằng tiếng Việt
        EmailService.send_account_activation_email(
            email=saved_user.email,
            full_name=saved_user.full_name,
            temporary_password=temporary_password,
        )

        return saved_user

    @staticmethod
    def update_user(
        db: Session,
        user_id: str,
        payload: UserUpdateSchema,
        current_user: User,
    ) -> User:
        """
        Cập nhật thông tin người dùng với các quy tắc bảo mật:
        - Quản trị viên KHÔNG được tự hạ quyền / bỏ quyền Admin của chính mình.
        - Trưởng nhóm bắt buộc phải có nhóm kinh doanh.
        """
        target_user = UserService.get_user_by_id(db, user_id)

        # 1. BẢO VỆ ADMIN & KIỂM TRA QUYỀN
        is_self_update = (current_user.id == target_user.id)
        current_is_admin = target_user.role.strip().lower() in ADMIN_ROLES
        caller_is_admin = current_user.role.strip().lower() in ADMIN_ROLES

        if not is_self_update and not caller_is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền chỉnh sửa thông tin người dùng khác.",
            )

        if is_self_update and current_is_admin:
            if payload.role and payload.role.strip().lower() not in ADMIN_ROLES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Quản trị viên không thể tự hạ quyền của chính mình.",
                )
            if payload.status and payload.status.strip().lower() in ["inactive", "locked", "deactivated"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Quản trị viên không thể tự vô hiệu hóa tài khoản của chính mình.",
                )

        # 2. Xử lý cập nhật Role
        new_role_name = target_user.role
        if payload.role_id:
            role_obj = UserRepository.get_role_by_id(db, payload.role_id)
            if not role_obj:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Vai trò có ID '{payload.role_id}' không tồn tại.",
                )
            new_role_name = role_obj.name
            UserRepository.assign_role_to_user(db, target_user, role_obj)
        elif payload.role and payload.role.strip():
            new_role_name = payload.role.strip()
            role_obj = UserRepository.get_or_create_role(db, new_role_name)
            UserRepository.assign_role_to_user(db, target_user, role_obj)

        # 3. Xử lý cập nhật Team
        if payload.team_id is not None:
            if payload.team_id.strip():
                team_obj = UserRepository.get_team_by_id(db, payload.team_id.strip())
                if not team_obj:
                    team_obj = UserRepository.get_or_create_team(db, team_name=payload.team_id.strip(), team_id=payload.team_id.strip())
                UserRepository.assign_team_to_user(db, target_user, team_obj)
            else:
                target_user.team_id = None
                target_user.teams.clear()

        # 4. QUY TẮC: Trưởng nhóm phải có ít nhất một nhóm
        if new_role_name.strip().lower() in LEADER_ROLES:
            has_team = UserRepository.user_has_any_team(db, target_user)
            if not has_team:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Trưởng nhóm phải được gán vào ít nhất một nhóm kinh doanh.",
                )

        # 5. Cập nhật các trường cơ bản
        if payload.full_name is not None:
            target_user.full_name = payload.full_name.strip()
        if payload.title is not None:
            target_user.title = payload.title.strip()
        if payload.department is not None:
            target_user.department = payload.department.strip()
        if payload.status is not None:
            target_user.status = payload.status.strip().lower()

        return UserRepository.update(db, target_user)

    @staticmethod
    def assign_role_endpoint(
        db: Session,
        user_id: str,
        payload: RoleAssignSchema,
        current_user: User,
    ) -> User:
        """Gán vai trò cho người dùng với đầy đủ kiểm tra an ninh."""
        role_identifier = payload.role_id or payload.role_name
        if not role_identifier:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vui lòng cung cấp roleId hoặc roleName hợp lệ.",
            )
        update_payload = UserUpdateSchema(role_id=payload.role_id, role=payload.role_name)
        return UserService.update_user(db, user_id, update_payload, current_user)

    @staticmethod
    def assign_team_endpoint(
        db: Session,
        user_id: str,
        payload: TeamAssignSchema,
        current_user: User,
    ) -> User:
        """Gán nhóm kinh doanh cho người dùng."""
        team_identifier = payload.team_id or payload.team_name
        if not team_identifier:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vui lòng cung cấp teamId hoặc teamName hợp lệ.",
            )
        update_payload = UserUpdateSchema(team_id=team_identifier)
        return UserService.update_user(db, user_id, update_payload, current_user)

    @staticmethod
    def deactivate_user_and_handover(
        db: Session,
        target_user_id: str,
        payload: UserDeactivateSchema,
        current_user: User,
    ) -> Dict[str, Any]:
        """
        Vô hiệu hóa tài khoản và bàn giao toàn bộ dữ liệu (Khách hàng, Cơ hội, Báo giá)
        cho người kế thừa trong một giao dịch duy nhất (Atomic Transaction).
        """
        # 0. Kiểm tra quyền quản trị
        if current_user.role.strip().lower() not in ADMIN_ROLES:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền vô hiệu hóa tài khoản người dùng.",
            )

        # 1. Kiểm tra tài khoản mục tiêu
        target_user = UserService.get_user_by_id(db, target_user_id)

        # 2. Không cho phép tự vô hiệu hóa tài khoản của chính mình nếu là Admin
        if current_user.id == target_user.id and target_user.role.strip().lower() in ADMIN_ROLES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quản trị viên không thể tự vô hiệu hóa tài khoản của chính mình.",
            )

        # 3. Kiểm tra người kế thừa
        successor_id = payload.successor_user_id.strip()
        if target_user.id == successor_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Người kế thừa không thể là chính người dùng bị vô hiệu hóa.",
            )

        successor_user = UserRepository.get_by_id(db, successor_id)
        if not successor_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Người kế thừa có ID '{successor_id}' không tồn tại trên hệ thống.",
            )

        # 4. Người kế thừa bắt buộc phải đang hoạt động (active)
        if successor_user.status.strip().lower() != "active":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Người kế thừa ({successor_user.email}) hiện không ở trạng thái hoạt động (active).",
            )

        # 5. Thực thi bàn giao và khóa tài khoản giao dịch (Atomic)
        customers_transferred, deals_transferred = UserRepository.execute_deactivation_and_handover(
            db=db,
            target_user=target_user,
            successor_user=successor_user,
            reason=payload.reason,
            performed_by_id=current_user.id,
        )

        return {
            "ok": True,
            "message": "Đã vô hiệu hóa tài khoản và hoàn tất bàn giao dữ liệu thành công.",
            "targetUserId": target_user.id,
            "successorUserId": successor_user.id,
            "transferredCustomersCount": customers_transferred,
            "transferredDealsCount": deals_transferred,
            "userStatus": target_user.status,
        }

    @staticmethod
    def delete_user(db: Session, user_id: str, current_user: User) -> Dict[str, str]:
        """
        Xóa tài khoản người dùng:
        - Nếu người dùng sở hữu dữ liệu khách hàng hoặc cơ hội, sử dụng Soft-Delete (inactive).
        - Quản trị viên không thể tự xóa chính mình.
        """
        if current_user.role.strip().lower() not in ADMIN_ROLES:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền xóa tài khoản người dùng.",
            )

        target_user = UserService.get_user_by_id(db, user_id)

        if current_user.id == target_user.id and target_user.role.strip().lower() in ADMIN_ROLES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quản trị viên không thể tự xóa tài khoản của chính mình.",
            )

        # Kiểm tra xem người dùng có sở hữu dữ liệu hay không
        owned_customers = db.query(Customer).filter(Customer.assigned_user_id == target_user.id).count()
        owned_deals = db.query(Deal).filter(Deal.owner_id == target_user.id).count()

        if owned_customers > 0 or owned_deals > 0:
            # Bảo toàn dữ liệu lịch sử: Thực hiện Soft-Delete
            UserRepository.delete(db, target_user, soft_delete=True)
            return {"message": "Tài khoản có dữ liệu liên kết nên đã được chuyển sang trạng thái vô hiệu hóa (inactive)."}

        UserRepository.delete(db, target_user, soft_delete=False)
        return {"message": "Đã xóa tài khoản người dùng thành công."}
