"""
Bộ Giám Sát SLA Phản Hồi Chạy Nền (Background SLA Monitor)
User Story: SCRUM-30 / SCRUM-51
Đáp ứng Tiêu chí 3:
"Quá SLA phản hồi mà chưa liên hệ thì lead được gắn cờ và báo cho trưởng nhóm"
"""

import time
import threading
from datetime import datetime
from database import db, format_datetime


class BackgroundSLAMonitor:
    """
    Luồng chạy nền tự động quét định kỳ các Lead trong hệ thống.
    Nếu phát hiện lead nào đã hết hạn SLA phản hồi mà nhân viên chưa liên hệ:
    -> Tự động gắn cờ vi phạm (is_flagged = True)
    -> Tự động gửi thông báo khẩn cấp cho Trưởng nhóm
    """
    def __init__(self, check_interval_seconds=2):
        self.interval = check_interval_seconds
        self.thread = None
        self.is_running = False
        self.is_paused = False
        self.total_scans = 0
        self.last_scan_time = None
        self.lock = threading.Lock()

    def start(self):
        """Khởi động luồng nền daemon"""
        with self.lock:
            if self.is_running:
                return
            self.is_running = True
            self.is_paused = False
            self.thread = threading.Thread(target=self._run_loop, daemon=True, name="SLAMonitorWorker")
            self.thread.start()

    def pause(self):
        """Tạm dừng quét"""
        with self.lock:
            self.is_paused = True

    def resume(self):
        """Tiếp tục quét"""
        with self.lock:
            self.is_paused = False

    def scan_now(self):
        """Kích hoạt quét ngay lập tức"""
        with self.lock:
            self.total_scans += 1
            self.last_scan_time = datetime.now()
            flagged = db.check_and_flag_sla_breaches()
            return flagged

    def get_status(self):
        """Lấy trạng thái hiện tại của worker"""
        with self.lock:
            return {
                "is_running": self.is_running,
                "is_paused": self.is_paused,
                "interval_seconds": self.interval,
                "total_scans": self.total_scans,
                "last_scan_time": format_datetime(self.last_scan_time) if self.last_scan_time else "Chưa quét"
            }

    def _run_loop(self):
        """Vòng lặp quét liên tục mỗi interval giây"""
        while self.is_running:
            if not self.is_paused:
                try:
                    with self.lock:
                        self.total_scans += 1
                        self.last_scan_time = datetime.now()
                    # Quét và gắn cờ các vi phạm
                    db.check_and_flag_sla_breaches()
                except Exception as e:
                    print(f"[SLA Monitor Worker Error] {e}")
            time.sleep(self.interval)


# Singleton SLA Monitor
sla_monitor = BackgroundSLAMonitor(check_interval_seconds=2)
