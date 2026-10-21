from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.services.task_service import TaskService
from app.services.task_reminder_service import TaskReminderService
from app.repositories.reminder_setting_repository import ReminderSettingRepository
from app.schemas.task import (
    TaskDTO,
    CreateTaskDTO,
    UpdateTaskDTO,
    PersonalDashboardDTO,
    TeamStatisticsDTO,
    ReminderSettingDTO,
    UpdateReminderSettingDTO,
)

router = APIRouter(prefix="/tasks", tags=["Tasks & Reminders Management"])


# =============================================================================
# 1. TRANG CHỦ CÁ NHÂN & THỐNG KÊ (DASHBOARD & TEAM STATS)
# =============================================================================

@router.get(
    "/my-dashboard",
    response_model=PersonalDashboardDTO,
    summary="Dashboard cá nhân cho Nhân viên kinh doanh (Việc quá hạn, sắp đến hạn, hôm nay)",
)
def get_personal_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PersonalDashboardDTO:
    """
    User Story 1:
    Là Nhân viên kinh doanh, tôi muốn được nhắc việc sắp đến hạn và việc quá hạn
    trong ứng dụng để không để trôi việc.
    """
    return TaskService.get_personal_dashboard(db=db, user=current_user)


@router.get(
    "/team-lead/statistics",
    response_model=TeamStatisticsDTO,
    summary="Thống kê tổng số việc quá hạn và tiến độ của từng thành viên trong nhóm",
)
def get_team_lead_statistics(
    team_id: Optional[str] = Query(None, alias="teamId", description="Mã nhóm (nếu là Admin)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TeamStatisticsDTO:
    """
    User Story 2:
    Trưởng nhóm cần theo dõi được tổng số việc quá hạn của từng thành viên trong nhóm.
    - Yêu cầu quyền: Trưởng nhóm / Quản lý (DataScope.TEAM) hoặc Ban Giám Đốc/Admin (DataScope.ALL).
    - Nhân viên thông thường bị từ chối với HTTP 403 Forbidden.
    """
    return TaskService.get_team_lead_statistics(
        db=db,
        current_user=current_user,
        target_team_id=team_id,
    )


# =============================================================================
# 2. CẤU HÌNH MỐC NHẮC NHỞ (REMINDER SETTINGS)
# =============================================================================

@router.get(
    "/reminder-settings",
    response_model=ReminderSettingDTO,
    summary="Lấy cấu hình mốc thời gian nhắc việc trước hạn của người dùng",
)
def get_reminder_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReminderSettingDTO:
    """
    Trả về cấu hình nhắc việc của người dùng hiện tại (hoặc cấu hình mặc định hệ thống nếu chưa tuỳ chỉnh).
    Mặc định: [15, 60, 1440] (15 phút, 1 giờ, 1 ngày).
    """
    setting = ReminderSettingRepository.get_effective_setting(db=db, user_id=current_user.id)
    return ReminderSettingDTO(
        id=setting.id,
        userId=setting.user_id,
        remindBeforeMinutes=setting.remind_before_minutes or [15, 60, 1440],
        notifyOnOverdue=setting.notify_on_overdue,
        enableInApp=setting.enable_in_app,
        enableEmail=setting.enable_email,
        createdAt=setting.created_at,
        updatedAt=setting.updated_at,
    )


@router.put(
    "/reminder-settings",
    response_model=ReminderSettingDTO,
    summary="Cập nhật cấu hình mốc thời gian nhắc việc trước hạn của người dùng",
)
def update_reminder_settings(
    dto: UpdateReminderSettingDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReminderSettingDTO:
    """
    Cho phép nhân viên kinh doanh thiết lập mốc thời gian nhắc trước hạn cá nhân
    (ví dụ: nhắc trước 15 phút, 1 giờ, 1 ngày...).
    """
    # Lọc bỏ các giá trị âm hoặc trùng lặp
    valid_minutes = sorted(list({int(m) for m in dto.remind_before_minutes if m > 0}))
    if not valid_minutes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Danh sách mốc thời gian nhắc nhở phải chứa ít nhất một mốc phút lớn hơn 0.",
        )

    updated = ReminderSettingRepository.create_or_update_user_setting(
        db=db,
        user_id=current_user.id,
        remind_before_minutes=valid_minutes,
        notify_on_overdue=dto.notify_on_overdue if dto.notify_on_overdue is not None else True,
        enable_in_app=dto.enable_in_app if dto.enable_in_app is not None else True,
        enable_email=dto.enable_email if dto.enable_email is not None else False,
    )
    return ReminderSettingDTO(
        id=updated.id,
        userId=updated.user_id,
        remindBeforeMinutes=updated.remind_before_minutes,
        notifyOnOverdue=updated.notify_on_overdue,
        enableInApp=updated.enable_in_app,
        enableEmail=updated.enable_email,
        createdAt=updated.created_at,
        updatedAt=updated.updated_at,
    )


# =============================================================================
# 3. KÍCH HOẠT TIẾN TRÌNH QUÉT NHẮC VIỆC (MANUAL TRIGGER / CRONJOB)
# =============================================================================

@router.post(
    "/trigger-scan",
    summary="Kích hoạt tức thì tiến trình quét việc sắp đến hạn và quá hạn",
)
def trigger_task_reminder_scan(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Endpoint kích hoạt thủ công cho Admin / Scheduled Cronjob bên ngoài hoặc kiểm thử tự động.
    """
    return TaskReminderService.scan_and_notify_tasks(db=db)


# =============================================================================
# 4. CRUD CÔNG VIỆC (TASKS CRUD)
# =============================================================================

@router.get("", response_model=List[TaskDTO], summary="Lấy danh sách công việc (Tuân thủ Data Scope)")
def get_tasks(
    status: Optional[str] = Query(None, description="Lọc theo trạng thái: pending, in_progress, completed, overdue, cancelled"),
    priority: Optional[str] = Query(None, description="Lọc theo mức độ ưu tiên: low, medium, high, urgent"),
    assigneeId: Optional[str] = Query(None, description="Lọc theo nhân viên phụ trách"),
    isOverdue: Optional[bool] = Query(None, description="Lọc việc đã quá hạn"),
    search: Optional[str] = Query(None, description="Tìm kiếm theo tiêu đề hoặc mô tả"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[TaskDTO]:
    tasks, _ = TaskService.get_tasks(
        db=db,
        user=current_user,
        status_filter=status,
        priority=priority,
        assignee_id=assigneeId,
        is_overdue=isOverdue,
        search=search,
        skip=skip,
        limit=limit,
    )
    return tasks


@router.post("", response_model=TaskDTO, status_code=status.HTTP_201_CREATED, summary="Tạo mới công việc")
def create_task(
    dto: CreateTaskDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskDTO:
    return TaskService.create_task(db=db, dto=dto, creator=current_user)


@router.get("/{task_id}", response_model=TaskDTO, summary="Xem chi tiết một công việc")
def get_task_detail(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskDTO:
    return TaskService.get_task_by_id(db=db, task_id=task_id, user=current_user)


@router.put("/{task_id}", response_model=TaskDTO, summary="Cập nhật thông tin công việc")
def update_task(
    task_id: str,
    dto: UpdateTaskDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskDTO:
    return TaskService.update_task(db=db, task_id=task_id, dto=dto, user=current_user)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Xóa công việc")
def delete_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    TaskService.delete_task(db=db, task_id=task_id, user=current_user)
    return None

