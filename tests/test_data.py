"""Milestone 1 tests: data loading, validation and the data_dictionary.md reference values."""

import hashlib
from pathlib import Path

import pandas as pd
import pytest

from gia.data import DEFAULT_CSV, DataValidationError, load_processed_data

ROOT = Path(__file__).resolve().parent.parent

# SHA-256 fingerprints of the five source documents, recorded before any development.
# If one of these fails, a source file was changed.
SOURCE_FINGERPRINTS = {
    "PRD.md": "dfcbed9e7c79870313e004c44b045373b87befca6738b2f18fdcc28c10143a00",
    "daily_data.csv": "dbf61490a4b7876ada6d131c43db10aa309a54624dbcab2fbf65759a8f9d9a2f",
    "data_dictionary.md": "fbafcf2751c2c8ac567532ae89592a21482dd78b3178d1b10e581927c74162d5",
    "agent_policy.md": "79d63301e0481cd05fa0c7ab8c559aafb2c681142da269ae35168633732c94d2",
    "eval_cases.json": "d3bb2da9c06ae24aa6a1995ae44b6b63bcba291e924eb26289df1c0ffd3fc172",
}


@pytest.fixture(scope="module")
def data():
    return load_processed_data()


def views(data, artwork_id):
    return data.artwork_daily.loc[data.artwork_daily["artwork_id"] == artwork_id, "artwork_views"]


# --- Source files are untouched -------------------------------------------------

@pytest.mark.parametrize("name,expected", SOURCE_FINGERPRINTS.items())
def test_source_document_unchanged(name, expected):
    assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected


# --- Expected integrity checks from data_dictionary.md --------------------------

def test_row_counts(data):
    assert data.total_rows == 35
    assert data.eligible_rows == 28
    assert len(data.gallery_daily) == 4
    assert len(data.artwork_daily) == 24


def test_day5_excluded(data):
    assert data.processed_dates == ["2026-10-14", "2026-10-15", "2026-10-16", "2026-10-17"]
    assert data.excluded_dates == ["2026-10-18"]
    assert "2026-10-18" not in set(data.artwork_daily["fair_date"])
    assert "2026-10-18" not in set(data.gallery_daily["fair_date"])


def test_processed_gallery_views_total(data):
    assert data.gallery_daily["gallery_views"].tolist() == [120, 165, 158, 172]
    assert data.gallery_daily["gallery_views"].sum() == 615


def test_a001_processed_views_is_286_not_436(data):
    assert views(data, "A001").tolist() == [40, 80, 76, 90]
    assert views(data, "A001").sum() == 286


def test_a002_and_artist_a_totals(data):
    assert views(data, "A002").sum() == 130
    artist_a = data.artwork_daily[data.artwork_daily["artist_id"] == "AR01"]
    assert sorted(artist_a["artwork_id"].unique()) == ["A001", "A002"]
    assert artist_a["artwork_views"].sum() == 416


def test_c002_day2_unique_viewers_is_unknown_not_zero(data):
    row = data.artwork_daily[
        (data.artwork_daily["artwork_id"] == "C002") & (data.artwork_daily["fair_date"] == "2026-10-15")
    ].iloc[0]
    assert pd.isna(row["unique_artwork_viewers"])
    assert row["artwork_views"] == 20
    assert any("C002" in note for note in data.notes)


def test_seeded_scenario_series(data):
    a1 = data.artwork_daily[data.artwork_daily["artwork_id"] == "A001"]
    assert a1["unique_artwork_viewers"].tolist() == [30, 45, 50, 60]
    assert a1["favourites"].tolist() == [5, 12, 11, 13]
    assert views(data, "B001").tolist() == [30, 45, 32, 31]
    assert views(data, "B002").tolist() == [20, 21, 20, 20]
    assert views(data, "C001").tolist()[:2] == [0, 10]


def test_measured_zero_is_kept_as_zero(data):
    c1_day1 = data.artwork_daily[
        (data.artwork_daily["artwork_id"] == "C001") & (data.artwork_daily["fair_date"] == "2026-10-14")
    ].iloc[0]
    assert c1_day1["artwork_views"] == 0
    assert c1_day1["unique_artwork_viewers"] == 0


def test_unknown_gallery_or_edition_is_rejected():
    with pytest.raises(DataValidationError):
        load_processed_data(gallery_id="G999")
    with pytest.raises(DataValidationError):
        load_processed_data(edition_id="E000")


# --- Invalid files are rejected ------------------------------------------------

def write_variant(tmp_path, edit):
    """Copy the real CSV, apply `edit` to its list of lines, and return the new path."""
    lines = DEFAULT_CSV.read_text().splitlines()
    edit(lines)
    path = tmp_path / "variant.csv"
    path.write_text("\n".join(lines) + "\n")
    return path


def find_line(lines, *parts):
    return next(i for i, line in enumerate(lines) if all(p in line for p in parts))


def replace_in(lines, old, new, *parts):
    i = find_line(lines, *parts)
    assert old in lines[i]
    lines[i] = lines[i].replace(old, new, 1)


def expect_issue(path, text):
    with pytest.raises(DataValidationError) as err:
        load_processed_data(path)
    assert any(text in issue for issue in err.value.issues), err.value.issues


def test_rejects_duplicate_record(tmp_path):
    path = write_variant(tmp_path, lambda l: l.append(l[find_line(l, "2026-10-15", "A001")]))
    expect_issue(path, "duplicate record")


def test_rejects_negative_count(tmp_path):
    path = write_variant(tmp_path, lambda l: replace_in(l, ",80,45,", ",-80,45,", "2026-10-15", "A001"))
    expect_issue(path, "artwork_views '-80'")


def test_rejects_decimal_count(tmp_path):
    path = write_variant(tmp_path, lambda l: replace_in(l, ",80,45,", ",80.0,45,", "2026-10-15", "A001"))
    expect_issue(path, "artwork_views '80.0'")


def test_rejects_invalid_date(tmp_path):
    path = write_variant(tmp_path, lambda l: replace_in(l, "2026-10-15", "2026-13-15", "2026-10-15", "A001"))
    expect_issue(path, "not a valid YYYY-MM-DD date")


def test_rejects_unrecognised_boolean(tmp_path):
    path = write_variant(tmp_path, lambda l: replace_in(l, ",true,", ",yes,", "2026-10-15", "A001"))
    expect_issue(path, "day_processed 'yes'")


def test_rejects_blank_required_metric_on_processed_row(tmp_path):
    path = write_variant(tmp_path, lambda l: replace_in(l, ",12,0", ",,0", "2026-10-15", "A001"))
    expect_issue(path, "missing favourites")


def test_rejects_inconsistent_artist_metadata(tmp_path):
    path = write_variant(tmp_path, lambda l: replace_in(l, "Artist A", "Artist Z", "2026-10-15", "A001"))
    expect_issue(path, "inconsistent artist_name")


def test_rejects_gallery_row_with_artwork_metric(tmp_path):
    path = write_variant(tmp_path, lambda l: replace_in(l, ",165,,,,", ",165,10,,,", "gallery", "2026-10-15"))
    expect_issue(path, "gallery row must leave artwork_views blank")


def test_rejects_missing_gallery_row(tmp_path):
    path = write_variant(tmp_path, lambda l: l.pop(find_line(l, "gallery", "2026-10-15")))
    expect_issue(path, "expected exactly one gallery row")


def test_rejects_missing_artwork_row(tmp_path):
    path = write_variant(tmp_path, lambda l: l.pop(find_line(l, "2026-10-16", "B002")))
    expect_issue(path, "missing artwork rows for ['B002']")


def test_rejects_wrong_columns(tmp_path):
    path = write_variant(tmp_path, lambda l: l.__setitem__(0, l[0].replace("favourites", "favorites")))
    expect_issue(path, "columns must be exactly")
