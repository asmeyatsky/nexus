"""
Nexus CRM API

Architectural Intent:
- REST API for Nexus CRM operations
- Follows skill2026 presentation layer patterns
- FastAPI-based HTTP endpoints
"""

from typing import Optional, List
from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field, validator
from datetime import datetime, timedelta

from infrastructure.adapters.auth import (
    create_access_token,
    decode_token,
    user_repo,
    TokenData,
    UserCreate,
    User,
)
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
    GetAccountsByOwnerQuery,
    GetContactQuery,
    ListContactsQuery,
    GetContactsByAccountQuery,
    GetOpportunityQuery,
    ListOpportunitiesQuery,
    GetOpportunitiesByAccountQuery,
    GetOpenOpportunitiesQuery,
    GetLeadQuery,
    ListLeadsQuery,
    GetCaseQuery,
    GetCaseByNumberQuery,
    ListCasesQuery,
    GetOpenCasesQuery,
    CreateAccountDTO,
    CreateContactDTO,
    CreateOpportunityDTO,
    CreateLeadDTO,
    CreateCaseDTO,
)
from infrastructure.mcp_servers.nexus_crm_server import (
    InMemoryAccountRepository,
    InMemoryContactRepository,
    InMemoryOpportunityRepository,
    InMemoryLeadRepository,
    InMemoryCaseRepository,
)
from infrastructure.adapters import (
    InMemoryEventBusAdapter,
    ConsoleAuditLogAdapter,
)
from infrastructure.adapters.security import (
    SecurityMiddleware,
    rate_limiter,
    ip_security,
    RateLimitTier,
)

app = FastAPI(
    title="Nexus CRM API",
    description="Salesforce Replacement CRM API",
    version="1.0.0",
)

app.add_middleware(
    SecurityMiddleware, rate_limiter=rate_limiter, ip_security=ip_security
)
rate_limiter.configure("default", RateLimitTier.STANDARD)
ip_security.enable()

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> TokenData:
    token = credentials.credentials
    token_data = decode_token(token)
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid token")
    return token_data


def require_role(allowed_roles: List[str]):
    async def role_checker(
        current_user: TokenData = Depends(get_current_user),
    ) -> TokenData:
        if current_user.role not in allowed_roles and current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user

    return role_checker


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict


@app.post("/auth/register", response_model=User)
async def register(request: LoginRequest):
    existing = await user_repo.get_by_email(request.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = await user_repo.create_user(
        UserCreate(
            email=request.email,
            password=request.password,
            name=request.email.split("@")[0],
        )
    )
    return user


@app.post("/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    user = await user_repo.get_by_email(request.email)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not await user_repo.verify_password(user.id, request.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(
        data={"sub": user.id, "email": user.email, "role": user.role},
        expires_delta=timedelta(hours=24),
    )

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user={"id": user.id, "email": user.email, "role": user.role},
    )


account_repo = InMemoryAccountRepository()
contact_repo = InMemoryContactRepository()
opportunity_repo = InMemoryOpportunityRepository()
lead_repo = InMemoryLeadRepository()
case_repo = InMemoryCaseRepository()
event_bus = InMemoryEventBusAdapter()
audit_log = ConsoleAuditLogAdapter()


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
    name: str
    industry: str = Field(..., pattern="|".join(INDUSTRIES))
    territory: str = Field(..., pattern="|".join(TERRITORIES))
    owner_id: str
    website: Optional[str] = None
    phone: Optional[str] = None
    billing_address: Optional[str] = None
    annual_revenue: Optional[float] = Field(None, ge=0)
    currency: str = "USD"
    employee_count: Optional[int] = Field(None, ge=0)

    @validator("industry")
    def validate_industry(cls, v):
        if v not in INDUSTRIES:
            raise ValueError(f"Industry must be one of: {', '.join(INDUSTRIES)}")
        return v

    @validator("territory")
    def validate_territory(cls, v):
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
    account_id: str
    first_name: str
    last_name: str
    email: EmailStr
    owner_id: str
    phone: Optional[str] = None
    title: Optional[str] = None
    department: Optional[str] = None


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
    account_id: str
    name: str
    amount: float
    currency: str
    close_date: datetime
    owner_id: str
    source: Optional[str] = None
    contact_id: Optional[str] = None
    description: Optional[str] = None


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
    first_name: str
    last_name: str
    email: EmailStr
    company: str
    owner_id: str
    source: Optional[str] = None
    phone: Optional[str] = None
    title: Optional[str] = None
    website: Optional[str] = None


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


class CreateCaseRequest(BaseModel):
    subject: str
    description: str
    account_id: str
    owner_id: str
    case_number: str
    contact_id: Optional[str] = None
    priority: str = "medium"
    origin: str = "web"

    @validator("priority")
    def validate_priority(cls, v):
        if v not in PRIORITIES:
            raise ValueError(f"Priority must be one of: {', '.join(PRIORITIES)}")
        return v

    @validator("origin")
    def validate_origin(cls, v):
        if v not in ORIGINS:
            raise ValueError(f"Origin must be one of: {', '.join(ORIGINS)}")
        return v


@app.get("/")
async def root():
    return {"message": "Nexus CRM API", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/accounts", response_model=AccountResponse)
async def create_account(
    request: CreateAccountRequest,
    current_user: TokenData = Depends(require_role(["admin", "manager", "sales_rep"])),
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
    return result


@app.get("/accounts", response_model=List[AccountResponse])
async def list_accounts(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: TokenData = Depends(get_current_user),
):
    query = ListAccountsQuery(repository=account_repo)
    return await query.execute(limit, offset)


@app.get("/accounts/{account_id}", response_model=AccountResponse)
async def get_account(
    account_id: str,
    current_user: TokenData = Depends(get_current_user),
):
    query = GetAccountQuery(repository=account_repo)
    result = await query.execute(account_id)
    if not result:
        raise HTTPException(status_code=404, detail="Account not found")
    return result


@app.put("/accounts/{account_id}", response_model=AccountResponse)
async def update_account(
    account_id: str,
    request: CreateAccountRequest,
    current_user: TokenData = Depends(require_role(["admin", "manager", "sales_rep"])),
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
    try:
        result = await command.execute(account_id, dto, request.owner_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/contacts", response_model=ContactResponse)
async def create_contact(
    request: CreateContactRequest,
    current_user: TokenData = Depends(require_role(["admin", "manager", "sales_rep"])),
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
    return result


@app.get("/contacts", response_model=List[ContactResponse])
async def list_contacts(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: TokenData = Depends(get_current_user),
):
    query = ListContactsQuery(repository=contact_repo)
    return await query.execute(limit, offset)


@app.get("/contacts/{contact_id}", response_model=ContactResponse)
async def get_contact(
    contact_id: str,
    current_user: TokenData = Depends(get_current_user),
):
    query = GetContactQuery(repository=contact_repo)
    result = await query.execute(contact_id)
    if not result:
        raise HTTPException(status_code=404, detail="Contact not found")
    return result


@app.get("/accounts/{account_id}/contacts", response_model=List[ContactResponse])
async def get_account_contacts(
    account_id: str,
    current_user: TokenData = Depends(get_current_user),
):
    query = GetContactsByAccountQuery(repository=contact_repo)
    return await query.execute(account_id)


@app.post("/opportunities", response_model=OpportunityResponse)
async def create_opportunity(
    request: CreateOpportunityRequest,
    current_user: TokenData = Depends(require_role(["admin", "manager", "sales_rep"])),
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
    return result


@app.get("/opportunities", response_model=List[OpportunityResponse])
async def list_opportunities(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: TokenData = Depends(get_current_user),
):
    query = ListOpportunitiesQuery(repository=opportunity_repo)
    return await query.execute(limit, offset)


@app.get("/opportunities/{opportunity_id}", response_model=OpportunityResponse)
async def get_opportunity(
    opportunity_id: str,
    current_user: TokenData = Depends(get_current_user),
):
    query = GetOpportunityQuery(repository=opportunity_repo)
    result = await query.execute(opportunity_id)
    if not result:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return result


@app.get("/opportunities/open", response_model=List[OpportunityResponse])
async def get_open_opportunities(
    current_user: TokenData = Depends(get_current_user),
):
    query = GetOpenOpportunitiesQuery(repository=opportunity_repo)
    return await query.execute()


@app.patch("/opportunities/{opportunity_id}/stage")
async def update_opportunity_stage(
    opportunity_id: str,
    stage: str,
    user_id: str,
    reason: Optional[str] = None,
    current_user: TokenData = Depends(require_role(["admin", "manager", "sales_rep"])),
):
    command = UpdateOpportunityStageCommand(
        repository=opportunity_repo,
        event_bus=event_bus,
        audit_log=audit_log,
    )
    result = await command.execute(opportunity_id, stage, user_id, reason)
    return result


@app.post("/leads", response_model=LeadResponse)
async def create_lead(
    request: CreateLeadRequest,
    current_user: TokenData = Depends(
        require_role(["admin", "manager", "sales_rep", "marketing_user"])
    ),
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
    return result


@app.get("/leads", response_model=List[LeadResponse])
async def list_leads(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: TokenData = Depends(get_current_user),
):
    query = ListLeadsQuery(repository=lead_repo)
    return await query.execute(limit, offset)


@app.get("/leads/{lead_id}", response_model=LeadResponse)
async def get_lead(
    lead_id: str,
    current_user: TokenData = Depends(get_current_user),
):
    query = GetLeadQuery(repository=lead_repo)
    result = await query.execute(lead_id)
    if not result:
        raise HTTPException(status_code=404, detail="Lead not found")
    return result


@app.post("/leads/{lead_id}/qualify")
async def qualify_lead(
    lead_id: str,
    user_id: str,
    current_user: TokenData = Depends(require_role(["admin", "manager", "sales_rep"])),
):
    command = QualifyLeadCommand(
        repository=lead_repo,
        event_bus=event_bus,
        audit_log=audit_log,
    )
    result = await command.execute(lead_id, user_id)
    return result


@app.post("/cases", response_model=CaseResponse)
async def create_case(
    request: CreateCaseRequest,
    current_user: TokenData = Depends(
        require_role(["admin", "manager", "support_user"])
    ),
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
    return result


@app.get("/cases", response_model=List[CaseResponse])
async def list_cases(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    current_user: TokenData = Depends(get_current_user),
):
    query = ListCasesQuery(repository=case_repo)
    return await query.execute(limit, offset)


@app.get("/cases/{case_id}", response_model=CaseResponse)
async def get_case(
    case_id: str,
    current_user: TokenData = Depends(get_current_user),
):
    query = GetCaseQuery(repository=case_repo)
    result = await query.execute(case_id)
    if not result:
        raise HTTPException(status_code=404, detail="Case not found")
    return result


@app.get("/cases/open", response_model=List[CaseResponse])
async def get_open_cases(
    current_user: TokenData = Depends(get_current_user),
):
    query = GetOpenCasesQuery(repository=case_repo)
    return await query.execute()


@app.patch("/cases/{case_id}/status")
async def update_case_status(
    case_id: str,
    status: str,
    user_id: str,
    current_user: TokenData = Depends(
        require_role(["admin", "manager", "support_user"])
    ),
):
    command = UpdateCaseStatusCommand(
        repository=case_repo,
        event_bus=event_bus,
        audit_log=audit_log,
    )
    result = await command.execute(case_id, status, user_id)
    return result


@app.post("/cases/{case_id}/resolve")
async def resolve_case(
    case_id: str,
    resolution_notes: str,
    resolved_by: str,
    user_id: str,
    current_user: TokenData = Depends(
        require_role(["admin", "manager", "support_user"])
    ),
):
    command = ResolveCaseCommand(
        repository=case_repo,
        event_bus=event_bus,
        audit_log=audit_log,
    )
    result = await command.execute(case_id, resolution_notes, resolved_by, user_id)
    return result
