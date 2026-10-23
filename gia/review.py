"""Evidence-review and usefulness-feedback state for one analysis (Milestone 5).

Pure Python, no Streamlit and no API calls. The app keeps one ReviewState per displayed analysis
in st.session_state, so feedback lasts only for the current browser session (MVP decision).

Feedback is evaluation data about the agent's insight. It never authorises or triggers any action.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

FEEDBACK_OPTIONS = {
    "useful": "Useful / Worth investigating",
    "not_useful": "Not useful",
}
NOT_AUTHORISATION_NOTE = ("Feedback helps evaluate the agent's insights. It does not approve, authorise or "
                          "trigger any action. Nothing is sent or changed.")
SESSION_ONLY_NOTE = "Feedback is kept for this browser session only; it is not saved permanently."


class ReviewError(ValueError):
    """An evidence view or feedback could not be recorded (unknown insight or option)."""


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


@dataclass
class InsightReview:
    evidence_viewed_at: str | None = None
    feedback: str | None = None          # a key of FEEDBACK_OPTIONS
    feedback_at: str | None = None

    @property
    def evidence_viewed(self) -> bool:
        return self.evidence_viewed_at is not None


@dataclass
class ReviewState:
    """Review progress for the validated insights of one analysis."""

    analysis_key: str                      # identifies the analysis these insights belong to
    insight_ids: list[str]                 # validated (published) insight IDs, in display order
    reviews: dict[str, InsightReview] = field(default_factory=dict)

    def __post_init__(self):
        for insight_id in self.insight_ids:
            self.reviews.setdefault(insight_id, InsightReview())

    def _review(self, insight_id: str) -> InsightReview:
        if insight_id not in self.reviews:
            raise ReviewError(f"'{insight_id}' is not a validated insight in this analysis.")
        return self.reviews[insight_id]

    def record_evidence_view(self, insight_id: str) -> None:
        review = self._review(insight_id)
        if review.evidence_viewed_at is None:      # keep the first time it was opened
            review.evidence_viewed_at = _now()

    def record_feedback(self, insight_id: str, option: str) -> None:
        if option not in FEEDBACK_OPTIONS:
            raise ReviewError(f"Unknown feedback option '{option}'. Use one of {list(FEEDBACK_OPTIONS)}.")
        review = self._review(insight_id)
        review.feedback, review.feedback_at = option, _now()   # the latest choice counts

    def completed_ids(self) -> list[str]:
        """Insights whose evidence was viewed AND that received feedback (the same insight)."""
        return [i for i in self.insight_ids if self.reviews[i].evidence_viewed and self.reviews[i].feedback]

    @property
    def complete(self) -> bool:
        return bool(self.completed_ids())

    def progress(self) -> dict:
        viewed = sum(r.evidence_viewed for r in self.reviews.values())
        rated = sum(r.feedback is not None for r in self.reviews.values())
        useful = sum(r.feedback == "useful" for r in self.reviews.values())
        return {"insights": len(self.insight_ids), "evidence_viewed": viewed, "rated": rated,
                "useful": useful, "complete": self.complete, "completed_ids": self.completed_ids()}


def start_review(result) -> ReviewState:
    """Fresh review state for a newly displayed analysis (each Analyze click starts a new review)."""
    import uuid
    return ReviewState(analysis_key=uuid.uuid4().hex, insight_ids=[p["insight_id"] for p in result.published])
