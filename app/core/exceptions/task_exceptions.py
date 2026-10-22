from typing import Optional


class TaskDomainException(Exception):
    def __init__(self, message: str, code: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.code = code


class TaskNotFoundException(TaskDomainException):
    pass


class TaskPermissionDeniedException(TaskDomainException):
    pass


class InvalidReminderSettingException(TaskDomainException):
    pass
