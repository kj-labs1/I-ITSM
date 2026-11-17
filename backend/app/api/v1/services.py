"""IT service catalogue management endpoints."""

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
from app.infrastructure.database.models import ServiceModel
from app.infrastructure.database.session import get_db_session

router = APIRouter(tags=["Service Catalogue"])


class ServiceCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str | None = None
    business_criticality: int = Field(
        default=3, alias="businessCriticality", ge=1, le=5
    )

    model_config = ConfigDict(populate_by_name=True)


class ServiceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = None
    business_criticality: int | None = Field(
        default=None, alias="businessCriticality", ge=1, le=5
    )
    is_active: bool | None = Field(default=None, alias="isActive")

    model_config = ConfigDict(populate_by_name=True)


class ServiceResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    business_criticality: int = Field(serialization_alias="businessCriticality")
    is_active: bool = Field(serialization_alias="isActive")

    model_config = ConfigDict(from_attributes=True)


@router.post(
    "",
    response_model=ServiceResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role("ADMIN"))],
)
async def create_service(
    request: ServiceCreate,
    db: AsyncSession = Depends(get_db_session),
):
    """Create a new IT service."""

    name = request.name.strip()

    existing = await db.execute(select(ServiceModel).where(ServiceModel.name == name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Service already exists")

    service = ServiceModel(
        name=name,
        description=request.description,
        business_criticality=request.business_criticality,
        is_active=True,
    )

    db.add(service)
    await db.flush()
    return service


@router.get("", response_model=list[ServiceResponse])
async def list_services(
    include_inactive: bool = False,
    _user_id: UUID = Depends(get_current_user_id),
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db_session),
):
    """List active services. Only administrators can include inactive ones."""

    if include_inactive:
        payload = decode_access_token(token)
        if payload.get("role") != "ADMIN":
            raise HTTPException(
                status_code=403,
                detail="Administrator access required",
            )

    query = select(ServiceModel)

    if not include_inactive:
        query = query.where(ServiceModel.is_active.is_(True))

    result = await db.execute(query.order_by(ServiceModel.name))
    return result.scalars().all()


@router.get("/{service_id}", response_model=ServiceResponse)
async def get_service(
    service_id: UUID,
    _user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
):
    """Retrieve a service by ID."""

    service = await db.get(ServiceModel, service_id)

    if service is None:
        raise HTTPException(status_code=404, detail="Service not found")

    return service


@router.patch(
    "/{service_id}",
    response_model=ServiceResponse,
    dependencies=[Depends(require_role("ADMIN"))],
)
async def update_service(
    service_id: UUID,
    request: ServiceUpdate,
    db: AsyncSession = Depends(get_db_session),
):
    """Update service details or active status."""

    service = await db.get(ServiceModel, service_id)

    if service is None:
        raise HTTPException(status_code=404, detail="Service not found")

    changes = request.model_dump(exclude_unset=True)

    if not changes:
        raise HTTPException(status_code=400, detail="No changes provided")

    for field in ("name", "business_criticality", "is_active"):
        if field in changes and changes[field] is None:
            raise HTTPException(
                status_code=422,
                detail=f"{field} cannot be null",
            )

    if changes.get("name") is not None:
        name = changes["name"].strip()
        duplicate = await db.execute(
            select(ServiceModel).where(
                ServiceModel.name == name,
                ServiceModel.id != service_id,
            )
        )
        if duplicate.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Service name already exists")
        changes["name"] = name

    for field, value in changes.items():
        setattr(service, field, value)

    await db.flush()
    return service


@router.delete(
    "/{service_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role("ADMIN"))],
)
async def deactivate_service(
    service_id: UUID,
    db: AsyncSession = Depends(get_db_session),
):
    """Deactivate a service instead of permanently deleting it."""

    service = await db.get(ServiceModel, service_id)

    if service is None:
        raise HTTPException(status_code=404, detail="Service not found")

    service.is_active = False
    await db.flush()
