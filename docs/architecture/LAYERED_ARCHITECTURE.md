# Tài Liệu Thiết Kế Kiến Trúc Phân Tầng (Layered Architecture)

```
[ HTTP Requests / Clients (React Frontend) ]
                    |
                    v
    [ API Routers (FastAPI / Pydantic V2) ]
                    |
                    v
    [ Services Layer (Core Business Logic) ]
                    |
                    v
    [ Repositories Layer (Data Access Object) ]
                    |
                    v
    [ Database Layer (SQLAlchemy ORM / SQLite / MySQL) ]
```

Mỗi tầng đều độc lập, tuân thủ nguyên tắc Dependency Inversion và Single Responsibility.
