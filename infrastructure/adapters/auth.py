"""
Authentication Module - SECURED

Architectural Intent:
- JWT-based authentication with JTI for revocation
- Password hashing with bcrypt
- Role-based access control
- Password policy enforcement
- Token revocation via Redis (in-memory fallback with max size + cleanup)
- Password history tracking
- Per-account failed login tracking with lockout
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, List
from uuid import uuid4
import logging
import re

import jwt
from jwt.exceptions import PyJWTError
from passlib.context import CryptContext
from pydantic import BaseModel, field_validator

from infrastructure.config.settings import settings


logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

DEFAULT_ORG_ID = "00000000-0000-0000-0000-000000000000"

# Token revocation store limits
_MAX_REVOKED_TOKENS = 100_000

# Account lockout settings
_MAX_FAILED_LOGIN_ATTEMPTS = 5
_LOCKOUT_DURATION_SECONDS = 900  # 15 minutes


class TokenData(BaseModel):
    user_id: str
    email: str
    role: str
    org_id: str = DEFAULT_ORG_ID
    jti: Optional[str] = None


class User(BaseModel):
    id: str
    email: str
    name: str
    role: str
    org_id: str = DEFAULT_ORG_ID
    is_active: bool = True


class UserCreate(BaseModel):
    email: str
    password: str
    name: str
    role: str = "user"
    org_id: str = DEFAULT_ORG_ID

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < settings.min_password_length:
            raise ValueError(
                f"Password must be at least {settings.min_password_length} characters"
            )
        if settings.require_password_uppercase and not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if settings.require_password_lowercase and not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if settings.require_password_digit and not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        if settings.require_password_special and not re.search(
            r"[!@#$%^&*(),.?\":{}|<>]", v
        ):
            raise ValueError("Password must contain at least one special character")
        return v


class Token(BaseModel):
    access_token: str
    token_type: str


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    jti = str(uuid4())
    to_encode.update({"exp": expire, "jti": jti})
    return jwt.encode(
        to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )


def decode_token(token: str) -> Optional[TokenData]:
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        user_id = payload.get("sub")
        email = payload.get("email")
        role = payload.get("role", "user")
        org_id = payload.get("org_id", DEFAULT_ORG_ID)
        jti = payload.get("jti")
        if user_id is None:
            return None
        return TokenData(
            user_id=user_id, email=email, role=role, org_id=org_id, jti=jti
        )
    except (PyJWTError, Exception):
        return None


def require_role(user_role: str, required_roles: list[str]) -> bool:
    return user_role in required_roles or user_role == "admin"


class TokenRevocationStore:
    """In-memory token revocation store with max size and automatic cleanup.

    TODO: For production, replace with a Redis-backed implementation:

        class RedisTokenRevocationStore:
            def __init__(self, redis_client):
                self._redis = redis_client

            async def revoke(self, jti: str, expires_at: float):
                ttl = int(expires_at - time.time())
                if ttl > 0:
                    await self._redis.setex(f"revoked:{jti}", ttl, "1")

            async def is_revoked(self, jti: str) -> bool:
                return await self._redis.exists(f"revoked:{jti}") > 0

    The in-memory store is kept as a fallback with bounded size.
    """

    def __init__(self, max_size: int = _MAX_REVOKED_TOKENS):
        self._revoked_jtis: dict[str, float] = {}
        self._max_size = max_size

    async def revoke(self, jti: str, expires_at: float):
        # Cleanup if approaching max size
        if len(self._revoked_jtis) >= self._max_size:
            self.cleanup_expired()

        # If still at max after cleanup, remove oldest entries
        if len(self._revoked_jtis) >= self._max_size:
            sorted_jtis = sorted(self._revoked_jtis.items(), key=lambda x: x[1])
            # Remove oldest 10%
            to_remove = max(1, self._max_size // 10)
            for jti_key, _ in sorted_jtis[:to_remove]:
                del self._revoked_jtis[jti_key]

        self._revoked_jtis[jti] = expires_at

    async def is_revoked(self, jti: str) -> bool:
        if jti in self._revoked_jtis:
            return True
        return False

    def cleanup_expired(self):
        now = datetime.now(timezone.utc).timestamp()
        expired = [jti for jti, exp in self._revoked_jtis.items() if exp < now]
        for jti in expired:
            del self._revoked_jtis[jti]


token_revocation_store = TokenRevocationStore()


class FailedLoginTracker:
    """Track failed login attempts per account and enforce lockout policy.

    After _MAX_FAILED_LOGIN_ATTEMPTS consecutive failures, the account is
    locked for _LOCKOUT_DURATION_SECONDS.
    """

    def __init__(
        self,
        max_attempts: int = _MAX_FAILED_LOGIN_ATTEMPTS,
        lockout_duration: int = _LOCKOUT_DURATION_SECONDS,
    ):
        # key: user_id or email -> {"count": int, "locked_until": float | None}
        self._attempts: dict[str, dict] = {}
        self._max_attempts = max_attempts
        self._lockout_duration = lockout_duration

    def is_locked(self, account_key: str) -> bool:
        """Check if the account is currently locked out."""
        record = self._attempts.get(account_key)
        if not record:
            return False
        locked_until = record.get("locked_until")
        if locked_until and datetime.now(timezone.utc).timestamp() < locked_until:
            return True
        # Lockout expired -- reset
        if locked_until and datetime.now(timezone.utc).timestamp() >= locked_until:
            del self._attempts[account_key]
        return False

    def record_failure(self, account_key: str):
        """Record a failed login attempt. Locks the account if threshold is reached."""
        if account_key not in self._attempts:
            self._attempts[account_key] = {"count": 0, "locked_until": None}

        record = self._attempts[account_key]
        record["count"] += 1

        if record["count"] >= self._max_attempts:
            record["locked_until"] = (
                datetime.now(timezone.utc).timestamp() + self._lockout_duration
            )
            logger.warning(
                "Account %s locked for %d seconds after %d failed attempts",
                account_key,
                self._lockout_duration,
                record["count"],
            )

    def record_success(self, account_key: str):
        """Clear failed login tracking on successful login."""
        self._attempts.pop(account_key, None)

    def get_remaining_attempts(self, account_key: str) -> int:
        """Return how many attempts remain before lockout."""
        record = self._attempts.get(account_key)
        if not record:
            return self._max_attempts
        return max(0, self._max_attempts - record["count"])


failed_login_tracker = FailedLoginTracker()

MAX_PASSWORD_HISTORY = 5


class UserRepository:
    """Secure user repository with encrypted password storage."""

    def __init__(self):
        self._users: dict = {}
        self._passwords: dict = {}
        self._password_history: dict[str, List[str]] = {}

    async def create_user(self, user: UserCreate) -> User:
        user_id = str(uuid4())
        hashed = get_password_hash(user.password)

        new_user = User(
            id=user_id,
            email=user.email,
            name=user.name,
            role=user.role,
            org_id=user.org_id,
        )
        self._users[user_id] = new_user
        self._passwords[user_id] = hashed
        self._password_history[user_id] = [hashed]
        return new_user

    async def get_by_email(self, email: str) -> Optional[User]:
        for user in self._users.values():
            if user.email.lower() == email.lower():
                return user
        return None

    async def get_by_id(self, user_id: str) -> Optional[User]:
        return self._users.get(user_id)

    async def verify_password(self, user_id: str, password: str) -> bool:
        hashed = self._passwords.get(user_id)
        if not hashed:
            return False
        return verify_password(password, hashed)

    async def update_password(self, user_id: str, new_password: str) -> bool:
        if user_id not in self._users:
            return False

        new_hash = get_password_hash(new_password)

        # Check password history
        history = self._password_history.get(user_id, [])
        for old_hash in history:
            if verify_password(new_password, old_hash):
                raise ValueError(
                    "Password was used recently. Choose a different password."
                )

        self._passwords[user_id] = new_hash

        # Update history
        history.append(new_hash)
        if len(history) > MAX_PASSWORD_HISTORY:
            history = history[-MAX_PASSWORD_HISTORY:]
        self._password_history[user_id] = history

        return True


user_repo = UserRepository()
