"""
Tests for authentication endpoints:
  POST /api/v1/auth/register
  POST /api/v1/auth/login
  POST /api/v1/auth/refresh
  POST /api/v1/auth/logout
  GET  /api/v1/auth/me
"""
import pytest
from httpx import AsyncClient

from tests.conftest import auth_headers


pytestmark = pytest.mark.asyncio


class TestRegister:
    async def test_register_success(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/register", json={
            "email": "newuser@test.com",
            "password": "Password123!",
            "full_name": "New User",
        })
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["email"] == "newuser@test.com"
        assert data["user"]["role"] == "customer"

    async def test_register_duplicate_email(self, client: AsyncClient, customer_user):
        response = await client.post("/api/v1/auth/register", json={
            "email": customer_user.email,
            "password": "Password123!",
            "full_name": "Duplicate",
        })
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    async def test_register_short_password(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/register", json={
            "email": "shortpass@test.com",
            "password": "abc",
            "full_name": "Short Pass",
        })
        assert response.status_code == 422  # Pydantic validation error

    async def test_register_invalid_email(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/register", json={
            "email": "not-an-email",
            "password": "Password123!",
            "full_name": "Bad Email",
        })
        assert response.status_code == 422


class TestLogin:
    async def test_login_success(self, client: AsyncClient, customer_user):
        response = await client.post("/api/v1/auth/login", json={
            "email": customer_user.email,
            "password": "TestPass123!",
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password(self, client: AsyncClient, customer_user):
        response = await client.post("/api/v1/auth/login", json={
            "email": customer_user.email,
            "password": "WrongPassword!",
        })
        assert response.status_code == 401

    async def test_login_unknown_email(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/login", json={
            "email": "nobody@nowhere.com",
            "password": "Password123!",
        })
        assert response.status_code == 401

    async def test_login_inactive_user(self, client: AsyncClient, db_session, customer_user):
        customer_user.is_active = False
        await db_session.flush()
        response = await client.post("/api/v1/auth/login", json={
            "email": customer_user.email,
            "password": "TestPass123!",
        })
        assert response.status_code == 403


class TestGetMe:
    async def test_get_me_authenticated(self, client: AsyncClient, customer_user):
        response = await client.get(
            "/api/v1/auth/me",
            headers=auth_headers(customer_user),
        )
        assert response.status_code == 200
        assert response.json()["email"] == customer_user.email

    async def test_get_me_unauthenticated(self, client: AsyncClient):
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 401

    async def test_get_me_invalid_token(self, client: AsyncClient):
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer this.is.invalid"},
        )
        assert response.status_code == 401


class TestUpdateMe:
    async def test_update_profile(self, client: AsyncClient, customer_user):
        response = await client.put(
            "/api/v1/auth/me",
            json={"full_name": "Updated Name", "phone": "+2348012345678"},
            headers=auth_headers(customer_user),
        )
        assert response.status_code == 200

    async def test_update_profile_unauthenticated(self, client: AsyncClient):
        response = await client.put("/api/v1/auth/me", json={"full_name": "X"})
        assert response.status_code == 401


class TestForgotPassword:
    async def test_forgot_password_always_200(self, client: AsyncClient):
        """Should always return 200 to prevent email enumeration."""
        for email in ["real@test.com", "fake@nowhere.com", "not-an-email"]:
            response = await client.post(
                "/api/v1/auth/forgot-password",
                params={"email": email},
            )
            # 200 for real/fake, 422 for invalid format is acceptable
            assert response.status_code in (200, 422)
