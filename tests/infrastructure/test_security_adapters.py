"""
Tests for security infrastructure adapters (rate limiter, IP security).
"""

import os
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["DATABASE_URL"] = "sqlite:///test.db"
os.environ["ENVIRONMENT"] = "test"

import pytest
from infrastructure.adapters.security import (
    RateLimiter,
    IPSecurity,
    RateLimitTier,
    _validate_ip_address,
)


# ---------------------------------------------------------------------------
# RateLimiter
# ---------------------------------------------------------------------------

def test_rate_limiter_initial_state_allows_requests():
    limiter = RateLimiter()
    allowed, info = limiter.check_rate_limit("user-1")
    assert allowed is True
    assert "remaining" in info
    assert "limit" in info


def test_rate_limiter_exhaustion_returns_false():
    limiter = RateLimiter()
    limiter.configure("test-user", RateLimitTier.FREE)
    # FREE tier = 100 requests per 60s, burst = 200
    # Exhaust the burst tokens
    for _ in range(201):
        limiter.check_rate_limit("test-user")

    allowed, info = limiter.check_rate_limit("test-user")
    assert allowed is False
    assert info["remaining"] == 0


def test_rate_limiter_reset_works():
    limiter = RateLimiter()
    limiter.configure("user-reset", RateLimitTier.FREE)
    # Exhaust tokens
    for _ in range(201):
        limiter.check_rate_limit("user-reset")

    allowed_before, _ = limiter.check_rate_limit("user-reset")
    assert allowed_before is False

    limiter.reset("user-reset")
    allowed_after, _ = limiter.check_rate_limit("user-reset")
    assert allowed_after is True


def test_rate_limiter_configure_with_different_tiers():
    limiter = RateLimiter()
    limiter.configure("free-user", RateLimitTier.FREE)
    limiter.configure("enterprise-user", RateLimitTier.ENTERPRISE)

    # Both should allow first request
    allowed_free, info_free = limiter.check_rate_limit("free-user")
    allowed_ent, info_ent = limiter.check_rate_limit("enterprise-user")

    assert allowed_free is True
    assert allowed_ent is True
    # Enterprise should have higher limit
    assert info_ent["limit"] > info_free["limit"]


def test_rate_limiter_with_org_id():
    limiter = RateLimiter()
    allowed, info = limiter.check_rate_limit("user-1", org_id="org-abc")
    assert allowed is True


# ---------------------------------------------------------------------------
# IPSecurity
# ---------------------------------------------------------------------------

def test_ip_security_add_allowed_ip():
    security = IPSecurity()
    security.add_allowed_ip("192.168.1.100")
    assert "192.168.1.100" in security.get_allowed_ips()


def test_ip_security_add_blocked_ip():
    security = IPSecurity()
    security.add_blocked_ip("10.0.0.5")
    assert "10.0.0.5" in security.get_blocked_ips()


def test_ip_security_check_ip_blocked():
    security = IPSecurity()
    security.add_blocked_ip("10.0.0.5")
    allowed, reason = security.check_ip("10.0.0.5")
    assert allowed is False
    assert reason == "blocked"


def test_ip_security_check_ip_allowed():
    security = IPSecurity()
    security.add_allowed_ip("192.168.1.100")
    allowed, reason = security.check_ip("192.168.1.100")
    assert allowed is True
    assert reason == "allowed"


def test_ip_security_check_ip_not_in_allowlist():
    security = IPSecurity()
    security.add_allowed_ip("192.168.1.100")
    # IP not in allowlist should be blocked when allowlist is active
    allowed, reason = security.check_ip("10.0.0.99")
    assert allowed is False
    assert reason == "not_allowed"


def test_ip_security_enable_disable():
    security = IPSecurity()
    security.add_blocked_ip("10.0.0.5")

    # Verify blocked when enabled
    allowed, _ = security.check_ip("10.0.0.5")
    assert allowed is False

    # Disable security - should allow all
    security.disable()
    allowed, reason = security.check_ip("10.0.0.5")
    assert allowed is True

    # Re-enable
    security.enable()
    allowed, _ = security.check_ip("10.0.0.5")
    assert allowed is False


def test_ip_security_remove_ip():
    security = IPSecurity()
    security.add_blocked_ip("10.0.0.5")
    security.remove_ip("10.0.0.5")
    assert "10.0.0.5" not in security.get_blocked_ips()


def test_validate_ip_address_valid_ipv4():
    result = _validate_ip_address("192.168.1.1")
    assert result == "192.168.1.1"


def test_validate_ip_address_valid_ipv6():
    result = _validate_ip_address("::1")
    assert result == "::1"


def test_validate_ip_address_invalid_raises_value_error():
    with pytest.raises(ValueError):
        _validate_ip_address("not.an.ip.address.x")


def test_validate_ip_address_invalid_octets():
    with pytest.raises(ValueError):
        _validate_ip_address("999.999.999.999")


def test_rate_limiter_no_config_uses_free_tier_defaults():
    """Without configure(), limiter uses FREE tier defaults."""
    limiter = RateLimiter()
    allowed, info = limiter.check_rate_limit("unconfigured-user")
    assert allowed is True
    assert info["limit"] == 100  # FREE tier limit
