"""Quản lý các biến môi trường nâng cao LOG_LEVEL, TOKEN_EXPIRE_MINUTES, CORS."""
import os

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
