"""
Pytest configuration and shared fixtures for Wearify tests.
"""
import asyncio
import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db

# ── Mock Redis for tests (no real Redis needed) ────────────────────────────────
import fakeredis.aioredis
import app.core.redis as _redis_module
import app.core.security as _security_module

_fake_redis = fakeredis.aioredis.FakeRedis()
_redis_module.redis_client = _fake_redis
_security_module.redis_client = _fake_redis


from app.core.security import get_password_hash, create_access_token
from app.models.user import User, UserRole
from app.models.vendor import Vendor, KYCStatus
from app.models.category import Category
from app.models.product import Product, ProductStatus
from app.models.wallet import Wallet

# ── In-memory SQLite for tests ─────────────────────────────────────────────────
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_test_tables():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session():
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    """HTTP client with overridden DB dependency."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


# ── User fixtures ──────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def customer_user(db_session: AsyncSession) -> User:
    user = User(
        id=uuid.uuid4(),
        email=f"customer_{uuid.uuid4().hex[:6]}@test.com",
        hashed_password=get_password_hash("TestPass123!"),
        full_name="Test Customer",
        role=UserRole.customer,
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def vendor_user(db_session: AsyncSession) -> User:
    user = User(
        id=uuid.uuid4(),
        email=f"vendor_{uuid.uuid4().hex[:6]}@test.com",
        hashed_password=get_password_hash("TestPass123!"),
        full_name="Test Vendor",
        role=UserRole.vendor,
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    user = User(
        id=uuid.uuid4(),
        email=f"admin_{uuid.uuid4().hex[:6]}@test.com",
        hashed_password=get_password_hash("AdminPass123!"),
        full_name="Test Admin",
        role=UserRole.admin,
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def vendor(db_session: AsyncSession, vendor_user: User) -> Vendor:
    v = Vendor(
        id=uuid.uuid4(),
        user_id=vendor_user.id,
        store_name=f"Test Store {uuid.uuid4().hex[:4]}",
        store_slug=f"test-store-{uuid.uuid4().hex[:4]}",
        kyc_status=KYCStatus.approved,
        commission_rate=10,
    )
    db_session.add(v)
    await db_session.flush()
    wallet = Wallet(id=uuid.uuid4(), vendor_id=v.id)
    db_session.add(wallet)
    await db_session.flush()
    return v


@pytest_asyncio.fixture
async def category(db_session: AsyncSession) -> Category:
    cat = Category(
        id=uuid.uuid4(),
        name="Women",
        slug=f"women-{uuid.uuid4().hex[:4]}",
        is_active=True,
    )
    db_session.add(cat)
    await db_session.flush()
    return cat


@pytest_asyncio.fixture
async def product(db_session: AsyncSession, vendor: Vendor, category: Category) -> Product:
    p = Product(
        id=uuid.uuid4(),
        vendor_id=vendor.id,
        category_id=category.id,
        name="Test Ankara Dress",
        slug=f"test-ankara-dress-{uuid.uuid4().hex[:4]}",
        base_price=18500,
        sku=f"TST-{uuid.uuid4().hex[:6].upper()}",
        stock_quantity=20,
        status=ProductStatus.active,
        tags=None,  # SQLite-safe: no list default
    )
    db_session.add(p)
    await db_session.flush()
    return p


# ── Auth helpers ───────────────────────────────────────────────────────────────

def auth_headers(user: User) -> dict:
    """Return Authorization header dict for a given user."""
    token = create_access_token({"sub": str(user.id), "role": user.role})
    return {"Authorization": f"Bearer {token}"}
