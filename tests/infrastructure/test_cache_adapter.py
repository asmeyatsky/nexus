"""
Tests for Redis cache adapter (graceful degradation without Redis).
"""

import os

os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["DATABASE_URL"] = "sqlite:///test.db"
os.environ["ENVIRONMENT"] = "test"

import pytest

from infrastructure.adapters.cache import RedisCache, CacheTier, _escape_glob


# ---------------------------------------------------------------------------
# RedisCache graceful degradation (no Redis connection)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_redis_cache_without_connection_returns_none_on_get():
    # Redis URL pointing to a non-existent server
    cache = RedisCache(redis_url="redis://localhost:9999")
    # _client is None until connect() is called
    result = await cache.get("some-key")
    assert result is None


@pytest.mark.asyncio
async def test_redis_cache_without_connection_is_noop_on_set():
    cache = RedisCache(redis_url="redis://localhost:9999")
    # Should not raise even without a connection
    await cache.set("some-key", {"data": "value"})


def test_redis_cache_generate_key_produces_correct_format():
    cache = RedisCache()
    key = cache.generate_key(CacheTier.QUERY, "org-123", "accounts", "page-1")
    assert key.startswith("nexus:query:org-123:")
    # Key should contain a hash suffix
    parts = key.split(":")
    assert len(parts) == 4
    assert parts[0] == "nexus"
    assert parts[1] == "query"
    assert parts[2] == "org-123"
    # Hash should be 12 characters
    assert len(parts[3]) == 12


# ---------------------------------------------------------------------------
# CacheTier enum values
# ---------------------------------------------------------------------------


def test_cache_tier_enum_values():
    assert CacheTier.SESSION.value == "session"
    assert CacheTier.QUERY.value == "query"
    assert CacheTier.COMPUTED.value == "computed"
    assert CacheTier.STATIC.value == "static"


# ---------------------------------------------------------------------------
# _escape_glob
# ---------------------------------------------------------------------------


def test_escape_glob_escapes_asterisk():
    result = _escape_glob("acct*123")
    assert "[*]" in result


def test_escape_glob_escapes_question_mark():
    result = _escape_glob("acct?123")
    assert "[?]" in result


def test_escape_glob_escapes_brackets():
    result = _escape_glob("acct[123]")
    assert "[[" in result or "[[]" in result


def test_escape_glob_no_special_chars_unchanged():
    result = _escape_glob("regular-key-123")
    assert result == "regular-key-123"
