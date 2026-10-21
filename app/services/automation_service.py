import uuid
import json
from datetime import datetime, date, timedelta
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.automation import AutomationRule, AutomationLog
from app.models.task import Task
from app.models.notification import Notification
from app.models.user import User
from app.models.deal import Deal
from app.models.lead import Lead
from app.schemas.automation import CreateAutomationRuleDTO, UpdateAutomationRuleDTO, AutomationRuleDTO, AutomationLogDTO


class AutomationService:
    """
    S7-09: Động cơ Quy tắc Tự động hóa IF–THEN (Automation Rules Engine).
    Thực thi linh hoạt khi có sự kiện thay đổi trạng thái hoặc điều kiện thời gian.
    Hành động: Tạo nhiệm vụ, gửi thông báo in-app, điều chuyển người phụ trách.
    """

    @staticmethod
    def get_rules(db: Session, skip: int = 0, limit: int = 100) -> Tuple[List[AutomationRuleDTO], int]:
        query = db.query(AutomationRule)
        total = query.count()
        rules = query.order_by(AutomationRule.created_at.desc()).offset(skip).limit(limit).all()
        dto_list = []
        for r in rules:
            cond = None
            if r.conditions:
                try:
                    cond = json.loads(r.conditions) if isinstance(r.conditions, str) else r.conditions
                except Exception:
                    cond = r.conditions

            act_cfg = None
            if r.action_config:
                try:
                    act_cfg = json.loads(r.action_config) if isinstance(r.action_config, str) else r.action_config
                except Exception:
                    act_cfg = r.action_config

            dto_list.append(AutomationRuleDTO(
                id=r.id,
                name=r.name,
                description=r.description,
                isActive=r.is_active,
                triggerEntity=r.trigger_entity,
                triggerEvent=r.trigger_event,
                conditions=cond,
                actionType=r.action_type,
                actionConfig=act_cfg,
                createdAt=r.created_at.isoformat() if r.created_at else None,
                updatedAt=r.updated_at.isoformat() if r.updated_at else None,
            ))
        return dto_list, total

    @staticmethod
    def create_rule(db: Session, dto: CreateAutomationRuleDTO) -> AutomationRuleDTO:
        cond_str = json.dumps(dto.conditions) if isinstance(dto.conditions, (dict, list)) else (dto.conditions or "")
        act_str = json.dumps(dto.actionConfig) if isinstance(dto.actionConfig, (dict, list)) else (dto.actionConfig or "")

        rule = AutomationRule(
            id=str(uuid.uuid4()),
            name=dto.name,
            description=dto.description,
            is_active=dto.isActive,
            trigger_entity=dto.triggerEntity,
            trigger_event=dto.triggerEvent,
            conditions=cond_str,
            action_type=dto.actionType,
            action_config=act_str,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(rule)
        db.commit()
        db.refresh(rule)

        return AutomationRuleDTO(
            id=rule.id,
            name=rule.name,
            description=rule.description,
            isActive=rule.is_active,
            triggerEntity=rule.trigger_entity,
            triggerEvent=rule.trigger_event,
            conditions=dto.conditions,
            actionType=rule.action_type,
            actionConfig=dto.actionConfig,
            createdAt=rule.created_at.isoformat(),
            updatedAt=rule.updated_at.isoformat(),
        )

    @staticmethod
    def toggle_rule(db: Session, rule_id: str) -> AutomationRuleDTO:
        rule = db.query(AutomationRule).filter(AutomationRule.id == rule_id).first()
        if not rule:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy quy tắc tự động hóa.")
        rule.is_active = not rule.is_active
        rule.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(rule)

        cond = json.loads(rule.conditions) if rule.conditions and rule.conditions.startswith("{") else rule.conditions
        act_cfg = json.loads(rule.action_config) if rule.action_config and rule.action_config.startswith("{") else rule.action_config

        return AutomationRuleDTO(
            id=rule.id,
            name=rule.name,
            description=rule.description,
            isActive=rule.is_active,
            triggerEntity=rule.trigger_entity,
            triggerEvent=rule.trigger_event,
            conditions=cond,
            actionType=rule.action_type,
            actionConfig=act_cfg,
            createdAt=rule.created_at.isoformat(),
            updatedAt=rule.updated_at.isoformat(),
        )

    @staticmethod
    def delete_rule(db: Session, rule_id: str) -> bool:
        rule = db.query(AutomationRule).filter(AutomationRule.id == rule_id).first()
        if not rule:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy quy tắc.")
        db.delete(rule)
        db.commit()
        return True

    @staticmethod
    def get_logs(db: Session, rule_id: Optional[str] = None, skip: int = 0, limit: int = 100) -> Tuple[List[AutomationLogDTO], int]:
        query = db.query(AutomationLog)
        if rule_id:
            query = query.filter(AutomationLog.rule_id == rule_id)
        total = query.count()
        logs = query.order_by(AutomationLog.executed_at.desc()).offset(skip).limit(limit).all()

        dto_list = [
            AutomationLogDTO(
                id=log.id,
                ruleId=log.rule_id,
                ruleName=log.rule_name,
                triggerEvent=log.trigger_event,
                entityType=log.entity_type,
                entityId=log.entity_id,
                actionType=log.action_type,
                status=log.status,
                details=log.details,
                executedAt=log.executed_at.isoformat(),
            )
            for log in logs
        ]
        return dto_list, total

    @classmethod
    def evaluate_and_execute(
        cls,
        db: Session,
        trigger_entity: str,
        trigger_event: str,
        entity_id: str,
        record_data: Dict[str, Any],
        actor_user: Optional[User] = None,
    ):
        """
        Kích hoạt bộ kiểm tra và thực thi các quy tắc tự động hóa IF-THEN tương ứng.
        """
        rules = db.query(AutomationRule).filter(
            AutomationRule.is_active == True,
            AutomationRule.trigger_entity == trigger_entity,
            AutomationRule.trigger_event == trigger_event,
        ).all()

        for rule in rules:
            match = True
            # Kiểm tra điều kiện
            if rule.conditions:
                try:
                    cond = json.loads(rule.conditions) if isinstance(rule.conditions, str) else rule.conditions
                    if isinstance(cond, dict):
                        field = cond.get("field")
                        op = cond.get("operator", "equals")
                        expected = cond.get("value")
                        actual = record_data.get(field)

                        if op == "equals":
                            if str(actual).lower() != str(expected).lower():
                                match = False
                        elif op == "contains":
                            if str(expected).lower() not in str(actual).lower():
                                match = False
                except Exception:
                    pass

            if not match:
                continue

            # Thực thi hành động
            log_status = "success"
            details = ""
            try:
                act_cfg = json.loads(rule.action_config) if isinstance(rule.action_config, str) else rule.action_config
                if not isinstance(act_cfg, dict):
                    act_cfg = {}

                if rule.action_type == "create_task":
                    # Tạo nhiệm vụ
                    task_title = act_cfg.get("title", f"Nhiệm vụ tự động cho {trigger_entity} {entity_id}")
                    # Định dạng placeholder {title}, {quote_number}
                    for k, v in record_data.items():
                        task_title = task_title.replace(f"{{{k}}}", str(v))

                    due_days = int(act_cfg.get("due_days", 2))
                    assignee_id = act_cfg.get("assignee_id") or record_data.get("owner_id") or record_data.get("assigned_user_id") or (actor_user.id if actor_user else "admin")

                    task = Task(
                        id=str(uuid.uuid4()),
                        title=task_title,
                        description=act_cfg.get("description", "Nhiệm vụ được tạo tự động bởi quy tắc IF–THEN."),
                        priority=act_cfg.get("priority", "medium"),
                        status="pending",
                        due_date=date.today() + timedelta(days=due_days),
                        creator_id=actor_user.id if actor_user else assignee_id,
                        assignee_id=assignee_id,
                        deal_id=entity_id if trigger_entity == "deal" else None,
                        created_at=datetime.utcnow(),
                    )
                    db.add(task)
                    details = f"Đã tự động tạo nhiệm vụ '{task_title}' gán cho {assignee_id}."

                elif rule.action_type == "send_notification":
                    # Gửi thông báo
                    notif_title = act_cfg.get("title", f"Thông báo tự động: {rule.name}")
                    notif_desc = act_cfg.get("description", f"Hệ thống tự động kích hoạt quy tắc {rule.name}")
                    for k, v in record_data.items():
                        notif_title = notif_title.replace(f"{{{k}}}", str(v))
                        notif_desc = notif_desc.replace(f"{{{k}}}", str(v))

                    recipient_id = act_cfg.get("user_id") or record_data.get("owner_id") or record_data.get("assigned_user_id") or (actor_user.id if actor_user else "admin")

                    link = f"/{trigger_entity}s"
                    if trigger_entity == "deal":
                        link = "/deals"
                    elif trigger_entity == "quotation":
                        link = "/quotes/approvals"

                    notif = Notification(
                        id=str(uuid.uuid4()),
                        user_id=recipient_id,
                        type="automation_rule",
                        title=notif_title,
                        description=notif_desc,
                        target_type=trigger_entity,
                        target_id=entity_id,
                        link_url=link,
                        is_read=False,
                        created_at=datetime.utcnow(),
                    )
                    db.add(notif)
                    details = f"Đã gửi thông báo '{notif_title}' tới người dùng {recipient_id}."

                elif rule.action_type == "change_owner":
                    new_owner_id = act_cfg.get("new_owner_id")
                    if new_owner_id:
                        if trigger_entity == "deal":
                            deal = db.query(Deal).filter(Deal.id == entity_id).first()
                            if deal:
                                deal.owner_id = new_owner_id
                                details = f"Đã chuyển chủ sở hữu deal {entity_id} sang {new_owner_id}."
                        elif trigger_entity == "lead":
                            lead = db.query(Lead).filter(Lead.id == entity_id).first()
                            if lead:
                                lead.assigned_user_id = new_owner_id
                                details = f"Đã chuyển người phụ trách lead {entity_id} sang {new_owner_id}."

                db.commit()

            except Exception as exc:
                db.rollback()
                log_status = "failed"
                details = f"Lỗi thực thi action {rule.action_type}: {str(exc)}"

            # Ghi log thực thi
            log = AutomationLog(
                id=str(uuid.uuid4()),
                rule_id=rule.id,
                rule_name=rule.name,
                trigger_event=f"{trigger_entity}.{trigger_event}",
                entity_type=trigger_entity,
                entity_id=entity_id,
                action_type=rule.action_type,
                status=log_status,
                details=details,
                executed_at=datetime.utcnow(),
            )
            db.add(log)
            db.commit()
