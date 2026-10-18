import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from app.models.task import Task
from app.models.notification import Notification
from app.repositories.task_repository import TaskRepository
from app.repositories.reminder_setting_repository import ReminderSettingRepository
from app.repositories.notification_repository import NotificationRepository
from app.core.websocket_manager import notification_manager
from app.schemas.task import format_duration_vietnamese

logger = logging.getLogger("nexuscrm.task_reminder")


def trigger_websocket_broadcast(user_id: str, payload: Dict[str, Any]):
    """Gửi WebSocket message an toàn ngay cả khi đang chạy trong sync context."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(notification_manager.send_personal_message(user_id, payload))
        else:
            loop.run_until_complete(notification_manager.send_personal_message(user_id, payload))
    except Exception as e:
        logger.debug(f"[WEBSOCKET NOTICE] Không thể gửi WebSocket: {e}")


class TaskReminderService:

    @staticmethod
    def scan_and_notify_tasks(db: Session) -> Dict[str, Any]:
        """
        Tiến trình cốt lõi quét toàn bộ công việc chưa hoàn thành:
        1. Kiểm tra việc quá hạn (due_date < now):
           - Cập nhật trạng thái 'overdue'.
           - Gửi thông báo in-app & WebSocket nếu chưa gửi mốc 'overdue'.
        2. Kiểm tra việc sắp đến hạn (due_date >= now):
           - So khớp thời gian còn lại với các mốc cấu hình (ví dụ: 15 phút, 1 giờ, 1 ngày).
           - Gửi thông báo in-app & WebSocket nếu chạm mốc và chưa gửi ở mốc đó.
        - Cơ chế Idempotent: Sử dụng mảng `reminded_milestones` trên từng Task để
          ngăn ngừa tuyệt đối việc gửi thông báo trùng lặp.
        """
        tasks = TaskRepository.get_unfinished_tasks_for_scanning(db)
        now = datetime.utcnow()

        scanned_count = len(tasks)
        reminders_sent = 0
        overdue_marked = 0

        for task in tasks:
            if not task.due_date:
                continue

            milestones: List[str] = list(task.reminded_milestones or [])
            milestones_updated = False

            # -----------------------------------------------------------------
            # 1. KIỂM TRA VIỆC QUÁ HẠN (OVERDUE)
            # -----------------------------------------------------------------
            if task.due_date < now:
                # Cập nhật trạng thái thành overdue nếu chưa hoàn thành
                if task.status in ["pending", "in_progress"]:
                    task.status = "overdue"
                    task.updated_at = now

                # Kiểm tra xem mốc 'overdue' đã được thông báo chưa
                if "overdue" not in milestones:
                    milestones.append("overdue")
                    milestones_updated = True
                    overdue_marked += 1

                    if task.assignee_id:
                        overdue_duration = (now - task.due_date).total_seconds()
                        overdue_text = format_duration_vietnamese(overdue_duration)
                        due_str = task.due_date.strftime("%H:%M ngày %d/%m/%Y")

                        notif = Notification(
                            user_id=task.assignee_id,
                            task_id=task.id,
                            title=f"⚠️ Công việc quá hạn: {task.title}",
                            message=f"Công việc '{task.title}' đã quá hạn {overdue_text} (Hạn chót: {due_str}). Vui lòng xử lý ngay!",
                            type="task_overdue",
                            milestone="overdue",
                            metadata_json={
                                "taskId": task.id,
                                "taskTitle": task.title,
                                "dueDate": task.due_date.isoformat(),
                                "isOverdue": True,
                            },
                        )
                        NotificationRepository.create(db, notif)

                        # Đẩy real-time qua WebSocket
                        trigger_websocket_broadcast(task.assignee_id, {
                            "event": "TASK_OVERDUE",
                            "notificationId": notif.id,
                            "taskId": task.id,
                            "title": notif.title,
                            "message": notif.message,
                            "type": "task_overdue",
                            "createdAt": notif.created_at.isoformat(),
                        })

            # -----------------------------------------------------------------
            # 2. KIỂM TRA VIỆC SẮP ĐẾN HẠN (DUE SOON)
            # -----------------------------------------------------------------
            else:
                remaining_seconds = (task.due_date - now).total_seconds()
                remaining_minutes = remaining_seconds / 60.0

                # Lấy cấu hình các mốc nhắc nhở của user phụ trách
                setting = ReminderSettingRepository.get_effective_setting(db, task.assignee_id)
                configured_minutes = sorted(
                    list({int(m) for m in (setting.remind_before_minutes or [15, 60, 1440]) if m > 0})
                )

                # Tìm mốc nhỏ nhất thoả mãn remaining_minutes <= m (mốc phù hợp nhất hiện tại)
                active_milestone = None
                larger_milestones = []
                for m in configured_minutes:
                    if remaining_minutes <= m:
                        if active_milestone is None:
                            active_milestone = m
                        else:
                            larger_milestones.append(m)

                if active_milestone is not None:
                    tag = f"{active_milestone}m"

                    # Đánh dấu các mốc lớn hơn là đã qua thời điểm (tránh nhắc lại lùi mốc)
                    for lm in larger_milestones:
                        ltag = f"{lm}m"
                        if ltag not in milestones:
                            milestones.append(ltag)
                            milestones_updated = True

                    if tag not in milestones:
                        milestones.append(tag)
                        milestones_updated = True
                        reminders_sent += 1

                        if task.assignee_id:
                            time_left_text = format_duration_vietnamese(remaining_seconds)
                            due_str = task.due_date.strftime("%H:%M ngày %d/%m/%Y")

                            notif = Notification(
                                user_id=task.assignee_id,
                                task_id=task.id,
                                title=f"⏰ Nhắc việc sắp đến hạn: {task.title}",
                                message=f"Công việc '{task.title}' còn {time_left_text} nữa là đến hạn hoàn thành (Hạn chót: {due_str}).",
                                type="task_reminder",
                                milestone=tag,
                                metadata_json={
                                    "taskId": task.id,
                                    "taskTitle": task.title,
                                    "dueDate": task.due_date.isoformat(),
                                    "milestone": tag,
                                    "remainingMinutes": remaining_minutes,
                                },
                            )
                            NotificationRepository.create(db, notif)

                            # Đẩy real-time qua WebSocket
                            trigger_websocket_broadcast(task.assignee_id, {
                                "event": "TASK_REMINDER",
                                "notificationId": notif.id,
                                "taskId": task.id,
                                "title": notif.title,
                                "message": notif.message,
                                "type": "task_reminder",
                                "milestone": tag,
                                "createdAt": notif.created_at.isoformat(),
                            })


            if milestones_updated:
                task.reminded_milestones = milestones
                task.updated_at = now

        db.commit()

        result = {
            "scannedTasks": scanned_count,
            "remindersSent": reminders_sent,
            "overdueMarked": overdue_marked,
            "timestamp": now.isoformat(),
        }
        logger.info(f"[TASK REMINDER SCAN] {result}")
        return result
