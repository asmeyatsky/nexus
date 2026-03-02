"""
Enterprise Audit Logging

Architectural Intent:
- Immutable audit logs for compliance (SOC 2, GDPR)
- Cloud Audit Logs integration
- Log retention policies
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from uuid import UUID, uuid4
from enum import Enum
import json
import hashlib
import threading


class AuditAction(Enum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    EXPORT = "export"
    LOGIN_FAILED = "login_failed"
    PERMISSION_DENIED = "permission_denied"
    API_ACCESS = "api_access"


class AuditResourceType(Enum):
    ACCOUNT = "account"
    CONTACT = "contact"
    OPPORTUNITY = "opportunity"
    LEAD = "lead"
    CASE = "case"
    USER = "user"
    ROLE = "role"
    ORGANIZATION = "organization"
    TEAM = "team"
    REPORT = "report"
    EXPORT = "export"
    SETTINGS = "settings"


@dataclass
class AuditLog:
    id: UUID
    timestamp: datetime
    action: AuditAction
    resource_type: AuditResourceType
    resource_id: Optional[UUID]
    user_id: Optional[UUID]
    user_email: Optional[str]
    org_id: Optional[UUID]
    ip_address: Optional[str]
    user_agent: Optional[str]
    request_id: Optional[str]
    changes: Optional[Dict[str, Any]]
    old_values: Optional[Dict[str, Any]]
    new_values: Optional[Dict[str, Any]]
    success: bool
    error_message: Optional[str]
    metadata: Dict[str, Any] = field(default_factory=dict)
    checksum: str = ""

    def __post_init__(self):
        if not self.checksum:
            self.checksum = self._calculate_checksum()

    def _calculate_checksum(self) -> str:
        data = f"{self.timestamp}{self.action.value}{self.user_id}{self.resource_type.value}{self.resource_id}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]


def _hash_pii(value: Optional[str]) -> Optional[str]:
    """Hash PII values for storage while preserving lookup capability."""
    if not value:
        return value
    return hashlib.sha256(value.encode()).hexdigest()[:16]


class AuditLogService:
    """Enterprise audit logging service with Cloud Audit Logs integration."""

    def __init__(self, project_id: str = None):
        self._logs: List[AuditLog] = []
        self._lock = threading.Lock()
        self.project_id = project_id
        self._callbacks: List[callable] = []

    def log(
        self,
        action: AuditAction,
        resource_type: AuditResourceType,
        user_id: UUID = None,
        user_email: str = None,
        org_id: UUID = None,
        resource_id: UUID = None,
        ip_address: str = None,
        user_agent: str = None,
        request_id: str = None,
        changes: Dict[str, Any] = None,
        old_values: Dict[str, Any] = None,
        new_values: Dict[str, Any] = None,
        success: bool = True,
        error_message: str = None,
        metadata: Dict[str, Any] = None,
    ) -> AuditLog:
        log_entry = AuditLog(
            id=uuid4(),
            timestamp=datetime.now(),
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            user_id=user_id,
            user_email=_hash_pii(user_email),
            org_id=org_id,
            ip_address=_hash_pii(ip_address),
            user_agent=user_agent,
            request_id=request_id,
            changes=changes,
            old_values=old_values,
            new_values=new_values,
            success=success,
            error_message=error_message,
            metadata=metadata or {},
        )

        with self._lock:
            self._logs.append(log_entry)

            for callback in self._callbacks:
                try:
                    callback(log_entry)
                except Exception as e:
                    print(f"Audit callback error: {e}")

        self._publish_to_cloud_log(log_entry)

        return log_entry

    def _publish_to_cloud_log(self, log: AuditLog):
        """Publish to Cloud Audit Logs."""
        if not self.project_id:
            return

        try:
            import google.cloud.logging

            client = google.cloud.logging.Client()
            logger = client.logger("audit_logs")

            logger.info(
                json.dumps(
                    {
                        "audit": {
                            "action": log.action.value,
                            "resource_type": log.resource_type.value,
                            "resource_id": str(log.resource_id)
                            if log.resource_id
                            else None,
                            "user_id": str(log.user_id) if log.user_id else None,
                            "user_email": log.user_email,
                            "org_id": str(log.org_id) if log.org_id else None,
                            "ip_address": log.ip_address,
                            "success": log.success,
                        }
                    }
                ),
                resource={
                    "type": "audited_resource",
                    "labels": {
                        "project_id": self.project_id,
                    },
                },
            )
        except Exception as e:
            print(f"Cloud logging error: {e}")

    def register_callback(self, callback: callable):
        """Register callback for async processing."""
        self._callbacks.append(callback)

    def query(
        self,
        user_id: UUID = None,
        org_id: UUID = None,
        resource_type: AuditResourceType = None,
        action: AuditAction = None,
        start_date: datetime = None,
        end_date: datetime = None,
        limit: int = 1000,
    ) -> List[AuditLog]:
        results = []

        with self._lock:
            for log in self._logs:
                if user_id and log.user_id != user_id:
                    continue
                if org_id and log.org_id != org_id:
                    continue
                if resource_type and log.resource_type != resource_type:
                    continue
                if action and log.action != action:
                    continue
                if start_date and log.timestamp < start_date:
                    continue
                if end_date and log.timestamp > end_date:
                    continue

                results.append(log)

        return results[-limit:]

    def get_user_activity(self, user_id: UUID, days: int = 30) -> Dict[str, int]:
        start_date = datetime.now() - timedelta(days=days)
        logs = self.query(user_id=user_id, start_date=start_date)

        activity = {}
        for log in logs:
            action = log.action.value
            activity[action] = activity.get(action, 0) + 1

        return activity

    def get_resource_history(
        self, resource_id: UUID, resource_type: AuditResourceType
    ) -> List[AuditLog]:
        return self.query(resource_type=resource_type, resource_id=resource_id)

    def export_logs(
        self,
        start_date: datetime,
        end_date: datetime,
        format: str = "json",
    ) -> List[Dict]:
        logs = self.query(start_date=start_date, end_date=end_date, limit=100000)

        if format == "json":
            return [
                {
                    "id": str(entry.id),
                    "timestamp": entry.timestamp.isoformat(),
                    "action": entry.action.value,
                    "resource_type": entry.resource_type.value,
                    "resource_id": str(entry.resource_id)
                    if entry.resource_id
                    else None,
                    "user_id": str(entry.user_id) if entry.user_id else None,
                    "user_email": entry.user_email,
                    "org_id": str(entry.org_id) if entry.org_id else None,
                    "ip_address": entry.ip_address,
                    "success": entry.success,
                    "changes": entry.changes,
                    "checksum": entry.checksum,
                }
                for entry in logs
            ]

        return logs

    def verify_integrity(self, log_id: UUID) -> bool:
        with self._lock:
            for log in self._logs:
                if log.id == log_id:
                    expected = log._calculate_checksum()
                    return log.checksum == expected
        return False


audit_service = AuditLogService()
