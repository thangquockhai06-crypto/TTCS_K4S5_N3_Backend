from typing import Optional, List
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.reminder_setting import ReminderSetting


DEFAULT_REMINDER_MINUTES = [15, 60, 1440]  # 15 phút, 1 giờ, 1 ngày


class ReminderSettingRepository:

    @staticmethod
    def get_by_user_id(db: Session, user_id: str) -> Optional[ReminderSetting]:
        return db.query(ReminderSetting).filter(ReminderSetting.user_id == user_id).first()

    @staticmethod
    def get_system_default(db: Session) -> Optional[ReminderSetting]:
        return db.query(ReminderSetting).filter(ReminderSetting.user_id.is_(None)).first()

    @staticmethod
    def get_effective_setting(db: Session, user_id: Optional[str]) -> ReminderSetting:
        """
        Lấy cấu hình hiệu lực:
        1. Ưu tiên cấu hình riêng của user.
        2. Nếu user chưa tạo -> lấy cấu hình hệ thống (user_id is None).
        3. Nếu chưa có trong DB -> tự động tạo cấu hình mặc định [15, 60, 1440].
        """
        if user_id:
            user_setting = ReminderSettingRepository.get_by_user_id(db, user_id)
            if user_setting:
                return user_setting

        sys_default = ReminderSettingRepository.get_system_default(db)
        if sys_default:
            return sys_default

        # Tạo cấu hình mặc định hệ thống nếu chưa có
        default_setting = ReminderSetting(
            user_id=None,
            remind_before_minutes=DEFAULT_REMINDER_MINUTES,
            notify_on_overdue=True,
            enable_in_app=True,
            enable_email=False,
        )
        db.add(default_setting)
        db.commit()
        db.refresh(default_setting)
        return default_setting

    @staticmethod
    def create_or_update_user_setting(
        db: Session,
        user_id: str,
        remind_before_minutes: List[int],
        notify_on_overdue: bool = True,
        enable_in_app: bool = True,
        enable_email: bool = False,
    ) -> ReminderSetting:
        setting = ReminderSettingRepository.get_by_user_id(db, user_id)
        if not setting:
            setting = ReminderSetting(
                user_id=user_id,
                remind_before_minutes=remind_before_minutes,
                notify_on_overdue=notify_on_overdue,
                enable_in_app=enable_in_app,
                enable_email=enable_email,
            )
            db.add(setting)
        else:
            setting.remind_before_minutes = remind_before_minutes
            setting.notify_on_overdue = notify_on_overdue
            setting.enable_in_app = enable_in_app
            setting.enable_email = enable_email
            setting.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(setting)
        return setting

