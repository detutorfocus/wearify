"""
Tests for cart endpoints:
  GET    /api/v1/cart
  POST   /api/v1/cart/items
  PUT    /api/v1/cart/items/{id}
  DELETE /api/v1/cart/items/{id}
  DELETE /api/v1/cart
"""
import pytest
from httpx import AsyncClient

from tests.conftest import auth_headers


pytestmark = pytest.mark.asyncio


class TestGetCart:
    async def test_get_empty_cart(self, client: AsyncClient, customer_user):
        response = await client.get("/api/v1/cart", headers=auth_headers(customer_user))
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_get_cart_unauthenticated(self, client: AsyncClient):
        response = await client.get("/api/v1/cart")
        assert response.status_code == 401


class TestAddToCart:
    async def test_add_product_to_cart(self, client: AsyncClient, customer_user, product):
        response = await client.post(
            "/api/v1/cart/items",
            json={"product_id": str(product.id), "quantity": 2},
            headers=auth_headers(customer_user),
        )
        assert response.status_code == 201
        data = response.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["quantity"] == 2
        assert data["total"] > 0

    async def test_add_same_product_increases_quantity(self, client: AsyncClient, customer_user, product):
        await client.post(
            "/api/v1/cart/items",
            json={"product_id": str(product.id), "quantity": 1},
            headers=auth_headers(customer_user),
        )
        await client.post(
            "/api/v1/cart/items",
            json={"product_id": str(product.id), "quantity": 1},
            headers=auth_headers(customer_user),
        )
        response = await client.get("/api/v1/cart", headers=auth_headers(customer_user))
        # Should have one item with qty=2, not two separate items
        cart_items = response.json()["items"]
        product_items = [i for i in cart_items if i["product_id"] == str(product.id)]
        assert len(product_items) == 1
        assert product_items[0]["quantity"] == 2

    async def test_add_inactive_product(self, client: AsyncClient, db_session, customer_user, product):
        from app.models.product import ProductStatus
        product.status = ProductStatus.archived
        await db_session.flush()
        response = await client.post(
            "/api/v1/cart/items",
            json={"product_id": str(product.id), "quantity": 1},
            headers=auth_headers(customer_user),
        )
        assert response.status_code == 404

    async def test_add_to_cart_unauthenticated(self, client: AsyncClient, product):
        response = await client.post(
            "/api/v1/cart/items",
            json={"product_id": str(product.id), "quantity": 1},
        )
        assert response.status_code == 401


class TestUpdateCartItem:
    async def test_update_quantity(self, client: AsyncClient, customer_user, product):
        add_resp = await client.post(
            "/api/v1/cart/items",
            json={"product_id": str(product.id), "quantity": 1},
            headers=auth_headers(customer_user),
        )
        item_id = add_resp.json()["items"][0]["id"]

        response = await client.put(
            f"/api/v1/cart/items/{item_id}",
            json={"quantity": 5},
            headers=auth_headers(customer_user),
        )
        assert response.status_code == 200


class TestRemoveFromCart:
    async def test_remove_item(self, client: AsyncClient, customer_user, product):
        add_resp = await client.post(
            "/api/v1/cart/items",
            json={"product_id": str(product.id), "quantity": 1},
            headers=auth_headers(customer_user),
        )
        item_id = add_resp.json()["items"][0]["id"]

        response = await client.delete(
            f"/api/v1/cart/items/{item_id}",
            headers=auth_headers(customer_user),
        )
        assert response.status_code == 204

        cart = await client.get("/api/v1/cart", headers=auth_headers(customer_user))
        assert all(i["id"] != item_id for i in cart.json()["items"])


class TestClearCart:
    async def test_clear_cart(self, client: AsyncClient, customer_user, product):
        await client.post(
            "/api/v1/cart/items",
            json={"product_id": str(product.id), "quantity": 1},
            headers=auth_headers(customer_user),
        )
        response = await client.delete("/api/v1/cart", headers=auth_headers(customer_user))
        assert response.status_code == 204

        cart = await client.get("/api/v1/cart", headers=auth_headers(customer_user))
        assert cart.json()["items"] == []
