"""
Tests for vendor endpoints:
  POST /api/v1/vendors/register
  GET  /api/v1/vendors/{slug}
  GET  /api/v1/vendors/me/dashboard
  GET  /api/v1/vendors/me/wallet
  PUT  /api/v1/vendors/me/profile
"""
import pytest
from httpx import AsyncClient

from tests.conftest import auth_headers


pytestmark = pytest.mark.asyncio


class TestVendorRegister:
    async def test_register_as_authenticated_customer(self, client: AsyncClient, customer_user):
        response = await client.post(
            "/api/v1/vendors/register",
            json={"store_name": "My New Store", "description": "Fresh African fashion"},
            headers=auth_headers(customer_user),
        )
        assert response.status_code == 201

    async def test_register_duplicate_store_name(self, client: AsyncClient, customer_user, vendor):
        response = await client.post(
            "/api/v1/vendors/register",
            json={"store_name": vendor.store_name},
            headers=auth_headers(customer_user),
        )
        assert response.status_code == 400
        assert "taken" in response.json()["detail"].lower()

    async def test_register_unauthenticated(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/vendors/register",
            json={"store_name": "Ghost Store"},
        )
        assert response.status_code == 401


class TestVendorStorefront:
    async def test_get_public_storefront(self, client: AsyncClient, vendor):
        response = await client.get(f"/api/v1/vendors/{vendor.store_slug}")
        assert response.status_code == 200
        data = response.json()
        assert data["store_slug"] == vendor.store_slug
        assert data["store_name"] == vendor.store_name

    async def test_get_nonexistent_storefront(self, client: AsyncClient):
        response = await client.get("/api/v1/vendors/this-store-does-not-exist")
        assert response.status_code == 404


class TestVendorDashboard:
    async def test_dashboard_requires_vendor_role(self, client: AsyncClient, customer_user):
        response = await client.get(
            "/api/v1/vendors/me/dashboard",
            headers=auth_headers(customer_user),
        )
        assert response.status_code == 403

    async def test_dashboard_for_vendor(self, client: AsyncClient, vendor_user, vendor):
        response = await client.get(
            "/api/v1/vendors/me/dashboard",
            headers=auth_headers(vendor_user),
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_revenue" in data
        assert "total_orders" in data
        assert "total_products" in data
        assert "wallet_balance" in data

    async def test_dashboard_unauthenticated(self, client: AsyncClient):
        response = await client.get("/api/v1/vendors/me/dashboard")
        assert response.status_code == 401


class TestVendorWallet:
    async def test_get_wallet_as_vendor(self, client: AsyncClient, vendor_user, vendor):
        response = await client.get(
            "/api/v1/vendors/me/wallet",
            headers=auth_headers(vendor_user),
        )
        assert response.status_code == 200
        data = response.json()
        assert "balance" in data
        assert "pending_balance" in data
        assert "total_earned" in data
        assert "transactions" in data
        assert isinstance(data["transactions"], list)

    async def test_wallet_requires_vendor_role(self, client: AsyncClient, customer_user):
        response = await client.get(
            "/api/v1/vendors/me/wallet",
            headers=auth_headers(customer_user),
        )
        assert response.status_code == 403


class TestVendorProfileUpdate:
    async def test_update_profile(self, client: AsyncClient, vendor_user, vendor):
        response = await client.put(
            "/api/v1/vendors/me/profile",
            json={"description": "Updated description for my store"},
            headers=auth_headers(vendor_user),
        )
        assert response.status_code == 200

    async def test_update_profile_as_customer(self, client: AsyncClient, customer_user):
        response = await client.put(
            "/api/v1/vendors/me/profile",
            json={"description": "I am not a vendor"},
            headers=auth_headers(customer_user),
        )
        assert response.status_code == 403
