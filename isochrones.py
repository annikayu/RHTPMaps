# ── isochrones.py ────────────────────────────────────────────────────────────
# Fetch drive-time isochrone polygons from the HERE Maps Isoline Routing API.

import requests
import geopandas as gpd
from shapely.geometry import Polygon
import flexpolyline as fp

from config import HOSPITAL_LAT, HOSPITAL_LON, DRIVE_TIMES


HERE_ENDPOINT = "https://isoline.router.hereapi.com/v8/isolines"


def fetch_isochrones(here_api_key: str) -> gpd.GeoDataFrame:
    """
    Request one drive-time isochrone per DRIVE_TIMES entry from HERE Maps.

    HERE Isoline API uses lat,lon order for origin (correct order).
    Polygon rings are returned as HERE flexible-polyline encoded strings;
    decoded with the `flexpolyline` library into (lat, lon) tuples which are
    then swapped to (lon, lat) for Shapely.

    Returns a GeoDataFrame with columns: drive_minutes, geometry (EPSG:4326),
    sorted largest → smallest so map layers render correctly.
    """
    rows = []

    for minutes in DRIVE_TIMES:
        seconds = minutes * 60

        params = {
            "transportMode":  "car",
            "origin":         f"{HOSPITAL_LAT},{HOSPITAL_LON}",   # lat,lon
            "range[type]":    "time",
            "range[values]":  str(seconds),
            "routingMode":    "fast",
            "apikey":         here_api_key,
        }

        resp = requests.get(HERE_ENDPOINT, params=params, timeout=60)

        if not resp.ok:
            raise RuntimeError(
                f"HERE API error {resp.status_code} for {minutes}-min isochrone:\n"
                f"{resp.text}"
            )

        data = resp.json()

        # HERE response: data["isolines"][0]["polygons"] — list of ring objects
        # Each ring object has "outer": encoded flexible-polyline string
        polygons = data["isolines"][0]["polygons"]

        if len(polygons) > 1:
            # Multiple rings (disconnected areas) — take the largest by coord count
            rings = [fp.decode(p["outer"]) for p in polygons]
            coords_latlon = max(rings, key=len)
        else:
            coords_latlon = fp.decode(polygons[0]["outer"])

        # flexpolyline returns (lat, lon, [altitude]) tuples; Shapely needs (lon, lat)
        coords_lonlat = [(lon, lat) for lat, lon, *_ in coords_latlon]

        rows.append({
            "drive_minutes": minutes,
            "geometry":      Polygon(coords_lonlat),
        })

    gdf = gpd.GeoDataFrame(rows, crs="EPSG:4326")

    # Sort descending so the 30-min ring is drawn before the 10-min ring
    gdf = gdf.sort_values("drive_minutes", ascending=False).reset_index(drop=True)

    return gdf
