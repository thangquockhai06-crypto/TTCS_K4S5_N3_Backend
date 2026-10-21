"""Công cụ CLI sao lưu dữ liệu toàn hệ thống ra tệp JSON."""
import json
import os
import sys

def export_summary():
    summary = {
        "system": "NexusCRM Enterprise",
        "export_date": "2026-10-21",
        "version": "7.0.0",
        "tables": ["users", "customers", "contacts", "leads", "deals", "quotations", "contracts"]
    }
    os.makedirs("backup_data", exist_ok=True)
    with open("backup_data/system_export_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print("Exported system summary successfully.")

if __name__ == "__main__":
    export_summary()
