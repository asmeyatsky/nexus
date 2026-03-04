"""
Rate Limiting & Security

Architectural Intent:
- API rate limiting per user/org
- IP allowlisting
- DDoS protection configuration
"""

from typing import Dict, Optional, Set
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import ipaddress
import json
import time
import threading
from collections import defaultdict


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

# Maximum number of rate limiter buckets before triggering cleanup
_MAX_BUCKETS = 100_000
# Buckets idle for longer than this (seconds) are considered stale
_STALE_BUCKET_AGE = 600  # 10 minutes


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


def _validate_ip_address(ip: str) -> str:
    """Validate and normalize an IP address string.

    Raises ValueError if the string is not a valid IPv4 or IPv6 address.
    """
    addr = ipaddress.ip_address(ip)
    return str(addr)


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

    def _cleanup_stale_buckets(self):
        """Remove buckets that have been idle longer than _STALE_BUCKET_AGE.

        Must be called while holding self._lock.
        """
        now = time.time()
        stale_keys = [
            key
            for key, bucket in self._buckets.items()
            if now - bucket.get("last_update", 0) > _STALE_BUCKET_AGE
        ]
        for key in stale_keys:
            del self._buckets[key]

    def check_rate_limit(
        self,
        identifier: str,
        org_id: str = None,
    ) -> tuple[bool, Dict]:
        config = self._config.get(identifier)
        if not config:
            limits = RATE_LIMITS[RateLimitTier.FREE]
            config = RateLimitConfig(
                requests=limits["requests"],
                window=limits["window"],
                burst=limits["requests"] * 2,
            )

        bucket_key = f"{org_id}:{identifier}" if org_id else identifier
        now = time.time()

        with self._lock:
            # Periodically clean up stale buckets to prevent unbounded memory growth
            if len(self._buckets) > _MAX_BUCKETS:
                self._cleanup_stale_buckets()

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


class RedisRateLimiter:
    """Redis-backed token bucket rate limiter.

    Bucket state is stored as JSON under ``rate:{org_id}:{identifier}`` so it
    is shared across all application instances and survives restarts.
    Falls back gracefully (allow) on any Redis error.
    """

    def __init__(self, redis_client):
        self._redis = redis_client
        self._config: Dict[str, RateLimitConfig] = {}

    def configure(self, identifier: str, tier: RateLimitTier):
        limits = RATE_LIMITS[tier]
        self._config[identifier] = RateLimitConfig(
            requests=limits["requests"],
            window=limits["window"],
            burst=limits["requests"] * 2,
        )

    async def check_rate_limit(
        self,
        identifier: str,
        org_id: str = None,
    ) -> tuple[bool, Dict]:
        config = self._config.get(identifier)
        if not config:
            limits = RATE_LIMITS[RateLimitTier.FREE]
            config = RateLimitConfig(
                requests=limits["requests"],
                window=limits["window"],
                burst=limits["requests"] * 2,
            )

        key = f"rate:{org_id}:{identifier}" if org_id else f"rate:{identifier}"
        now = time.time()
        refill_rate = config.requests / config.window

        try:
            raw = await self._redis.get(key)
            if raw:
                bucket = json.loads(raw)
                elapsed = now - bucket["last_update"]
                bucket["tokens"] = min(
                    config.burst, bucket["tokens"] + elapsed * refill_rate
                )
            else:
                bucket = {"tokens": float(config.burst), "last_update": now}

            bucket["last_update"] = now

            if bucket["tokens"] >= 1:
                bucket["tokens"] -= 1
                await self._redis.set(key, json.dumps(bucket), ex=config.window * 2)
                return True, {
                    "remaining": int(bucket["tokens"]),
                    "reset_at": now + config.window,
                    "limit": config.requests,
                }
            else:
                await self._redis.set(key, json.dumps(bucket), ex=config.window * 2)
                retry_after = int((1 - bucket["tokens"]) / refill_rate)
                return False, {
                    "remaining": 0,
                    "reset_at": now + retry_after,
                    "limit": config.requests,
                    "retry_after": retry_after,
                }
        except Exception:
            # Fail open: allow the request rather than blocking on Redis errors
            return True, {
                "remaining": config.requests,
                "reset_at": now + config.window,
                "limit": config.requests,
            }

    async def reset(self, identifier: str, org_id: str = None):
        key = f"rate:{org_id}:{identifier}" if org_id else f"rate:{identifier}"
        try:
            await self._redis.delete(key)
        except Exception:
            pass


class IPSecurity:
    """IP allowlisting and blocklisting."""

    def __init__(self):
        self._allowed_ips: Set[str] = set()
        self._blocked_ips: Set[str] = set()
        self._rules: Dict[str, IPRule] = {}
        self._lock = threading.Lock()
        self._enabled = True  # Enabled by default for security

    def enable(self):
        self._enabled = True

    def disable(self):
        self._enabled = False

    def add_allowed_ip(self, ip: str, description: str = ""):
        ip = _validate_ip_address(ip)
        with self._lock:
            self._allowed_ips.add(ip)
            self._rules[ip] = IPRule(ip, "allow", description)

    def add_blocked_ip(
        self, ip: str, description: str = "", expires_at: datetime = None
    ):
        ip = _validate_ip_address(ip)
        with self._lock:
            self._blocked_ips.add(ip)
            self._rules[ip] = IPRule(ip, "block", description, expires_at)

    def remove_ip(self, ip: str):
        with self._lock:
            self._allowed_ips.discard(ip)
            self._blocked_ips.discard(ip)
            self._rules.pop(ip, None)

    def _is_block_expired(self, ip: str) -> bool:
        """Check if a blocked IP's rule has expired."""
        rule = self._rules.get(ip)
        if rule and rule.expires_at and rule.expires_at <= datetime.now():
            return True
        return False

    def check_ip(self, ip: str) -> tuple[bool, str]:
        if not self._enabled:
            return True, "allowed"

        with self._lock:
            if ip in self._blocked_ips:
                # Check if the block has expired
                if self._is_block_expired(ip):
                    self._blocked_ips.discard(ip)
                    self._rules.pop(ip, None)
                    # Fall through to allowlist check
                else:
                    return False, "blocked"

            if self._allowed_ips and ip not in self._allowed_ips:
                return False, "not_allowed"

            return True, "allowed"

    def get_allowed_ips(self) -> list:
        return list(self._allowed_ips)

    def get_blocked_ips(self) -> list:
        return list(self._blocked_ips)


class RedisIPSecurity:
    """Redis-backed IP allowlist / blocklist.

    Allowed IPs are stored in a Redis set ``ip_security:allowed``.
    Blocked IPs are stored in a Redis set ``ip_security:blocked``.
    Falls back to allowing all traffic on any Redis error.
    """

    def __init__(self, redis_client):
        self._redis = redis_client
        self._enabled = True

    def enable(self):
        self._enabled = True

    def disable(self):
        self._enabled = False

    async def add_allowed_ip(self, ip: str, description: str = ""):
        ip = _validate_ip_address(ip)
        try:
            await self._redis.sadd("ip_security:allowed", ip)
        except Exception:
            pass

    async def add_blocked_ip(
        self, ip: str, description: str = "", expires_at: datetime = None
    ):
        ip = _validate_ip_address(ip)
        try:
            await self._redis.sadd("ip_security:blocked", ip)
        except Exception:
            pass

    async def remove_ip(self, ip: str):
        try:
            await self._redis.srem("ip_security:allowed", ip)
            await self._redis.srem("ip_security:blocked", ip)
        except Exception:
            pass

    async def check_ip(self, ip: str) -> tuple[bool, str]:
        if not self._enabled:
            return True, "allowed"

        try:
            if await self._redis.sismember("ip_security:blocked", ip):
                return False, "blocked"

            allowed_count = await self._redis.scard("ip_security:allowed")
            if allowed_count and not await self._redis.sismember(
                "ip_security:allowed", ip
            ):
                return False, "not_allowed"
        except Exception:
            # Fail open on Redis errors
            return True, "allowed"

        return True, "allowed"

    async def get_allowed_ips(self) -> list:
        try:
            members = await self._redis.smembers("ip_security:allowed")
            return [m.decode() if isinstance(m, bytes) else m for m in members]
        except Exception:
            return []

    async def get_blocked_ips(self) -> list:
        try:
            members = await self._redis.smembers("ip_security:blocked")
            return [m.decode() if isinstance(m, bytes) else m for m in members]
        except Exception:
            return []


def _create_rate_limiter():
    import os

    redis_url = os.environ.get("REDIS_URL", "")
    env = os.environ.get("ENVIRONMENT", "")
    if redis_url and env != "test":
        try:
            import redis.asyncio as aioredis

            client = aioredis.from_url(redis_url)
            return RedisRateLimiter(client)
        except Exception:
            pass
    return RateLimiter()


def _create_ip_security():
    import os

    redis_url = os.environ.get("REDIS_URL", "")
    env = os.environ.get("ENVIRONMENT", "")
    if redis_url and env != "test":
        try:
            import redis.asyncio as aioredis

            client = aioredis.from_url(redis_url)
            return RedisIPSecurity(client)
        except Exception:
            pass
    return IPSecurity()


rate_limiter = _create_rate_limiter()
ip_security = _create_ip_security()


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

        # Use client IP for rate limiting -- never trust spoofable headers
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
