"""Administrative reporting endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_role
from app.infrastructure.database.models import (
    IncidentCategoryModel,
    ServiceModel,
    UserModel,
)
from app.infrastructure.database.session import get_db_session
from app.shared.enums import UserRole

router = APIRouter(tags=["Reports"])


@router.get("/summary", dependencies=[Depends(require_role("ADMIN"))])
async def get_summary(db: AsyncSession = Depends(get_db_session)):
    """Return a summary of users, services and incident categories."""

    role_rows = await db.execute(
        select(UserModel.role, func.count(UserModel.id)).group_by(UserModel.role)
    )

    users_by_role = {role.value: count for role, count in role_rows.all()}

    for role in UserRole:
        users_by_role.setdefault(role.value, 0)

    total_users = sum(users_by_role.values())

    active_users = (
        await db.scalar(
            select(func.count(UserModel.id)).where(UserModel.is_active.is_(True))
        )
        or 0
    )

    total_services = await db.scalar(select(func.count(ServiceModel.id))) or 0

    active_services = (
        await db.scalar(
            select(func.count(ServiceModel.id)).where(ServiceModel.is_active.is_(True))
        )
        or 0
    )

    total_categories = (
        await db.scalar(select(func.count(IncidentCategoryModel.id))) or 0
    )

    active_categories = (
        await db.scalar(
            select(func.count(IncidentCategoryModel.id)).where(
                IncidentCategoryModel.is_active.is_(True)
            )
        )
        or 0
    )

    return {
        "users": {
            "total": total_users,
            "active": active_users,
            "inactive": total_users - active_users,
            "byRole": users_by_role,
        },
        "services": {
            "total": total_services,
            "active": active_services,
            "inactive": total_services - active_services,
        },
        "categories": {
            "total": total_categories,
            "active": active_categories,
            "inactive": total_categories - active_categories,
        },
    }
