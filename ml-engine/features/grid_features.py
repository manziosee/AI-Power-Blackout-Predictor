import h3


COUNTRY_GRID_TYPE = {
    "RW": "hydro",
    "UG": "hydro",
    "ET": "hydro",
    "ZA": "coal",
    "NG": "gas",
    "GH": "gas",
    "FR": "nuclear",
    "DE": "mixed",
    "US": "mixed",
    "IN": "coal",
    "BR": "hydro",
}


def build_grid_features(h3_index: str, country_code: str) -> dict:
    """Encode grid-level and geographic features for an H3 cell."""
    center = h3.cell_to_latlng(h3_index)
    resolution = h3.get_resolution(h3_index)
    grid_type = COUNTRY_GRID_TYPE.get(country_code, "mixed")

    return {
        "h3_resolution": resolution,
        "center_lat": round(center[0], 5),
        "center_lng": round(center[1], 5),
        "grid_type_hydro": int(grid_type == "hydro"),
        "grid_type_coal": int(grid_type == "coal"),
        "grid_type_gas": int(grid_type == "gas"),
        "grid_type_nuclear": int(grid_type == "nuclear"),
        "grid_type_mixed": int(grid_type == "mixed"),
    }
