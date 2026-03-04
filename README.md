# Nexus CRM

![Uploading Generated Image March 04, 2026 - 4_58PM.jpg.jpeg…]()


Enterprise Salesforce replacement built on Google Cloud Platform. Nexus CRM provides full-lifecycle customer relationship management with accounts, contacts, opportunities, leads, and cases.

## Architecture

Nexus follows **hexagonal (ports & adapters) architecture** with DDD, CQRS, and event-driven patterns:

- **Domain Layer** — Entities, value objects, domain services, repository ports
- **Application Layer** — Commands (writes), queries (reads), DTOs, event handlers
- **Infrastructure Layer** — Repository implementations, adapters (auth, RBAC, monitoring, integrations), database, config
- **Presentation Layer** — FastAPI REST API, CLI

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.11 |
| Web Framework | FastAPI + Uvicorn |
| ORM | SQLAlchemy 2.0 |
| Database | PostgreSQL (asyncpg) |
| Cache | Redis |
| Auth | JWT (python-jose) + bcrypt |
| Migrations | Alembic |
| Cloud | Google Cloud Platform (GKE, Cloud SQL, Secret Manager) |
| CI/CD | GitHub Actions |
| Linting | Ruff |

## Project Structure

```
nexus/
├── domain/                     # Core business logic
│   ├── entities/               # Account, Contact, Opportunity, Lead, Case, ...
│   ├── value_objects/          # Email, Money, Industry, Territory, Phone
│   ├── services/               # Pricing, Deduplication, LeadScoring, Forecasting
│   ├── events/                 # Domain events
│   └── ports/                  # Repository & service interfaces
├── application/                # Use cases
│   ├── commands/               # Write operations (CQRS)
│   ├── queries/                # Read operations
│   ├── dtos/                   # Data transfer objects
│   ├── event_handlers/         # Event subscribers
│   └── orchestration/          # Saga / workflow orchestration
├── infrastructure/             # External concerns
│   ├── adapters/               # Auth, RBAC, monitoring, webhooks, integrations
│   ├── repositories/           # SQLAlchemy repository implementations
│   ├── config/                 # Settings, DI, Terraform
│   ├── mcp_servers/            # MCP server implementations
│   └── database.py             # Database engine setup
├── presentation/
│   ├── api/main.py             # FastAPI application
│   └── cli/                    # CLI tools
├── alembic/                    # Database migrations
├── tests/                      # Test suites
├── Dockerfile                  # Production container
├── requirements.txt            # Production dependencies
├── requirements-ci.txt         # CI/test dependencies
└── .github/workflows/          # CI/CD pipeline
```

## Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL 15+ (production) or SQLite (development)
- Redis 7+ (optional, for caching and token revocation)

### Installation

```bash
# Clone the repository
git clone <repo-url> && cd nexus

# Create virtual environment
python -m venv .venv && source .venv/bin/activate

# Install dependencies
pip install -r requirements-ci.txt
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `sqlite:///nexus.db` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379` |
| `JWT_SECRET_KEY` | Secret for JWT signing | *(required)* |
| `ENVIRONMENT` | `development`, `test`, or `production` | `development` |
| `CORS_ALLOWED_ORIGINS` | Comma-separated origins | `""` |

### Run Development Server

```bash
uvicorn presentation.api.main:app --reload --host 0.0.0.0 --port 8000
```

### Run Tests

```bash
pytest tests/ -v
```

## API Overview

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Register user (admin-only) |
| POST | `/auth/login` | Login, returns JWT |
| POST | `/auth/logout` | Revoke token |
| POST | `/auth/refresh` | Refresh JWT |
| POST | `/auth/change-password` | Change password |

### Accounts

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/accounts` | Create account |
| GET | `/accounts` | List accounts |
| GET | `/accounts/{id}` | Get account |
| PUT | `/accounts/{id}` | Update account |
| DELETE | `/accounts/{id}` | Delete account |
| POST | `/accounts/{id}/deactivate` | Deactivate account |

### Contacts

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/contacts` | Create contact |
| GET | `/contacts` | List contacts |
| GET | `/contacts/{id}` | Get contact |
| PUT | `/contacts/{id}` | Update contact |
| DELETE | `/contacts/{id}` | Delete contact |
| GET | `/accounts/{id}/contacts` | Contacts by account |

### Opportunities

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/opportunities` | Create opportunity |
| GET | `/opportunities` | List opportunities |
| GET | `/opportunities/{id}` | Get opportunity |
| PUT | `/opportunities/{id}` | Update opportunity |
| DELETE | `/opportunities/{id}` | Delete opportunity |
| GET | `/opportunities/open` | List open opportunities |
| PATCH | `/opportunities/{id}/stage` | Update stage |

### Leads

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/leads` | Create lead |
| GET | `/leads` | List leads |
| GET | `/leads/{id}` | Get lead |
| DELETE | `/leads/{id}` | Delete lead |
| POST | `/leads/{id}/qualify` | Qualify lead |
| POST | `/leads/{id}/convert` | Convert lead |

### Cases

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/cases` | Create case |
| GET | `/cases` | List cases |
| GET | `/cases/{id}` | Get case |
| DELETE | `/cases/{id}` | Delete case |
| GET | `/cases/open` | List open cases |
| PATCH | `/cases/{id}/status` | Update status |
| POST | `/cases/{id}/resolve` | Resolve case |
| POST | `/cases/{id}/close` | Close case |

### Monitoring

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check (DB, Redis, externals) |
| GET | `/metrics` | Prometheus-style metrics (requires `audit:view`) |

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=domain --cov=application --cov=infrastructure --cov=presentation

# Run specific suite
pytest tests/integration/ -v
pytest tests/domain/ -v
pytest tests/infrastructure/ -v
```

## Deployment

### Docker

```bash
docker build -t nexus-crm .
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/nexus \
  -e JWT_SECRET_KEY=your-secret \
  nexus-crm
```

### GitHub Actions CI/CD

The pipeline runs on every push:
1. **Lint** — `ruff check .` and `ruff format --check .`
2. **Test** — `pytest` with coverage
3. **Security Scan** — `bandit` static analysis
4. **Build** — Docker image to GCR (when `ENABLE_DEPLOY` repo variable is `true`)
5. **Deploy Staging** — Auto-deploy on `develop` branch
6. **Deploy Production** — Auto-deploy on `main`/`master` branch

### Required Secrets (for deployment)

| Secret | Description |
|--------|-------------|
| `GCP_SA_KEY` | GCP service account JSON key |
| `GCP_PROJECT_ID` | GCP project ID |

### GKE Cluster

The app deploys to a GKE cluster named `nexus-crm-cluster` in `europe-west2`. Namespaces: `staging` and `production`.
