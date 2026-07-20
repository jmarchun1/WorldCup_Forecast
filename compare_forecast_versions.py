"""
compare_forecast_versions.py — Compare v1 (original) vs v2 (re-fetched) forecast accuracy.

Extracts v1 forecasts from a git commit in the GitHub Pages repo (where all forecast
JSON is embedded in index.html), then scores both versions against actual results
and prints a per-model accuracy comparison table.

Usage:
    python compare_forecast_versions.py
    python compare_forecast_versions.py --v1-commit 8455ec4
"""

import json
import os
import re
import subprocess
import sys
from collections import defaultdict

BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
SCORED_DIR     = os.path.join(BASE_DIR, "results", "scored")
FORECASTS_DIR  = os.path.join(BASE_DIR, "results", "forecasts")
PAGES_REPO     = r"C:\Users\I846720\OneDrive\Github\WCFCST"

# Last commit before the June 15 context refresh
DEFAULT_V1_COMMIT = "8455ec4"


def get_actuals() -> dict[str, tuple[int, int]]:
    """Load actual scores from scored files. Returns {match_id: (home, away)}."""
    actuals = {}
    for fname in os.listdir(SCORED_DIR):
        if not fname.endswith(".json"):
            continue
        with open(os.path.join(SCORED_DIR, fname), encoding="utf-8") as f:
            d = json.load(f)
        mid = d["match_id"]
        actuals[mid] = (d["actual_home"], d["actual_away"])
    return actuals


def extract_forecasts_from_html(html: str) -> dict[tuple[str, str], dict]:
    """
    Parse forecast JSON objects embedded in index.html.
    The HTML contains: const FORECASTS = [{...}, {...}];
    Returns {(match_id, model_short): {home_goals, away_goals, ...}}
    """
    # Find the start of the FORECASTS array
    marker = "const FORECASTS = ["
    idx = html.find(marker)
    if idx == -1:
        return {}

    # Walk forward to find the matching closing bracket
    start = idx + len(marker) - 1  # points at '['
    depth = 0
    end = start
    for i, ch in enumerate(html[start:], start):
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                end = i
                break

    array_str = html[start:end + 1]
    try:
        records = json.loads(array_str)
    except json.JSONDecodeError:
        return {}

    results = {}
    for obj in records:
        if not isinstance(obj, dict):
            continue
        if obj.get("home_goals") is None or obj.get("match_id") is None:
            continue
        key = (obj["match_id"], obj["model_short"])
        results[key] = obj
    return results


def score_prediction(pred_home: int, pred_away: int,
                     actual_home: int, actual_away: int) -> tuple[int, str]:
    """Return (points, breakdown) using the same rules as score.py."""
    if pred_home == actual_home and pred_away == actual_away:
        return 4, "exact_score"
    pred_gd   = pred_home - pred_away
    actual_gd = actual_home - actual_away
    pred_result   = "H" if pred_home > pred_away else ("D" if pred_home == pred_away else "A")
    actual_result = "H" if actual_home > actual_away else ("D" if actual_home == actual_away else "A")
    if pred_result == actual_result:
        if pred_gd == actual_gd:
            return 2, "correct_result_exact_gd"
        return 1, "correct_result"
    return 0, "wrong_result"


def load_v2_forecasts() -> dict[tuple[str, str], dict]:
    """Load current (v2) forecasts from results/forecasts/."""
    results = {}
    for fname in os.listdir(FORECASTS_DIR):
        if not fname.endswith(".json") or fname.endswith("_CONSENSUS.json"):
            continue
        with open(os.path.join(FORECASTS_DIR, fname), encoding="utf-8") as f:
            d = json.load(f)
        if d.get("home_goals") is None:
            continue
        key = (d["match_id"], d["model_short"])
        results[key] = d
    return results


def compare(v1_commit: str = DEFAULT_V1_COMMIT):
    # 1. Get actuals
    actuals = get_actuals()
    if not actuals:
        print("No scored matches yet.")
        return
    print(f"Scored matches: {len(actuals)}")

    # 2. Extract v1 from git
    print(f"Extracting v1 forecasts from commit {v1_commit}...")
    result = subprocess.run(
        ["git", "show", f"{v1_commit}:index.html"],
        cwd=PAGES_REPO,
        capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        sys.exit(1)
    v1_forecasts = extract_forecasts_from_html(result.stdout)
    print(f"V1 forecasts extracted: {len(v1_forecasts)}")

    # 3. Load v2
    v2_forecasts = load_v2_forecasts()
    print(f"V2 forecasts loaded: {len(v2_forecasts)}")

    # 4. Score both versions on the same scored matches
    models = sorted({k[1] for k in v1_forecasts} | {k[1] for k in v2_forecasts})

    stats = {
        m: {
            "v1": {"pts": 0, "exact": 0, "gd": 0, "result": 0, "zero": 0, "n": 0},
            "v2": {"pts": 0, "exact": 0, "gd": 0, "result": 0, "zero": 0, "n": 0},
        }
        for m in models
    }

    for mid, (ah, aa) in actuals.items():
        for model in models:
            key = (mid, model)
            for ver, fc_dict in [("v1", v1_forecasts), ("v2", v2_forecasts)]:
                rec = fc_dict.get(key)
                if not rec:
                    continue
                ph, pa = rec["home_goals"], rec["away_goals"]
                pts, bd = score_prediction(ph, pa, ah, aa)
                s = stats[model][ver]
                s["pts"] += pts
                s["n"]   += 1
                if bd == "exact_score":            s["exact"]  += 1
                elif bd == "correct_result_exact_gd": s["gd"]  += 1
                elif bd == "correct_result":        s["result"] += 1
                else:                               s["zero"]   += 1

    # 5. Print comparison table
    print()
    print(f"{'Model':<22} {'V1 Pts':>7} {'V1 Exact':>9} {'V1 0pts':>8}  {'V2 Pts':>7} {'V2 Exact':>9} {'V2 0pts':>8}  {'Delta':>7}")
    print("-" * 85)
    for model in sorted(models, key=lambda m: -(stats[m]["v2"]["pts"])):
        v1 = stats[model]["v1"]
        v2 = stats[model]["v2"]
        if v1["n"] == 0 and v2["n"] == 0:
            continue
        delta = v2["pts"] - v1["pts"]
        delta_str = f"+{delta}" if delta > 0 else str(delta)
        print(
            f"{model:<22} {v1['pts']:>7} {v1['exact']:>9} {v1['zero']:>8}  "
            f"{v2['pts']:>7} {v2['exact']:>9} {v2['zero']:>8}  {delta_str:>7}"
        )
    print()
    # Summary
    total_v1 = sum(stats[m]["v1"]["pts"] for m in models)
    total_v2 = sum(stats[m]["v2"]["pts"] for m in models)
    print(f"Total points — V1: {total_v1}  V2: {total_v2}  Delta: {total_v2 - total_v1:+d}")


if __name__ == "__main__":
    commit = DEFAULT_V1_COMMIT
    if "--v1-commit" in sys.argv:
        idx = sys.argv.index("--v1-commit")
        commit = sys.argv[idx + 1]
    compare(commit)
