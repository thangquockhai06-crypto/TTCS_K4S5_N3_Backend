"""API endpoint cung cấp phiên bản hệ thống, thông tin Sprint và môi trường chạy."""
from fastapi import APIRouter

router = APIRouter(prefix="/system", tags=["System Info"])

@router.get("/info")
def get_system_info():
    return {
        "app_name": "NexusCRM Enterprise",
        "version": "7.0.0",
        "active_sprints": ["Sprint 1", "Sprint 2", "Sprint 3", "Sprint 4", "Sprint 5", "Sprint 6", "Sprint 7"],
        "modules": [
            "User Management & RBAC",
            "Customer 360 & Hierarchy",
            "Lead Management & Web Forms",
            "Deal Pipeline & Kanban",
            "Task & Activity Timeline",
            "Quotation Builder & PDF Export",
            "Contract Management & Lifecycle",
            "Sales Automation Engine",
            "In-App Notification Hub"
        ],
        "status": "production-ready"
    }
