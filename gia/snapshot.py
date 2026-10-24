"""Recorded investigations for DEMO mode.

save_snapshot() turns a completed LIVE run into a JSON file that contains only:
- the real tool-call trace (tool names, arguments and deterministic tool outputs),
- insights that passed the mandatory publication gate,
- deterministic context (pattern categories and explanations from the tools).
Free text the model wrote outside validated insights (its notes, summary, reasons) and
withheld drafts are left out, so a snapshot never carries unvalidated claims. The file is
scanned for credentials before it is written.

load_snapshot() replays it without any API access, after checking that the data file is
unchanged and re-running the publication gate on every saved insight.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
from pathlib import Path

from gia import explain
from gia.agent import AnalysisResult, TraceStep, publication_gate
from gia.data import DEFAULT_CSV

SNAPSHOT_VERSION = 1
DEFAULT_SNAPSHOT = Path(__file__).resolve().parent.parent / "demo" / "recorded_investigation.json"
SECRET_PATTERNS = [r"sk-ant-[A-Za-z0-9_\-]+", r"(?i)api[_-]?key\s*[:=]", r"(?i)authorization\s*:", r"(?i)bearer\s+\S"]


class SnapshotError(Exception):
    """The snapshot cannot be saved or replayed safely."""


def data_fingerprint(path: Path = DEFAULT_CSV) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _sanitize_step(step: TraceStep) -> dict:
    s = {"step": step.step, "kind": step.kind, "title": step.title, "tool": step.tool,
         "arguments": step.arguments, "detail": step.detail, "result": step.result,
         "duration_ms": step.duration_ms}
    if step.kind == "model_turn":
        s["detail"] = ""                      # model's free-text notes are not validated
    if step.tool == "validate_evidence":
        insight = (step.arguments or {}).get("insight") or {}
        s["arguments"] = {"insight": f"draft insight for {insight.get('artwork_id', '?')}"}
        if isinstance(step.result, dict):
            s["result"] = {"insight_id": step.result.get("insight_id"), "valid": step.result.get("valid"),
                           "error_count": len(step.result.get("errors", []))}
    if step.kind == "gate":                   # withheld drafts' errors may quote unvalidated text: keep only
        subs = (step.result or {}).get("next_step_substitutions", []) if isinstance(step.result, dict) else []
        s["result"] = {"next_step_substitutions": [{"insight_id": x["insight_id"], "policy": x["policy"]}
                                                   for x in subs]}   # the policy codes, never the original text
    return s


def _recorded_followup(f) -> dict:
    """Only grounded, shown answers are recorded; validate_evidence calls (which carry draft text) are
    left out, so an answer that depended on them will simply fail re-verification and not be replayed."""
    return {"question": f.question, "insight_id": f.insight_id, "answer_type": f.answer_type,
            "answer": f.answer, "limitations": f.limitations, "facts": f.facts,
            "tool_calls": [c for c in f.tool_calls if c["tool"] != "validate_evidence"],
            "recorded_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}


def build_snapshot(result: AnalysisResult, followups: list | None = None) -> dict:
    if result.replayed:
        raise SnapshotError("A replayed investigation cannot be recorded again.")
    if result.status != "completed":
        raise SnapshotError(f"Only completed live investigations can be recorded (status: {result.status}).")
    published = [{"insight_id": p["insight_id"], "insight": p["insight"],
                  "next_step_substitution": p.get("next_step_substitution")} for p in result.published]
    not_surfaced = explain.not_surfaced({p["insight"]["artwork_id"] for p in published})
    return {
        "snapshot_version": SNAPSHOT_VERSION,
        "recorded_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "model": result.model,
        "data_file": DEFAULT_CSV.name,
        "data_sha256": data_fingerprint(),
        "tool_calls": result.tool_calls,
        "model_turns": result.model_turns,
        "usage": result.usage,
        "withheld_count": len(result.withheld),
        "published": published,
        "not_surfaced": not_surfaced,
        "trace": [_sanitize_step(s) for s in result.trace],
        "followups": [_recorded_followup(f) for f in (followups or []) if f.shown],
    }


def _check_no_secrets(text: str, api_key: str | None) -> None:
    if api_key and api_key in text:
        raise SnapshotError("Refusing to save: the snapshot contains the API key.")
    for pattern in SECRET_PATTERNS:
        if re.search(pattern, text):
            raise SnapshotError("Refusing to save: the snapshot contains something that looks like a credential.")


def save_snapshot(result: AnalysisResult, path: Path = DEFAULT_SNAPSHOT, api_key: str | None = None,
                  followups: list | None = None) -> Path:
    text = json.dumps(build_snapshot(result, followups), indent=2, default=str)
    _check_no_secrets(text, api_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text + "\n")
    return path


def load_snapshot(path: Path | None = None) -> AnalysisResult:
    """Rebuild a recorded investigation for display. Makes no API calls.

    The file is DEFAULT_SNAPSHOT unless the server-side setting GIA_DEMO_SNAPSHOT names another one."""
    if path is None:
        from gia import config
        path = Path(config.demo_snapshot_path() or DEFAULT_SNAPSHOT)
    if not path.exists():
        raise SnapshotError("No recorded investigation is available yet.")
    snap = json.loads(path.read_text())
    if snap.get("snapshot_version") != SNAPSHOT_VERSION:
        raise SnapshotError("The recorded investigation uses an unsupported format.")
    if snap.get("data_sha256") != data_fingerprint():
        raise SnapshotError("The data file has changed since this investigation was recorded, so it cannot "
                            "be replayed as evidence. Record a new live investigation.")
    published, withheld = publication_gate([p["insight"] for p in snap["published"]])
    if withheld:
        raise SnapshotError("A recorded insight no longer passes evidence validation; replay refused.")
    recorded_subs = {p["insight_id"]: p.get("next_step_substitution") for p in snap["published"]}
    for p in published:   # the saved insight already carries the safe wording; restore the record of the swap
        p["next_step_substitution"] = p["next_step_substitution"] or recorded_subs.get(p["insight_id"])
    result = AnalysisResult(status="completed", model=snap["model"], replayed=True,
                            recorded_at=snap["recorded_at"], tool_calls=snap["tool_calls"],
                            model_turns=snap["model_turns"], usage=snap["usage"])
    result.published = published
    # Explanations are regenerated from the tools, so DEMO and LIVE always show the same deterministic text.
    result.not_surfaced = explain.not_surfaced({p["insight"]["artwork_id"] for p in published})
    result.trace = [TraceStep(**s) for s in snap["trace"]]
    result.withheld_count = snap["withheld_count"]
    # Recorded follow-up answers are re-checked by re-running their deterministic tool calls.
    from gia.followup import reverify_recorded
    examples = [reverify_recorded(f, published) for f in snap.get("followups", [])]
    result.followup_examples = [e for e in examples if e is not None]
    return result
