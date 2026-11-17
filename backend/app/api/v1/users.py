"""Admin APIs for user management."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user_id, require_role
from app.infrastructure.database.models import UserModel
from app.infrastructure.database.session import get_db_session
from app.shared.enums import UserRole

router = APIRouter(tags=["User Management"])


class UserResponse(BaseModel):
    id: UUID
    username: str
    email: str
    full_name: str = Field(serialization_alias="fullName")
    role: UserRole
    is_active: bool = Field(serialization_alias="isActive")

    model_config = ConfigDict(from_attributes=True)


class UserUpdateRequest(BaseModel):
    full_name: str | None = Field(
        default=None, alias="fullName", min_length=2, max_length=100
    )
    role: UserRole | None = None
    is_active: bool | None = Field(default=None, alias="isActive")

    model_config = ConfigDict(populate_by_name=True)


@router.get("/summary", dependencies=[Depends(require_role("ADMIN"))])
async def user_summary(db: AsyncSession = Depends(get_db_session)):
    """Return total, active, inactive and role-wise user counts."""

    rows = await db.execute(
        select(UserModel.role, func.count(UserModel.id)).group_by(UserModel.role)
    )

    counts = {role.value: count for role, count in rows.all()}
    for role in UserRole:
        counts.setdefault(role.value, 0)

    total = sum(counts.values())

    active = (
        await db.scalar(
            select(func.count(UserModel.id)).where(UserModel.is_active.is_(True))
        )
        or 0
    )

    return {
        "totalUsers": total,
        "activeUsers": active,
        "inactiveUsers": total - active,
        "usersByRole": counts,
    }


@router.get(
    "", response_model=list[UserResponse], dependencies=[Depends(require_role("ADMIN"))]
)
async def list_users(db: AsyncSession = Depends(get_db_session)):
    """List all registered users."""

    result = await db.execute(select(UserModel).order_by(UserModel.created_at.desc()))
    return result.scalars().all()


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    dependencies=[Depends(require_role("ADMIN"))],
)
async def get_user(user_id: UUID, db: AsyncSession = Depends(get_db_session)):
    """Retrieve a user by ID."""

    user = await db.get(UserModel, user_id)

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return user


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    request: UserUpdateRequest,
    admin_id: UUID = Depends(get_current_user_id),
    _role: str = Depends(require_role("ADMIN")),
    db: AsyncSession = Depends(get_db_session),
):
    """Update a user's name, role or active status."""

    user = await db.get(UserModel, user_id)

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    changes = request.model_dump(exclude_unset=True)

    if not changes:
        raise HTTPException(status_code=400, detail="No changes provided")

    # Prevent an administrator from accidentally locking themselves out.
    if user.id == admin_id and (
        changes.get("role") not in (None, UserRole.ADMIN)
        or changes.get("is_active") is False
    ):
        raise HTTPException(
            status_code=400,
            detail="You cannot deactivate or demote your own account",
        )

    for field, value in changes.items():
        if value is not None:
            setattr(user, field, value)

    await db.flush()
    return user


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def deactivate_user(
    user_id: UUID,
    admin_id: UUID = Depends(get_current_user_id),
    _role: str = Depends(require_role("ADMIN")),
    db: AsyncSession = Depends(get_db_session),
):
    """Deactivate a user without permanently deleting their account."""

    if user_id == admin_id:
        raise HTTPException(
            status_code=400,
            detail="You cannot deactivate your own account",
        )

    user = await db.get(UserModel, user_id)

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = False
    await db.flush()
