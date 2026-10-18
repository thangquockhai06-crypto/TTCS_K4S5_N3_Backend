from datetime import datetime
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc, asc

from app.models.task import Task
from app.models.user import User
from app.repositories.base_repository import BaseRepository, apply_data_scope_filter


class TaskRepository:

    @staticmethod
    def get_by_id(db: Session, task_id: str, user: Optional[User] = None) -> Optional[Task]:
        """Lấy chi tiết Task có kiểm tra phạm vi dữ liệu (Data Scope)."""
        if user is not None:
            return BaseRepository.get_scoped_record_or_raise(
                db=db,
                model=Task,
                record_id=task_id,
                user=user,
                not_found_msg="Không tìm thấy công việc.",
                forbidden_msg="Bạn không có quyền truy cập công việc này.",
            )
        return db.query(Task).filter(Task.id == task_id).first()

    @staticmethod
    def get_tasks(
        db: Session,
        user: Optional[User] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        assignee_id: Optional[str] = None,
        is_overdue: Optional[bool] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Task], int]:
        """Lấy danh sách Tasks tuân thủ Centralized Data Scope."""
        query = db.query(Task)
        if user is not None:
            query = apply_data_scope_filter(query=query, user=user, model=Task)

        if status:
            query = query.filter(Task.status == status)
        if priority:
            query = query.filter(Task.priority == priority)
        if assignee_id:
            query = query.filter(Task.assignee_id == assignee_id)

        now = datetime.utcnow()
        if is_overdue is True:
            query = query.filter(
                Task.status.notin_(["completed", "cancelled"]),
                Task.due_date.isnot(None),
                Task.due_date < now,
            )
        elif is_overdue is False:
            query = query.filter(
                or_(
                    Task.status.in_(["completed", "cancelled"]),
                    Task.due_date.is_(None),
                    Task.due_date >= now,
                )
            )

        if search:
            search_term = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Task.title.ilike(search_term),
                    Task.description.ilike(search_term),
                )
            )

        total = query.count()
        tasks = query.order_by(asc(Task.due_date.is_(None)), asc(Task.due_date), desc(Task.created_at)).offset(skip).limit(limit).all()
        return tasks, total

    @staticmethod
    def create(db: Session, task: Task) -> Task:
        db.add(task)
        db.commit()
        db.refresh(task)
        return task

    @staticmethod
    def update(db: Session, task: Task) -> Task:
        task.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(task)
        return task

    @staticmethod
    def delete(db: Session, task: Task) -> None:
        db.delete(task)
        db.commit()

    @staticmethod
    def get_unfinished_tasks_for_scanning(db: Session) -> List[Task]:
        """
        Lấy tất cả các task chưa hoàn thành có cài đặt due_date
        để phục vụ tiến trình chạy ngầm quét nhắc nhở và đánh dấu quá hạn.
        """
        return (
            db.query(Task)
            .filter(
                Task.status.notin_(["completed", "cancelled"]),
                Task.due_date.isnot(None),
            )
            .all()
        )

    @staticmethod
    def get_tasks_by_assignee(db: Session, assignee_id: str) -> List[Task]:
        return db.query(Task).filter(Task.assignee_id == assignee_id).all()

