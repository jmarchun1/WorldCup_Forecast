"""
backtest_prompts.py — Controlled prompt-variant backtest against scored matches.

Replays all scored historical matches through different prompt versions and
scores predictions against known results. Answers: do our prompt iterations
actually improve accuracy?

Knowledge-cutoff instruction prevents models from recalling results:
  "Predict as if today is the day before the match. Do not use any knowledge
   of the actual result or post-match reports."

Usage:
    python backtest_prompts.py --variant baseline
    python backtest_prompts.py --variant calibrated
    python backtest_prompts.py --variant all         # runs all variants
    python backtest_prompts.py --variant all --model sonnet  # single model only
    python backtest_prompts.py --variant all --dry-run       # print prompts, no API calls

Variants:
    baseline    — original prompt (no calibration block, original goal prior)
    calibrated  — current v11 prompt (goal volume prior + 5-check calibration block)

Output:
    results/backtest_prompts/<variant>/<match_id>_<model>.json
    results/backtest_prompts/summary.json
"""

import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from forecast import (
    _call_model, _extract_json, _get_base_rate_prior, _get_draw_reminder,
    _get_dead_rubber_context, _is_knockout, WC2026_INJURIES, WC2026_TILT,
)

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
SCORED_DIR  = os.path.join(BASE_DIR, "results", "scored")
DATA_DIR    = os.path.join(BASE_DIR, "data")
OUT_BASE    = os.path.join(BASE_DIR, "results", "backtest_prompts")
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

with open(CONFIG_PATH, encoding="utf-8") as f:
    CONFIG = json.load(f)

# ── Baseline goal prior (pre-v11, no WC2026 in-tournament data) ──────────────
WC_BASE_RATE_PRIOR_BASELINE = (
    "Historical World Cup group-stage base rates (1990-2022): "
    "most common scorelines are 1-0 (18%), 1-1 (14%), 2-0 (11%), 2-1 (10%), 0-0 (7%). "
    "When Elo rating gap exceeds 150 points, the stronger team wins ~70% of the time. "
    "Goals per match average 2.6 historically."
)

CUTOFF_INSTRUCTION = (
    "IMPORTANT — KNOWLEDGE CUTOFF: You are predicting this match BEFORE it has been played. "
    "Treat today as the day before the match date shown above. "
    "Do NOT use any knowledge of the actual result, post-match reports, or any information "
    "published after the match date. Base your prediction solely on pre-match context below."
)


# ── Prompt builders ───────────────────────────────────────────────────────────

def _prompt_header(match_data: dict) -> list:
    home       = match_data["home"]
    away       = match_data["away"]
    stage      = match_data["stage"]
    venue      = match_data["venue"]
    match_date = match_data["date"]
    odds       = match_data.get("odds", {})

    home_odds    = odds.get("home_win", 2.50)
    draw_odds    = odds.get("draw", 3.20)
    away_odds    = odds.get("away_win", 2.80)
    implied_home = odds.get("implied_home", 0.38)
    implied_draw = odds.get("implied_draw", 0.30)
    implied_away = odds.get("implied_away", 0.34)

    lines = [
        f"You are a football/soccer analyst. Today is {match_date}.",
        "",
        CUTOFF_INSTRUCTION,
        "",
        f"Match: {home} vs {away}",
        f"Stage: {stage} — {venue}",
        f"Match date: {match_date}",
        "",
    ]

    # PELE Tilt
    home_tilt = WC2026_TILT.get(home)
    away_tilt = WC2026_TILT.get(away)

    return lines, home_odds, draw_odds, away_odds, implied_home, implied_draw, implied_away, home_tilt, away_tilt


def _prompt_footer(match_data: dict, draw_reminder: str, calibration_block: list) -> list:
    home = match_data["home"]
    away = match_data["away"]
    lines = [
        f"=== PREDICTION REQUEST ===",
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
        draw_reminder,
        "",
    ]
    lines += calibration_block
    lines += [
        f"State your predicted scoreline in your reasoning as: 'Predicted score: X-Y'. Then output the JSON.",
        "",
        "Respond ONLY with valid JSON:",
        json.dumps({
            "home_goals": 0, "away_goals": 0,
            "home_win_prob": 0.0, "draw_prob": 0.0, "away_win_prob": 0.0,
            "confidence": 0, "reasoning": "...",
        }, indent=2),
    ]
    return lines


def build_baseline_prompt(match_data: dict) -> str:
    """Pre-v11 prompt: original goal prior, no calibration block."""
    stage   = match_data["stage"]
    context = match_data.get("context", "")

    lines, home_odds, draw_odds, away_odds, ih, id_, ia, home_tilt, away_tilt = _prompt_header(match_data)

    lines += [
        "=== HISTORICAL BASE RATES ===",
        WC_BASE_RATE_PRIOR_BASELINE,
        "",
        "=== KEY INJURY ABSENCES (WC 2026) ===",
        WC2026_INJURIES,
        "",
    ]
    if home_tilt or away_tilt:
        lines += ["=== TEAM STYLE (PELE TILT RATINGS) ==="]
        if home_tilt:
            lines.append(f"  {match_data['home']}: {home_tilt[1]}")
        if away_tilt:
            lines.append(f"  {match_data['away']}: {away_tilt[1]}")
        lines.append("")

    lines += [
        "=== CURRENT BOOKMAKER ODDS ===",
        f"  {match_data['home']} win: {home_odds} (implied {ih:.1%})",
        f"  Draw: {draw_odds} (implied {id_:.1%})",
        f"  {match_data['away']} win: {away_odds} (implied {ia:.1%})",
        "",
        "=== MATCH CONTEXT (ODDS, FORM, HEAD-TO-HEAD) ===",
        context or "No additional context available.",
        "",
    ]

    dead_rubber = _get_dead_rubber_context(match_data)
    if dead_rubber:
        lines += [dead_rubber, ""]

    lines += _prompt_footer(match_data, _get_draw_reminder(stage), [])
    return "\n".join(lines)


def build_calibrated_prompt(match_data: dict) -> str:
    """v11 prompt: updated goal prior + 5-check calibration block."""
    stage   = match_data["stage"]
    context = match_data.get("context", "")

    lines, home_odds, draw_odds, away_odds, ih, id_, ia, home_tilt, away_tilt = _prompt_header(match_data)

    lines += [
        "=== HISTORICAL BASE RATES ===",
        _get_base_rate_prior(stage),
        "",
        "=== KEY INJURY ABSENCES (WC 2026) ===",
        WC2026_INJURIES,
        "",
    ]
    if home_tilt or away_tilt:
        lines += ["=== TEAM STYLE (PELE TILT RATINGS) ==="]
        if home_tilt:
            lines.append(f"  {match_data['home']}: {home_tilt[1]}")
            if len(home_tilt) > 2:
                lines.append(f"  {match_data['home']} draw rate (last 20 competitive matches): ~{home_tilt[2]:.0%}")
        if away_tilt:
            lines.append(f"  {match_data['away']}: {away_tilt[1]}")
            if len(away_tilt) > 2:
                lines.append(f"  {match_data['away']} draw rate (last 20 competitive matches): ~{away_tilt[2]:.0%}")
        lines.append("")

    lines += [
        "=== CURRENT BOOKMAKER ODDS ===",
        f"  {match_data['home']} win: {home_odds} (implied {ih:.1%})",
        f"  Draw: {draw_odds} (implied {id_:.1%})",
        f"  {match_data['away']} win: {away_odds} (implied {ia:.1%})",
        "",
        "=== MATCH CONTEXT (ODDS, FORM, HEAD-TO-HEAD) ===",
        context or "No additional context available.",
        "",
    ]

    dead_rubber = _get_dead_rubber_context(match_data)
    if dead_rubber:
        lines += [dead_rubber, ""]

    calibration = [
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
        "When the favourite's implied probability is 60-70%, underdogs still win ~22% of the time. "
        "What specific factors in this match push that rate above or below the base rate?",
        "",
        "4. MINORITY SCENARIO: In 2-3 sentences, describe the most plausible path to an underdog "
        "win or surprise draw. Do your probabilities reflect this plausible path?",
        "",
        "5. BRIER SCORING: Your probabilities are evaluated by Brier score, which penalises "
        "overconfidence heavily. Assign at least 10% probability to every outcome unless there "
        "is an overwhelming structural reason to exclude it.",
        "",
    ]

    lines += _prompt_footer(match_data, _get_draw_reminder(stage), calibration)
    return "\n".join(lines)


# ── Contest variant constants ─────────────────────────────────────────────────

DRAW_DETECTION_BLOCK = [
    "=== DRAW DETECTION ===",
    "Draws occur in ~28% of WC2026 group matches. Before finalising, check explicitly:",
    "  - Are these teams within 80 Elo points of each other (roughly equal quality)?",
    "  - Does the match context (form, H2H, advancement stakes) point to a cautious, low-risk approach?",
    "ONLY predict a draw if BOTH conditions are clearly satisfied AND the bookmaker draw odds are below 3.5.",
    "If the favourite has implied win probability above 55%, do NOT predict a draw — back the favourite.",
    "The 1-1 scoreline is over-predicted by AI models at 2x its actual rate. Only predict 1-1 when",
    "both teams are genuinely evenly matched. Otherwise predict 1-0, 2-0, 2-1, or 0-1.",
    "",
]

DRAW_DETECTION_BLOCK_KNOCKOUT = [
    "=== KNOCKOUT STAGE: SCORING RULES ===",
    "IMPORTANT: This competition scores on the 90-MINUTE result only. Extra time and penalty shootouts",
    "are ignored entirely. A match that ends 1-1 after 90 minutes and goes to penalties is scored as",
    "a 1-1 draw — predicting 1-1 would earn the full 4 points.",
    "→ If you think a match is likely to be settled by penalty shootout, predict a DRAW scoreline.",
    "",
    "Draw after 90 minutes occurs in ~20% of WC knockout matches.",
    "Predict a draw when EITHER condition applies:",
    "  - Both teams are within 80 Elo points AND the bookmaker draw odds are below 3.8 (implied draw >26%)",
    "  - The match context strongly suggests a tight, cautious tactical battle with no clear favourite",
    "For lopsided matchups (implied win >60%), back the favourite with a decisive scoreline (1-0, 2-0, 2-1).",
    "Do NOT predict 1-1 as a default hedge on every match — only when the draw is genuinely likely.",
    "",
]

COMMIT_INSTRUCTION = [
    "=== CONTEST SCORING ===",
    "Scoring: exact scoreline = 4 pts, correct goal-difference = 2 pts, correct result direction = 1 pt, wrong = 0 pts.",
    "OPTIMAL STRATEGY: commit to your single most likely scoreline. Do NOT hedge toward 1-1 or 1-0 as a safe default.",
    "Pick the MODE (most probable outcome), not the mean. A 30% confident 2-1 beats a 15% confident 1-1.",
    "",
]


def build_contest_prompt(match_data: dict) -> str:
    """Contest-optimised prompt: draw detection + 0-0 detector + commit instruction. No hedging."""
    stage   = match_data["stage"]
    context = match_data.get("context", "")

    lines, home_odds, draw_odds, away_odds, ih, id_, ia, home_tilt, away_tilt = _prompt_header(match_data)

    lines += [
        "=== HISTORICAL BASE RATES ===",
        _get_base_rate_prior(stage),
        "",
        "=== KEY INJURY ABSENCES (WC 2026) ===",
        WC2026_INJURIES,
        "",
    ]
    if home_tilt or away_tilt:
        lines += ["=== TEAM STYLE (PELE TILT RATINGS) ==="]
        if home_tilt:
            lines.append(f"  {match_data['home']}: {home_tilt[1]}")
            if len(home_tilt) > 2:
                lines.append(f"  {match_data['home']} draw rate (last 20 competitive matches): ~{home_tilt[2]:.0%}")
        if away_tilt:
            lines.append(f"  {match_data['away']}: {away_tilt[1]}")
            if len(away_tilt) > 2:
                lines.append(f"  {match_data['away']} draw rate (last 20 competitive matches): ~{away_tilt[2]:.0%}")
        lines.append("")

    lines += [
        "=== CURRENT BOOKMAKER ODDS ===",
        f"  {match_data['home']} win: {home_odds} (implied {ih:.1%})",
        f"  Draw: {draw_odds} (implied {id_:.1%})",
        f"  {match_data['away']} win: {away_odds} (implied {ia:.1%})",
        "",
        "=== MATCH CONTEXT (ODDS, FORM, HEAD-TO-HEAD) ===",
        context or "No additional context available.",
        "",
    ]

    dead_rubber = _get_dead_rubber_context(match_data)
    if dead_rubber:
        lines += [dead_rubber, ""]

    draw_block = DRAW_DETECTION_BLOCK_KNOCKOUT if _is_knockout(stage) else DRAW_DETECTION_BLOCK
    contest_block = draw_block + COMMIT_INSTRUCTION
    lines += _prompt_footer(match_data, _get_draw_reminder(stage), contest_block)
    return "\n".join(lines)


VARIANTS = {
    "baseline":   build_baseline_prompt,
    "calibrated": build_calibrated_prompt,
    "contest":    build_contest_prompt,
    "ev":         build_calibrated_prompt,
}


# ── Scoring helpers ───────────────────────────────────────────────────────────

def _result(h, a):
    if h > a: return "home_win"
    if a > h: return "away_win"
    return "draw"


def _fantasy_points(ph, pa, ah, aa):
    if ph == ah and pa == aa:
        return 4
    pr = _result(ph, pa); ar = _result(ah, aa)
    if pr != ar:
        return 0
    if ar != "draw" and abs(ph - pa) == abs(ah - aa):
        return 2
    return 1


def _brier(hw, dp, aw, actual):
    o = {"home_win": (1,0,0), "draw": (0,1,0), "away_win": (0,0,1)}[actual]
    return round((hw-o[0])**2 + (dp-o[1])**2 + (aw-o[2])**2, 4)


# ── Core runner ───────────────────────────────────────────────────────────────

def get_scored_matches() -> list[dict]:
    """Return unique (match_id, actual_home, actual_away) from scored dir."""
    seen = {}
    for f in os.listdir(SCORED_DIR):
        if not f.endswith(".json"):
            continue
        rec = json.load(open(f"{SCORED_DIR}/{f}", encoding="utf-8"))
        mid = rec["match_id"]
        if mid not in seen:
            seen[mid] = (rec["actual_home"], rec["actual_away"])
    return [{"match_id": mid, "actual_home": ah, "actual_away": aa}
            for mid, (ah, aa) in sorted(seen.items())]


def run_one(match_id: str, actual_home: int, actual_away: int,
            model_cfg: dict, variant: str, out_dir: str, dry_run: bool) -> dict | None:
    out_path = os.path.join(out_dir, f"{match_id}_{model_cfg['short']}.json")
    if os.path.exists(out_path):
        return json.load(open(out_path, encoding="utf-8"))

    data_path = os.path.join(DATA_DIR, f"{match_id}.json")
    if not os.path.exists(data_path):
        return None

    match_data = json.load(open(data_path, encoding="utf-8"))
    prompt     = VARIANTS[variant](match_data)

    if dry_run:
        print(f"\n{'='*60}\n{match_id} | {model_cfg['short']} | {variant}\n{'='*60}")
        print(prompt[:800], "...[truncated]")
        return None

    result = _call_model(model_cfg, prompt, CONFIG)
    raw    = result.get("raw_response", "")
    parsed = _extract_json(raw)
    if parsed is None:
        return None

    ph = parsed.get("home_goals", 0) or 0
    pa = parsed.get("away_goals", 0) or 0
    hw = parsed.get("home_win_prob", 0) or 0
    dp = parsed.get("draw_prob", 0) or 0
    aw = parsed.get("away_win_prob", 0) or 0
    actual_outcome = _result(actual_home, actual_away)

    rec = {
        "match_id":      match_id,
        "model_short":   model_cfg["short"],
        "variant":       variant,
        "actual_home":   actual_home,
        "actual_away":   actual_away,
        "actual_outcome": actual_outcome,
        "home_goals":    ph,
        "away_goals":    pa,
        "home_win_prob": hw,
        "draw_prob":     dp,
        "away_win_prob": aw,
        "points":        _fantasy_points(ph, pa, actual_home, actual_away),
        "brier":         _brier(hw, dp, aw, actual_outcome),
        "goals_predicted": ph + pa,
        "cost_usd":      result.get("cost_usd", 0.0),
        "reasoning":     parsed.get("reasoning", ""),
    }
    with open(out_path, "w", encoding="utf-8") as fp:
        json.dump(rec, fp, indent=2, ensure_ascii=False)
    return rec


def summarise(out_dir: str, variant: str) -> dict:
    recs = []
    for f in os.listdir(out_dir):
        if f.endswith(".json") and f != "summary.json":
            recs.append(json.load(open(f"{out_dir}/{f}", encoding="utf-8")))
    if not recs:
        return {}

    n          = len(recs)
    ppg        = round(sum(r["points"] for r in recs) / n, 3)
    exact_pct  = round(sum(1 for r in recs if r["points"] == 4) / n * 100, 1)
    correct_pct= round(sum(1 for r in recs if r["points"] > 0) / n * 100, 1)
    avg_brier  = round(sum(r["brier"] for r in recs) / n, 3)
    avg_goals  = round(sum(r["goals_predicted"] for r in recs) / n, 2)
    draw_pred  = round(sum(1 for r in recs if _result(r["home_goals"], r["away_goals"]) == "draw") / n * 100, 1)
    ones_ones  = round(sum(1 for r in recs if r["home_goals"] == 1 and r["away_goals"] == 1) / n * 100, 1)
    total_cost = round(sum(r.get("cost_usd", 0) for r in recs), 4)

    summary = {
        "variant": variant, "n": n,
        "ppg": ppg, "exact_pct": exact_pct, "correct_pct": correct_pct,
        "avg_brier": avg_brier, "avg_goals_predicted": avg_goals,
        "draw_pred_pct": draw_pred, "ones_ones_pct": ones_ones,
        "total_cost_usd": total_cost,
    }
    with open(os.path.join(out_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    return summary


def print_summary_table(summaries: list[dict]):
    print()
    print(f"{'Variant':<14} {'N':>5} {'PPG':>6} {'Exact%':>7} {'Correct%':>9} {'Brier':>7} {'Goals':>6} {'Draw%':>7} {'1-1%':>6} {'Cost$':>7}")
    print("-" * 85)
    for s in summaries:
        print(
            f"{s['variant']:<14} {s['n']:>5} {s['ppg']:>6} {s['exact_pct']:>6}% "
            f"{s['correct_pct']:>8}% {s['avg_brier']:>7} {s['avg_goals_predicted']:>6} "
            f"{s['draw_pred_pct']:>6}% {s['ones_ones_pct']:>5}% {s['total_cost_usd']:>7.3f}"
        )
    print()


def main():
    dry_run    = "--dry-run" in sys.argv
    yes        = "--yes" in sys.argv
    model_filter = sys.argv[sys.argv.index("--model") + 1] if "--model" in sys.argv else None

    variant_arg = "all"
    if "--variant" in sys.argv:
        variant_arg = sys.argv[sys.argv.index("--variant") + 1]

    variants_to_run = list(VARIANTS.keys()) if variant_arg == "all" else [variant_arg]
    for v in variants_to_run:
        if v not in VARIANTS:
            print(f"Unknown variant '{v}'. Options: {list(VARIANTS.keys())}")
            sys.exit(1)

    models = CONFIG["models"]
    if model_filter:
        models = [m for m in models if m["short"] == model_filter]
        if not models:
            print(f"No model matching '{model_filter}'")
            sys.exit(1)

    scored_matches = get_scored_matches()
    print(f"Scored matches: {len(scored_matches)}")
    print(f"Models: {[m['short'] for m in models]}")
    print(f"Variants: {variants_to_run}")
    print(f"Total API calls: ~{len(scored_matches) * len(models) * len(variants_to_run)}")

    if not dry_run and not yes:
        total_calls = len(scored_matches) * len(models) * len(variants_to_run)
        print(f"\nEstimated cost: ~${total_calls * 0.008:.0f}–${total_calls * 0.015:.0f}")
        confirm = input("Proceed? [y/N] ").strip().lower()
        if confirm != "y":
            print("Aborted.")
            return

    summaries = []
    for variant in variants_to_run:
        out_dir = os.path.join(OUT_BASE, variant)
        os.makedirs(out_dir, exist_ok=True)

        tasks  = [(m, cfg) for m in scored_matches for cfg in models]
        total  = len(tasks)
        done   = 0

        print(f"\n--- Variant: {variant} ({total} tasks) ---")

        with ThreadPoolExecutor(max_workers=8) as ex:
            futures = {
                ex.submit(run_one, m["match_id"], m["actual_home"], m["actual_away"],
                          cfg, variant, out_dir, dry_run): (m["match_id"], cfg["short"])
                for m, cfg in tasks
            }
            for fut in as_completed(futures):
                mid, model = futures[fut]
                done += 1
                try:
                    rec = fut.result()
                    if rec and done % 20 == 0:
                        print(f"  [{done}/{total}] {model:14} {mid}: {rec['home_goals']}-{rec['away_goals']} pts={rec['points']}")
                except Exception as e:
                    print(f"  [{done}/{total}] {model:14} {mid}: ERROR {e}")

        s = summarise(out_dir, variant)
        if s:
            summaries.append(s)
            print(f"  {variant}: PPG={s['ppg']} exact={s['exact_pct']}% brier={s['avg_brier']} goals={s['avg_goals_predicted']} 1-1={s['ones_ones_pct']}%")

    if summaries:
        print_summary_table(summaries)

    print(f"Results in: {OUT_BASE}")


if __name__ == "__main__":
    main()
