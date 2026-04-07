# ── fetch_census.py ───────────────────────────────────────────────────────────

import io
import requests
import pandas as pd
import geopandas as gpd

from config import (
    CENSUS_YEAR, STATE_FIPS_LIST, ACS_VARS, RENT_COLS,
    CENSUS_NULL, AFFORD_THRESHOLD, CNA_AFFORD_THRESHOLD, TIGER_URLS,
)

SQ_METERS_PER_SQ_MILE = 2_589_988.0


def fetch_acs_data(census_api_key: str) -> pd.DataFrame:
    base_url  = f"https://api.census.gov/data/{CENSUS_YEAR}/acs/acs5"
    acs_codes = ["NAME"] + list(ACS_VARS.keys())
    frames    = []

    for state_fips in STATE_FIPS_LIST:
        params = {
            "get": ",".join(acs_codes),
            "for": "tract:*",
            "in":  f"state:{state_fips}",
            "key": census_api_key,
        }
        resp = requests.get(base_url, params=params, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        frames.append(pd.DataFrame(data[1:], columns=data[0]))

    df = pd.concat(frames, ignore_index=True).rename(columns=ACS_VARS)

    df["GEOID"] = (
        df["state"].str.zfill(2)
        + df["county"].str.zfill(3)
        + df["tract"].str.zfill(6)
    )

    for col in RENT_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce")
        df[col] = df[col].where(
            (df[col] != CENSUS_NULL) & (df[col] >= 0), other=None
        )

    # Vacancy rate
    df["vacancy_rate"] = (df["vacant_units"] / df["total_units_vac"] * 100).where(
        df["total_units_vac"] > 0
    )

    # % renters cost-burdened (≥30%)
    burden = (
        df["burden_30_34"].fillna(0) + df["burden_35_39"].fillna(0)
        + df["burden_40_49"].fillna(0) + df["burden_50plus"].fillna(0)
    )
    df["cost_burdened_pct"] = (burden / df["renters_computed"] * 100).where(
        df["renters_computed"] > 0
    )
    df.loc[df["renters_computed"].isna() | (df["renters_computed"] == 0),
           "cost_burdened_pct"] = None

    keep = ["GEOID", "NAME"] + RENT_COLS + ["vacancy_rate", "cost_burdened_pct"]
    return df[keep].reset_index(drop=True)


def fetch_tract_shapefiles() -> gpd.GeoDataFrame:
    gdfs = []
    for state_fips, url in TIGER_URLS.items():
        resp = requests.get(url, timeout=180)
        resp.raise_for_status()
        gdf = gpd.read_file(io.BytesIO(resp.content))
        gdf["GEOID"] = gdf["GEOID"].astype(str)
        if gdf.crs is None or gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs(epsg=4326)
        gdfs.append(gdf)

    combined = gpd.GeoDataFrame(pd.concat(gdfs, ignore_index=True), crs="EPSG:4326")
    combined["ALAND_SQMI"] = combined["ALAND"].astype(float) / SQ_METERS_PER_SQ_MILE
    return combined


def add_density_columns(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    valid = gdf["ALAND_SQMI"] > 0
    gdf["pop_density"]     = (gdf["population"]    / gdf["ALAND_SQMI"]).where(valid)
    gdf["housing_density"] = (gdf["housing_units"] / gdf["ALAND_SQMI"]).where(valid)
    return gdf


def build_affordability_flags(df: pd.DataFrame) -> pd.DataFrame:
    """Add RN and CNA affordability columns."""
    df["rn_affordable"] = df["median_rent"].apply(
        lambda r: (r <= AFFORD_THRESHOLD) if pd.notna(r) else None
    )
    df["cna_affordable"] = df["median_rent"].apply(
        lambda r: (r <= CNA_AFFORD_THRESHOLD) if pd.notna(r) else None
    )
    return df
