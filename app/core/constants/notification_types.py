from enum import Enum


class NotificationType(str, Enum):
    TASK_REMINDER = "task_reminder"
    TASK_OVERDUE = "task_overdue"
    TASK_ASSIGNED = "task_assigned"
    LEAD_ASSIGNED = "lead_assigned"
    QUOTE_PENDING = "quote_pending"
    QUOTE_ACCEPTED = "quote_accepted"
    QUOTE_REJECTED = "quote_rejected"
    CONTRACT_EXPIRING = "contract_expiring"
    DEAL_STALLED = "deal_stalled"
    SYSTEM_ALERT = "system_alert"


class NotificationPriority(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
