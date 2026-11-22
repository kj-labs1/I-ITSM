"""
Idempotent Database Seeder for I-ITSM.

Initializes standard demo accounts, services, incident categories, and technician profiles.
Safe to run repeatedly on existing or fresh databases:
- Detects existing records and preserves them.
- Uses standard password hashing.
- Sets up demo roles:
    - admin_user (ADMIN)
    - sysadmin   (ADMIN)
    - emp_bob    (EMPLOYEE)
    - tech_alice (TECHNICIAN with complete profile and skills)
    - tech_charlie (TECHNICIAN with complete profile and skills)
- Seeds initial IT services and incident category taxonomies.
"""

from __future__ import annotations

import asyncio
import logging
from uuid import UUID, uuid4

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import hash_password
from app.infrastructure.database.models import (
    IncidentCategoryModel,
    ServiceModel,
    TechnicianModel,
    TechnicianSkillModel,
    UserModel,
)
from app.infrastructure.database.session import close_engine, get_session_factory
from app.shared.enums import AvailabilityStatus, IncidentCategory, UserRole

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("seed_demo_data")

# ── Demo Users Definition ───────────────────────────────────────────────────

DEMO_USERS = [
    {
        "id": UUID("00000000-0000-0000-0000-000000000001"),
        "username": "sysadmin",
        "email": "sysadmin@iitsm.local",
        "full_name": "System Administrator",
        "password": "AdminPassword123!",
        "role": UserRole.ADMIN,
    },
    {
        "id": UUID("00000000-0000-0000-0000-000000000002"),
        "username": "admin_user",
        "email": "admin_user@iitsm.local",
        "full_name": "IT Operations Admin",
        "password": "AdminPassword123!",
        "role": UserRole.ADMIN,
    },
    {
        "id": UUID("00000000-0000-0000-0000-000000000003"),
        "username": "emp_bob",
        "email": "bob@iitsm.local",
        "full_name": "Bob Smith",
        "password": "EmpPassword123!",
        "role": UserRole.EMPLOYEE,
    },
    {
        "id": UUID("00000000-0000-0000-0000-000000000004"),
        "username": "tech_alice",
        "email": "alice@iitsm.local",
        "full_name": "Alice Johnson",
        "password": "TechPassword123!",
        "role": UserRole.TECHNICIAN,
        "profile": {
            "experience_years": 5,
            "max_capacity": 10,
            "availability": AvailabilityStatus.AVAILABLE,
            "skills": [
                ("NETWORK", 5),
                ("SECURITY", 4),
                ("CLOUD", 3),
            ],
        },
    },
    {
        "id": UUID("00000000-0000-0000-0000-000000000005"),
        "username": "tech_charlie",
        "email": "charlie@iitsm.local",
        "full_name": "Charlie Davis",
        "password": "TechPassword123!",
        "role": UserRole.TECHNICIAN,
        "profile": {
            "experience_years": 3,
            "max_capacity": 8,
            "availability": AvailabilityStatus.AVAILABLE,
            "skills": [
                ("HARDWARE", 4),
                ("SOFTWARE", 4),
                ("APPLICATION", 3),
            ],
        },
    },
]

# ── Demo Services Definition ────────────────────────────────────────────────

DEMO_SERVICES = [
    {
        "id": UUID("00000000-0000-0000-0001-000000000001"),
        "name": "Core Network Infrastructure",
        "description": "High-availability enterprise networking, WAN/LAN routing, and VPN gateways.",
        "business_criticality": 5,
    },
    {
        "id": UUID("00000000-0000-0000-0001-000000000002"),
        "name": "Production Database Cluster",
        "description": "PostgreSQL replication cluster hosting core business services.",
        "business_criticality": 5,
    },
    {
        "id": UUID("00000000-0000-0000-0001-000000000003"),
        "name": "Corporate Identity & SSO",
        "description": "Centralized authentication, OAuth2, and active directory identity provider.",
        "business_criticality": 4,
    },
    {
        "id": UUID("00000000-0000-0000-0001-000000000004"),
        "name": "Workplace Endpoints & Hardware",
        "description": "Laptops, workstations, peripherals, and workstation operating systems.",
        "business_criticality": 3,
    },
]

# ── Demo Categories Definition ──────────────────────────────────────────────

DEMO_CATEGORIES = [
    (IncidentCategory.NETWORK, "NETWORK", "Network connectivity, switches, Wi-Fi, and firewall issues"),
    (IncidentCategory.HARDWARE, "HARDWARE", "Physical computer equipment, monitors, peripherals, and printers"),
    (IncidentCategory.SOFTWARE, "SOFTWARE", "Operating system, desktop applications, and productivity tools"),
    (IncidentCategory.DATABASE, "DATABASE", "Database connections, queries, integrity, and replication"),
    (IncidentCategory.SECURITY, "SECURITY", "Access violations, suspicious activity, malware, and certificates"),
    (IncidentCategory.CLOUD, "CLOUD", "Virtual servers, storage buckets, and containerized cloud services"),
    (IncidentCategory.APPLICATION, "APPLICATION", "Internal enterprise web portals and ERP business systems"),
    (IncidentCategory.AUTHENTICATION, "AUTHENTICATION", "Account lockout, password resets, MFA, and SSO failures"),
    (IncidentCategory.STORAGE, "STORAGE", "Network attached storage, shared drives, and backup recovery"),
]


async def seed_users_and_technicians(db: AsyncSession) -> None:
    for user_def in DEMO_USERS:
        # Check if user already exists by username or email
        existing_user = (
            await db.execute(
                select(UserModel).where(
                    or_(
                        UserModel.username == user_def["username"],
                        UserModel.email == user_def["email"],
                    )
                )
            )
        ).scalar_one_or_none()

        if existing_user is None:
            user = UserModel(
                id=user_def["id"],
                username=user_def["username"],
                email=user_def["email"],
                full_name=user_def["full_name"],
                password_hash=hash_password(user_def["password"]),
                role=user_def["role"],
                is_active=True,
            )
            db.add(user)
            await db.flush()
            logger.info("Created demo user: %s (Role: %s)", user.username, user.role.value)
        else:
            user = existing_user
            logger.info("Preserved existing user: %s", user.username)

        # Seed technician operational profile if specified
        if "profile" in user_def:
            prof_data = user_def["profile"]
            existing_tech = (
                await db.execute(
                    select(TechnicianModel).where(TechnicianModel.user_id == user.id)
                )
            ).scalar_one_or_none()

            if existing_tech is None:
                tech = TechnicianModel(
                    id=uuid4(),
                    user_id=user.id,
                    experience_years=prof_data["experience_years"],
                    max_capacity=prof_data["max_capacity"],
                    availability=prof_data["availability"],
                )
                db.add(tech)
                await db.flush()

                for skill_name, prof_lvl in prof_data["skills"]:
                    skill = TechnicianSkillModel(
                        id=uuid4(),
                        technician_id=tech.id,
                        skill_name=skill_name,
                        proficiency_level=prof_lvl,
                    )
                    db.add(skill)

                logger.info("Created technician profile for: %s with %d skills", user.username, len(prof_data["skills"]))
            else:
                logger.info("Preserved existing technician profile for: %s", user.username)


async def seed_services(db: AsyncSession) -> None:
    for s_def in DEMO_SERVICES:
        existing = (
            await db.execute(
                select(ServiceModel).where(ServiceModel.name == s_def["name"])
            )
        ).scalar_one_or_none()

        if existing is None:
            svc = ServiceModel(
                id=s_def["id"],
                name=s_def["name"],
                description=s_def["description"],
                business_criticality=s_def["business_criticality"],
                is_active=True,
            )
            db.add(svc)
            logger.info("Created IT service: %s", s_def["name"])
        else:
            logger.info("Preserved existing service: %s", s_def["name"])


async def seed_categories(db: AsyncSession) -> None:
    for cat_enum, req_skill, desc in DEMO_CATEGORIES:
        existing = (
            await db.execute(
                select(IncidentCategoryModel).where(
                    IncidentCategoryModel.category == cat_enum
                )
            )
        ).scalar_one_or_none()

        if existing is None:
            category_record = IncidentCategoryModel(
                id=uuid4(),
                category=cat_enum,
                required_skill=req_skill,
                description=desc,
                is_active=True,
            )
            db.add(category_record)
            logger.info("Created incident category: %s -> %s", cat_enum.value, req_skill)
        else:
            logger.info("Preserved existing category: %s", cat_enum.value)


async def main() -> None:
    factory = get_session_factory()
    logger.info("Starting I-ITSM database seeding...")
    async with factory() as db:
        try:
            await seed_users_and_technicians(db)
            await seed_services(db)
            await seed_categories(db)
            await db.commit()
            logger.info("I-ITSM demo data seeding completed successfully.")
        except Exception:
            await db.rollback()
            logger.exception("Seeding failed; transaction rolled back.")
            raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    finally:
        asyncio.run(close_engine())
