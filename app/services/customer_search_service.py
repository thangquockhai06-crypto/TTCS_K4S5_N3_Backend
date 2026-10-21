from typing import List, Optional, Sequence, Tuple
import uuid

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.core.customer_search import normalize_text
from app.models.category import Category
from app.models.customer import Customer
from app.models.saved_filter import SavedFilter
from app.models.user import User
from app.repositories.customer_repository import CustomerRepository
from app.schemas.customer_search import (
    CustomerFilterDefinition,
    SavedFilterCreateDTO,
    SavedFilterDTO,
    SavedFilterUpdateDTO,
)


VALID_STATUSES = {"lead", "prospect", "active", "inactive"}
VALID_INDUSTRIES = {"TECH", "FINANCE", "MANUFACTURING", "RETAIL", "REAL_ESTATE"}
VALID_COMPANY_SIZES = {"SMB", "MID_MARKET", "ENTERPRISE"}
VALID_SORTS = {"name", "created_at", "status", "owner", "industry", "company_size", "region"}


def split_values(values: Optional[Sequence[str]]) -> List[str]:
    result: List[str] = []
    for raw_value in values or []:
        result.extend(part.strip() for part in raw_value.split(",") if part.strip())
    return list(dict.fromkeys(result))


def _validate_values(
    db: Session,
    user: User,
    definition: CustomerFilterDefinition,
    allow_stale_owner: bool = False,
) -> Tuple[CustomerFilterDefinition, List[str], bool]:
    statuses = [value.lower() for value in split_values(definition.status)]
    invalid_statuses = sorted(set(statuses) - VALID_STATUSES)
    if invalid_statuses:
        raise HTTPException(status_code=422, detail=f"status không hợp lệ: {', '.join(invalid_statuses)}")

    industries = [value.upper() for value in split_values(definition.industry)]
    configured_industries = {
        row[0].upper()
        for row in db.query(Category.code).filter(func.lower(Category.type) == "industry").all()
    }
    invalid_industries = sorted(set(industries) - (VALID_INDUSTRIES | configured_industries))
    if invalid_industries:
        raise HTTPException(status_code=422, detail=f"industry không hợp lệ: {', '.join(invalid_industries)}")

    company_sizes = [value.upper() for value in split_values(definition.company_size)]
    invalid_sizes = sorted(set(company_sizes) - VALID_COMPANY_SIZES)
    if invalid_sizes:
        raise HTTPException(status_code=422, detail=f"companySize không hợp lệ: {', '.join(invalid_sizes)}")

    regions = [value.strip() for value in split_values(definition.region)]
    if any(len(value) > 100 for value in regions):
        raise HTTPException(status_code=422, detail="region không được vượt quá 100 ký tự.")

    owner_values = split_values(definition.owner)
    owner_ids: List[str] = []
    include_unassigned = False
    for owner in owner_values:
        owner_lower = owner.lower()
        if owner_lower == "me":
            owner_ids.append(user.id)
        elif owner_lower == "unassigned":
            include_unassigned = True
        else:
            owner_ids.append(owner)
    owner_ids = list(dict.fromkeys(owner_ids))
    if owner_ids:
        existing_ids = {row[0] for row in db.query(User.id).filter(User.id.in_(owner_ids)).all()}
        missing_ids = sorted(set(owner_ids) - existing_ids)
        if missing_ids and not allow_stale_owner:
            raise HTTPException(status_code=422, detail=f"owner không tồn tại: {', '.join(missing_ids)}")
        owner_ids = [owner_id for owner_id in owner_ids if owner_id in existing_ids]
        if owner_values and not owner_ids and not include_unassigned:
            owner_ids = ["__stale_saved_filter_owner__"]

    sort = definition.sort.lower()
    if sort not in VALID_SORTS:
        raise HTTPException(status_code=422, detail=f"sort không hợp lệ. Cho phép: {', '.join(sorted(VALID_SORTS))}")

    normalized = definition.model_copy(
        update={
            "status": statuses,
            "industry": industries,
            "company_size": company_sizes,
            "region": regions,
            "owner": owner_values,
            "sort": sort,
        }
    )
    return normalized, owner_ids, include_unassigned


def _merge_query(
    saved: Optional[dict],
    q: Optional[str],
    status_values: Optional[Sequence[str]],
    industries: Optional[Sequence[str]],
    company_sizes: Optional[Sequence[str]],
    regions: Optional[Sequence[str]],
    owners: Optional[Sequence[str]],
    sort: Optional[str],
    descending: Optional[bool],
    skip: Optional[int],
    limit: Optional[int],
) -> CustomerFilterDefinition:
    saved = saved or {}
    return CustomerFilterDefinition(
        q=q if q is not None else saved.get("q"),
        status=list(status_values) if status_values is not None else saved.get("status", []),
        industry=list(industries) if industries is not None else saved.get("industry", []),
        companySize=list(company_sizes) if company_sizes is not None else saved.get("companySize", saved.get("company_size", [])),
        region=list(regions) if regions is not None else saved.get("region", []),
        owner=list(owners) if owners is not None else saved.get("owner", []),
        sort=sort if sort is not None else saved.get("sort", "created_at"),
        descending=descending if descending is not None else saved.get("descending", True),
        skip=skip if skip is not None else saved.get("skip", 0),
        limit=limit if limit is not None else saved.get("limit", 50),
    )


class CustomerSearchService:
    def __init__(self, db: Session):
        self.db = db

    def list_customers(
        self,
        user: User,
        saved_filter_id: Optional[str] = None,
        q: Optional[str] = None,
        status_values: Optional[Sequence[str]] = None,
        industries: Optional[Sequence[str]] = None,
        company_sizes: Optional[Sequence[str]] = None,
        regions: Optional[Sequence[str]] = None,
        owners: Optional[Sequence[str]] = None,
        sort: Optional[str] = None,
        descending: Optional[bool] = None,
        skip: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> Tuple[List[Customer], int]:
        saved_definition = None
        if saved_filter_id:
            saved = self.db.query(SavedFilter).filter(
                SavedFilter.id == saved_filter_id,
                SavedFilter.user_id == user.id,
            ).first()
            if not saved:
                raise HTTPException(status_code=404, detail="Không tìm thấy saved filter.")
            saved_definition = saved.filter_definition

        definition = _merge_query(
            saved_definition,
            q,
            status_values,
            industries,
            company_sizes,
            regions,
            owners,
            sort,
            descending,
            skip,
            limit,
        )
        definition, owner_ids, include_unassigned = _validate_values(
            self.db, user, definition, allow_stale_owner=bool(saved_filter_id)
        )
        return CustomerRepository.get_all(
            db=self.db,
            user=user,
            search=definition.q,
            status=definition.status,
            industry=definition.industry,
            company_size=definition.company_size,
            region=definition.region,
            owner_ids=owner_ids,
            include_unassigned=include_unassigned,
            sort=definition.sort,
            descending=definition.descending,
            skip=definition.skip,
            limit=definition.limit,
        )

    def list_saved_filters(self, user: User) -> List[SavedFilterDTO]:
        filters = self.db.query(SavedFilter).filter(SavedFilter.user_id == user.id).order_by(SavedFilter.name.asc()).all()
        return [_saved_filter_dto(item) for item in filters]

    def get_saved_filter(self, filter_id: str, user: User) -> SavedFilterDTO:
        return _saved_filter_dto(self._get_saved_filter(filter_id, user))

    def create_saved_filter(self, dto: SavedFilterCreateDTO, user: User) -> SavedFilterDTO:
        self._validate_saved_definition(dto.filter_definition, user)
        if self.db.query(SavedFilter).filter(SavedFilter.user_id == user.id).count() >= settings.MAX_SAVED_CUSTOMER_FILTERS:
            raise HTTPException(status_code=409, detail="Đã đạt số lượng saved filter tối đa.")
        self._ensure_unique_name(user, dto.name)
        if dto.is_default:
            self.db.query(SavedFilter).filter(SavedFilter.user_id == user.id).update({SavedFilter.is_default: False})
        item = SavedFilter(
            id=str(uuid.uuid4()),
            user_id=user.id,
            name=dto.name.strip(),
            filter_definition=dto.filter_definition.model_dump(by_alias=True),
            is_default=dto.is_default,
        )
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return _saved_filter_dto(item)

    def update_saved_filter(self, filter_id: str, dto: SavedFilterUpdateDTO, user: User) -> SavedFilterDTO:
        item = self._get_saved_filter(filter_id, user)
        if dto.name is not None:
            self._ensure_unique_name(user, dto.name, exclude_id=item.id)
            item.name = dto.name.strip()
        if dto.filter_definition is not None:
            self._validate_saved_definition(dto.filter_definition, user)
            item.filter_definition = dto.filter_definition.model_dump(by_alias=True)
        if dto.is_default:
            self.db.query(SavedFilter).filter(SavedFilter.user_id == user.id).update({SavedFilter.is_default: False})
        if dto.is_default is not None:
            item.is_default = dto.is_default
        self.db.commit()
        self.db.refresh(item)
        return _saved_filter_dto(item)

    def delete_saved_filter(self, filter_id: str, user: User) -> None:
        item = self._get_saved_filter(filter_id, user)
        self.db.delete(item)
        self.db.commit()

    def _validate_saved_definition(self, definition: CustomerFilterDefinition, user: User) -> None:
        _validate_values(self.db, user, definition)

    def _get_saved_filter(self, filter_id: str, user: User) -> SavedFilter:
        item = self.db.query(SavedFilter).filter(SavedFilter.id == filter_id, SavedFilter.user_id == user.id).first()
        if not item:
            raise HTTPException(status_code=404, detail="Không tìm thấy saved filter.")
        return item

    def _ensure_unique_name(self, user: User, name: str, exclude_id: Optional[str] = None) -> None:
        normalized_name = normalize_text(name)
        if not normalized_name:
            raise HTTPException(status_code=422, detail="Tên saved filter không được để trống.")
        query = self.db.query(SavedFilter).filter(
            SavedFilter.user_id == user.id,
            func.lower(SavedFilter.name) == normalized_name,
        )
        if exclude_id:
            query = query.filter(SavedFilter.id != exclude_id)
        if query.first():
            raise HTTPException(status_code=409, detail="Tên saved filter đã tồn tại.")


def _saved_filter_dto(item: SavedFilter) -> SavedFilterDTO:
    return SavedFilterDTO(
        id=item.id,
        name=item.name,
        filter_definition=item.filter_definition,
        is_default=item.is_default,
        created_at=item.created_at.isoformat() if item.created_at else None,
        updated_at=item.updated_at.isoformat() if item.updated_at else None,
    )
