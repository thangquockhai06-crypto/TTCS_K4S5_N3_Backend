from enum import Enum
from typing import List


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


DEFAULT_REMINDER_MILESTONES: List[int] = [15, 60, 1440]  # Phút: 15p, 1h, 1 ngày
MAX_REMINDER_MILESTONES_PER_USER: int = 10
MIN_REMINDER_OFFSET_MINUTES: int = 5
MAX_REMINDER_OFFSET_MINUTES: int = 43200  # 30 ngày
