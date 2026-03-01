"""
Authentication Module - SECURED

Architectural Intent:
- JWT-based authentication
- Password hashing with bcrypt
- Role-based access control
- Password policy enforcement
"""

from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4
import re

from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, validator
from fastapi import HTTPException, status

from infrastructure.config.settings import settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TokenData(BaseModel):
    user_id: str
    email: str
    role: str


class User(BaseModel):
    id: str
    email: str
    name: str
    role: str
    is_active: bool = True


class UserCreate(BaseModel):
    email: str
    password: str
    name: str
    role: str = "user"

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
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire})
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
        if user_id is None:
            return None
        return TokenData(user_id=user_id, email=email, role=role)
    except JWTError:
        return None


def require_role(user_role: str, required_roles: list[str]) -> bool:
    return user_role in required_roles or user_role == "admin"


class UserRepository:
    """Secure user repository with encrypted password storage."""

    def __init__(self):
        self._users: dict = {}
        self._passwords: dict = {}

    async def create_user(self, user: UserCreate) -> User:
        user_id = str(uuid4())
        hashed = get_password_hash(user.password)

        new_user = User(
            id=user_id,
            email=user.email,
            name=user.name,
            role=user.role,
        )
        self._users[user_id] = new_user
        self._passwords[user_id] = hashed
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
        self._passwords[user_id] = get_password_hash(new_password)
        return True


user_repo = UserRepository()
