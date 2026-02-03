

### 2) Pydantic models: RAW + NORMALIZED (the contract in code)

# path: boat-ride-api/app/models/route_models.py

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Tuple
from pydantic import BaseModel, Field, field_validator, model_validator


RouteVersion = Literal["1.0"]


class RawRouteGeometry(BaseModel):
    type: Literal["LineString"]
    coordinates: List[Tuple[float, float]]  # (lon, lat)

    @field_validator("coordinates")
    @classmethod
    def validate_coords(cls, coords: List[Tuple[float, float]]):
        if len(coords) < 2:
            raise ValueError("LineString must contain at least 2 coordinates")
        for lon, lat in coords:
            if not (-180.0 <= lon <= 180.0):
                raise ValueError(f"lon out of range [-180,180]: {lon}")
            if not (-90.0 <= lat <= 90.0):
                raise ValueError(f"lat out of range [-90,90]: {lat}")
        return coords


class RawRouteProperties(BaseModel):
    name: Optional[str] = Field(default=None, max_length=80)
    source: Optional[str] = Field(default="mobile")
    created_at_utc: Optional[datetime] = None
    notes: Optional[str] = None
    client: Optional[Dict[str, Any]] = None


class RawRouteFeature(BaseModel):
    route_version: RouteVersion = "1.0"
    type: Literal["Feature"]
    geometry: RawRouteGeometry
    properties: RawRouteProperties = Field(default_factory=RawRouteProperties)

    @model_validator(mode="after")
    def dedupe_consecutive_points(self):
        # NOTE: validation-only spec says API SHOULD de-dupe consecutive duplicates on ingest.
        # This model doesn't mutate by default, but we keep this hook in case you later want to.
        return self


class NormalizedPoint(BaseModel):
    i: int = Field(ge=0)
    lat: float
    lon: float
    cum_dist_m: float = Field(ge=0)
    seg_dist_m: float = Field(ge=0)
    bearing_deg_true: float = Field(ge=0, lt=360)


class BBoxWGS84(BaseModel):
    min_lat: float
    min_lon: float
    max_lat: float
    max_lon: float


class NormalizedRouteBody(BaseModel):
    spacing_m: float = Field(gt=0)
    total_distance_m: float = Field(ge=0)
    point_count: int = Field(ge=2)
    bbox_wgs84: BBoxWGS84
    points: List[NormalizedPoint]

    @model_validator(mode="after")
    def validate_point_count(self):
        if self.point_count != len(self.points):
            raise ValueError("point_count must equal len(points)")
        if len(self.points) < 2:
            raise ValueError("Normalized route must have at least 2 points")
        # Ensure indexes are contiguous starting at 0
        for idx, p in enumerate(self.points):
            if p.i != idx:
                raise ValueError("Normalized points must have contiguous i starting at 0")
        return self


class NormalizedRoute(BaseModel):
    route_version: RouteVersion = "1.0"
    route_id: str
    normalized: NormalizedRouteBody
    source_raw_hash: Optional[str] = None
    created_at_utc: datetime = Field(default_factory=lambda: datetime.utcnow())
