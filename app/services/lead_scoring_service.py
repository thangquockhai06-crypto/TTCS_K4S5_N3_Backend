"""
LeadScoringService: Tầng xử lý nghiệp vụ Cấu hình chấm điểm Lead (SCRUM-48 / Sprint 4).
Hỗ trợ:
- Quản lý quy tắc chấm điểm động (INDUSTRY, COMPANY_SIZE, SOURCE, INTEREST_LEVEL).
- Quản lý cấu hình ngưỡng phân loại nhiệt độ Lead (Hot/Warm/Cold).
- Engine tự động tính điểm theo thuộc tính Lead.
- Tác vụ tính toán lại điểm số hàng loạt (Batch Recalculate).
"""
import time
import uuid
from datetime import datetime
from typing import List, Tuple, Optional

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.lead import Lead
from app.models.lead_scoring import LeadScoringRule, LeadScoringSettings
from app.models.user import User
from app.schemas.lead_scoring import (
    ScoringRuleCreate,
    ScoringRuleUpdate,
    ScoringSettingsUpdate,
    BatchRecalculateResponse,
)


class LeadScoringService:
    @staticmethod
    def get_or_create_settings(db: Session) -> LeadScoringSettings:
        """Lấy bản ghi cấu hình ngưỡng (Singleton ID=1) hoặc tạo mới với giá trị mặc định."""
        settings = db.query(LeadScoringSettings).filter(LeadScoringSettings.id == 1).first()
        if not settings:
            settings = LeadScoringSettings(
                id=1,
                hot_threshold=70,
                warm_threshold=40,
                updated_at=datetime.utcnow(),
            )
            db.add(settings)
            db.commit()
            db.refresh(settings)
        return settings

    @classmethod
    def update_settings(
        cls,
        db: Session,
        update_data: ScoringSettingsUpdate,
        current_user: User,
    ) -> LeadScoringSettings:
        """Cập nhật ngưỡng Hot/Warm/Cold của hệ thống."""
        settings = cls.get_or_create_settings(db)
        settings.hot_threshold = update_data.hot_threshold
        settings.warm_threshold = update_data.warm_threshold
        settings.updated_by = current_user.id
        settings.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(settings)
        return settings

    @staticmethod
    def get_rules(
        db: Session,
        criteria_type: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> List[LeadScoringRule]:
        """Lấy danh sách các quy tắc chấm điểm có bộ lọc."""
        query = db.query(LeadScoringRule)
        if criteria_type:
            query = query.filter(LeadScoringRule.criteria_type == criteria_type.upper())
        if is_active is not None:
            query = query.filter(LeadScoringRule.is_active == is_active)
        return query.order_by(LeadScoringRule.created_at.asc()).all()

    @staticmethod
    def create_rule(
        db: Session,
        rule_data: ScoringRuleCreate,
        current_user: User,
    ) -> LeadScoringRule:
        """Tạo mới một quy tắc chấm điểm Lead."""
        rule = LeadScoringRule(
            id=str(uuid.uuid4()),
            criteria_type=rule_data.criteria_type.upper(),
            criteria_value=rule_data.criteria_value.strip(),
            score=rule_data.score,
            is_active=rule_data.is_active,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(rule)
        db.commit()
        db.refresh(rule)
        return rule

    @staticmethod
    def update_rule(
        db: Session,
        rule_id: str,
        rule_data: ScoringRuleUpdate,
        current_user: User,
    ) -> LeadScoringRule:
        """Cập nhật một quy tắc chấm điểm Lead theo ID."""
        rule = db.query(LeadScoringRule).filter(LeadScoringRule.id == rule_id).first()
        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy quy tắc chấm điểm với ID: {rule_id}",
            )

        if rule_data.criteria_type is not None:
            rule.criteria_type = rule_data.criteria_type.upper()
        if rule_data.criteria_value is not None:
            rule.criteria_value = rule_data.criteria_value.strip()
        if rule_data.score is not None:
            rule.score = rule_data.score
        if rule_data.is_active is not None:
            rule.is_active = rule_data.is_active

        rule.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(rule)
        return rule

    @staticmethod
    def delete_rule(
        db: Session,
        rule_id: str,
        current_user: User,
    ) -> None:
        """Xóa một quy tắc chấm điểm Lead theo ID."""
        rule = db.query(LeadScoringRule).filter(LeadScoringRule.id == rule_id).first()
        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy quy tắc chấm điểm với ID: {rule_id}",
            )
        db.delete(rule)
        db.commit()

    @staticmethod
    def calculate_lead_score(
        lead: Lead,
        rules: List[LeadScoringRule],
        settings: LeadScoringSettings,
    ) -> Tuple[int, str]:
        """
        Tính điểm và phân loại nhiệt độ Lead:
        - So khớp các thuộc tính của Lead với toàn bộ rule đang kích hoạt.
        - Phân loại HOT (>= hot_threshold), WARM (>= warm_threshold), COLD (< warm_threshold).
        """
        total_score = 0

        lead_industry = (lead.industry or "").strip().lower()
        lead_company_size = (lead.company_size or "").strip().lower()
        lead_source = (lead.source or "").strip().lower()
        lead_interest = (lead.interest_level or "").strip().lower()
        lead_need = (lead.interest_need or "").strip().lower()

        for rule in rules:
            if not rule.is_active:
                continue

            r_val = rule.criteria_value.strip().lower()
            c_type = rule.criteria_type.upper()

            # 1. So khớp Ngành nghề (INDUSTRY)
            if c_type == "INDUSTRY" and lead_industry:
                if r_val == lead_industry or (len(r_val) >= 3 and (r_val in lead_industry or lead_industry in r_val)):
                    total_score += rule.score

            # 2. So khớp Quy mô doanh nghiệp (COMPANY_SIZE)
            elif c_type == "COMPANY_SIZE" and lead_company_size:
                if r_val == lead_company_size or r_val in lead_company_size or lead_company_size in r_val:
                    total_score += rule.score

            # 3. So khớp Nguồn thu thập (SOURCE)
            elif c_type == "SOURCE" and lead_source:
                if r_val == lead_source or (len(r_val) >= 3 and (r_val in lead_source or lead_source in r_val)):
                    total_score += rule.score

            # 4. So khớp Mức độ quan tâm (INTEREST_LEVEL)
            elif c_type == "INTEREST_LEVEL":
                if lead_interest and (r_val == lead_interest or r_val in lead_interest):
                    total_score += rule.score
                elif lead_need and r_val in lead_need:
                    total_score += rule.score

        # Phân loại theo ngưỡng nhiệt độ
        if total_score >= settings.hot_threshold:
            temperature = "HOT"
        elif total_score >= settings.warm_threshold:
            temperature = "WARM"
        else:
            temperature = "COLD"

        return total_score, temperature

    @classmethod
    def apply_scoring_to_lead(
        cls,
        db: Session,
        lead: Lead,
        commit: bool = False,
    ) -> Lead:
        """Tự động tính và cập nhật điểm số & nhiệt độ cho một bản ghi Lead."""
        rules = db.query(LeadScoringRule).filter(LeadScoringRule.is_active == True).all()
        settings = cls.get_or_create_settings(db)

        score, temperature = cls.calculate_lead_score(lead, rules, settings)
        lead.score = score
        lead.temperature = temperature

        if commit:
            db.commit()
            db.refresh(lead)

        return lead

    @classmethod
    def recalculate_all_leads(cls, db: Session) -> BatchRecalculateResponse:
        """
        Tính toán lại toàn bộ điểm số cho tất cả Lead đang hoạt động (Batch Recalculate):
        - Quét danh sách lead chưa gộp (status != 'MERGED').
        - Cập nhật đồng loạt và trả về báo cáo số lượng phân loại.
        """
        start_time = time.time()
        rules = db.query(LeadScoringRule).filter(LeadScoringRule.is_active == True).all()
        settings = cls.get_or_create_settings(db)

        leads = db.query(Lead).filter(Lead.status != "MERGED").all()

        hot_count = 0
        warm_count = 0
        cold_count = 0

        for lead in leads:
            score, temperature = cls.calculate_lead_score(lead, rules, settings)
            lead.score = score
            lead.temperature = temperature

            if temperature == "HOT":
                hot_count += 1
            elif temperature == "WARM":
                warm_count += 1
            else:
                cold_count += 1

        db.commit()
        execution_time = round(time.time() - start_time, 3)

        return BatchRecalculateResponse(
            total_leads_processed=len(leads),
            hot_count=hot_count,
            warm_count=warm_count,
            cold_count=cold_count,
            execution_time_seconds=execution_time,
        )

    calculate_lead_score_sync = calculate_lead_score


# Function alias theo đặc tả SCRUM-48 AC
calculate_lead_score_sync = LeadScoringService.calculate_lead_score
