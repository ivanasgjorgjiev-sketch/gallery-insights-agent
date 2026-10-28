"""Generate the fictional sample artwork thumbnails in assets/artworks/ (Milestone 10).

Abstract SVG compositions, made here rather than taken from any real artwork, so there are no image rights to
clear. Each artist has one motif and palette, so an artist's works look related; the layout of each work is
seeded by its artwork ID, so the output is identical on every run. Run from the project root:

    .venv/bin/python scripts/make_artwork_thumbnails.py
"""

from __future__ import annotations

import hashlib
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gia import catalog  # noqa: E402

SIZE = 120
PALETTES = {
    "AR01": ["#1f3b57", "#3d6a8a", "#8fb3c9", "#e9c9a0", "#f4e6cf"],   # harbour blues, early light
    "AR02": ["#7a1f1f", "#b23a2e", "#d9734e", "#4a4a4a", "#e8e2d6"],   # reds and greys, hard edges
    "AR03": ["#1d2a44", "#355c8c", "#7ea6c9", "#d8e3ec", "#f7f4ee"],   # ink blues on paper
}


def _rng(artwork_id: str) -> random.Random:
    return random.Random(int(hashlib.sha256(artwork_id.encode()).hexdigest()[:12], 16))


def _bands(r: random.Random, p: list[str]) -> list[str]:
    """Horizontal colour fields (AR01)."""
    shapes, y = [], 0
    for colour in r.sample(p, len(p)):
        h = r.randint(16, 34)
        shapes.append(f'<rect x="0" y="{y}" width="{SIZE}" height="{min(h, SIZE - y)}" fill="{colour}"/>')
        y += h
        if y >= SIZE:
            break
    if y < SIZE:
        shapes.append(f'<rect x="0" y="{y}" width="{SIZE}" height="{SIZE - y}" fill="{p[0]}"/>')
    sun = r.choice(p[3:])
    shapes.append(f'<circle cx="{r.randint(30, 90)}" cy="{r.randint(22, 50)}" r="{r.randint(9, 15)}" '
                  f'fill="{sun}" opacity="0.9"/>')
    return shapes


def _blocks(r: random.Random, p: list[str]) -> list[str]:
    """Overlapping rectangles (AR02)."""
    shapes = [f'<rect width="{SIZE}" height="{SIZE}" fill="{p[4]}"/>']
    for _ in range(5):
        w, h = r.randint(28, 70), r.randint(20, 60)
        x, y = r.randint(0, SIZE - w), r.randint(0, SIZE - h)
        shapes.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{r.choice(p[:4])}" '
                      f'opacity="{r.choice([0.75, 0.85, 1])}"/>')
    return shapes


def _ink(r: random.Random, p: list[str]) -> list[str]:
    """Soft circles and a line on paper (AR03)."""
    shapes = [f'<rect width="{SIZE}" height="{SIZE}" fill="{p[4]}"/>']
    for _ in range(4):
        shapes.append(f'<circle cx="{r.randint(20, 100)}" cy="{r.randint(20, 100)}" r="{r.randint(10, 32)}" '
                      f'fill="{r.choice(p[:4])}" opacity="{r.choice([0.35, 0.5, 0.7])}"/>')
    y1, y2 = r.randint(30, 90), r.randint(30, 90)
    shapes.append(f'<path d="M8 {y1} C40 {y2} 80 {y1} 112 {y2}" stroke="{p[0]}" stroke-width="2" fill="none"/>')
    return shapes


MOTIFS = {"AR01": _bands, "AR02": _blocks, "AR03": _ink}


def svg(artwork_id: str) -> str:
    entry = catalog.ARTWORKS[artwork_id]
    r = _rng(artwork_id)
    shapes = MOTIFS[entry["artist_id"]](r, PALETTES[entry["artist_id"]])
    label = f"{entry['title']}: abstract thumbnail, {catalog.FICTIONAL_NOTE.lower()}"
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {SIZE} {SIZE}" width="{SIZE}" height="{SIZE}" '
            f'role="img" aria-label="{label}">\n<title>{label}</title>\n' + "\n".join(shapes) + "\n</svg>\n")


def main() -> None:
    catalog.ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    for artwork_id in catalog.ARTWORKS:
        (catalog.ASSETS_DIR / f"{artwork_id}.svg").write_text(svg(artwork_id), encoding="utf-8")
        print(f"wrote assets/artworks/{artwork_id}.svg")


if __name__ == "__main__":
    main()
