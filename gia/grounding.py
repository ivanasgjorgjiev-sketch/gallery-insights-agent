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
# "286 views (40 + 80 + 76 + 90)": a figure followed by its breakdown in brackets
BREAKDOWN = re.compile(r"(\d+(?:\.\d+)?)(?:\s+[A-Za-z\-]+){0,3}\s*\(\s*(\d+(?:\.\d+)?(?:\s*\+\s*\d+(?:\.\d+)?)+)\s*\)")
BOUND_DATE_GAP = re.compile(r"^\s*(?:[A-Za-z\-]+\s+){0,3}?(?:on|for)\s+(?:the\s+)?$", re.IGNORECASE)
# "57 favourites": a metric named right after a number describes that number (lists of several metrics).
BOUND_METRIC_GAP = re.compile(r"^\s*(?:more|fewer|additional|extra|new|total|daily|combined)?\s*$", re.IGNORECASE)
# Date ranges: "Oct 14 to 15", "14–15 October", "between the 14th and 15th", "Oct 14→15", "2026-10-14 to 2026-10-17".
RANGE_WORD = r"(?:to|through|until|till|and|-|–|—|→|->)"
RANGE_GAP = re.compile(rf"^\s*{RANGE_WORD}\s*(?:the\s+)?$", re.IGNORECASE)
BETWEEN = re.compile(r"\bbetween\s+(?:the\s+)?$", re.IGNORECASE)
ORDINAL_DAY = re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)\b")
# A bare day after a dated anchor ("Oct 14 to 15"), unless it reads as a value ("to 15 on ...", "to 15 views").
DAY_AFTER = re.compile(rf"^\s*({RANGE_WORD})\s*(?:the\s+)?(\d{{1,2}})(?:st|nd|rd|th)?\b(?!\s*(?:%|[.,]\d|on\b|for\b))",
                       re.IGNORECASE)
# A bare day before a dated anchor ("from 14 to 15 October", "(14–15 Oct)").
DAY_BEFORE = re.compile(rf"(?:\b(?:from|between|on|over|during)\s+(?:the\s+)?|\()(\d{{1,2}})(?:st|nd|rd|th)?"
                        rf"\s*({RANGE_WORD})\s*(?:the\s+)?$", re.IGNORECASE)
VALUE_ON = re.compile(r"\d\s+(?:on|for)\s+$", re.IGNORECASE)      # "15 on Oct 14": the date belongs to a value
RULE_WORDS = re.compile(r"\b(thresholds?|minimums?|minima|at least|rules?|criteria|criterion|screening)\b",
                        re.IGNORECASE)
# A figure written as a threshold itself: "the +3 minimum", "the minimums are +30%", "the rule of at least 30%".
THRESHOLD_AFTER = re.compile(r"^\s*(?:[A-Za-z\-]+\s+)?(minimums?|thresholds?)\b", re.IGNORECASE)
THRESHOLD_BEFORE = re.compile(r"\b(minimums?|thresholds?|rules?)\s+(?:of|is|are|was|were)\s*(?:at least\s*)?$",
                              re.IGNORECASE)
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


def components(fact: Fact, data: _Data) -> tuple[list[float], set[str]] | None:
    """The figures a verified total is made of, recomputed with the tools, and their subjects:
    an artwork total -> its daily values; an artist total -> its artworks' totals; gallery -> daily views."""
    if fact.measure != "total":
        return None
    if fact.metric == "gallery_views":
        return [float(v) for v in data.gallery_series().values()], {fact.subject}
    if fact.subject in data.artists:
        agg = tools.aggregate_artist_metrics(fact.subject, [fact.metric])["totals"][fact.metric]["per_artwork"]
        return [float(a["total_events"]) for a in agg], {a["artwork_id"] for a in agg}
    if fact.subject in data.artworks and fact.metric in tools.SUMMABLE_METRICS:
        values = list(data.series(fact.subject, fact.metric).values())
        return (None if None in values else [float(v) for v in values]), {fact.subject}
    return None


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


def _dates_in(sentence: str, year: str, fair_dates: frozenset[str] = frozenset()
              ) -> list[tuple[int, str, tuple[int, int]]]:
    """Dates written in a sentence. Day numbers without a month ("the 14th", the 15 in "Oct 14 to 15")
    count as dates only when they name a fair date (processed or excluded) in the anchor's month."""
    found = []
    for m in ISO_DATE.finditer(sentence):
        found.append((m.start(), m.group(0), m.span()))
    anchors = []                                   # (match, iso) for dates written with a month name
    for m in MONTH_DAY.finditer(sentence):
        anchors.append((m, f"{m.group(3) or year}-{MONTHS[m.group(1)[:3].lower()]:02d}-{int(m.group(2)):02d}"))
    for m in DAY_MONTH.finditer(sentence):
        anchors.append((m, f"{m.group(3) or year}-{MONTHS[m.group(2)[:3].lower()]:02d}-{int(m.group(1)):02d}"))
    found += [(m.start(), iso, m.span()) for m, iso in anchors]

    def free(a: int, b: int) -> bool:
        return not any(s < b and a < e for _, _, (s, e) in found)

    def bare(anchor_iso: str, day: str) -> str | None:
        iso = f"{anchor_iso[:8]}{int(day):02d}"
        return iso if iso in fair_dates else None

    for m, iso in anchors:
        after = DAY_AFTER.match(sentence[m.end():])
        if after and not VALUE_ON.search(sentence[:m.start()]) and \
                not METRIC_RE.match(sentence[m.end() + after.end():].lstrip()):
            day_iso = bare(iso, after.group(2))
            a, b = m.end() + after.start(2), m.end() + after.end(2)
            if day_iso and day_iso > iso and free(a, b) and \
                    (after.group(1).lower() != "and" or BETWEEN.search(sentence[:m.start()])):
                found.append((a, day_iso, (a, b)))
        before = DAY_BEFORE.search(sentence[:m.start()])
        if before:
            day_iso = bare(iso, before.group(1))
            a, b = before.start(1), before.end(1)
            if day_iso and day_iso < iso and free(a, b) and \
                    (before.group(2).lower() != "and" or BETWEEN.search(sentence[:a])):
                found.append((a, day_iso, (a, b)))
    if fair_dates:
        month = min(fair_dates)[:8]
        for m in ORDINAL_DAY.finditer(sentence):
            iso = f"{month}{int(m.group(1)):02d}"
            if iso in fair_dates and free(*m.span()):
                found.append((m.start(), iso, m.span()))
    return sorted(found)


def _link_ranges(sentence: str, found: list[tuple[int, str, tuple[int, int]]]) -> list[tuple[int, str | tuple]]:
    """Date mentions for attribution. Two dates joined as a range ("Oct 14 to 15", "between the 14th and
    15th") become one (start, end) mention at both positions; "and" counts only after "between"."""
    mentions: list[tuple[int, str | tuple]] = [(pos, iso) for pos, iso, _ in found]
    for i in range(len(found) - 1):
        (_, iso_a, (sa, ea)), (_, iso_b, (sb, _)) = found[i], found[i + 1]
        gap = sentence[ea:sb]
        if iso_a == iso_b or not RANGE_GAP.match(gap):
            continue
        if gap.strip().lower().startswith("and") and not BETWEEN.search(sentence[:sa]):
            continue
        span = tuple(sorted((iso_a, iso_b)))
        mentions[i], mentions[i + 1] = (mentions[i][0], span), (mentions[i + 1][0], span)
    return mentions


def _date_matches(fact: Fact, date: str | tuple) -> bool:
    """A figure described with a date: a daily value must be on that date (or a range's start or end);
    a change must cover exactly that range; totals cover all processed days."""
    if fact.measure == "total":
        return True
    if isinstance(date, tuple):
        if fact.measure in ("change", "percent_change"):
            return (fact.start_date, fact.end_date) == date
        return fact.start_date in date
    return date in fact.dates()


def _is_rule_value(value: float, is_pct: bool, metric: str | None) -> bool:
    """Whether a figure written next to rule wording is one of the approved screening-rule values, of the
    right kind: a rule percentage; the metric's own minimum change (any metric's when none is named);
    or the number of later days."""
    rules = tools.PATTERN_RULES
    if is_pct:
        return value in {float(rules["min_increase_pct"]), float(rules["support_min_pct"]),
                         rules["min_gain_retained"] * 100, rules["stable_tolerance"] * 100}
    minimums = {m: float(v) for m, v in rules["min_absolute_change"].items()}
    if value == float(rules["min_later_days"]):
        return True
    return value == minimums.get(metric) if metric else value in minimums.values()


def _blank(text: str, spans) -> str:
    chars = list(text)
    for a, b in spans:
        chars[a:b] = " " * (b - a)
    return "".join(chars)


def _nearest(mentions: list[tuple[int, str]], pos: int) -> str | None:
    """Prefer the closest mention before the number; otherwise the closest one after it."""
    before = [m for m in mentions if m[0] < pos]
    if before:
        return max(before, key=lambda m: m[0])[1]
    after = [m for m in mentions if m[0] > pos]
    return min(after, key=lambda m: m[0])[1] if after else None


def check_text(text: str, facts: list[Fact], extra_numbers: set[float] = frozenset(),
               data: _Data | None = None, tool_numbers: set[float] | None = None,
               identifiers: tuple[str, ...] | list[str] = ()) -> list[str]:
    """Problems with numbers in `text` given verified `facts` (empty list = grounded).

    tool_numbers: numbers returned by tools in this question (follow-ups). When given, the parts of a
    written sum must also appear there; insights pass None.
    identifiers: exact internal IDs (e.g. published insight IDs) whose digits are part of a name, not a figure."""
    data = data or _Data()
    year = data.overview["processed_dates"][0][:4]
    subject_pats = _subject_patterns(data)
    problems: list[str] = []
    excluded = {e["date"] for e in data.overview["excluded_dates"]}
    fair_dates = frozenset(data.overview["processed_dates"]) | excluded
    id_pattern = re.compile("|".join(re.escape(i) for i in sorted(set(identifiers), key=len, reverse=True))) \
        if identifiers else None

    for sentence in SENTENCE_SPLIT.split(text):
        if not sentence.strip():
            continue
        if id_pattern:                                    # known insight IDs are names, not evidence
            sentence = _blank(sentence, (m.span() for m in id_pattern.finditer(sentence)))
        dates = _dates_in(sentence, year, fair_dates)
        masked = _blank(sentence, (span for _, _, span in dates))
        masked = ID_TOKEN.sub(lambda m: " " * len(m.group(0)), masked)
        subjects = sorted({(m.start(), sid) for pat, sid in subject_pats for m in pat.finditer(sentence)})
        metrics = [(m.start(), METRIC_OF[m.group(1).lower()]) for m in METRIC_RE.finditer(sentence)]
        date_mentions = _link_ranges(sentence, dates)

        verified_positions: set[int] = set()
        result_measures: dict[int, tuple] = {}            # a written result must be the right kind of figure
        expressions = []                                  # (result value, result pos, [(operand, pos)], all plus)
        for m in SUM_EXPR.finditer(masked):
            ops = [(float(x.group(0)), m.start(1) + x.start()) for x in re.finditer(r"\d+(?:\.\d+)?", m.group(1))]
            signs = re.findall(r"[+−-]", m.group(1))
            total = ops[0][0] + sum(o if sg == "+" else -o for sg, (o, _) in zip(signs, ops[1:]))
            if abs(total - float(m.group(2))) > TOLERANCE:
                problems.append(f"incorrect arithmetic: '{m.group(0)}'")
                continue
            all_plus = all(sg == "+" for sg in signs)
            expressions.append((float(m.group(2)), m.start(2), ops, all_plus))
            result_measures[m.start(2)] = ("total",) if all_plus else ("change",)
        for m in BREAKDOWN.finditer(masked):
            ops = [(float(x.group(0)), m.start(2) + x.start()) for x in re.finditer(r"\d+(?:\.\d+)?", m.group(2))]
            if abs(sum(o for o, _ in ops) - float(m.group(1))) > TOLERANCE:
                problems.append(f"incorrect arithmetic: '{m.group(1)}' is not the sum of '{m.group(2)}'")
                continue
            expressions.append((float(m.group(1)), m.start(1), ops, True))
            result_measures[m.start(1)] = ("total",)

        named = {sid for _, sid in subjects}
        for value, rpos, ops, all_plus in expressions:
            # A written sum is accepted only if its parts are exactly the components of a verified total,
            # recomputed with the tools, seen in this question's tool output, and attributed consistently.
            if not all_plus:
                continue                                  # differences: every number is checked on its own below
            subj, metric = _nearest(subjects, rpos), _nearest(metrics, rpos)
            for fact in (f for f in facts if f.measure == "total" and abs(f.value - value) <= TOLERANCE):
                comp = components(fact, data)
                if not comp or sorted(o for o, _ in ops) != sorted(comp[0]):
                    continue
                if tool_numbers is not None and not all(o in tool_numbers for o, _ in ops):
                    continue
                if metric and metric != fact.metric:
                    continue
                parts_subjects = comp[1]
                if subj and subj != fact.subject and not (subj in parts_subjects and parts_subjects <= named):
                    continue
                verified_positions.add(rpos)
                verified_positions.update(pos for _, pos in ops)
                break

        for m in NUMBER.finditer(masked):
            raw, value, is_pct = m.group(0).strip(), float(m.group(2)), bool(m.group(3))
            pos = m.start(2)
            after = masked[m.end():m.end() + 16].lower()
            before = masked[max(0, m.start() - 6):m.start()].lower()
            if pos in verified_positions:
                continue
            if not is_pct and value == int(value) and 1 <= value <= 7 and (
                    "day" in before or re.match(r"\s*(processed )?(fair )?days?\b", after)):
                continue                                  # "Day 2", "4 processed days"
            if value == float(year) or (not is_pct and value == 100 and re.search(r"[×x*]\s*$", before)):
                continue
            # "416 artwork views, 57 favourites and 3 inquiries": a metric named right after the number is its own.
            bound_metric = next((met for mpos, met in metrics if mpos >= m.end()
                                 and BOUND_METRIC_GAP.match(sentence[m.end():mpos])), None)
            metric = bound_metric or _nearest(metrics, pos)
            # Screening-rule figures. A figure written as a threshold ("the +3 minimum") must be an approved rule
            # value. Otherwise a rule value is exempt only in a sentence about rules, of the right kind (a rule
            # percentage, the metric's own minimum, the number of later days) and before any artwork or artist
            # is named, so "By the rules, A2's favourites rose by 3" is still checked as A2's data.
            if THRESHOLD_AFTER.match(sentence[m.end():]) or THRESHOLD_BEFORE.search(sentence[:m.start()]):
                if not _is_rule_value(value, is_pct, metric):
                    problems.append(f"'{raw}' is not an approved screening-rule value")
                continue
            if RULE_WORDS.search(sentence) and _is_rule_value(value, is_pct, metric) \
                    and not any(spos < m.start() for spos, _ in subjects):
                continue
            if value in extra_numbers:
                continue

            subject = _nearest(subjects, pos)
            # "13 on 2026-10-17": a date introduced by on/for right after the number belongs to it.
            bound = next((iso for dpos, iso in date_mentions if dpos >= m.end()
                          and BOUND_DATE_GAP.match(sentence[m.end():dpos])), None)
            date = bound or _nearest(date_mentions, pos)
            off_days = sorted(set(date if isinstance(date, tuple) else (date,)) & excluded) if date else []
            measures = ("percent_change",) if is_pct else result_measures.get(pos, ("value", "change", "total"))
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
            if off_days:
                problems.append(f"'{raw}' is described for the excluded date {off_days[0]}")
            elif date:
                narrowed = [f for f in candidates if _date_matches(f, date)]
                if not narrowed:
                    described = " to ".join(date) if isinstance(date, tuple) else date
                    problems.append(f"'{raw}' is described for {described} but the verified figure is for "
                                    f"{', '.join(sorted({d for f in candidates for d in f.dates()}))}")
                    continue
    return problems
