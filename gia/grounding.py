"""Claim-level grounding (Milestone 7).

Two deterministic steps decide whether text may be shown as fact:

1. verify_fact(): every structured fact (subject, metric, date(s), measure, value) is recomputed
   with the analytical tools and must match exactly.
2. check_text(): every number written in the text must correspond to a verified fact *in context*:
   the nearest subject (artwork/artist), metric and date mentioned in the same sentence must agree
   with the fact, a "%" must be a verified percentage change, and written sums must add up.
   Reusing a valid number for the wrong artwork, metric or date therefore fails.

This is a transparent heuristic, not natural-language understanding: it is designed to fail safe
(withhold) when wording is ambiguous, and it is backed by human review in evaluations.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from gia import tools

METRICS = ["artwork_views", "unique_artwork_viewers", "favourites", "inquiries", "gallery_views"]
MEASURES = ["value", "missing", "change", "percent_change", "total"]
TOLERANCE = 0.1

# Longest phrases first so "gallery views" wins over "views" and "unique viewers" over "viewers".
METRIC_PHRASES = [
    ("gallery-profile views", "gallery_views"), ("gallery profile views", "gallery_views"),
    ("gallery views", "gallery_views"), ("daily unique viewers", "unique_artwork_viewers"),
    ("unique artwork viewers", "unique_artwork_viewers"), ("unique viewers", "unique_artwork_viewers"),
    ("artwork-view events", "artwork_views"), ("artwork view events", "artwork_views"),
    ("artwork views", "artwork_views"), ("view events", "artwork_views"), ("viewers", "unique_artwork_viewers"),
    ("views", "artwork_views"), ("viewed", "artwork_views"), ("favourites", "favourites"),
    ("favorites", "favourites"), ("favourite", "favourites"), ("inquiries", "inquiries"), ("inquiry", "inquiries"),
]
METRIC_RE = re.compile(r"\b(" + "|".join(re.escape(p) for p, _ in METRIC_PHRASES) + r")\b", re.IGNORECASE)
METRIC_OF = {p: m for p, m in METRIC_PHRASES}

MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct",
                                       "nov", "dec"], start=1)}
ISO_DATE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
MONTH_DAY = re.compile(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.? (\d{1,2})(?:st|nd|rd|th)?"
                       r"(?:, (\d{4}))?\b")
DAY_MONTH = re.compile(r"\b(\d{1,2}) (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?(?: (\d{4}))?\b")
ID_TOKEN = re.compile(r"\b[A-Z]+\d+\b")
NUMBER = re.compile(r"(?<![\w.])([+\-−]?)(\d+(?:\.\d+)?)(\s?%)?")
SUM_EXPR = re.compile(r"(\d+(?:\.\d+)?(?:\s*[+−-]\s*\d+(?:\.\d+)?)+)\s*=\s*(\d+(?:\.\d+)?)")
RULE_WORDS = re.compile(r"\b(threshold|minimum|at least|rule|criteria|criterion|screening)\b", re.IGNORECASE)
SENTENCE_SPLIT = re.compile(r"(?<=[.!?;])\s+|\n+")
AGGREGATE_WORDS = re.compile(r"\b(combined|in total|total|together|altogether|across both|overall)\b", re.IGNORECASE)


@dataclass
class Fact:
    subject: str            # artwork ID (A001), artist ID (AR01) or gallery ID (G001)
    metric: str
    measure: str            # value | missing | change | percent_change | total
    value: float
    start_date: str = ""    # value/missing: the date; change/percent_change: first date
    end_date: str = ""      # change/percent_change: second date
    context_dates: tuple = ()   # extra dates the value may be described with (e.g. a comparison's period)

    def dates(self) -> set[str]:
        return {d for d in (self.start_date, self.end_date, *self.context_dates) if d}


def fact_from_dict(d: dict) -> Fact:
    return Fact(subject=str(d.get("subject", "")), metric=str(d.get("metric", "")),
                measure=str(d.get("measure", "")), value=float(d.get("value") or 0),
                start_date=str(d.get("start_date") or ""), end_date=str(d.get("end_date") or ""))


# --- Step 1: verify facts against the tools ---------------------------------------------

class _Data:
    """Small per-check cache of tool results."""

    def __init__(self):
        self.overview = tools.get_processed_data()
        self.artworks = {a["artwork_id"]: a for a in self.overview["artworks"]}
        self.artists = {a["artist_id"]: a["artist_name"] for a in self.overview["artworks"]}
        self._metrics: dict[str, dict] = {}

    def series(self, artwork_id: str, metric: str) -> dict[str, int | None]:
        if artwork_id not in self._metrics:
            self._metrics[artwork_id] = tools.get_artwork_metrics(artwork_id)["metrics"]
        return {d["date"]: d["value"] for d in self._metrics[artwork_id][metric]["daily"]}

    def gallery_series(self) -> dict[str, int]:
        return {d["date"]: d["gallery_views"] for d in self.overview["gallery_profile_views"]["daily"]}


def verify_fact(fact: Fact, data: _Data | None = None) -> str | None:
    """Return None if the fact matches the source data, else the reason it does not."""
    data = data or _Data()
    label = f"{fact.subject} {fact.metric} {fact.measure}"
    if fact.metric not in METRICS or fact.measure not in MEASURES:
        return f"{label}: unknown metric or measure"
    for d in (fact.start_date, fact.end_date):
        if d and d in data.overview["processed_dates"]:
            continue
        if d and d in [e["date"] for e in data.overview["excluded_dates"]]:
            return f"{label}: {d} is excluded (day_processed=false) and cannot be used"
        if d:
            return f"{label}: {d} is not a processed fair date"

    is_gallery = fact.metric == "gallery_views"
    if is_gallery and fact.subject != data.overview["gallery_id"]:
        return f"{label}: gallery views belong to {data.overview['gallery_id']}"
    if not is_gallery and fact.subject not in data.artworks and fact.subject not in data.artists:
        return f"{label}: unknown subject {fact.subject}"
    if fact.subject in data.artists and fact.measure != "total":
        return f"{label}: artist-level facts can only be totals"

    def series():
        return data.gallery_series() if is_gallery else data.series(fact.subject, fact.metric)

    if fact.measure in ("value", "missing"):
        if not fact.start_date:
            return f"{label}: a daily value needs its date"
        actual = series()[fact.start_date]
        if fact.measure == "missing":
            return None if actual is None else f"{label}: the value on {fact.start_date} is {actual}, not missing"
        if actual is None:
            return f"{label}: the value on {fact.start_date} is not recorded (unknown, not {fact.value:g})"
        return None if actual == fact.value else f"{label}: source gives {actual}, not {fact.value:g}"

    if fact.measure in ("change", "percent_change"):
        if not (fact.start_date and fact.end_date) or fact.start_date >= fact.end_date:
            return f"{label}: a change needs two processed dates in order"
        s = series()
        cmp = tools.compare_values(s[fact.start_date], s[fact.end_date])
        if cmp["status"] == "unavailable":
            return f"{label}: comparison unavailable because a value is not recorded"
        if fact.measure == "change":
            return None if cmp["absolute_change"] == fact.value else \
                f"{label}: source change is {cmp['absolute_change']}, not {fact.value:g}"
        if cmp["percentage_change"] is None:
            return f"{label}: percentage change is undefined from a zero baseline"
        return None if abs(abs(cmp["percentage_change"]) - abs(fact.value)) <= TOLERANCE else \
            f"{label}: source percentage is {cmp['percentage_change']}, not {fact.value:g}"

    # total over the processed days
    if fact.metric == "unique_artwork_viewers":
        return f"{label}: daily unique viewers cannot be totalled (they are not distinct people)"
    if is_gallery:
        actual = data.overview["gallery_profile_views"]["total"]
    elif fact.subject in data.artists:
        actual = tools.aggregate_artist_metrics(fact.subject, [fact.metric])["totals"][fact.metric]["artist_total_events"]
    else:
        actual = sum(v for v in series().values())
    return None if actual == fact.value else f"{label}: source total is {actual}, not {fact.value:g}"


def facts_from_insight(insight: dict) -> list[Fact]:
    """Structured facts implied by an insight's metric_changes and metric_totals."""
    facts = []
    for c in insight.get("metric_changes") or []:
        a, m, d1, d2 = c.get("artwork_id"), c.get("metric"), c.get("old_date"), c.get("new_date")
        period = (d1, d2)
        if c.get("old_value") is not None:
            facts.append(Fact(a, m, "value", c["old_value"], d1, context_dates=period))
        if c.get("new_value") is not None:
            facts.append(Fact(a, m, "value", c["new_value"], d2, context_dates=period))
        if c.get("absolute_change") is not None:
            facts.append(Fact(a, m, "change", c["absolute_change"], d1, d2))
        if c.get("percentage_change") is not None:
            facts.append(Fact(a, m, "percent_change", c["percentage_change"], d1, d2))
    for t in insight.get("metric_totals") or []:
        facts.append(Fact(t.get("id"), t.get("metric"), "total", t.get("total") or 0))
    return facts


# --- Step 2: check every number in the text, in context ------------------------------------

def _subject_patterns(data: _Data) -> list[tuple[re.Pattern, str]]:
    pats = []
    for artwork_id, a in data.artworks.items():
        short = a["artwork_title"].split()[-1]                    # "Artwork A1" -> "A1"
        for text in (a["artwork_title"], artwork_id, short):
            pats.append((re.compile(rf"\b{re.escape(text)}\b", re.IGNORECASE if " " in text else 0), artwork_id))
    for artist_id, name in data.artists.items():
        for text in (name, artist_id):
            pats.append((re.compile(rf"\b{re.escape(text)}\b(?!\w)", re.IGNORECASE if " " in text else 0), artist_id))
    pats.append((re.compile(rf"\b{data.overview['gallery_id']}\b"), data.overview["gallery_id"]))
    return pats


def _dates_in(sentence: str, year: str) -> list[tuple[int, str, tuple[int, int]]]:
    found = []
    for m in ISO_DATE.finditer(sentence):
        found.append((m.start(), m.group(0), m.span()))
    for m in MONTH_DAY.finditer(sentence):
        found.append((m.start(), f"{m.group(3) or year}-{MONTHS[m.group(1)[:3].lower()]:02d}-{int(m.group(2)):02d}",
                      m.span()))
    for m in DAY_MONTH.finditer(sentence):
        found.append((m.start(), f"{m.group(3) or year}-{MONTHS[m.group(2)[:3].lower()]:02d}-{int(m.group(1)):02d}",
                      m.span()))
    return found


def _nearest(mentions: list[tuple[int, str]], pos: int) -> str | None:
    """Prefer the closest mention before the number; otherwise the closest one after it."""
    before = [m for m in mentions if m[0] < pos]
    if before:
        return max(before, key=lambda m: m[0])[1]
    after = [m for m in mentions if m[0] > pos]
    return min(after, key=lambda m: m[0])[1] if after else None


def check_text(text: str, facts: list[Fact], extra_numbers: set[float] = frozenset(),
               data: _Data | None = None) -> list[str]:
    """Problems with numbers in `text` given verified `facts` (empty list = grounded)."""
    data = data or _Data()
    year = data.overview["processed_dates"][0][:4]
    subject_pats = _subject_patterns(data)
    rule_values = {float(tools.PATTERN_RULES[k]) for k in ("min_increase_pct", "support_min_pct", "min_later_days")}
    rule_values |= {float(v) for v in tools.PATTERN_RULES["min_absolute_change"].values()}
    rule_values |= {tools.PATTERN_RULES["min_gain_retained"] * 100, tools.PATTERN_RULES["stable_tolerance"] * 100}
    problems: list[str] = []
    excluded = {e["date"] for e in data.overview["excluded_dates"]}

    for sentence in SENTENCE_SPLIT.split(text):
        if not sentence.strip():
            continue
        dates = _dates_in(sentence, year)
        masked = list(sentence)
        for _, _, (a, b) in dates:
            masked[a:b] = " " * (b - a)
        masked = "".join(masked)
        masked = ID_TOKEN.sub(lambda m: " " * len(m.group(0)), masked)
        subjects = sorted({(m.start(), sid) for pat, sid in subject_pats for m in pat.finditer(sentence)})
        metrics = [(m.start(), METRIC_OF[m.group(1).lower()]) for m in METRIC_RE.finditer(sentence)]
        date_mentions = [(pos, iso) for pos, iso, _ in dates]

        sums, sum_parts = {}, set()
        for m in SUM_EXPR.finditer(masked):
            sum_parts.update(range(m.start(1), m.end(1)))
            parts = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", m.group(1))]
            signs = re.findall(r"[+−-]", m.group(1))
            total = parts[0] + sum(p if s == "+" else -p for s, p in zip(signs, parts[1:]))
            if abs(total - float(m.group(2))) > TOLERANCE:
                problems.append(f"incorrect arithmetic: '{m.group(0)}'")
            sums[m.start(2)] = True                 # a correct written sum's result is checked by the sum itself

        for m in NUMBER.finditer(masked):
            raw, value, is_pct = m.group(0).strip(), float(m.group(2)), bool(m.group(3))
            pos = m.start(2)
            after = masked[m.end():m.end() + 16].lower()
            before = masked[max(0, m.start() - 6):m.start()].lower()
            if pos in sums:
                continue
            if not is_pct and value == int(value) and 1 <= value <= 7 and (
                    "day" in before or re.match(r"\s*(processed )?(fair )?days?\b", after)):
                continue                                  # "Day 2", "4 processed days"
            if value == float(year) or (not is_pct and value == 100 and re.search(r"[×x*]\s*$", before)):
                continue
            if value in rule_values and RULE_WORDS.search(sentence):
                continue
            if value in extra_numbers:
                continue

            subject = _nearest(subjects, pos)
            metric = _nearest(metrics, pos)
            date = _nearest(date_mentions, pos)
            measures = ("percent_change",) if is_pct else ("value", "change", "total")
            candidates = [f for f in facts if f.measure in measures and abs(abs(f.value) - value) <= (
                TOLERANCE if is_pct else 0)]
            if not candidates:
                kind = "percentage change" if is_pct else "value"
                problems.append(f"'{raw}' is not a verified {kind}")
                continue
            if metric and metric != "gallery_views":
                narrowed = [f for f in candidates if f.metric == metric]
                if not narrowed:
                    problems.append(f"'{raw}' is described as {metric} but the verified figure is for "
                                    f"{', '.join(sorted({f.metric for f in candidates}))}")
                    continue
                candidates = narrowed
            if subject and not (metric == "gallery_views"):
                allowed = {subject}
                if pos in sum_parts and subject in data.artists:   # parts of an artist total = its artworks
                    allowed |= {a for a, info in data.artworks.items() if info["artist_id"] == subject}
                if AGGREGATE_WORDS.search(masked[max(0, m.start() - 25):m.end() + 25]):
                    # "...: 416 combined view events" -> a total for anyone named in the sentence (or their artist)
                    named = {sid for _, sid in subjects}
                    allowed |= named | {data.artworks[a]["artist_id"] for a in named if a in data.artworks}
                    candidates = [f for f in candidates if f.measure == "total"] or candidates
                narrowed = [f for f in candidates if f.subject in allowed]
                if not narrowed:
                    problems.append(f"'{raw}' is attributed to {subject} but the verified figure belongs to "
                                    f"{', '.join(sorted({f.subject for f in candidates}))}")
                    continue
                candidates = narrowed
            if date and date not in excluded:
                narrowed = [f for f in candidates if f.measure == "total" or date in f.dates()]
                if not narrowed:
                    problems.append(f"'{raw}' is described for {date} but the verified figure is for "
                                    f"{', '.join(sorted(d for f in candidates for d in f.dates()))}")
                    continue
            elif date in excluded:
                problems.append(f"'{raw}' is described for the excluded date {date}")
    return problems
