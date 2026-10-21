from app.core.constants.notification_types import NotificationType


def test_notification_types_enum():
    assert NotificationType.TASK_REMINDER.value == "task_reminder"
    assert NotificationType.TASK_OVERDUE.value == "task_overdue"
    assert NotificationType.LEAD_ASSIGNED.value == "lead_assigned"
