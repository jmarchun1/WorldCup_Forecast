# World Cup 2026 LLM Forecasting

A benchmarking project that pits 12+ large language models against each other predicting FIFA World Cup 2026 match scorelines. Final standings, accuracy metrics, and the full forecast archive are published as a live GitHub Pages dashboard.

**[View the live dashboard →](https://jmarchun1.github.io/WorldCup_Forecast/)**

---

## What this does

- Runs every participating LLM (Anthropic, OpenAI, Google, Perplexity) through the same structured match-prediction prompt
- Produces a per-model scoreline forecast (`home_goals–away_goals`) for every WC2026 fixture
- Scores forecasts using a 4/2/1/0 fantasy league system (exact / correct margin / correct result / wrong)
- Tracks cumulative points, Brier score, and cost-per-correct-forecast across all models
- Publishes a sortable leaderboard, per-match forecast grid, and model accuracy breakdown to GitHub Pages after each match day

---

## Scoring system

| Outcome | Points |
|---------|--------|
| Exact scoreline | 4 |
| Correct goal margin (wrong score) | 2 |
| Correct result direction (win/draw/loss) | 1 |
| Wrong result | 0 |

---

## Models tracked

| Short name | Model | Vendor |
|------------|-------|--------|
| `haiku` | Claude Haiku 4.5 | Anthropic |
| `sonnet` | Claude Sonnet 4.6 | Anthropic |
| `opus` | Claude Opus 4.7 | Anthropic |
| `gpt5mini` | GPT-5 Mini | OpenAI |
| `gpt54` | GPT-5.4 | OpenAI |
| `gpt5` | GPT-5 | OpenAI |
| `gem25flashlite` | Gemini 2.5 Flash Lite | Google |
| `gem31flashlite` | Gemini 3.1 Flash Lite | Google |
| `gem25flash` | Gemini 2.5 Flash | Google |
| `gem25pro` | Gemini 2.5 Pro | Google |
| `sonar` | Perplexity Sonar | Perplexity |
| `sonarpro` | Perplexity Sonar Pro | Perplexity |

> **Note on Sonar/SonarPro:** These models have live web search. Forecasts submitted on or after match day are flagged as tainted and excluded from scored comparisons.

---

## Pipeline overview

```
fixtures.py          — fixture list with dates, venues, stages
forecast.py          — prompt each model, write results/forecasts/<match>_<model>.json
recompute_consensus.py — weighted Bayesian consensus across all models
score.py             — score completed matches, write results/scored/<match>.json
build_model_weights.py — inverse-Brier normalized weights → model_weights.json
push_to_pages.py     — inject JSON data into docs/_template.html → WCFCST/index.html
auto_score.py        — orchestrates fetch → score → push (runs on a schedule)
```

---

## Setup

### Prerequisites

- Python 3.11+
- Anthropic API key (env: `ANTHROPIC_API_KEY`)
- OpenAI-compatible gateway for GPT/Gemini/Sonar models (see `litellm_base_url` in config)
- football-data.org API key for live results
- (Optional) Kalshi API key for prediction market odds comparison

### Config

```bash
cp config.example.json config.json
# Fill in your API keys in config.json — this file is gitignored
```

### Run a forecast

```bash
python forecast.py --match "Spain_Argentina_2026-07-19"
python recompute_consensus.py
python score.py
python push_to_pages.py
```

---

## Repository layout

```
forecast.py            — main forecast runner
score.py               — scoring engine
fixtures.py            — all WC2026 fixtures
build_model_weights.py — Bayesian weight calculator
push_to_pages.py       — dashboard builder / GitHub Pages deployer
auto_score.py          — scheduled orchestrator
backtest_prompts.py    — prompt variant backtester
docs/
  _template.html       — dashboard source template
results/
  forecasts/           — per-model forecast JSON files
  scored/              — scored match JSON files
  consensus/           — weighted consensus forecasts
  bonus/               — tournament-level bonus question forecasts
config.example.json    — config template (copy to config.json, fill in keys)
model_weights.json     — current Bayesian model weights
```

---

## Dashboard

The GitHub Pages site at `docs/index.html` (built from `docs/_template.html`) shows:

- **Leaderboard** — sortable by points, Brier score, exact hits, cost
- **Forecasts** — per-match grid of all model predictions vs actual result
- **Model accuracy** — per-model calibration across all scored matches
- **Schedule** — upcoming fixtures with consensus forecasts

---

## Key findings (WC2026, 102 matches)

- LLM aggregate PPG: ~1.05 vs top human forecasters ~1.2–1.4
- Models systematically under-predict draws (~27% of matches); mostly predict 2-0/1-0
- Models over-hedge to 1-1 (most common prediction); 1-0 and 2-1 hit at higher rates
- No positive EV identified vs Kalshi prediction markets (market Brier ~0.48, best model ~0.52)

---

## License

MIT
