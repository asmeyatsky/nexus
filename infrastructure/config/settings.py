"""
Secure Configuration

Architectural Intent:
- Centralized configuration with environment variables
- Secret management via GCP Secret Manager
- No hardcoded secrets
"""

import os
from typing import Optional
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    app_name: str = "Nexus CRM"
    debug: bool = False
    environment: str = "production"

    # Security - JWT
    jwt_secret_key: str = os.environ.get("JWT_SECRET_KEY", "")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30  # Reduced from 24 hours

    # Security - Password
    min_password_length: int = 12
    require_password_uppercase: bool = True
    require_password_lowercase: bool = True
    require_password_digit: bool = True
    require_password_special: bool = True

    # Database
    database_url: str = os.environ.get("DATABASE_URL", "")
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # Redis
    redis_url: str = os.environ.get("REDIS_URL", "redis://localhost:6379")

    # GCP
    gcp_project_id: str = os.environ.get("GCP_PROJECT_ID", "")
    gcp_region: str = os.environ.get("GCP_REGION", "europe-west2")

    # SSO
    sso_google_client_id: str = os.environ.get("SSO_GOOGLE_CLIENT_ID", "")
    sso_google_client_secret: str = os.environ.get("SSO_GOOGLE_CLIENT_SECRET", "")
    sso_azure_client_id: str = os.environ.get("SSO_AZURE_CLIENT_ID", "")
    sso_azure_client_secret: str = os.environ.get("SSO_AZURE_CLIENT_SECRET", "")
    sso_azure_tenant_id: str = os.environ.get("SSO_AZURE_TENANT_ID", "")
    sso_okta_domain: str = os.environ.get("SSO_OKTA_DOMAIN", "")
    sso_okta_api_key: str = os.environ.get("SSO_OKTA_API_KEY", "")

    # Rate Limiting
    rate_limit_requests: int = 1000
    rate_limit_window: int = 60

    # IP Security
    ip_allowlist_enabled: bool = True
    ip_blocklist_enabled: bool = True

    # CORS
    cors_allowed_origins: str = os.environ.get("CORS_ALLOWED_ORIGINS", "")
    cors_allow_credentials: bool = True

    # External Services
    salesforce_client_id: str = os.environ.get("SALESFORCE_CLIENT_ID", "")
    salesforce_client_secret: str = os.environ.get("SALESFORCE_CLIENT_SECRET", "")
    sendgrid_api_key: str = os.environ.get("SENDGRID_API_KEY", "")
    mailchimp_api_key: str = os.environ.get("MAILCHIMP_API_KEY", "")

    class Config:
        env_file = ".env"
        case_sensitive = False

    def validate_secrets(self):
        """Ensure critical secrets are not empty in any environment."""
        if not self.jwt_secret_key:
            raise ValueError("JWT_SECRET_KEY must be set")
        if not self.database_url:
            raise ValueError("DATABASE_URL must be set")

        if self.environment == "production":
            if not self.redis_url or self.redis_url == "redis://localhost:6379":
                raise ValueError("REDIS_URL must be explicitly set in production")
            required_prod = {
                "SSO_GOOGLE_CLIENT_ID": self.sso_google_client_id,
                "SSO_GOOGLE_CLIENT_SECRET": self.sso_google_client_secret,
                "SSO_AZURE_CLIENT_ID": self.sso_azure_client_id,
                "SSO_AZURE_CLIENT_SECRET": self.sso_azure_client_secret,
                "SSO_AZURE_TENANT_ID": self.sso_azure_tenant_id,
                "SSO_OKTA_DOMAIN": self.sso_okta_domain,
                "SSO_OKTA_API_KEY": self.sso_okta_api_key,
                "SENDGRID_API_KEY": self.sendgrid_api_key,
            }
            for name, value in required_prod.items():
                if not value:
                    raise ValueError(f"{name} must be set in production")


@lru_cache()
def get_settings() -> Settings:
    settings = Settings()
    settings.validate_secrets()
    return settings


settings = get_settings()
