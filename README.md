# TimeZone_Update

## Overview

This project builds a **county-level U.S. time zone dataset** using authoritative external data sources and expands it into a **yearly time zone table** similar to the legacy `tzstdst` schema.

The pipeline is fully automated and designed to:

- avoid manual maintenance of county lists
- rely on official government data sources
- generate reproducible results
- support both county-level accuracy and state-level derivations

---

## Project Structure
```text
TimeZone_Update/
├── data/
├── output/
├── scripts/
│   ├── config.py
│   ├── debug.py
│   ├── _00_run_all.py
│   ├── _01_install_requirements.py
│   ├── _02_fetch_geography.py
│   ├── _03_build_tz_table.py
│   ├── _04_compare_orig.py
│   └── _99_start_over.py
└── utility/
    └── requirements.txt
```

---

## External Data Sources

### 1. U.S. Census TIGER/Line Counties

Source: U.S. Census Bureau  
URL: https://www2.census.gov/geo/tiger/TIGER2025/COUNTY/tl_2025_us_county.zip  

Purpose:
- Provides authoritative county and county-equivalent boundaries
- Used as the base geographic unit

Fields used:
- STATEFP
- COUNTYFP
- GEOID
- NAME / NAMELSAD
- geometry

---

### 2. BTS NTAD Time Zone Boundaries

Source: Bureau of Transportation Statistics (NTAD)  
Accessed via ArcGIS REST API  

Purpose:
- Provides legal U.S. time zone boundaries
- Defines which counties belong to which time zone

Fields used:
- zone → normalized to LegalZoneName
- utc (informational)

---

### 3. IANA Time Zone Database (via Python)

Accessed through Python's `zoneinfo` module and `tzdata` package

Purpose:
- Defines DST rules and UTC offsets
- Used to compute:
  - DST start/end dates
  - standard and daylight offsets

---

## Execution Flow

Entry Point:
_00_run_all.py

Execution Order:
1. _01_install_requirements.py
2. _02_fetch_geography.py
3. _03_build_tz_table.py
4. _04_compare_orig.py

---

## Script Descriptions

### _99_start_over.py

Purpose:
- Resets the environment for testing

Actions:
- Deletes all files in:
  - /data
  - /output
- Uninstalls project dependencies (optional)

Use case:
- Full end-to-end validation
- Clean environment testing

---

### _01_install_requirements.py

Purpose:
- Installs dependencies from utility/requirements.txt

Key behavior:
- Uses pip via subprocess
- Ensures required libraries are present

Dependencies installed:
- pandas
- geopandas
- requests
- shapely
- pyogrio
- pyproj
- tzdata
- fiona
- psutil
- datacompy

---

### _02_fetch_geography.py

Purpose:
- Builds the county-to-time-zone reference dataset

Steps:
1. Downloads Census county shapefile
2. Downloads BTS time zone boundaries (GeoJSON)
3. Normalizes time zone names
4. Maps legal zones → IANA zones
5. Spatially joins counties to time zones

Output artifact:
output/county_timezones.gpkg

Key columns created:

- TZState: State abbreviation  
- CountyFIPS: County identifier  
- CountyName: County name  
- LegalZoneName: Legal time zone  
- IanaZone: IANA time zone  

---

### _03_build_tz_table.py

Purpose:
- Generates yearly time zone data from IANA rules

Steps:
1. Reads county_timezones.gpkg
2. Iterates over counties and years
3. Uses zoneinfo to compute:
   - UTC offsets
   - DST rules
4. Formats output to match legacy schema
5. Rolls the county-level rows up to one row per state and year
   (the most common zone is primary; other zone labels go to TZN2 / TSN3)

Options:
- --start-year (default 2025)
- --end-year (default: current year)

Output artifacts:
- output/tzstdst_county_year.csv
- output/tzstdst_state_year.csv

---

### _04_compare_orig.py

Purpose:
- Compares the legacy data/tzstdst_orig.csv with the newly generated
  output/tzstdst_state_year.csv using DataComPy

Key behavior:
- Filters the original to the years present in the new file
- Joins on TZState + Year

Output artifacts:
- output/tzstdst_compare_report.txt
- output/tzstdst_compare_row_diffs.csv
- output/tzstdst_compare_column_diffs.csv

---

### _00_run_all.py

Purpose:
- Orchestrates the full pipeline

Steps executed:
1. Install dependencies
2. Fetch geography
3. Build time zone tables
4. Compare against the original

Use case:
- Single-click execution (VS Code GUI)
- Production entry point

---

### debug.py

Purpose:
- Scratch script that prints the Florida county rows from the county-level output

---

## Data Dictionary (Final Output)

File:
output/tzstdst_county_year.csv

Granularity:
County + Year

(output/tzstdst_state_year.csv has the same columns minus
IanaZone, LegalZoneName, CountyFIPS and CountyName, at State + Year granularity.)

Columns:

- TZState: State abbreviation  
- StateName: Full state name  
- CountyFIPS: County identifier  
- CountyName: County name  
- IanaZone: IANA time zone (e.g., America/New_York)  
- LegalZoneName: U.S. legal time zone  
- TZ: Standard time abbreviation  
- ADJHRS: Standard UTC offset (hours)  
- ADJHRSDST: DST UTC offset (hours)  
- DST: Y/N flag for DST  
- TZN: Descriptive time zone label  
- TZN2: (Reserved)  
- TSN3: (Reserved)  
- stdatedt: DST start datetime  
- endatedt: DST end datetime  
- Year: Year of record  
- tzStart: Human-readable DST start  
- tzEnd: Human-readable DST end  
- tstdate: DST start (YYYYMMDD)  
- tendate: DST end (YYYYMMDD)  
- stdate: DST start date  
- endate: DST end date  
- endatep1: DST end + 1 day  

---

## Design Notes

### Why county-level?

- U.S. time zones are defined along county boundaries
- Avoids incorrect assumptions from state-level grouping
- Enables accurate modeling of split states

---

### What is IsPrimary?

Not currently implemented.

- Not part of IANA
- Must be defined as a business rule

Possible definitions:
- largest population
- largest land area
- most counties
- legacy compatibility

---

### Caching behavior

- BTS GeoJSON is cached in /data
- Census shapefiles are cached in /data
- Re-runs do not re-download unless data is cleared

---

## Testing Workflow

Full reset:
_99_start_over.py

Run full pipeline:
_00_run_all.py

---

## Summary

This system:

- Uses authoritative external data
- Eliminates manual maintenance
- Produces reproducible outputs
- Supports both county and state-level analysis
- Is fully executable from a single Python entry point