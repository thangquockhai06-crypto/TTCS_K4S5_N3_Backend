"""In-memory rate limiter chống brute-force và spam cho các API nhạy cảm."""
import time
from collections import defaultdict
from fastapi import HTTPException, status

class SimpleRateLimiter:
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)

    def check(self, client_ip: str):
        now = time.time()
        window_start = now - self.window_seconds
        self.requests[client_ip] = [t for t in self.requests[client_ip] if t > window_start]
        
        if len(self.requests[client_ip]) >= self.max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests, please slow down."
            )
        self.requests[client_ip].append(now)

global_rate_limiter = SimpleRateLimiter(max_requests=120, window_seconds=60)
