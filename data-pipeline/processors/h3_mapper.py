"""Map lat/lng coordinates to H3 cells and upsert into h3_cells table."""
import os

import h3
import sqlalchemy as sa

DATABASE_URL = os.getenv("SYNC_DATABASE_URL", "postgresql://postgres:password@localhost:5432/blackout_predictor")
engine = sa.create_engine(DATABASE_URL)


def register_cell(lat: float, lng: float, country_code: str, city: str = "", resolution: int = 8) -> str:
    h3_index = h3.latlng_to_cell(lat, lng, resolution)
    center = h3.cell_to_latlng(h3_index)

    with engine.begin() as conn:
        conn.execute(
            sa.text("""
                INSERT INTO h3_cells (h3_index, center_lat, center_lng, country_code, city, resolution)
                VALUES (:h3, :lat, :lng, :cc, :city, :res)
                ON CONFLICT (h3_index) DO NOTHING
            """),
            {"h3": h3_index, "lat": center[0], "lng": center[1], "cc": country_code, "city": city, "res": resolution},
        )
    return h3_index


def seed_country(country_code: str, center_lat: float, center_lng: float, radius_km: float = 50) -> int:
    """Seed H3 cells around a city center for a given country."""
    center_cell = h3.latlng_to_cell(center_lat, center_lng, 8)
    ring_size = max(1, int(radius_km / 1.2))
    cells = h3.grid_disk(center_cell, ring_size)

    count = 0
    for cell in cells:
        lat, lng = h3.cell_to_latlng(cell)
        register_cell(lat, lng, country_code, resolution=8)
        count += 1
    return count


CITY_SEEDS = [
    ("RW", -1.9441, 30.0619, "Kigali", 30),
    ("KE", -1.2921, 36.8219, "Nairobi", 40),
    ("UG", 0.3476, 32.5825, "Kampala", 30),
    ("NG", 6.5244, 3.3792, "Lagos", 50),
    ("GH", 5.6037, -0.1870, "Accra", 30),
    ("ZA", -26.2041, 28.0473, "Johannesburg", 50),
    ("FR", 48.8566, 2.3522, "Paris", 40),
    ("DE", 52.5200, 13.4050, "Berlin", 40),
    ("GB", 51.5074, -0.1278, "London", 40),
    ("US", 40.7128, -74.0060, "New York", 50),
    ("BR", -23.5505, -46.6333, "São Paulo", 50),
    ("IN", 28.6139, 77.2090, "Delhi", 50),
]

if __name__ == "__main__":
    total = 0
    for cc, lat, lng, city, radius in CITY_SEEDS:
        n = seed_country(cc, lat, lng, radius)
        print(f"Seeded {n} cells for {city} ({cc})")
        total += n
    print(f"Total: {total} H3 cells")
