from __future__ import annotations

import io
import zipfile
from pathlib import Path

import geopandas as gpd
import requests
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import (
    BTS_TIMEZONES_SERVICE,
    CENSUS_COUNTIES_ZIP,
    COUNTIES_DIR,
    TIMEZONES_GEOJSON,
    COUNTIES_JOINED_GPKG,
    COUNTIES_JOINED_LAYER,
    LEGAL_ZONE_TO_IANA,
    STATEFP_TO_ABBR,
    VERIFY_SSL,
)


if not VERIFY_SSL:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def create_session() -> requests.Session:
    session = requests.Session()

    retries = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["GET"],
    )

    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    return session


SESSION = create_session()


def http_get(url: str) -> requests.Response:
    return SESSION.get(
        url,
        timeout=120,
        headers={"User-Agent": "TimeZone_Update/1.0"},
        verify=VERIFY_SSL,
    )


def download_geojson(url: str, dest_file: Path) -> Path:
    if dest_file.exists():
        print(f"Using cached file: {dest_file}")
        return dest_file

    print(f"Downloading to: {dest_file}")
    resp = http_get(url)
    resp.raise_for_status()

    dest_file.write_bytes(resp.content)
    return dest_file


def download_and_extract_zip(url: str, dest_dir: Path) -> None:
    dest_dir.mkdir(parents=True, exist_ok=True)

    print(f"Downloading and extracting to: {dest_dir}")
    resp = http_get(url)
    resp.raise_for_status()

    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        zf.extractall(dest_dir)


def find_vector_file(folder: Path) -> Path:
    shp_files = list(folder.rglob("*.shp"))
    if shp_files:
        return shp_files[0]

    gpkg_files = list(folder.rglob("*.gpkg"))
    if gpkg_files:
        return gpkg_files[0]

    gdb_dirs = [p for p in folder.rglob("*.gdb") if p.is_dir()]
    if gdb_dirs:
        return gdb_dirs[0]

    raise FileNotFoundError(f"No supported vector file found under {folder}")


def load_counties() -> gpd.GeoDataFrame:
    if not COUNTIES_DIR.exists() or not any(COUNTIES_DIR.iterdir()):
        download_and_extract_zip(CENSUS_COUNTIES_ZIP, COUNTIES_DIR)

    counties_path = find_vector_file(COUNTIES_DIR)
    print(f"Reading counties from: {counties_path}")

    gdf = gpd.read_file(counties_path)

    keep = [
        c
        for c in ["STATEFP", "COUNTYFP", "GEOID", "NAME", "NAMELSAD", "geometry"]
        if c in gdf.columns
    ]
    gdf = gdf[keep].copy()

    gdf["TZState"] = gdf["STATEFP"].map(STATEFP_TO_ABBR)
    gdf["CountyFIPS"] = gdf["GEOID"]
    gdf["CountyName"] = gdf["NAMELSAD"] if "NAMELSAD" in gdf.columns else gdf["NAME"]

    return gdf


def load_timezones() -> gpd.GeoDataFrame:
    print("Downloading time zone boundaries from BTS ArcGIS service...")

    local_geojson = download_geojson(BTS_TIMEZONES_SERVICE, TIMEZONES_GEOJSON)

    print(f"Reading local GeoJSON: {local_geojson}")
    gdf = gpd.read_file(local_geojson)

    print(f"Columns returned: {list(gdf.columns)}")

    if "zone" not in gdf.columns:
        raise KeyError(
            f"Expected 'zone' column not found. Columns: {list(gdf.columns)}"
        )

    gdf = gdf[["zone", "utc", "geometry"]].copy()
    gdf = gdf.rename(columns={"zone": "LegalZoneName", "utc": "UtcLabel"})
    return gdf


def normalize_legal_zone_name(raw: str) -> str:
    if raw is None:
        return ""

    s = str(raw).strip()
    s_upper = s.upper()

    if "EASTERN" in s_upper:
        return "Eastern"
    if "CENTRAL" in s_upper:
        return "Central"
    if "MOUNTAIN" in s_upper:
        return "Mountain"
    if "PACIFIC" in s_upper:
        return "Pacific"
    if "ALASKA" in s_upper:
        return "Alaska"
    if "HAWAII" in s_upper or "ALEUTIAN" in s_upper:
        return "Hawaii-Aleutian"
    if "ATLANTIC" in s_upper:
        return "Atlantic"
    if "SAMOA" in s_upper:
        return "Samoa"
    if "CHAMORRO" in s_upper or "GUAM" in s_upper:
        return "Chamorro"

    return s


def build_county_timezone_reference() -> gpd.GeoDataFrame:
    counties = load_counties()
    timezones = load_timezones()

    if counties.crs != timezones.crs:
        timezones = timezones.to_crs(counties.crs)

    timezones["LegalZoneName"] = timezones["LegalZoneName"].map(
        normalize_legal_zone_name
    )
    timezones["IanaZone"] = timezones["LegalZoneName"].map(LEGAL_ZONE_TO_IANA)

    missing = (
        timezones[timezones["IanaZone"].isna()]["LegalZoneName"]
        .dropna()
        .unique()
        .tolist()
    )
    if missing:
        raise ValueError(f"Unmapped legal zones found in BTS layer: {missing}")

    counties_centroid = counties.copy()
    counties_centroid["geometry"] = counties_centroid.geometry.representative_point()

    joined = gpd.sjoin(
        counties_centroid,
        timezones[["LegalZoneName", "IanaZone", "geometry"]],
        how="left",
        predicate="within",
    )

    result = counties.merge(
        joined[["CountyFIPS", "LegalZoneName", "IanaZone"]],
        on="CountyFIPS",
        how="left",
    )

    missing_counties = result[result["IanaZone"].isna()][["CountyFIPS", "CountyName"]]
    if not missing_counties.empty:
        raise ValueError(
            f"Some counties did not match a time zone polygon. Sample: "
            f"{missing_counties.head(10).to_dict(orient='records')}"
        )

    if COUNTIES_JOINED_GPKG.exists():
        COUNTIES_JOINED_GPKG.unlink()

    result.to_file(COUNTIES_JOINED_GPKG, layer=COUNTIES_JOINED_LAYER, driver="GPKG")
    return result


def main() -> None:
    gdf = build_county_timezone_reference()
    print(
        gdf[["TZState", "CountyFIPS", "CountyName", "LegalZoneName", "IanaZone"]].head(
            20
        )
    )
    print(f"Wrote {COUNTIES_JOINED_GPKG} layer={COUNTIES_JOINED_LAYER}")


if __name__ == "__main__":
    main()
