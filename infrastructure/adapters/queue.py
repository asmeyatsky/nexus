"""
Message Queue (Cloud Tasks / PubSub)

Architectural Intent:
- Async task processing
- Event-driven architecture
- Background job processing
"""

from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4
from enum import Enum
import asyncio
import json
import base64
import threading


class TaskStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY = "retry"


class TaskPriority(Enum):
    LOW = 1
    NORMAL = 5
    HIGH = 10
    CRITICAL = 20


@dataclass
class Task:
    id: str
    task_type: str
    payload: Dict[str, Any]
    status: TaskStatus
    priority: TaskPriority
    org_id: str
    user_id: Optional[str]
    attempts: int = 0
    max_attempts: int = 3
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    result: Optional[Dict] = None


class MessageQueue:
    """Async message queue with task processing."""

    def __init__(self):
        self._tasks: Dict[str, Task] = {}
        self._handlers: Dict[str, Callable] = {}
        self._queue: List[Task] = []
        self._lock = threading.Lock()
        self._processing = False

    def register_handler(self, task_type: str, handler: Callable):
        self._handlers[task_type] = handler

    async def enqueue(
        self,
        task_type: str,
        payload: Dict[str, Any],
        org_id: str,
        user_id: str = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        max_attempts: int = 3,
    ) -> str:
        task = Task(
            id=str(uuid4()),
            task_type=task_type,
            payload=payload,
            status=TaskStatus.PENDING,
            priority=priority,
            org_id=org_id,
            user_id=user_id,
            max_attempts=max_attempts,
        )

        with self._lock:
            self._tasks[task.id] = task
            self._queue.append(task)
            self._queue.sort(key=lambda t: t.priority.value, reverse=True)

        return task.id

    async def process(self, task_id: str) -> Dict[str, Any]:
        task = self._tasks.get(task_id)
        if not task:
            return {"error": "Task not found"}

        task.status = TaskStatus.PROCESSING
        task.started_at = datetime.now()

        handler = self._handlers.get(task.task_type)
        if not handler:
            task.status = TaskStatus.FAILED
            task.error = f"No handler for task type: {task.task_type}"
            return {"error": task.error}

        try:
            if asyncio.iscoroutinefunction(handler):
                result = await handler(task.payload)
            else:
                result = handler(task.payload)

            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            task.result = result
            return result

        except Exception as e:
            task.attempts += 1
            if task.attempts < task.max_attempts:
                task.status = TaskStatus.RETRY
                task.error = str(e)
            else:
                task.status = TaskStatus.FAILED
                task.error = str(e)
            return {"error": str(e)}

    async def process_all(self, max_concurrent: int = 10):
        semaphore = asyncio.Semaphore(max_concurrent)

        async def process_with_semaphore(task: Task):
            async with semaphore:
                await self.process(task.id)

        while True:
            with self._lock:
                pending = [t for t in self._queue if t.status == TaskStatus.PENDING]

            if not pending:
                break

            await asyncio.gather(
                *[process_with_semaphore(t) for t in pending[:max_concurrent]]
            )

    def get_task_status(self, task_id: str) -> Optional[Dict]:
        task = self._tasks.get(task_id)
        if not task:
            return None

        return {
            "id": task.id,
            "type": task.task_type,
            "status": task.status.value,
            "attempts": task.attempts,
            "error": task.error,
            "result": task.result,
            "created_at": task.created_at.isoformat(),
        }

    def get_org_tasks(self, org_id: str, status: TaskStatus = None) -> List[Dict]:
        tasks = [t for t in self._tasks.values() if t.org_id == org_id]
        if status:
            tasks = [t for t in tasks if t.status == status]
        return [
            {
                "id": t.id,
                "type": t.task_type,
                "status": t.status.value,
                "created_at": t.created_at.isoformat(),
            }
            for t in tasks
        ]


message_queue = MessageQueue()


async def send_email_handler(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handler for sending emails."""
    to = payload.get("to")
    subject = payload.get("subject")
    body = payload.get("body")

    print(f"Sending email to {to}: {subject}")

    return {"sent": True, "to": to}


async def sync_to_analytics_handler(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handler for syncing data to analytics."""
    entity_type = payload.get("entity_type")
    entity_id = payload.get("entity_id")

    print(f"Syncing {entity_type}:{entity_id} to analytics")

    return {"synced": True}


message_queue.register_handler("send_email", send_email_handler)
message_queue.register_handler("sync_to_analytics", sync_to_analytics_handler)


class PubSubPublisher:
    """Google Cloud Pub/Sub publisher."""

    def __init__(self, project_id: str = None):
        self.project_id = project_id
        self._client = None

    async def publish(self, topic: str, message: Dict):
        if not self.project_id:
            print(f"Pub/Sub mock: Publishing to {topic}")
            return True

        try:
            from google.cloud import pubsub_v1

            publisher = pubsub_v1.PublisherClient()
            topic_path = publisher.topic_path(self.project_id, topic)

            message_bytes = json.dumps(message).encode("utf-8")
            future = publisher.publish(topic_path, message_bytes)
            future.result()
            return True
        except Exception as e:
            print(f"Pub/Sub publish error: {e}")
            return False


pubsub_publisher = PubSubPublisher()
