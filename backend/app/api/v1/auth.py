"""Registration, login and current-user endpoints (Member 1)."""

from uuid import UUID

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, get_current_user_id
from app.infrastructure.database.models import UserModel
from app.infrastructure.database.session import get_db_session
from app.shared.enums import UserRole

router = APIRouter(tags=["Authentication"])


# ---------- Request and response schemas ----------


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: str = Field(min_length=5, max_length=255)
    full_name: str = Field(alias="fullName", min_length=2, max_length=100)
    password: str = Field(min_length=8, max_length=128)

    model_config = ConfigDict(populate_by_name=True)


class UserResponse(BaseModel):
    id: UUID
    username: str
    email: str
    full_name: str = Field(serialization_alias="fullName")
    role: UserRole
    is_active: bool = Field(serialization_alias="isActive")

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str = Field(serialization_alias="accessToken")
    token_type: str = Field(default="bearer", serialization_alias="tokenType")


# ---------- Password helpers ----------


def hash_password(password: str) -> str:
    """Return a secure hash of the supplied password."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Check a password against its stored hash."""
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"),
            password_hash.encode("utf-8"),
        )
    except Exception:
        return False


# ---------- Registration ----------


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """Register a new employee account."""

    email = request.email.strip().lower()
    username = request.username.strip()

    existing = await db.execute(
        select(UserModel).where(
            or_(
                UserModel.username == username,
                UserModel.email == email,
            )
        )
    )

    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already exists",
        )

    user = UserModel(
        username=username,
        email=email,
        full_name=request.full_name.strip(),
        password_hash=hash_password(request.password),
        role=UserRole.EMPLOYEE,
        is_active=True,
    )

    db.add(user)
    await db.flush()

    return user


# ---------- Login ----------


@router.post("/login", response_model=TokenResponse)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db_session),
):
    """Authenticate using username or email and return a JWT."""

    result = await db.execute(
        select(UserModel).where(
            or_(
                UserModel.username == form.username.strip(),
                UserModel.email == form.username.strip().lower(),
            )
        )
    )

    user = result.scalar_one_or_none()

    if (
        user is None
        or not verify_password(form.password, user.password_hash)
        or not user.is_active
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(
        {
            "sub": str(user.id),
            "role": user.role.value,
        }
    )

    return TokenResponse(access_token=token)


# ---------- Current user ----------


@router.get("/me", response_model=UserResponse)
async def get_me(
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
):
    """Return the currently authenticated user's profile."""

    result = await db.execute(select(UserModel).where(UserModel.id == user_id))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found or inactive",
        )

    return user
