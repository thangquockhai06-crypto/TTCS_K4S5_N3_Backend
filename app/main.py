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
from app.database import engine, Base, ensure_schema_compatibility, run_auto_migrations
from app.routers import (
    auth_router,
    user_import_router,
    catalog_items_router,
    customer_import_router,
    customers_router,
    customer_hierarchy_router,
    saved_filters_router,
    users_router,
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
    customer_care_router,
    web_forms_router,
    public_forms_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Tu dong tao cac bang trong CSDL neu chua ton tai
    try:
        Base.metadata.create_all(bind=engine)
        ensure_schema_compatibility()
        run_auto_migrations()
        print("[DATABASE] Da ket noi va dong bo cau truc bang thanh cong.")

        # Tu dong cap nhat cot moi vao cac bang da ton tai tu truoc (SCRUM-63 / SCRUM-89)
        run_auto_migrations()

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
        "và duy trì/thu hồi phiên đăng xuất (SCRUM-34)."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

Path(settings.AVATAR_STORAGE_DIR).mkdir(parents=True, exist_ok=True)
app.mount(settings.MEDIA_URL, StaticFiles(directory=settings.AVATAR_STORAGE_DIR), name="media")

# Cấu hình CORS (Cho phép Frontend React/Vite tại localhost:5173 truy cập)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Middleware CORS cho Public Web Forms (Cho phép submit từ mọi website bất kỳ - SCRUM-24)
@app.middleware("http")
async def public_cors_middleware(request: Request, call_next):
    is_public = request.url.path.startswith("/api/v1/public/") or request.url.path.startswith("/static/")
    if is_public and request.method == "OPTIONS":
        return Response(
            status_code=status.HTTP_204_NO_CONTENT,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With, Accept",
                "Access-Control-Max-Age": "86400",
            },
        )
    response = await call_next(request)
    if is_public:
        response.headers["Access-Control-Allow-Origin"] = "*"
    return response

# Mount các Router API
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(user_import_router, prefix=settings.API_V1_STR)
app.include_router(users_router, prefix=settings.API_V1_STR)
app.include_router(customer_import_router, prefix=settings.API_V1_STR)
app.include_router(customers_router, prefix=settings.API_V1_STR)
app.include_router(customer_hierarchy_router, prefix=settings.API_V1_STR)
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
app.include_router(catalog_items_router, prefix=settings.API_V1_STR)
app.include_router(win_loss_router, prefix=settings.API_V1_STR)
app.include_router(customer_care_router, prefix=settings.API_V1_STR)
app.include_router(web_forms_router, prefix=settings.API_V1_STR)
app.include_router(public_forms_router, prefix=settings.API_V1_STR)

# Phục vụ file script tải form nhúng trực tiếp
@app.get("/static/form-loader.js", tags=["Public Web-to-Lead Forms (SCRUM-24)"])
def serve_form_loader_js(request: Request):
    from app.routers.public_forms import get_form_loader_script
    return get_form_loader_script(request)


@app.get("/", summary="Health Check")
def root():
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "docsUrl": "/docs",
        "version": "1.0.0",
        "scrum_stories": ["SCRUM-32 (Login & 15m Lockout)", "SCRUM-34 (Session & Logout Revocation)"],
    }

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"message": "Đã xảy ra lỗi máy chủ nội bộ.", "details": str(exc) if settings.DEBUG else None},
    )
