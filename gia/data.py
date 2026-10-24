"""Load, validate and filter daily_data.csv.

Rules follow data_dictionary.md:
- Every value is read as text first, so a blank is never silently turned into 0.
- The whole file is validated (schema, types, record relationships, duplicates,
  artist metadata). Any problem stops the analysis with a clear list of issues.
- Only rows for the selected gallery/edition with day_processed=true are eligible.
- unique_artwork_viewers may be blank and stays "unknown" (pandas <NA>), never 0.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import pandas as pd

DEFAULT_CSV = Path(__file__).resolve().parent.parent / "daily_data.csv"
DEFAULT_GALLERY_ID = "G001"
DEFAULT_EDITION_ID = "E001"

COLUMNS = [
    "record_type", "gallery_id", "edition_id", "fair_date", "day_processed",
    "artist_id", "artist_name", "artwork_id", "artwork_title",
    "gallery_views", "artwork_views", "unique_artwork_viewers", "favourites", "inquiries",
]
ARTWORK_TEXT_FIELDS = ["artist_id", "artist_name", "artwork_id", "artwork_title"]
ARTWORK_REQUIRED_METRICS = ["artwork_views", "favourites", "inquiries"]
ARTWORK_METRICS = ["artwork_views", "unique_artwork_viewers", "favourites", "inquiries"]
BOOLEANS = {"true": True, "false": False}


class DataValidationError(Exception):
    """Raised when the CSV fails validation. `issues` lists every problem found."""

    def __init__(self, issues: list[str]):
        self.issues = issues
        super().__init__(f"{len(issues)} data validation issue(s): " + "; ".join(issues))


@dataclass
class ProcessedData:
    """Eligible (processed, in-scope) records plus context about what was excluded."""

    gallery_id: str
    edition_id: str
    source_file: str
    gallery_daily: pd.DataFrame   # fair_date, gallery_views, source_line
    artwork_daily: pd.DataFrame   # fair_date, artist/artwork fields, artwork metrics, source_line
    processed_dates: list[str]
    excluded_dates: list[str]     # in-scope dates with day_processed=false
    total_rows: int
    eligible_rows: int
    out_of_scope_rows: int        # rows for other galleries/editions
    notes: list[str] = field(default_factory=list)


def _parse_count(value: str) -> int | None:
    """Parse a nonnegative whole number. Returns None for invalid text."""
    if value.isdigit():
        return int(value)
    return None


def _validate(raw: pd.DataFrame) -> list[str]:
    issues: list[str] = []

    for i, row in raw.iterrows():
        line = i + 2  # +1 for header, +1 for 1-based line numbers
        where = f"line {line}"

        rtype = row["record_type"]
        if rtype not in ("gallery", "artwork"):
            issues.append(f"{where}: record_type '{rtype}' must be 'gallery' or 'artwork'")
            continue
        for col in ("gallery_id", "edition_id"):
            if not row[col]:
                issues.append(f"{where}: {col} is required")
        try:
            dt.date.fromisoformat(row["fair_date"])
            if len(row["fair_date"]) != 10:
                raise ValueError
        except ValueError:
            issues.append(f"{where}: fair_date '{row['fair_date']}' is not a valid YYYY-MM-DD date")
        processed_text = row["day_processed"].lower()
        if processed_text not in BOOLEANS:
            issues.append(f"{where}: day_processed '{row['day_processed']}' must be 'true' or 'false'")
        processed = BOOLEANS.get(processed_text, False)

        if rtype == "gallery":
            for col in ARTWORK_TEXT_FIELDS + ARTWORK_METRICS:
                if row[col]:
                    issues.append(f"{where}: gallery row must leave {col} blank")
            value = row["gallery_views"]
            if value and _parse_count(value) is None:
                issues.append(f"{where}: gallery_views '{value}' must be a nonnegative whole number")
            elif not value and processed:
                issues.append(f"{where}: processed gallery row is missing gallery_views")
        else:
            for col in ARTWORK_TEXT_FIELDS:
                if not row[col]:
                    issues.append(f"{where}: artwork row is missing {col}")
            if row["gallery_views"]:
                issues.append(f"{where}: artwork row must leave gallery_views blank")
            for col in ARTWORK_METRICS:
                value = row[col]
                if value and _parse_count(value) is None:
                    issues.append(f"{where}: {col} '{value}' must be a nonnegative whole number")
                elif not value and processed and col in ARTWORK_REQUIRED_METRICS:
                    issues.append(f"{where}: processed artwork row is missing {col}")

    key = ["record_type", "gallery_id", "edition_id", "fair_date", "artwork_id"]
    for _, dup in raw[raw.duplicated(key, keep=False)].groupby(key):
        lines = ", ".join(str(i + 2) for i in dup.index)
        issues.append(f"lines {lines}: duplicate record for {tuple(dup.iloc[0][key])}")

    artworks = raw[raw["record_type"] == "artwork"]
    for artwork_id, rows in artworks.groupby("artwork_id"):
        for col in ("artist_id", "artist_name", "artwork_title"):
            if rows[col].nunique() > 1:
                issues.append(f"artwork {artwork_id}: inconsistent {col} values {sorted(rows[col].unique())}")
    for artist_id, rows in artworks.groupby("artist_id"):
        if rows["artist_name"].nunique() > 1:
            issues.append(f"artist {artist_id}: inconsistent artist_name values {sorted(rows['artist_name'].unique())}")

    # Record relationships: per gallery/edition, every date has one gallery row
    # and one row for each artwork that appears in that edition.
    for (gallery_id, edition_id), scope in raw.groupby(["gallery_id", "edition_id"]):
        expected_artworks = set(scope.loc[scope["record_type"] == "artwork", "artwork_id"])
        for fair_date, day in scope.groupby("fair_date"):
            label = f"{gallery_id}/{edition_id} {fair_date}"
            if (day["record_type"] == "gallery").sum() != 1:
                issues.append(f"{label}: expected exactly one gallery row")
            missing = expected_artworks - set(day.loc[day["record_type"] == "artwork", "artwork_id"])
            if missing:
                issues.append(f"{label}: missing artwork rows for {sorted(missing)}")
        if scope.groupby("fair_date")["day_processed"].nunique().gt(1).any():
            issues.append(f"{gallery_id}/{edition_id}: day_processed differs between rows of the same date")

    return issues


def load_processed_data(
    path: str | Path = DEFAULT_CSV,
    gallery_id: str = DEFAULT_GALLERY_ID,
    edition_id: str = DEFAULT_EDITION_ID,
) -> ProcessedData:
    """Validate the CSV and return only the eligible records for one gallery/edition.

    Raises DataValidationError if the file fails any check. Results are cached until the file
    changes (path, size and modification time), so repeated tool calls do not re-validate.
    Callers must treat the returned frames as read-only.
    """
    path = Path(path).resolve()
    stat = path.stat()
    return _load_cached(str(path), stat.st_size, stat.st_mtime_ns, gallery_id, edition_id)


@lru_cache(maxsize=16)
def _load_cached(path_str: str, size: int, mtime_ns: int, gallery_id: str, edition_id: str) -> ProcessedData:
    path = Path(path_str)
    raw = pd.read_csv(path, dtype=str, keep_default_na=False)
    if list(raw.columns) != COLUMNS:
        raise DataValidationError([f"columns must be exactly {COLUMNS}, found {list(raw.columns)}"])
    raw = raw.apply(lambda col: col.str.strip())

    issues = _validate(raw)
    if issues:
        raise DataValidationError(issues)
    raw["source_line"] = raw.index + 2  # line number in the CSV, for provenance

    in_scope = raw[(raw["gallery_id"] == gallery_id) & (raw["edition_id"] == edition_id)]
    if in_scope.empty:
        raise DataValidationError([f"no records found for {gallery_id}/{edition_id}"])
    processed_mask = in_scope["day_processed"].str.lower() == "true"
    eligible = in_scope[processed_mask]
    if eligible.empty:
        raise DataValidationError([f"no processed days found for {gallery_id}/{edition_id}"])

    gallery_daily = eligible[eligible["record_type"] == "gallery"][
        ["fair_date", "gallery_views", "source_line"]
    ].copy()
    gallery_daily["gallery_views"] = gallery_daily["gallery_views"].astype("int64")

    artwork_daily = eligible[eligible["record_type"] == "artwork"][
        ["fair_date"] + ARTWORK_TEXT_FIELDS + ARTWORK_METRICS + ["source_line"]
    ].copy()
    for col in ARTWORK_METRICS:
        # Nullable integers: blank -> <NA> (unknown), never 0.
        artwork_daily[col] = pd.array(
            [int(v) if v else pd.NA for v in artwork_daily[col]], dtype="Int64"
        )

    notes = []
    missing_uniques = artwork_daily[artwork_daily["unique_artwork_viewers"].isna()]
    for _, r in missing_uniques.iterrows():
        notes.append(f"{r['artwork_id']} on {r['fair_date']}: unique_artwork_viewers is unknown (blank in source)")

    return ProcessedData(
        gallery_id=gallery_id,
        edition_id=edition_id,
        source_file=path.name,
        gallery_daily=gallery_daily.sort_values("fair_date").reset_index(drop=True),
        artwork_daily=artwork_daily.sort_values(["fair_date", "artwork_id"]).reset_index(drop=True),
        processed_dates=sorted(eligible["fair_date"].unique()),
        excluded_dates=sorted(in_scope.loc[~processed_mask, "fair_date"].unique()),
        total_rows=len(raw),
        eligible_rows=len(eligible),
        out_of_scope_rows=len(raw) - len(in_scope),
        notes=notes,
    )
