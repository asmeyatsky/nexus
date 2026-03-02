"""
Authentication Module - SECURED

Architectural Intent:
- JWT-based authentication with JTI for revocation
- Password hashing with bcrypt
- Role-based access control
- Password policy enforcement
- Token revocation via Redis
- Password history tracking
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, List
from uuid import uuid4
import re

from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, validator

from infrastructure.config.settings import settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

DEFAULT_ORG_ID = "00000000-0000-0000-0000-000000000000"


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

    @validator("password")
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
    except JWTError:
        return None


def require_role(user_role: str, required_roles: list[str]) -> bool:
    return user_role in required_roles or user_role == "admin"


class TokenRevocationStore:
    """In-memory token revocation store. Use Redis in production."""

    def __init__(self):
        self._revoked_jtis: dict[str, float] = {}

    async def revoke(self, jti: str, expires_at: float):
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
