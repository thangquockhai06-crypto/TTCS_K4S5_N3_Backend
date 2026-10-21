from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="Tiêu đề công việc")
    description: Optional[str] = Field("", description="Mô tả chi tiết công việc")
    priority: str = Field("medium", description="Mức ưu tiên: low, medium, high, urgent")
    status: Optional[str] = Field("pending", description="Trạng thái: pending, in_progress, completed, cancelled")
    isCompleted: Optional[bool] = Field(False, description="Đã hoàn thành hay chưa")
    dueDate: Optional[str] = Field(None, description="Hạn xử lý (YYYY-MM-DD)")
    assigneeId: Optional[str] = Field(None, description="Người được giao việc")
    customerId: Optional[str] = Field(None, description="Khách hàng liên quan")
    dealId: Optional[str] = Field(None, description="Cơ hội bán hàng liên quan")


class CreateTaskDTO(TaskBase):
    pass


class UpdateTaskDTO(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    isCompleted: Optional[bool] = None
    dueDate: Optional[str] = None
    assigneeId: Optional[str] = None
    customerId: Optional[str] = None
    dealId: Optional[str] = None


class TaskDTO(BaseModel):
    id: str
    title: str
    description: Optional[str] = ""
    priority: str
    status: str
    isCompleted: bool
    dueDate: Optional[str] = None
    completedAt: Optional[str] = None
    assigneeId: Optional[str] = None
    assigneeName: Optional[str] = None
    creatorId: Optional[str] = None
    creatorName: Optional[str] = None
    customerId: Optional[str] = None
    customerName: Optional[str] = None
    dealId: Optional[str] = None
    dealTitle: Optional[str] = None
    isOverdue: bool = False
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


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
