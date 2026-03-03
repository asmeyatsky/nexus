"""Tests for the audit logging service."""

from uuid import uuid4
from datetime import datetime, timedelta
from infrastructure.adapters.audit import (
    AuditLogService,
    AuditAction,
    AuditResourceType,
    _hash_pii,
)


class TestAuditLogService:
    def setup_method(self):
        self.svc = AuditLogService()

    def test_create_log_entry(self):
        entry = self.svc.log(
            action=AuditAction.CREATE,
            resource_type=AuditResourceType.ACCOUNT,
            user_id=uuid4(),
            resource_id=uuid4(),
            success=True,
        )
        assert entry.action == AuditAction.CREATE
        assert entry.success is True
        assert entry.checksum != ""

    def test_integrity_verification(self):
        entry = self.svc.log(
            action=AuditAction.UPDATE,
            resource_type=AuditResourceType.CONTACT,
            user_id=uuid4(),
        )
        assert self.svc.verify_integrity(entry.id) is True

    def test_integrity_fails_for_unknown_id(self):
        assert self.svc.verify_integrity(uuid4()) is False

    def test_query_by_user(self):
        uid = uuid4()
        self.svc.log(
            action=AuditAction.CREATE,
            resource_type=AuditResourceType.ACCOUNT,
            user_id=uid,
        )
        self.svc.log(
            action=AuditAction.READ,
            resource_type=AuditResourceType.ACCOUNT,
            user_id=uuid4(),  # different user
        )
        results = self.svc.query(user_id=uid)
        assert len(results) == 1

    def test_query_by_resource_type(self):
        self.svc.log(
            action=AuditAction.CREATE,
            resource_type=AuditResourceType.ACCOUNT,
        )
        self.svc.log(
            action=AuditAction.CREATE,
            resource_type=AuditResourceType.CONTACT,
        )
        results = self.svc.query(resource_type=AuditResourceType.ACCOUNT)
        assert len(results) == 1

    def test_query_by_date_range(self):
        self.svc.log(
            action=AuditAction.CREATE,
            resource_type=AuditResourceType.LEAD,
        )
        results = self.svc.query(
            start_date=datetime.now() - timedelta(minutes=1),
            end_date=datetime.now() + timedelta(minutes=1),
        )
        assert len(results) >= 1

    def test_pii_hashing(self):
        hashed = _hash_pii("alice@example.com")
        assert hashed is not None
        assert hashed != "alice@example.com"
        assert len(hashed) == 16

    def test_pii_hashing_none(self):
        assert _hash_pii(None) is None

    def test_log_with_pii_fields(self):
        entry = self.svc.log(
            action=AuditAction.LOGIN,
            resource_type=AuditResourceType.USER,
            user_email="alice@example.com",
            ip_address="192.168.1.1",
        )
        # PII should be hashed
        assert entry.user_email != "alice@example.com"
        assert entry.ip_address != "192.168.1.1"
