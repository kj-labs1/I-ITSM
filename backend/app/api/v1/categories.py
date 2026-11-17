"""Incident category configuration and required-skill mapping."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    decode_access_token,
    get_current_user_id,
    oauth2_scheme,
    require_role,
)
from app.infrastructure.database.models import IncidentCategoryModel
from app.infrastructure.database.session import get_db_session
from app.shared.enums import IncidentCategory

router = APIRouter(tags=["Incident Categories"])


class CategoryCreate(BaseModel):
    category: IncidentCategory
    description: str | None = None
    required_skill: str = Field(alias="requiredSkill", min_length=2, max_length=100)

    model_config = ConfigDict(populate_by_name=True)


class CategoryUpdate(BaseModel):
    category: IncidentCategory | None = None
    description: str | None = None
    required_skill: str | None = Field(
        default=None, alias="requiredSkill", min_length=2, max_length=100
    )
    is_active: bool | None = Field(default=None, alias="isActive")

    model_config = ConfigDict(populate_by_name=True)


class CategoryResponse(BaseModel):
    id: UUID
    category: IncidentCategory
    description: str | None
    required_skill: str = Field(serialization_alias="requiredSkill")
    is_active: bool = Field(serialization_alias="isActive")

    model_config = ConfigDict(from_attributes=True)


@router.post(
    "",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role("ADMIN"))],
)
async def create_category(
    request: CategoryCreate,
    db: AsyncSession = Depends(get_db_session),
):
    """Create a category and map it to a required technician skill."""

    existing = await db.execute(
        select(IncidentCategoryModel).where(
            IncidentCategoryModel.category == request.category
        )
    )

    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Category already exists")

    category = IncidentCategoryModel(
        category=request.category,
        description=request.description,
        required_skill=request.required_skill.strip(),
        is_active=True,
    )

    db.add(category)
    await db.flush()
    return category


@router.get("", response_model=list[CategoryResponse])
async def list_categories(
    include_inactive: bool = False,
    _user_id: UUID = Depends(get_current_user_id),
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db_session),
):
    """List active categories. Only administrators can include inactive ones."""

    if include_inactive:
        payload = decode_access_token(token)
        if payload.get("role") != "ADMIN":
            raise HTTPException(
                status_code=403,
                detail="Administrator access required",
            )

    query = select(IncidentCategoryModel)

    if not include_inactive:
        query = query.where(IncidentCategoryModel.is_active.is_(True))

    result = await db.execute(query.order_by(IncidentCategoryModel.category))

    return result.scalars().all()


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: UUID,
    _user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
):
    """Retrieve an incident category by ID."""

    category = await db.get(IncidentCategoryModel, category_id)

    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")

    return category


@router.patch(
    "/{category_id}",
    response_model=CategoryResponse,
    dependencies=[Depends(require_role("ADMIN"))],
)
async def update_category(
    category_id: UUID,
    request: CategoryUpdate,
    db: AsyncSession = Depends(get_db_session),
):
    """Update a category, its required skill, or active status."""

    category = await db.get(IncidentCategoryModel, category_id)

    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")

    changes = request.model_dump(exclude_unset=True)

    if not changes:
        raise HTTPException(status_code=400, detail="No changes provided")

    for field in ("category", "required_skill", "is_active"):
        if field in changes and changes[field] is None:
            raise HTTPException(status_code=422, detail=f"{field} cannot be null")

    if "category" in changes:
        duplicate = await db.execute(
            select(IncidentCategoryModel).where(
                IncidentCategoryModel.category == changes["category"],
                IncidentCategoryModel.id != category_id,
            )
        )
        if duplicate.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Category already exists")

    if "required_skill" in changes:
        changes["required_skill"] = changes["required_skill"].strip()

    for field, value in changes.items():
        setattr(category, field, value)

    await db.flush()
    return category


@router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role("ADMIN"))],
)
async def deactivate_category(
    category_id: UUID,
    db: AsyncSession = Depends(get_db_session),
):
    """Deactivate a category without permanently deleting it."""

    category = await db.get(IncidentCategoryModel, category_id)

    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")

    category.is_active = False
    await db.flush()
