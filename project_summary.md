# Housing Affordability Analysis for Hospital Workers
## Nor-Lea Hospital · Lovington, New Mexico
**Prepared for:** [Client Name]
**Date:** March 2026

---

## Overview

This project answers a practical question for hospital leadership and workforce planners:

> **For a registered nurse earning the median salary at Nor-Lea Hospital, which neighborhoods within a reasonable commute are actually affordable to rent in?**

The output is an interactive map showing every census tract within a 2-hour drive of the hospital, color-coded from dark green (very affordable) to red (not affordable), with drive-time rings marking the 10, 20, 30, 60, and 120-minute commute boundaries.

---

## Key Parameters & Assumptions

| Parameter | Value | Source / Rationale |
|---|---|---|
| Annual salary | $88,260 | Median RN salary used as the benchmark worker |
| Monthly income | $7,355 | Annual ÷ 12 |
| Affordability threshold | $2,207.50/mo | Standard 30%-of-income rule (HUD definition of "cost-burdened") |
| Hospital location | 32.9805° N, 103.3453° W | Nor-Lea Hospital, Lovington NM |
| Drive-time bands | 10, 20, 30, 60, 120 minutes | Represent realistic commute ranges from a rural hospital |
| Census data year | 2024 (2020–2024 ACS 5-year estimates) | Most recent available ACS 5-year release |
| Geographic scope | All New Mexico census tracts intersecting the 120-min drive boundary | Captures the full realistic commute shed |

**The 30% rule:** A household is considered "housing cost-burdened" when it spends more than 30% of gross income on rent. This is the standard definition used by HUD and most housing policy research. At a monthly income of $7,355, this means any rental unit above $2,207.50/month is considered unaffordable.

---

## Data Sources

### 1. Rent Data — U.S. Census Bureau ACS
- **Table:** B25064 — Median Gross Rent (all unit sizes combined)
- **Geography:** All census tracts in New Mexico
- **Accessed via:** Census Bureau API (`api.census.gov`)
- **Why this table:** B25064 reports a single median rent figure per tract regardless of bedroom size. Bedroom-specific tables (B25031) were initially considered but were found to have very high suppression rates in rural New Mexico — most tracts simply do not have enough rental units of each bedroom size for the Census to publish a reliable estimate. The all-units median provided substantially better coverage (543 of 612 NM tracts had data, vs. 222 with bedroom-specific data).

### 2. Census Tract Boundaries — U.S. Census Bureau TIGER/Line
- **File:** 2024 TIGER/Line Shapefiles, New Mexico census tracts
- **Accessed via:** Census FTP (`www2.census.gov/geo/tiger/TIGER2024/TRACT/`)
- **Format:** Shapefile, projected to WGS84 (EPSG:4326)

### 3. Drive-Time Isochrones — HERE Maps Isoline Routing API
- **Endpoint:** HERE Isoline Routing API v8
- **Transport mode:** Car (driving)
- **Routing mode:** Fast (fastest available route)
- **Why HERE Maps:** Selected for accuracy on rural New Mexico road networks. One API request was made per drive-time interval (5 total requests).

---

## Methodology

### Step 1: Rent Data Collection
The Census API was queried for variable `B25064_001E` (median gross rent) for all census tracts in New Mexico (state FIPS code 35). The Census returns this as raw JSON, which was parsed into a tabular format.

**Data cleaning applied:**
- The Census uses `-666,666,666` as a placeholder for suppressed or unavailable data. All values matching this sentinel were removed and treated as missing.
- Any remaining negative values were also removed.
- 543 of 612 New Mexico census tracts had usable rent data after cleaning.

### Step 2: Geographic Identifiers (GEOID Matching)
Census tract data comes from two separate sources — the API (rent data) and the TIGER shapefile (geographic boundaries) — which must be joined together using a shared identifier called a GEOID.

- The GEOID is an 11-character string: **2-digit state** + **3-digit county** + **6-digit tract**
- The API returns state, county, and tract as separate columns that must be concatenated, with zero-padding applied to ensure correct lengths
- This step is critical: even a single missing leading zero causes the join to fail silently, resulting in tracts appearing on the map with no data

### Step 3: Drive-Time Isochrones
Five drive-time polygons (isochrones) were generated using the HERE Maps API, centered on Nor-Lea Hospital's coordinates. Each polygon represents the full geographic area reachable by car within that time limit.

- Coordinates were passed in latitude/longitude order as required by the HERE API
- Polygon boundaries are returned in HERE's proprietary flexible polyline encoding format and were decoded to standard geographic coordinates

### Step 4: Spatial Join — Assigning Tracts to Drive-Time Bands
Each census tract was assigned to a drive-time band based on which isochrone polygon it intersects.

**Method used: intersection (not centroid)**
An earlier version used each tract's center point (centroid) to determine which ring it fell into. This was replaced with a full intersection approach because Lea County and surrounding areas contain several very large rural tracts where the geographic center sits far from the hospital even though the tract boundary overlaps a drive-time ring. Using intersection ensures these tracts are correctly included.

When a tract intersects multiple nested rings (e.g., a tract near the hospital falls inside both the 30-min and 60-min polygons), it is assigned to the **smallest** (innermost) ring.

Only tracts intersecting the 120-minute isochrone are shown on the map — 68 of New Mexico's 612 tracts.

### Step 5: Affordability Classification
Each tract's median rent was compared to the $2,207.50 threshold:
- **Affordable:** Median rent ≤ $2,207.50/month
- **Not affordable:** Median rent > $2,207.50/month
- **No data:** Census suppressed the estimate for this tract

### Step 6: Map Construction
The interactive map was built using the Folium library (Python wrapper for Leaflet.js). It renders as a standalone HTML file openable in any web browser.

---

## Key Findings

- **44 of 44 census tracts** with rent data within the 120-minute drive area are affordable for an RN at the median salary — **100% affordability rate**
- Within the immediate 10-minute drive, all 4 tracts with data are affordable
- The highest observed median rent within the 120-minute commute shed is well below the $2,207.50 threshold
- Rural southeastern New Mexico is, by this measure, an exceptionally affordable region for hospital workers relative to the RN salary

---

## Limitations & Caveats

**1. Median rent may not reflect available inventory.**
The ACS reports the median rent across all currently occupied rental units — not units actively on the market. In rural areas with low turnover, this may not reflect what a new employee would actually find available to rent.

**2. Data suppression in rural tracts.**
Some tracts — particularly those with small populations or very few rental units — have suppressed rent data. These appear as gray on the map. Suppression does not mean there is no housing; it means the sample size was too small for the Census to publish a reliable estimate.

**3. Drive times assume typical road conditions.**
Isochrones are based on standard driving speed estimates. Actual commute times may vary due to road conditions, weather, or time of day. Rural New Mexico roads may have seasonal variability not captured in the routing model.

**4. ACS 5-year estimates are averaged over 2020–2024.**
The rent figures reflect conditions across a 5-year window and may lag recent market changes. New Mexico has seen some rent increases in recent years that may not be fully reflected.

**5. Single salary benchmark.**
This analysis uses the median RN salary. Individual workers' salaries vary by experience, specialty, and employment type. The analysis does not account for household size, number of earners, or other housing costs (utilities, renters insurance).

**6. Affordable ≠ Available.**
A tract being classified as "affordable" means the median rent there is below the threshold. It does not indicate housing unit availability, quality, or suitability.

---

## Output

**File:** `nor_lea_affordability.html`
An interactive map that can be opened in any web browser. Features include:
- Census tracts colored on a gradient from dark green (lowest rent, most affordable) to red (highest rent, least affordable)
- Gray tracts indicate suppressed Census data
- Dashed rings showing 10, 20, 30, 60, and 120-minute drive-time boundaries
- Hover tooltips on each tract showing the median rent, affordability status, and drive time
- Toggleable layers for tract fills, tract boundaries, and county boundaries
- A color scale legend anchored to the $2,207.50 affordability threshold

---

*Analysis conducted using Python (geopandas, folium, pandas), U.S. Census Bureau ACS 5-year estimates, TIGER/Line shapefiles, and HERE Maps Isoline Routing API.*
