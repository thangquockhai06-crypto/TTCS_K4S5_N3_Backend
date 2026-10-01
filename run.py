"""
Run file for NexusCRM Backend Server
Usage: python run.py
"""
import sys
import uvicorn
from app.config import settings

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(f"[*] Khoi dong {settings.PROJECT_NAME} tai http://localhost:{settings.PORT}")
    print(f"[*] Tai lieu Swagger API: http://localhost:{settings.PORT}/docs")
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=settings.PORT,
        reload=False,
    )
