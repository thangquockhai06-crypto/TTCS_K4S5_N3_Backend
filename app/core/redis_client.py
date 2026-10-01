"""
Redis Client Manager cho NexusCRM Enterprise Backend.
Hỗ trợ lưu token đặt lại mật khẩu với TTL 30 phút (SCRUM-71 / S1-03).
Tự động chuyển đổi sang In-Memory Cache an toàn nếu môi trường không có Redis Server.
"""
import time
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger("nexuscrm.redis")

# Hằng số chuẩn PEP 8 (UPPER_CASE_SNAKE)
TOKEN_EXPIRE_MINUTES: int = 30
TOKEN_EXPIRE_SECONDS: int = TOKEN_EXPIRE_MINUTES * 60  # 1800 giây


class RedisManager:
    """
    Quản lý lưu trữ tạm thời Redis / In-memory TTL Cache.
    """
    _in_memory_store: Dict[str, Dict[str, Any]] = {}
    _redis_client = None

    @classmethod
    def get_client(cls):
        if cls._redis_client is None:
            try:
                import redis
                cls._redis_client = redis.Redis(
                    host="localhost",
                    port=6379,
                    db=0,
                    decode_responses=True,
                    socket_timeout=1.0,
                )
                cls._redis_client.ping()
                logger.info("[REDIS] Kết nối Redis Server thành công.")
            except Exception:
                cls._redis_client = False
                logger.info("[REDIS NOTICE] Redis Server chưa sẵn sàng, sử dụng In-Memory Cache thay thế.")
        return cls._redis_client if cls._redis_client is not False else None

    @classmethod
    def set_reset_token(cls, token: str, email: str, ttl_seconds: int = TOKEN_EXPIRE_SECONDS) -> bool:
        """
        Lưu token vào Redis với TTL 30 phút (1800s).
        """
        client = cls.get_client()
        key = f"password_reset:{token}"
        if client:
            try:
                client.setex(key, ttl_seconds, email)
                return True
            except Exception as e:
                logger.warning(f"[REDIS ERROR] Lỗi setex Redis: {e}")

        # Fallback to In-Memory TTL store
        cls._in_memory_store[key] = {
            "email": email,
            "expires_at": time.time() + ttl_seconds,
        }
        return True

    @classmethod
    def get_reset_token(cls, token: str) -> Optional[str]:
        """
        Lấy email gắn liền với token nếu token hợp lệ và chưa hết hạn.
        """
        client = cls.get_client()
        key = f"password_reset:{token}"
        if client:
            try:
                email = client.get(key)
                if email:
                    return str(email)
            except Exception as e:
                logger.warning(f"[REDIS ERROR] Lỗi get Redis: {e}")

        # Fallback to In-Memory TTL store
        entry = cls._in_memory_store.get(key)
        if entry:
            if time.time() < entry["expires_at"]:
                return entry["email"]
            else:
                # Token đã hết hạn 30 phút
                del cls._in_memory_store[key]
        return None

    @classmethod
    def delete_reset_token(cls, token: str) -> bool:
        """
        Xóa token ngay lập tức sau khi dùng xong (Đảm bảo liên kết chỉ dùng được 1 lần).
        """
        client = cls.get_client()
        key = f"password_reset:{token}"
        if client:
            try:
                client.delete(key)
            except Exception as e:
                logger.warning(f"[REDIS ERROR] Lỗi delete Redis: {e}")

        if key in cls._in_memory_store:
            del cls._in_memory_store[key]
        return True


redis_manager = RedisManager()
