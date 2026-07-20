"""
patch_kalshi_odds.py — Store live Kalshi odds on CONSENSUS files and recompute EV.

Usage:
    python patch_kalshi_odds.py --match "USA_Turkey_2026-06-25" --home 1.82 --draw 4.14 --away 4.00
    python patch_kalshi_odds.py --batch kalshi_odds.json

Batch JSON format:
    {
        "USA_Turkey_2026-06-25":    {"home": 1.82, "draw": 4.14, "away": 4.00},
        "Norway_France_2026-06-26": {"home": 4.51, "draw": 4.31, "away": 1.65}
    }

Once patched, CONSENSUS files gain:
    kalshi_odds:         {"home": X, "draw": Y, "away": Z, "patched_date": "..."}
    kalshi_ev_home_win:  float
    kalshi_ev_draw:      float
    kalshi_ev_away_win:  float
    kalshi_value_bets:   [{"outcome": "...", "ev": ..., "odds": ...}]

score.py uses kalshi_odds when present for per-model EV computation.
"""

import json
import os
import sys
from datetime import date

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FORECASTS_DIR = os.path.join(BASE_DIR, "results", "forecasts")

EV_THRESHOLD = 0.05


def _ev(p: float, decimal_odds: float) -> float:
    return p * (decimal_odds - 1) - (1 - p)


def patch_match(match_id: str, home_odds: float, draw_odds: float, away_odds: float) -> bool:
    consensus_path = os.path.join(FORECASTS_DIR, f"{match_id}_CONSENSUS.json")
    if not os.path.exists(consensus_path):
        print(f"  No CONSENSUS file for {match_id}")
        return False

    with open(consensus_path, encoding="utf-8") as f:
        cons = json.load(f)

    hp = cons.get("avg_home_win_prob", 0)
    dp = cons.get("avg_draw_prob", 0)
    ap = cons.get("avg_away_win_prob", 0)

    ev_h = _ev(hp, home_odds)
    ev_d = _ev(dp, draw_odds)
    ev_a = _ev(ap, away_odds)

    value_bets = []
    if ev_h > EV_THRESHOLD:
        value_bets.append({"outcome": "home", "ev": round(ev_h, 4), "odds": home_odds, "our_prob": round(hp, 4)})
    if ev_d > EV_THRESHOLD:
        value_bets.append({"outcome": "draw", "ev": round(ev_d, 4), "odds": draw_odds, "our_prob": round(dp, 4)})
    if ev_a > EV_THRESHOLD:
        value_bets.append({"outcome": "away", "ev": round(ev_a, 4), "odds": away_odds, "our_prob": round(ap, 4)})
    value_bets.sort(key=lambda x: -x["ev"])

    cons["kalshi_odds"] = {
        "home": home_odds,
        "draw": draw_odds,
        "away": away_odds,
        "patched_date": date.today().isoformat(),
    }
    cons["kalshi_ev_home_win"] = round(ev_h, 4)
    cons["kalshi_ev_draw"] = round(ev_d, 4)
    cons["kalshi_ev_away_win"] = round(ev_a, 4)
    cons["kalshi_value_bets"] = value_bets

    with open(consensus_path, "w", encoding="utf-8") as f:
        json.dump(cons, f, indent=2, ensure_ascii=False)

    vb_str = ", ".join(f"{b['outcome']} EV={b['ev']:+.3f}" for b in value_bets) or "none"
    print(f"  {match_id}: patched (value_bets: {vb_str})")
    return True


def main():
    if "--batch" in sys.argv:
        idx = sys.argv.index("--batch")
        batch_file = sys.argv[idx + 1]
        with open(batch_file, encoding="utf-8") as f:
            batch = json.load(f)
        for mid, odds in batch.items():
            patch_match(mid, odds["home"], odds["draw"], odds["away"])

    elif "--match" in sys.argv:
        idx = sys.argv.index("--match")
        match_id = sys.argv[idx + 1]
        home  = float(sys.argv[sys.argv.index("--home")  + 1])
        draw  = float(sys.argv[sys.argv.index("--draw")  + 1])
        away  = float(sys.argv[sys.argv.index("--away")  + 1])
        patch_match(match_id, home, draw, away)

    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
