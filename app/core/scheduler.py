import asyncio
import logging
from typing import Optional
from app.database import SessionLocal
from app.services.task_reminder_service import TaskReminderService

logger = logging.getLogger("nexuscrm.scheduler")

_scheduler_task: Optional[asyncio.Task] = None
_is_running: bool = False


async def reminder_scheduler_loop(interval_seconds: int = 60):
    """
    Tiến trình Scheduled Worker chạy ngầm:
    - Định kỳ quét các công việc sắp đến hạn và quá hạn (mặc định mỗi 60 giây).
    - Tạo phiên CSDL độc lập, tự động dọn dẹp sau mỗi chu kỳ.
    - An toàn tuyệt đối: Bắt toàn bộ ngoại lệ để không bao giờ làm sập tiến trình nền.
    """
    global _is_running
    _is_running = True
    logger.info(f"[SCHEDULER] Khoi dong Scheduled Worker quet nhac viec (chu ky: {interval_seconds}s).")

    while _is_running:
        try:
            db = SessionLocal()
            try:
                TaskReminderService.scan_and_notify_tasks(db)
            finally:
                db.close()
        except asyncio.CancelledError:
            logger.info("[SCHEDULER] Scheduled Worker da nhan tin hieu dung (Graceful Shutdown).")
            break
        except Exception as exc:
            logger.error(f"[SCHEDULER ERROR] Ngoai le trong chu ky quet nhac viec: {exc}", exc_info=True)

        try:
            await asyncio.sleep(interval_seconds)
        except asyncio.CancelledError:
            break

    _is_running = False


def start_scheduler(interval_seconds: int = 60) -> Optional[asyncio.Task]:
    """Khởi động worker trong event loop của FastAPI."""
    global _scheduler_task
    if _scheduler_task is None or _scheduler_task.done():
        loop = asyncio.get_event_loop()
        _scheduler_task = loop.create_task(reminder_scheduler_loop(interval_seconds))
    return _scheduler_task


def stop_scheduler():
    """Dừng worker an toàn khi ứng dụng shutdown."""
    global _scheduler_task, _is_running
    _is_running = False
    if _scheduler_task and not _scheduler_task.done():
        _scheduler_task.cancel()
        logger.info("[SCHEDULER] Da gui tin hieu huy worker quet nhac viec.")

