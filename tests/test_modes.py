"""LIVE / DEMO mode, recorded snapshots and cost safeguards (no API calls)."""

import json
from pathlib import Path

import anthropic
import pytest
from streamlit.testing.v1 import AppTest

from gia import config, snapshot
from tests.test_agent import FakeClient, a1_insight, final, happy_script, response, text, run

FAKE_KEY = "sk-ant-test-0123456789abcdef"
APP = str(Path(__file__).resolve().parent.parent / "app.py")


# --- Mode configuration ---------------------------------------------------------------

@pytest.mark.parametrize("value,expected", [(None, "demo"), ("demo", "demo"), ("live", "live"),
                                            (" LIVE ", "live"), ("lvie", "demo"), ("", "demo")])
def test_mode_defaults_to_demo(monkeypatch, value, expected):
    monkeypatch.setattr(config, "_setting", lambda name: value if name == "GIA_MODE" else None)
    assert config.mode() == expected


def test_force_demo_overrides_live(monkeypatch):
    settings = {"GIA_MODE": "live", "GIA_FORCE_DEMO": "1"}
    monkeypatch.setattr(config, "_setting", lambda name: settings.get(name))
    assert config.mode() == "demo"


def test_force_demo_beats_secrets_promoted_into_environment(monkeypatch, tmp_path):
    # Reproduces the real failure: Streamlit copies secrets.toml (GIA_MODE="live") into os.environ.
    monkeypatch.setenv("GIA_MODE", "live")
    monkeypatch.setenv("GIA_FORCE_DEMO", "1")
    assert config.mode() == "demo"
    at = AppTest.from_file(APP)
    monkeypatch.setattr(anthropic, "Anthropic", lambda *a, **k: pytest.fail("API client created"))
    at.run(timeout=30)
    assert any("Demo mode" in c.value for c in at.caption)


# --- Snapshots ------------------------------------------------------------------------

def completed_run(**kw):
    script = happy_script()
    script[2].content.insert(0, text("Model note with an unverified claim: 999 people will buy this."))
    script[2].stop_reason = "tool_use"
    bad = a1_insight(artwork_id="B001", title="B1 grew")
    script[-1] = final([a1_insight(), bad])
    result, _ = run(script, **kw)
    return result


def test_snapshot_contains_only_validated_and_deterministic_content(tmp_path):
    result = completed_run()
    assert len(result.published) == 1 and len(result.withheld) == 1
    path = snapshot.save_snapshot(result, tmp_path / "snap.json", api_key=FAKE_KEY)
    blob = path.read_text()
    snap = json.loads(blob)
    assert [p["insight_id"] for p in snap["published"]] == ["INS-A001-SUSTAINED_GROWTH-20261014_20261015"]
    assert "999 people" not in blob                      # model notes are not saved
    assert "B1 grew" not in blob                         # withheld drafts are not saved
    assert "Test summary" not in blob                    # model's free-text summary is not saved
    assert snap["withheld_count"] == 1
    assert [s["tool"] for s in snap["trace"] if s["kind"] == "tool_call"] == [
        "get_processed_data", "detect_engagement_patterns", "compare_daily_metrics", "validate_evidence"]
    assert {n["artwork_id"] for n in snap["not_surfaced"]} == {"A002", "B001", "B002", "C001", "C002"}


def test_snapshot_refuses_credentials(tmp_path):
    result = completed_run()
    tool_step = next(s for s in result.trace if s.kind == "tool_call")
    tool_step.detail = f"leaked {FAKE_KEY}"
    with pytest.raises(snapshot.SnapshotError, match="API key"):
        snapshot.save_snapshot(result, tmp_path / "snap.json", api_key=FAKE_KEY)
    tool_step.detail = "Authorization: Bearer abc"
    with pytest.raises(snapshot.SnapshotError, match="credential"):
        snapshot.save_snapshot(result, tmp_path / "snap.json")


def test_only_completed_live_runs_can_be_recorded(tmp_path):
    result, _ = run([response("refusal")])
    with pytest.raises(snapshot.SnapshotError, match="completed"):
        snapshot.save_snapshot(result, tmp_path / "snap.json")


def test_replay_round_trip_makes_no_api_calls(tmp_path, monkeypatch):
    path = snapshot.save_snapshot(completed_run(), tmp_path / "snap.json")
    monkeypatch.setattr(anthropic, "Anthropic", lambda *a, **k: pytest.fail("API client created in replay"))
    replay = snapshot.load_snapshot(path)
    assert replay.replayed and replay.recorded_at
    assert [p["insight_id"] for p in replay.published] == ["INS-A001-SUSTAINED_GROWTH-20261014_20261015"]
    assert replay.tool_calls == 4


def test_replay_rejects_tampered_insight(tmp_path):
    path = snapshot.save_snapshot(completed_run(), tmp_path / "snap.json")
    snap = json.loads(path.read_text())
    snap["published"][0]["insight"]["metric_changes"][0]["percentage_change"] = 250.0
    path.write_text(json.dumps(snap))
    with pytest.raises(snapshot.SnapshotError, match="no longer passes"):
        snapshot.load_snapshot(path)


def test_replay_rejects_changed_data(tmp_path):
    path = snapshot.save_snapshot(completed_run(), tmp_path / "snap.json")
    snap = json.loads(path.read_text())
    snap["data_sha256"] = "0" * 64
    path.write_text(json.dumps(snap))
    with pytest.raises(snapshot.SnapshotError, match="changed"):
        snapshot.load_snapshot(path)


# --- The app in each mode ---------------------------------------------------------------

def app_with(monkeypatch, settings, snap_path=None):
    monkeypatch.setattr(config, "_setting", lambda name: settings.get(name))
    if snap_path is not None:
        monkeypatch.setattr(snapshot, "DEFAULT_SNAPSHOT", snap_path)
        monkeypatch.setattr(snapshot.load_snapshot, "__defaults__", (snap_path,))
    monkeypatch.setattr(anthropic, "Anthropic", lambda *a, **k: pytest.fail("API client created"))
    return AppTest.from_file(APP).run(timeout=30)


def test_demo_mode_never_creates_api_client_even_with_key(monkeypatch, tmp_path):
    path = snapshot.save_snapshot(completed_run(), tmp_path / "snap.json")
    at = app_with(monkeypatch, {"ANTHROPIC_API_KEY": FAKE_KEY}, path)   # GIA_MODE unset -> demo
    assert not at.exception
    at.button[0].click().run(timeout=30)
    assert not at.exception
    labels = " ".join(i.value for i in at.info)
    assert "Recorded AI investigation" in labels and "not a fresh analysis" in labels
    assert not any("Save this run" in b.label for b in at.button)


def test_demo_mode_without_recording_disables_button(monkeypatch, tmp_path):
    at = app_with(monkeypatch, {}, tmp_path / "missing.json")
    assert at.button[0].disabled
    assert any("No recorded investigation" in c.value for c in at.caption)


def test_live_mode_without_key_is_disabled(monkeypatch):
    at = app_with(monkeypatch, {"GIA_MODE": "live"})
    assert at.button[0].disabled
