from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field, ConfigDict


def format_duration_vietnamese(seconds: float) -> str:
    """Format khoảng thời gian thành chuỗi tiếng Việt thân thiện."""
    if seconds < 0:
        return "Vừa xong"
    minutes = int(seconds // 60)
    hours = int(minutes // 60)
    days = int(hours // 24)

    if days > 0:
        remain_hours = hours % 24
        if remain_hours > 0:
            return f"{days} ngày {remain_hours} giờ"
        return f"{days} ngày"
    if hours > 0:
        remain_minutes = minutes % 60
        if remain_minutes > 0:
            return f"{hours} giờ {remain_minutes} phút"
        return f"{hours} giờ"
    if minutes > 0:
        return f"{minutes} phút"
    return "Dưới 1 phút"


class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="Tiêu đề công việc")
    description: Optional[str] = Field("", description="Mô tả chi tiết công việc")
    priority: str = Field("medium", description="Mức ưu tiên: low, medium, high, urgent")
    status: Optional[str] = Field("pending", description="Trạng thái: pending, in_progress, completed, cancelled, overdue")
    isCompleted: Optional[bool] = Field(False, description="Đã hoàn thành hay chưa")
    dueDate: Optional[Any] = Field(None, alias="due_date", description="Hạn xử lý")
    assigneeId: Optional[str] = Field(None, alias="assignee_id", description="Người được giao việc")
    customerId: Optional[str] = Field(None, alias="customer_id", description="Khách hàng liên quan")
    dealId: Optional[str] = Field(None, alias="deal_id", description="Cơ hội bán hàng liên quan")

    model_config = ConfigDict(populate_by_name=True)


class CreateTaskDTO(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="Tiêu đề công việc")
    description: Optional[str] = Field(None, description="Mô tả chi tiết công việc")
    due_date: Optional[datetime] = Field(None, alias="dueDate", description="Hạn chót hoàn thành")
    priority: Optional[str] = Field("medium", description="Mức độ ưu tiên: low, medium, high, urgent")
    assignee_id: Optional[str] = Field(None, alias="assigneeId", description="Mã nhân viên phụ trách")
    customer_id: Optional[str] = Field(None, alias="customerId", description="Mã khách hàng liên quan")
    deal_id: Optional[str] = Field(None, alias="dealId", description="Mã cơ hội liên quan")

    model_config = ConfigDict(populate_by_name=True)


class UpdateTaskDTO(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    due_date: Optional[datetime] = Field(None, alias="dueDate")
    status: Optional[str] = Field(None, description="pending, in_progress, completed, overdue, cancelled")
    priority: Optional[str] = None
    assignee_id: Optional[str] = Field(None, alias="assigneeId")
    customer_id: Optional[str] = Field(None, alias="customerId")
    deal_id: Optional[str] = Field(None, alias="dealId")
    isCompleted: Optional[bool] = None

    model_config = ConfigDict(populate_by_name=True)


class TaskDTO(BaseModel):
    id: str
    title: str
    description: Optional[str] = ""
    due_date: Optional[datetime] = Field(None, alias="dueDate")
    status: str
    priority: str
    isCompleted: Optional[bool] = False
    assignee_id: Optional[str] = Field(None, alias="assigneeId")
    assignee_name: Optional[str] = Field(None, alias="assigneeName")
    creator_id: Optional[str] = Field(None, alias="creatorId")
    creator_name: Optional[str] = Field(None, alias="creatorName")
    customer_id: Optional[str] = Field(None, alias="customerId")
    customer_name: Optional[str] = Field(None, alias="customerName")
    deal_id: Optional[str] = Field(None, alias="dealId")
    deal_title: Optional[str] = Field(None, alias="dealTitle")
    reminded_milestones: Optional[List[str]] = Field(default_factory=list, alias="remindedMilestones")
    completed_at: Optional[datetime] = Field(None, alias="completedAt")
    created_at: Optional[datetime] = Field(None, alias="createdAt")
    updated_at: Optional[datetime] = Field(None, alias="updatedAt")

    # Các trường mở rộng phục vụ Dashboard & Nhắc việc
    is_overdue: bool = Field(False, alias="isOverdue")
    overdue_seconds: Optional[float] = Field(None, alias="overdueSeconds")
    overdue_display: Optional[str] = Field(None, alias="overdueDisplay")
    is_due_soon: bool = Field(False, alias="isDueSoon")
    time_remaining_seconds: Optional[float] = Field(None, alias="timeRemainingSeconds")
    time_remaining_display: Optional[str] = Field(None, alias="timeRemainingDisplay")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ReminderSettingDTO(BaseModel):
    id: str
    user_id: Optional[str] = Field(None, alias="userId")
    remind_before_minutes: List[int] = Field(default_factory=lambda: [15, 60, 1440], alias="remindBeforeMinutes")
    notify_on_overdue: bool = Field(True, alias="notifyOnOverdue")
    enable_in_app: bool = Field(True, alias="enableInApp")
    enable_email: bool = Field(False, alias="enableEmail")
    created_at: Optional[datetime] = Field(None, alias="createdAt")
    updated_at: Optional[datetime] = Field(None, alias="updatedAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class UpdateReminderSettingDTO(BaseModel):
    remind_before_minutes: List[int] = Field(..., min_length=1, alias="remindBeforeMinutes", description="Mốc phút nhắc nhở, vd: [15, 60, 1440]")
    notify_on_overdue: Optional[bool] = Field(True, alias="notifyOnOverdue")
    enable_in_app: Optional[bool] = Field(True, alias="enableInApp")
    enable_email: Optional[bool] = Field(False, alias="enableEmail")

    model_config = ConfigDict(populate_by_name=True)


class NotificationDTO(BaseModel):
    id: str
    user_id: str = Field(..., alias="userId")
    task_id: Optional[str] = Field(None, alias="taskId")
    title: str
    message: str
    type: str
    is_read: bool = Field(False, alias="isRead")
    read_at: Optional[datetime] = Field(None, alias="readAt")
    milestone: Optional[str] = None
    created_at: Optional[datetime] = Field(None, alias="createdAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class PersonalTaskStatsDTO(BaseModel):
    total_tasks: int = Field(0, alias="totalTasks")
    pending_tasks: int = Field(0, alias="pendingTasks")
    in_progress_tasks: int = Field(0, alias="inProgressTasks")
    completed_tasks: int = Field(0, alias="completedTasks")
    overdue_tasks_count: int = Field(0, alias="overdueTasksCount")
    due_soon_tasks_count: int = Field(0, alias="dueSoonTasksCount")
    completion_rate: str = Field("0%", alias="completionRate")

    model_config = ConfigDict(populate_by_name=True)


class PersonalDashboardDTO(BaseModel):
    stats: PersonalTaskStatsDTO
    overdue_tasks: List[TaskDTO] = Field(default_factory=list, alias="overdueTasks")
    due_soon_tasks: List[TaskDTO] = Field(default_factory=list, alias="dueSoonTasks")
    today_tasks: List[TaskDTO] = Field(default_factory=list, alias="todayTasks")

    model_config = ConfigDict(populate_by_name=True)


class TeamMemberTaskStatsDTO(BaseModel):
    user_id: str = Field(..., alias="userId")
    full_name: str = Field(..., alias="fullName")
    email: str
    role: str
    avatar_url: Optional[str] = Field(None, alias="avatarUrl")
    total_tasks: int = Field(0, alias="totalTasks")
    completed_tasks: int = Field(0, alias="completedTasks")
    pending_tasks: int = Field(0, alias="pendingTasks")
    overdue_tasks_count: int = Field(0, alias="overdueTasksCount")
    due_soon_tasks_count: int = Field(0, alias="dueSoonTasksCount")
    completion_rate: str = Field("0%", alias="completionRate")
    overdue_tasks: List[TaskDTO] = Field(default_factory=list, alias="overdueTasks")

    model_config = ConfigDict(populate_by_name=True)


class TeamStatisticsDTO(BaseModel):
    team_id: Optional[str] = Field(None, alias="teamId")
    team_name: str = Field(..., alias="teamName")
    leader_name: Optional[str] = Field(None, alias="leaderName")
    total_members: int = Field(0, alias="totalMembers")
    team_total_tasks: int = Field(0, alias="teamTotalTasks")
    team_overdue_tasks: int = Field(0, alias="teamOverdueTasks")
    team_completed_tasks: int = Field(0, alias="teamCompletedTasks")
    team_completion_rate: str = Field("0%", alias="teamCompletionRate")
    members: List[TeamMemberTaskStatsDTO] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)


class MemberWorkloadDTO(BaseModel):
    userId: str
    userName: str
    totalTasks: int = 0
    completedTasks: int = 0
    pendingTasks: int = 0
    inProgressTasks: int = 0
    overdueTasks: int = 0


class TeamTaskDashboardDTO(BaseModel):
    totalTasks: int = 0
    completedTasks: int = 0
    pendingTasks: int = 0
    inProgressTasks: int = 0
    dueTodayTasks: int = 0
    overdueTasks: int = 0
    completionRate: float = 0.0
    teamWorkload: List[MemberWorkloadDTO] = []
