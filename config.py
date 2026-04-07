# ── config.py ────────────────────────────────────────────────────────────────
# All constants and parameters for the Nor-Lea Hospital Housing Needs Map.

# ── Salary / Affordability — RN ──────────────────────────────────────────────
SALARY_ANNUAL    = 88_260
MONTHLY_INCOME   = SALARY_ANNUAL / 12
AFFORD_THRESHOLD = MONTHLY_INCOME * 0.30     # ~$2,207.50/mo

# ── Salary / Affordability — CNA ─────────────────────────────────────────────
CNA_SALARY_ANNUAL    = 38_000
CNA_MONTHLY_INCOME   = CNA_SALARY_ANNUAL / 12
CNA_AFFORD_THRESHOLD = CNA_MONTHLY_INCOME * 0.30    # ~$950.00/mo

# ── Hospital ─────────────────────────────────────────────────────────────────
HOSPITAL_NAME = "Nor-Lea Hospital"
HOSPITAL_LAT  = 32.98049203086512
HOSPITAL_LON  = -103.34531372633968

# ── Drive-time bands (minutes) ───────────────────────────────────────────────
DRIVE_TIMES = [10, 20, 30, 60, 120]

# ── Census ───────────────────────────────────────────────────────────────────
CENSUS_YEAR     = 2024
STATE_FIPS_LIST = ["35", "48"]   # New Mexico, Texas
STATE_FIPS      = "35"
COUNTY_FIPS     = "025"          # Lea County
CENSUS_NULL     = -666_666_666

# ── ACS variables ─────────────────────────────────────────────────────────────
ACS_VARS = {
    "B25064_001E": "median_rent",
    "B01003_001E": "population",
    "B25001_001E": "housing_units",
    "B25002_001E": "total_units_vac",
    "B25002_003E": "vacant_units",
    "B25070_001E": "renters_computed",
    "B25070_007E": "burden_30_34",
    "B25070_008E": "burden_35_39",
    "B25070_009E": "burden_40_49",
    "B25070_010E": "burden_50plus",
}
RENT_COLS = list(ACS_VARS.values())

# ── TIGER/Line shapefile URLs ─────────────────────────────────────────────────
TIGER_URLS = {
    "35": "https://www2.census.gov/geo/tiger/TIGER2024/TRACT/tl_2024_35_tract.zip",
    "48": "https://www2.census.gov/geo/tiger/TIGER2024/TRACT/tl_2024_48_tract.zip",
}

# ── Map color gradients ───────────────────────────────────────────────────────
COLOR_NO_DATA = "#d9d9d9"

# Rent affordability: dark green (cheap) → light green → yellow → red
RENT_GRADIENT = ["#1b4332", "#52b788", "#b7e4c7", "#f9c74f", "#d62828"]

# Vacancy rate: white → steel blue (higher vacancy = more available)
VACANCY_GRADIENT = ["#f7fbff", "#6baed6", "#08519c"]

# % cost-burdened: white → orange → dark red
BURDEN_GRADIENT = ["#fff5eb", "#fd8d3c", "#7f2704"]

# Population density: white → dark purple
POP_DENSITY_GRADIENT = ["#fcfbfd", "#9e9ac8", "#3f007d"]

# Housing unit density: white → dark teal
HOUSING_DENSITY_GRADIENT = ["#f7fcfd", "#41b6c4", "#0c2c84"]

# ── Isochrone ring colors ─────────────────────────────────────────────────────
RING_COLORS = {
    10:  "#c0392b",
    20:  "#e67e22",
    30:  "#f1c40f",
    60:  "#27ae60",
    120: "#2980b9",
}

# ── Output ────────────────────────────────────────────────────────────────────
OUTPUT_HTML = "nor_lea_affordability.html"
