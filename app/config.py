import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "NexusCRM Enterprise Backend API"
    API_V1_STR: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Database
    DATABASE_URL: str = "mysql+pymysql://root:password@localhost:3306/nexuscrm_db?charset=utf8mb4"

    # JWT
    JWT_SECRET_KEY: str = "nexuscrm-secret-key-change-in-production-2026-very-secure"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    REMEMBER_ME_EXPIRE_DAYS: int = 30

    # Avatar storage
    AVATAR_STORAGE_DIR: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
    MEDIA_URL: str = "/media"
    AVATAR_THUMBNAIL_SIZE: int = 128
    MAX_SAVED_CUSTOMER_FILTERS: int = 20

    # Brute-force protection (SCRUM-32 / SCRUM-101)
    MAX_FAILED_ATTEMPTS: int = 5
    LOCKOUT_DURATION_MINUTES: int = 15

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> List[str]:
        if not self.CORS_ORIGINS:
            return ["*"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

settings = Settings()
