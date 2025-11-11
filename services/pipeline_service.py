"""Pipeline automation helpers."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Iterable

from loguru import logger
from sqlalchemy.orm import Session

from database.models import Client
from database.models_crm import PipelineStage, ClientPipeline, ActionType, SalesPipeline


STATUS_BY_STAGE: Dict[str, str] = {
    "Первичный контакт": "new",
    "Консультация": "qualified",
    "Принимают решение": "qualified",
    "Куплена услуга": "client",
    "Активный клиент": "client",
    "Завершен": "client",
    "Неактивен": "inactive",
}


@dataclass(slots=True)
class PipelineRule:
    """Automation rule for stage transitions."""

    name: str
    to_stage: str
    action_types: Iterable[str]
    from_stage: Optional[str] = None
    min_stage_order: Optional[int] = None
    next_contact_hours: Optional[int] = None
    notes_template: str = "Автоматическое перемещение после действия {action_type}"


PIPELINE_RULES: tuple[PipelineRule, ...] = (
    PipelineRule(
        name="contact_to_consultation",
        from_stage="Первичный контакт",
        to_stage="Консультация",
        action_types={
            ActionType.CALL.value,
            ActionType.MESSAGE.value,
            ActionType.CONSULTATION.value,
            ActionType.CONSULTATION_SCHEDULED.value,
            ActionType.MEETING.value,
        },
        next_contact_hours=24,
        notes_template="Контакт с клиентом ({action_type}) → этап 'Консультация'",
    ),
    PipelineRule(
        name="consultation_to_decision",
        from_stage="Консультация",
        to_stage="Принимают решение",
        action_types={
            ActionType.PROPOSAL_SENT.value,
            ActionType.EMAIL.value,
            ActionType.MEETING.value,
        },
        next_contact_hours=48,
        notes_template="Отправлено предложение ({action_type}) → этап 'Принимают решение'",
    ),
    PipelineRule(
        name="decision_to_purchased",
        from_stage="Принимают решение",
        to_stage="Куплена услуга",
        action_types={
            ActionType.PAYMENT_RECEIVED.value,
            ActionType.PROGRAM_ASSIGNED.value,
        },
        next_contact_hours=None,
        notes_template="Оплата/программа ({action_type}) → этап 'Куплена услуга'",
    ),
)


class PipelineAutomation:
    """Encapsulates pipeline stage automation and reminders."""

    def __init__(self, db: Session):
        self.db = db
        self._stages_by_name: Dict[str, PipelineStage] = {}
        self._stages_by_id: Dict[int, PipelineStage] = {}

    # ------------------------------------------------------------------ helpers
    def _get_stage_by_name(self, name: str) -> Optional[PipelineStage]:
        if not name:
            return None
        if name not in self._stages_by_name:
            stage = (
                self.db.query(PipelineStage)
                .filter(
                    PipelineStage.name == name,
                    PipelineStage.is_active == True,  # noqa: E712
                )
                .first()
            )
            if stage:
                self._stages_by_name[name] = stage
                self._stages_by_id[stage.id] = stage
        return self._stages_by_name.get(name)

    def _get_stage_by_id(self, stage_id: Optional[int]) -> Optional[PipelineStage]:
        if not stage_id:
            return None
        if stage_id not in self._stages_by_id:
            stage = self.db.query(PipelineStage).filter(PipelineStage.id == stage_id).first()
            if stage:
                self._stages_by_id[stage_id] = stage
                self._stages_by_name[stage.name] = stage
        return self._stages_by_id.get(stage_id)

    def _update_client_status_for_stage(self, client: Client, stage: PipelineStage) -> None:
        target_status = STATUS_BY_STAGE.get(stage.name)
        if target_status and client.status != target_status:
            client.status = target_status

    def schedule_follow_up(self, client: Client, base_time: datetime, hours: Optional[int]) -> None:
        if hours is None:
            return
        if hours <= 0:
            client.next_contact_at = None
            return
        client.next_contact_at = base_time + timedelta(hours=hours)

    # ---------------------------------------------------------------- movement
    def move_client_to_stage(
        self,
        client: Client,
        target_stage: PipelineStage,
        moved_by: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> bool:
        """Move client to provided stage, recording history."""
        if not client or not target_stage:
            return False

        current_stage = self._get_stage_by_id(client.pipeline_stage_id)
        if current_stage and current_stage.id == target_stage.id:
            return False

        # prevent moving backwards unless explicitly requested
        if current_stage and current_stage.order is not None and target_stage.order is not None:
            if target_stage.order < current_stage.order:
                logger.debug(
                    "Skipping stage downgrade for client %s: %s -> %s",
                    client.id,
                    current_stage.name,
                    target_stage.name,
                )
                return False

        # Enforce exclusivity: only one active pipeline per client at a time.
        # Determine pipeline_id of stage (None means Default/global).
        target_pipeline_id = getattr(target_stage, "pipeline_id", None)

        # Update client current stage
        client.pipeline_stage_id = target_stage.id
        self._update_client_status_for_stage(client, target_stage)

        pipeline_entry = ClientPipeline(
            client_id=client.id,
            stage_id=target_stage.id,
            pipeline_id=target_pipeline_id,
            moved_by=moved_by,
            notes=notes,
            moved_at=datetime.utcnow(),
        )
        self.db.add(pipeline_entry)
        logger.info(
            "Client %s moved to pipeline stage '%s'%s",
            client.id,
            target_stage.name,
            f" (by user {moved_by})" if moved_by else " (automation)",
        )
        return True

    def move_client_to_stage_by_name(
        self,
        client: Client,
        stage_name: str,
        moved_by: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> bool:
        stage = self._get_stage_by_name(stage_name)
        if not stage:
            logger.warning("Pipeline stage '%s' not found or inactive", stage_name)
            return False
        return self.move_client_to_stage(client, stage, moved_by=moved_by, notes=notes)

    # ---------------------------------------------------------------- automation
    def handle_action_created(
        self,
        client: Optional[Client],
        action,
        created_by: Optional[int] = None,
        follow_up_hours_override: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Apply automation when a client action is recorded.

        Returns a dict with automation results for API consumers.
        """
        result: Dict[str, Any] = {
            "stage_changed": False,
            "new_stage": None,
            "next_contact_at": None,
            "applied_rule": None,
        }

        if not client or not action:
            return result

        action_type = getattr(action, "action_type", None)
        action_date = getattr(action, "action_date", None) or datetime.utcnow()

        # Update last contact timestamp
        if not client.last_contact_at or action_date > client.last_contact_at:
            client.last_contact_at = action_date

        current_stage = self._get_stage_by_id(client.pipeline_stage_id)
        applied_rule: Optional[PipelineRule] = None

        for rule in PIPELINE_RULES:
            if action_type not in rule.action_types:
                continue

            if rule.from_stage:
                if not current_stage or current_stage.name != rule.from_stage:
                    continue

            if rule.min_stage_order is not None:
                if not current_stage or current_stage.order is None:
                    continue
                if current_stage.order < rule.min_stage_order:
                    continue

            target_stage = self._get_stage_by_name(rule.to_stage)
            if not target_stage:
                continue

            moved = self.move_client_to_stage(
                client,
                target_stage,
                moved_by=created_by,
                notes=rule.notes_template.format(action_type=action_type),
            )
            if moved:
                result["stage_changed"] = True
                result["new_stage"] = target_stage.name
                applied_rule = rule
                current_stage = target_stage  # Update for subsequent rules
            break

        # Follow-up scheduling
        follow_up_hours = (
            follow_up_hours_override
            if follow_up_hours_override is not None
            else (applied_rule.next_contact_hours if applied_rule else None)
        )

        if follow_up_hours is not None:
            self.schedule_follow_up(client, action_date, follow_up_hours)
            result["next_contact_at"] = (
                client.next_contact_at.isoformat() if client.next_contact_at else None
            )

        if applied_rule:
            result["applied_rule"] = applied_rule.name

        return result


