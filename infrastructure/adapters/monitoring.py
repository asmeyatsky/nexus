"""
Monitoring, Metrics & Observability

Architectural Intent:
- Structured JSON logging with correlation ID support
- In-memory Prometheus-style metrics collection
- Health checks for dependency monitoring
- ASGI tracing middleware for request lifecycle
"""

from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import asyncio
import contextvars
import json
import logging
import os
import time
import threading
import uuid


# ---------------------------------------------------------------------------
# 1. Structured Logging
# ---------------------------------------------------------------------------

_correlation_id_var = contextvars.ContextVar("correlation_id", default=None)


class _CorrelationIdStorage:
    """Asyncio-safe correlation ID storage using contextvars."""

    def get(self) -> Optional[str]:
        return _correlation_id_var.get()

    def set(self, value: Optional[str]) -> None:
        _correlation_id_var.set(value)


correlation_id_ctx = _CorrelationIdStorage()


class StructuredJsonFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        correlation_id = correlation_id_ctx.get()
        if correlation_id:
            log_entry["correlation_id"] = correlation_id

        if record.exc_info and record.exc_info[1] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Merge any extra fields attached via the `extra` kwarg.
        for key in (
            "request_method",
            "request_path",
            "status_code",
            "duration_ms",
            "event_type",
            "component",
            "detail",
        ):
            value = getattr(record, key, None)
            if value is not None:
                log_entry[key] = value

        return json.dumps(log_entry, default=str)


def setup_logging(
    level: int = logging.INFO,
    logger_name: Optional[str] = None,
) -> logging.Logger:
    """Configure and return a logger that emits structured JSON.

    Call once at application startup for root configuration, or pass a
    *logger_name* to configure a child logger independently.

    Args:
        level: Minimum log level (default ``logging.INFO``).
        logger_name: Optional logger name; ``None`` configures the root logger.

    Returns:
        The configured :class:`logging.Logger` instance.
    """
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)

    # Avoid adding duplicate handlers when called multiple times.
    if not any(
        isinstance(h, logging.StreamHandler)
        and isinstance(h.formatter, StructuredJsonFormatter)
        for h in logger.handlers
    ):
        handler = logging.StreamHandler()
        handler.setFormatter(StructuredJsonFormatter())
        logger.addHandler(handler)

    return logger


# ---------------------------------------------------------------------------
# 2. Prometheus-style In-Memory Metrics
# ---------------------------------------------------------------------------


class _Counter:
    """Thread-safe monotonically increasing counter."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._values: Dict[tuple, float] = {}

    def inc(self, labels: Dict[str, str], value: float = 1.0) -> None:
        key = tuple(sorted(labels.items()))
        with self._lock:
            self._values[key] = self._values.get(key, 0.0) + value

    def get(self, labels: Optional[Dict[str, str]] = None) -> float:
        if labels is not None:
            key = tuple(sorted(labels.items()))
            with self._lock:
                return self._values.get(key, 0.0)
        with self._lock:
            return sum(self._values.values())

    def collect(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [{"labels": dict(k), "value": v} for k, v in self._values.items()]


class _Gauge:
    """Thread-safe gauge that can go up and down."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._values: Dict[tuple, float] = {}

    def inc(self, labels: Optional[Dict[str, str]] = None, value: float = 1.0) -> None:
        key = tuple(sorted((labels or {}).items()))
        with self._lock:
            self._values[key] = self._values.get(key, 0.0) + value

    def dec(self, labels: Optional[Dict[str, str]] = None, value: float = 1.0) -> None:
        self.inc(labels, -value)

    def set(self, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        key = tuple(sorted((labels or {}).items()))
        with self._lock:
            self._values[key] = value

    def get(self, labels: Optional[Dict[str, str]] = None) -> float:
        key = tuple(sorted((labels or {}).items()))
        with self._lock:
            return self._values.get(key, 0.0)

    def collect(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [{"labels": dict(k), "value": v} for k, v in self._values.items()]


# Default histogram buckets (seconds), matching Prometheus defaults.
_DEFAULT_BUCKETS = (
    0.005,
    0.01,
    0.025,
    0.05,
    0.1,
    0.25,
    0.5,
    1.0,
    2.5,
    5.0,
    10.0,
    float("inf"),
)


class _Histogram:
    """Thread-safe histogram with configurable buckets."""

    def __init__(self, buckets: tuple = _DEFAULT_BUCKETS) -> None:
        self._lock = threading.Lock()
        self._buckets = buckets
        # Per-label-set data: {"bucket_counts": [...], "sum": float, "count": int}
        self._data: Dict[tuple, Dict[str, Any]] = {}

    def _ensure(self, key: tuple) -> Dict[str, Any]:
        if key not in self._data:
            self._data[key] = {
                "bucket_counts": [0] * len(self._buckets),
                "sum": 0.0,
                "count": 0,
            }
        return self._data[key]

    def observe(self, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        key = tuple(sorted((labels or {}).items()))
        with self._lock:
            d = self._ensure(key)
            d["sum"] += value
            d["count"] += 1
            for i, bound in enumerate(self._buckets):
                if value <= bound:
                    d["bucket_counts"][i] += 1

    def collect(self) -> List[Dict[str, Any]]:
        with self._lock:
            results = []
            for key, d in self._data.items():
                buckets_out = {
                    str(b): c for b, c in zip(self._buckets, d["bucket_counts"])
                }
                results.append(
                    {
                        "labels": dict(key),
                        "buckets": buckets_out,
                        "count": d["count"],
                        "sum": d["sum"],
                    }
                )
            return results


class MetricsCollector:
    """Central registry of application metrics.

    Uses simple in-memory counters, gauges, and histograms -- no external
    dependencies required.

    Attributes:
        http_requests_total: Counter keyed by (method, path, status).
        http_request_duration_seconds: Histogram keyed by (method, path).
        active_connections: Gauge (label-free by default).
        domain_events_total: Counter keyed by (event_type,).
    """

    def __init__(self) -> None:
        self.http_requests_total = _Counter()
        self.http_request_duration_seconds = _Histogram()
        self.active_connections = _Gauge()
        self.domain_events_total = _Counter()

    # -- convenience helpers --------------------------------------------------

    def record_request(
        self, method: str, path: str, status: int, duration: float
    ) -> None:
        """Record a completed HTTP request in one call."""
        labels = {"method": method, "path": path, "status": str(status)}
        self.http_requests_total.inc(labels)
        self.http_request_duration_seconds.observe(
            duration, {"method": method, "path": path}
        )

    def record_domain_event(self, event_type: str) -> None:
        """Increment the domain event counter for *event_type*."""
        self.domain_events_total.inc({"event_type": event_type})

    def snapshot(self) -> Dict[str, Any]:
        """Return a JSON-serialisable snapshot of all metrics."""
        return {
            "http_requests_total": self.http_requests_total.collect(),
            "http_request_duration_seconds": self.http_request_duration_seconds.collect(),
            "active_connections": self.active_connections.collect(),
            "domain_events_total": self.domain_events_total.collect(),
        }

    def to_prometheus_format(self) -> str:
        """Return metrics in Prometheus text exposition format."""
        lines: List[str] = []

        # http_requests_total counter
        lines.append("# HELP http_requests_total Total HTTP requests")
        lines.append("# TYPE http_requests_total counter")
        for entry in self.http_requests_total.collect():
            labels = ",".join(f'{k}="{v}"' for k, v in sorted(entry["labels"].items()))
            lines.append(f"http_requests_total{{{labels}}} {entry['value']}")

        # http_request_duration_seconds histogram
        lines.append("# HELP http_request_duration_seconds HTTP request duration")
        lines.append("# TYPE http_request_duration_seconds histogram")
        for entry in self.http_request_duration_seconds.collect():
            labels = ",".join(f'{k}="{v}"' for k, v in sorted(entry["labels"].items()))
            for bucket, count in entry.get("buckets", {}).items():
                lines.append(f'http_request_duration_seconds_bucket{{{labels},le="{bucket}"}} {count}')
            lines.append(f"http_request_duration_seconds_sum{{{labels}}} {entry['sum']}")
            lines.append(f"http_request_duration_seconds_count{{{labels}}} {entry['count']}")

        # active_connections gauge
        lines.append("# HELP active_connections Current active connections")
        lines.append("# TYPE active_connections gauge")
        for entry in self.active_connections.collect():
            labels = ",".join(f'{k}="{v}"' for k, v in sorted(entry["labels"].items()))
            label_str = f"{{{labels}}}" if labels else ""
            lines.append(f"active_connections{label_str} {entry['value']}")

        # domain_events_total counter
        lines.append("# HELP domain_events_total Total domain events")
        lines.append("# TYPE domain_events_total counter")
        for entry in self.domain_events_total.collect():
            labels = ",".join(f'{k}="{v}"' for k, v in sorted(entry["labels"].items()))
            lines.append(f"domain_events_total{{{labels}}} {entry['value']}")

        return "\n".join(lines) + "\n"


# Module-level singleton so all components share one collector.
metrics = MetricsCollector()


# ---------------------------------------------------------------------------
# 3. Health Check
# ---------------------------------------------------------------------------


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class CheckResult:
    name: str
    status: HealthStatus
    latency_ms: float = 0.0
    detail: Optional[str] = None


class HealthChecker:
    """Aggregates dependency health checks and reports overall status.

    Args:
        version: Application version string included in the response.
        db_url: Database connection URL for the database check.
        redis_url: Redis connection URL for the Redis check.
        external_urls: Mapping of service name -> URL for external checks.
    """

    def __init__(
        self,
        version: str = "0.0.0",
        db_url: Optional[str] = None,
        redis_url: Optional[str] = None,
        external_urls: Optional[Dict[str, str]] = None,
    ) -> None:
        self.version = version
        self.db_url = db_url or os.getenv("DATABASE_URL", "")
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.external_urls = external_urls or {}

    # -- individual checks ---------------------------------------------------

    async def _check_database(self) -> CheckResult:
        """Verify database connectivity with a lightweight query."""
        start = time.monotonic()
        try:
            # Import lazily to avoid hard dependency.
            import asyncpg  # type: ignore[import-untyped]

            conn = await asyncio.wait_for(asyncpg.connect(self.db_url), timeout=5.0)
            try:
                await conn.fetchval("SELECT 1")
            finally:
                await conn.close()

            latency = (time.monotonic() - start) * 1000
            return CheckResult(
                name="database",
                status=HealthStatus.HEALTHY,
                latency_ms=round(latency, 2),
            )
        except Exception as exc:
            latency = (time.monotonic() - start) * 1000
            return CheckResult(
                name="database",
                status=HealthStatus.UNHEALTHY,
                latency_ms=round(latency, 2),
                detail=str(exc),
            )

    async def _check_redis(self) -> CheckResult:
        """Verify Redis connectivity with a PING."""
        start = time.monotonic()
        try:
            import redis.asyncio as aioredis  # type: ignore[import-untyped]

            client = aioredis.from_url(self.redis_url, socket_timeout=5.0)
            try:
                await client.ping()
            finally:
                await client.aclose()

            latency = (time.monotonic() - start) * 1000
            return CheckResult(
                name="redis",
                status=HealthStatus.HEALTHY,
                latency_ms=round(latency, 2),
            )
        except Exception as exc:
            latency = (time.monotonic() - start) * 1000
            return CheckResult(
                name="redis",
                status=HealthStatus.UNHEALTHY,
                latency_ms=round(latency, 2),
                detail=str(exc),
            )

    async def _check_external(self, name: str, url: str) -> CheckResult:
        """Check reachability of an external HTTP service."""
        start = time.monotonic()
        try:
            import httpx  # type: ignore[import-untyped]

            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(url)
                latency = (time.monotonic() - start) * 1000
                status = (
                    HealthStatus.HEALTHY
                    if resp.status_code < 500
                    else HealthStatus.UNHEALTHY
                )
                return CheckResult(
                    name=name,
                    status=status,
                    latency_ms=round(latency, 2),
                    detail=f"HTTP {resp.status_code}",
                )
        except Exception as exc:
            latency = (time.monotonic() - start) * 1000
            return CheckResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                latency_ms=round(latency, 2),
                detail=str(exc),
            )

    # -- aggregate -----------------------------------------------------------

    async def check_health(self) -> Dict[str, Any]:
        """Run all checks concurrently and return an aggregate report.

        Returns:
            A dict with keys ``status``, ``checks``, ``version``, and
            ``timestamp``.  ``status`` is the worst status across all checks.
        """
        tasks: List[asyncio.Task] = []

        if self.db_url:
            tasks.append(asyncio.ensure_future(self._check_database()))
        if self.redis_url:
            tasks.append(asyncio.ensure_future(self._check_redis()))
        for svc_name, svc_url in self.external_urls.items():
            tasks.append(asyncio.ensure_future(self._check_external(svc_name, svc_url)))

        results: List[CheckResult] = await asyncio.gather(*tasks) if tasks else []

        # Derive overall status: worst-case wins.
        priority = {
            HealthStatus.HEALTHY: 0,
            HealthStatus.DEGRADED: 1,
            HealthStatus.UNHEALTHY: 2,
        }
        overall = HealthStatus.HEALTHY
        for r in results:
            if priority[r.status] > priority[overall]:
                overall = r.status

        return {
            "status": overall.value,
            "checks": [
                {
                    "name": r.name,
                    "status": r.status.value,
                    "latency_ms": r.latency_ms,
                    **({"detail": r.detail} if r.detail else {}),
                }
                for r in results
            ],
            "version": self.version,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        }


# ---------------------------------------------------------------------------
# 4. ASGI Tracing Middleware
# ---------------------------------------------------------------------------


class TracingMiddleware:
    """ASGI middleware that adds per-request tracing and metrics.

    For every incoming HTTP request this middleware will:
    1. Generate (or propagate) a correlation/request ID.
    2. Store the ID in ``request.state`` (Starlette convention) and set it on
       the context-var :data:`correlation_id_ctx` so that downstream log
       calls automatically include it.
    3. Log structured entries for request start and end (with timing).
    4. Append an ``X-Request-ID`` response header.
    5. Record request duration and status in the module-level :data:`metrics`
       collector.

    Args:
        app: The ASGI application to wrap.
        header_name: Name of the header used to carry the correlation ID.
    """

    REQUEST_ID_HEADER = "x-request-id"

    def __init__(self, app: Any, header_name: str = "X-Request-ID") -> None:
        self.app = app
        self.header_name = header_name
        self._header_name_lower = header_name.lower().encode("latin-1")
        self._header_name_bytes = header_name.encode("latin-1")
        self.logger = setup_logging(logger_name="nexus.tracing")

    async def __call__(
        self, scope: Dict[str, Any], receive: Callable, send: Callable
    ) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        # --- Extract or generate correlation ID ---
        headers = dict(scope.get("headers", []))
        request_id = headers.get(self._header_name_lower, b"").decode("latin-1")
        if not request_id:
            request_id = uuid.uuid4().hex

        # Make available to downstream loggers.
        correlation_id_ctx.set(request_id)

        # Attach to scope state (Starlette-compatible).
        if "state" not in scope:
            scope["state"] = {}
        scope["state"]["correlation_id"] = request_id

        method = scope.get("method", "WS")
        path = scope.get("path", "/")

        metrics.active_connections.inc()
        start = time.monotonic()

        self.logger.info(
            "Request started",
            extra={
                "request_method": method,
                "request_path": path,
                "component": "tracing",
            },
        )

        status_code = 500  # default in case of unhandled error

        async def send_wrapper(message: Dict[str, Any]) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 200)
                # Inject correlation ID into response headers.
                response_headers = list(message.get("headers", []))
                response_headers.append(
                    (self._header_name_bytes, request_id.encode("latin-1"))
                )
                message = {**message, "headers": response_headers}
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            status_code = 500
            raise
        finally:
            duration = time.monotonic() - start
            metrics.active_connections.dec()
            metrics.record_request(method, path, status_code, duration)

            self.logger.info(
                "Request completed",
                extra={
                    "request_method": method,
                    "request_path": path,
                    "status_code": status_code,
                    "duration_ms": round(duration * 1000, 2),
                    "component": "tracing",
                },
            )

            # Clean up context-var correlation ID.
            correlation_id_ctx.set(None)
