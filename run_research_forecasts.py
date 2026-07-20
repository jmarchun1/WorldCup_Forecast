"""
run_research_forecasts.py — Prompt B (no market odds).

Runs all remaining unscored matches through every model using a prompt
that deliberately withholds bookmaker/market odds. This produces a clean
condition for the A/B comparison in the paper:

  Condition A: standard prompt (includes market odds)  → results/forecasts/
  Condition B: this script (no market odds)            → results/forecasts_research/

Brier and directional accuracy compared across both conditions answers:
  "How much forecasting value do LLMs add beyond simply echoing the market?"
"""

import json
import os
import sys
import re
from datetime import date
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from forecast import (
    _call_model, _extract_json, _forecast_one,
    WC_BASE_RATE_PRIOR, WC2026_INJURIES, WC2026_TILT,
    _get_dead_rubber_context, _get_base_rate_prior, _get_draw_reminder,
    FORECASTS_DIR,
)

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
RESEARCH_DIR = os.path.join(BASE_DIR, "results", "forecasts_research")
os.makedirs(RESEARCH_DIR, exist_ok=True)

CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
with open(CONFIG_PATH, encoding="utf-8") as f:
    CONFIG = json.load(f)


def build_research_prompt(match_data: dict) -> str:
    """Prompt B — identical context to Prompt A except market odds are omitted.
    This is the clean research condition for the LLM-value paper.
    """
    home       = match_data["home"]
    away       = match_data["away"]
    stage      = match_data["stage"]
    venue      = match_data["venue"]
    match_date = match_data["date"]
    context    = match_data.get("context", "")
    today      = date.today().isoformat()

    # Strip any odds/implied probability lines from context blob
    # (Sonar sometimes injects them into the context field)
    cleaned_context = "\n".join(
        line for line in (context or "").splitlines()
        if not re.search(r"implied|decimal odds|bookmaker|kalshi|win odds|draw odds", line, re.I)
    )

    lines = [
        f"You are a football/soccer analyst. Today is {today}.",
        "",
        f"Match: {home} vs {away}",
        f"Stage: {stage} — {venue}",
        f"Match date: {match_date}",
        "",
        "=== HISTORICAL BASE RATES ===",
        _get_base_rate_prior(stage),
        "",
        "=== KEY INJURY ABSENCES (WC 2026) ===",
        WC2026_INJURIES,
        "",
    ]

    home_tilt = WC2026_TILT.get(home)
    away_tilt = WC2026_TILT.get(away)
    if home_tilt or away_tilt:
        lines += ["=== TEAM STYLE (PELE TILT RATINGS) ==="]
        if home_tilt:
            lines.append(f"  {home}: {home_tilt[1]}")
            if len(home_tilt) > 2:
                lines.append(f"  {home} draw rate (last 20 competitive matches): ~{home_tilt[2]:.0%}")
        if away_tilt:
            lines.append(f"  {away}: {away_tilt[1]}")
            if len(away_tilt) > 2:
                lines.append(f"  {away} draw rate (last 20 competitive matches): ~{away_tilt[2]:.0%}")
        lines.append("")

    # NOTE: === CURRENT BOOKMAKER ODDS === section intentionally omitted

    lines += [
        "=== MATCH CONTEXT (FORM, HEAD-TO-HEAD) ===",
        cleaned_context or "No additional context available.",
        "",
    ]

    dead_rubber = _get_dead_rubber_context(match_data)
    if dead_rubber:
        lines += [dead_rubber, ""]

    lines += [
        "=== PREDICTION REQUEST ===",
        f"Predict the final score for {home} vs {away}.",
        "",
        "Provide:",
        "- home_goals: integer goals for home team",
        "- away_goals: integer goals for away team",
        "- home_win_prob: your probability 0.0-1.0 that home team wins",
        "- draw_prob: your probability 0.0-1.0 of a draw",
        "- away_win_prob: your probability 0.0-1.0 that away team wins",
        "- confidence: your confidence 0-100",
        "- reasoning: 2-3 sentences",
        "",
        "Probabilities must sum to 1.0.",
        _get_draw_reminder(stage),
        "",
        "=== CALIBRATION INSTRUCTIONS ===",
        "IMPORTANT — before finalising your prediction, apply these checks:",
        "",
        "1. GOAL VOLUME: Does home_goals + away_goals fall between 2.0 and 4.5? "
        "WC2026 matches average 2.9 goals. If your total is below 2.0, reconsider unless specific "
        "context (elite defences, dead rubber) justifies it. Under-predicting goals is the "
        "single most common AI forecasting error in this tournament.",
        "",
        "2. SCORE ATTRACTOR CHECK: The score 1-1 is predicted by AI models at 2x its actual "
        "base rate. Do not predict 1-1 as a default hedge — only predict it when the match "
        "context specifically points to a draw between evenly-matched teams.",
        "",
        "3. UPSET BASELINE: Before committing to the favourite, state the underdog win base rate. "
        f"When the favourite's implied probability is 60-70%, underdogs still win ~22% of the time. "
        "What specific factors in this match push that rate above or below the base rate? "
        "Your away_win_prob and draw_prob must reflect a genuine assessment of this.",
        "",
        "4. MINORITY SCENARIO: In 2-3 sentences, describe the most plausible path to an underdog "
        "win or surprise draw. Then ask yourself: do your probabilities reflect the existence of "
        "this plausible path? Include this reasoning in your 'reasoning' field.",
        "",
        "5. BRIER SCORING: Your probabilities are evaluated by Brier score, which penalises "
        "overconfidence heavily. Assign at least 10% probability to every outcome unless there "
        "is an overwhelming structural reason to exclude it (e.g., team forfeiture).",
        "",
        f"State your predicted scoreline in your reasoning as: 'Predicted score: X-Y'. Then output the JSON.",
        "",
        "Respond ONLY with valid JSON:",
        json.dumps({
            "home_goals": 0,
            "away_goals": 0,
            "home_win_prob": 0.0,
            "draw_prob": 0.0,
            "away_win_prob": 0.0,
            "confidence": 0,
            "reasoning": "...",
        }, indent=2),
    ]
    return "\n".join(lines)


def get_remaining_matches() -> list[dict]:
    """Return match data dicts for matches not yet scored."""
    from fixtures import FIXTURES

    scored_dir = os.path.join(BASE_DIR, "results", "scored")
    scored_mids = set()
    for f in os.listdir(scored_dir):
        if f.endswith(".json"):
            # match_id is everything before the last _<model>.json
            parts = f.rsplit("_", 1)
            if len(parts) == 2:
                scored_mids.add(parts[0])

    today = date.today().isoformat()
    remaining = []
    for fix in FIXTURES:
        if fix["date"] < today:
            continue
        def _safe(s): return s.replace(" ", "_").replace("'", "").replace("/", "").replace("&", "and")
        mid = f"{_safe(fix['home'])}_{_safe(fix['away'])}_{fix['date']}"
        if mid in scored_mids:
            continue
        data_path = os.path.join(BASE_DIR, "data", f"{_safe(fix['home'])}_{_safe(fix['away'])}_{fix['date']}.json")
        if not os.path.exists(data_path):
            continue
        with open(data_path, encoding="utf-8") as fp:
            match_data = json.load(fp)
        remaining.append(match_data)

    return remaining


def run_research_forecast(match_data: dict, model_cfg: dict, forecast_date: str) -> dict | None:
    mid        = match_data["match_id"]
    model_short = model_cfg["short"]
    out_path   = os.path.join(RESEARCH_DIR, f"{mid}_{model_short}.json")

    if os.path.exists(out_path):
        return None  # already done

    prompt = build_research_prompt(match_data)
    result = _call_model(model_cfg, prompt, CONFIG)
    raw    = result.get("raw_response", "")
    parsed = _extract_json(raw)

    if parsed is None:
        print(f"  {model_short}: parse error — {raw[:120]}")
        return None

    rec = {
        "match_id":       mid,
        "model_short":    model_short,
        "model_id":       model_cfg.get("id"),
        "vendor":         model_cfg.get("vendor"),
        "forecast_date":  forecast_date,
        "prompt_variant": "research_no_odds",
        "home_goals":     parsed.get("home_goals"),
        "away_goals":     parsed.get("away_goals"),
        "home_win_prob":  parsed.get("home_win_prob"),
        "draw_prob":      parsed.get("draw_prob"),
        "away_win_prob":  parsed.get("away_win_prob"),
        "confidence":     parsed.get("confidence"),
        "reasoning":      parsed.get("reasoning"),
        "cost_usd":       result.get("cost_usd", 0.0),
    }
    with open(out_path, "w", encoding="utf-8") as fp:
        json.dump(rec, fp, indent=2, ensure_ascii=False)
    return rec


def main():
    matches = get_remaining_matches()
    if not matches:
        print("No remaining matches found.")
        return

    models = CONFIG["models"]
    forecast_date = date.today().isoformat()

    print(f"Research forecast (no odds) — {len(matches)} matches × {len(models)} models")
    print(f"Output: {RESEARCH_DIR}")
    print()

    tasks = [(m, cfg) for m in matches for cfg in models]
    total = len(tasks)
    done  = 0

    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {ex.submit(run_research_forecast, m, cfg, forecast_date): (m["match_id"], cfg["short"])
                   for m, cfg in tasks}
        for fut in as_completed(futures):
            mid, model = futures[fut]
            done += 1
            try:
                rec = fut.result()
                if rec:
                    h, a = rec.get("home_goals","?"), rec.get("away_goals","?")
                    print(f"  [{done}/{total}] {model:16} {mid}: {h}-{a}")
            except Exception as e:
                print(f"  [{done}/{total}] {model:16} {mid}: ERROR {e}")

    print(f"\nDone. Files in {RESEARCH_DIR}")


if __name__ == "__main__":
    main()
