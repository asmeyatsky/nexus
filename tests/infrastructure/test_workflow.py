"""Tests for the workflow automation engine."""

import pytest
from infrastructure.adapters.workflow import (
    WorkflowEngine,
    WorkflowTriggerType,
    WorkflowActionType,
    WorkflowCondition,
    ConditionOperator,
)


class TestWorkflowEngine:
    def setup_method(self):
        self.engine = WorkflowEngine()

    def test_create_workflow(self):
        wf = self.engine.create_workflow(
            name="Test WF", description="A test workflow", org_id="org1"
        )
        assert wf.name == "Test WF"
        assert wf.is_active is False

    def test_activate_requires_trigger_and_actions(self):
        wf = self.engine.create_workflow("WF", "desc", "org1")
        assert self.engine.activate(wf.id) is False

    def test_activate_with_trigger_and_action(self):
        wf = self.engine.create_workflow("WF", "desc", "org1")
        self.engine.add_trigger(wf.id, WorkflowTriggerType.RECORD_CREATED, "account")
        self.engine.add_action(
            wf.id,
            WorkflowActionType.SEND_EMAIL,
            {"to": "a@b.com", "subject": "Hi"},
        )
        assert self.engine.activate(wf.id) is True
        assert self.engine._workflows[wf.id].is_active is True

    def test_deactivate_workflow(self):
        wf = self.engine.create_workflow("WF", "desc", "org1")
        self.engine.add_trigger(wf.id, WorkflowTriggerType.RECORD_CREATED, "account")
        self.engine.add_action(wf.id, WorkflowActionType.SEND_EMAIL, {"to": "a@b.com"})
        self.engine.activate(wf.id)
        assert self.engine.deactivate(wf.id) is True
        assert self.engine._workflows[wf.id].is_active is False

    def test_condition_equals(self):
        conditions = [WorkflowCondition("status", ConditionOperator.EQUALS, "new")]
        assert self.engine._check_conditions(conditions, {"status": "new"}) is True
        assert self.engine._check_conditions(conditions, {"status": "closed"}) is False

    def test_condition_contains(self):
        conditions = [WorkflowCondition("name", ConditionOperator.CONTAINS, "Corp")]
        assert self.engine._check_conditions(conditions, {"name": "Acme Corp"}) is True

    def test_condition_is_empty(self):
        conditions = [WorkflowCondition("phone", ConditionOperator.IS_EMPTY, None)]
        assert self.engine._check_conditions(conditions, {"phone": ""}) is True
        assert self.engine._check_conditions(conditions, {"phone": "555"}) is False

    @pytest.mark.asyncio
    async def test_execute_workflow(self):
        wf = self.engine.create_workflow("WF", "desc", "org1")
        self.engine.add_trigger(wf.id, WorkflowTriggerType.RECORD_CREATED, "account")

        async def mock_action(config, trigger_data):
            return {"sent": True}

        self.engine.register_action_handler(WorkflowActionType.SEND_EMAIL, mock_action)
        self.engine.add_action(wf.id, WorkflowActionType.SEND_EMAIL, {"to": "a@b.com"})
        self.engine.activate(wf.id)

        result = await self.engine.execute(wf.id, {"name": "New Account"})
        assert result["success"] is True
        assert len(result["actions_executed"]) == 1

    @pytest.mark.asyncio
    async def test_execute_inactive_workflow(self):
        wf = self.engine.create_workflow("WF", "desc", "org1")
        result = await self.engine.execute(wf.id, {})
        assert "error" in result

    def test_empty_conditions_pass(self):
        assert self.engine._check_conditions([], {}) is True
