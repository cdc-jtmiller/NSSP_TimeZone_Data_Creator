import pandas as pd
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
county_file = project_root / "output" / "tzstdst_county_year.csv"

df = pd.read_csv(county_file, dtype=str)

fl = df[df["TZState"] == "FL"]

print(
    fl[["CountyName", "LegalZoneName", "IanaZone", "TZ", "TZN", "Year"]]
    .drop_duplicates()
    .sort_values(["Year", "LegalZoneName", "CountyName"])
    .to_string(index=False)
)

print()
print(fl.groupby(["Year", "LegalZoneName", "IanaZone", "TZ", "TZN"]).size())
