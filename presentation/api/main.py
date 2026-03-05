"""
Nexus CRM API

Architectural Intent:
- REST API for Nexus CRM operations
- Follows presentation layer patterns
- FastAPI-based HTTP endpoints
- Tenant isolation via org_id
- RBAC permission enforcement
"""

import logging
from typing import Optional, List
from uuid import UUID as PyUUID
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field, field_validator, constr
from datetime import datetime, timedelta, timezone

from infrastructure.adapters.auth import (
    create_access_token,
    decode_token,
    user_repo,
    TokenData,
    UserCreate,
    User,
    token_revocation_store,
)
from infrastructure.config.settings import settings
from application import (
    CreateAccountCommand,
    UpdateAccountCommand,
    DeactivateAccountCommand,
    CreateContactCommand,
    UpdateContactCommand,
    CreateOpportunityCommand,
    UpdateOpportunityStageCommand,
    UpdateOpportunityCommand,
    CreateLeadCommand,
    QualifyLeadCommand,
    ConvertLeadCommand,
    CreateCaseCommand,
    UpdateCaseStatusCommand,
    ResolveCaseCommand,
    CloseCaseCommand,
    GetAccountQuery,
    ListAccountsQuery,
    GetContactQuery,
    ListContactsQuery,
    GetContactsByAccountQuery,
    GetOpportunityQuery,
    ListOpportunitiesQuery,
    GetOpenOpportunitiesQuery,
    GetLeadQuery,
    ListLeadsQuery,
    GetCaseQuery,
    ListCasesQuery,
    GetOpenCasesQuery,
    SearchAccountsQuery,
    SearchContactsQuery,
    SearchOpportunitiesQuery,
    SearchLeadsQuery,
    SearchCasesQuery,
    CreateAccountDTO,
    CreateContactDTO,
    CreateOpportunityDTO,
    CreateLeadDTO,
    CreateCaseDTO,
)
from infrastructure.config.dependency_injection import container
from infrastructure.adapters.security import (
    SecurityMiddleware,
    rate_limiter,
    ip_security,
    RateLimitTier,
)
from infrastructure.adapters.rbac import (
    Permission,
    RoleType,
    rbac_service,
)
from infrastructure.adapters.monitoring import (
    TracingMiddleware,
    HealthChecker,
    metrics,
    setup_logging,
)
from starlette.responses import Response, PlainTextResponse

logger = logging.getLogger(__name__)

openapi_tags = [
    {"name": "Auth", "description": "Authentication and user management"},
    {"name": "Accounts", "description": "Account CRUD operations"},
    {"name": "Contacts", "description": "Contact CRUD operations"},
    {
        "name": "Opportunities",
        "description": "Sales pipeline and opportunity management",
    },
    {"name": "Leads", "description": "Lead management and conversion"},
    {"name": "Cases", "description": "Customer support case management"},
    {"name": "Reports", "description": "Reporting and aggregation endpoints"},
    {"name": "Analytics", "description": "Advanced analytics and forecasting"},
    {"name": "System", "description": "Health checks, metrics, and system endpoints"},
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup/shutdown lifecycle."""
    setup_logging()

    # Initialize DB session for container if using database
    if container._use_database:
        try:
            from infrastructure.database import async_session  # noqa: F401

            logger.info("Database mode enabled — using SQLAlchemy repositories")
        except Exception as e:
            logger.warning(f"Database init failed, falling back to in-memory: {e}")
    else:
        logger.info("In-memory mode — no DATABASE_URL configured")

    # Register event subscribers at startup
    try:
        from application.event_handlers import register_all_subscribers

        register_all_subscribers(event_bus)
        logger.info("Event subscribers registered")
    except ImportError:
        pass

    # Seed default admin user if no users exist
    if not user_repo._users:
        try:
            admin = await user_repo.create_user(
                UserCreate(
                    email="admin@nexus.local",
                    password="Admin123!@#$",
                    name="Admin",
                    role="admin",
                    org_id="00000000-0000-0000-0000-000000000000",
                )
            )
            logger.info(f"Seeded admin user: admin@nexus.local (id={admin.id})")
        except Exception as e:
            logger.warning(f"Failed to seed admin user: {e}")

    yield


health_checker = HealthChecker(
    version="1.0.0",
    db_url=settings.database_url,
    redis_url=settings.redis_url,
)


app = FastAPI(
    title="Nexus CRM API",
    description="Salesforce Replacement CRM API",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
    openapi_tags=openapi_tags,
    lifespan=lifespan,
)


@app.exception_handler(ValueError)
async def value_error_handler(request, exc: ValueError):
    msg = str(exc).lower()
    if "not found" in msg:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
    return JSONResponse(status_code=400, content={"detail": str(exc)})


# CORS middleware
if settings.cors_allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins.split(","),
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "Accept", "X-Request-ID"],
    )

app.add_middleware(
    SecurityMiddleware, rate_limiter=rate_limiter, ip_security=ip_security
)
app.add_middleware(TracingMiddleware)
rate_limiter.configure("default", RateLimitTier.STANDARD)
ip_security.enable()

# Brute force protection
_login_attempts: dict[str, list[float]] = {}
MAX_LOGIN_ATTEMPTS = 5
LOGIN_LOCKOUT_SECONDS = 900  # 15 minutes

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> TokenData:
    token = credentials.credentials
    token_data = decode_token(token)
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Check if token has been revoked
    if token_data.jti and await token_revocation_store.is_revoked(token_data.jti):
        raise HTTPException(status_code=401, detail="Token has been revoked")

    return token_data


def require_role(allowed_roles: List[str]):
    async def role_checker(
        current_user: TokenData = Depends(get_current_user),
    ) -> TokenData:
        if current_user.role not in allowed_roles and current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user

    return role_checker


def require_permission(permission: Permission):
    """FastAPI dependency for RBAC permission checks."""

    async def permission_checker(
        current_user: TokenData = Depends(get_current_user),
    ) -> TokenData:
        # Admin bypasses permission checks
        if current_user.role == "admin":
            return current_user

        # Map role string to RoleType for RBAC lookup
        try:
            role_type = RoleType(current_user.role)
        except ValueError:
            role_type = RoleType.READ_ONLY

        from infrastructure.adapters.rbac import ROLE_PERMISSIONS

        role_perms = ROLE_PERMISSIONS.get(role_type, set())

        if permission not in role_perms:
            raise HTTPException(
                status_code=403,
                detail=f"Permission denied: {permission.value}",
            )
        return current_user

    return permission_checker


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict


class RegisterRequest(BaseModel):
    email: str
    password: str
    invitation_token: str


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str


@app.post(
    "/auth/register",
    response_model=User,
    tags=["Auth"],
    summary="Register a new user",
    responses={401: {"description": "Unauthorized"}, 403: {"description": "Forbidden"}},
)
async def register(
    request: RegisterRequest,
    current_user: TokenData = Depends(require_role(["admin"])),
):
    """Registration requires admin auth and an invitation token."""
    if not request.invitation_token:
        raise HTTPException(status_code=403, detail="Invitation token required")

    existing = await user_repo.get_by_email(request.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = await user_repo.create_user(
        UserCreate(
            email=request.email,
            password=request.password,
            name=request.email.split("@")[0],
            org_id=current_user.org_id,
        )
    )
    return user


def _check_brute_force(email: str):
    """Check and enforce brute force protection."""
    import time

    now = time.time()
    attempts = _login_attempts.get(email, [])
    # Remove old attempts outside the lockout window
    attempts = [t for t in attempts if now - t < LOGIN_LOCKOUT_SECONDS]
    _login_attempts[email] = attempts

    if len(attempts) >= MAX_LOGIN_ATTEMPTS:
        raise HTTPException(
            status_code=429,
            detail="Too many login attempts. Try again later.",
        )


def _record_failed_login(email: str):
    import time

    if email not in _login_attempts:
        _login_attempts[email] = []
    _login_attempts[email].append(time.time())


@app.post(
    "/auth/login",
    response_model=LoginResponse,
    tags=["Auth"],
    summary="Login and obtain access token",
)
async def login(request: LoginRequest):
    _check_brute_force(request.email)

    user = await user_repo.get_by_email(request.email)
    if not user:
        _record_failed_login(request.email)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not await user_repo.verify_password(user.id, request.password):
        _record_failed_login(request.email)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Clear failed attempts on success
    _login_attempts.pop(request.email, None)

    access_token = create_access_token(
        data={
            "sub": user.id,
            "email": user.email,
            "role": user.role,
            "org_id": user.org_id,
        },
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user={
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "org_id": user.org_id,
        },
    )


@app.post(
    "/auth/logout",
    tags=["Auth"],
    summary="Logout and revoke token",
    responses={401: {"description": "Unauthorized"}},
)
async def logout(current_user: TokenData = Depends(get_current_user)):
    """Revoke the current token."""
    if current_user.jti:
        # Revoke for token lifetime (30 min default)
        expires_at = (
            datetime.now(timezone.utc)
            + timedelta(minutes=settings.access_token_expire_minutes)
        ).timestamp()
        await token_revocation_store.revoke(current_user.jti, expires_at)
    return {"message": "Logged out successfully"}


@app.post(
    "/auth/refresh",
    response_model=LoginResponse,
    tags=["Auth"],
    summary="Refresh access token",
    responses={401: {"description": "Unauthorized"}},
)
async def refresh_token(current_user: TokenData = Depends(get_current_user)):
    """Issue a new token if the current token is valid."""
    # Revoke the old token
    if current_user.jti:
        expires_at = (
            datetime.now(timezone.utc)
            + timedelta(minutes=settings.access_token_expire_minutes)
        ).timestamp()
        await token_revocation_store.revoke(current_user.jti, expires_at)

    # Issue new token
    new_token = create_access_token(
        data={
            "sub": current_user.user_id,
            "email": current_user.email,
            "role": current_user.role,
            "org_id": current_user.org_id,
        },
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )

    return LoginResponse(
        access_token=new_token,
        token_type="bearer",
        user={
            "id": current_user.user_id,
            "email": current_user.email,
            "role": current_user.role,
            "org_id": current_user.org_id,
        },
    )


@app.post(
    "/auth/change-password",
    tags=["Auth"],
    summary="Change user password",
    responses={401: {"description": "Unauthorized"}},
)
async def change_password(
    request: PasswordChangeRequest,
    current_user: TokenData = Depends(get_current_user),
):
    """Change user password with history check."""
    if not await user_repo.verify_password(
        current_user.user_id, request.current_password
    ):
        raise HTTPException(status_code=401, detail="Current password is incorrect")

    await user_repo.update_password(current_user.user_id, request.new_password)

    return {"message": "Password changed successfully"}


account_repo = container.account_repository()
contact_repo = container.contact_repository()
opportunity_repo = container.opportunity_repository()
lead_repo = container.lead_repository()
case_repo = container.case_repository()
event_bus = container.event_bus()
audit_log = container.audit_log()


class AccountResponse(BaseModel):
    id: str
    name: str
    industry: str
    territory: str
    website: Optional[str]
    phone: Optional[str]
    billing_address: Optional[str]
    annual_revenue: Optional[float]
    currency: Optional[str]
    employee_count: Optional[int]
    owner_id: str
    parent_account_id: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime


INDUSTRIES = [
    "technology",
    "finance",
    "healthcare",
    "manufacturing",
    "retail",
    "education",
    "government",
    "nonprofit",
    "other",
]
TERRITORIES = [
    "north_america",
    "europe",
    "asia_pacific",
    "latin_america",
    "middle_east",
    "africa",
]
PRIORITIES = ["low", "medium", "high", "critical"]
ORIGINS = ["web", "email", "phone", "chat", "social"]


class CreateAccountRequest(BaseModel):
    name: constr(min_length=1, max_length=255)
    industry: str = Field(..., pattern="|".join(INDUSTRIES))
    territory: str = Field(..., pattern="|".join(TERRITORIES))
    owner_id: constr(max_length=100)
    website: Optional[constr(max_length=2048)] = None
    phone: Optional[constr(max_length=50)] = None
    billing_address: Optional[constr(max_length=500)] = None
    annual_revenue: Optional[float] = Field(None, ge=0)
    currency: constr(max_length=10) = "USD"
    employee_count: Optional[int] = Field(None, ge=0)

    @field_validator("industry")
    @classmethod
    def validate_industry(cls, v: str) -> str:
        if v not in INDUSTRIES:
            raise ValueError(f"Industry must be one of: {', '.join(INDUSTRIES)}")
        return v

    @field_validator("territory")
    @classmethod
    def validate_territory(cls, v: str) -> str:
        if v not in TERRITORIES:
            raise ValueError(f"Territory must be one of: {', '.join(TERRITORIES)}")
        return v


class ContactResponse(BaseModel):
    id: str
    account_id: str
    first_name: str
    last_name: str
    email: str
    phone: Optional[str]
    title: Optional[str]
    department: Optional[str]
    owner_id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class CreateContactRequest(BaseModel):
    account_id: constr(max_length=100)
    first_name: constr(min_length=1, max_length=100)
    last_name: constr(min_length=1, max_length=100)
    email: EmailStr
    owner_id: constr(max_length=100)
    phone: Optional[constr(max_length=50)] = None
    title: Optional[constr(max_length=200)] = None
    department: Optional[constr(max_length=200)] = None


class OpportunityResponse(BaseModel):
    id: str
    account_id: str
    name: str
    stage: str
    amount: float
    currency: str
    probability: int
    close_date: datetime
    owner_id: str
    contact_id: Optional[str]
    source: Optional[str]
    description: Optional[str]
    is_active: bool
    is_won: bool
    is_lost: bool
    is_closed: bool
    weighted_value: float
    created_at: datetime
    updated_at: datetime


class CreateOpportunityRequest(BaseModel):
    account_id: constr(max_length=100)
    name: constr(min_length=1, max_length=255)
    amount: float = Field(..., ge=0)
    currency: constr(max_length=10)
    close_date: datetime
    owner_id: constr(max_length=100)
    source: Optional[constr(max_length=100)] = None
    contact_id: Optional[constr(max_length=100)] = None
    description: Optional[constr(max_length=5000)] = None


class LeadResponse(BaseModel):
    id: str
    first_name: str
    last_name: str
    email: str
    company: str
    status: str
    rating: str
    owner_id: str
    source: Optional[str]
    phone: Optional[str]
    title: Optional[str]
    website: Optional[str]
    created_at: datetime
    updated_at: datetime


class CreateLeadRequest(BaseModel):
    first_name: constr(min_length=1, max_length=100)
    last_name: constr(min_length=1, max_length=100)
    email: EmailStr
    company: constr(min_length=1, max_length=255)
    owner_id: constr(max_length=100)
    source: Optional[constr(max_length=100)] = None
    phone: Optional[constr(max_length=50)] = None
    title: Optional[constr(max_length=200)] = None
    website: Optional[constr(max_length=2048)] = None


class CaseResponse(BaseModel):
    id: str
    case_number: str
    subject: str
    description: str
    account_id: str
    contact_id: Optional[str]
    status: str
    priority: str
    origin: str
    owner_id: str
    resolution_notes: Optional[str]
    resolved_by: Optional[str]
    resolved_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class UpdateStageRequest(BaseModel):
    stage: str
    reason: Optional[str] = None


class UpdateStatusRequest(BaseModel):
    status: str


class ResolveCaseRequest(BaseModel):
    resolution_notes: constr(min_length=1, max_length=5000)
    resolved_by: constr(max_length=100)


class CreateCaseRequest(BaseModel):
    subject: constr(min_length=1, max_length=500)
    description: constr(min_length=1, max_length=10000)
    account_id: constr(max_length=100)
    owner_id: constr(max_length=100)
    case_number: constr(max_length=50)
    contact_id: Optional[constr(max_length=100)] = None
    priority: str = "medium"
    origin: str = "web"

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: str) -> str:
        if v not in PRIORITIES:
            raise ValueError(f"Priority must be one of: {', '.join(PRIORITIES)}")
        return v

    @field_validator("origin")
    @classmethod
    def validate_origin(cls, v: str) -> str:
        if v not in ORIGINS:
            raise ValueError(f"Origin must be one of: {', '.join(ORIGINS)}")
        return v


@app.get("/", tags=["System"], summary="API root")
async def root():
    return {"message": "Nexus CRM API", "version": "1.0.0"}


@app.get("/health", tags=["System"], summary="Health check")
async def health():
    return await health_checker.check_health()


@app.get("/metrics", tags=["System"], summary="Application metrics")
async def get_metrics(
    current_user: TokenData = Depends(require_permission(Permission.AUDIT_VIEW)),
):
    return metrics.snapshot()


@app.get("/metrics/prometheus", tags=["System"], summary="Prometheus metrics endpoint")
async def get_prometheus_metrics(
    current_user: TokenData = Depends(require_permission(Permission.AUDIT_VIEW)),
):
    return PlainTextResponse(
        content=metrics.to_prometheus_format(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


@app.post(
    "/accounts",
    response_model=AccountResponse,
    tags=["Accounts"],
    summary="Create account",
    responses={401: {"description": "Unauthorized"}},
)
async def create_account(
    request: CreateAccountRequest,
    current_user: TokenData = Depends(require_permission(Permission.ACCOUNTS_CREATE)),
):
    dto = CreateAccountDTO(
        name=request.name,
        industry=request.industry,
        territory=request.territory,
        owner_id=request.owner_id,
        website=request.website,
        phone=request.phone,
        billing_address=request.billing_address,
        annual_revenue=request.annual_revenue,
        currency=request.currency,
        employee_count=request.employee_count,
    )
    command = CreateAccountCommand(
        repository=account_repo,
        event_bus=event_bus,
        audit_log=audit_log,
    )
    result = await command.execute(dto)

    # Grant record access to creator
    try:
        rbac_service.grant_record_access(
            "account", PyUUID(result.id), [PyUUID(current_user.user_id)]
        )
    except (ValueError, TypeError):
        pass

    return result


@app.get(
    "/accounts",
    tags=["Accounts"],
    summary="List accounts",
    responses={401: {"description": "Unauthorized"}},
)
async def list_accounts(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None),
    industry: Optional[str] = Query(None),
    territory: Optional[str] = Query(None),
    owner_id: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    current_user: TokenData = Depends(require_permission(Permission.ACCOUNTS_VIEW)),
):
    query = SearchAccountsQuery(repository=account_repo)
    items, total = await query.execute(
        search=search, industry=industry, territory=territory,
        owner_id=owner_id, is_active=is_active, sort_by=sort_by,
        sort_order=sort_order, limit=limit, offset=offset)
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@app.get(
    "/accounts/{account_id}",
    response_model=AccountResponse,
    tags=["Accounts"],
    summary="Get account by ID",
    responses={
        401: {"description": "Unauthorized"},
        404: {"description": "Account not found"},
    },
)
async def get_account(
    account_id: str,
    current_user: TokenData = Depends(require_permission(Permission.ACCOUNTS_VIEW)),
):
    query = GetAccountQuery(repository=account_repo)
    result = await query.execute(account_id)
    if not result:
        raise HTTPException(status_code=404, detail="Account not found")
    return result


@app.put(
    "/accounts/{account_id}",
    response_model=AccountResponse,
    tags=["Accounts"],
    summary="Update account",
    responses={
        401: {"description": "Unauthorized"},
        404: {"description": "Account not found"},
    },
)
async def update_account(
    account_id: str,
    request: CreateAccountRequest,
    current_user: TokenData = Depends(require_permission(Permission.ACCOUNTS_EDIT)),
):
    dto = CreateAccountDTO(
        name=request.name,
        industry=request.industry,
        territory=request.territory,
        owner_id=request.owner_id,
        website=request.website,
        phone=request.phone,
        billing_address=request.billing_address,
        annual_revenue=request.annual_revenue,
        currency=request.currency,
        employee_count=request.employee_count,
    )
    command = UpdateAccountCommand(
        repository=account_repo,
        event_bus=event_bus,
        audit_log=audit_log,
    )
    result = await command.execute(account_id, dto, current_user.user_id)
    return result


@app.post(
    "/contacts",
    response_model=ContactResponse,
    tags=["Contacts"],
    summary="Create contact",
    responses={401: {"description": "Unauthorized"}},
)
async def create_contact(
    request: CreateContactRequest,
    current_user: TokenData = Depends(require_permission(Permission.CONTACTS_CREATE)),
):
    dto = CreateContactDTO(
        account_id=request.account_id,
        first_name=request.first_name,
        last_name=request.last_name,
        email=request.email,
        owner_id=request.owner_id,
        phone=request.phone,
        title=request.title,
        department=request.department,
    )
    command = CreateContactCommand(
        repository=contact_repo,
        account_repository=account_repo,
        event_bus=event_bus,
        audit_log=audit_log,
    )
    result = await command.execute(dto)

    try:
        rbac_service.grant_record_access(
            "contact", PyUUID(result.id), [PyUUID(current_user.user_id)]
        )
    except (ValueError, TypeError):
        pass

    return result


@app.get(
    "/contacts",
    tags=["Contacts"],
    summary="List contacts",
    responses={401: {"description": "Unauthorized"}},
)
async def list_contacts(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None),
    account_id: Optional[str] = Query(None),
    owner_id: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    current_user: TokenData = Depends(require_permission(Permission.CONTACTS_VIEW)),
):
    query = SearchContactsQuery(repository=contact_repo)
    items, total = await query.execute(
        search=search, account_id=account_id, owner_id=owner_id,
        is_active=is_active, sort_by=sort_by, sort_order=sort_order,
        limit=limit, offset=offset)
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@app.get(
    "/contacts/{contact_id}",
    response_model=ContactResponse,
    tags=["Contacts"],
    summary="Get contact by ID",
    responses={
        401: {"description": "Unauthorized"},
        404: {"description": "Contact not found"},
    },
)
async def get_contact(
    contact_id: str,
    current_user: TokenData = Depends(require_permission(Permission.CONTACTS_VIEW)),
):
    query = GetContactQuery(repository=contact_repo)
    result = await query.execute(contact_id)
    if not result:
        raise HTTPException(status_code=404, detail="Contact not found")
    return result


@app.get(
    "/accounts/{account_id}/contacts",
    response_model=List[ContactResponse],
    tags=["Contacts"],
    summary="Get contacts by account",
    responses={401: {"description": "Unauthorized"}},
)
async def get_account_contacts(
    account_id: str,
    current_user: TokenData = Depends(require_permission(Permission.CONTACTS_VIEW)),
):
    query = GetContactsByAccountQuery(repository=contact_repo)
    return await query.execute(account_id)


@app.post(
    "/opportunities",
    response_model=OpportunityResponse,
    tags=["Opportunities"],
    summary="Create opportunity",
    responses={401: {"description": "Unauthorized"}},
)
async def create_opportunity(
    request: CreateOpportunityRequest,
    current_user: TokenData = Depends(
        require_permission(Permission.OPPORTUNITIES_CREATE)
    ),
):
    dto = CreateOpportunityDTO(
        account_id=request.account_id,
        name=request.name,
        amount=request.amount,
        currency=request.currency,
        close_date=request.close_date,
        owner_id=request.owner_id,
        source=request.source,
        contact_id=request.contact_id,
        description=request.description,
    )
    command = CreateOpportunityCommand(
        repository=opportunity_repo,
        account_repository=account_repo,
        event_bus=event_bus,
        audit_log=audit_log,
    )
    result = await command.execute(dto)

    try:
        rbac_service.grant_record_access(
            "opportunity", PyUUID(result.id), [PyUUID(current_user.user_id)]
        )
    except (ValueError, TypeError):
        pass

    return result


@app.get(
    "/opportunities",
    tags=["Opportunities"],
    summary="List opportunities",
    responses={401: {"description": "Unauthorized"}},
)
async def list_opportunities(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None),
    stage: Optional[str] = Query(None),
    owner_id: Optional[str] = Query(None),
    account_id: Optional[str] = Query(None),
    is_closed: Optional[bool] = Query(None),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    current_user: TokenData = Depends(
        require_permission(Permission.OPPORTUNITIES_VIEW)
    ),
):
    query = SearchOpportunitiesQuery(repository=opportunity_repo)
    items, total = await query.execute(
        search=search, stage=stage, owner_id=owner_id,
        account_id=account_id, is_closed=is_closed,
        sort_by=sort_by, sort_order=sort_order, limit=limit, offset=offset)
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@app.get(
    "/opportunities/open",
    response_model=List[OpportunityResponse],
    tags=["Opportunities"],
    summary="Get open opportunities",
    responses={401: {"description": "Unauthorized"}},
)
async def get_open_opportunities(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: TokenData = Depends(
        require_permission(Permission.OPPORTUNITIES_VIEW)
    ),
):
    query = GetOpenOpportunitiesQuery(repository=opportunity_repo)
    return await query.execute(limit, offset)


@app.get(
    "/opportunities/{opportunity_id}",
    response_model=OpportunityResponse,
    tags=["Opportunities"],
    summary="Get opportunity by ID",
    responses={
        401: {"description": "Unauthorized"},
        404: {"description": "Opportunity not found"},
    },
)
async def get_opportunity(
    opportunity_id: str,
    current_user: TokenData = Depends(
        require_permission(Permission.OPPORTUNITIES_VIEW)
    ),
):
    query = GetOpportunityQuery(repository=opportunity_repo)
    result = await query.execute(opportunity_id)
    if not result:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return result


@app.patch(
    "/opportunities/{opportunity_id}/stage",
    tags=["Opportunities"],
    summary="Update opportunity stage",
    responses={
        401: {"description": "Unauthorized"},
        404: {"description": "Opportunity not found"},
    },
)
async def update_opportunity_stage(
    opportunity_id: str,
    request: UpdateStageRequest,
    current_user: TokenData = Depends(
        require_permission(Permission.OPPORTUNITIES_EDIT)
    ),
):
    command = UpdateOpportunityStageCommand(
        repository=opportunity_repo,
        event_bus=event_bus,
        audit_log=audit_log,
    )
    result = await command.execute(
        opportunity_id, request.stage, current_user.user_id, request.reason
    )
    return result


@app.post(
    "/leads",
    response_model=LeadResponse,
    tags=["Leads"],
    summary="Create lead",
    responses={401: {"description": "Unauthorized"}},
)
async def create_lead(
    request: CreateLeadRequest,
    current_user: TokenData = Depends(require_permission(Permission.LEADS_CREATE)),
):
    dto = CreateLeadDTO(
        first_name=request.first_name,
        last_name=request.last_name,
        email=request.email,
        company=request.company,
        owner_id=request.owner_id,
        source=request.source,
        phone=request.phone,
        title=request.title,
        website=request.website,
    )
    command = CreateLeadCommand(
        repository=lead_repo,
        event_bus=event_bus,
        audit_log=audit_log,
    )
    result = await command.execute(dto)

    try:
        rbac_service.grant_record_access(
            "lead", PyUUID(result.id), [PyUUID(current_user.user_id)]
        )
    except (ValueError, TypeError):
        pass

    return result


@app.get(
    "/leads",
    tags=["Leads"],
    summary="List leads",
    responses={401: {"description": "Unauthorized"}},
)
async def list_leads(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    rating: Optional[str] = Query(None),
    owner_id: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    current_user: TokenData = Depends(require_permission(Permission.LEADS_VIEW)),
):
    query = SearchLeadsQuery(repository=lead_repo)
    items, total = await query.execute(
        search=search, status=status, rating=rating, owner_id=owner_id,
        source=source, sort_by=sort_by, sort_order=sort_order,
        limit=limit, offset=offset)
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@app.get(
    "/leads/{lead_id}",
    response_model=LeadResponse,
    tags=["Leads"],
    summary="Get lead by ID",
    responses={
        401: {"description": "Unauthorized"},
        404: {"description": "Lead not found"},
    },
)
async def get_lead(
    lead_id: str,
    current_user: TokenData = Depends(require_permission(Permission.LEADS_VIEW)),
):
    query = GetLeadQuery(repository=lead_repo)
    result = await query.execute(lead_id)
    if not result:
        raise HTTPException(status_code=404, detail="Lead not found")
    return result


@app.post(
    "/leads/{lead_id}/qualify",
    tags=["Leads"],
    summary="Qualify a lead",
    responses={
        401: {"description": "Unauthorized"},
        404: {"description": "Lead not found"},
    },
)
async def qualify_lead(
    lead_id: str,
    current_user: TokenData = Depends(require_permission(Permission.LEADS_CONVERT)),
):
    command = QualifyLeadCommand(
        repository=lead_repo,
        event_bus=event_bus,
        audit_log=audit_log,
    )
    result = await command.execute(lead_id, current_user.user_id)
    return result


@app.post(
    "/cases",
    response_model=CaseResponse,
    tags=["Cases"],
    summary="Create case",
    responses={401: {"description": "Unauthorized"}},
)
async def create_case(
    request: CreateCaseRequest,
    current_user: TokenData = Depends(require_permission(Permission.CASES_CREATE)),
):
    dto = CreateCaseDTO(
        subject=request.subject,
        description=request.description,
        account_id=request.account_id,
        owner_id=request.owner_id,
        case_number=request.case_number,
        contact_id=request.contact_id,
        priority=request.priority,
        origin=request.origin,
    )
    command = CreateCaseCommand(
        repository=case_repo,
        account_repository=account_repo,
        event_bus=event_bus,
        audit_log=audit_log,
    )
    result = await command.execute(dto)

    try:
        rbac_service.grant_record_access(
            "case", PyUUID(result.id), [PyUUID(current_user.user_id)]
        )
    except (ValueError, TypeError):
        pass

    return result


@app.get(
    "/cases",
    tags=["Cases"],
    summary="List cases",
    responses={401: {"description": "Unauthorized"}},
)
async def list_cases(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    origin: Optional[str] = Query(None),
    owner_id: Optional[str] = Query(None),
    account_id: Optional[str] = Query(None),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    current_user: TokenData = Depends(require_permission(Permission.CASES_VIEW)),
):
    query = SearchCasesQuery(repository=case_repo)
    items, total = await query.execute(
        search=search, status=status, priority=priority, origin=origin,
        owner_id=owner_id, account_id=account_id, sort_by=sort_by,
        sort_order=sort_order, limit=limit, offset=offset)
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@app.get(
    "/cases/open",
    response_model=List[CaseResponse],
    tags=["Cases"],
    summary="Get open cases",
    responses={401: {"description": "Unauthorized"}},
)
async def get_open_cases(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: TokenData = Depends(require_permission(Permission.CASES_VIEW)),
):
    query = GetOpenCasesQuery(repository=case_repo)
    return await query.execute(limit, offset)


@app.get(
    "/cases/{case_id}",
    response_model=CaseResponse,
    tags=["Cases"],
    summary="Get case by ID",
    responses={
        401: {"description": "Unauthorized"},
        404: {"description": "Case not found"},
    },
)
async def get_case(
    case_id: str,
    current_user: TokenData = Depends(require_permission(Permission.CASES_VIEW)),
):
    query = GetCaseQuery(repository=case_repo)
    result = await query.execute(case_id)
    if not result:
        raise HTTPException(status_code=404, detail="Case not found")
    return result


@app.patch(
    "/cases/{case_id}/status",
    tags=["Cases"],
    summary="Update case status",
    responses={
        401: {"description": "Unauthorized"},
        404: {"description": "Case not found"},
    },
)
async def update_case_status(
    case_id: str,
    request: UpdateStatusRequest,
    current_user: TokenData = Depends(require_permission(Permission.CASES_EDIT)),
):
    command = UpdateCaseStatusCommand(
        repository=case_repo,
        event_bus=event_bus,
        audit_log=audit_log,
    )
    result = await command.execute(case_id, request.status, current_user.user_id)
    return result


@app.post(
    "/cases/{case_id}/resolve",
    tags=["Cases"],
    summary="Resolve a case",
    responses={
        401: {"description": "Unauthorized"},
        404: {"description": "Case not found"},
    },
)
async def resolve_case(
    case_id: str,
    request: ResolveCaseRequest,
    current_user: TokenData = Depends(require_permission(Permission.CASES_RESOLVE)),
):
    command = ResolveCaseCommand(
        repository=case_repo,
        event_bus=event_bus,
        audit_log=audit_log,
    )
    result = await command.execute(
        case_id, request.resolution_notes, request.resolved_by, current_user.user_id
    )
    return result


# ---------------------------------------------------------------------------
# UPDATE / ACTION ENDPOINTS
# ---------------------------------------------------------------------------


@app.put(
    "/contacts/{contact_id}",
    response_model=ContactResponse,
    tags=["Contacts"],
    summary="Update contact",
    responses={
        401: {"description": "Unauthorized"},
        404: {"description": "Contact not found"},
    },
)
async def update_contact(
    contact_id: str,
    request: CreateContactRequest,
    current_user: TokenData = Depends(require_permission(Permission.CONTACTS_EDIT)),
):
    dto = CreateContactDTO(
        account_id=request.account_id,
        first_name=request.first_name,
        last_name=request.last_name,
        email=request.email,
        owner_id=request.owner_id,
        phone=request.phone,
        title=request.title,
        department=request.department,
    )
    command = UpdateContactCommand(
        repository=contact_repo,
        event_bus=event_bus,
        audit_log=audit_log,
    )
    result = await command.execute(contact_id, dto, current_user.user_id)
    return result


@app.put(
    "/opportunities/{opportunity_id}",
    response_model=OpportunityResponse,
    tags=["Opportunities"],
    summary="Update opportunity",
    responses={
        401: {"description": "Unauthorized"},
        404: {"description": "Opportunity not found"},
    },
)
async def update_opportunity(
    opportunity_id: str,
    request: CreateOpportunityRequest,
    current_user: TokenData = Depends(
        require_permission(Permission.OPPORTUNITIES_EDIT)
    ),
):
    dto = CreateOpportunityDTO(
        account_id=request.account_id,
        name=request.name,
        amount=request.amount,
        currency=request.currency,
        close_date=request.close_date,
        owner_id=request.owner_id,
        source=request.source,
        contact_id=request.contact_id,
        description=request.description,
    )
    command = UpdateOpportunityCommand(
        repository=opportunity_repo,
        event_bus=event_bus,
        audit_log=audit_log,
    )
    result = await command.execute(opportunity_id, dto, current_user.user_id)
    return result


@app.post(
    "/accounts/{account_id}/deactivate",
    response_model=AccountResponse,
    tags=["Accounts"],
    summary="Deactivate account",
    responses={
        401: {"description": "Unauthorized"},
        404: {"description": "Account not found"},
    },
)
async def deactivate_account(
    account_id: str,
    current_user: TokenData = Depends(require_permission(Permission.ACCOUNTS_EDIT)),
):
    command = DeactivateAccountCommand(
        repository=account_repo,
        event_bus=event_bus,
        audit_log=audit_log,
    )
    result = await command.execute(account_id, current_user.user_id)
    return result


class ConvertLeadRequest(BaseModel):
    account_id: constr(max_length=100)
    contact_id: constr(max_length=100)
    opportunity_id: Optional[constr(max_length=100)] = None


@app.post(
    "/leads/{lead_id}/convert",
    tags=["Leads"],
    summary="Convert lead to account/contact",
    responses={
        401: {"description": "Unauthorized"},
        404: {"description": "Lead not found"},
    },
)
async def convert_lead(
    lead_id: str,
    request: ConvertLeadRequest,
    current_user: TokenData = Depends(require_permission(Permission.LEADS_CONVERT)),
):
    command = ConvertLeadCommand(
        lead_repository=lead_repo,
        account_repository=account_repo,
        contact_repository=contact_repo,
        opportunity_repository=opportunity_repo,
        event_bus=event_bus,
        audit_log=audit_log,
    )
    result = await command.execute(
        lead_id,
        request.account_id,
        request.contact_id,
        request.opportunity_id or "",
        current_user.user_id,
    )
    return result


@app.post(
    "/cases/{case_id}/close",
    tags=["Cases"],
    summary="Close a case",
    responses={
        401: {"description": "Unauthorized"},
        404: {"description": "Case not found"},
    },
)
async def close_case(
    case_id: str,
    current_user: TokenData = Depends(require_permission(Permission.CASES_RESOLVE)),
):
    command = CloseCaseCommand(
        repository=case_repo,
        event_bus=event_bus,
        audit_log=audit_log,
    )
    result = await command.execute(case_id, current_user.user_id)
    return result


# ---------------------------------------------------------------------------
# DELETE ENDPOINTS
# ---------------------------------------------------------------------------


@app.delete(
    "/accounts/{account_id}",
    tags=["Accounts"],
    summary="Delete account",
    responses={
        401: {"description": "Unauthorized"},
        404: {"description": "Account not found"},
    },
)
async def delete_account(
    account_id: str,
    current_user: TokenData = Depends(require_permission(Permission.ACCOUNTS_DELETE)),
):
    query = GetAccountQuery(repository=account_repo)
    result = await query.execute(account_id)
    if not result:
        raise HTTPException(status_code=404, detail="Account not found")
    await account_repo.delete(account_id)
    await audit_log.log(
        user_id=current_user.user_id,
        action="DELETE",
        resource_type="Account",
        resource_id=account_id,
        details={"name": result.name},
    )
    return Response(status_code=204)


@app.delete(
    "/contacts/{contact_id}",
    tags=["Contacts"],
    summary="Delete contact",
    responses={
        401: {"description": "Unauthorized"},
        404: {"description": "Contact not found"},
    },
)
async def delete_contact(
    contact_id: str,
    current_user: TokenData = Depends(require_permission(Permission.CONTACTS_DELETE)),
):
    query = GetContactQuery(repository=contact_repo)
    result = await query.execute(contact_id)
    if not result:
        raise HTTPException(status_code=404, detail="Contact not found")
    await contact_repo.delete(contact_id)
    await audit_log.log(
        user_id=current_user.user_id,
        action="DELETE",
        resource_type="Contact",
        resource_id=contact_id,
        details={"name": f"{result.first_name} {result.last_name}"},
    )
    return Response(status_code=204)


@app.delete(
    "/opportunities/{opportunity_id}",
    tags=["Opportunities"],
    summary="Delete opportunity",
    responses={
        401: {"description": "Unauthorized"},
        404: {"description": "Opportunity not found"},
    },
)
async def delete_opportunity(
    opportunity_id: str,
    current_user: TokenData = Depends(
        require_permission(Permission.OPPORTUNITIES_DELETE)
    ),
):
    query = GetOpportunityQuery(repository=opportunity_repo)
    result = await query.execute(opportunity_id)
    if not result:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    await opportunity_repo.delete(opportunity_id)
    await audit_log.log(
        user_id=current_user.user_id,
        action="DELETE",
        resource_type="Opportunity",
        resource_id=opportunity_id,
        details={"name": result.name},
    )
    return Response(status_code=204)


@app.delete(
    "/leads/{lead_id}",
    tags=["Leads"],
    summary="Delete lead",
    responses={
        401: {"description": "Unauthorized"},
        404: {"description": "Lead not found"},
    },
)
async def delete_lead(
    lead_id: str,
    current_user: TokenData = Depends(require_permission(Permission.LEADS_DELETE)),
):
    query = GetLeadQuery(repository=lead_repo)
    result = await query.execute(lead_id)
    if not result:
        raise HTTPException(status_code=404, detail="Lead not found")
    await lead_repo.delete(lead_id)
    await audit_log.log(
        user_id=current_user.user_id,
        action="DELETE",
        resource_type="Lead",
        resource_id=lead_id,
        details={"name": f"{result.first_name} {result.last_name}"},
    )
    return Response(status_code=204)


@app.delete(
    "/cases/{case_id}",
    tags=["Cases"],
    summary="Delete case",
    responses={
        401: {"description": "Unauthorized"},
        404: {"description": "Case not found"},
    },
)
async def delete_case(
    case_id: str,
    current_user: TokenData = Depends(require_permission(Permission.CASES_DELETE)),
):
    query = GetCaseQuery(repository=case_repo)
    result = await query.execute(case_id)
    if not result:
        raise HTTPException(status_code=404, detail="Case not found")
    await case_repo.delete(case_id)
    await audit_log.log(
        user_id=current_user.user_id,
        action="DELETE",
        resource_type="Case",
        resource_id=case_id,
        details={"case_number": result.case_number, "subject": result.subject},
    )
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# REPORTS ENDPOINTS (Tier 2)
# ---------------------------------------------------------------------------

forecasting_service = container.forecasting_service()
lead_scoring_service = container.lead_scoring_service()


@app.get(
    "/reports/pipeline-summary",
    tags=["Reports"],
    summary="Pipeline summary report",
    responses={401: {"description": "Unauthorized"}},
)
async def pipeline_summary(
    owner_id: Optional[str] = Query(None),
    current_user: TokenData = Depends(require_permission(Permission.REPORTS_VIEW)),
):
    all_opps = list(opportunity_repo._opportunities.values())
    if owner_id:
        all_opps = [o for o in all_opps if str(o.owner_id) == owner_id]
    by_stage = forecasting_service.forecast_by_stage(all_opps)
    total_pipeline = forecasting_service.calculate_weighted_pipeline(all_opps)
    total_value = sum(o.amount.amount_float for o in all_opps if not o.is_closed)
    won_count = sum(1 for o in all_opps if o.is_won)
    lost_count = sum(1 for o in all_opps if o.is_lost)
    open_count = sum(1 for o in all_opps if not o.is_closed)
    return {
        "by_stage": by_stage,
        "total_pipeline_value": total_value,
        "total_weighted_pipeline": total_pipeline,
        "won_count": won_count,
        "lost_count": lost_count,
        "open_count": open_count,
    }


@app.get(
    "/reports/lead-funnel",
    tags=["Reports"],
    summary="Lead funnel report",
    responses={401: {"description": "Unauthorized"}},
)
async def lead_funnel(
    owner_id: Optional[str] = Query(None),
    current_user: TokenData = Depends(require_permission(Permission.REPORTS_VIEW)),
):
    all_leads = list(lead_repo._leads.values())
    if owner_id:
        all_leads = [l for l in all_leads if str(l.owner_id) == owner_id]
    by_status = {}
    for lead in all_leads:
        s = lead.status.value
        by_status[s] = by_status.get(s, 0) + 1
    return {"by_status": by_status, "total": len(all_leads)}


@app.get(
    "/reports/case-metrics",
    tags=["Reports"],
    summary="Case metrics report",
    responses={401: {"description": "Unauthorized"}},
)
async def case_metrics(
    owner_id: Optional[str] = Query(None),
    current_user: TokenData = Depends(require_permission(Permission.REPORTS_VIEW)),
):
    from domain.entities.case import CaseStatus as CS
    all_cases = list(case_repo._cases.values())
    if owner_id:
        all_cases = [c for c in all_cases if str(c.owner_id) == owner_id]
    open_count = sum(1 for c in all_cases if c.status not in (CS.RESOLVED, CS.CLOSED))
    resolved_count = sum(1 for c in all_cases if c.status == CS.RESOLVED)
    closed_count = sum(1 for c in all_cases if c.status == CS.CLOSED)
    resolution_hours = []
    for c in all_cases:
        if c.resolved_at and c.created_at:
            diff = (c.resolved_at - c.created_at).total_seconds() / 3600
            resolution_hours.append(diff)
    avg_resolution = sum(resolution_hours) / len(resolution_hours) if resolution_hours else 0
    by_priority = {}
    for c in all_cases:
        p = c.priority.value
        by_priority[p] = by_priority.get(p, 0) + 1
    by_status = {}
    for c in all_cases:
        s = c.status.value
        by_status[s] = by_status.get(s, 0) + 1
    return {
        "open_count": open_count,
        "resolved_count": resolved_count,
        "closed_count": closed_count,
        "avg_resolution_hours": round(avg_resolution, 1),
        "by_priority": by_priority,
        "by_status": by_status,
        "total": len(all_cases),
    }


@app.get(
    "/reports/activity-summary",
    tags=["Reports"],
    summary="Activity summary report",
    responses={401: {"description": "Unauthorized"}},
)
async def activity_summary(
    period: str = Query("day", pattern="^(day|week|month)$"),
    owner_id: Optional[str] = Query(None),
    current_user: TokenData = Depends(require_permission(Permission.REPORTS_VIEW)),
):
    from collections import defaultdict

    def bucket_key(dt: datetime) -> str:
        if period == "day":
            return dt.strftime("%Y-%m-%d")
        elif period == "week":
            return dt.strftime("%Y-W%W")
        else:
            return dt.strftime("%Y-%m")

    result = {}
    repos = {
        "accounts": account_repo._accounts,
        "contacts": contact_repo._contacts,
        "opportunities": opportunity_repo._opportunities,
        "leads": lead_repo._leads,
        "cases": case_repo._cases,
    }
    for entity_name, store in repos.items():
        buckets = defaultdict(int)
        for item in store.values():
            if owner_id and str(item.owner_id) != owner_id:
                continue
            key = bucket_key(item.created_at)
            buckets[key] += 1
        result[entity_name] = dict(sorted(buckets.items()))
    return result


# ---------------------------------------------------------------------------
# ANALYTICS ENDPOINTS (Tier 4)
# ---------------------------------------------------------------------------


@app.get(
    "/analytics/revenue-forecast",
    tags=["Analytics"],
    summary="Revenue forecast",
    responses={401: {"description": "Unauthorized"}},
)
async def revenue_forecast(
    owner_id: Optional[str] = Query(None),
    current_user: TokenData = Depends(require_permission(Permission.REPORTS_VIEW)),
):
    from collections import defaultdict
    all_opps = list(opportunity_repo._opportunities.values())
    if owner_id:
        all_opps = [o for o in all_opps if str(o.owner_id) == owner_id]
    weighted = forecasting_service.calculate_weighted_pipeline(all_opps)
    best_case = sum(o.amount.amount_float for o in all_opps if not o.is_closed)
    committed = sum(o.amount.amount_float for o in all_opps if not o.is_closed and o.probability >= 75)
    closed_won_total = sum(o.amount.amount_float for o in all_opps if o.is_won)
    by_month = defaultdict(lambda: {"weighted": 0.0, "total": 0.0, "count": 0})
    for o in all_opps:
        if not o.is_closed:
            key = o.close_date.strftime("%Y-%m")
            by_month[key]["weighted"] += o.weighted_value.amount_float
            by_month[key]["total"] += o.amount.amount_float
            by_month[key]["count"] += 1
    by_stage = forecasting_service.forecast_by_stage(all_opps)
    return {
        "weighted_pipeline": weighted,
        "best_case": best_case,
        "committed": committed,
        "closed_won_total": closed_won_total,
        "by_month": dict(sorted(by_month.items())),
        "by_stage": by_stage,
    }


@app.get(
    "/analytics/lead-scores",
    tags=["Analytics"],
    summary="Lead scores",
    responses={401: {"description": "Unauthorized"}},
)
async def lead_scores(
    owner_id: Optional[str] = Query(None),
    current_user: TokenData = Depends(require_permission(Permission.REPORTS_VIEW)),
):
    all_leads = list(lead_repo._leads.values())
    if owner_id:
        all_leads = [l for l in all_leads if str(l.owner_id) == owner_id]
    scored = []
    scores_list = []
    for lead in all_leads:
        score = lead_scoring_service.score(lead)
        scores_list.append(score)
        scored.append({
            "id": str(lead.id),
            "name": f"{lead.first_name} {lead.last_name}",
            "company": lead.company,
            "email": str(lead.email),
            "status": lead.status.value,
            "rating": lead.rating.value,
            "score": score,
        })
    scored.sort(key=lambda x: x["score"], reverse=True)
    avg_score = sum(scores_list) / len(scores_list) if scores_list else 0
    hot = sum(1 for s in scores_list if s >= 70)
    warm = sum(1 for s in scores_list if 40 <= s < 70)
    cold = sum(1 for s in scores_list if s < 40)
    return {
        "leads": scored,
        "avg_score": round(avg_score, 1),
        "distribution": {"hot": hot, "warm": warm, "cold": cold},
        "total": len(scored),
    }


@app.get(
    "/analytics/trends",
    tags=["Analytics"],
    summary="Entity trends",
    responses={401: {"description": "Unauthorized"}},
)
async def trends(
    entity: str = Query("opportunities", pattern="^(accounts|contacts|opportunities|leads|cases)$"),
    period: str = Query("month", pattern="^(day|week|month)$"),
    group_by: Optional[str] = Query(None),
    owner_id: Optional[str] = Query(None),
    current_user: TokenData = Depends(require_permission(Permission.REPORTS_VIEW)),
):
    from collections import defaultdict

    def bucket_key(dt: datetime) -> str:
        if period == "day":
            return dt.strftime("%Y-%m-%d")
        elif period == "week":
            return dt.strftime("%Y-W%W")
        else:
            return dt.strftime("%Y-%m")

    repos = {
        "accounts": account_repo._accounts,
        "contacts": contact_repo._contacts,
        "opportunities": opportunity_repo._opportunities,
        "leads": lead_repo._leads,
        "cases": case_repo._cases,
    }
    store = repos.get(entity, {})
    items = list(store.values())
    if owner_id:
        items = [i for i in items if str(i.owner_id) == owner_id]

    if group_by:
        grouped = defaultdict(lambda: defaultdict(int))
        for item in items:
            key = bucket_key(item.created_at)
            field_val = getattr(item, group_by, None)
            if field_val is not None:
                field_str = field_val.value if hasattr(field_val, "value") else str(field_val)
            else:
                field_str = "unknown"
            grouped[key][field_str] += 1
        return {"data": {k: dict(v) for k, v in sorted(grouped.items())}, "grouped": True}
    else:
        buckets = defaultdict(int)
        for item in items:
            key = bucket_key(item.created_at)
            buckets[key] += 1
        return {"data": dict(sorted(buckets.items())), "grouped": False}


@app.get(
    "/analytics/win-loss",
    tags=["Analytics"],
    summary="Win/loss analysis",
    responses={401: {"description": "Unauthorized"}},
)
async def win_loss(
    owner_id: Optional[str] = Query(None),
    current_user: TokenData = Depends(require_permission(Permission.REPORTS_VIEW)),
):
    from collections import defaultdict
    all_opps = list(opportunity_repo._opportunities.values())
    if owner_id:
        all_opps = [o for o in all_opps if str(o.owner_id) == owner_id]
    won = [o for o in all_opps if o.is_won]
    lost = [o for o in all_opps if o.is_lost]
    closed = won + lost
    win_rate = len(won) / len(closed) * 100 if closed else 0
    avg_won_amount = sum(o.amount.amount_float for o in won) / len(won) if won else 0
    avg_lost_amount = sum(o.amount.amount_float for o in lost) / len(lost) if lost else 0
    cycle_days = []
    for o in closed:
        if o.closed_at and o.created_at:
            days = (o.closed_at - o.created_at).total_seconds() / 86400
            cycle_days.append(days)
    avg_cycle = sum(cycle_days) / len(cycle_days) if cycle_days else 0
    by_source = defaultdict(lambda: {"won": 0, "lost": 0})
    for o in closed:
        src = o.source.value if o.source else "unknown"
        if o.is_won:
            by_source[src]["won"] += 1
        else:
            by_source[src]["lost"] += 1
    by_month = defaultdict(lambda: {"won": 0, "lost": 0, "won_amount": 0.0, "lost_amount": 0.0})
    for o in closed:
        close_dt = o.closed_at or o.updated_at
        key = close_dt.strftime("%Y-%m")
        if o.is_won:
            by_month[key]["won"] += 1
            by_month[key]["won_amount"] += o.amount.amount_float
        else:
            by_month[key]["lost"] += 1
            by_month[key]["lost_amount"] += o.amount.amount_float
    return {
        "win_rate": round(win_rate, 1),
        "avg_cycle_days": round(avg_cycle, 1),
        "avg_won_amount": round(avg_won_amount, 2),
        "avg_lost_amount": round(avg_lost_amount, 2),
        "won_count": len(won),
        "lost_count": len(lost),
        "by_source": dict(by_source),
        "by_month": dict(sorted(by_month.items())),
    }


# ---------------------------------------------------------------------------
# REPORT BUILDER ENDPOINTS (Tier 3)
# ---------------------------------------------------------------------------


class FilterCondition(BaseModel):
    field: str
    operator: str = "eq"
    value: str


class ReportConfig(BaseModel):
    entity: str
    columns: Optional[List[str]] = None
    filters: Optional[List[FilterCondition]] = None
    sort_by: Optional[str] = None
    sort_order: str = "asc"
    group_by: Optional[str] = None
    limit: int = 100


def _get_entity_store(entity: str):
    stores = {
        "accounts": account_repo._accounts,
        "contacts": contact_repo._contacts,
        "opportunities": opportunity_repo._opportunities,
        "leads": lead_repo._leads,
        "cases": case_repo._cases,
    }
    return stores.get(entity)


def _get_entity_field(item, field: str):
    val = getattr(item, field, None)
    if val is None:
        return None
    if hasattr(val, "value"):
        return val.value
    if hasattr(val, "amount_float"):
        return val.amount_float
    if hasattr(val, "display_name"):
        return val.display_name
    return val


def _check_condition(item, cond: FilterCondition) -> bool:
    val = _get_entity_field(item, cond.field)
    if val is None:
        return cond.operator == "is_empty"
    val_str = str(val).lower()
    cond_val = cond.value.lower()
    if cond.operator == "eq":
        return val_str == cond_val
    elif cond.operator == "neq":
        return val_str != cond_val
    elif cond.operator == "contains":
        return cond_val in val_str
    elif cond.operator == "gt":
        try:
            return float(val) > float(cond.value)
        except (ValueError, TypeError):
            return False
    elif cond.operator == "lt":
        try:
            return float(val) < float(cond.value)
        except (ValueError, TypeError):
            return False
    elif cond.operator == "gte":
        try:
            return float(val) >= float(cond.value)
        except (ValueError, TypeError):
            return False
    elif cond.operator == "lte":
        try:
            return float(val) <= float(cond.value)
        except (ValueError, TypeError):
            return False
    elif cond.operator == "is_empty":
        return val_str == "" or val is None
    elif cond.operator == "is_not_empty":
        return val_str != "" and val is not None
    return True


def _project_entity(item, columns: Optional[List[str]]) -> dict:
    if not columns:
        result = {}
        for attr in ["id", "name", "first_name", "last_name", "email", "company",
                      "stage", "status", "amount", "probability", "close_date",
                      "industry", "territory", "rating", "source", "priority",
                      "origin", "case_number", "subject", "owner_id", "account_id",
                      "is_active", "is_closed", "is_won", "is_lost", "created_at", "updated_at"]:
            val = _get_entity_field(item, attr)
            if val is not None:
                result[attr] = str(val) if isinstance(val, datetime) else val
        return result
    result = {}
    for col in columns:
        val = _get_entity_field(item, col)
        result[col] = str(val) if isinstance(val, datetime) else val
    return result


@app.post(
    "/reports/query",
    tags=["Reports"],
    summary="Run custom report query",
    responses={401: {"description": "Unauthorized"}},
)
async def run_report_query(
    config: ReportConfig,
    current_user: TokenData = Depends(require_permission(Permission.REPORTS_VIEW)),
):
    store = _get_entity_store(config.entity)
    if store is None:
        raise HTTPException(status_code=400, detail=f"Unknown entity: {config.entity}")
    items = list(store.values())
    if config.filters:
        for cond in config.filters:
            items = [i for i in items if _check_condition(i, cond)]
    if config.sort_by:
        reverse = config.sort_order == "desc"
        items.sort(key=lambda i: _get_entity_field(i, config.sort_by) or "", reverse=reverse)
    total = len(items)
    items = items[:config.limit]
    if config.group_by:
        from collections import defaultdict
        groups = defaultdict(list)
        for item in items:
            key = _get_entity_field(item, config.group_by)
            key_str = str(key) if key is not None else "unknown"
            groups[key_str].append(_project_entity(item, config.columns))
        agg = {}
        for key, group_items in groups.items():
            agg[key] = {"count": len(group_items), "items": group_items}
        return {"type": "aggregated", "data": agg, "total": total}
    projected = [_project_entity(item, config.columns) for item in items]
    return {"type": "tabular", "data": projected, "total": total}


class CrossQueryConfig(BaseModel):
    primary_entity: str
    related_entity: str
    related_filters: List[FilterCondition]
    primary_columns: Optional[List[str]] = None
    limit: int = 100


@app.post(
    "/reports/cross-query",
    tags=["Reports"],
    summary="Cross-entity report query",
    responses={401: {"description": "Unauthorized"}},
)
async def run_cross_query(
    config: CrossQueryConfig,
    current_user: TokenData = Depends(require_permission(Permission.REPORTS_VIEW)),
):
    related_store = _get_entity_store(config.related_entity)
    primary_store = _get_entity_store(config.primary_entity)
    if not related_store or not primary_store:
        raise HTTPException(status_code=400, detail="Unknown entity")
    related_items = list(related_store.values())
    for cond in config.related_filters:
        related_items = [i for i in related_items if _check_condition(i, cond)]
    if config.primary_entity == "accounts":
        linking_ids = {str(getattr(i, "account_id", i.id)) for i in related_items}
        primary_items = [p for p in primary_store.values() if str(p.id) in linking_ids]
    else:
        linking_ids = {str(i.id) for i in related_items}
        primary_items = [p for p in primary_store.values()
                         if str(getattr(p, "account_id", "")) in linking_ids]
    total = len(primary_items)
    primary_items = primary_items[:config.limit]
    projected = [_project_entity(item, config.primary_columns) for item in primary_items]
    return {"type": "tabular", "data": projected, "total": total}
