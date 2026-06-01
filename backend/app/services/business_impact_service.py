"""Business Impact Score — estimate financial cost of a predicted outage."""
import logging

log = logging.getLogger(__name__)

# ── Hourly cost defaults by business type + country income group (USD) ────────
# Derived from IEA, World Bank, and industry surveys on power outage costs.
# income_group: high | upper_middle | lower_middle | low
HOURLY_COST = {
    "high": {           # US, EU, Australia, Japan, South Korea
        "shop":       55,
        "restaurant": 90,
        "office":     75,
        "factory":    250,
        "hospital":   500,
        "other":      60,
    },
    "upper_middle": {   # Brazil, South Africa, Colombia, Malaysia
        "shop":       20,
        "restaurant": 35,
        "office":     28,
        "factory":    80,
        "hospital":   180,
        "other":      22,
    },
    "lower_middle": {   # Nigeria, Kenya, Ghana, India, Morocco
        "shop":        8,
        "restaurant": 15,
        "office":     12,
        "factory":    35,
        "hospital":    80,
        "other":       9,
    },
    "low": {            # Rwanda, Uganda, Ethiopia, Tanzania, Mali
        "shop":        3,
        "restaurant":  6,
        "office":      5,
        "factory":     15,
        "hospital":   40,
        "other":       4,
    },
}

COUNTRY_INCOME_GROUP = {
    # High income
    "US": "high", "GB": "high", "FR": "high", "DE": "high", "JP": "high",
    "AU": "high", "CA": "high", "KR": "high", "SG": "high",
    # Upper middle
    "BR": "upper_middle", "ZA": "upper_middle", "CO": "upper_middle",
    "MX": "upper_middle", "MY": "upper_middle", "TH": "upper_middle",
    "TR": "upper_middle", "AR": "upper_middle",
    # Lower middle
    "NG": "lower_middle", "KE": "lower_middle", "GH": "lower_middle",
    "IN": "lower_middle", "PK": "lower_middle", "BD": "lower_middle",
    "MA": "lower_middle", "EG": "lower_middle", "CI": "lower_middle",
    # Low income
    "RW": "low", "UG": "low", "TZ": "low", "ET": "low", "ML": "low",
    "BF": "low", "SN": "low", "MZ": "low",
}

BUSINESS_TYPE_LABELS = {
    "shop":       "Retail Shop",
    "restaurant": "Restaurant / Food Service",
    "office":     "Office / Co-working",
    "factory":    "Manufacturing / Factory",
    "hospital":   "Hospital / Clinic",
    "other":      "Other Business",
}


def compute_impact(
    business_type: str,
    country_code: str,
    duration_hours: float,
    probability: float,
    monthly_revenue_usd: float | None = None,
) -> dict:
    """Return estimated financial impact with breakdown.

    If the business provided their own revenue, use that for a precise estimate.
    Otherwise use the industry average for their country income group.
    """
    income_group = COUNTRY_INCOME_GROUP.get(country_code.upper(), "lower_middle")
    type_key = business_type if business_type in HOURLY_COST["high"] else "other"

    if monthly_revenue_usd:
        # Custom hourly rate: assume 8 operating hours/day, 26 days/month
        hourly_rate = monthly_revenue_usd / (26 * 8)
    else:
        hourly_rate = HOURLY_COST[income_group][type_key]

    direct_loss     = round(hourly_rate * duration_hours, 2)
    expected_loss   = round(direct_loss * probability, 2)   # probability-weighted
    monthly_risk    = round(expected_loss * 4, 2)           # ~4 outage windows per week

    return {
        "business_type": type_key,
        "business_type_label": BUSINESS_TYPE_LABELS.get(type_key, "Business"),
        "country_code": country_code.upper(),
        "income_group": income_group,
        "duration_hours": duration_hours,
        "probability": probability,
        "hourly_cost_usd": round(hourly_rate, 2),
        "direct_loss_usd": direct_loss,
        "expected_loss_usd": expected_loss,
        "monthly_risk_usd": monthly_risk,
        "using_custom_revenue": monthly_revenue_usd is not None,
        "recommendation": _recommendation(expected_loss, probability),
    }


async def get_area_impact(h3_index: str, country_code: str) -> dict:
    """Aggregate impact across all businesses registered in an H3 cell."""
    from app.core.database import AsyncSessionLocal
    from app.models.enterprise import BusinessProfile
    from app.services.duration_service import predict_duration
    from sqlalchemy import select

    duration_data = await predict_duration(h3_index, country_code)
    duration_hours = duration_data["median_minutes"] / 60

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(BusinessProfile).where(BusinessProfile.h3_index == h3_index)
        )
        profiles = result.scalars().all()

    if not profiles:
        # Generic area estimate — assume 5 shops + 2 restaurants + 1 office
        default_types = ["shop"] * 5 + ["restaurant"] * 2 + ["office"]
        total = sum(
            compute_impact(t, country_code, duration_hours, 0.70)["direct_loss_usd"]
            for t in default_types
        )
        return {
            "h3_index": h3_index,
            "registered_businesses": 0,
            "estimated_total_impact_usd": round(total, 2),
            "note": "Estimated from typical neighborhood business mix — register your business for a precise score",
            "duration_hours": duration_hours,
        }

    impacts = [
        compute_impact(p.business_type, country_code, duration_hours, 0.70, p.monthly_revenue_usd)
        for p in profiles
    ]
    total = sum(i["expected_loss_usd"] for i in impacts)

    return {
        "h3_index": h3_index,
        "registered_businesses": len(profiles),
        "estimated_total_impact_usd": round(total, 2),
        "duration_hours": duration_hours,
        "breakdown": impacts,
    }


def _recommendation(expected_loss: float, probability: float) -> str:
    if expected_loss >= 100 and probability >= 0.65:
        return "High financial risk — consider a UPS or generator. Estimated ROI in < 3 months."
    if expected_loss >= 30:
        return "Moderate risk — charge all devices and prepare backup power for critical equipment."
    return "Low financial impact expected — standard precautions recommended."
