# path: boat-ride-api/app/api/routes/routes.py

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import uuid

from app.models.route_models import RawRouteFeature, NormalizedRoute
from app.services.route_normalizer import normalize_raw_route

router = APIRouter(prefix="/routes", tags=["routes"])


class CreateRouteResponse(BaseModel):
    route_id: str
    normalized: NormalizedRoute


@router.post("", response_model=CreateRouteResponse)
def create_route(raw: RawRouteFeature) -> CreateRouteResponse:
    # Step 1 scope: contract + normalization only (no DB/auth).
    route_id = str(uuid.uuid4())
    try:
        normalized = normalize_raw_route(route_id=route_id, raw=raw)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return CreateRouteResponse(route_id=route_id, normalized=normalized)
