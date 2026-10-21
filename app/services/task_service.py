import uuid
from datetime import datetime, date
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.task import Task
from app.models.user import User
from app.schemas.task import (
    CreateTaskDTO,
    UpdateTaskDTO,
    TaskDTO,
    TeamTaskDashboardDTO,
    MemberWorkloadDTO,
)
from app.repositories.task_repository import TaskRepository
from app.repositories.customer_repository import CustomerRepository
from app.repositories.deal_repository import DealRepository


class TaskService:
    """
    Tầng Service xử lý toàn bộ nghiệp vụ Quản lý Công việc & Dashboard Tiến độ (S6-06, S6-07, S6-09).
    """

    @classmethod
    def map_to_dto(cls, task: Task) -> TaskDTO:
        today = date.today()
        is_comp = bool(task.is_completed or (task.status == "completed"))
        is_over = bool(task.due_date and task.due_date < today and not is_comp)

        assignee_name = task.assignee.full_name if task.assignee else None
        creator_name = task.creator.full_name if task.creator else None
        customer_name = task.customer.full_name if task.customer else None
        deal_title = task.deal.title if task.deal else None

        return TaskDTO(
            id=task.id,
            title=task.title,
            description=task.description or "",
            priority=task.priority,
            status=task.status,
            isCompleted=is_comp,
            dueDate=task.due_date.isoformat() if task.due_date else None,
            completedAt=task.completed_at.isoformat() if task.completed_at else None,
            assigneeId=task.assignee_id,
            assigneeName=assignee_name,
            creatorId=task.creator_id,
            creatorName=creator_name,
            customerId=task.customer_id,
            customerName=customer_name,
            dealId=task.deal_id,
            dealTitle=deal_title,
            isOverdue=is_over,
            createdAt=task.created_at.isoformat() if task.created_at else None,
            updatedAt=task.updated_at.isoformat() if task.updated_at else None,
        )

    @staticmethod
    def get_tasks(
        db: Session,
        user: User,
        assignee_id: Optional[str] = None,
        status: Optional[str] = None,
        due_date_from: Optional[date] = None,
        due_date_to: Optional[date] = None,
        is_overdue: Optional[bool] = None,
        search: Optional[str] = None,
        priority: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Task], int]:
        """S6-07: Lọc công việc theo người thực hiện, trạng thái, hạn xử lý và quá hạn."""
        return TaskRepository.get_all(
            db=db,
            user=user,
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

    @staticmethod
    def get_task_by_id(db: Session, task_id: str, user: User) -> Task:
        return TaskRepository.get_scoped_by_id(db, task_id, user)

    @classmethod
    def create_task(cls, db: Session, dto: CreateTaskDTO, user: User) -> Task:
        """S6-06: Tạo mới công việc."""
        if dto.customerId:
            CustomerRepository.get_scoped_by_id(db, dto.customerId, user)
        if dto.dealId:
            DealRepository.get_scoped_by_id(db, dto.dealId, user)

        due_d = None
        if dto.dueDate:
            try:
                due_d = date.fromisoformat(dto.dueDate.strip().split('T')[0])
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Định dạng hạn xử lý không hợp lệ (chuẩn YYYY-MM-DD).",
                )

        new_task = Task(
            id=str(uuid.uuid4()),
            title=dto.title.strip(),
            description=dto.description or "",
            priority=(dto.priority or "medium").lower(),
            status=(dto.status or "pending").lower(),
            is_completed=bool(dto.isCompleted),
            due_date=due_d,
            assignee_id=dto.assigneeId or user.id,
            creator_id=user.id,
            customer_id=dto.customerId,
            deal_id=dto.dealId,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        created_task = TaskRepository.create(db, new_task)
        if created_task.assignee_id and created_task.assignee_id != user.id:
            try:
                from app.services.notification_service import NotificationService
                NotificationService.notify_task_assigned(
                    db=db,
                    task_id=created_task.id,
                    task_title=created_task.title,
                    assignee_id=created_task.assignee_id,
                    creator_name=user.full_name or user.email,
                )
            except Exception:
                pass
        return created_task

    @classmethod
    def update_task(cls, db: Session, task_id: str, dto: UpdateTaskDTO, user: User) -> Task:
        """S6-06: Cập nhật thông tin công việc."""
        task = TaskRepository.get_scoped_by_id(db, task_id, user)

        if dto.title is not None:
            task.title = dto.title.strip()
        if dto.description is not None:
            task.description = dto.description
        if dto.priority is not None:
            task.priority = dto.priority.lower()
        if dto.assigneeId is not None:
            task.assignee_id = dto.assigneeId or None
        if dto.customerId is not None:
            task.customer_id = dto.customerId or None
        if dto.dealId is not None:
            task.deal_id = dto.dealId or None

        if dto.dueDate is not None:
            if dto.dueDate.strip():
                try:
                    task.due_date = date.fromisoformat(dto.dueDate.strip().split('T')[0])
                except ValueError:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Định dạng ngày hạn không hợp lệ.")
            else:
                task.due_date = None

        if dto.isCompleted is not None:
            task.is_completed = dto.isCompleted
            if dto.isCompleted:
                task.status = "completed"
                task.completed_at = datetime.utcnow()
            else:
                if task.status == "completed":
                    task.status = "pending"
                task.completed_at = None

        if dto.status is not None:
            task.status = dto.status.lower()
            if task.status == "completed":
                task.is_completed = True
                task.completed_at = datetime.utcnow()
            elif task.is_completed and task.status != "completed":
                task.is_completed = False
                task.completed_at = None

        return TaskRepository.update(db, task)

    @classmethod
    def toggle_completion(cls, db: Session, task_id: str, user: User) -> Task:
        """S6-06: Đảo trạng thái hoàn thành công việc nhanh chóng."""
        task = TaskRepository.get_scoped_by_id(db, task_id, user)
        task.is_completed = not task.is_completed
        if task.is_completed:
            task.status = "completed"
            task.completed_at = datetime.utcnow()
        else:
            task.status = "pending"
            task.completed_at = None
        return TaskRepository.update(db, task)

    @classmethod
    def delete_task(cls, db: Session, task_id: str, user: User) -> None:
        """S6-06: Xóa công việc."""
        task = TaskRepository.get_scoped_by_id(db, task_id, user)
        TaskRepository.delete(db, task)

    @classmethod
    def get_dashboard(cls, db: Session, user: User) -> TeamTaskDashboardDTO:
        """S6-09: Dashboard tiến độ công việc nhóm."""
        metrics = TaskRepository.get_dashboard_metrics(db, user)
        return TeamTaskDashboardDTO(
            totalTasks=metrics["totalTasks"],
            completedTasks=metrics["completedTasks"],
            pendingTasks=metrics["pendingTasks"],
            inProgressTasks=metrics["inProgressTasks"],
            dueTodayTasks=metrics["dueTodayTasks"],
            overdueTasks=metrics["overdueTasks"],
            completionRate=metrics["completionRate"],
            teamWorkload=[MemberWorkloadDTO(**m) for m in metrics["teamWorkload"]],
        )
