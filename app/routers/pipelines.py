from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.pipeline_stage import PipelineStage
from app.models.deal import Deal
from app.schemas.pipeline import (
    PipelineStageDTO,
    CreatePipelineStageDTO,
    UpdatePipelineStageDTO,
    ReorderStagesDTO,
)

router = APIRouter(prefix="/pipelines", tags=["Pipeline Configuration Management (S2-09)"])


@router.get("/stages", response_model=List[PipelineStageDTO], summary="Lấy danh sách các giai đoạn phễu bán hàng")
def get_pipeline_stages(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[PipelineStageDTO]:
    stages = db.query(PipelineStage).order_by(PipelineStage.order_index.asc()).all()

    # Pre-populate default standard stages if empty
    if not stages:
        default_stages = [
            PipelineStage(
                name="Tiếp cận ban đầu",
                stage_key="New",
                order_index=0,
                probability=20,
                exit_rules='{"require_contact": true, "require_meeting": false}',
                color="#3b82f6",
                is_won=False,
                is_lost=False,
            ),
            PipelineStage(
                name="Đã liên hệ & Khảo sát",
                stage_key="Contacted",
                order_index=1,
                probability=45,
                exit_rules='{"require_meeting": true, "require_budget": true}',
                color="#06b6d4",
                is_won=False,
                is_lost=False,
            ),
            PipelineStage(
                name="Thương thảo hợp đồng",
                stage_key="Negotiation",
                order_index=2,
                probability=80,
                exit_rules='{"require_quote": true, "require_approval": true}',
                color="#f59e0b",
                is_won=False,
                is_lost=False,
            ),
            PipelineStage(
                name="Chốt thành công (Won)",
                stage_key="Won",
                order_index=3,
                probability=100,
                exit_rules='{"require_contract": true, "require_payment": true}',
                color="#10b981",
                is_won=True,
                is_lost=False,
            ),
            PipelineStage(
                name="Thất bại (Lost)",
                stage_key="Lost",
                order_index=4,
                probability=0,
                exit_rules='{"require_loss_reason": true}',
                color="#ef4444",
                is_won=False,
                is_lost=True,
            ),
        ]
        db.add_all(default_stages)
        db.commit()
        stages = db.query(PipelineStage).order_by(PipelineStage.order_index.asc()).all()

    return [
        PipelineStageDTO(
            id=s.id,
            name=s.name,
            stage_key=s.stage_key,
            order_index=s.order_index,
            probability=s.probability,
            exit_rules=s.exit_rules,
            color=s.color,
            is_won=s.is_won,
            is_lost=s.is_lost,
        )
        for s in stages
    ]


@router.post("/stages", response_model=PipelineStageDTO, status_code=status.HTTP_201_CREATED, summary="Tạo mới giai đoạn phễu")
def create_pipeline_stage(
    dto: CreatePipelineStageDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PipelineStageDTO:
    prob = max(0, min(100, dto.probability))
    stage = PipelineStage(
        name=dto.name.strip(),
        stage_key=dto.stage_key.strip(),
        order_index=dto.order_index or 0,
        probability=prob,
        exit_rules=dto.exit_rules,
        color=dto.color,
        is_won=dto.is_won,
        is_lost=dto.is_lost,
    )
    db.add(stage)
    db.commit()
    db.refresh(stage)
    return PipelineStageDTO(
        id=stage.id,
        name=stage.name,
        stage_key=stage.stage_key,
        order_index=stage.order_index,
        probability=stage.probability,
        exit_rules=stage.exit_rules,
        color=stage.color,
        is_won=stage.is_won,
        is_lost=stage.is_lost,
    )


@router.post("/reorder", summary="Cập nhật thứ tự giai đoạn")
@router.put("/reorder", summary="Cập nhật thứ tự giai đoạn")
@router.post("/stages/reorder", summary="Kéo thả sắp xếp lại thứ tự giai đoạn (S2-09)")
@router.put("/stages/reorder", summary="Kéo thả sắp xếp lại thứ tự giai đoạn (S2-09)")
def reorder_pipeline_stages(
    dto: ReorderStagesDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if dto.ordered_stage_ids:
        for idx, s_id in enumerate(dto.ordered_stage_ids):
            s = db.query(PipelineStage).filter(PipelineStage.id == s_id).first()
            if s:
                s.order_index = idx
        db.commit()
        return {"message": "Cập nhật thứ tự giai đoạn thành công. Không ảnh hưởng đến các Deals hiện hữu."}
    elif dto.items:
        for item in dto.items:
            s = db.query(PipelineStage).filter(PipelineStage.id == item.id).first()
            if s:
                s.order_index = item.order_index
        db.commit()
        return {"message": "Cập nhật thứ tự giai đoạn thành công. Không ảnh hưởng đến các Deals hiện hữu."}
    return {"message": "Không có dữ liệu thay đổi thứ tự."}


@router.put("/stages/{stage_id}", response_model=PipelineStageDTO, summary="Cập nhật tham số giai đoạn")
def update_pipeline_stage(
    stage_id: str,
    dto: UpdatePipelineStageDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PipelineStageDTO:
    stage = db.query(PipelineStage).filter(PipelineStage.id == stage_id).first()
    if not stage:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy giai đoạn phễu.")

    if dto.name is not None:
        stage.name = dto.name.strip()
    if dto.probability is not None:
        stage.probability = max(0, min(100, dto.probability))
    if dto.exit_rules is not None:
        stage.exit_rules = dto.exit_rules
    if dto.color is not None:
        stage.color = dto.color

    db.commit()
    db.refresh(stage)
    return PipelineStageDTO(
        id=stage.id,
        name=stage.name,
        stage_key=stage.stage_key,
        order_index=stage.order_index,
        probability=stage.probability,
        exit_rules=stage.exit_rules,
        color=stage.color,
        is_won=stage.is_won,
        is_lost=stage.is_lost,
    )


@router.delete("/stages/{stage_id}", summary="Xóa giai đoạn phễu bán hàng (S2-09)")
def delete_pipeline_stage(
    stage_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stage = db.query(PipelineStage).filter(PipelineStage.id == stage_id).first()
    if not stage:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy giai đoạn phễu.")

    # Không cho phép xóa các giai đoạn hệ thống chuẩn (Chốt thành công hoặc Thất bại)
    if stage.is_won or stage.is_lost or stage.stage_key in ["Won", "Lost"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Không thể xóa giai đoạn chuẩn Chốt thành công hoặc Thất bại của hệ thống.",
        )

    remaining_stages = db.query(PipelineStage).filter(PipelineStage.id != stage_id).all()
    if not remaining_stages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Hệ thống cần duy trì ít nhất một giai đoạn phễu bán hàng.",
        )

    # Bảo toàn an toàn dữ liệu cơ hội bán hàng (Deals):
    # Nếu có deals thuộc giai đoạn này, di chuyển sang giai đoạn mở đầu tiên còn lại
    fallback_stage = next(
        (s for s in remaining_stages if not s.is_won and not s.is_lost),
        remaining_stages[0],
    )
    fallback_key = fallback_stage.stage_key.lower() if fallback_stage else "lead"
    valid_enum_stages = ["lead", "contact", "proposal", "negotiation", "won", "lost"]
    target_stage = fallback_key if fallback_key in valid_enum_stages else "lead"

    deals = db.query(Deal).filter(
        (Deal.stage == stage.stage_key) |
        (Deal.stage == stage.stage_key.lower()) |
        (Deal.stage == stage.name)
    ).all()
    for d in deals:
        d.stage = target_stage

    stage_name = stage.name
    db.delete(stage)
    db.commit()

    return {"message": f"Đã xóa giai đoạn '{stage_name}' thành công. Các cơ hội liên quan đã được bảo toàn an toàn."}
