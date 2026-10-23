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

## Secrets

Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and add your Anthropic API key.
That file is git-ignored and must never be committed.

## Source documents (do not modify)

`PRD.md`, `daily_data.csv`, `data_dictionary.md`, `agent_policy.md`, `eval_cases.json`
