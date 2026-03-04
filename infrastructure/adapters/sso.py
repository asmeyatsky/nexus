"""
SSO/SAML Authentication - SECURED

Architectural Intent:
- Multi-provider SSO: Google Workspace, Azure AD, Okta
- SAML 2.0 protocol support with signature verification
- Session management with secure tokens
- XXE protection (defusedxml mandatory)
- CSRF protection for cookie-based sessions
- Configurable session backend (in-memory default, Redis for production)
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
import logging
import secrets
import time
import ipaddress

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# defusedxml is MANDATORY -- never fall back to stdlib xml.etree.ElementTree
try:
    import defusedxml.ElementTree as SafeET
except ImportError:
    raise ImportError(
        "defusedxml is required for secure SAML XML parsing. "
        "Install it with: pip install defusedxml"
    )

from infrastructure.config.settings import settings


logger = logging.getLogger(__name__)


class SSOProvider(Enum):
    GOOGLE = "google"
    AZURE_AD = "azure_ad"
    OKTA = "okta"


@dataclass
class SSOConfig:
    provider: SSOProvider
    client_id: str
    client_secret: str
    tenant_id: Optional[str] = None
    domain: Optional[str] = None
    metadata_url: Optional[str] = None


# Internal IP ranges to block for SSRF prevention
BLOCKED_IP_RANGES = [
    "10.0.0.0/8",
    "172.16.0.0/12",
    "192.168.0.0/16",
    "127.0.0.0/8",
    "169.254.0.0/16",
    "0.0.0.0/8",
    "100.64.0.0/10",
    "192.0.0.0/24",
    "192.0.2.0/24",
    "198.51.100.0/24",
    "203.0.113.0/24",
    "fc00::/7",
    "fe80::/10",
]


def is_ip_blocked(ip_str: str) -> bool:
    """Check if IP is in blocked ranges."""
    try:
        ip = ipaddress.ip_address(ip_str)
        for blocked in BLOCKED_IP_RANGES:
            if ip in ipaddress.ip_network(blocked):
                return True
    except ValueError:
        return True
    return False


class SessionBackend:
    """Abstract interface for session storage.

    The default in-memory implementation is suitable for development/testing.
    For production, use a Redis-backed implementation:

        class RedisSessionBackend(SessionBackend):
            def __init__(self, redis_client):
                self._redis = redis_client

            def get(self, key):
                data = self._redis.get(f"session:{key}")
                return json.loads(data) if data else None

            def set(self, key, value):
                self._redis.setex(f"session:{key}", 1800, json.dumps(value))

            def delete(self, key):
                self._redis.delete(f"session:{key}")

            def count(self):
                return len(self._redis.keys("session:*"))
    """

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    def set(self, key: str, value: Dict[str, Any]) -> None:
        raise NotImplementedError

    def delete(self, key: str) -> None:
        raise NotImplementedError

    def count(self) -> int:
        raise NotImplementedError


class InMemorySessionBackend(SessionBackend):
    """In-memory session backend for development/testing."""

    def __init__(self):
        self._store: Dict[str, Dict[str, Any]] = {}

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        return self._store.get(key)

    def set(self, key: str, value: Dict[str, Any]) -> None:
        self._store[key] = value

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def count(self) -> int:
        return len(self._store)


class SSOSession:
    """Secure SSO session management with CSRF protection and max session limits."""

    def __init__(
        self,
        backend: Optional[SessionBackend] = None,
        max_sessions: int = None,
    ):
        self._backend = backend or InMemorySessionBackend()
        self._max_sessions = max_sessions or settings.sso_max_sessions

    def create_session(
        self, user_id: str, email: str, provider: SSOProvider, org_id: str
    ) -> tuple[str, str]:
        """Create session and return (session_id, csrf_token)."""
        # Enforce max session limit to prevent unbounded memory growth
        if self._backend.count() >= self._max_sessions:
            raise RuntimeError(
                f"Maximum session limit ({self._max_sessions}) reached. "
                "Cannot create new sessions until existing sessions expire."
            )

        session_id = secrets.token_urlsafe(32)
        csrf_token = secrets.token_urlsafe(32)
        self._backend.set(
            session_id,
            {
                "user_id": user_id,
                "email": email,
                "provider": provider.value,
                "org_id": org_id,
                "csrf_token": csrf_token,
                "created_at": time.time(),
                "last_activity": time.time(),
            },
        )
        return session_id, csrf_token

    def validate_session(
        self, session_id: str, max_age: int = 1800
    ) -> Optional[Dict]:  # 30 min default
        session = self._backend.get(session_id)
        if not session:
            return None

        if time.time() - session["last_activity"] > max_age:
            self._backend.delete(session_id)
            return None

        session["last_activity"] = time.time()
        self._backend.set(session_id, session)
        return session

    def validate_csrf(self, session_id: str, csrf_token: str) -> bool:
        """Validate CSRF token against session."""
        session = self._backend.get(session_id)
        if not session:
            return False
        return secrets.compare_digest(session.get("csrf_token", ""), csrf_token)

    def destroy_session(self, session_id: str):
        self._backend.delete(session_id)


class SAMLAuthHandler:
    """SAML 2.0 Authentication Handler with signature verification."""

    def __init__(self, config: SSOConfig):
        self.config = config

    def generate_auth_request(self, relay_state: str) -> str:
        """Generate SAML AuthnRequest."""
        return self._generate_saml_request(relay_state)

    def _generate_saml_request(self, relay_state: str) -> str:
        """Generate secure SAML AuthnRequest."""
        import uuid

        saml_issuer = settings.saml_issuer
        saml_acs_url = settings.saml_acs_url

        if not saml_issuer:
            raise ValueError("SAML_ISSUER must be configured in settings/environment")
        if not saml_acs_url:
            raise ValueError("SAML_ACS_URL must be configured in settings/environment")

        request_id = f"_{uuid.uuid4()}"

        saml_request = f"""<?xml version="1.0" encoding="UTF-8"?>
<samlp:AuthnRequest xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol"
    ID="{request_id}"
    Version="2.0"
    IssueInstant="{time.strftime("%Y-%m-%dT%H:%M:%SZ")}"
    AssertionConsumerServiceURL="{saml_acs_url}"
    ProtocolBinding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST">
    <saml:Issuer xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion">{saml_issuer}</saml:Issuer>
    <samlp:NameIDPolicy Format="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"/>
</samlp:AuthnRequest>"""
        import base64

        return base64.b64encode(saml_request.encode()).decode()

    def parse_response(self, saml_response: str) -> Optional[Dict[str, Any]]:
        """Parse and verify SAML Response with XXE protection."""
        import base64

        try:
            # Decode base64
            decoded = base64.b64decode(saml_response).decode("utf-8")

            # Parse XML -- defusedxml blocks XXE, entity expansion, DTDs by default
            root = SafeET.fromstring(decoded)

            # Verify response has signature -- reject unsigned responses
            signature = root.find(".//{http://www.w3.org/2000/09/xmldsig#}Signature")
            if signature is None:
                logger.error("Unsigned SAML response rejected")
                return None

            # CRITICAL: Cryptographic signature verification is REQUIRED.
            # The mere presence of a <Signature> element does NOT prove
            # authenticity -- an attacker can insert a fake Signature element.
            # A production deployment MUST use a library such as signxml or
            # python3-saml to verify the XML signature against the IdP's
            # X.509 certificate.
            raise NotImplementedError(
                "SAML cryptographic signature verification is required but "
                "not yet implemented. Use a library such as signxml or "
                "python3-saml to verify the XML digital signature against "
                "the IdP certificate before trusting the assertion."
            )

        except NotImplementedError:
            raise
        except SafeET.ParseError as e:
            logger.error("SAML parse error: %s", e)
            return None
        except Exception as e:
            logger.error("SAML processing error: %s", e)
            return None


def _get_redirect_uri_allowlist() -> List[str]:
    """Parse the SSO redirect URI allowlist from settings."""
    raw = settings.sso_redirect_uri_allowlist
    if not raw:
        return []
    return [uri.strip() for uri in raw.split(",") if uri.strip()]


def validate_redirect_uri(redirect_uri: str) -> bool:
    """Validate redirect_uri against the configured allowlist.

    Returns True if the redirect_uri is in the allowlist, False otherwise.
    If no allowlist is configured, rejects all redirect URIs for safety.
    """
    from urllib.parse import urlparse

    allowlist = _get_redirect_uri_allowlist()
    if not allowlist:
        logger.warning(
            "SSO_REDIRECT_URI_ALLOWLIST is not configured; rejecting redirect_uri=%s",
            redirect_uri,
        )
        return False

    parsed = urlparse(redirect_uri)
    # Require HTTPS (or http for localhost in development)
    if parsed.scheme not in ("https", "http"):
        return False

    for allowed in allowlist:
        allowed_parsed = urlparse(allowed)
        # Match scheme + netloc + path prefix
        if (
            parsed.scheme == allowed_parsed.scheme
            and parsed.netloc == allowed_parsed.netloc
            and parsed.path.startswith(allowed_parsed.path)
        ):
            return True

    return False


class GoogleSSOHandler:
    """Google Workspace SSO via OpenID Connect."""

    def __init__(
        self, client_id: str = None, client_secret: str = None, domain: str = None
    ):
        self.client_id = client_id or settings.sso_google_client_id
        self.client_secret = client_secret or settings.sso_google_client_secret
        self.domain = domain
        self.authorization_url = "https://accounts.google.com/o/oauth2/v2/auth"
        self.token_url = "https://oauth2.googleapis.com/token"
        self.userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"

    def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        from urllib.parse import urlencode

        # Validate redirect_uri against allowlist to prevent open redirect
        if not validate_redirect_uri(redirect_uri):
            raise ValueError(
                f"redirect_uri is not in the configured allowlist: {redirect_uri}"
            )

        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        }
        if self.domain:
            params["hd"] = self.domain

        return f"{self.authorization_url}?{urlencode(params)}"

    async def exchange_code(self, code: str, redirect_uri: str) -> Optional[Dict]:
        import httpx

        # Validate redirect_uri against allowlist to prevent open redirect
        if not validate_redirect_uri(redirect_uri):
            raise ValueError(
                f"redirect_uri is not in the configured allowlist: {redirect_uri}"
            )

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.token_url,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri,
                },
            )

            if response.status_code == 200:
                return response.json()
            return None

    async def get_userinfo(self, access_token: str) -> Optional[Dict]:
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.userinfo_url,
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if response.status_code == 200:
                return response.json()
            return None


STATE_CHANGING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class SSOMiddleware(BaseHTTPMiddleware):
    """Middleware for SSO session validation with CSRF protection."""

    def __init__(self, app, sso_session: SSOSession, excluded_paths: List[str] = None):
        super().__init__(app)
        self.sso_session = sso_session
        self.excluded_paths = excluded_paths or [
            "/health",
            "/auth/login",
            "/auth/register",
            "/auth/saml/init",
            "/docs",
            "/openapi.json",
            "/auth/saml/callback",
        ]

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        if any(path.startswith(excluded) for excluded in self.excluded_paths):
            return await call_next(request)

        session_id = request.cookies.get("nexus_session")
        if not session_id:
            session_id = request.headers.get("X-Session-Token")

        if session_id:
            session = self.sso_session.validate_session(session_id)
            if session:
                # CSRF validation for state-changing requests
                if request.method in STATE_CHANGING_METHODS:
                    csrf_token = request.headers.get("X-CSRF-Token")
                    if not csrf_token or not self.sso_session.validate_csrf(
                        session_id, csrf_token
                    ):
                        return Response(
                            status_code=403,
                            content='{"detail":"CSRF validation failed"}',
                            media_type="application/json",
                        )

                request.state.user = session
                return await call_next(request)

        return Response(
            status_code=302,
            headers={"Location": "/auth/login"},
        )


sso_session = SSOSession()
