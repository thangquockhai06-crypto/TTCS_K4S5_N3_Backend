# Hướng Dẫn Triển Khai Hệ Thống Backend (Deployment Guide)

## 1. Yêu cầu môi trường
- Python 3.10+ (Khuyến nghị Python 3.12).
- Thư viện phụ thuộc: `pip install -r requirements.txt`.

## 2. Khởi chạy cục bộ
```bash
# Khoi tao CSDL va seed du lieu mau
python seed.py

# Khoi dong FastAPI server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
