"""Tests for the RBAC service."""

from uuid import uuid4
from infrastructure.adapters.rbac import (
    RBACService,
    Permission,
    RoleType,
    ROLE_PERMISSIONS,
)


class TestRBACService:
    def setup_method(self):
        self.svc = RBACService()

    def test_create_org(self):
        org = self.svc.create_org("Acme")
        assert org.name == "Acme"
        assert org.is_active is True

    def test_create_team(self):
        org = self.svc.create_org("Acme")
        team = self.svc.create_team("Sales", org.id)
        assert team.name == "Sales"
        assert team.org_id == org.id

    def test_create_user(self):
        org = self.svc.create_org("Acme")
        user = self.svc.create_user("alice@acme.com", "Alice", org.id)
        assert user.email == "alice@acme.com"
        assert user.role_type == RoleType.SALES_REP

    def test_admin_has_all_permissions(self):
        org = self.svc.create_org("Acme")
        user = self.svc.create_user("admin@acme.com", "Admin", org.id, RoleType.ADMIN)
        perms = self.svc.get_user_permissions(user.id)
        assert Permission.ACCOUNTS_DELETE in perms
        assert Permission.USERS_MANAGE in perms
        assert Permission.CASES_RESOLVE in perms

    def test_read_only_limited_permissions(self):
        org = self.svc.create_org("Acme")
        user = self.svc.create_user(
            "viewer@acme.com", "Viewer", org.id, RoleType.READ_ONLY
        )
        perms = self.svc.get_user_permissions(user.id)
        assert Permission.ACCOUNTS_VIEW in perms
        assert Permission.ACCOUNTS_CREATE not in perms
        assert Permission.ACCOUNTS_DELETE not in perms

    def test_has_permission_positive(self):
        org = self.svc.create_org("Acme")
        user = self.svc.create_user("rep@acme.com", "Rep", org.id, RoleType.SALES_REP)
        assert self.svc.has_permission(user.id, Permission.ACCOUNTS_CREATE) is True

    def test_has_permission_negative(self):
        org = self.svc.create_org("Acme")
        user = self.svc.create_user("rep@acme.com", "Rep", org.id, RoleType.SALES_REP)
        assert self.svc.has_permission(user.id, Permission.USERS_MANAGE) is False

    def test_has_permission_unknown_user(self):
        assert self.svc.has_permission(uuid4(), Permission.ACCOUNTS_VIEW) is False

    def test_can_access_record_via_direct_access(self):
        org = self.svc.create_org("Acme")
        user = self.svc.create_user("u@acme.com", "U", org.id)
        record_id = uuid4()
        self.svc.grant_record_access("account", record_id, [user.id])
        assert self.svc.can_access_record(user.id, "account", record_id) is True

    def test_can_access_record_with_sharing_rule(self):
        org = self.svc.create_org("Acme")
        user = self.svc.create_user("u@acme.com", "U", org.id)
        record_id = uuid4()
        self.svc.create_sharing_rule("account", org.id, "read", user_id=user.id)
        assert self.svc.can_access_record(user.id, "account", record_id) is True

    def test_grant_and_revoke_record_access(self):
        org = self.svc.create_org("Acme")
        user = self.svc.create_user("u@acme.com", "U", org.id)
        record_id = uuid4()
        self.svc.grant_record_access("account", record_id, [user.id])
        assert self.svc.can_access_record(user.id, "account", record_id) is True
        self.svc.revoke_record_access("account", record_id, user.id)
        assert self.svc.can_access_record(user.id, "account", record_id) is False

    def test_custom_permissions(self):
        org = self.svc.create_org("Acme")
        user = self.svc.create_user(
            "custom@acme.com", "Custom", org.id, RoleType.CUSTOM
        )
        user.custom_permissions.add(Permission.ACCOUNTS_VIEW)
        perms = self.svc.get_user_permissions(user.id)
        assert Permission.ACCOUNTS_VIEW in perms
        assert Permission.ACCOUNTS_CREATE not in perms

    def test_add_user_to_team(self):
        org = self.svc.create_org("Acme")
        team = self.svc.create_team("Sales", org.id)
        user = self.svc.create_user("u@acme.com", "U", org.id)
        self.svc.add_user_to_team(user.id, team.id)
        assert team.id in user.team_ids
        assert user.id in team.members

    def test_manager_has_cases_delete(self):
        perms = ROLE_PERMISSIONS[RoleType.MANAGER]
        assert Permission.CASES_DELETE in perms

    def test_support_user_has_cases_delete(self):
        perms = ROLE_PERMISSIONS[RoleType.SUPPORT_USER]
        assert Permission.CASES_DELETE in perms
