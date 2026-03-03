"""
Enterprise RBAC with Organization Hierarchy

Architectural Intent:
- Multi-tenant RBAC with organization hierarchy
- Role-based permissions at org, team, and user level
- Support for Salesforce-like sharing rules
"""

from typing import Optional, List, Set, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID, uuid4
from datetime import datetime


class Permission(Enum):
    # Account permissions
    ACCOUNTS_VIEW = "accounts:view"
    ACCOUNTS_CREATE = "accounts:create"
    ACCOUNTS_EDIT = "accounts:edit"
    ACCOUNTS_DELETE = "accounts:delete"
    ACCOUNTS_EXPORT = "accounts:export"

    # Contact permissions
    CONTACTS_VIEW = "contacts:view"
    CONTACTS_CREATE = "contacts:create"
    CONTACTS_EDIT = "contacts:edit"
    CONTACTS_DELETE = "contacts:delete"

    # Opportunity permissions
    OPPORTUNITIES_VIEW = "opportunities:view"
    OPPORTUNITIES_CREATE = "opportunities:create"
    OPPORTUNITIES_EDIT = "opportunities:edit"
    OPPORTUNITIES_DELETE = "opportunities:delete"
    OPPORTUNITIES_CLOSE = "opportunities:close"

    # Lead permissions
    LEADS_VIEW = "leads:view"
    LEADS_CREATE = "leads:create"
    LEADS_EDIT = "leads:edit"
    LEADS_CONVERT = "leads:convert"
    LEADS_DELETE = "leads:delete"

    # Case permissions
    CASES_VIEW = "cases:view"
    CASES_CREATE = "cases:create"
    CASES_EDIT = "cases:edit"
    CASES_DELETE = "cases:delete"
    CASES_ESCALATE = "cases:escalate"
    CASES_RESOLVE = "cases:resolve"

    # Admin permissions
    USERS_MANAGE = "users:manage"
    ROLES_MANAGE = "roles:manage"
    ORGS_MANAGE = "orgs:manage"
    SETTINGS_MANAGE = "settings:manage"
    AUDIT_VIEW = "audit:view"
    REPORTS_VIEW = "reports:view"
    EXPORT_DATA = "export:data"


class RoleType(Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    SALES_REP = "sales_rep"
    MARKETING_USER = "marketing_user"
    SUPPORT_USER = "support_user"
    READ_ONLY = "read_only"
    CUSTOM = "custom"


ROLE_PERMISSIONS: Dict[RoleType, Set[Permission]] = {
    RoleType.ADMIN: set(Permission),
    RoleType.MANAGER: {
        Permission.ACCOUNTS_VIEW,
        Permission.ACCOUNTS_CREATE,
        Permission.ACCOUNTS_EDIT,
        Permission.ACCOUNTS_EXPORT,
        Permission.CONTACTS_VIEW,
        Permission.CONTACTS_CREATE,
        Permission.CONTACTS_EDIT,
        Permission.OPPORTUNITIES_VIEW,
        Permission.OPPORTUNITIES_CREATE,
        Permission.OPPORTUNITIES_EDIT,
        Permission.OPPORTUNITIES_CLOSE,
        Permission.LEADS_VIEW,
        Permission.LEADS_CREATE,
        Permission.LEADS_EDIT,
        Permission.LEADS_CONVERT,
        Permission.CASES_VIEW,
        Permission.CASES_CREATE,
        Permission.CASES_EDIT,
        Permission.CASES_DELETE,
        Permission.CASES_ESCALATE,
        Permission.CASES_RESOLVE,
        Permission.USERS_MANAGE,
        Permission.REPORTS_VIEW,
        Permission.AUDIT_VIEW,
        Permission.EXPORT_DATA,
    },
    RoleType.SALES_REP: {
        Permission.ACCOUNTS_VIEW,
        Permission.ACCOUNTS_CREATE,
        Permission.ACCOUNTS_EDIT,
        Permission.CONTACTS_VIEW,
        Permission.CONTACTS_CREATE,
        Permission.CONTACTS_EDIT,
        Permission.OPPORTUNITIES_VIEW,
        Permission.OPPORTUNITIES_CREATE,
        Permission.OPPORTUNITIES_EDIT,
        Permission.LEADS_VIEW,
        Permission.LEADS_CREATE,
        Permission.LEADS_EDIT,
        Permission.LEADS_CONVERT,
        Permission.CASES_VIEW,
        Permission.REPORTS_VIEW,
    },
    RoleType.MARKETING_USER: {
        Permission.ACCOUNTS_VIEW,
        Permission.LEADS_VIEW,
        Permission.LEADS_CREATE,
        Permission.LEADS_EDIT,
        Permission.LEADS_CONVERT,
        Permission.CONTACTS_VIEW,
        Permission.OPPORTUNITIES_VIEW,
        Permission.REPORTS_VIEW,
    },
    RoleType.SUPPORT_USER: {
        Permission.ACCOUNTS_VIEW,
        Permission.CONTACTS_VIEW,
        Permission.CASES_VIEW,
        Permission.CASES_CREATE,
        Permission.CASES_EDIT,
        Permission.CASES_DELETE,
        Permission.CASES_ESCALATE,
        Permission.CASES_RESOLVE,
    },
    RoleType.READ_ONLY: {
        Permission.ACCOUNTS_VIEW,
        Permission.CONTACTS_VIEW,
        Permission.OPPORTUNITIES_VIEW,
        Permission.LEADS_VIEW,
        Permission.CASES_VIEW,
        Permission.REPORTS_VIEW,
    },
    RoleType.CUSTOM: set(),
}


@dataclass
class Organization:
    id: UUID
    name: str
    parent_org_id: Optional[UUID] = None
    org_type: str = "company"
    settings: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    is_active: bool = True

    def get_ancestor_ids(self) -> List[UUID]:
        return []


@dataclass
class Team:
    id: UUID
    name: str
    org_id: UUID
    parent_team_id: Optional[UUID] = None
    members: List[UUID] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    is_active: bool = True


@dataclass
class UserProfile:
    id: UUID
    email: str
    name: str
    org_id: UUID
    team_ids: List[UUID] = field(default_factory=list)
    role_type: RoleType = RoleType.SALES_REP
    custom_permissions: Set[Permission] = field(default_factory=set)
    is_active: bool = True
    last_login: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class SharingRule:
    id: UUID
    record_type: str
    org_id: UUID
    role_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    team_id: Optional[UUID] = None
    access_level: str = "read"
    related_org_id: Optional[UUID] = None


class RBACService:
    """Enterprise RBAC with org hierarchy and sharing rules."""

    def __init__(self):
        self._orgs: Dict[UUID, Organization] = {}
        self._teams: Dict[UUID, Team] = {}
        self._users: Dict[UUID, UserProfile] = {}
        self._sharing_rules: Dict[UUID, SharingRule] = {}
        self._record_access: Dict[str, Set[UUID]] = {}

    def create_org(self, name: str, parent_org_id: UUID = None) -> Organization:
        org = Organization(id=uuid4(), name=name, parent_org_id=parent_org_id)
        self._orgs[org.id] = org
        return org

    def create_team(self, name: str, org_id: UUID, parent_team_id: UUID = None) -> Team:
        team = Team(id=uuid4(), name=name, org_id=org_id, parent_team_id=parent_team_id)
        self._teams[team.id] = team
        return team

    def create_user(
        self,
        email: str,
        name: str,
        org_id: UUID,
        role_type: RoleType = RoleType.SALES_REP,
    ) -> UserProfile:
        user = UserProfile(
            id=uuid4(),
            email=email,
            name=name,
            org_id=org_id,
            role_type=role_type,
        )
        self._users[user.id] = user
        return user

    def add_user_to_team(self, user_id: UUID, team_id: UUID):
        user = self._users.get(user_id)
        team = self._teams.get(team_id)
        if user and team:
            if team_id not in user.team_ids:
                user.team_ids.append(team_id)
            if user_id not in team.members:
                team.members.append(user_id)

    def get_user_permissions(self, user_id: UUID) -> Set[Permission]:
        user = self._users.get(user_id)
        if not user:
            return set()

        base_permissions = ROLE_PERMISSIONS.get(user.role_type, set())
        return base_permissions | user.custom_permissions

    def has_permission(self, user_id: UUID, permission: Permission) -> bool:
        return permission in self.get_user_permissions(user_id)

    def can_access_record(
        self,
        user_id: UUID,
        record_type: str,
        record_id: UUID,
        access_level: str = "read",
    ) -> bool:
        user = self._users.get(user_id)
        if not user:
            return False

        if Permission(f"{record_type}s:delete") in self.get_user_permissions(user_id):
            return True

        record_key = f"{record_type}:{record_id}"

        if record_key in self._record_access:
            allowed_users = self._record_access[record_key]
            if user_id in allowed_users:
                return True

        for rule in self._sharing_rules.values():
            if rule.record_type != record_type:
                continue

            if rule.org_id != user.org_id:
                continue

            if rule.user_id and rule.user_id == user_id:
                return True

            if rule.team_id and rule.team_id in user.team_ids:
                return True

            if rule.role_id:
                continue

        return False

    def grant_record_access(
        self,
        record_type: str,
        record_id: UUID,
        user_ids: List[UUID],
    ):
        record_key = f"{record_type}:{record_id}"
        if record_key not in self._record_access:
            self._record_access[record_key] = set()
        self._record_access[record_key].update(user_ids)

    def revoke_record_access(self, record_type: str, record_id: UUID, user_id: UUID):
        record_key = f"{record_type}:{record_id}"
        if record_key in self._record_access:
            self._record_access[record_key].discard(user_id)

    def create_sharing_rule(
        self,
        record_type: str,
        org_id: UUID,
        access_level: str,
        user_id: UUID = None,
        team_id: UUID = None,
        role_id: UUID = None,
    ) -> SharingRule:
        rule = SharingRule(
            id=uuid4(),
            record_type=record_type,
            user_id=user_id,
            team_id=team_id,
            role_id=role_id,
            org_id=org_id,
            access_level=access_level,
        )
        self._sharing_rules[rule.id] = rule
        return rule

    def get_accessible_records(
        self,
        user_id: UUID,
        record_type: str,
    ) -> List[UUID]:
        user = self._users.get(user_id)
        if not user:
            return []

        accessible = []

        for record_id, allowed_users in self._record_access.items():
            if record_id.startswith(f"{record_type}:"):
                if user_id in allowed_users:
                    _, rid = record_id.split(":")
                    accessible.append(UUID(rid))

        return accessible


rbac_service = RBACService()
