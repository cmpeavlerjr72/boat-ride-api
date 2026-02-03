# path: boat-ride-api/app/services/route_normalizer.py

from __future__ import annotations

from typing import List, Tuple
import hashlib
import json

from app.models.route_models import (
    RawRouteFeature,
    NormalizedRoute,
    NormalizedRouteBody,
    NormalizedPoint,
    BBoxWGS84,
)
from app.utils.geo import bbox_wgs84, polyline_length_m, haversine_m, bearing_deg_true


DEFAULT_SPACING_M = 250.0
MAX_POINTS = 2500
MIN_ROUTE_M = 25.0
MAX_ROUTE_M = 500_000.0
MAX_SEGMENT_M = 50_000.0


def stable_json_sha256(obj) -> str:
    data = json.dumps(obj, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return "sha256:" + hashlib.sha256(data).hexdigest()


def validate_route_guardrails(points_lonlat: List[Tuple[float, float]]) -> None:
    # De-dupe consecutive duplicates
    deduped = [points_lonlat[0]]
    for p in points_lonlat[1:]:
        if p != deduped[-1]:
            deduped.append(p)
    if len(deduped) < 2:
        raise ValueError("Route collapses to <2 unique points after de-dupe")

    # Segment sanity
    for i in range(1, len(deduped)):
        a_lon, a_lat = deduped[i - 1]
        b_lon, b_lat = deduped[i]
        seg = haversine_m(a_lon, a_lat, b_lon, b_lat)
        if seg <= 0:
            raise ValueError("Adjacent duplicate points not allowed")
        if seg > MAX_SEGMENT_M:
            raise ValueError(f"Segment too long (> {MAX_SEGMENT_M} m): {seg:.1f} m")

    total = polyline_length_m(deduped)
    if total < MIN_ROUTE_M:
        raise ValueError(f"Route too short (< {MIN_ROUTE_M} m): {total:.1f} m")
    if total > MAX_ROUTE_M:
        raise ValueError(f"Route too long (> {MAX_ROUTE_M} m): {total:.1f} m")


def pick_spacing_m(total_distance_m: float, requested_spacing_m: float | None = None) -> float:
    spacing = float(requested_spacing_m or DEFAULT_SPACING_M)
    # Increase spacing if point count would exceed MAX_POINTS
    if total_distance_m <= 0:
        return spacing
    est_points = int(total_distance_m // spacing) + 2
    if est_points <= MAX_POINTS:
        return spacing
    # Increase spacing to satisfy cap
    spacing = total_distance_m / max(2, (MAX_POINTS - 1))
    return float(spacing)


def resample_even_spacing(points_lonlat: List[Tuple[float, float]], spacing_m: float) -> List[Tuple[float, float, float, float]]:
    """
    Returns list of tuples: (lat, lon, seg_dist_m, cum_dist_m)
    """
    # Work in lon/lat list, generate cumulative distance along original polyline.
    # Simple linear interpolation along segments by distance.
    # (Swap to geodesic interpolation later if desired; contract stays same.)

    # Build segment lengths
    segs = []
    for i in range(1, len(points_lonlat)):
        a_lon, a_lat = points_lonlat[i - 1]
        b_lon, b_lat = points_lonlat[i]
        seg_len = haversine_m(a_lon, a_lat, b_lon, b_lat)
        segs.append((a_lon, a_lat, b_lon, b_lat, seg_len))

    total = sum(s[-1] for s in segs)
    if total == 0:
        raise ValueError("Route length is zero")

    # Target distances along route
    targets = [0.0]
    d = spacing_m
    while d < total:
        targets.append(d)
        d += spacing_m
    if targets[-1] != total:
        targets.append(total)

    out = []
    seg_idx = 0
    seg_start_cum = 0.0

    last_cum = 0.0
    for t in targets:
        while seg_idx < len(segs) and seg_start_cum + segs[seg_idx][-1] < t:
            seg_start_cum += segs[seg_idx][-1]
            seg_idx += 1
        if seg_idx >= len(segs):
            # Should only happen at end
            a_lon, a_lat, b_lon, b_lat, seg_len = segs[-1]
            lon, lat = b_lon, b_lat
        else:
            a_lon, a_lat, b_lon, b_lat, seg_len = segs[seg_idx]
            if seg_len == 0:
                lon, lat = b_lon, b_lat
            else:
                frac = (t - seg_start_cum) / seg_len
                lon = a_lon + frac * (b_lon - a_lon)
                lat = a_lat + frac * (b_lat - a_lat)

        seg_dist = 0.0 if not out else (t - last_cum)
        out.append((lat, lon, float(seg_dist), float(t)))
        last_cum = t

    return out


def normalize_raw_route(route_id: str, raw: RawRouteFeature, spacing_m: float | None = None) -> NormalizedRoute:
    points_lonlat = [(lon, lat) for (lon, lat) in raw.geometry.coordinates]

    validate_route_guardrails(points_lonlat)
    total = polyline_length_m(points_lonlat)
    spacing = pick_spacing_m(total, spacing_m)

    samples = resample_even_spacing(points_lonlat, spacing)

    # Bearings from consecutive normalized points (true degrees)
    bearings = []
    for i in range(len(samples) - 1):
        lat1, lon1, _, _ = samples[i]
        lat2, lon2, _, _ = samples[i + 1]
        bearings.append(bearing_deg_true(lon1, lat1, lon2, lat2))
    if bearings:
        bearings.append(bearings[-1])
    else:
        bearings.append(0.0)

    pts = []
    for i, (lat, lon, seg_dist_m, cum_dist_m) in enumerate(samples):
        pts.append(
            NormalizedPoint(
                i=i,
                lat=float(lat),
                lon=float(lon),
                seg_dist_m=float(seg_dist_m),
                cum_dist_m=float(cum_dist_m),
                bearing_deg_true=float(bearings[i]),
            )
        )

    bbox = bbox_wgs84([(p.lon, p.lat) for p in pts])
    body = NormalizedRouteBody(
        spacing_m=float(spacing),
        total_distance_m=float(pts[-1].cum_dist_m),
        point_count=len(pts),
        bbox_wgs84=BBoxWGS84(**bbox),
        points=pts,
    )

    # Hash raw with stable ordering (Feature dict form)
    raw_dict = raw.model_dump(mode="json")
    raw_hash = stable_json_sha256(raw_dict)

    return NormalizedRoute(
        route_id=route_id,
        normalized=body,
        source_raw_hash=raw_hash,
    )
