"""Tests for the message queue."""

import pytest
from infrastructure.adapters.queue import (
    MessageQueue,
    TaskPriority,
)


class TestMessageQueue:
    def setup_method(self):
        self.queue = MessageQueue()

    @pytest.mark.asyncio
    async def test_enqueue_task(self):
        task_id = await self.queue.enqueue(
            task_type="send_email",
            payload={"to": "a@b.com"},
            org_id="org1",
        )
        assert task_id is not None
        status = self.queue.get_task_status(task_id)
        assert status["status"] == "pending"

    @pytest.mark.asyncio
    async def test_process_with_handler(self):
        self.queue.register_handler("test_task", lambda payload: {"done": True})
        task_id = await self.queue.enqueue(
            task_type="test_task",
            payload={"data": "hello"},
            org_id="org1",
        )
        result = await self.queue.process(task_id)
        assert result == {"done": True}
        status = self.queue.get_task_status(task_id)
        assert status["status"] == "completed"

    @pytest.mark.asyncio
    async def test_process_missing_handler(self):
        task_id = await self.queue.enqueue(
            task_type="unknown_task",
            payload={},
            org_id="org1",
        )
        result = await self.queue.process(task_id)
        assert "error" in result
        status = self.queue.get_task_status(task_id)
        assert status["status"] == "failed"

    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        call_count = 0

        def failing_handler(payload):
            nonlocal call_count
            call_count += 1
            raise RuntimeError("fail")

        self.queue.register_handler("fail_task", failing_handler)
        task_id = await self.queue.enqueue(
            task_type="fail_task",
            payload={},
            org_id="org1",
            max_attempts=3,
        )
        # Process once — should retry
        await self.queue.process(task_id)
        status = self.queue.get_task_status(task_id)
        assert status["status"] == "retry"

    @pytest.mark.asyncio
    async def test_priority_ordering(self):
        await self.queue.enqueue(
            task_type="t",
            payload={},
            org_id="org1",
            priority=TaskPriority.LOW,
        )
        high_id = await self.queue.enqueue(
            task_type="t",
            payload={},
            org_id="org1",
            priority=TaskPriority.CRITICAL,
        )
        # Queue should be sorted by priority descending
        assert self.queue._queue[0].id == high_id

    @pytest.mark.asyncio
    async def test_status_transitions(self):
        self.queue.register_handler("t", lambda p: {"ok": True})
        task_id = await self.queue.enqueue(task_type="t", payload={}, org_id="org1")
        assert self.queue.get_task_status(task_id)["status"] == "pending"
        await self.queue.process(task_id)
        assert self.queue.get_task_status(task_id)["status"] == "completed"

    @pytest.mark.asyncio
    async def test_get_org_tasks(self):
        await self.queue.enqueue("t", {}, "org1")
        await self.queue.enqueue("t", {}, "org2")
        tasks = self.queue.get_org_tasks("org1")
        assert len(tasks) == 1

    def test_get_task_status_missing(self):
        assert self.queue.get_task_status("nonexistent") is None
