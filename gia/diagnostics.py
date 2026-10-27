"""Local diagnostics for withheld follow-up answers (Milestone 8).

When the grounding check withholds a LIVE answer, the app appends one JSON line to a git-ignored local
file (diagnostics/withheld_followups.jsonl), so the failure can be investigated later without another
API request. Records are never shown in the app and never committed. Anything that looks like a
credential, and the configured API key itself, is redacted before writing. Writing is best-effort:
a diagnostics problem never affects the app.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from gia import snapshot

FILE_NAME = "withheld_followups.jsonl"
REDACTED = "[REDACTED]"


def _redact(value: Any, api_key: str | None) -> Any:
    if isinstance(value, str):
        if api_key:
            value = value.replace(api_key, REDACTED)
        for pattern in snapshot.SECRET_PATTERNS:
            value = re.sub(pattern, REDACTED, value)
        return value
    if isinstance(value, dict):
        return {k: _redact(v, api_key) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_redact(v, api_key) for v in value]
    return value


def _code_version() -> str | None:
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=Path(__file__).resolve().parent,
                             capture_output=True, text=True, timeout=2)
        return out.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def build_record(f, mode: str, context: str, effort: str | None = None) -> dict:
    """Everything needed to re-check a withheld answer offline: the original response, its declared facts,
    the tool calls (deterministic, so their outputs can be recomputed), the problems and run metadata."""
    return {
        "kind": "withheld_followup",
        "recorded_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "mode": mode, "model": f.model, "effort": effort, "code_version": _code_version(),
        "data_fingerprint": snapshot.data_fingerprint(),
        "question": f.question, "insight_id": f.insight_id, "context_sent": context,
        "answer_type": f.answer_type, "answer": f.answer, "limitations": f.limitations, "facts": f.facts,
        "grounding_problems": f.grounding_errors,
        "tool_calls": f.tool_calls,
        "trace": [{"step": s.step, "kind": s.kind, "title": s.title, "tool": s.tool, "arguments": s.arguments,
                   "detail": s.detail} for s in f.trace],
        "usage": f.usage, "estimated_cost_usd": f.estimated_cost_usd,
    }


def record_withheld(f, mode: str, context: str, api_key: str | None = None, effort: str | None = None,
                    directory: Path | None = None) -> Path | None:
    """Append a record for a withheld LIVE answer. Returns the file written, or None if nothing was written."""
    if f.status != "withheld" or mode != "live" or directory is None:
        return None
    try:
        record = _redact(build_record(f, mode, context, effort), api_key)
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / FILE_NAME
        with path.open("a", encoding="utf-8") as out:
            out.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
        return path
    except Exception:  # diagnostics must never break the app
        return None


def load_records(directory: Path) -> list[dict]:
    path = directory / FILE_NAME
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
