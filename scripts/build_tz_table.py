from __future__ import annotations

import argparse
from datetime import datetime, timedelta
from typing import Optional, Tuple

import geopandas as gpd
import pandas as pd
from zoneinfo import ZoneInfo

from config import (
    COUNTIES_JOINED_GPKG,
    COUNTIES_JOINED_LAYER,
    FINAL_ORIG_CSV,
    FINAL_CSV,
    IANA_TO_LABELS,
    STATE_ABBR_TO_NAME,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build county-year timezone table from joined county/timezone geography."
    )
    parser.add_argument(
        "--start-year",
        type=int,
        default=2025,
        help="First year to generate.",
    )
    parser.add_argument(
        "--end-year",
        type=int,
        default=datetime.now().year,
        help="Last year to generate.",
    )
    parser.add_argument(
        "--reference-gpkg",
        default=str(COUNTIES_JOINED_GPKG),
        help="Path to county/timezone reference GeoPackage.",
    )
    parser.add_argument(
        "--reference-layer",
        default=COUNTIES_JOINED_LAYER,
        help="Layer name inside the GeoPackage.",
    )
    parser.add_argument(
        "--output-csv",
        default=str(FINAL_CSV),
        help="Path to output CSV.",
    )
    return parser.parse_args()


def format_dt(dt: Optional[datetime]) -> str:
    return dt.strftime("%Y-%m-%d 00:00:00.000") if dt else ""


def format_date(dt: Optional[datetime]) -> str:
    return dt.strftime("%Y-%m-%d") if dt else ""


def format_month_day(dt: Optional[datetime]) -> str:
    return f"{dt.strftime('%B')} {dt.day}" if dt else ""


def format_yyyymmdd(dt: Optional[datetime]) -> str:
    return dt.strftime("%Y%m%d") if dt else ""


def offset_hours_legacy(dt: datetime) -> int:
    """
    Match the legacy convention used by the existing table:
    positive hours offset magnitude, e.g.
      EST -> 5
      CST -> 6
      MST -> 7
      PST -> 8
      AKST -> 9
      AST -> 4
      ChST -> 10
      SST -> 11
    """
    off = dt.utcoffset()
    if off is None:
        raise ValueError("No UTC offset available for datetime.")
    return abs(int(off.total_seconds() // 3600))


def find_transition(
    tz: ZoneInfo,
    start_local: datetime,
    end_local: datetime,
) -> datetime:
    """
    Binary search within a local interval to find when the UTC offset changes.
    Returns a naive local datetime rounded to the minute.
    """
    start_off = start_local.replace(tzinfo=tz).utcoffset()
    end_off = end_local.replace(tzinfo=tz).utcoffset()

    if start_off == end_off:
        raise ValueError("No transition found in the supplied interval.")

    lo = start_local
    hi = end_local

    while (hi - lo) > timedelta(minutes=1):
        mid = lo + (hi - lo) / 2
        if mid.replace(tzinfo=tz).utcoffset() == start_off:
            lo = mid
        else:
            hi = mid

    return hi.replace(second=0, microsecond=0)


def year_transitions(zone_name: str, year: int) -> list[datetime]:
    """
    Scan a year day-by-day to locate offset changes, then refine each one.
    """
    tz = ZoneInfo(zone_name)
    transitions: list[datetime] = []

    current = datetime(year, 1, 1)
    year_end = datetime(year + 1, 1, 1)

    prev_day = current
    prev_off = prev_day.replace(tzinfo=tz).utcoffset()

    current += timedelta(days=1)
    while current <= year_end:
        current_off = current.replace(tzinfo=tz).utcoffset()
        if current_off != prev_off:
            transitions.append(find_transition(tz, prev_day, current))
            prev_off = current_off
        prev_day = current
        current += timedelta(days=1)

    return transitions


def derive_dst_bounds(
    zone_name: str, year: int
) -> Tuple[Optional[datetime], Optional[datetime]]:
    """
    Return DST start and end datetimes for a zone/year.
    For non-DST zones, both return values are None.
    """
    tz = ZoneInfo(zone_name)
    dst_start: Optional[datetime] = None
    dst_end: Optional[datetime] = None

    for trans in year_transitions(zone_name, year):
        before = (trans - timedelta(minutes=30)).replace(tzinfo=tz)
        after = (trans + timedelta(minutes=30)).replace(tzinfo=tz)

        before_off = before.utcoffset()
        after_off = after.utcoffset()

        if before_off is None or after_off is None:
            continue

        if after_off > before_off:
            dst_start = trans
        elif after_off < before_off:
            dst_end = trans

    return dst_start, dst_end


def build_rows(reference: pd.DataFrame, start_year: int, end_year: int) -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    for _, rec in reference.iterrows():
        zone_name = rec["IanaZone"]
        tz = ZoneInfo(zone_name)

        labels = IANA_TO_LABELS.get(zone_name)
        if labels is None:
            raise KeyError(
                f"No legacy label mapping configured for IANA zone: {zone_name}"
            )

        tz_state = rec["TZState"]
        state_name = STATE_ABBR_TO_NAME.get(tz_state, tz_state)

        for year in range(start_year, end_year + 1):
            jan = datetime(year, 1, 15, 12, 0, tzinfo=tz)
            jul = datetime(year, 7, 15, 12, 0, tzinfo=tz)

            jan_dst = jan.dst() or timedelta(0)
            jul_dst = jul.dst() or timedelta(0)

            uses_dst = jan.utcoffset() != jul.utcoffset() or jan_dst != jul_dst
            stdatedt, endatedt = derive_dst_bounds(zone_name, year)

            if uses_dst:
                if jan_dst == timedelta(0):
                    adjhrs = offset_hours_legacy(jan)
                    adjhrsdst = offset_hours_legacy(jul)
                else:
                    adjhrs = offset_hours_legacy(jul)
                    adjhrsdst = offset_hours_legacy(jan)
            else:
                adjhrs = offset_hours_legacy(jan)
                adjhrsdst = adjhrs

            rows.append(
                {
                    "TZState": tz_state,
                    "StateName": state_name,
                    "CountyFIPS": rec["CountyFIPS"],
                    "CountyName": rec["CountyName"],
                    "IanaZone": zone_name,
                    "LegalZoneName": rec["LegalZoneName"],
                    "TZ": labels["TZ"],
                    "ADJHRS": adjhrs,
                    "ADJHRSDST": adjhrsdst,
                    "DST": "Y" if uses_dst else "N",
                    "TZN": labels["TZN"],
                    "TZN2": "",
                    "TSN3": "",
                    "stdatedt": format_dt(stdatedt),
                    "endatedt": format_dt(endatedt),
                    "Year": year,
                    "tzStart": format_month_day(stdatedt),
                    "tzEnd": format_month_day(endatedt),
                    "tstdate": format_yyyymmdd(stdatedt),
                    "tendate": format_yyyymmdd(endatedt),
                    "stdate": format_date(stdatedt),
                    "endate": format_date(endatedt),
                    "endatep1": format_date(endatedt + timedelta(days=1))
                    if endatedt
                    else "",
                }
            )

    return pd.DataFrame(rows)[
        [
            "TZState",
            "StateName",
            "CountyFIPS",
            "CountyName",
            "IanaZone",
            "LegalZoneName",
            "TZ",
            "ADJHRS",
            "ADJHRSDST",
            "DST",
            "TZN",
            "TZN2",
            "TSN3",
            "stdatedt",
            "endatedt",
            "Year",
            "tzStart",
            "tzEnd",
            "tstdate",
            "tendate",
            "stdate",
            "endate",
            "endatep1",
        ]
    ]


def build_orig_rows(county_df: pd.DataFrame) -> pd.DataFrame:
    """
    Collapse county-year rows to one row per state-year. This 
	dataframe matches the original table's schema exactly and 
	can be used for direct comparison. However, the output may
    not match the time zone chosen for those states with multiple 
	time zones (13) . To clarify, for those states with multiple
	time zones, we have chosen the timezone with the most counties
    in that state. We don't know the original logic for how the
	original time zone was chosen.
    
    Rule:
    - For each TZState + Year, pick the time-zone pattern used by the largest
      number of counties in that state for that year.
    """

    working = county_df.copy()

    # Count county rows per state/year/signature
    signature_cols = [
        "TZState",
        "Year",
        "StateName",
        "TZ",
        "ADJHRS",
        "ADJHRSDST",
        "DST",
        "TZN",
        "TZN2",
        "TSN3",
        "stdatedt",
        "endatedt",
        "tzStart",
        "tzEnd",
        "tstdate",
        "tendate",
        "stdate",
        "endate",
        "endatep1",
    ]

    grouped = (
        working.groupby(signature_cols, dropna=False)
        .size()
        .reset_index(name="CountyCount")
    )

    # Sort so the most common pattern per state/year wins
    grouped = grouped.sort_values(
        ["TZState", "Year", "CountyCount", "TZ", "ADJHRS", "TZN"],
        ascending=[True, True, False, True, True, True],
)

    # Keep one row per state/year
    orig_schema = grouped.drop_duplicates(subset=["TZState", "Year"], keep="first").copy()

    # Match original schema exactly
    orig_schema = orig_schema[
        [
            "TZState",
            "StateName",
            "TZ",
            "ADJHRS",
            "ADJHRSDST",
            "DST",
            "TZN",
            "TZN2",
            "TSN3",
            "stdatedt",
            "endatedt",
            "Year",
            "tzStart",
            "tzEnd",
            "tstdate",
            "tendate",
            "stdate",
            "endate",
            "endatep1",
        ]
    ].reset_index(drop=True)

    return orig_schema


def validate_reference(reference: pd.DataFrame) -> None:
    required_columns = {
        "TZState",
        "CountyFIPS",
        "CountyName",
        "LegalZoneName",
        "IanaZone",
    }

    missing = required_columns - set(reference.columns)
    if missing:
        raise ValueError(
            f"Reference geography is missing required columns: {sorted(missing)}"
        )

    if reference["IanaZone"].isna().any():
        sample = reference[reference["IanaZone"].isna()].head(10)
        raise ValueError(
            "Reference geography contains rows with null IanaZone values. "
            f"Sample: {sample.to_dict(orient='records')}"
        )


def main() -> None:
    args = parse_args()

    if args.start_year > args.end_year:
        raise ValueError("--start-year cannot be greater than --end-year")

    reference = gpd.read_file(args.reference_gpkg, layer=args.reference_layer)
    validate_reference(reference)

    county_output = build_rows(reference, args.start_year, args.end_year)
    county_output = county_output.sort_values(
        ["TZState", "CountyName", "Year"]
    ).reset_index(drop=True)
    county_output.to_csv(args.output_csv, index=False, encoding="utf-8")

    orig_output = build_orig_rows(county_output)
    orig_output = orig_output.sort_values(
        ["TZState", "Year"]
    ).reset_index(drop=True)
    orig_output.to_csv(FINAL_ORIG_CSV, index=False, encoding="utf-8")

    print(f"Wrote county-level file: {args.output_csv}")
    print(f"County-level rows written: {len(county_output)}")
    print(f"Wrote original-schema file: {FINAL_ORIG_CSV}")
    print(f"Original-schema rows written: {len(orig_output)}")


if __name__ == "__main__":
    main()
