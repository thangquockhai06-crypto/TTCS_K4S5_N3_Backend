from datetime import datetime, timedelta
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.task import Task
from app.models.user import User
from app.models.team import Team, user_teams
from app.core.scope import DataScope, get_user_data_scope
from app.repositories.task_repository import TaskRepository
from app.repositories.base_repository import BaseRepository
from app.schemas.task import (
    CreateTaskDTO,
    UpdateTaskDTO,
    TaskDTO,
    PersonalDashboardDTO,
    PersonalTaskStatsDTO,
    TeamStatisticsDTO,
    TeamMemberTaskStatsDTO,
    format_duration_vietnamese,
)


def enrich_task_dto(task: Task) -> TaskDTO:
    """Bổ sung các trường tính toán thời gian quá hạn và sắp đến hạn cho TaskDTO."""
    now = datetime.utcnow()
    is_overdue = False
    overdue_seconds = None
    overdue_display = None
    is_due_soon = False
    time_remaining_seconds = None
    time_remaining_display = None

    if task.due_date and task.status not in ["completed", "cancelled"]:
        diff = (task.due_date - now).total_seconds()
        if diff < 0:
            is_overdue = True
            overdue_seconds = abs(diff)
            overdue_display = f"Quá hạn {format_duration_vietnamese(overdue_seconds)}"
        else:
            time_remaining_seconds = diff
            time_remaining_display = f"Còn {format_duration_vietnamese(diff)}"
            # Coi là sắp đến hạn nếu còn <= 24 giờ (86400 giây)
            if diff <= 86400:
                is_due_soon = True

    return TaskDTO(
        id=task.id,
        title=task.title,
        description=task.description,
        dueDate=task.due_date,
        status=task.status,
        priority=task.priority,
        assigneeId=task.assignee_id,
        creatorId=task.creator_id,
        customerId=task.customer_id,
        dealId=task.deal_id,
        remindedMilestones=task.reminded_milestones or [],
        completedAt=task.completed_at,
        createdAt=task.created_at,
        updatedAt=task.updated_at,
        isOverdue=is_overdue,
        overdueSeconds=overdue_seconds,
        overdueDisplay=overdue_display,
        isDueSoon=is_due_soon,
        timeRemainingSeconds=time_remaining_seconds,
        timeRemainingDisplay=time_remaining_display,
    )


class TaskService:

    @staticmethod
    def get_tasks(
        db: Session,
        user: User,
        status_filter: Optional[str] = None,
        priority: Optional[str] = None,
        assignee_id: Optional[str] = None,
        is_overdue: Optional[bool] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[TaskDTO], int]:
        tasks, total = TaskRepository.get_tasks(
            db=db,
            user=user,
            status=status_filter,
            priority=priority,
            assignee_id=assignee_id,
            is_overdue=is_overdue,
            search=search,
            skip=skip,
            limit=limit,
        )
        return [enrich_task_dto(t) for t in tasks], total

    @staticmethod
    def get_task_by_id(db: Session, task_id: str, user: User) -> TaskDTO:
        task = TaskRepository.get_by_id(db, task_id=task_id, user=user)
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy công việc.")
        return enrich_task_dto(task)

    @staticmethod
    def create_task(db: Session, dto: CreateTaskDTO, creator: User) -> TaskDTO:
        assignee_id = dto.assignee_id or creator.id

        task = Task(
            title=dto.title,
            description=dto.description,
            due_date=dto.due_date,
            priority=dto.priority or "medium",
            status="pending",
            assignee_id=assignee_id,
            creator_id=creator.id,
            customer_id=dto.customer_id,
            deal_id=dto.deal_id,
            reminded_milestones=[],
        )
        created = TaskRepository.create(db, task)
        return enrich_task_dto(created)

    @staticmethod
    def update_task(db: Session, task_id: str, dto: UpdateTaskDTO, user: User) -> TaskDTO:
        task = TaskRepository.get_by_id(db, task_id=task_id, user=user)
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy công việc.")

        if dto.title is not None:
            task.title = dto.title
        if dto.description is not None:
            task.description = dto.description
        if dto.due_date is not None:
            # Nếu thay đổi hạn chót -> reset danh sách các mốc đã nhắc nhở để quét lại chính xác
            if task.due_date != dto.due_date:
                task.due_date = dto.due_date
                task.reminded_milestones = []
        if dto.priority is not None:
            task.priority = dto.priority
        if dto.assignee_id is not None:
            task.assignee_id = dto.assignee_id
        if dto.customer_id is not None:
            task.customer_id = dto.customer_id
        if dto.deal_id is not None:
            task.deal_id = dto.deal_id

        if dto.status is not None:
            task.status = dto.status
            if dto.status == "completed":
                task.completed_at = datetime.utcnow()
            elif dto.status != "completed":
                task.completed_at = None

        updated = TaskRepository.update(db, task)
        return enrich_task_dto(updated)

    @staticmethod
    def delete_task(db: Session, task_id: str, user: User) -> None:
        task = TaskRepository.get_by_id(db, task_id=task_id, user=user)
        if not task:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy công việc.")
        TaskRepository.delete(db, task)

    # =========================================================================
    # 2. PERSONAL DASHBOARD CHO NHÂN VIÊN KINH DOANH
    # =========================================================================
    @staticmethod
    def get_personal_dashboard(db: Session, user: User) -> PersonalDashboardDTO:
        """
        Trả về dashboard cá nhân cho nhân viên kinh doanh:
        - Các công việc đã quá hạn (is_overdue: True)
        - Các công việc sắp đến hạn trong vòng 24h (is_due_soon: True)
        - Việc cần làm trong ngày hôm nay
        - Thống kê tổng số việc, việc đã xong, tỷ lệ hoàn thành
        """
        all_user_tasks = TaskRepository.get_tasks_by_assignee(db, assignee_id=user.id)
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)

        overdue_list: List[TaskDTO] = []
        due_soon_list: List[TaskDTO] = []
        today_list: List[TaskDTO] = []

        completed_count = 0
        pending_count = 0
        in_progress_count = 0

        for t in all_user_tasks:
            dto = enrich_task_dto(t)
            if t.status == "completed":
                completed_count += 1
            elif t.status == "in_progress":
                in_progress_count += 1
            elif t.status == "pending":
                pending_count += 1

            if dto.is_overdue:
                overdue_list.append(dto)
            elif dto.is_due_soon:
                due_soon_list.append(dto)

            # Việc có hạn trong ngày hôm nay
            if t.due_date and today_start <= t.due_date < today_end and t.status not in ["completed", "cancelled"]:
                today_list.append(dto)

        # Sắp xếp việc quá hạn: quá hạn lâu nhất lên đầu
        overdue_list.sort(key=lambda x: x.overdue_seconds or 0, reverse=True)
        # Sắp xếp việc sắp đến hạn: việc gần hạn nhất lên đầu
        due_soon_list.sort(key=lambda x: x.time_remaining_seconds or 9999999)

        total_tasks = len(all_user_tasks)
        rate = f"{(completed_count / total_tasks * 100):.1f}%" if total_tasks > 0 else "0%"

        stats = PersonalTaskStatsDTO(
            totalTasks=total_tasks,
            pendingTasks=pending_count,
            inProgressTasks=in_progress_count,
            completedTasks=completed_count,
            overdueTasksCount=len(overdue_list),
            dueSoonTasksCount=len(due_soon_list),
            completionRate=rate,
        )

        return PersonalDashboardDTO(
            stats=stats,
            overdueTasks=overdue_list,
            dueSoonTasks=due_soon_list,
            todayTasks=today_list,
        )

    # =========================================================================
    # 3. THỐNG KÊ CHO TRƯỞNG NHÓM (TEAM LEAD / MANAGER)
    # =========================================================================
    @staticmethod
    def get_team_lead_statistics(db: Session, current_user: User, target_team_id: Optional[str] = None) -> TeamStatisticsDTO:
        """
        Thống kê chi tiết tình trạng công việc của toàn bộ thành viên trong nhóm dành cho Trưởng nhóm.
        Bảo vệ phân quyền:
        - Nhân viên (DataScope.OWN) -> HTTP 403 Forbidden
        - Trưởng nhóm (DataScope.TEAM) -> Xem nhóm của mình
        - Quản trị viên/Giám đốc (DataScope.ALL) -> Xem nhóm chỉ định hoặc nhóm đầu tiên
        """
        scope = get_user_data_scope(current_user)
        if scope == DataScope.OWN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền truy cập báo cáo thống kê của Trưởng nhóm.",
            )

        # Xác định team_id và team_name
        effective_team_id = target_team_id if (target_team_id and scope == DataScope.ALL) else current_user.team_id
        team_name = effective_team_id or "Nhóm Kinh Doanh"
        leader_name = current_user.full_name

        team: Optional[Team] = None
        if effective_team_id:
            team = db.query(Team).filter(
                (Team.id == effective_team_id) | (Team.name == effective_team_id)
            ).first()

        if not team:
            team = db.query(Team).filter(Team.leader_id == current_user.id).first()

        if team:
            effective_team_id = team.id
            team_name = team.name
            leader_name = team.leader_name or current_user.full_name

        # Lấy danh sách thành viên trong nhóm:
        all_members = []
        if team:
            team_members = list(team.users)
            extra_members = db.query(User).filter(
                (User.team_id == team.id) | (User.team_id == team.name)
            ).all()
            all_members = team_members + extra_members
        elif effective_team_id:
            all_members = db.query(User).filter(User.team_id == effective_team_id).all()
        elif scope == DataScope.ALL:
            all_members = db.query(User).all()

        member_dict = {u.id: u for u in all_members}
        all_members = list(member_dict.values())


        members_dto: List[TeamMemberTaskStatsDTO] = []
        team_total_tasks = 0
        team_overdue_tasks = 0
        team_completed_tasks = 0

        for m in all_members:
            m_tasks = TaskRepository.get_tasks_by_assignee(db, assignee_id=m.id)
            m_total = len(m_tasks)
            m_completed = 0
            m_pending = 0
            m_due_soon = 0
            m_overdue_list: List[TaskDTO] = []

            for t in m_tasks:
                dto = enrich_task_dto(t)
                if t.status == "completed":
                    m_completed += 1
                elif t.status in ["pending", "in_progress"]:
                    m_pending += 1

                if dto.is_overdue:
                    m_overdue_list.append(dto)
                elif dto.is_due_soon:
                    m_due_soon += 1

            m_overdue_count = len(m_overdue_list)
            m_rate = f"{(m_completed / m_total * 100):.1f}%" if m_total > 0 else "0%"

            team_total_tasks += m_total
            team_overdue_tasks += m_overdue_count
            team_completed_tasks += m_completed

            # Sắp xếp việc quá hạn của thành viên
            m_overdue_list.sort(key=lambda x: x.overdue_seconds or 0, reverse=True)

            members_dto.append(
                TeamMemberTaskStatsDTO(
                    userId=m.id,
                    fullName=m.full_name,
                    email=m.email,
                    role=m.role,
                    avatarUrl=m.avatar_url,
                    totalTasks=m_total,
                    completedTasks=m_completed,
                    pendingTasks=m_pending,
                    overdueTasksCount=m_overdue_count,
                    dueSoonTasksCount=m_due_soon,
                    completionRate=m_rate,
                    overdueTasks=m_overdue_list,
                )
            )

        # Sắp xếp thành viên có nhiều việc quá hạn nhất lên đầu để Trưởng nhóm dễ theo dõi
        members_dto.sort(key=lambda x: x.overdue_tasks_count, reverse=True)

        team_rate = f"{(team_completed_tasks / team_total_tasks * 100):.1f}%" if team_total_tasks > 0 else "0%"

        return TeamStatisticsDTO(
            teamId=team.id if team else effective_team_id,
            teamName=team.name if team else team_name,
            leaderName=(team.leader_name or current_user.full_name) if team else leader_name,
            totalMembers=len(all_members),
            teamTotalTasks=team_total_tasks,
            teamOverdueTasks=team_overdue_tasks,
            teamCompletedTasks=team_completed_tasks,
            teamCompletionRate=team_rate,
            members=members_dto,
        )

