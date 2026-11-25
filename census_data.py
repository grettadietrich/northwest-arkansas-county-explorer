"""Download and cache the Census estimates and county boundaries."""

import csv
import io
import json
import math
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.request import urlopen
from zipfile import ZipFile

import shapefile


COUNTIES = {"05007": "Benton", "05143": "Washington", "05087": "Madison", "05015": "Carroll"}
ACS_URL = "https://www2.census.gov/programs-surveys/acs/summary_file/2024/table-based-SF/data/5YRData/"
BOUNDARY_URL = "https://www2.census.gov/geo/tiger/GENZ2024/shp/cb_2024_us_county_5m.zip"
CACHE_FILE = Path(__file__).resolve().parent / ".census-cache" / "acs-2024-counties.json"

# Each measure has a display label, table, estimate lines and display format.
METRICS = {
    "population": ("Population", "B01003", (1,), ",.0f"),
    "income": ("Median household income", "B19013", (1,), "$,.0f"),
    "age": ("Median age", "B01002", (1,), ".1f"),
    "education": ("Bachelor’s degree or higher", "B15003", (1, 22, 23, 24, 25), ".1%"),
    "poverty": ("Poverty rate", "B17001", (1, 2), ".1%"),
    "housing": ("Median home value", "B25077", (1,), "$,.0f"),
}


def read_estimate(raw):
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    # Census uses large negative sentinel codes for unavailable estimates.
    return value if math.isfinite(value) and value > -100_000_000 else None


def download_metric(table, lines):
    columns = [f"{table}_E{line:03d}" for line in lines]
    geo_ids = {f"0500000US{fips}": fips for fips in COUNTIES}
    estimates = {}
    with urlopen(f"{ACS_URL}acsdt5y2024-{table.lower()}.dat", timeout=60) as response:
        reader = csv.DictReader(io.TextIOWrapper(response, encoding="utf-8-sig"), delimiter="|")
        if not {"GEO_ID", *columns}.issubset(reader.fieldnames or []):
            raise ValueError(f"Unexpected Census columns in {table}.")
        for row in reader:
            fips = geo_ids.get(row["GEO_ID"])
            if fips is None:
                continue
            values = [read_estimate(row[column]) for column in columns]
            if len(values) == 1:
                estimates[fips] = values[0]
            else:
                denominator, *counts = values
                estimates[fips] = None
                if denominator and denominator > 0 and all(count is not None and count >= 0 for count in counts):
                    numerator = sum(counts)
                    if numerator <= denominator:
                        estimates[fips] = numerator / denominator
            if len(estimates) == len(COUNTIES):
                break
    if not estimates:
        raise ValueError(f"No Northwest Arkansas county records were found in {table}.")
    return estimates


def download_boundaries():
    with urlopen(BOUNDARY_URL, timeout=60) as response:
        archive_bytes = response.read()
    with ZipFile(io.BytesIO(archive_bytes)) as archive:
        stem = "cb_2024_us_county_5m"
        parts = {ext: io.BytesIO(archive.read(f"{stem}.{ext}")) for ext in ("shp", "shx", "dbf")}
        with shapefile.Reader(encoding="latin1", **parts) as reader:
            features = [
                {"type": "Feature", "id": item.record["GEOID"], "properties": {},
                 "geometry": item.shape.__geo_interface__}
                for item in reader.iterShapeRecords(fields=["GEOID"])
                if item.record["GEOID"] in COUNTIES
            ]
    if {feature["id"] for feature in features} != set(COUNTIES):
        raise ValueError("The Census boundary file did not include all four counties.")
    return {"type": "FeatureCollection", "features": features}


def load_data():
    try:
        return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    metrics = {key: download_metric(table, lines) for key, (_, table, lines, _) in METRICS.items()}
    rows = [
        {"fips": fips, "county": county, **{key: values.get(fips) for key, values in metrics.items()}}
        for fips, county in COUNTIES.items()
    ]
    data = {"rows": rows, "boundaries": download_boundaries()}
    CACHE_FILE.parent.mkdir(exist_ok=True)
    # A second session can only see the cache after the complete file is written.
    with NamedTemporaryFile(mode="w", encoding="utf-8", dir=CACHE_FILE.parent, delete=False) as temp:
        temp_path = Path(temp.name)
        try:
            json.dump(data, temp, allow_nan=False)
            temp.close()
            temp_path.replace(CACHE_FILE)
        finally:
            temp.close()
            temp_path.unlink(missing_ok=True)
    return data
