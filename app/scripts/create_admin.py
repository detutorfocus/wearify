"""
Create an admin user from the command line.

Usage:
  docker-compose exec backend python -m app.scripts.create_admin \
    --email admin@wearify.com \
    --password SecurePass123! \
    --name "Platform Admin"
"""
import asyncio
import argparse
import uuid

from app.core.database import AsyncSessionLocal, create_tables
from app.core.security import get_password_hash
from app.models.user import User, UserRole


async def create_admin(email: str, password: str, full_name: str) -> None:
    await create_tables()
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        existing = await db.execute(select(User).where(User.email == email))
        if existing.scalar_one_or_none():
            print(f"❌ User {email} already exists.")
            return

        user = User(
            id=uuid.uuid4(),
            email=email,
            hashed_password=get_password_hash(password),
            full_name=full_name,
            role=UserRole.admin,
            is_active=True,
            is_verified=True,
        )
        db.add(user)
        await db.commit()
        print(f"✅ Admin created: {email}")


def main():
    parser = argparse.ArgumentParser(description="Create a Wearify admin user")
    parser.add_argument("--email", required=True, help="Admin email address")
    parser.add_argument("--password", required=True, help="Admin password (min 8 chars)")
    parser.add_argument("--name", default="Platform Admin", help="Admin full name")
    args = parser.parse_args()

    if len(args.password) < 8:
        print("❌ Password must be at least 8 characters.")
        return

    asyncio.run(create_admin(args.email, args.password, args.name))


if __name__ == "__main__":
    main()
