"""
Rate Limiting & Security

Architectural Intent:
- API rate limiting per user/org
- IP allowlisting
- DDoS protection configuration
"""

from typing import Dict, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import time
import threading
from collections import defaultdict
import hashlib


class RateLimitTier(Enum):
    FREE = "free"
    STANDARD = "standard"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


RATE_LIMITS = {
    RateLimitTier.FREE: {"requests": 100, "window": 60},
    RateLimitTier.STANDARD: {"requests": 1000, "window": 60},
    RateLimitTier.PREMIUM: {"requests": 10000, "window": 60},
    RateLimitTier.ENTERPRISE: {"requests": 100000, "window": 60},
}


@dataclass
class RateLimitConfig:
    requests: int
    window: int
    burst: int = 0


@dataclass
class IPRule:
    ip_address: str
    rule_type: str
    description: str = ""
    expires_at: Optional[datetime] = None


class RateLimiter:
    """Token bucket rate limiter with per-org and per-user limits."""

    def __init__(self):
        self._buckets: Dict[str, Dict] = defaultdict(dict)
        self._lock = threading.Lock()
        self._config: Dict[str, RateLimitConfig] = {}

    def configure(self, identifier: str, tier: RateLimitTier):
        limits = RATE_LIMITS[tier]
        self._config[identifier] = RateLimitConfig(
            requests=limits["requests"],
            window=limits["window"],
            burst=limits["requests"] * 2,
        )

    def check_rate_limit(
        self,
        identifier: str,
        org_id: str = None,
    ) -> tuple[bool, Dict]:
        config = self._config.get(identifier)
        if not config:
            config = RateLimitConfig(
                requests=RATE_LIMITS[RateLimitTier.FREE]["requests"],
                window=RATE_LIMITS[RateLimitTier.FREE]["window"],
            )

        bucket_key = f"{org_id}:{identifier}" if org_id else identifier
        now = time.time()

        with self._lock:
            if bucket_key not in self._buckets:
                self._buckets[bucket_key] = {
                    "tokens": config.burst,
                    "last_update": now,
                }

            bucket = self._buckets[bucket_key]
            elapsed = now - bucket["last_update"]
            refill_rate = config.requests / config.window

            bucket["tokens"] = min(
                config.burst, bucket["tokens"] + elapsed * refill_rate
            )
            bucket["last_update"] = now

            if bucket["tokens"] >= 1:
                bucket["tokens"] -= 1
                return True, {
                    "remaining": int(bucket["tokens"]),
                    "reset_at": now + config.window,
                    "limit": config.requests,
                }
            else:
                retry_after = int((1 - bucket["tokens"]) / refill_rate)
                return False, {
                    "remaining": 0,
                    "reset_at": now + retry_after,
                    "limit": config.requests,
                    "retry_after": retry_after,
                }

    def reset(self, identifier: str, org_id: str = None):
        bucket_key = f"{org_id}:{identifier}" if org_id else identifier
        with self._lock:
            self._buckets.pop(bucket_key, None)


class IPSecurity:
    """IP allowlisting and blocklisting."""

    def __init__(self):
        self._allowed_ips: Set[str] = set()
        self._blocked_ips: Set[str] = set()
        self._rules: Dict[str, IPRule] = {}
        self._lock = threading.Lock()
        self._enabled = False

    def enable(self):
        self._enabled = True

    def disable(self):
        self._enabled = False

    def add_allowed_ip(self, ip: str, description: str = ""):
        with self._lock:
            self._allowed_ips.add(ip)
            self._rules[ip] = IPRule(ip, "allow", description)

    def add_blocked_ip(
        self, ip: str, description: str = "", expires_at: datetime = None
    ):
        with self._lock:
            self._blocked_ips.add(ip)
            self._rules[ip] = IPRule(ip, "block", description, expires_at)

    def remove_ip(self, ip: str):
        with self._lock:
            self._allowed_ips.discard(ip)
            self._blocked_ips.discard(ip)
            self._rules.pop(ip, None)

    def check_ip(self, ip: str) -> tuple[bool, str]:
        if not self._enabled:
            return True, "allowed"

        with self._lock:
            if ip in self._blocked_ips:
                return False, "blocked"

            if self._allowed_ips and ip not in self._allowed_ips:
                return False, "not_allowed"

            return True, "allowed"

    def get_allowed_ips(self) -> list:
        return list(self._allowed_ips)

    def get_blocked_ips(self) -> list:
        return list(self._blocked_ips)


rate_limiter = RateLimiter()
ip_security = IPSecurity()


class SecurityMiddleware:
    """Combined security middleware for rate limiting and IP filtering."""

    def __init__(self, app, rate_limiter: RateLimiter, ip_security: IPSecurity):
        self.app = app
        self.rate_limiter = rate_limiter
        self.ip_security = ip_security

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        from starlette.requests import Request
        from starlette.responses import JSONResponse

        request = Request(scope, receive)

        client_ip = request.client.host if request.client else "unknown"

        allowed, reason = self.ip_security.check_ip(client_ip)
        if not allowed:
            response = JSONResponse(
                {"error": "Access denied", "reason": reason},
                status_code=403,
            )
            await response(scope, receive, send)
            return

        # Use client IP for rate limiting — never trust spoofable headers
        user_id = client_ip
        org_id = "default"

        allowed, info = self.rate_limiter.check_rate_limit(user_id, org_id)
        if not allowed:
            response = JSONResponse(
                {
                    "error": "Rate limit exceeded",
                    "retry_after": info.get("retry_after", 60),
                },
                status_code=429,
                headers={
                    "X-RateLimit-Limit": str(info["limit"]),
                    "X-RateLimit-Remaining": str(info["remaining"]),
                    "X-RateLimit-Reset": str(info["reset_at"]),
                    "Retry-After": str(info.get("retry_after", 60)),
                },
            )
            await response(scope, receive, send)
            return

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                message["headers"].extend(
                    [
                        (b"X-RateLimit-Limit", str(info["limit"]).encode()),
                        (b"X-RateLimit-Remaining", str(info["remaining"]).encode()),
                    ]
                )
            await send(message)

        await self.app(scope, receive, send_wrapper)
