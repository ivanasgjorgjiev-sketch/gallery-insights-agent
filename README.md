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

## Secrets

Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and add your Anthropic API key
(needed from Milestone 3). That file is git-ignored. On Streamlit Community Cloud, use the app's Secrets settings.

## Source documents (do not modify)

`PRD.md`, `daily_data.csv`, `data_dictionary.md`, `agent_policy.md`, `eval_cases.json`
