import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin
from app.core.database import get_db
from app.models.organization import Organization
from app.models.user import User

router = APIRouter(prefix="/orgs", tags=["Organizations"])


class OrgCreate(BaseModel):
    name: str
    slug: str
    plan: str = "free"
    region: str = "global"


class OrgOut(BaseModel):
    id: str
    name: str
    slug: str
    plan: str
    region: str
    created_at: datetime

    model_config = {"from_attributes": True}


@router.post("", response_model=OrgOut, status_code=201)
async def create_org(
    body: OrgCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> OrgOut:
    existing = await db.execute(select(Organization).where(Organization.slug == body.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="slug already taken")
    org = Organization(
        id=uuid.uuid4(),
        name=body.name,
        slug=body.slug,
        plan=body.plan,
        region=body.region,
    )
    db.add(org)
    await db.commit()
    await db.refresh(org)
    return OrgOut(
        id=str(org.id),
        name=org.name,
        slug=org.slug,
        plan=org.plan,
        region=org.region,
        created_at=org.created_at,
    )


@router.get("", response_model=list[OrgOut])
async def list_orgs(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> list[OrgOut]:
    rows = await db.execute(select(Organization).order_by(Organization.created_at.desc()))
    orgs = rows.scalars().all()
    return [
        OrgOut(
            id=str(o.id), name=o.name, slug=o.slug,
            plan=o.plan, region=o.region, created_at=o.created_at,
        )
        for o in orgs
    ]


@router.get("/{slug}", response_model=OrgOut)
async def get_org(
    slug: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> OrgOut:
    row = await db.execute(select(Organization).where(Organization.slug == slug))
    org = row.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return OrgOut(
        id=str(org.id), name=org.name, slug=org.slug,
        plan=org.plan, region=org.region, created_at=org.created_at,
    )


@router.delete("/{slug}", status_code=204)
async def delete_org(
    slug: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
) -> None:
    row = await db.execute(select(Organization).where(Organization.slug == slug))
    org = row.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    await db.delete(org)
    await db.commit()
