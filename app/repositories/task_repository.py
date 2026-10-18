from typing import Optional, List, Tuple, Dict, Any
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_, desc

from app.models.task import Task
from app.models.user import User
from app.repositories.base_repository import BaseRepository


class TaskRepository(BaseRepository):
    """
    Tầng Repository xử lý truy vấn dữ liệu Công việc (Tasks & Team Task Progress: S6-06, S6-07, S6-09).
    Tích hợp Centralized Data Scope Filter ở mức CSDL.
    """

    @staticmethod
    def get_all(
        db: Session,
        user: Optional[User] = None,
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
        """Lấy danh sách công việc thỏa mãn Data Scope và các bộ lọc Sprint 6 (S6-07)."""
        query = db.query(Task)

        # 1. Centralized Data Scope
        if user is not None:
            query = BaseRepository.apply_data_scope_filter(query, user, Task)

        # 2. Lọc theo người được phân công (assignee)
        if assignee_id and assignee_id.lower() != "all":
            query = query.filter(Task.assignee_id == assignee_id)

        # 3. Lọc theo trạng thái (status)
        if status and status.lower() != "all":
            norm_status = status.lower()
            if norm_status == "completed":
                query = query.filter(or_(Task.status == "completed", Task.is_completed == True))
            elif norm_status == "pending":
                query = query.filter(and_(Task.status == "pending", Task.is_completed == False))
            elif norm_status == "in_progress":
                query = query.filter(and_(Task.status == "in_progress", Task.is_completed == False))
            else:
                query = query.filter(Task.status == norm_status)

        # 4. Lọc theo hạn xử lý (due date range)
        if due_date_from is not None:
            query = query.filter(Task.due_date >= due_date_from)
        if due_date_to is not None:
            query = query.filter(Task.due_date <= due_date_to)

        # 5. Lọc theo trạng thái quá hạn (overdue status)
        today = date.today()
        if is_overdue is True:
            query = query.filter(
                and_(
                    Task.due_date != None,
                    Task.due_date < today,
                    Task.is_completed == False,
                    Task.status != "completed",
                )
            )
        elif is_overdue is False:
            query = query.filter(
                or_(
                    Task.due_date == None,
                    Task.due_date >= today,
                    Task.is_completed == True,
                    Task.status == "completed",
                )
            )

        # 6. Tìm kiếm tiêu đề & mô tả
        if search and search.strip():
            pat = f"%{search.strip()}%"
            query = query.filter(or_(Task.title.ilike(pat), Task.description.ilike(pat)))

        # 7. Lọc theo mức độ ưu tiên (priority)
        if priority and priority.lower() != "all":
            query = query.filter(Task.priority == priority.lower())

        total = query.count()
        tasks = query.order_by(Task.is_completed.asc(), Task.due_date.asc(), Task.created_at.desc()).offset(skip).limit(limit).all()
        return tasks, total

    @staticmethod
    def get_by_id(db: Session, task_id: str) -> Optional[Task]:
        return db.query(Task).filter(Task.id == task_id).first()

    @staticmethod
    def get_scoped_by_id(db: Session, task_id: str, user: User) -> Task:
        return BaseRepository.get_scoped_record_or_raise(
            db=db,
            model=Task,
            record_id=task_id,
            user=user,
            not_found_msg="Không tìm thấy công việc.",
            forbidden_msg="Bạn không có quyền truy cập công việc này.",
        )

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
    def get_dashboard_metrics(db: Session, user: User) -> Dict[str, Any]:
        """Tính toán các chỉ số Dashboard Tiến độ Công việc Nhóm (S6-09)."""
        base_query = db.query(Task)
        scoped_query = BaseRepository.apply_data_scope_filter(base_query, user, Task)
        all_tasks = scoped_query.all()

        today = date.today()
        total_tasks = len(all_tasks)
        completed_tasks = 0
        in_progress_tasks = 0
        pending_tasks = 0
        due_today_tasks = 0
        overdue_tasks = 0

        # Phân loại khối lượng theo từng thành viên (Team Workload)
        user_map: Dict[str, Dict[str, Any]] = {}

        for t in all_tasks:
            is_comp = t.is_completed or (t.status == "completed")
            is_over = bool(t.due_date and t.due_date < today and not is_comp)
            is_due_today = bool(t.due_date and t.due_date == today and not is_comp)

            if is_comp:
                completed_tasks += 1
            elif t.status == "in_progress":
                in_progress_tasks += 1
            else:
                pending_tasks += 1

            if is_over:
                overdue_tasks += 1
            if is_due_today:
                due_today_tasks += 1

            # Workload
            uid = t.assignee_id or "unassigned"
            uname = t.assignee.full_name if t.assignee else "Chưa phân công"
            if uid not in user_map:
                user_map[uid] = {
                    "userId": uid,
                    "userName": uname,
                    "totalTasks": 0,
                    "completedTasks": 0,
                    "pendingTasks": 0,
                    "inProgressTasks": 0,
                    "overdueTasks": 0,
                }
            user_map[uid]["totalTasks"] += 1
            if is_comp:
                user_map[uid]["completedTasks"] += 1
            elif t.status == "in_progress":
                user_map[uid]["inProgressTasks"] += 1
            else:
                user_map[uid]["pendingTasks"] += 1
            if is_over:
                user_map[uid]["overdueTasks"] += 1

        completion_rate = round((completed_tasks / total_tasks * 100), 1) if total_tasks > 0 else 0.0

        return {
            "totalTasks": total_tasks,
            "completedTasks": completed_tasks,
            "pendingTasks": pending_tasks,
            "inProgressTasks": in_progress_tasks,
            "dueTodayTasks": due_today_tasks,
            "overdueTasks": overdue_tasks,
            "completionRate": completion_rate,
            "teamWorkload": list(user_map.values()),
        }
