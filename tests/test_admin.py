"""
Tests for admin endpoints:
  GET /api/v1/admin/dashboard
  GET /api/v1/admin/vendors
  PUT /api/v1/admin/vendors/{id}/approve
  GET /api/v1/admin/products
  GET /api/v1/admin/orders
  GET /api/v1/admin/analytics
  GET /api/v1/admin/users
"""
import pytest
from httpx import AsyncClient

from tests.conftest import auth_headers


pytestmark = pytest.mark.asyncio


class TestAdminAccess:
    async def test_admin_routes_blocked_for_customer(self, client: AsyncClient, customer_user):
        for path in ["/api/v1/admin/dashboard", "/api/v1/admin/vendors", "/api/v1/admin/orders"]:
            response = await client.get(path, headers=auth_headers(customer_user))
            assert response.status_code == 403, f"Expected 403 for {path}"

    async def test_admin_routes_blocked_for_vendor(self, client: AsyncClient, vendor_user):
        response = await client.get("/api/v1/admin/dashboard", headers=auth_headers(vendor_user))
        assert response.status_code == 403

    async def test_admin_routes_blocked_unauthenticated(self, client: AsyncClient):
        response = await client.get("/api/v1/admin/dashboard")
        assert response.status_code == 401


class TestAdminDashboard:
    async def test_dashboard_stats(self, client: AsyncClient, admin_user):
        response = await client.get(
            "/api/v1/admin/dashboard",
            headers=auth_headers(admin_user),
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_users" in data
        assert "total_vendors" in data
        assert "total_orders" in data
        assert "total_revenue" in data
        assert "pending_vendors" in data
        assert "total_products" in data
        # All values should be non-negative numbers
        for key in ["total_users", "total_vendors", "total_orders", "total_products", "pending_vendors"]:
            assert data[key] >= 0


class TestAdminVendors:
    async def test_list_all_vendors(self, client: AsyncClient, admin_user, vendor):
        response = await client.get(
            "/api/v1/admin/vendors",
            headers=auth_headers(admin_user),
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    async def test_list_vendors_filter_by_kyc(self, client: AsyncClient, admin_user):
        for status in ["pending", "approved", "rejected"]:
            response = await client.get(
                f"/api/v1/admin/vendors?kyc_status={status}",
                headers=auth_headers(admin_user),
            )
            assert response.status_code == 200

    async def test_approve_vendor(self, client: AsyncClient, admin_user, vendor):
        response = await client.put(
            f"/api/v1/admin/vendors/{vendor.id}/approve",
            headers=auth_headers(admin_user),
        )
        assert response.status_code == 200
        assert "approved" in response.json()["message"].lower()

    async def test_reject_vendor(self, client: AsyncClient, admin_user, vendor):
        response = await client.put(
            f"/api/v1/admin/vendors/{vendor.id}/reject",
            json={"reason": "Incomplete documentation"},
            headers=auth_headers(admin_user),
        )
        assert response.status_code == 200

    async def test_approve_nonexistent_vendor(self, client: AsyncClient, admin_user):
        import uuid
        response = await client.put(
            f"/api/v1/admin/vendors/{uuid.uuid4()}/approve",
            headers=auth_headers(admin_user),
        )
        assert response.status_code == 404


class TestAdminProducts:
    async def test_list_all_products(self, client: AsyncClient, admin_user, product):
        response = await client.get(
            "/api/v1/admin/products",
            headers=auth_headers(admin_user),
        )
        assert response.status_code == 200
        assert "items" in response.json()

    async def test_moderate_product_archive(self, client: AsyncClient, admin_user, product):
        response = await client.put(
            f"/api/v1/admin/products/{product.id}/moderate",
            json={"action": "archive"},
            headers=auth_headers(admin_user),
        )
        assert response.status_code == 200

    async def test_moderate_product_approve(self, client: AsyncClient, admin_user, product):
        response = await client.put(
            f"/api/v1/admin/products/{product.id}/moderate",
            json={"action": "approve"},
            headers=auth_headers(admin_user),
        )
        assert response.status_code == 200


class TestAdminAnalytics:
    async def test_get_analytics(self, client: AsyncClient, admin_user):
        response = await client.get(
            "/api/v1/admin/analytics",
            headers=auth_headers(admin_user),
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_revenue" in data
        assert "total_orders" in data
        assert "period_days" in data

    async def test_analytics_different_ranges(self, client: AsyncClient, admin_user):
        for r in ["7d", "30d", "90d"]:
            response = await client.get(
                f"/api/v1/admin/analytics?range={r}",
                headers=auth_headers(admin_user),
            )
            assert response.status_code == 200


class TestAdminUsers:
    async def test_list_users(self, client: AsyncClient, admin_user, customer_user):
        response = await client.get(
            "/api/v1/admin/users",
            headers=auth_headers(admin_user),
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 1
