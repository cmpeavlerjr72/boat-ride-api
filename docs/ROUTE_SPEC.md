<!-- path: boat-ride-api/docs/ROUTE_SPEC.md -->

# Route Spec (v1.0)

> Canonical route contract between:
> - boat-ride-mobile → boat-ride-api (RAW)
> - boat-ride-api → boat-ride (NORMALIZED)

## Version
- `route_version`: `"1.0"`

---

## RAW Route (Mobile → API)

### Format
GeoJSON **Feature** with **LineString** geometry.

### Coordinate order (LOCKED)
GeoJSON coordinates MUST be `[lon, lat]` in WGS84 (EPSG:4326).

### Minimal RAW shape
```json
{
  "route_version": "1.0",
  "type": "Feature",
  "geometry": { "type": "LineString", "coordinates": [[-81.0942, 31.9871], [-81.0837, 31.9929]] },
  "properties": { "name": "optional", "source": "mobile", "created_at_utc": "2026-02-03T22:15:03Z" }
}
