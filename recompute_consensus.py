"""
recompute_consensus.py — Rebuild all CONSENSUS files using current model weights.

Run after build_model_weights.py to apply Bayesian weighting to all existing forecasts.
Preserves kalshi_odds patches already written to CONSENSUS files.

Usage:
    python recompute_consensus.py           # rebuild all upcoming matches
    python recompute_consensus.py --all     # rebuild all matches (including past)
    python recompute_consensus.py --date 2026-06-27
"""

import json
import os
import sys
from datetime import date

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Patch sys.path so we can import forecast internals
sys.path.insert(0, BASE_DIR)
import forecast as fc
from fixtures import FIXTURES


def main():
    config_path = os.path.join(BASE_DIR, "config.json")
    with open(config_path, encoding="utf-8") as f:
        config = json.load(f)

    # Invalidate weights cache so fresh weights are loaded
    fc._model_weights_cache = None

    rebuild_all = "--all" in sys.argv
    filter_date = None
    if "--date" in sys.argv:
        filter_date = sys.argv[sys.argv.index("--date") + 1]

    today = date.today().isoformat()
    fixtures = FIXTURES if rebuild_all else [f for f in FIXTURES if f["date"] >= today]
    if filter_date:
        fixtures = [f for f in fixtures if f["date"] == filter_date]

    print(f"Recomputing consensus for {len(fixtures)} matches (bayesian_weighted={bool(fc._load_model_weights())})...")
    rebuilt = 0
    changed = 0

    for fix in fixtures:
        # Derive match_id the same way forecast.py does
        def _safe(s): return s.replace(" ", "_").replace("'", "").replace("/", "").replace("&", "and")
        mid = f"{_safe(fix['home'])}_{_safe(fix['away'])}_{fix['date']}"
        match_data = fc.load_match_data(mid)
        if match_data is None:
            continue

        # Preserve existing kalshi_odds patch before overwriting
        cons_path = os.path.join(fc.FORECASTS_DIR, f"{mid}_CONSENSUS.json")
        kalshi_patch = {}
        if os.path.exists(cons_path):
            with open(cons_path, encoding="utf-8") as f2:
                old = json.load(f2)
            for k in ("kalshi_odds", "kalshi_ev_home_win", "kalshi_ev_draw",
                      "kalshi_ev_away_win", "kalshi_value_bets"):
                if k in old:
                    kalshi_patch[k] = old[k]
            old_score = (old.get("consensus_home_goals"), old.get("consensus_away_goals"))
        else:
            old_score = (None, None)

        new_cons = fc._compute_consensus(match_data, today, config)
        if new_cons is None:
            continue

        # Re-apply kalshi patch
        if kalshi_patch:
            with open(cons_path, encoding="utf-8") as f2:
                new_cons_disk = json.load(f2)
            new_cons_disk.update(kalshi_patch)
            with open(cons_path, "w", encoding="utf-8") as f2:
                json.dump(new_cons_disk, f2, indent=2, ensure_ascii=False)

        new_score = (new_cons.get("consensus_home_goals"), new_cons.get("consensus_away_goals"))
        score_changed = new_score != old_score
        if score_changed:
            changed += 1
            print(f"  CHANGED {mid}: {old_score[0]}-{old_score[1]} -> {new_score[0]}-{new_score[1]}")
        rebuilt += 1

    print(f"\nDone: {rebuilt} rebuilt, {changed} scoreline changes.")


if __name__ == "__main__":
    main()
