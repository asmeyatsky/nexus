"""
Workflow Automation Builder

Architectural Intent:
- Visual workflow automation builder
- Trigger-based automation
- Action sequences with conditions
"""

from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4
from enum import Enum


class WorkflowTriggerType(Enum):
    RECORD_CREATED = "record_created"
    RECORD_UPDATED = "record_updated"
    FIELD_CHANGED = "field_changed"
    STAGE_CHANGED = "stage_changed"
    LEAD_STATUS_CHANGED = "lead_status_changed"
    SCHEDULED = "scheduled"
    WEBHOOK_RECEIVED = "webhook_received"


class WorkflowActionType(Enum):
    CREATE_RECORD = "create_record"
    UPDATE_RECORD = "update_record"
    DELETE_RECORD = "delete_record"
    SEND_EMAIL = "send_email"
    SEND_NOTIFICATION = "send_notification"
    ASSIGN_OWNER = "assign_owner"
    ADD_TO_CAMPAIGN = "add_to_campaign"
    CREATE_TASK = "create_task"
    WEBHOOK_CALL = "webhook_call"
    WAIT = "wait"


class ConditionOperator(Enum):
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    IS_EMPTY = "is_empty"
    IS_NOT_EMPTY = "is_not_empty"


@dataclass
class WorkflowCondition:
    field: str
    operator: ConditionOperator
    value: Any


@dataclass
class WorkflowAction:
    type: WorkflowActionType
    config: Dict[str, Any]
    conditions: List[WorkflowCondition] = field(default_factory=list)


@dataclass
class WorkflowTrigger:
    type: WorkflowTriggerType
    object_type: str
    conditions: List[WorkflowCondition] = field(default_factory=list)


@dataclass
class Workflow:
    id: str
    name: str
    description: str
    is_active: bool = False
    trigger: Optional[WorkflowTrigger] = None
    actions: List[WorkflowAction] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    org_id: str = ""


class WorkflowEngine:
    """Workflow automation engine."""

    def __init__(self):
        self._workflows: Dict[str, Workflow] = {}
        self._action_handlers: Dict[WorkflowActionType, Callable] = {}
        self._execution_log: List[Dict] = []

    def register_action_handler(
        self, action_type: WorkflowActionType, handler: Callable
    ):
        self._action_handlers[action_type] = handler

    def create_workflow(
        self,
        name: str,
        description: str,
        org_id: str,
    ) -> Workflow:
        workflow = Workflow(
            id=str(uuid4()),
            name=name,
            description=description,
            org_id=org_id,
        )
        self._workflows[workflow.id] = workflow
        return workflow

    def add_trigger(
        self,
        workflow_id: str,
        trigger_type: WorkflowTriggerType,
        object_type: str,
        conditions: List[WorkflowCondition] = None,
    ) -> bool:
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return False

        workflow.trigger = WorkflowTrigger(
            type=trigger_type,
            object_type=object_type,
            conditions=conditions or [],
        )
        return True

    def add_action(
        self,
        workflow_id: str,
        action_type: WorkflowActionType,
        config: Dict[str, Any],
        conditions: List[WorkflowCondition] = None,
    ) -> bool:
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return False

        action = WorkflowAction(
            type=action_type,
            config=config,
            conditions=conditions or [],
        )
        workflow.actions.append(action)
        return True

    def activate(self, workflow_id: str) -> bool:
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return False

        if not workflow.trigger or not workflow.actions:
            return False

        workflow.is_active = True
        workflow.updated_at = datetime.now()
        return True

    def deactivate(self, workflow_id: str) -> bool:
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return False

        workflow.is_active = False
        return True

    async def execute(self, workflow_id: str, trigger_data: Dict[str, Any]) -> Dict:
        workflow = self._workflows.get(workflow_id)
        if not workflow or not workflow.is_active:
            return {"error": "Workflow not found or inactive"}

        execution_result = {
            "workflow_id": workflow_id,
            "workflow_name": workflow.name,
            "trigger_data": trigger_data,
            "actions_executed": [],
            "success": True,
        }

        for action in workflow.actions:
            if not self._check_conditions(action.conditions, trigger_data):
                continue

            handler = self._action_handlers.get(action.type)
            if handler:
                try:
                    result = await handler(action.config, trigger_data)
                    execution_result["actions_executed"].append(
                        {
                            "type": action.type.value,
                            "success": True,
                            "result": result,
                        }
                    )
                except Exception as e:
                    execution_result["actions_executed"].append(
                        {
                            "type": action.type.value,
                            "success": False,
                            "error": str(e),
                        }
                    )
                    execution_result["success"] = False

        self._execution_log.append(execution_result)
        return execution_result

    def _check_conditions(
        self, conditions: List[WorkflowCondition], data: Dict
    ) -> bool:
        if not conditions:
            return True

        for condition in conditions:
            field_value = data.get(condition.field)

            if condition.operator == ConditionOperator.EQUALS:
                if field_value != condition.value:
                    return False
            elif condition.operator == ConditionOperator.NOT_EQUALS:
                if field_value == condition.value:
                    return False
            elif condition.operator == ConditionOperator.CONTAINS:
                if condition.value not in str(field_value):
                    return False
            elif condition.operator == ConditionOperator.IS_EMPTY:
                if field_value:
                    return False
            elif condition.operator == ConditionOperator.IS_NOT_EMPTY:
                if not field_value:
                    return False

        return True


workflow_engine = WorkflowEngine()


def _safe_format(template: str, data: Dict) -> str:
    """Safe string formatting that only allows simple key substitution."""
    import re

    def replacer(match):
        key = match.group(1)
        return str(data.get(key, match.group(0)))

    return re.sub(r"\{(\w+)\}", replacer, template)


async def send_email_action(config: Dict, trigger_data: Dict) -> Dict:
    """Send email action handler."""
    to = _safe_format(config.get("to", ""), trigger_data)
    subject = _safe_format(config.get("subject", ""), trigger_data)
    _body = _safe_format(config.get("body", ""), trigger_data)

    print(f"Sending email to {to}: {subject}")

    return {"sent": True, "to": to}


async def create_task_action(config: Dict, trigger_data: Dict) -> Dict:
    """Create task action handler."""
    subject = _safe_format(config.get("subject", ""), trigger_data)
    _due_date = config.get("due_date", "")
    _owner_id = config.get("owner_id", "")

    print(f"Creating task: {subject}")

    return {"created": True, "subject": subject}


workflow_engine.register_action_handler(
    WorkflowActionType.SEND_EMAIL, send_email_action
)
workflow_engine.register_action_handler(
    WorkflowActionType.CREATE_TASK, create_task_action
)
