from __future__ import annotations

from pathlib import Path


# Project structure:
# TimeZone_Update/
# ├── data/
# ├── output/
# ├── scripts/
# │   └── config.py
# └── utility/
#     └── requirements.txt

# Temporary testing setting for environments with SSL interception / trust issues.
# Set to True once your local certificate chain is working correctly.
VERIFY_SSL = False

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
UTILITY_DIR = PROJECT_ROOT / "utility"
DATA_DIR = PROJECT_ROOT / "data"
OUT_DIR = PROJECT_ROOT / "output"

REQUIREMENTS_FILE = UTILITY_DIR / "requirements.txt"

DATA_DIR.mkdir(parents=True, exist_ok=True)
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Official external sources
CENSUS_COUNTIES_ZIP = (
    "https://www2.census.gov/geo/tiger/TIGER2025/COUNTY/tl_2025_us_county.zip"
)

BTS_TIMEZONES_SERVICE = (
    "https://services.arcgis.com/xOi1kZaI0eWDREZv/ArcGIS/rest/services/"
    "NTAD_Time_Zones/FeatureServer/0/query"
    "?where=1%3D1"
    "&outFields=*"
    "&returnGeometry=true"
    "&f=geojson"
)


# Raw extracted source directories
TIMEZONES_GEOJSON = DATA_DIR / "bts_timezones.geojson"

COUNTIES_DIR = DATA_DIR / "counties"
COUNTIES_DIR.mkdir(parents=True, exist_ok=True)


# Intermediate / output artifacts
COUNTIES_JOINED_GPKG = OUT_DIR / "county_timezones.gpkg"
COUNTIES_JOINED_LAYER = "county_timezones"

FINAL_ORIG_CSV = OUT_DIR / "tzstdst_state_year.csv"
FINAL_CSV = OUT_DIR / "tzstdst_county_year.csv"


# Minimal stable mapping from legal U.S. zone names to IANA representative zones.
# You may need to adjust the keys slightly after inspecting the BTS attribute values.
LEGAL_ZONE_TO_IANA = {
    "Eastern": "America/New_York",
    "Central": "America/Chicago",
    "Mountain": "America/Denver",
    "Pacific": "America/Los_Angeles",
    "Alaska": "America/Anchorage",
    "Hawaii-Aleutian": "Pacific/Honolulu",
    "Atlantic": "America/Puerto_Rico",
    "Samoa": "Pacific/Pago_Pago",
    "Chamorro": "Pacific/Guam",
}


# Labels to mimic the legacy schema as closely as possible
IANA_TO_LABELS = {
    "America/New_York": {
        "TZ": "EST",
        "TZN": "Eastern Standard Time (EST)",
    },
    "America/Chicago": {
        "TZ": "CST",
        "TZN": "Central Standard Time (CST)",
    },
    "America/Denver": {
        "TZ": "MST",
        "TZN": "Mountain Standard Time (MST)",
    },
    "America/Los_Angeles": {
        "TZ": "PST",
        "TZN": "Pacific Standard Time (PST)",
    },
    "America/Anchorage": {
        "TZ": "AKST",
        "TZN": "Alaska Standard Time (AKST)",
    },
    "Pacific/Honolulu": {
        "TZ": "HST",
        "TZN": "Hawaii-Aleutian Standard Time (HST)",
    },
    "America/Puerto_Rico": {
        "TZ": "AST",
        "TZN": "UTC-4: Atlantic Standard Time (AST)",
    },
    "Pacific/Pago_Pago": {
        "TZ": "SST",
        "TZN": "UTC-11: Samoa Standard Time",
    },
    "Pacific/Guam": {
        "TZ": "ChST",
        "TZN": "UTC+10: Chamorro Standard Time",
    },
}


# State / territory abbreviations by state FIPS code
STATEFP_TO_ABBR = {
    "01": "AL",
    "02": "AK",
    "04": "AZ",
    "05": "AR",
    "06": "CA",
    "08": "CO",
    "09": "CT",
    "10": "DE",
    "11": "DC",
    "12": "FL",
    "13": "GA",
    "15": "HI",
    "16": "ID",
    "17": "IL",
    "18": "IN",
    "19": "IA",
    "20": "KS",
    "21": "KY",
    "22": "LA",
    "23": "ME",
    "24": "MD",
    "25": "MA",
    "26": "MI",
    "27": "MN",
    "28": "MS",
    "29": "MO",
    "30": "MT",
    "31": "NE",
    "32": "NV",
    "33": "NH",
    "34": "NJ",
    "35": "NM",
    "36": "NY",
    "37": "NC",
    "38": "ND",
    "39": "OH",
    "40": "OK",
    "41": "OR",
    "42": "PA",
    "44": "RI",
    "45": "SC",
    "46": "SD",
    "47": "TN",
    "48": "TX",
    "49": "UT",
    "50": "VT",
    "51": "VA",
    "53": "WA",
    "54": "WV",
    "55": "WI",
    "56": "WY",
    "60": "AS",
    "66": "GU",
    "69": "MP",
    "72": "PR",
    "78": "VI",
}


STATE_ABBR_TO_NAME = {
    "AL": "Alabama",
    "AK": "Alaska",
    "AZ": "Arizona",
    "AR": "Arkansas",
    "AS": "American Samoa",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DC": "Washington, D.C.",
    "DE": "Delaware",
    "FL": "Florida",
    "GA": "Georgia",
    "GU": "Guam",
    "HI": "Hawaii",
    "IA": "Iowa",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "MA": "Massachusetts",
    "MD": "Maryland",
    "ME": "Maine",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MO": "Missouri",
    "MP": "Northern Mariana Islands",
    "MS": "Mississippi",
    "MT": "Montana",
    "NC": "North Carolina",
    "ND": "North Dakota",
    "NE": "Nebraska",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    "NV": "Nevada",
    "NY": "New York",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PA": "Pennsylvania",
    "PR": "Puerto Rico",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VA": "Virginia",
    "VI": "U.S. Virgin Islands",
    "VT": "Vermont",
    "WA": "Washington",
    "WI": "Wisconsin",
    "WV": "West Virginia",
    "WY": "Wyoming",
}
