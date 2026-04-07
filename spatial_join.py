# ── spatial_join.py ──────────────────────────────────────────────────────────
# Spatially join census tracts to drive-time isochrone rings.

import geopandas as gpd
import pandas as pd


def join_tracts_to_isochrones(
    tracts_gdf: gpd.GeoDataFrame,
    isochrones_gdf: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    """
    Assign each census tract to the smallest drive-time ring it intersects.

    Strategy
    --------
    Uses intersection (not centroid-within) so that large rural tracts whose
    centroid sits outside a ring are still captured if any part of the tract
    overlaps that ring.

    Because isochrones are nested (30-min polygon fully contains 10-min polygon),
    a tract near the hospital will intersect all rings. Keeping the minimum
    drive_minutes per tract correctly assigns it to the innermost ring.
    """
    iso_cols = isochrones_gdf[["drive_minutes", "geometry"]].copy()

    # sjoin with 'intersects' — tract gets a row for every ring it touches
    joined = gpd.sjoin(
        tracts_gdf[["GEOID", "geometry"]],
        iso_cols,
        how="left",
        predicate="intersects",
    )

    # Keep only the smallest drive_minutes per tract
    joined = joined.sort_values("drive_minutes", ascending=True)
    joined = joined.drop_duplicates(subset="GEOID", keep="first")

    # Map drive_minutes back onto the original (full-column) tract GeoDataFrame
    result = tracts_gdf.copy()
    drive_time_map = joined.set_index("GEOID")["drive_minutes"]
    result["drive_minutes"] = result["GEOID"].map(drive_time_map)

    return result
