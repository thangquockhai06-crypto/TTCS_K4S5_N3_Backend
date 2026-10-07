import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import settings
from app.database import engine, Base, run_ep03_migrations
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
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Tu dong tao cac bang trong CSDL neu chua ton tai
    try:
        Base.metadata.create_all(bind=engine)
        run_ep03_migrations(engine)
        print("[DATABASE] Da ket noi va dong bo cau truc bang thanh cong (EP-03 san sang).")
        try:
            import seed
            seed.seed_database()
        except Exception as seed_err:
            print(f"[DATABASE SEED] Khong the tu dong nap du lieu: {seed_err}")
    except Exception as exc:
        print(f"[DATABASE WARNING] Khong the tu dong tao bang: {exc}")
        print("[DATABASE TIP] Hay chac chan MySQL Server dang chay hoac file CSDL co quyen ghi.")
    yield

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

# Cấu hình CORS (Cho phép Frontend React/Vite tại localhost:5173 truy cập)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

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

@app.get("/", summary="Health Check")
def root():
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "docsUrl": "/docs",
        "version": "1.0.0",
        "sprint": "Sprint 3 (EP-03 Customer Management)",
        "scrum_stories": [
            "SCRUM-32 (Login & 15m Lockout)",
            "SCRUM-34 (Session & Logout Revocation)",
            "S3-01 -> S3-09 (Full Customer Management)",
        ],
    }
