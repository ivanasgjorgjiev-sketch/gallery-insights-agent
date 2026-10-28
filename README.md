# Gallery Insights Agent (course prototype)

Demonstration prototype using **synthetic data** only. Built for the Product Faculty AI PM course.

## Run locally (macOS)

```bash
cd ~/Documents/gallery-insights-agent
source .venv/bin/activate
streamlit run app.py
```

The app opens at http://localhost:8501. Stop it with `Ctrl+C` in the terminal.

## Run the automated tests

```bash
.venv/bin/python -m pytest -v
```

## First-time setup

```bash
/opt/homebrew/bin/python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Modes (`GIA_MODE`, server-side only)

| Mode | What "Analyze Daily Engagement" does | API calls |
|---|---|---|
| `demo` (default) | Replays the recorded live investigation in `demo/recorded_investigation.json`, clearly labelled | None, ever |
| `live` | Runs a genuine Claude tool-calling investigation | Yes, within the limits below |

The public deployment must stay in `demo` mode (leave `GIA_MODE` unset there and add no API key).

Live-mode safeguards: max 15 tool calls and 12 model turns per analysis, max 8,000 output tokens per
response, analysis stops once estimated spend passes $0.75, max 5 analyses per browser session.
All are configurable (`GIA_MAX_TOOL_CALLS`, `GIA_MAX_OUTPUT_TOKENS`, `GIA_MAX_COST_PER_ANALYSIS_USD`,
`GIA_MAX_ANALYSES_PER_SESSION`). Also set a spend limit in the Anthropic Console.

## Guided insight exploration (Milestone 8)

Each validated insight card offers four questions: *What makes this insight worth my attention?*,
*How did engagement evolve over the fair?*, *What other signals support—or challenge—this pattern?* and
*What should I look into next?* The answers are deterministic: built from the insight's verified data with the
analytical tools, identical in both modes, and checked before display. Opening them makes no API call. See
`M8_DECISIONS.md` and `evals/M8_EVALUATION.md`.

**Milestone 9 interface:** each card shows the key change, labelled supporting measures, a small chart of
daily artwork views (processed days only) and one validated sentence. *Explore insight* opens the four
questions (collapsed); *View evidence* shows a short summary first, with calculations, checks and source
records on demand. See `M9_DECISIONS.md`.

**Milestone 10 manager experience:** a daily briefing above the cards (published insights, artworks not
prioritised and drafts withheld by validation, kept apart), plain-language evidence ratings (technical terms in
tooltips and the evidence), a suggested follow-up per insight (approved templates, no action taken), and a
fictional sample catalog with abstract thumbnails (`gia/catalog.py`, `assets/artworks/`, regenerated with
`python scripts/make_artwork_thumbnails.py`). All of it is built from the validated results, checked before
display and makes no API call; the analysis still uses only the source IDs. See `M10_DECISIONS.md`.

Open-ended follow-up questions are not part of the MVP. Their implementation is kept and can be shown again
locally with `GIA_ENABLE_FOLLOWUPS=1`; never set it on the public deployment. When they are on, any answer
withheld in LIVE mode is recorded for offline investigation in the git-ignored `diagnostics/` folder.

## Secrets

Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and add your Anthropic API key.
That file is git-ignored and must never be committed.

## Source documents (do not modify)

`PRD.md`, `daily_data.csv`, `data_dictionary.md`, `agent_policy.md`, `eval_cases.json`
