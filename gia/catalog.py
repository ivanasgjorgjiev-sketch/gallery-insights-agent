"""Fictional sample artwork catalog (Milestone 10): display context for each artwork.

Presentation only, like display_names.py. Titles, artists, media and thumbnails are invented sample data and
are never passed to the agent, the tools, the validation checks or the evaluations, which keep using the
source IDs and labels in daily_data.csv (A001 / "Artwork A1"). Titles contain no digits, so text that names
an artwork is never mistaken for a figure by the grounding check.
"""

from __future__ import annotations

from pathlib import Path

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets" / "artworks"
FICTIONAL_NOTE = "Fictional sample artwork"
CATALOG_HELP = ("Titles, artists, media and images are fictional sample data for this prototype. The analysis "
                "uses only the source IDs and engagement figures.")

ARTISTS = {
    "AR01": "Ines Halvorsen",
    "AR02": "Tomas Reyland",
    "AR03": "Noor Castellane",
}

ARTWORKS = {
    "A001": {"title": "Harbour at First Light", "artist_id": "AR01", "medium": "Oil on linen"},
    "A002": {"title": "Salt Study, Grey", "artist_id": "AR01", "medium": "Oil on panel"},
    "B001": {"title": "Red Interval", "artist_id": "AR02", "medium": "Acrylic on canvas"},
    "B002": {"title": "Quiet Grid", "artist_id": "AR02", "medium": "Acrylic on canvas"},
    "C001": {"title": "Paper Moon", "artist_id": "AR03", "medium": "Ink on paper"},
    "C002": {"title": "Field Notes in Blue", "artist_id": "AR03", "medium": "Watercolour"},
}


def title(artwork_id: str, fallback: str | None = None) -> str:
    """The catalog title, or the source label when the artwork is not in the catalog."""
    entry = ARTWORKS.get(artwork_id)
    return entry["title"] if entry else (fallback or artwork_id)


def artist(artist_id: str, fallback: str | None = None) -> str:
    return ARTISTS.get(artist_id, fallback or artist_id)


def medium(artwork_id: str) -> str | None:
    entry = ARTWORKS.get(artwork_id)
    return entry["medium"] if entry else None


def thumbnail_svg(artwork_id: str) -> str | None:
    """The artwork's thumbnail as SVG markup, or None when there is no catalog image."""
    path = ASSETS_DIR / f"{artwork_id}.svg"
    if artwork_id not in ARTWORKS or not path.is_file():
        return None
    return path.read_text(encoding="utf-8")
