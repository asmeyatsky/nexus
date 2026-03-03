"""Tests for webhook service — SSRF protection, HMAC signatures, URL validation."""

import pytest
from infrastructure.adapters.webhooks import (
    WebhookService,
    WebhookEvent,
    is_url_safe,
)


class TestSSRFProtection:
    def test_blocks_localhost_ip(self):
        safe, reason = is_url_safe("http://127.0.0.1/callback")
        assert safe is False

    def test_blocks_private_10x(self):
        safe, reason = is_url_safe("http://10.0.0.1/hook")
        assert safe is False

    def test_blocks_private_192_168(self):
        safe, reason = is_url_safe("http://192.168.1.1/hook")
        assert safe is False

    def test_blocks_localhost_hostname(self):
        safe, reason = is_url_safe("http://localhost/hook")
        assert safe is False

    def test_blocks_internal_domain(self):
        safe, reason = is_url_safe("http://service.internal/hook")
        assert safe is False

    def test_blocks_non_http_scheme(self):
        safe, reason = is_url_safe("ftp://example.com/hook")
        assert safe is False

    def test_allows_external_ip(self):
        # Use a known public IP (Google DNS) that is not in any blocked range
        safe, reason = is_url_safe("https://8.8.8.8/callback")
        assert safe is True


class TestWebhookService:
    def setup_method(self):
        self.svc = WebhookService()

    def test_create_webhook_with_valid_url(self):
        wh = self.svc.create_webhook(
            url="https://8.8.8.8/cb",
            events=[WebhookEvent.ACCOUNT_CREATED],
            org_id="org1",
        )
        assert wh is not None
        assert wh.is_active is True

    def test_create_webhook_with_ssrf_url_raises(self):
        with pytest.raises(ValueError, match="URL validation failed"):
            self.svc.create_webhook(
                url="http://127.0.0.1/evil",
                events=[WebhookEvent.ACCOUNT_CREATED],
                org_id="org1",
            )

    def test_hmac_signature_generation(self):
        sig = self.svc._generate_signature({"event": "test"}, "my-secret", "12345")
        assert isinstance(sig, str)
        assert len(sig) == 64  # SHA-256 hex digest

    def test_hmac_signature_deterministic(self):
        payload = {"key": "value"}
        sig1 = self.svc._generate_signature(payload, "secret", "100")
        sig2 = self.svc._generate_signature(payload, "secret", "100")
        assert sig1 == sig2

    def test_hmac_signature_differs_with_different_secret(self):
        payload = {"key": "value"}
        sig1 = self.svc._generate_signature(payload, "secret1", "100")
        sig2 = self.svc._generate_signature(payload, "secret2", "100")
        assert sig1 != sig2

    def test_get_webhooks_for_event(self):
        self.svc.create_webhook(
            url="https://8.8.4.4/cb",
            events=[WebhookEvent.ACCOUNT_CREATED],
            org_id="org1",
        )
        self.svc.create_webhook(
            url="https://1.1.1.1/cb",
            events=[WebhookEvent.CONTACT_CREATED],
            org_id="org1",
        )
        hooks = self.svc.get_webhooks_for_event(WebhookEvent.ACCOUNT_CREATED, "org1")
        assert len(hooks) == 1

    def test_delete_webhook(self):
        wh = self.svc.create_webhook(
            url="https://1.0.0.1/cb",
            events=[WebhookEvent.LEAD_CREATED],
            org_id="org1",
        )
        self.svc.delete_webhook(wh.id)
        hooks = self.svc.get_webhooks_for_event(WebhookEvent.LEAD_CREATED, "org1")
        assert len(hooks) == 0
