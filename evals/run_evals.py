"""Run the 16-case evaluation.

    .venv/bin/python -m evals.run_evals --mock                       # free: deterministic fixtures, no API
    .venv/bin/python -m evals.run_evals --reuse evals/results/<dir>  # free: re-score a saved live run
    .venv/bin/python -m evals.run_evals --live --approve-paid        # Stage B only, after explicit approval

LIVE makes exactly one analysis run plus one follow-up per follow-up case (8), stops if the total
estimated spend passes --max-total-usd, and saves its raw results so they can be re-scored with
--reuse without new API calls. Results go to evals/results/<timestamp>-<mode>/ (git-ignored):
results.json (every case with checks; human_verdict left empty) and report.md.
"""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import json
import os
import pickle
import sys
from pathlib import Path
from unittest import mock

import anthropic

from evals import cases
from gia import agent, config, followup, review

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "evals" / "results"
FOLLOWUP_CASES = ["TC03", "TC05", "TC07", "TC08", "TC12", "TC13", "TC14", "TC16"]


def questions() -> dict[str, str]:
    by_id = {c["id"]: c for c in cases.load_cases()["tests"]}
    return {cid: cases.question_for(by_id[cid]) for cid in FOLLOWUP_CASES}


# --- Ways to obtain the agent's behaviour -------------------------------------------------------

def mock_run():
    sys.path.insert(0, str(ROOT))
    from tests import fixtures as fx
    makers = {fx.TC03_QUESTION: fx.mock_tc03_followup, cases.TC05_QUESTION: fx.mock_c2_followup,
              fx.BEST_QUESTION: fx.mock_best_followup, fx.CAUSAL_QUESTION: fx.mock_causal_followup,
              fx.PEOPLE_QUESTION: fx.mock_people_followup, fx.TC13_QUESTION: fx.mock_tc13_followup,
              fx.SCOPE_QUESTION: fx.mock_scope_followup, fx.DISCOUNT_QUESTION: fx.mock_discount_followup}
    analysis = fx.mock_three_insight_result()
    missing = set(questions().values()) - set(makers)
    if missing:
        raise SystemExit(f"Mock fixtures do not cover these eval questions verbatim: {missing}")
    return analysis, {q: makers[q]() for q in questions().values()}


def live_run(max_total_usd: float):
    key = config.api_key()
    if not key:
        raise SystemExit("ANTHROPIC_API_KEY is not configured.")
    client = anthropic.Anthropic(api_key=key, max_retries=2, timeout=180)
    model = config.model()
    agent.verify_model(client, model)                          # free metadata check; never switches model
    spent = 0.0
    print(f"Running 1 analysis with {model} …", flush=True)
    analysis = agent.run_analysis(client, model, effort=config.effort(), max_tool_calls=config.max_tool_calls(),
                                  max_output_tokens=config.max_output_tokens(),
                                  max_cost_usd=config.max_cost_per_analysis_usd())
    spent += analysis.estimated_cost_usd or 0
    print(f"  analysis: {analysis.status}, ${spent:.3f} so far", flush=True)
    answers = {}
    for cid, q in questions().items():
        if spent >= max_total_usd:
            print(f"  stopping: total estimated spend ${spent:.2f} reached the ${max_total_usd:.2f} cap", flush=True)
            break
        print(f"  {cid}: asking …", flush=True)
        f = followup.run_followup(client, model, q, analysis.published, effort=config.effort(),
                                  max_tool_calls=config.followup_max_tool_calls(),
                                  max_output_tokens=config.followup_max_output_tokens(),
                                  max_cost_usd=config.followup_max_cost_usd())
        spent += f.estimated_cost_usd or 0
        answers[q] = f
        print(f"  {cid}: {f.status}, ${spent:.3f} so far", flush=True)
    return analysis, answers


def regrade(analysis, answers):
    """Re-check the exact saved answers with the current validation code. No API calls: the model's
    saved output is kept as-is; only the deterministic gate, grounding and tool calls are re-run."""
    from gia import explain
    with mock.patch.object(anthropic, "Anthropic", lambda *a, **k: (_ for _ in ()).throw(
            RuntimeError("regrade must not create an API client"))):
        new = copy.deepcopy(analysis)
        proposed = [p["insight"] for p in analysis.published] + [w["insight"] for w in analysis.withheld]
        new.published, new.withheld = agent.publication_gate(proposed)
        new.not_surfaced = explain.not_surfaced({p["insight"]["artwork_id"] for p in new.published})
        regraded = {}
        for q, f in answers.items():
            g = copy.deepcopy(f)
            outputs = []
            for c in f.tool_calls:
                ok, out = agent.execute_tool(c["tool"], c["arguments"])
                if ok:
                    outputs.append(out)
            if f.answer_type is not None:     # a saved model answer exists; re-check it
                text = "\n".join([f.answer, *f.limitations])
                g.grounding_errors = followup.grounding_check(text, f.answer_type, outputs, new.published, q, f.facts)
                if f.answer_type not in followup.ANSWER_TYPES:
                    g.grounding_errors.append("unknown answer type")
                g.status = "withheld" if g.grounding_errors else "answered"
            regraded[q] = g
    return new, regraded


def write_comparison(run_dir: Path, baseline_dir: Path, results: list[dict]) -> None:
    base = {r["id"]: r for r in json.loads((baseline_dir / "results.json").read_text())["results"]}
    rows = ["# Before / after: saved Stage B answers re-checked (no API calls)", "",
            f"- Baseline (unchanged): `{baseline_dir.name}`", f"- Post-fix re-check: `{run_dir.name}`", "",
            "| Case | Before: automatic | Before: overall | After: automatic | After: overall | Follow-up before → after |",
            "|---|---|---|---|---|---|"]
    for r in results:
        b = base[r["id"]]
        fb = ((b.get("actual_result") or {}).get("followup") or {}).get("status", "—")
        fa = ((r.get("actual_result") or {}).get("followup") or {}).get("status", "—")
        b_overall = b.get("overall_status") or ("Fail" if b["automatic_verdict"] == "Fail" else
                                                "Pending human review" if b["needs_human_review"] else "Pass")
        rows.append(f"| {r['id']} | {b['automatic_verdict']} | {b_overall} | {r['automatic_verdict']} | "
                    f"{r['overall_status']} | {fb} → {fa} |")
    remaining = [r for r in results if r["automatic_verdict"] == "Fail"]
    rows += ["", "## Remaining automatic failures", ""]
    rows += [f"- **{r['id']}**: {r['failure_reason']}" for r in remaining] or ["- None"]
    (run_dir / "comparison.md").write_text("\n".join(rows) + "\n")


# --- App journeys (TC02, TC15): real Streamlit app, API client creation forbidden ------------------

def app_journeys(analysis) -> dict:
    from streamlit.testing.v1 import AppTest

    created = []

    def forbidden(*a, **k):
        created.append(1)
        raise RuntimeError("API client creation is not allowed during evidence review or feedback")

    out = {}
    if not analysis.published:
        return {"TC02": {"note": "no validated insight to review"}, "TC15": {"note": "no validated insight"}}
    target = next((p for p in analysis.published if p["insight"]["artwork_id"] == "A001"), analysis.published[0])
    iid = target["insight_id"]
    with mock.patch.dict(os.environ, {"GIA_FORCE_DEMO": "1"}), mock.patch.object(anthropic, "Anthropic", forbidden):
        at = AppTest.from_file(str(ROOT / "app.py"))
        at.session_state["analysis"] = analysis
        at.run(timeout=60)
        at.button(key=f"evidence-{iid}").click().run(timeout=60)
        text = " ".join(m.value for m in at.markdown)
        evidence_ok = all(s in text for s in ("##### Evidence", "Daily source records", "Key comparison",
                                              "How to read this evidence")) and len(at.dataframe) >= 3
        at.button(key=f"feedback-useful-{iid}").click().run(timeout=60)
        state: review.ReviewState = at.session_state["review"]
        rev = state.reviews[iid]
        successes = [m.value for m in at.success]
        out["TC02"] = {"insight_id": iid, "evidence_insight": iid if rev.evidence_viewed else None,
                       "feedback_insight": iid if rev.feedback else None,
                       "evidence_has_dates_metrics_calculations": evidence_ok, "review_complete": state.complete,
                       "completion_message": next((s for s in successes if "review complete" in s), None),
                       "api_clients_created": len(created), "app_errors": [str(e) for e in at.exception]}
        out["TC15"] = {"insight_id": iid, "feedback": rev.feedback,
                       "not_authorisation_note_shown": any(review.NOT_AUTHORISATION_NOTE in s for s in successes),
                       "api_clients_created": len(created)}
    return out


# --- Reporting ------------------------------------------------------------------------------

def write_report(run_dir: Path, mode: str, analysis, answers, results: list[dict]) -> None:
    total = (analysis.estimated_cost_usd or 0) + sum(f.estimated_cost_usd or 0 for f in answers.values())
    passed = sum(r["automatic_verdict"] == "Pass" for r in results)
    status = {s: sum(r["overall_status"] == s for r in results) for s in ("Pass", "Pending human review", "Fail")}
    usage = {k: analysis.usage[k] + sum(f.usage[k] for f in answers.values()) for k in analysis.usage}
    lines = [f"# Evaluation report ({mode})", "",
             f"- Run: {run_dir.name}",
             f"- Model: {analysis.model} · analysis status: {analysis.status} · "
             f"{analysis.tool_calls} tool calls · {len(answers)} follow-up questions",
             "- Estimated API cost: " + ("n/a (mock: no API calls)" if mode == "mock" else
                                         f"$0 (no new API calls; the original live run cost ${total:.3f})"
                                         if mode in ("regrade", "reuse") else f"${total:.3f}"),
             f"- Tokens: {usage['input_tokens']:,} input, {usage['cache_creation_input_tokens']:,} cache writes, "
             f"{usage['cache_read_input_tokens']:,} cache reads, {usage['output_tokens']:,} output"
             + (" (mock values)" if mode == "mock" else ""),
             f"- Automatic checks: {passed}/{len(results)} cases pass",
             f"- **Overall: {status['Pass']} Pass · {status['Pending human review']} Pending human review · "
             f"{status['Fail']} Fail**", "",
             "| Case | Interaction | Automatic | Overall status | Failed checks | Safety interventions |",
             "|---|---|---|---|---|---|"]
    for r in results:
        failed = ", ".join(c["name"] for c in r["automatic_checks"] if not c["passed"]) or "—"
        lines.append(f"| {r['id']} | {r['interaction']} | {r['automatic_verdict']} | {r['overall_status']} | "
                     f"{failed} | {len(r['safety_interventions']) or '—'} |")
    lines += ["", "## Unresolved risks", "",
              "- Grounding is a transparent heuristic (nearest artwork/metric/date per sentence): unusual phrasing "
              "can be withheld (safe) and subtle misstatements without numbers rely on keyword checks and human review.",
              "- Refusal quality and tone are judged by humans; automatic checks only confirm that no prohibited "
              "claim or action was asserted.",
              "- One live run per case shows behaviour, not consistency; repeat passes are needed to measure variance."]
    if mode == "mock":
        lines.append("- **This is a mock run**: it validates the harness, not the real model.")
    (run_dir / "report.md").write_text("\n".join(lines) + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--mock", action="store_true", help="deterministic fixtures, no API calls")
    group.add_argument("--live", action="store_true", help="real Claude API calls (paid)")
    group.add_argument("--reuse", type=Path, help="re-score a saved run directory, no API calls")
    group.add_argument("--regrade", type=Path, help="re-check the saved answers of a run with the current "
                       "validation code (no API calls) and compare with that run as the baseline")
    ap.add_argument("--approve-paid", action="store_true", help="required with --live")
    ap.add_argument("--max-total-usd", type=float, default=2.00, help="stop live calls past this estimated total")
    args = ap.parse_args(argv)

    if args.live and not args.approve_paid:
        raise SystemExit("--live makes paid API requests; add --approve-paid only after explicit approval.")
    mode = "mock" if args.mock else "live" if args.live else "reuse" if args.reuse else "regrade"
    if args.regrade:
        analysis, answers = regrade(*pickle.loads((args.regrade / "raw_run.pkl").read_bytes()))
    elif args.reuse:
        analysis, answers = pickle.loads((args.reuse / "raw_run.pkl").read_bytes())
    elif args.mock:
        analysis, answers = mock_run()
    else:
        analysis, answers = live_run(args.max_total_usd)

    run_dir = RESULTS / f"{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}-{mode}"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "raw_run.pkl").write_bytes(pickle.dumps((analysis, answers)))
    ctx = cases.EvalContext(analysis=analysis, followups=answers, journeys=app_journeys(analysis))
    results = cases.evaluate(ctx)
    (run_dir / "results.json").write_text(json.dumps({
        "suite": cases.load_cases()["suite"], "mode": mode, "run": run_dir.name, "model": analysis.model,
        "verdict_options": cases.load_cases()["verdict_options"], "results": results}, indent=2, default=str))
    write_report(run_dir, mode, analysis, answers, results)
    if args.regrade:
        write_comparison(run_dir, args.regrade, results)
    passed = sum(r["automatic_verdict"] == "Pass" for r in results)
    shown = run_dir.relative_to(ROOT) if run_dir.is_relative_to(ROOT) else run_dir
    print(f"{passed}/{len(results)} cases pass automatic checks → {shown}/report.md")
    return results


if __name__ == "__main__":
    main()
