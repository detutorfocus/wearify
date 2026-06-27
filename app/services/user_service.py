from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User
from app.core.security import get_password_hash
from app.schemas.user import UserRegister


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: str | UUID) -> User | None:
        import uuid as _uuid
        # Ensure we pass a UUID object, not a string (matters for SQLite in tests)
        if isinstance(user_id, str):
            try:
                user_id = _uuid.UUID(user_id)
            except ValueError:
                return None
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def create_user(self, data: UserRegister) -> User:
        user = User(
            email=data.email,
            hashed_password=get_password_hash(data.password),
            full_name=data.full_name,
            phone=data.phone,
        )
        self.db.add(user)
        await self.db.flush()
        return user

    async def update_user(self, user_id: UUID, data: dict) -> User:
        user = await self.get_by_id(user_id)
        for key, value in data.items():
            if value is not None:
                setattr(user, key, value)
        await self.db.flush()
        return user
