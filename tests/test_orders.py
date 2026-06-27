"""
Tests for order endpoints:
  POST /api/v1/orders
  GET  /api/v1/orders
  GET  /api/v1/orders/{id}
  POST /api/v1/orders/{id}/cancel
"""
import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cart import CartItem
from tests.conftest import auth_headers


pytestmark = pytest.mark.asyncio


async def _add_item_to_cart(db: AsyncSession, user, product, quantity=1):
    """Helper to add a product directly to cart in DB."""
    item = CartItem(
        id=uuid.uuid4(),
        customer_id=user.id,
        product_id=product.id,
        quantity=quantity,
        unit_price_snapshot=product.base_price,
    )
    db.add(item)
    await db.flush()
    return item


SHIPPING_ADDRESS = {
    "full_name": "Jane Test",
    "phone": "+2348012345678",
    "address_line1": "12 Test Street",
    "city": "Lagos",
    "state": "Lagos State",
    "country": "Nigeria",
}


class TestCreateOrder:
    async def test_create_order_with_cart(self, client: AsyncClient, db_session, customer_user, product, vendor):
        await _add_item_to_cart(db_session, customer_user, product)
        response = await client.post(
            "/api/v1/orders",
            json={"shipping_address": SHIPPING_ADDRESS, "payment_method": "paystack"},
            headers=auth_headers(customer_user),
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "pending"
        assert data["payment_status"] == "pending"
        assert len(data["items"]) == 1
        assert float(data["total"]) > 0

    async def test_create_order_empty_cart(self, client: AsyncClient, customer_user):
        response = await client.post(
            "/api/v1/orders",
            json={"shipping_address": SHIPPING_ADDRESS, "payment_method": "paystack"},
            headers=auth_headers(customer_user),
        )
        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()

    async def test_create_order_unauthenticated(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/orders",
            json={"shipping_address": SHIPPING_ADDRESS, "payment_method": "paystack"},
        )
        assert response.status_code == 401

    async def test_create_order_reduces_stock(self, client: AsyncClient, db_session, customer_user, product):
        initial_stock = product.stock_quantity
        await _add_item_to_cart(db_session, customer_user, product, quantity=2)
        response = await client.post(
            "/api/v1/orders",
            json={"shipping_address": SHIPPING_ADDRESS, "payment_method": "paystack"},
            headers=auth_headers(customer_user),
        )
        assert response.status_code == 201
        # Stock should have been reduced
        await db_session.refresh(product)
        assert product.stock_quantity == initial_stock - 2


class TestListOrders:
    async def test_list_my_orders(self, client: AsyncClient, customer_user):
        response = await client.get(
            "/api/v1/orders",
            headers=auth_headers(customer_user),
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    async def test_list_orders_unauthenticated(self, client: AsyncClient):
        response = await client.get("/api/v1/orders")
        assert response.status_code == 401

    async def test_list_orders_pagination(self, client: AsyncClient, customer_user):
        response = await client.get(
            "/api/v1/orders?page=1&page_size=5",
            headers=auth_headers(customer_user),
        )
        assert response.status_code == 200
        assert len(response.json()["items"]) <= 5


class TestGetOrder:
    async def test_get_own_order(self, client: AsyncClient, db_session, customer_user, product):
        await _add_item_to_cart(db_session, customer_user, product)
        create_resp = await client.post(
            "/api/v1/orders",
            json={"shipping_address": SHIPPING_ADDRESS, "payment_method": "paystack"},
            headers=auth_headers(customer_user),
        )
        order_id = create_resp.json()["id"]

        response = await client.get(
            f"/api/v1/orders/{order_id}",
            headers=auth_headers(customer_user),
        )
        assert response.status_code == 200
        assert response.json()["id"] == order_id

    async def test_get_other_users_order_forbidden(self, client: AsyncClient, db_session, customer_user, product, admin_user):
        await _add_item_to_cart(db_session, customer_user, product)
        create_resp = await client.post(
            "/api/v1/orders",
            json={"shipping_address": SHIPPING_ADDRESS, "payment_method": "paystack"},
            headers=auth_headers(customer_user),
        )
        order_id = create_resp.json()["id"]

        # Another customer cannot see this order
        import uuid as _uuid
        from app.models.user import User, UserRole
        from app.core.security import get_password_hash
        other = User(
            id=_uuid.uuid4(), email="other@customer.com",
            hashed_password=get_password_hash("Pass123!"),
            full_name="Other", role=UserRole.customer,
            is_active=True, is_verified=True,
        )
        response = await client.get(
            f"/api/v1/orders/{order_id}",
            headers=auth_headers(other),
        )
        assert response.status_code in (401, 403)

    async def test_get_nonexistent_order(self, client: AsyncClient, customer_user):
        response = await client.get(
            f"/api/v1/orders/{uuid.uuid4()}",
            headers=auth_headers(customer_user),
        )
        assert response.status_code == 404


class TestCancelOrder:
    async def test_cancel_pending_order(self, client: AsyncClient, db_session, customer_user, product):
        await _add_item_to_cart(db_session, customer_user, product)
        create_resp = await client.post(
            "/api/v1/orders",
            json={"shipping_address": SHIPPING_ADDRESS, "payment_method": "paystack"},
            headers=auth_headers(customer_user),
        )
        order_id = create_resp.json()["id"]

        response = await client.post(
            f"/api/v1/orders/{order_id}/cancel",
            headers=auth_headers(customer_user),
        )
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"

    async def test_cancel_restores_stock(self, client: AsyncClient, db_session, customer_user, product):
        initial_stock = product.stock_quantity
        qty = 3
        await _add_item_to_cart(db_session, customer_user, product, quantity=qty)
        create_resp = await client.post(
            "/api/v1/orders",
            json={"shipping_address": SHIPPING_ADDRESS, "payment_method": "paystack"},
            headers=auth_headers(customer_user),
        )
        order_id = create_resp.json()["id"]
        await client.post(f"/api/v1/orders/{order_id}/cancel", headers=auth_headers(customer_user))

        await db_session.refresh(product)
        assert product.stock_quantity == initial_stock
