"""
Static catalog of major world cities available for weather tracking.

This is a curated list — not a database table — because the set of available
cities doesn't change at runtime. The user picks from this list to add favorites.

Each entry has a location_key computed as "{latitude},{longitude}", matching
the convention used across all database tables.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class CatalogCity:
    name: str
    country: str
    latitude: float
    longitude: float

    @property
    def location_key(self) -> str:
        return f"{self.latitude},{self.longitude}"


# Major world cities — geographically and culturally diverse selection.
# Coordinates are rounded to 4 decimal places for clean location_key strings.
CATALOG: list[CatalogCity] = [
    # North America
    CatalogCity("New York", "United States", 40.7128, -74.006),
    CatalogCity("Los Angeles", "United States", 34.0522, -118.2437),
    CatalogCity("Chicago", "United States", 41.8781, -87.6298),
    CatalogCity("Houston", "United States", 29.7604, -95.3698),
    CatalogCity("Miami", "United States", 25.7617, -80.1918),
    CatalogCity("Seattle", "United States", 47.6062, -122.3321),
    CatalogCity("Denver", "United States", 39.7392, -104.9903),
    CatalogCity("Toronto", "Canada", 43.6532, -79.3832),
    CatalogCity("Vancouver", "Canada", 49.2827, -123.1207),
    CatalogCity("Mexico City", "Mexico", 19.4326, -99.1332),
    # South America
    CatalogCity("São Paulo", "Brazil", -23.5505, -46.6333),
    CatalogCity("Rio de Janeiro", "Brazil", -22.9068, -43.1729),
    CatalogCity("Buenos Aires", "Argentina", -34.6037, -58.3816),
    CatalogCity("Bogotá", "Colombia", 4.711, -74.0721),
    CatalogCity("Lima", "Peru", -12.0464, -77.0428),
    # Europe
    CatalogCity("London", "United Kingdom", 51.5074, -0.1278),
    CatalogCity("Paris", "France", 48.8566, 2.3522),
    CatalogCity("Berlin", "Germany", 52.52, 13.405),
    CatalogCity("Madrid", "Spain", 40.4168, -3.7038),
    CatalogCity("Rome", "Italy", 41.9028, 12.4964),
    CatalogCity("Amsterdam", "Netherlands", 52.3676, 4.9041),
    CatalogCity("Stockholm", "Sweden", 59.3293, 18.0686),
    CatalogCity("Zurich", "Switzerland", 47.3769, 8.5417),
    CatalogCity("Istanbul", "Turkey", 41.0082, 28.9784),
    CatalogCity("Moscow", "Russia", 55.7558, 37.6173),
    # Africa & Middle East
    CatalogCity("Cairo", "Egypt", 30.0444, 31.2357),
    CatalogCity("Lagos", "Nigeria", 6.5244, 3.3792),
    CatalogCity("Johannesburg", "South Africa", -26.2041, 28.0473),
    CatalogCity("Nairobi", "Kenya", -1.2921, 36.8219),
    CatalogCity("Dubai", "UAE", 25.2048, 55.2708),
    # Asia & Pacific
    CatalogCity("Tokyo", "Japan", 35.6762, 139.6503),
    CatalogCity("Seoul", "South Korea", 37.5665, 126.978),
    CatalogCity("Beijing", "China", 39.9042, 116.4074),
    CatalogCity("Shanghai", "China", 31.2304, 121.4737),
    CatalogCity("Mumbai", "India", 19.076, 72.8777),
    CatalogCity("Delhi", "India", 28.7041, 77.1025),
    CatalogCity("Singapore", "Singapore", 1.3521, 103.8198),
    CatalogCity("Bangkok", "Thailand", 13.7563, 100.5018),
    CatalogCity("Hong Kong", "China", 22.3193, 114.1694),
    CatalogCity("Sydney", "Australia", -33.8688, 151.2093),
    CatalogCity("Melbourne", "Australia", -37.8136, 144.9631),
]

# Index by location_key for fast lookups
CATALOG_BY_KEY: dict[str, CatalogCity] = {city.location_key: city for city in CATALOG}


def get_city(location_key: str) -> CatalogCity | None:
    """Look up a catalog city by location_key. Returns None if not found."""
    return CATALOG_BY_KEY.get(location_key)
