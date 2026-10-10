"""Định nghĩa các Exception chuẩn hóa và Error Codes cho toàn hệ thống CRM."""
from fastapi import HTTPException, status

class NexusCRMException(HTTPException):
    def __init__(self, code: str, message: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(status_code=status_code, detail={"code": code, "message": message})

class EntityNotFoundException(NexusCRMException):
    def __init__(self, entity_name: str, entity_id: any):
        super().__init__(
            code=f"{entity_name.upper()}_NOT_FOUND",
            message=f"{entity_name} with ID {entity_id} does not exist.",
            status_code=status.HTTP_404_NOT_FOUND
        )

class PermissionDeniedException(NexusCRMException):
    def __init__(self, detail: str = "Access denied due to insufficient permissions."):
        super().__init__(
            code="PERMISSION_DENIED",
            message=detail,
            status_code=status.HTTP_403_FORBIDDEN
        )
