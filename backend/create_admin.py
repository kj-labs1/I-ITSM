import asyncio
from getpass import getpass

from sqlalchemy import or_, select

from app.api.v1.auth import hash_password
from app.infrastructure.database.models import UserModel
from app.infrastructure.database.session import (
    close_engine,
    get_session_factory,
)
from app.shared.enums import UserRole


async def main():
    username = "admin"
    email = "admin@iitsm.local"
    password = getpass("Choose an admin password (minimum 8 characters): ")

    if len(password) < 8:
        print("Password must contain at least 8 characters.")
        return

    factory = get_session_factory()

    async with factory() as db:
        existing = await db.execute(
            select(UserModel).where(
                or_(
                    UserModel.username == username,
                    UserModel.email == email,
                )
            )
        )

        if existing.scalar_one_or_none():
            print("An account with this username or email already exists.")
            return

        admin = UserModel(
            username=username,
            email=email,
            full_name="System Administrator",
            password_hash=hash_password(password),
            role=UserRole.ADMIN,
            is_active=True,
        )

        db.add(admin)
        await db.commit()

        print("Administrator account created successfully.")
        print("Username:", username)
        print("Email:", email)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    finally:
        asyncio.run(close_engine())
