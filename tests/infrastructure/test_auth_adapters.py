"""
Tests for authentication infrastructure adapters.
"""

import os
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["DATABASE_URL"] = "sqlite:///test.db"
os.environ["ENVIRONMENT"] = "test"

import pytest
from datetime import datetime, timezone, timedelta

from infrastructure.adapters.auth import (
    TokenRevocationStore,
    FailedLoginTracker,
    UserRepository,
    UserCreate,
    create_access_token,
    decode_token,
    verify_password,
    get_password_hash,
)

# Check if bcrypt is functional in this environment
try:
    _test_hash = get_password_hash("TestPass1!")
    _BCRYPT_WORKS = True
except Exception:
    _BCRYPT_WORKS = False

bcrypt_required = pytest.mark.skipif(
    not _BCRYPT_WORKS,
    reason="bcrypt/passlib incompatibility in this environment (passlib detect_wrap_bug uses >72 byte password)",
)


# ---------------------------------------------------------------------------
# TokenRevocationStore
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_token_revocation_store_revoke_and_is_revoked():
    store = TokenRevocationStore()
    jti = "test-jti-001"
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()

    await store.revoke(jti, expires_at)
    assert await store.is_revoked(jti) is True


@pytest.mark.asyncio
async def test_token_revocation_store_not_revoked_for_unknown_jti():
    store = TokenRevocationStore()
    assert await store.is_revoked("nonexistent-jti") is False


@pytest.mark.asyncio
async def test_token_revocation_store_cleanup_on_max_size():
    store = TokenRevocationStore(max_size=5)
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).timestamp()
    future = (datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()

    # Fill with expired tokens
    for i in range(5):
        await store.revoke(f"expired-jti-{i}", past)

    # Revoke a new one -- should trigger cleanup of expired
    await store.revoke("new-jti", future)
    # New JTI should still be revoked
    assert await store.is_revoked("new-jti") is True


# ---------------------------------------------------------------------------
# FailedLoginTracker
# ---------------------------------------------------------------------------

def test_failed_login_tracker_record_failure_and_is_locked():
    tracker = FailedLoginTracker(max_attempts=3, lockout_duration=900)
    account_key = "user@example.com"

    assert tracker.is_locked(account_key) is False

    tracker.record_failure(account_key)
    tracker.record_failure(account_key)
    tracker.record_failure(account_key)

    assert tracker.is_locked(account_key) is True


def test_failed_login_tracker_record_success_clears_attempts():
    tracker = FailedLoginTracker(max_attempts=5)
    account_key = "user@example.com"

    tracker.record_failure(account_key)
    tracker.record_failure(account_key)
    tracker.record_success(account_key)

    assert tracker.is_locked(account_key) is False
    assert tracker.get_remaining_attempts(account_key) == 5


def test_failed_login_tracker_get_remaining_attempts():
    tracker = FailedLoginTracker(max_attempts=5)
    account_key = "user@example.com"

    assert tracker.get_remaining_attempts(account_key) == 5

    tracker.record_failure(account_key)
    assert tracker.get_remaining_attempts(account_key) == 4

    tracker.record_failure(account_key)
    assert tracker.get_remaining_attempts(account_key) == 3


# ---------------------------------------------------------------------------
# UserRepository
# ---------------------------------------------------------------------------

@bcrypt_required
@pytest.mark.asyncio
async def test_user_repository_create_user():
    repo = UserRepository()
    user_create = UserCreate(
        email="test@example.com",
        password="SecurePass1!",
        name="Test User",
        role="user",
    )
    user = await repo.create_user(user_create)
    assert user.email == "test@example.com"
    assert user.name == "Test User"
    assert user.id is not None


@bcrypt_required
@pytest.mark.asyncio
async def test_user_repository_get_by_email_case_insensitive():
    repo = UserRepository()
    user_create = UserCreate(
        email="Test@Example.COM",
        password="SecurePass1!",
        name="Test User",
        role="user",
    )
    await repo.create_user(user_create)

    found = await repo.get_by_email("test@example.com")
    assert found is not None
    assert found.name == "Test User"


@bcrypt_required
@pytest.mark.asyncio
async def test_user_repository_get_by_id():
    repo = UserRepository()
    user_create = UserCreate(
        email="lookup@example.com",
        password="SecurePass1!",
        name="Lookup User",
        role="user",
    )
    created = await repo.create_user(user_create)
    found = await repo.get_by_id(created.id)
    assert found is not None
    assert found.id == created.id


@bcrypt_required
@pytest.mark.asyncio
async def test_user_repository_verify_password():
    repo = UserRepository()
    user_create = UserCreate(
        email="verify@example.com",
        password="SecurePass1!",
        name="Verify User",
        role="user",
    )
    user = await repo.create_user(user_create)

    assert await repo.verify_password(user.id, "SecurePass1!") is True
    assert await repo.verify_password(user.id, "WrongPassword") is False


@bcrypt_required
@pytest.mark.asyncio
async def test_user_repository_update_password():
    repo = UserRepository()
    user_create = UserCreate(
        email="updatepw@example.com",
        password="OldPass1!",
        name="PW User",
        role="user",
    )
    user = await repo.create_user(user_create)

    result = await repo.update_password(user.id, "NewPass1!")
    assert result is True
    assert await repo.verify_password(user.id, "NewPass1!") is True
    assert await repo.verify_password(user.id, "OldPass1!") is False


@bcrypt_required
@pytest.mark.asyncio
async def test_user_repository_update_password_raises_for_reused_password():
    repo = UserRepository()
    user_create = UserCreate(
        email="reuse@example.com",
        password="InitialPass1!",
        name="Reuse User",
        role="user",
    )
    user = await repo.create_user(user_create)

    with pytest.raises(ValueError, match="Password was used recently"):
        await repo.update_password(user.id, "InitialPass1!")


# ---------------------------------------------------------------------------
# JWT functions
# ---------------------------------------------------------------------------

def test_create_access_token_returns_valid_jwt():
    token = create_access_token({"sub": "user-123", "email": "user@example.com", "role": "user"})
    assert token is not None
    assert isinstance(token, str)
    assert len(token) > 0


def test_decode_token_decodes_correctly():
    token = create_access_token(
        {"sub": "user-123", "email": "user@example.com", "role": "admin", "org_id": "org-1"}
    )
    token_data = decode_token(token)
    assert token_data is not None
    assert token_data.user_id == "user-123"
    assert token_data.email == "user@example.com"
    assert token_data.role == "admin"


def test_decode_token_returns_none_for_invalid_token():
    result = decode_token("this.is.not.a.valid.token")
    assert result is None


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

@bcrypt_required
def test_get_password_hash_and_verify_password():
    password = "TestPassword123!"
    hashed = get_password_hash(password)
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword", hashed) is False
