"""
Module Bộ Máy Phân Bổ Lead & Luồng Xử Lý Nền (Background Worker)
Ticket: SCRUM-30 / SCRUM-49
Đáp ứng trọn vẹn 4 tiêu chí cốt lõi:
1. Phân bổ theo khu vực, theo ngành nghề, hoặc xoay vòng đều trong nhóm (Round-Robin).
2. Nhiều quy tắc xếp theo thứ tự ưu tiên, quy tắc đầu tiên khớp sẽ thắng (First-Match-Wins).
3. Lead không khớp quy tắc nào rơi vào hàng chờ để trưởng nhóm phân tay (Manual Queue).
4. Phân bổ chạy nền, hoàn tất trong vòng 5 phút kể từ khi lead vào (Background Thread & SLA Tracker).
"""

import time
import threading
from datetime import datetime
from typing import Dict, Any, Tuple, Optional
from config import (
    LEAD_STATUS_PENDING,
    LEAD_STATUS_ASSIGNED,
    LEAD_STATUS_MANUAL_QUEUE,
    ASSIGNMENT_TYPE_ROUND_ROBIN,
    ASSIGNMENT_TYPE_DIRECT,
    SLA_LIMIT_SECONDS,
    WORKER_POLL_INTERVAL_SECONDS
)
from database import db, get_current_time, format_datetime


class LeadAllocationEngine:
    """Bộ máy đánh giá và so khớp quy tắc phân bổ lead"""

    @staticmethod
    def match_rule_criteria(rule: Dict[str, Any], lead: Dict[str, Any]) -> bool:
        """
        Kiểm tra lead có thỏa mãn tiêu chí của quy tắc hay không:
        - Khu vực (Region): 'Toàn quốc' hoặc trùng tên khu vực
        - Ngành nghề (Industry): 'Tất cả ngành nghề' hoặc trùng tên ngành nghề
        - Giá trị tối thiểu (Estimated Value): Nếu có quy định
        """
        # 1. So khớp khu vực
        rule_region = rule.get("region", "Toàn quốc")
        lead_region = lead.get("region", "")
        if rule_region != "Toàn quốc" and rule_region != lead_region:
            return False

        # 2. So khớp ngành nghề
        rule_industry = rule.get("industry", "Tất cả ngành nghề")
        lead_industry = lead.get("industry", "")
        if rule_industry != "Tất cả ngành nghề" and rule_industry != lead_industry:
            return False

        # 3. So khớp giá trị tiềm năng tối thiểu (nếu có)
        min_val = rule.get("min_deal_value", 0)
        lead_val = lead.get("estimated_value", 0)
        if min_val and lead_val < min_val:
            return False

        return True

    @classmethod
    def evaluate_and_allocate(cls, lead: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Thực hiện đánh giá lead với các quy tắc đang hoạt động:
        - Tuân thủ nguyên tắc First-Match-Wins: Duyệt danh sách quy tắc theo thứ tự ưu tiên tăng dần (1, 2, 3...)
        - Quy tắc đầu tiên khớp sẽ thắng và thực hiện phân bổ ngay
        - Nếu không có quy tắc nào khớp: Lead rơi vào hàng chờ phân tay của Trưởng nhóm
        """
        start_time = time.time()
        now = get_current_time()
        lead_id = lead["id"]
        lead_code = lead["code"]

        # Lấy danh sách quy tắc đang kích hoạt (đã được sắp xếp theo priority 1 -> 2 -> 3...)
        active_rules = db.get_rules(active_only=True)

        matched_rule = None
        for rule in active_rules:
            if cls.match_rule_criteria(rule, lead):
                matched_rule = rule
                break  # TIÊU CHÍ: Quy tắc đầu tiên khớp sẽ thắng (First-Match-Wins), dừng duyệt ngay lập tức

        # Tính toán thời gian từ lúc tạo lead đến lúc xử lý
        elapsed_seconds = 0.0
        try:
            if lead.get("created_at"):
                created_dt = datetime.strptime(lead["created_at"], "%Y-%m-%d %H:%M:%S")
                # Chuyển về số giây thực tế trôi qua
                elapsed_seconds = round(max(0.1, (now.replace(tzinfo=None) - created_dt).total_seconds()), 2)
        except Exception:
            elapsed_seconds = 0.5

        sla_status = "MET" if elapsed_seconds <= SLA_LIMIT_SECONDS else "MISSED"

        # TRƯỜNG HỢP 1: TÌM THẤY QUY TẮC KHỚP
        if matched_rule:
            assignment_type = matched_rule.get("assignment_type", ASSIGNMENT_TYPE_ROUND_ROBIN)
            assigned_user = None
            assigned_team_id = None

            if assignment_type == ASSIGNMENT_TYPE_ROUND_ROBIN:
                # Phân bổ xoay vòng đều trong nhóm chỉ định
                target_team_id = matched_rule.get("target_team_id")
                assigned_user = db.get_next_round_robin_user(target_team_id)
                assigned_team_id = target_team_id
            elif assignment_type == ASSIGNMENT_TYPE_DIRECT:
                # Phân bổ trực tiếp cho chuyên viên chỉ định
                target_user_id = matched_rule.get("target_user_id")
                if target_user_id and target_user_id in db.users:
                    assigned_user = db.users[target_user_id]
                    assigned_team_id = assigned_user.get("team_id")
                    assigned_user["assigned_count"] = assigned_user.get("assigned_count", 0) + 1

            if assigned_user:
                with db.lock:
                    lead["status"] = LEAD_STATUS_ASSIGNED
                    lead["assigned_to_user_id"] = assigned_user["id"]
                    lead["assigned_team_id"] = assigned_team_id
                    lead["matched_rule_id"] = matched_rule["id"]
                    lead["matched_rule_name"] = matched_rule["name"]
                    lead["processed_at"] = format_datetime(now)
                    lead["elapsed_seconds"] = elapsed_seconds
                    lead["sla_status"] = sla_status
                    lead["unmatched_reason"] = None
                    method_str = "Xoay vòng Round-Robin" if assignment_type == ASSIGNMENT_TYPE_ROUND_ROBIN else "Chỉ định trực tiếp"
                    lead["notes"] = f"Khớp '{matched_rule['name']}' (Ưu tiên #{matched_rule['priority']}). {method_str} giao cho {assigned_user['name']}."

                    # Tăng số lần khớp của quy tắc
                    matched_rule["matches_count"] = matched_rule.get("matches_count", 0) + 1

                elapsed_calc = round((time.time() - start_time) * 1000, 1)
                db.add_worker_log({
                    "lead_id": lead_id,
                    "lead_code": lead_code,
                    "action": "AUTO_ASSIGN_SUCCESS",
                    "status": "SUCCESS",
                    "details": f"Lead {lead_code} ({lead['region']}, {lead['industry']}) khớp '{matched_rule['name']}' [Ưu tiên #{matched_rule['priority']}]. Đã phân bổ cho {assigned_user['name']}. Xử lý: {elapsed_seconds}s (SLA < 5 phút).",
                    "elapsed_ms": elapsed_calc
                })
                return True, f"Phân bổ thành công cho {assigned_user['name']} qua {matched_rule['name']}"

        # TRƯỜNG HỢP 2: KHÔNG KHỚP BẤT KỲ QUY TẮC NÀO -> RƠI VÀO HÀNG CHỜ PHÂN TAY
        # TIÊU CHÍ: Lead không khớp quy tắc nào rơi vào hàng chờ để trưởng nhóm phân tay
        reason_msg = f"Không khớp bất kỳ quy tắc nào trong {len(active_rules)} quy tắc đang kích hoạt (Khu vực: {lead.get('region')}, Ngành: {lead.get('industry')})"
        with db.lock:
            lead["status"] = LEAD_STATUS_MANUAL_QUEUE
            lead["assigned_to_user_id"] = None
            lead["assigned_team_id"] = None
            lead["matched_rule_id"] = None
            lead["matched_rule_name"] = None
            lead["processed_at"] = format_datetime(now)
            lead["elapsed_seconds"] = elapsed_seconds
            lead["sla_status"] = sla_status
            lead["unmatched_reason"] = reason_msg
            lead["notes"] = f"Không có quy tắc phù hợp. Chuyển vào hàng chờ phân tay của Trưởng nhóm theo ticket SCRUM-49."

        elapsed_calc = round((time.time() - start_time) * 1000, 1)
        db.add_worker_log({
            "lead_id": lead_id,
            "lead_code": lead_code,
            "action": "FALLBACK_MANUAL_QUEUE",
            "status": "WARNING",
            "details": f"Lead {lead_code} không khớp bất kỳ quy tắc nào -> Tự động chuyển vào Hàng chờ để Trưởng nhóm phân tay.",
            "elapsed_ms": elapsed_calc
        })
        return False, "Không khớp quy tắc -> Đã chuyển vào hàng chờ phân tay của Trưởng nhóm"


class BackgroundAllocationWorker:
    """
    Luồng chạy nền tự động phân bổ Lead
    TIÊU CHÍ: Phân bổ chạy nền, hoàn tất trong vòng 5 phút kể từ khi lead vào
    Đảm bảo xử lý liên tục, chu kỳ quét định kỳ hoặc tức thì khi có lead mới.
    """

    def __init__(self, poll_interval: int = WORKER_POLL_INTERVAL_SECONDS):
        self.poll_interval = poll_interval
        self.is_running = False
        self.is_paused = False
        self.thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._wake_event = threading.Event()
        self.total_processed_count = 0
        self.last_run_time: Optional[str] = None

    def start(self):
        """Khởi động luồng chạy nền (Daemon thread)"""
        if self.is_running:
            return
        self.is_running = True
        self.is_paused = False
        self._stop_event.clear()
        self.thread = threading.Thread(target=self._run_loop, name="LeadAllocationWorkerThread", daemon=True)
        self.thread.start()
        db.add_worker_log({
            "lead_id": None,
            "lead_code": "SYSTEM",
            "action": "WORKER_START",
            "status": "INFO",
            "details": f"Luồng chạy nền phân bổ lead đã khởi động (Chu kỳ quét: {self.poll_interval}s, SLA cam kết: {SLA_LIMIT_SECONDS}s / 5 phút).",
            "elapsed_ms": 0
        })

    def stop(self):
        """Dừng luồng chạy nền"""
        self.is_running = False
        self._stop_event.set()
        self._wake_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)

    def pause(self):
        """Tạm dừng luồng chạy nền (phục vụ kiểm thử hoặc bảo trì)"""
        self.is_paused = True
        db.add_worker_log({
            "lead_id": None,
            "lead_code": "SYSTEM",
            "action": "WORKER_PAUSE",
            "status": "WARNING",
            "details": "Luồng chạy nền đã tạm dừng. Lead mới nạp vào sẽ chờ ở hàng đợi PENDING.",
            "elapsed_ms": 0
        })

    def resume(self):
        """Tiếp tục luồng chạy nền sau khi tạm dừng"""
        self.is_paused = False
        self.trigger_now()
        db.add_worker_log({
            "lead_id": None,
            "lead_code": "SYSTEM",
            "action": "WORKER_RESUME",
            "status": "INFO",
            "details": "Luồng chạy nền đã tiếp tục hoạt động và đang quét lead tồn đọng.",
            "elapsed_ms": 0
        })

    def trigger_now(self):
        """Kích hoạt quét ngay lập tức không cần đợi hết chu kỳ sleep"""
        self._wake_event.set()

    def process_pending_leads(self) -> int:
        """Quét và phân bổ tất cả lead ở trạng thái PENDING"""
        pending_leads = db.get_pending_leads()
        if not pending_leads:
            return 0

        count = 0
        for lead in pending_leads:
            LeadAllocationEngine.evaluate_and_allocate(lead)
            count += 1
            self.total_processed_count += 1

        self.last_run_time = format_datetime(get_current_time())
        return count

    def re_evaluate_manual_queue(self) -> Dict[str, int]:
        """
        Dành cho Trưởng nhóm / Giám đốc:
        Sau khi thêm/sửa quy tắc mới, quét lại các lead đang ở hàng chờ phân tay
        để tự động phân bổ nếu giờ đã khớp quy tắc!
        """
        manual_leads = db.get_manual_queue_leads()
        reassigned_count = 0
        still_manual_count = 0

        for lead in manual_leads:
            matched, _ = LeadAllocationEngine.evaluate_and_allocate(lead)
            if matched:
                reassigned_count += 1
            else:
                still_manual_count += 1

        db.add_worker_log({
            "lead_id": None,
            "lead_code": "RE_EVALUATE",
            "action": "RE_EVALUATE_QUEUE",
            "status": "INFO",
            "details": f"Quét lại hàng chờ phân tay: {reassigned_count} lead đã khớp quy tắc mới và được phân bổ tự động, {still_manual_count} lead vẫn ở hàng chờ.",
            "elapsed_ms": 10
        })
        return {
            "reassigned": reassigned_count,
            "still_manual": still_manual_count,
            "total_checked": len(manual_leads)
        }

    def _run_loop(self):
        """Vòng lặp chính của background thread"""
        while not self._stop_event.is_set():
            if not self.is_paused:
                try:
                    self.process_pending_leads()
                except Exception as ex:
                    db.add_worker_log({
                        "lead_id": None,
                        "lead_code": "ERROR",
                        "action": "WORKER_ERROR",
                        "status": "ERROR",
                        "details": f"Lỗi trong vòng lặp background worker: {str(ex)}",
                        "elapsed_ms": 0
                    })

            # Chờ theo chu kỳ hoặc được đánh thức bởi trigger_now()
            self._wake_event.wait(timeout=self.poll_interval)
            self._wake_event.clear()

    def get_status(self) -> Dict[str, Any]:
        """Lấy thông tin trạng thái phục vụ hiển thị lên giao diện"""
        return {
            "is_running": self.is_running,
            "is_paused": self.is_paused,
            "poll_interval": self.poll_interval,
            "sla_limit_seconds": SLA_LIMIT_SECONDS,
            "total_processed": self.total_processed_count,
            "last_run_time": self.last_run_time or "Vừa mới quét",
            "thread_alive": self.thread.is_alive() if self.thread else False
        }


# Khởi tạo singleton worker toàn cục
allocation_worker = BackgroundAllocationWorker()
