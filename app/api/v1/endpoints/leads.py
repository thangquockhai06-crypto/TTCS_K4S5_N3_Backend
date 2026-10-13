"""
Endpoint proxy to ensure compatibility with app.api.v1.endpoints.leads
"""
from app.routers.leads import router

__all__ = ["router"]
