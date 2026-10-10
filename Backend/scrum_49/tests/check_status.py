import urllib.request
import json
import time
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

print("--- BẮT ĐẦU MÔ PHỎNG NẠP LEAD MỚI ---")
# 1. Nạp batch 5 leads
req = urllib.request.Request("http://127.0.0.1:5000/simulate/batch", data=b"", method="POST")
urllib.request.urlopen(req)
print("Đã gửi yêu cầu nạp Batch 5 Leads vào hệ thống!")

# 2. Đợi luồng nền quét và phân bổ (chu kỳ 2 giây)
print("Đang đợi luồng chạy nền (Background Worker) quét và phân bổ...")
time.sleep(3)

# 3. Kiểm tra kết quả qua API
status_res = urllib.request.urlopen("http://127.0.0.1:5000/api/status")
data = json.loads(status_res.read().decode())
m = data["metrics"]
w = data["worker"]

print("\n--- KẾT QUẢ SAU KHI LUỒNG NỀN XỬ LÝ ---")
print(f"Tổng số Lead trong hệ thống: {m['total_leads']}")
print(f"Số Lead đã được phân bổ tự động: {m['assigned_count']}")
print(f"Số Lead trong hàng chờ phân tay: {m['manual_queue_count']}")
print(f"Số Lead còn đang chờ (Pending): {m['pending_count']}")
print(f"Tỷ lệ đạt chuẩn SLA 5 phút (300s): {m['sla_rate']} %")
print(f"Số lead đã được worker xử lý: {w['total_processed']}")
print(f"Trạng thái luồng nền: {'Đang chạy' if w['is_running'] else 'Dừng'}")
print(f"Lần quét gần nhất: {w['last_run_time']}")
