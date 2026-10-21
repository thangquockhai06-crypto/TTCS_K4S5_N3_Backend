import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.core.scheduler import start_scheduler, stop_scheduler
from app.database import (
    engine,
    Base,
    run_ep03_migrations,
    run_ep04_ep05_migrations,
    run_ep06_migrations,
    run_ep07_migrations,
    run_sprint4_migrations,
)
from app.routers import (
    auth_router,
    users_router,
    customers_router,
    contacts_router,
    support_tickets_router,
    saved_filters_router,
    deals_router,
    opportunities_router,
    activities_router,
    quotations_router,
    dashboard_router,
    audit_logs_router,
    products_router,
    categories_router,
    org_tree_router,
    custom_fields_router,
    pipelines_router,
    win_loss_router,
    user_import_router,
    lead_scoring_router,
    leads_router,
    campaigns_router,
    tasks_router,
    contracts_router,
    pdf_templates_router,
    notifications_router,
    automations_router,
    public_quotes_router,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Tu dong tao cac bang trong CSDL neu chua ton tai
    try:
        Base.metadata.create_all(bind=engine)
        run_ep03_migrations(engine)
        run_sprint4_migrations(engine)
        run_ep04_ep05_migrations(engine)
        run_ep06_migrations(engine)
        run_ep07_migrations(engine)
        print("[DATABASE] Da ket noi va dong bo cau truc bang thanh cong.")
        try:
            import seed
            seed.seed_database()
        except Exception as seed_err:
            print(f"[DATABASE SEED] Khong the tu dong nap du lieu: {seed_err}")
    except Exception as exc:
        print(f"[DATABASE WARNING] Khong the tu dong tao bang: {exc}")
        print("[DATABASE TIP] Hay chac chan MySQL Server dang chay hoac file CSDL co quyen ghi.")

    # Khoi dong Background Scheduler quet nhac viec va qua han (moi 60s)
    try:
        start_scheduler(interval_seconds=60)
    except Exception as sched_err:
        print(f"[SCHEDULER WARNING] Khong the khoi dong worker quet nhac viec: {sched_err}")

    yield

    # Dung Scheduler worker khi shutdown
    try:
        stop_scheduler()
    except Exception:
        pass


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description=(
        "Backend API cho hệ thống NexusCRM (TTCS_K4S5_N3). "
        "Triển khai xác thực JWT an toàn, bảo vệ Brute-force 15 phút (SCRUM-32), "
        "duy trì/thu hồi phiên đăng xuất (SCRUM-34), "
        "và Phân hệ Quản lý Khách hàng Doanh nghiệp Toàn diện (Sprint 3 EP-03: S3-01 -> S3-09)."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

Path(settings.AVATAR_STORAGE_DIR).mkdir(parents=True, exist_ok=True)
Path(settings.DEAL_ATTACHMENTS_DIR).mkdir(parents=True, exist_ok=True)
app.mount(settings.MEDIA_URL, StaticFiles(directory=settings.AVATAR_STORAGE_DIR), name="media")

# Tuyệt đối không public thư mục chứa tệp đính kèm qua Static URL (SCRUM-208)
@app.middleware("http")
async def deal_attachments_security_middleware(request: Request, call_next):
    if request.url.path.startswith(f"{settings.MEDIA_URL}/deals") or request.url.path.startswith("/media/deals"):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": "Không được phép truy cập tài liệu qua URL tĩnh. Vui lòng tải xuống qua API bảo mật."},
        )
    return await call_next(request)


# Cấu hình CORS (Cho phép Frontend React/Vite tại localhost:5173 truy cập)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[
        "*",
        "X-Total-Count",
        "x-total-count",
        "X-Total-Pages",
        "x-total-pages",
        "X-Current-Page",
        "x-current-page",
        "X-Page-Size",
        "x-page-size",
    ],
)

# Phục vụ file uploads tĩnh (ảnh đại diện, tài liệu đính kèm)
import os
_uploads_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
os.makedirs(_uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=_uploads_dir), name="uploads")

# Mount các Router API
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(users_router, prefix=settings.API_V1_STR)
app.include_router(customers_router, prefix=settings.API_V1_STR)
app.include_router(contacts_router, prefix=settings.API_V1_STR)
app.include_router(support_tickets_router, prefix=settings.API_V1_STR)
app.include_router(saved_filters_router, prefix=settings.API_V1_STR)
app.include_router(deals_router, prefix=settings.API_V1_STR)
app.include_router(opportunities_router, prefix=settings.API_V1_STR)
app.include_router(activities_router, prefix=settings.API_V1_STR)
app.include_router(quotations_router, prefix=settings.API_V1_STR)
app.include_router(dashboard_router, prefix=settings.API_V1_STR)
app.include_router(audit_logs_router, prefix=settings.API_V1_STR)
app.include_router(products_router, prefix=settings.API_V1_STR)
app.include_router(categories_router, prefix=settings.API_V1_STR)
app.include_router(org_tree_router, prefix=settings.API_V1_STR)
app.include_router(custom_fields_router, prefix=settings.API_V1_STR)
app.include_router(pipelines_router, prefix=settings.API_V1_STR)
app.include_router(win_loss_router, prefix=settings.API_V1_STR)
app.include_router(user_import_router, prefix=settings.API_V1_STR)
app.include_router(lead_scoring_router, prefix=settings.API_V1_STR)
app.include_router(leads_router, prefix=settings.API_V1_STR)
app.include_router(campaigns_router, prefix=settings.API_V1_STR)
app.include_router(tasks_router, prefix=settings.API_V1_STR)
app.include_router(contracts_router, prefix=settings.API_V1_STR)
app.include_router(pdf_templates_router, prefix=settings.API_V1_STR)
app.include_router(notifications_router, prefix=settings.API_V1_STR)
app.include_router(automations_router, prefix=settings.API_V1_STR)
app.include_router(public_quotes_router, prefix=settings.API_V1_STR)

@app.get("/", summary="Health Check")
def root():
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "docsUrl": "/docs",
        "version": "1.0.0",
        "sprint": "NexusCRM Enterprise Unified",
    }
