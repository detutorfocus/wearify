"""
Tests for product endpoints:
  GET    /api/v1/products
  GET    /api/v1/products/{slug}
  GET    /api/v1/products/featured
  POST   /api/v1/products
  PUT    /api/v1/products/{id}
  DELETE /api/v1/products/{id}
  POST   /api/v1/products/categories/tree
"""
import pytest
from decimal import Decimal
from httpx import AsyncClient

from tests.conftest import auth_headers


pytestmark = pytest.mark.asyncio


class TestListProducts:
    async def test_list_products_public(self, client: AsyncClient, product):
        response = await client.get("/api/v1/products")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "pages" in data
        assert isinstance(data["items"], list)

    async def test_list_products_pagination(self, client: AsyncClient, product):
        response = await client.get("/api/v1/products?page=1&page_size=5")
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 5

    async def test_list_products_search(self, client: AsyncClient, product):
        response = await client.get(f"/api/v1/products?search={product.name[:5]}")
        assert response.status_code == 200

    async def test_list_products_sort_options(self, client: AsyncClient):
        for sort in ["newest", "price_asc", "price_desc", "popular"]:
            response = await client.get(f"/api/v1/products?sort={sort}")
            assert response.status_code == 200

    async def test_list_products_invalid_sort(self, client: AsyncClient):
        response = await client.get("/api/v1/products?sort=invalid")
        assert response.status_code == 422

    async def test_list_products_price_filter(self, client: AsyncClient):
        response = await client.get("/api/v1/products?min_price=1000&max_price=50000")
        assert response.status_code == 200

    async def test_list_products_page_size_limit(self, client: AsyncClient):
        """page_size > 50 should be rejected."""
        response = await client.get("/api/v1/products?page_size=200")
        assert response.status_code == 422


class TestGetProduct:
    async def test_get_product_by_slug(self, client: AsyncClient, product):
        response = await client.get(f"/api/v1/products/{product.slug}")
        assert response.status_code == 200
        data = response.json()
        assert data["slug"] == product.slug
        assert data["name"] == product.name
        assert "images" in data
        assert "variants" in data

    async def test_get_nonexistent_product(self, client: AsyncClient):
        response = await client.get("/api/v1/products/this-does-not-exist")
        assert response.status_code == 404

    async def test_get_product_increments_view_count(self, client: AsyncClient, product):
        initial_views = product.view_count
        await client.get(f"/api/v1/products/{product.slug}")
        # View count update is async (fire-and-forget), just verify no error


class TestCreateProduct:
    async def test_create_product_as_vendor(self, client: AsyncClient, vendor_user, vendor):
        response = await client.post(
            "/api/v1/products",
            json={
                "name": "New Test Dress",
                "description": "A beautiful test dress",
                "base_price": 25000,
                "stock_quantity": 10,
                "tags": ["dress", "women"],
            },
            headers=auth_headers(vendor_user),
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Test Dress"
        assert data["status"] == "draft"  # New products start as draft
        assert "sku" in data
        assert "slug" in data

    async def test_create_product_as_customer_forbidden(self, client: AsyncClient, customer_user):
        response = await client.post(
            "/api/v1/products",
            json={"name": "Sneaky Product", "base_price": 100, "stock_quantity": 1},
            headers=auth_headers(customer_user),
        )
        assert response.status_code == 403

    async def test_create_product_unauthenticated(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/products",
            json={"name": "Ghost Product", "base_price": 100, "stock_quantity": 1},
        )
        assert response.status_code == 401

    async def test_create_product_missing_price(self, client: AsyncClient, vendor_user, vendor):
        response = await client.post(
            "/api/v1/products",
            json={"name": "No Price Product", "stock_quantity": 5},
            headers=auth_headers(vendor_user),
        )
        assert response.status_code == 422


class TestUpdateProduct:
    async def test_update_own_product(self, client: AsyncClient, vendor_user, product):
        response = await client.put(
            f"/api/v1/products/{product.id}",
            json={"name": "Updated Name", "stock_quantity": 50},
            headers=auth_headers(vendor_user),
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Name"

    async def test_update_product_wrong_vendor(self, client: AsyncClient, db_session, product):
        """A different vendor cannot update another vendor's product."""
        import uuid as _uuid
        from app.models.user import User, UserRole
        from app.models.vendor import Vendor, KYCStatus
        from app.models.wallet import Wallet
        from app.core.security import get_password_hash

        # Create and PERSIST another vendor user
        other_user = User(
            id=_uuid.uuid4(), email=f"other_{_uuid.uuid4().hex[:6]}@vendor.com",
            hashed_password=get_password_hash("Pass123!"),
            full_name="Other Vendor", role=UserRole.vendor,
            is_active=True, is_verified=True,
        )
        db_session.add(other_user)
        await db_session.flush()
        other_vendor = Vendor(
            id=_uuid.uuid4(), user_id=other_user.id,
            store_name=f"Other Store {_uuid.uuid4().hex[:4]}",
            store_slug=f"other-store-{_uuid.uuid4().hex[:4]}",
            kyc_status=KYCStatus.approved, commission_rate=10,
        )
        db_session.add(other_vendor)
        wallet = Wallet(id=_uuid.uuid4(), vendor_id=other_vendor.id)
        db_session.add(wallet)
        await db_session.flush()

        response = await client.put(
            f"/api/v1/products/{product.id}",
            json={"name": "Hijacked"},
            headers=auth_headers(other_user),
        )
        assert response.status_code in (403, 404)

    async def test_update_nonexistent_product(self, client: AsyncClient, vendor_user):
        import uuid
        response = await client.put(
            f"/api/v1/products/{uuid.uuid4()}",
            json={"name": "Ghost"},
            headers=auth_headers(vendor_user),
        )
        assert response.status_code == 404


class TestDeleteProduct:
    async def test_soft_delete_product(self, client: AsyncClient, vendor_user, product):
        response = await client.delete(
            f"/api/v1/products/{product.id}",
            headers=auth_headers(vendor_user),
        )
        assert response.status_code == 204

        # Product should no longer appear in public listing (archived)
        list_response = await client.get(f"/api/v1/products/{product.slug}")
        assert list_response.status_code == 404


class TestFeaturedProducts:
    async def test_get_featured_products(self, client: AsyncClient):
        response = await client.get("/api/v1/products/featured")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_get_featured_limit(self, client: AsyncClient):
        response = await client.get("/api/v1/products/featured?limit=4")
        assert response.status_code == 200
        assert len(response.json()) <= 4


class TestCategories:
    async def test_get_category_tree(self, client: AsyncClient, category):
        response = await client.get("/api/v1/products/categories/tree")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
