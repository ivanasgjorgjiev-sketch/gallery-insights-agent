"""Presentation-only display names for the fictional demo.

These names are shown in the UI only. Data files, calculations, tool inputs
and evaluation cases always use the original IDs (G001, E001).
"""

GALLERY_NAMES = {"G001": "Atelier North Gallery"}

EDITIONS = {
    "E001": {"name": "Art Now Basel 2026", "dates": "October 14–18, 2026"},
}


def gallery_name(gallery_id: str) -> str:
    return GALLERY_NAMES.get(gallery_id, gallery_id)


def edition_label(edition_id: str) -> str:
    edition = EDITIONS.get(edition_id)
    if edition is None:
        return edition_id
    return f"{edition['name']} ({edition['dates']})"
