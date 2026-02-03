# path: boat-ride-api/app/utils/geo.py

from __future__ import annotations

from typing import Iterable, List, Tuple, Dict
import math


def bbox_wgs84(points_lonlat: Iterable[Tuple[float, float]]) -> Dict[str, float]:
    lons = [p[0] for p in points_lonlat]
    lats = [p[1] for p in points_lonlat]
    return {
        "min_lat": min(lats),
        "min_lon": min(lons),
        "max_lat": max(lats),
        "max_lon": max(lons),
    }


def haversine_m(a_lon: float, a_lat: float, b_lon: float, b_lat: float) -> float:
    # Good enough for validation guardrails; you can swap to pyproj/GeographicLib later.
    r = 6371000.0
    phi1 = math.radians(a_lat)
    phi2 = math.radians(b_lat)
    dphi = math.radians(b_lat - a_lat)
    dlmb = math.radians(b_lon - a_lon)

    s = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(s))


def bearing_deg_true(a_lon: float, a_lat: float, b_lon: float, b_lat: float) -> float:
    # Initial bearing (forward azimuth), degrees true, [0,360)
    phi1 = math.radians(a_lat)
    phi2 = math.radians(b_lat)
    dlmb = math.radians(b_lon - a_lon)

    y = math.sin(dlmb) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlmb)
    brng = math.degrees(math.atan2(y, x))
    return (brng + 360.0) % 360.0


def polyline_length_m(points_lonlat: List[Tuple[float, float]]) -> float:
    total = 0.0
    for i in range(1, len(points_lonlat)):
        a_lon, a_lat = points_lonlat[i - 1]
        b_lon, b_lat = points_lonlat[i]
        total += haversine_m(a_lon, a_lat, b_lon, b_lat)
    return total
