from app.core.constants.task_constants import TaskStatus, TaskPriority, DEFAULT_REMINDER_MILESTONES


def test_task_constants_values():
    assert TaskStatus.PENDING == "pending"
    assert TaskStatus.COMPLETED == "completed"
    assert TaskStatus.OVERDUE == "overdue"
    assert TaskPriority.URGENT == "urgent"
    assert 15 in DEFAULT_REMINDER_MILESTONES
    assert 60 in DEFAULT_REMINDER_MILESTONES
