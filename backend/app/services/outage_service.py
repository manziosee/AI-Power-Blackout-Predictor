import h3


def resolve_h3_from_coords(lat: float, lng: float, resolution: int = 8) -> str:
    return h3.latlng_to_cell(lat, lng, resolution)


def classify_risk(probability: float) -> str:
    if probability >= 0.85:
        return "critical"
    if probability >= 0.65:
        return "high"
    if probability >= 0.40:
        return "medium"
    return "low"
