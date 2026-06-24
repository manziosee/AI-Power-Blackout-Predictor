"""Seed the database with realistic demo data for local development / demo mode.

Run after migrations: python scripts/seed_demo.py
"""
from __future__ import annotations

import asyncio
import random
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.config import settings
from app.core.security import get_password_hash

# Sample H3 resolution-7 cells (Kigali area — for demo)
DEMO_CELLS = [
    ("872a1072fffffff", "RW", -1.9441, 30.0619),
    ("872a107a7ffffff", "RW", -1.9501, 30.0571),
    ("872a10729ffffff", "RW", -1.9381, 30.0667),
    ("872a1072bffffff", "RW", -1.9321, 30.0715),
    ("872a10761ffffff", "RW", -1.9601, 30.0523),
    ("872a107a1ffffff", "RW", -1.9441, 30.0523),
    ("872a10763ffffff", "RW", -1.9661, 30.0571),
    ("872a107b1ffffff", "RW", -1.9541, 30.0763),
]

RISK_LEVELS = ["low", "medium", "high", "critical"]
MODEL_VERSIONS = ["xgb-v2.1.0", "xgb-v2.2.0"]


async def seed(db: AsyncSession) -> None:
    from app.models.prediction import Prediction
    from app.models.outage import OutageReport
    from app.models.user import User
    from app.models.neighborhood import H3Cell

    # Check if already seeded
    result = await db.execute(text("SELECT COUNT(*) FROM users"))
    if result.scalar() > 0:
        print("Database already seeded — skipping.")
        return

    print("Seeding demo data...")

    # 1. Admin user
    admin = User(
        id=uuid.uuid4(),
        phone="+250788000001",
        country_code="RW",
        language="en",
        password_hash=get_password_hash("admin1234"),
        is_active=True,
        is_admin=True,
    )
    db.add(admin)

    # 2. Regular users
    users: list[User] = [admin]
    for i in range(1, 21):
        u = User(
            id=uuid.uuid4(),
            phone=f"+2507880000{i:02d}",
            country_code="RW",
            language=random.choice(["en", "fr", "rw"]),
            password_hash=get_password_hash("password123"),
            is_active=True,
        )
        db.add(u)
        users.append(u)

    # 3. H3 cells
    cells: list[H3Cell] = []
    for h3_idx, country, lat, lng in DEMO_CELLS:
        cell = H3Cell(
            id=uuid.uuid4(),
            h3_index=h3_idx,
            country_code=country,
            center_lat=lat,
            center_lng=lng,
            resolution=7,
        )
        db.add(cell)
        cells.append(cell)

    await db.flush()

    # 4. Predictions (last 48 hours, every 4 hours)
    now = datetime.now(timezone.utc)
    for cell in cells:
        for hours_ago in range(0, 49, 4):
            predicted_at = now - timedelta(hours=hours_ago)
            prob = round(random.uniform(0.05, 0.85), 3)
            risk = (
                "critical" if prob > 0.75
                else "high" if prob > 0.55
                else "medium" if prob > 0.35
                else "low"
            )
            pred = Prediction(
                id=uuid.uuid4(),
                h3_index=cell.h3_index,
                predicted_at=predicted_at,
                window_start=predicted_at,
                window_end=predicted_at + timedelta(hours=4),
                probability=prob,
                confidence=round(random.uniform(0.65, 0.95), 3),
                risk_level=risk,
                model_version=random.choice(MODEL_VERSIONS),
                region_model=f"xgb-{cell.country_code.lower()}-r7",
                features_snapshot={
                    "weather_risk": round(random.uniform(0, 10), 2),
                    "historical_frequency": round(random.uniform(0, 10), 2),
                    "grid_age": round(random.uniform(0, 10), 2),
                    "load_factor": round(random.uniform(0, 10), 2),
                    "time_since_last_outage": round(random.uniform(0, 10), 2),
                    "maintenance_score": round(random.uniform(0, 10), 2),
                },
            )
            db.add(pred)

    # 5. Outage reports (last 24 hours)
    for _ in range(30):
        cell = random.choice(cells)
        reporter = random.choice(users[1:])
        reported_at = now - timedelta(hours=random.uniform(0, 24))
        resolved = random.random() > 0.4
        report = OutageReport(
            id=uuid.uuid4(),
            user_id=reporter.id,
            h3_index=cell.h3_index,
            lat=cell.center_lat + random.uniform(-0.002, 0.002),
            lng=cell.center_lng + random.uniform(-0.002, 0.002),
            source=random.choice(["app", "sms", "ussd"]),
            reported_at=reported_at,
            verified=random.random() > 0.5,
            verification_count=random.randint(0, 5),
            resolved_at=reported_at + timedelta(hours=random.uniform(1, 6)) if resolved else None,
        )
        db.add(report)

    await db.commit()
    print(f"Seeded: {len(users)} users, {len(cells)} cells, predictions + {30} outage reports.")
    print("Admin login: phone=+250788000001 password=admin1234")


async def main() -> None:
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        await seed(session)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
