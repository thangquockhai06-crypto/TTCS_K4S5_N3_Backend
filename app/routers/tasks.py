from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.task import Task
from app.schemas.task import (
    TaskDTO,
    CreateTaskDTO,
    UpdateTaskDTO,
    TeamTaskDashboardDTO,
)
from app.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["Task Management (Sprint 6: S6-06, S6-07, S6-09)"])


# S6-09: Team task progress dashboard showing due/overdue tasks, completion status, and team workload
@router.get("/dashboard", response_model=TeamTaskDashboardDTO, summary="Dashboard tiến độ công việc nhóm (S6-09)")
def get_team_task_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TeamTaskDashboardDTO:
    """
    S6-09: Thống kê tiến độ công việc của nhóm:
    - Công việc đến hạn / quá hạn
    - Tỷ lệ hoàn thành công việc
    - Khối lượng công việc theo từng thành viên (Workload)
    """
    return TaskService.get_dashboard(db=db, user=current_user)


# S6-06 & S6-07: Filter tasks by assignee, status, due date, and overdue status
@router.get("", response_model=List[TaskDTO], summary="Lấy danh sách công việc có lọc (S6-06, S6-07)")
def get_tasks(
    response: Response,
    assignee_id: Optional[str] = Query(None, description="Lọc theo người được giao việc (S6-07)"),
    status: Optional[str] = Query(None, description="Lọc theo trạng thái: pending, in_progress, completed, all (S6-07)"),
    due_date_from: Optional[date] = Query(None, description="Lọc ngày đến hạn từ (S6-07)"),
    due_date_to: Optional[date] = Query(None, description="Lọc ngày đến hạn đến (S6-07)"),
    is_overdue: Optional[bool] = Query(None, description="Lọc trạng thái quá hạn (S6-07)"),
    search: Optional[str] = Query(None, description="Tìm kiếm theo tiêu đề hoặc mô tả"),
    priority: Optional[str] = Query(None, description="Lọc theo mức ưu tiên: low, medium, high, urgent"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[TaskDTO]:
    """
    S6-06 & S6-07: Quản lý và lọc công việc:
    - Trưởng nhóm xem được công việc của toàn bộ thành viên trong nhóm.
    - Nhân viên xem công việc do mình phụ trách hoặc được giao.
    """
    tasks, total = TaskService.get_tasks(
        db=db,
        user=current_user,
        assignee_id=assignee_id,
        status=status,
        due_date_from=due_date_from,
        due_date_to=due_date_to,
        is_overdue=is_overdue,
        search=search,
        priority=priority,
        skip=skip,
        limit=limit,
    )
    response.headers["X-Total-Count"] = str(total)
    return [TaskService.map_to_dto(t) for t in tasks]


# S6-06: Create task
@router.post("", response_model=TaskDTO, status_code=status.HTTP_201_CREATED, summary="Tạo mới công việc (S6-06)")
def create_task(
    dto: CreateTaskDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskDTO:
    """S6-06: Tạo mới công việc với tiêu đề, mô tả, mức ưu tiên, người phụ trách, hạn xử lý."""
    task = TaskService.create_task(db=db, dto=dto, user=current_user)
    return TaskService.map_to_dto(task)


# S6-06: Get single task detail
@router.get("/{task_id}", response_model=TaskDTO, summary="Xem chi tiết công việc (S6-06)")
def get_task_detail(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskDTO:
    task = TaskService.get_task_by_id(db=db, task_id=task_id, user=current_user)
    return TaskService.map_to_dto(task)


# S6-06: Update task
@router.put("/{task_id}", response_model=TaskDTO, summary="Cập nhật thông tin công việc (S6-06)")
def update_task(
    task_id: str,
    dto: UpdateTaskDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskDTO:
    """S6-06: Cập nhật tiêu đề, mô tả, mức ưu tiên, người phụ trách, hạn xử lý và trạng thái hoàn thành."""
    task = TaskService.update_task(db=db, task_id=task_id, dto=dto, user=current_user)
    return TaskService.map_to_dto(task)


# S6-06: Toggle completion status
@router.patch("/{task_id}/toggle", response_model=TaskDTO, summary="Chuyển đổi trạng thái hoàn thành công việc (S6-06)")
def toggle_task_completion(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskDTO:
    """S6-06: Đánh dấu nhanh đã hoàn thành hoặc chưa hoàn thành."""
    task = TaskService.toggle_completion(db=db, task_id=task_id, user=current_user)
    return TaskService.map_to_dto(task)


# S6-06: Delete task
@router.delete("/{task_id}", summary="Xóa công việc (S6-06)")
def delete_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    TaskService.delete_task(db=db, task_id=task_id, user=current_user)
    return {"message": "Đã xóa công việc thành công."}
