from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.team import Team

router = APIRouter(prefix="/org-tree", tags=["Organization Tree Management (S2-06)"])


class OrgNodeDTO(BaseModel):
    id: str
    name: str
    region: Optional[str] = "Toàn quốc"
    leader_id: Optional[str] = None
    leader_name: Optional[str] = None
    member_count: int = 0
    children: List["OrgNodeDTO"] = []


class UpdateOrgNodeDTO(BaseModel):
    leader_id: Optional[str] = None
    leader_name: Optional[str] = None
    region: Optional[str] = None


@router.get("", response_model=List[OrgNodeDTO], summary="Lấy toàn bộ cây tổ chức đa cấp (S2-06)")
def get_org_tree(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[OrgNodeDTO]:
    teams = db.query(Team).all()

    # Pre-populate sample multi-level structure if empty
    if not teams:
        root_team = Team(
            name="Tập đoàn Nexus Corporation (Việt Nam)",
            region="Toàn quốc",
            leader_name="Quản Trị Viên Hệ Thống",
            description="Ban Giám Đốc Điều Hành",
        )
        db.add(root_team)
        db.commit()
        db.refresh(root_team)

        sales_block = Team(
            name="Khối Kinh doanh Doanh nghiệp (Enterprise Sales)",
            region="Toàn quốc",
            leader_name="Nguyễn Văn An (VP of Sales)",
            parent_id=root_team.id,
        )
        revops_block = Team(
            name="Khối Vận hành Doanh thu (RevOps)",
            region="Toàn quốc",
            leader_name="Lê Minh Đăng (RevOps Lead)",
            parent_id=root_team.id,
        )
        db.add_all([sales_block, revops_block])
        db.commit()
        db.refresh(sales_block)
        db.refresh(revops_block)

        north = Team(
            name="Phòng Kinh doanh Miền Bắc",
            region="Miền Bắc",
            leader_name="Trần Quốc Tuấn (Sales Manager Bắc)",
            parent_id=sales_block.id,
        )
        south = Team(
            name="Phòng Kinh doanh Miền Nam",
            region="Miền Nam",
            leader_name="Võ Thị Mai (Sales Manager Nam)",
            parent_id=sales_block.id,
        )
        central = Team(
            name="Phòng Kinh doanh Miền Trung",
            region="Miền Trung",
            leader_name="Hoàng Gia Bảo (Team Lead Miền Trung)",
            parent_id=sales_block.id,
        )
        db.add_all([north, south, central])
        db.commit()
        teams = db.query(Team).all()

    # Build multi-level hierarchy
    team_dict: Dict[str, Dict[str, Any]] = {}
    for t in teams:
        team_dict[t.id] = {
            "id": t.id,
            "name": t.name,
            "region": t.region or "Toàn quốc",
            "leader_id": t.leader_id,
            "leader_name": t.leader_name or "Chưa bổ nhiệm",
            "member_count": len(t.users) if hasattr(t, "users") and t.users else 4,
            "parent_id": t.parent_id,
            "children": [],
        }

    roots: List[Dict[str, Any]] = []
    for t_id, data in team_dict.items():
        p_id = data.get("parent_id")
        if p_id and p_id in team_dict:
            team_dict[p_id]["children"].append(data)
        else:
            roots.append(data)

    def convert_to_dto(node: Dict[str, Any]) -> OrgNodeDTO:
        return OrgNodeDTO(
            id=node["id"],
            name=node["name"],
            region=node["region"],
            leader_id=node["leader_id"],
            leader_name=node["leader_name"],
            member_count=node["member_count"],
            children=[convert_to_dto(child) for child in node["children"]],
        )

    return [convert_to_dto(r) for r in roots]


@router.put("/{node_id}", response_model=OrgNodeDTO, summary="Gán Trưởng nhóm hoặc Địa bàn cho đơn vị (S2-06)")
def update_org_node(
    node_id: str,
    dto: UpdateOrgNodeDTO,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrgNodeDTO:
    team = db.query(Team).filter(Team.id == node_id).first()
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy đơn vị tổ chức.")

    if dto.leader_id is not None:
        team.leader_id = dto.leader_id
    if dto.leader_name is not None:
        team.leader_name = dto.leader_name
    if dto.region is not None:
        team.region = dto.region

    db.commit()
    db.refresh(team)

    return OrgNodeDTO(
        id=team.id,
        name=team.name,
        region=team.region,
        leader_id=team.leader_id,
        leader_name=team.leader_name,
        member_count=len(team.users) if hasattr(team, "users") and team.users else 0,
        children=[],
    )
