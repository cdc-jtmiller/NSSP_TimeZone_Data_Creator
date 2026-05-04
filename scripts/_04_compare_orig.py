from __future__ import annotations

from pathlib import Path
import argparse

import pandas as pd
from datacompy.core import Compare


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"

ORIGINAL_CSV = DATA_DIR / "tzstdst_orig.csv"
NEW_CSV = OUTPUT_DIR / "tzstdst_state_year.csv"
REPORT_TXT = OUTPUT_DIR / "tzstdst_compare_report.txt"
COLUMN_DIFF_CSV = OUTPUT_DIR / "tzstdst_compare_column_diffs.csv"
ROW_DIFF_CSV = OUTPUT_DIR / "tzstdst_compare_row_diffs.csv"

EXPECTED_COLUMNS = [
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

JOIN_COLUMNS = ["TZState", "Year"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare legacy tzstdst CSV with newly generated state-year CSV."
    )
    parser.add_argument(
        "--original-csv",
        default=str(ORIGINAL_CSV),
        help="Path to the original CSV in the data folder.",
    )
    parser.add_argument(
        "--new-csv",
        default=str(NEW_CSV),
        help="Path to the newly generated CSV in the output folder.",
    )
    parser.add_argument(
        "--report-txt",
        default=str(REPORT_TXT),
        help="Path to write the DataComPy text report.",
    )
    parser.add_argument(
        "--column-diff-csv",
        default=str(COLUMN_DIFF_CSV),
        help="Path to write cell-level differences.",
    )
    parser.add_argument(
        "--row-diff-csv",
        default=str(ROW_DIFF_CSV),
        help="Path to write row-presence differences.",
    )
    return parser.parse_args()


def load_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str, encoding="cp1252").fillna("")

    for col in df.columns:
        if df[col].dtype == object:
            df[col] = (
                df[col].astype(str).str.replace("\xa0", " ", regex=False).str.strip()
            )

    return df


def validate_columns(df: pd.DataFrame, label: str) -> None:
    missing = [c for c in EXPECTED_COLUMNS if c not in df.columns]
    extra = [c for c in df.columns if c not in EXPECTED_COLUMNS]

    if missing:
        raise ValueError(f"{label} is missing expected columns: {missing}")

    if extra:
        print(f"Warning: {label} has extra columns that will be ignored: {extra}")


def normalize_frames(
    original_df: pd.DataFrame,
    new_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    original_df = original_df[EXPECTED_COLUMNS].copy()
    new_df = new_df[EXPECTED_COLUMNS].copy()

    # Ensure identical column order
    original_df = original_df[EXPECTED_COLUMNS]
    new_df = new_df[EXPECTED_COLUMNS]

    return original_df, new_df


def filter_original_to_new_years(
    original_df: pd.DataFrame,
    new_df: pd.DataFrame,
) -> pd.DataFrame:
    years = sorted(new_df["Year"].dropna().unique())

    if not years:
        raise ValueError("New CSV does not contain any Year values to compare.")

    original_row_count = len(original_df)
    original_df = original_df[original_df["Year"].isin(years)].copy()

    print(
        "Filtered original CSV to years present in new CSV "
        f"({', '.join(years)}): {original_row_count} -> {len(original_df)} rows"
    )

    return original_df


def build_datacompy_report(
    original_df: pd.DataFrame,
    new_df: pd.DataFrame,
) -> Compare:
    compare = Compare(
        original_df.copy(),
        new_df.copy(),
        join_columns=JOIN_COLUMNS,
        df1_name="original",
        df2_name="new",
        abs_tol=0,
        rel_tol=0,
    )
    return compare


def build_row_diff_csv(
    original_df: pd.DataFrame,
    new_df: pd.DataFrame,
    output_path: str,
) -> None:
    original_keys = original_df[JOIN_COLUMNS].drop_duplicates().copy()
    new_keys = new_df[JOIN_COLUMNS].drop_duplicates().copy()

    merged = original_keys.merge(
        new_keys,
        on=JOIN_COLUMNS,
        how="outer",
        indicator=True,
    )

    merged = merged.rename(columns={"_merge": "RowStatus"})
    merged.to_csv(output_path, index=False, encoding="utf-8")


def build_column_diff_csv(
    original_df: pd.DataFrame,
    new_df: pd.DataFrame,
    output_path: str,
) -> None:
    merged = original_df.merge(
        new_df,
        on=JOIN_COLUMNS,
        how="outer",
        suffixes=("_original", "_new"),
        indicator=True,
    )

    diff_rows: list[dict[str, str]] = []
    compare_columns = [c for c in EXPECTED_COLUMNS if c not in JOIN_COLUMNS]

    for _, row in merged.iterrows():
        row_status = row["_merge"]

        if row_status != "both":
            diff_rows.append(
                {
                    "TZState": row.get("TZState", ""),
                    "Year": row.get("Year", ""),
                    "ColumnName": "",
                    "OriginalValue": "",
                    "NewValue": "",
                    "DifferenceType": f"row_{row_status}",
                }
            )
            continue

        for col in compare_columns:
            original_value = row.get(f"{col}_original", "")
            new_value = row.get(f"{col}_new", "")

            original_value = "" if pd.isna(original_value) else str(original_value)
            new_value = "" if pd.isna(new_value) else str(new_value)

            if original_value != new_value:
                diff_rows.append(
                    {
                        "TZState": row["TZState"],
                        "Year": row["Year"],
                        "ColumnName": col,
                        "OriginalValue": original_value,
                        "NewValue": new_value,
                        "DifferenceType": "cell_difference",
                    }
                )

    diff_df = pd.DataFrame(
        diff_rows,
        columns=[
            "TZState",
            "Year",
            "ColumnName",
            "OriginalValue",
            "NewValue",
            "DifferenceType",
        ],
    )
    diff_df.to_csv(output_path, index=False, encoding="utf-8")


def main() -> None:
    args = parse_args()

    original_df = load_csv(args.original_csv)
    new_df = load_csv(args.new_csv)

    validate_columns(original_df, "Original CSV")
    validate_columns(new_df, "New CSV")

    original_df, new_df = normalize_frames(original_df, new_df)
    original_df = filter_original_to_new_years(original_df, new_df)

    compare = build_datacompy_report(original_df, new_df)
    report_text = compare.report()

    Path(args.report_txt).write_text(report_text, encoding="utf-8")
    build_row_diff_csv(original_df, new_df, args.row_diff_csv)
    build_column_diff_csv(original_df, new_df, args.column_diff_csv)

    print(f"Wrote DataComPy report: {args.report_txt}")
    print(f"Wrote row-level differences: {args.row_diff_csv}")
    print(f"Wrote column-level differences: {args.column_diff_csv}")
    print(f"Matches exactly: {compare.matches(ignore_extra_columns=False)}")


if __name__ == "__main__":
    main()
