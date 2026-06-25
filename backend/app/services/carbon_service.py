"""Carbon impact estimation for power outages."""

# kg CO₂ per kWh (Sub-Saharan Africa grid average, IEA 2023)
_CO2_KG_PER_KWH = 0.884

# Approximate MW load per H3 resolution-9 cell at typical urban density
_DEFAULT_LOAD_MW_PER_CELL = 0.5


def estimate_impact(
    affected_cells: int,
    duration_hours: float,
    load_mw_per_cell: float = _DEFAULT_LOAD_MW_PER_CELL,
) -> dict:
    """Estimate CO₂ avoided (outage = no consumption) and kWh lost."""
    kwh_lost = affected_cells * load_mw_per_cell * 1_000 * duration_hours
    co2_kg = kwh_lost * _CO2_KG_PER_KWH
    return {
        "affected_cells": affected_cells,
        "duration_hours": duration_hours,
        "kwh_lost": round(kwh_lost, 2),
        "co2_kg_avoided": round(co2_kg, 2),
        "co2_tonnes_avoided": round(co2_kg / 1_000, 4),
        "load_mw_per_cell": load_mw_per_cell,
    }


def estimate_from_reports(
    outage_reports: list[dict],
    duration_hours: float = 2.0,
) -> dict:
    """Aggregate carbon impact from a list of outage report dicts."""
    h3_cells = {r.get("h3_index") for r in outage_reports if r.get("h3_index")}
    return estimate_impact(len(h3_cells), duration_hours)
