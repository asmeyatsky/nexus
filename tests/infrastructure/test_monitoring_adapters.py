"""
Tests for monitoring infrastructure adapters.
"""

import os
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["DATABASE_URL"] = "sqlite:///test.db"
os.environ["ENVIRONMENT"] = "test"

import json
import pytest
import logging

from infrastructure.adapters.monitoring import (
    MetricsCollector,
    _Counter,
    _Gauge,
    _Histogram,
    HealthChecker,
    setup_logging,
    StructuredJsonFormatter,
)


# ---------------------------------------------------------------------------
# MetricsCollector
# ---------------------------------------------------------------------------

def test_metrics_collector_record_request_increments_counter():
    m = MetricsCollector()
    m.record_request("GET", "/accounts", 200, 0.05)
    count = m.http_requests_total.get({"method": "GET", "path": "/accounts", "status": "200"})
    assert count == 1.0


def test_metrics_collector_record_multiple_requests():
    m = MetricsCollector()
    m.record_request("GET", "/accounts", 200, 0.05)
    m.record_request("GET", "/accounts", 200, 0.03)
    m.record_request("POST", "/accounts", 201, 0.1)

    count = m.http_requests_total.get({"method": "GET", "path": "/accounts", "status": "200"})
    assert count == 2.0


def test_metrics_collector_record_domain_event():
    m = MetricsCollector()
    m.record_domain_event("opportunity_won")
    m.record_domain_event("opportunity_won")
    m.record_domain_event("case_created")

    won_count = m.domain_events_total.get({"event_type": "opportunity_won"})
    assert won_count == 2.0


def test_metrics_collector_snapshot_returns_correct_structure():
    m = MetricsCollector()
    m.record_request("GET", "/leads", 200, 0.02)

    snapshot = m.snapshot()
    assert "http_requests_total" in snapshot
    assert "http_request_duration_seconds" in snapshot
    assert "active_connections" in snapshot
    assert "domain_events_total" in snapshot
    assert isinstance(snapshot["http_requests_total"], list)


def test_metrics_collector_to_prometheus_format_returns_valid_text():
    m = MetricsCollector()
    m.record_request("GET", "/health", 200, 0.01)
    m.record_domain_event("account_created")

    output = m.to_prometheus_format()
    assert isinstance(output, str)
    assert "# HELP http_requests_total" in output
    assert "# TYPE http_requests_total counter" in output
    assert "# HELP domain_events_total" in output
    assert output.endswith("\n")


# ---------------------------------------------------------------------------
# _Counter
# ---------------------------------------------------------------------------

def test_counter_inc_and_get():
    counter = _Counter()
    counter.inc({"method": "GET"})
    counter.inc({"method": "GET"}, value=2.0)
    counter.inc({"method": "POST"})

    assert counter.get({"method": "GET"}) == 3.0
    assert counter.get({"method": "POST"}) == 1.0
    assert counter.get() == 4.0  # total across all labels


def test_counter_collect_returns_entries():
    counter = _Counter()
    counter.inc({"status": "200"})
    counter.inc({"status": "404"})

    entries = counter.collect()
    assert len(entries) == 2


# ---------------------------------------------------------------------------
# _Gauge
# ---------------------------------------------------------------------------

def test_gauge_inc_dec_set_get():
    gauge = _Gauge()
    gauge.inc()
    gauge.inc(value=3.0)
    assert gauge.get() == 4.0

    gauge.dec(value=2.0)
    assert gauge.get() == 2.0

    gauge.set(10.0)
    assert gauge.get() == 10.0


def test_gauge_with_labels():
    gauge = _Gauge()
    gauge.set(5.0, labels={"region": "us"})
    gauge.set(3.0, labels={"region": "eu"})

    assert gauge.get(labels={"region": "us"}) == 5.0
    assert gauge.get(labels={"region": "eu"}) == 3.0


# ---------------------------------------------------------------------------
# _Histogram
# ---------------------------------------------------------------------------

def test_histogram_observe_and_collect():
    hist = _Histogram()
    hist.observe(0.1)
    hist.observe(0.5)
    hist.observe(2.0)

    entries = hist.collect()
    assert len(entries) == 1
    entry = entries[0]
    assert entry["count"] == 3
    assert entry["sum"] == pytest.approx(2.6)


def test_histogram_observe_with_labels():
    hist = _Histogram()
    hist.observe(0.05, labels={"path": "/api"})
    hist.observe(0.2, labels={"path": "/api"})

    entries = hist.collect()
    assert len(entries) == 1
    assert entries[0]["count"] == 2


# ---------------------------------------------------------------------------
# HealthChecker
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health_checker_check_health_returns_dict_with_status():
    # No db_url or redis_url, so no checks run -- still returns structure
    checker = HealthChecker(version="1.0.0", db_url=None, redis_url=None)
    result = await checker.check_health()

    assert "status" in result
    assert "checks" in result
    assert "version" in result
    assert result["version"] == "1.0.0"
    assert isinstance(result["checks"], list)


# ---------------------------------------------------------------------------
# setup_logging
# ---------------------------------------------------------------------------

def test_setup_logging_returns_logger():
    logger = setup_logging(logger_name="test.monitoring")
    assert isinstance(logger, logging.Logger)


def test_setup_logging_idempotent():
    """Calling setup_logging twice should not add duplicate handlers."""
    setup_logging(logger_name="test.idempotent")
    logger = setup_logging(logger_name="test.idempotent")
    json_handlers = [
        h for h in logger.handlers
        if isinstance(h.formatter, StructuredJsonFormatter)
    ]
    assert len(json_handlers) == 1


# ---------------------------------------------------------------------------
# StructuredJsonFormatter
# ---------------------------------------------------------------------------

def test_structured_json_formatter_produces_valid_json():
    formatter = StructuredJsonFormatter()
    record = logging.LogRecord(
        name="test.logger",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="Test message",
        args=(),
        exc_info=None,
    )
    output = formatter.format(record)
    parsed = json.loads(output)
    assert parsed["level"] == "INFO"
    assert parsed["message"] == "Test message"
    assert "timestamp" in parsed
