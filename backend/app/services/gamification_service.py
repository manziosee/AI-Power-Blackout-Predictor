"""Points, badges, levels and leaderboard for community engagement."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.community import UserPoints

log = logging.getLogger(__name__)

# ── Point values ──────────────────────────────────────────────────────────────
POINTS = {
    "report":         10,
    "first_reporter": 15,   # bonus if first in cell within last hour
    "confirm":         5,
    "resolve":         3,
    "add_note":        2,
    "streak_bonus":   10,   # daily streak maintained
}

# ── Badge definitions ─────────────────────────────────────────────────────────
BADGES = {
    "first_report": {
        "name": "First Responder",
        "emoji": "🚨",
        "description": "First person to report an outage",
        "condition": lambda stats: stats["report_count"] >= 1,
    },
    "reporter_10": {
        "name": "Reliable Reporter",
        "emoji": "📡",
        "description": "Submitted 10 verified outage reports",
        "condition": lambda stats: stats["report_count"] >= 10,
    },
    "reporter_50": {
        "name": "Field Agent",
        "emoji": "🕵️",
        "description": "Submitted 50 verified outage reports",
        "condition": lambda stats: stats["report_count"] >= 50,
    },
    "confirmer_25": {
        "name": "Truth Seeker",
        "emoji": "✅",
        "description": "Confirmed 25 outage reports from neighbors",
        "condition": lambda stats: stats["confirm_count"] >= 25,
    },
    "streak_7": {
        "name": "Streak Keeper",
        "emoji": "🔥",
        "description": "Reported or confirmed outages 7 days in a row",
        "condition": lambda stats: stats["current_streak_days"] >= 7,
    },
    "streak_30": {
        "name": "Guardian",
        "emoji": "🛡️",
        "description": "Maintained a 30-day activity streak",
        "condition": lambda stats: stats["current_streak_days"] >= 30,
    },
    "community_100": {
        "name": "Community Champion",
        "emoji": "🏆",
        "description": "Earned 100+ points contributing to the community",
        "condition": lambda stats: stats["total_points"] >= 100,
    },
    "community_500": {
        "name": "Power Hero",
        "emoji": "⚡",
        "description": "Earned 500+ points — a pillar of the community",
        "condition": lambda stats: stats["total_points"] >= 500,
    },
}

# ── Levels ────────────────────────────────────────────────────────────────────
LEVELS = [
    (0,    "Newcomer",    "🌱"),
    (50,   "Contributor", "📱"),
    (200,  "Reporter",    "📡"),
    (500,  "Guardian",    "🛡️"),
    (1000, "Champion",    "🏆"),
    (2500, "Power Hero",  "⚡"),
]


def get_level(total_points: int) -> dict:
    level_name, level_emoji = LEVELS[0][1], LEVELS[0][2]
    next_threshold = LEVELS[1][0]
    for i, (threshold, name, emoji) in enumerate(LEVELS):
        if total_points >= threshold:
            level_name, level_emoji = name, emoji
            next_threshold = LEVELS[i + 1][0] if i + 1 < len(LEVELS) else None
    progress = None
    if next_threshold:
        current_threshold = max(t for t, _, _ in LEVELS if total_points >= t)
        progress = round((total_points - current_threshold) / (next_threshold - current_threshold) * 100, 1)
    return {"name": level_name, "emoji": level_emoji, "next_at": next_threshold, "progress_pct": progress}


async def award_points(user_id: uuid.UUID, action: str, reference_id: str | None = None) -> int:
    """Award points for an action. Returns new total."""
    pts = POINTS.get(action, 0)
    if pts == 0:
        return 0

    from app.core.database import AsyncSessionLocal
    from app.models.community import PointTransaction, UserPoints
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(UserPoints).where(UserPoints.user_id == user_id))
        up = result.scalar_one_or_none()

        now = datetime.now(timezone.utc)

        if not up:
            up = UserPoints(
                user_id=user_id,
                total_points=0, weekly_points=0, monthly_points=0,
                report_count=0, confirm_count=0, note_count=0,
                current_streak_days=0,
            )
            db.add(up)

        # Streak check
        if up.last_action_at:
            gap = (now - up.last_action_at).days
            if gap == 1:
                up.current_streak_days += 1
                if up.current_streak_days % 7 == 0:
                    pts += POINTS["streak_bonus"]
                    db.add(PointTransaction(user_id=user_id, points=POINTS["streak_bonus"], action="streak_bonus"))
            elif gap > 1:
                up.current_streak_days = 1
        else:
            up.current_streak_days = 1

        up.total_points += pts
        up.weekly_points += pts
        up.monthly_points += pts
        up.last_action_at = now

        if action == "report":
            up.report_count += 1
        elif action == "confirm":
            up.confirm_count += 1
        elif action == "add_note":
            up.note_count += 1

        db.add(PointTransaction(user_id=user_id, points=pts, action=action, reference_id=reference_id))
        await db.commit()
        await db.refresh(up)

        # Check for new badges (fire and forget)
        await _check_and_award_badges(user_id, up)

        return up.total_points


async def _check_and_award_badges(user_id: uuid.UUID, up: "UserPoints") -> None:
    from app.core.database import AsyncSessionLocal
    from app.models.community import UserBadge
    from sqlalchemy import select

    stats = {
        "report_count": up.report_count,
        "confirm_count": up.confirm_count,
        "current_streak_days": up.current_streak_days,
        "total_points": up.total_points,
    }

    async with AsyncSessionLocal() as db:
        existing_result = await db.execute(
            select(UserBadge.badge_key).where(UserBadge.user_id == user_id)
        )
        existing_keys = {r[0] for r in existing_result.fetchall()}

        for key, badge in BADGES.items():
            if key in existing_keys:
                continue
            if badge["condition"](stats):
                db.add(UserBadge(
                    user_id=user_id,
                    badge_key=key,
                    badge_name=badge["name"],
                    badge_emoji=badge["emoji"],
                    badge_description=badge["description"],
                ))
                log.info(f"Badge awarded: {key} → user {user_id}")

        await db.commit()


async def get_user_stats(user_id: uuid.UUID) -> dict:
    from app.core.database import AsyncSessionLocal
    from app.models.community import UserBadge, UserPoints
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        up_result = await db.execute(select(UserPoints).where(UserPoints.user_id == user_id))
        up = up_result.scalar_one_or_none()

        badges_result = await db.execute(
            select(UserBadge).where(UserBadge.user_id == user_id).order_by(UserBadge.earned_at)
        )
        badges = badges_result.scalars().all()

    if not up:
        return {
            "total_points": 0, "weekly_points": 0, "report_count": 0,
            "confirm_count": 0, "current_streak_days": 0,
            "level": get_level(0), "badges": [],
        }

    return {
        "total_points": up.total_points,
        "weekly_points": up.weekly_points,
        "monthly_points": up.monthly_points,
        "report_count": up.report_count,
        "confirm_count": up.confirm_count,
        "note_count": up.note_count,
        "current_streak_days": up.current_streak_days,
        "level": get_level(up.total_points),
        "badges": [
            {
                "key": b.badge_key,
                "name": b.badge_name,
                "emoji": b.badge_emoji,
                "description": b.badge_description,
                "earned_at": b.earned_at.isoformat(),
            }
            for b in badges
        ],
    }


async def get_leaderboard(country_code: str, city: str | None = None, period: str = "weekly", limit: int = 20) -> list[dict]:
    """Return top users sorted by points for the given period."""
    from app.core.database import AsyncSessionLocal
    from app.models.community import UserPoints
    from app.models.user import User
    from sqlalchemy import select

    points_col = UserPoints.weekly_points if period == "weekly" else UserPoints.monthly_points

    async with AsyncSessionLocal() as db:
        query = (
            select(User.phone, User.country_code, UserPoints)
            .join(UserPoints, UserPoints.user_id == User.id)
            .where(User.country_code == country_code.upper())
            .order_by(points_col.desc())
            .limit(limit)
        )
        result = await db.execute(query)
        rows = result.fetchall()

    return [
        {
            "rank": i + 1,
            "phone_masked": _mask_phone(row.phone),
            "country_code": row.country_code,
            "points": getattr(row.UserPoints, f"{period}_points"),
            "total_points": row.UserPoints.total_points,
            "report_count": row.UserPoints.report_count,
            "confirm_count": row.UserPoints.confirm_count,
            "streak": row.UserPoints.current_streak_days,
            "level": get_level(row.UserPoints.total_points)["name"],
        }
        for i, row in enumerate(rows)
    ]


async def reset_weekly_points() -> None:
    """Reset weekly_points to 0 every Monday."""
    from app.core.database import AsyncSessionLocal
    from app.models.community import UserPoints
    from sqlalchemy import update

    async with AsyncSessionLocal() as db:
        await db.execute(update(UserPoints).values(weekly_points=0))
        await db.commit()


def _mask_phone(phone: str) -> str:
    if len(phone) < 6:
        return "****"
    return phone[:4] + "****" + phone[-2:]
