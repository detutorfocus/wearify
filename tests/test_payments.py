"""
Tests for payment endpoints:
  POST /api/v1/payments/initialize
  POST /api/v1/payments/verify/{ref}
  POST /api/v1/payments/webhooks/paystack
"""
import hashlib
import hmac
import json
import pytest
import uuid
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch

from app.core.config import settings
from tests.conftest import auth_headers


pytestmark = pytest.mark.asyncio


class TestInitializePayment:
    async def test_initialize_paystack(self, client: AsyncClient, db_session, customer_user, product, vendor):
        # Create an order first
        from app.models.cart import CartItem
        from decimal import Decimal
        cart_item = CartItem(
            id=uuid.uuid4(),
            customer_id=customer_user.id,
            product_id=product.id,
            quantity=1,
            unit_price_snapshot=Decimal("18500"),
        )
        db_session.add(cart_item)
        await db_session.flush()

        order_resp = await client.post(
            "/api/v1/orders",
            json={
                "shipping_address": {
                    "full_name": "Test", "phone": "+234801",
                    "address_line1": "1 Test St", "city": "Lagos", "state": "Lagos"
                },
                "payment_method": "paystack",
            },
            headers=auth_headers(customer_user),
        )
        assert order_resp.status_code == 201
        order_id = order_resp.json()["id"]

        # Mock Paystack API call
        mock_response = {
            "status": True,
            "data": {"authorization_url": "https://checkout.paystack.com/test", "reference": "WEA-ABC123"}
        }
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value.json.return_value = mock_response
            response = await client.post(
                "/api/v1/payments/initialize",
                json={"order_id": order_id, "provider": "paystack", "currency": "NGN"},
                headers=auth_headers(customer_user),
            )

        assert response.status_code == 200
        data = response.json()
        assert "payment_url" in data
        assert "reference" in data

    async def test_initialize_invalid_provider(self, client: AsyncClient, customer_user):
        response = await client.post(
            "/api/v1/payments/initialize",
            json={"order_id": str(uuid.uuid4()), "provider": "bitcoin"},
            headers=auth_headers(customer_user),
        )
        assert response.status_code in (400, 404)

    async def test_initialize_unauthenticated(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/payments/initialize",
            json={"order_id": str(uuid.uuid4()), "provider": "paystack"},
        )
        assert response.status_code == 401


class TestPaystackWebhook:
    def _make_signature(self, payload: bytes) -> str:
        return hmac.new(
            settings.PAYSTACK_SECRET.encode(),
            payload,
            hashlib.sha512,
        ).hexdigest()

    async def test_valid_webhook_charge_success(self, client: AsyncClient, db_session):
        """Valid webhook with correct HMAC signature should be accepted."""
        payload = json.dumps({
            "event": "charge.success",
            "data": {
                "reference": "WEA-TESTREF123",
                "status": "success",
                "amount": 1850000,
            }
        }).encode()

        signature = self._make_signature(payload)

        with patch("app.services.payment_service.PaymentService.handle_successful_payment", new_callable=AsyncMock):
            response = await client.post(
                "/api/v1/payments/webhooks/paystack",
                content=payload,
                headers={
                    "Content-Type": "application/json",
                    "x-paystack-signature": signature,
                },
            )
        assert response.status_code == 200

    async def test_invalid_webhook_signature(self, client: AsyncClient):
        """Webhook with wrong signature should be rejected."""
        payload = json.dumps({"event": "charge.success", "data": {"reference": "REF"}}).encode()
        response = await client.post(
            "/api/v1/payments/webhooks/paystack",
            content=payload,
            headers={
                "Content-Type": "application/json",
                "x-paystack-signature": "invalidsignature",
            },
        )
        assert response.status_code == 401

    async def test_webhook_without_signature(self, client: AsyncClient):
        payload = json.dumps({"event": "charge.success"}).encode()
        response = await client.post(
            "/api/v1/payments/webhooks/paystack",
            content=payload,
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 401
