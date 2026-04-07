# ── main.py ───────────────────────────────────────────────────────────────────
# Orchestrates all steps end-to-end for the Nor-Lea Housing Needs Map.

import os
import sys
from dotenv import load_dotenv

from config import DRIVE_TIMES, AFFORD_THRESHOLD, CNA_AFFORD_THRESHOLD, STATE_FIPS, COUNTY_FIPS
from fetch_census  import (fetch_acs_data, fetch_tract_shapefiles,
                            add_density_columns, build_affordability_flags)
from isochrones    import fetch_isochrones
from spatial_join  import join_tracts_to_isochrones
from map           import build_map


def main():
    # ── 0. Load API keys ──────────────────────────────────────────────────────
    load_dotenv()
    census_key = os.getenv("CENSUS_API_KEY")
    here_key   = os.getenv("HERE_API_KEY")

    if not census_key or census_key == "your_census_api_key_here":
        sys.exit("ERROR: CENSUS_API_KEY not set in .env")
    if not here_key or here_key == "your_here_api_key_here":
        sys.exit("ERROR: HERE_API_KEY not set in .env")

    # ── 1. ACS data (rent + population + housing + vacancy + cost burden) ─────
    print("▶ Fetching ACS 5-year data (NM + TX) …")
    acs_df = fetch_acs_data(census_key)
    acs_df = build_affordability_flags(acs_df)
    has_rent = acs_df["median_rent"].notna().sum()
    print(f"  {len(acs_df):,} tracts retrieved, {has_rent:,} with rent data.")

    # ── 2. TIGER/Line shapefiles (NM + TX) ───────────────────────────────────
    print("▶ Downloading TIGER/Line shapefiles (NM + TX) …")
    tracts_gdf = fetch_tract_shapefiles()
    print(f"  {len(tracts_gdf):,} tract geometries loaded.")

    # ── 3. Merge ACS data onto tract geometries ───────────────────────────────
    print("▶ Merging ACS data onto tract geometries …")
    merged_gdf = tracts_gdf.merge(acs_df, on="GEOID", how="left")
    merged_gdf = add_density_columns(merged_gdf)
    matched = merged_gdf["median_rent"].notna().sum()
    print(f"  {matched:,} tracts matched with rent data.")

    # ── 4. Isochrones ─────────────────────────────────────────────────────────
    print("▶ Fetching drive-time isochrones from HERE Maps …")
    isochrones_gdf = fetch_isochrones(here_key)
    print(f"  Isochrones: {sorted(isochrones_gdf['drive_minutes'].tolist())} minutes")

    # ── 5. Spatial join ───────────────────────────────────────────────────────
    print("▶ Joining tracts to isochrone rings …")
    joined_gdf = join_tracts_to_isochrones(merged_gdf, isochrones_gdf)
    within_120 = joined_gdf[joined_gdf["drive_minutes"].notna()]
    print(f"  {len(within_120):,} tracts (NM + TX) intersect the 120-min isochrone.")

    # ── 6. Build map ──────────────────────────────────────────────────────────
    print("▶ Building interactive folium map …")
    build_map(joined_gdf, isochrones_gdf)

    # ── 7. Summary ────────────────────────────────────────────────────────────
    print()
    print("=" * 62)
    print("  HOUSING NEEDS SUMMARY — Nor-Lea Hospital, Lovington NM")
    print(f"  RN salary ${88_260:,}/yr · threshold ${AFFORD_THRESHOLD:,.2f}/mo")
    print("=" * 62)

    for minutes in sorted(DRIVE_TIMES):
        band      = joined_gdf[joined_gdf["drive_minutes"] == minutes]
        has_rent  = band["median_rent"].notna().sum()
        rn_aff    = band["rn_affordable"].eq(True).sum()
        cna_aff   = band["cna_affordable"].eq(True).sum()
        rn_pct    = (rn_aff  / has_rent * 100) if has_rent else 0
        cna_pct   = (cna_aff / has_rent * 100) if has_rent else 0
        avg_vac   = band["vacancy_rate"].mean()
        avg_bur   = band["cost_burdened_pct"].mean()
        print(
            f"\n  ── Within {minutes}-min drive ({len(band)} tracts) ──\n"
            f"    RN affordable  (≤$2,208/mo): {rn_aff}/{has_rent} ({rn_pct:.0f}%)\n"
            f"    CNA affordable (≤$950/mo):   {cna_aff}/{has_rent} ({cna_pct:.0f}%)\n"
            f"    Avg vacancy rate:  {avg_vac:.1f}%   "
            f"Avg cost-burdened: {avg_bur:.1f}%"
        )

    lea_prefix = STATE_FIPS + COUNTY_FIPS
    lea = joined_gdf[joined_gdf["GEOID"].str.startswith(lea_prefix)]
    lea_has     = lea["median_rent"].notna().sum()
    lea_rn_aff  = lea["rn_affordable"].eq(True).sum()
    lea_cna_aff = lea["cna_affordable"].eq(True).sum()
    if lea_has:
        print(
            f"\n  ── Lea County ({len(lea)} tracts) ──\n"
            f"    RN affordable:  {lea_rn_aff}/{lea_has} ({lea_rn_aff/lea_has*100:.0f}%)\n"
            f"    CNA affordable: {lea_cna_aff}/{lea_has} ({lea_cna_aff/lea_has*100:.0f}%)"
        )

    print()
    print("  Done. Open nor_lea_affordability.html in any browser.")
    print("=" * 62)


if __name__ == "__main__":
    main()
