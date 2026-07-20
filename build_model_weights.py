"""
build_model_weights.py — Compute Bayesian model weights from scored history.

Weights are inverse-Brier-score normalised per model, saved to model_weights.json.
_compute_consensus() in forecast.py loads these automatically.

Usage:
    python build_model_weights.py          # compute and save weights
    python build_model_weights.py --show   # print weights, don't save
"""

import json
import os
import sys
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCORED_DIR = os.path.join(BASE_DIR, "results", "scored")
WEIGHTS_FILE = os.path.join(BASE_DIR, "model_weights.json")

# Minimum matches before a model gets a real weight (else use prior = 1.0)
MIN_MATCHES = 10


def _is_tainted(r: dict) -> bool:
    """Return True if a Sonar/SonarPro forecast was made on or after the match date."""
    WEB_SEARCH_MODELS = {"sonar", "sonarpro"}
    if r.get("model_short") not in WEB_SEARCH_MODELS:
        return False
    forecast_date = r.get("forecast_date", "")
    match_id = r.get("match_id", "")
    match_date = match_id[-10:] if len(match_id) >= 10 else ""
    return bool(forecast_date and match_date and forecast_date >= match_date)


def compute_weights(records: list[dict]) -> dict:
    by_model = defaultdict(lambda: {"brier": [], "matches": set()})
    for r in records:
        m = r.get("model_short")
        if not m:
            continue
        if _is_tainted(r):
            continue
        if r.get("brier_score") is not None:
            by_model[m]["brier"].append(r["brier_score"])
        by_model[m]["matches"].add(r["match_id"])

    inv_briers = {}
    for m, s in by_model.items():
        n = len(s["matches"])
        if n < MIN_MATCHES or not s["brier"]:
            inv_briers[m] = 1.0  # flat prior for data-sparse models
        else:
            avg_b = sum(s["brier"]) / len(s["brier"])
            inv_briers[m] = 1.0 / avg_b if avg_b > 0 else 1.0

    total = sum(inv_briers.values())
    weights = {m: round(v / total, 6) for m, v in inv_briers.items()}
    return weights


def main():
    records = []
    for f in os.listdir(SCORED_DIR):
        if f.endswith(".json"):
            with open(os.path.join(SCORED_DIR, f), encoding="utf-8") as fh:
                records.append(json.load(fh))

    weights = compute_weights(records)

    # Count matches per model for display (tainted records excluded)
    match_counts = defaultdict(set)
    brier_avgs = defaultdict(list)
    for r in records:
        if _is_tainted(r):
            continue
        m = r.get("model_short")
        if m:
            match_counts[m].add(r["match_id"])
            if r.get("brier_score") is not None:
                brier_avgs[m].append(r["brier_score"])

    print(f"{'Model':<15} {'Matches':>8} {'AvgBrier':>10} {'Weight':>8}")
    print("-" * 45)
    for m, w in sorted(weights.items(), key=lambda x: -x[1]):
        n = len(match_counts[m])
        avg_b = sum(brier_avgs[m]) / len(brier_avgs[m]) if brier_avgs[m] else 0
        flag = " *" if n < MIN_MATCHES else ""
        print(f"  {m:<13} {n:>8} {avg_b:>10.4f} {w:>8.4f}{flag}")

    if "--show" not in sys.argv:
        with open(WEIGHTS_FILE, "w", encoding="utf-8") as f:
            json.dump({"weights": weights, "n_records": len(records),
                       "min_matches_threshold": MIN_MATCHES}, f, indent=2)
        print(f"\nSaved to {WEIGHTS_FILE}")
    else:
        print("\n(--show mode, not saved)")


if __name__ == "__main__":
    main()
