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
    response_model=List[AccountResponse],
    tags=["Accounts"],
    summary="List accounts",
    responses={401: {"description": "Unauthorized"}},
)
async def list_accounts(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: TokenData = Depends(require_permission(Permission.ACCOUNTS_VIEW)),
):
    query = ListAccountsQuery(repository=account_repo)
    return await query.execute(limit, offset)


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
    response_model=List[ContactResponse],
    tags=["Contacts"],
    summary="List contacts",
    responses={401: {"description": "Unauthorized"}},
)
async def list_contacts(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: TokenData = Depends(require_permission(Permission.CONTACTS_VIEW)),
):
    query = ListContactsQuery(repository=contact_repo)
    return await query.execute(limit, offset)


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
    response_model=List[OpportunityResponse],
    tags=["Opportunities"],
    summary="List opportunities",
    responses={401: {"description": "Unauthorized"}},
)
async def list_opportunities(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: TokenData = Depends(
        require_permission(Permission.OPPORTUNITIES_VIEW)
    ),
):
    query = ListOpportunitiesQuery(repository=opportunity_repo)
    return await query.execute(limit, offset)


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
    response_model=List[LeadResponse],
    tags=["Leads"],
    summary="List leads",
    responses={401: {"description": "Unauthorized"}},
)
async def list_leads(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: TokenData = Depends(require_permission(Permission.LEADS_VIEW)),
):
    query = ListLeadsQuery(repository=lead_repo)
    return await query.execute(limit, offset)


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
    response_model=List[CaseResponse],
    tags=["Cases"],
    summary="List cases",
    responses={401: {"description": "Unauthorized"}},
)
async def list_cases(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: TokenData = Depends(require_permission(Permission.CASES_VIEW)),
):
    query = ListCasesQuery(repository=case_repo)
    return await query.execute(limit, offset)


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
