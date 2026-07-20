"""
score.py — Score completed World Cup matches using the 4/2/1/1 fantasy points system.

Scoring rules:
  4 pts — exact scoreline (both teams' goals correct)
  2 pts — correct result + exact goal difference (not for draws)
  1 pt  — correct result only
  1 pt  — correct draw (wrong score)
  0 pts — wrong result

Also computes:
  - Brier score (probability calibration)
  - EV realized (was the value bet correct?)
  - Cost per point

Usage:
    python score.py --match Mexico_Poland_2026-06-11 --result "2-1"
    python score.py --date 2026-06-11 --results "Mexico_Poland 2-1, Saudi_Arabia_Argentina 0-1"
    python score.py --date 2026-06-11  # interactive prompt for each match
"""

import json
import os
import sys
from datetime import date
from typing import Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
FORECASTS_DIR = os.path.join(BASE_DIR, "results", "forecasts")
SCORED_DIR = os.path.join(BASE_DIR, "results", "scored")
os.makedirs(SCORED_DIR, exist_ok=True)


def _load_config() -> dict:
    with open(os.path.join(BASE_DIR, "config.json")) as f:
        return json.load(f)


def _fantasy_points(pred_home: int, pred_away: int, actual_home: int, actual_away: int) -> tuple[int, str]:
    """Return (points, breakdown_label) for a single prediction."""
    # Exact scoreline
    if pred_home == actual_home and pred_away == actual_away:
        return 4, "exact_score"

    pred_result = _result(pred_home, pred_away)
    actual_result = _result(actual_home, actual_away)

    if pred_result != actual_result:
        return 0, "wrong_result"

    # Correct result — check goal difference (not for draws)
    if actual_result != "draw":
        pred_gd = abs(pred_home - pred_away)
        actual_gd = abs(actual_home - actual_away)
        if pred_gd == actual_gd:
            return 2, "correct_result_exact_gd"

    # Correct draw (wrong score)
    if actual_result == "draw":
        return 1, "correct_draw"

    # Correct result only
    return 1, "correct_result"


def _result(home: int, away: int) -> str:
    if home > away:
        return "home_win"
    if away > home:
        return "away_win"
    return "draw"


def _brier_score(probs: dict, actual_outcome: str) -> float:
    """Multi-class Brier score (sum of squared errors across 3 outcomes, undivided).
    Range 0.0–2.0. Matches football forecasting literature convention (e.g. onthepitch.now).
    Random baseline = 0.667. Perfect = 0.0.
    """
    outcomes = ["home_win", "draw", "away_win"]
    return round(sum(
        (probs.get(o, 0) - (1 if o == actual_outcome else 0)) ** 2
        for o in outcomes
    ), 4)


def score_match(match_id: str, actual_home: int, actual_away: int) -> list[dict]:
    """Score all model forecasts for one match. Returns list of scored records."""
    actual_outcome = _result(actual_home, actual_away)
    scored = []

    for fname in os.listdir(FORECASTS_DIR):
        if not fname.startswith(match_id) or fname.endswith("_CONSENSUS.json"):
            continue
        if not fname.endswith(".json"):
            continue
        # Exclude files that start with match_id but are for a different match
        # e.g. "Mexico_Poland_2026-06-11_haiku.json" must start with match_id exactly
        suffix = fname[len(match_id):]
        if not suffix.startswith("_"):
            continue

        fpath = os.path.join(FORECASTS_DIR, fname)
        with open(fpath, encoding="utf-8") as f:
            rec = json.load(f)

        if rec.get("error") and rec.get("error") != "missing horizons":
            continue
        if rec.get("home_goals") is None or rec.get("away_goals") is None:
            continue

        # Guard: skip web-search-capable models if forecast was generated on or after the match.
        # Sonar/SonarPro can look up results via real-time search, tainting their scores.
        # Same-day forecasts are also excluded (result may already be indexed).
        WEB_SEARCH_MODELS = {"sonar", "sonarpro"}
        forecast_date = rec.get("forecast_date", "")
        match_date = match_id[-10:] if len(match_id) >= 10 else ""
        if (rec.get("model_short") in WEB_SEARCH_MODELS
                and forecast_date and match_date and forecast_date >= match_date):
            continue

        pred_home = int(rec["home_goals"])
        pred_away = int(rec["away_goals"])
        points, breakdown = _fantasy_points(pred_home, pred_away, actual_home, actual_away)

        probs = {
            "home_win": rec.get("home_win_prob") or 0,
            "draw": rec.get("draw_prob") or 0,
            "away_win": rec.get("away_win_prob") or 0,
        }
        brier = _brier_score(probs, actual_outcome)

        cost_usd = rec.get("cost_usd", 0.0)
        cost_per_point = round(cost_usd / points, 8) if points > 0 else None

        # EV: was the flagged value bet correct?
        # Uses kalshi_odds when available (live market prices), else falls back to Sonar-parsed odds.
        consensus_path = os.path.join(FORECASTS_DIR, f"{match_id}_CONSENSUS.json")
        ev_value_bet = None
        ev_correct = None
        ev_home = ev_draw = ev_away = None
        kalshi_ev_value_bet = None
        kalshi_ev_correct = None
        kalshi_ev_home = kalshi_ev_draw = kalshi_ev_away = None
        if os.path.exists(consensus_path):
            with open(consensus_path) as cf:
                cons = json.load(cf)
            ev_home = cons.get("ev_home_win")
            ev_draw = cons.get("ev_draw")
            ev_away = cons.get("ev_away_win")
            value_bets = cons.get("value_bets", [])
            if value_bets:
                best_bet = max(value_bets, key=lambda b: b["ev"])
                ev_value_bet = best_bet["outcome"]
                ev_correct = (ev_value_bet == actual_outcome)

            # Per-model EV using live Kalshi odds + this model's own probabilities
            kalshi = cons.get("kalshi_odds")
            if kalshi:
                def _ev(p, odds): return p * (odds - 1) - (1 - p)
                kh = _ev(probs["home_win"], kalshi["home"])
                kd = _ev(probs["draw"],     kalshi["draw"])
                ka = _ev(probs["away_win"], kalshi["away"])
                kalshi_ev_home  = round(kh, 4)
                kalshi_ev_draw  = round(kd, 4)
                kalshi_ev_away  = round(ka, 4)
                best = max([("home", kh, kalshi["home"]), ("draw", kd, kalshi["draw"]), ("away", ka, kalshi["away"])],
                           key=lambda x: x[1])
                if best[1] > 0.05:
                    kalshi_ev_value_bet = best[0]
                    kalshi_ev_correct = (best[0] == actual_outcome)

        scored_rec = {
            "match_id": match_id,
            "scored_date": date.today().isoformat(),
            "forecast_date": rec.get("forecast_date", ""),
            "model_short": rec.get("model_short"),
            "model_id": rec.get("model_id"),
            "vendor": rec.get("vendor"),
            "predicted_home": pred_home,
            "predicted_away": pred_away,
            "actual_home": actual_home,
            "actual_away": actual_away,
            "actual_outcome": actual_outcome,
            "points": points,
            "score_breakdown": breakdown,
            "home_win_prob": probs["home_win"],
            "draw_prob": probs["draw"],
            "away_win_prob": probs["away_win"],
            "brier_score": brier,
            "confidence": rec.get("confidence"),
            "reasoning": rec.get("reasoning"),
            "cost_usd": cost_usd,
            "cost_per_point": cost_per_point,
            "ev_home_win": ev_home,
            "ev_draw": ev_draw,
            "ev_away_win": ev_away,
            "ev_value_bet": ev_value_bet,
            "ev_correct": ev_correct,
            "kalshi_ev_home_win": kalshi_ev_home,
            "kalshi_ev_draw": kalshi_ev_draw,
            "kalshi_ev_away_win": kalshi_ev_away,
            "kalshi_ev_value_bet": kalshi_ev_value_bet,
            "kalshi_ev_correct": kalshi_ev_correct,
        }

        out_path = os.path.join(SCORED_DIR, f"{match_id}_{rec.get('model_short', 'unknown')}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(scored_rec, f, indent=2, ensure_ascii=False)

        scored.append(scored_rec)

    return scored


def _parse_result_string(s: str) -> tuple[int, int]:
    """Parse '2-1' or '2 1' into (home_goals, away_goals)."""
    s = s.strip()
    m = None
    for sep in ("-", " ", ":"):
        parts = s.split(sep)
        if len(parts) == 2:
            try:
                return int(parts[0].strip()), int(parts[1].strip())
            except ValueError:
                continue
    raise ValueError(f"Cannot parse result string: {s!r}")


def load_all_scored() -> list[dict]:
    """Load all scored forecast files."""
    records = []
    for fname in os.listdir(SCORED_DIR):
        if not fname.endswith(".json"):
            continue
        with open(os.path.join(SCORED_DIR, fname), encoding="utf-8") as f:
            records.append(json.load(f))
    return records


def main():
    filter_match = None
    filter_date = None
    result_str = None
    results_str = None

    if "--match" in sys.argv:
        idx = sys.argv.index("--match")
        filter_match = sys.argv[idx + 1]
    if "--result" in sys.argv:
        idx = sys.argv.index("--result")
        result_str = sys.argv[idx + 1]
    if "--date" in sys.argv:
        idx = sys.argv.index("--date")
        filter_date = sys.argv[idx + 1]
    if "--results" in sys.argv:
        idx = sys.argv.index("--results")
        results_str = sys.argv[idx + 1]

    if filter_match and result_str:
        actual_home, actual_away = _parse_result_string(result_str)
        scored = score_match(filter_match, actual_home, actual_away)
        print(f"Scored {len(scored)} forecasts for {filter_match}: {actual_home}-{actual_away}")
        for s in sorted(scored, key=lambda x: -x["points"]):
            print(f"  {s['model_short']:15s} {s['predicted_home']}-{s['predicted_away']} -> {s['points']}pts ({s['score_breakdown']})")
        return

    if filter_date:
        # Find matches for this date from data/ directory
        match_ids = []
        for fname in os.listdir(DATA_DIR):
            if fname.endswith(".json") and filter_date in fname:
                match_ids.append(fname.replace(".json", ""))

        if not match_ids:
            print(f"No match data files found for {filter_date}")
            return

        # Parse results from --results flag or interactive
        result_map = {}
        if results_str:
            for part in results_str.split(","):
                part = part.strip()
                # Try "MatchID SCORE" or just "SCORE" if only one match
                tokens = part.rsplit(" ", 1)
                if len(tokens) == 2:
                    # Try to match against known match_ids
                    matched = None
                    for mid in match_ids:
                        if tokens[0].replace(" ", "_") in mid or mid.startswith(tokens[0].replace(" ", "_")):
                            matched = mid
                            break
                    if matched:
                        result_map[matched] = tokens[1]
                    else:
                        # Assume it's just a score for the only/first match
                        for mid in match_ids:
                            if mid not in result_map:
                                result_map[mid] = tokens[1]
                                break
                else:
                    for mid in match_ids:
                        if mid not in result_map:
                            result_map[mid] = part
                            break

        total_scored = 0
        for mid in match_ids:
            if mid in result_map:
                res = result_map[mid]
            else:
                res = input(f"Enter result for {mid} (e.g. 2-1, or blank to skip): ").strip()
                if not res:
                    continue
            try:
                actual_home, actual_away = _parse_result_string(res)
            except ValueError as e:
                print(f"  Skipping {mid}: {e}")
                continue
            scored = score_match(mid, actual_home, actual_away)
            total_scored += len(scored)
            print(f"  {mid}: {actual_home}-{actual_away} → scored {len(scored)} forecasts")
            for s in sorted(scored, key=lambda x: -x["points"])[:3]:
                print(f"    {s['model_short']:15s} predicted {s['predicted_home']}-{s['predicted_away']} → {s['points']}pts")

        print(f"\nTotal scored: {total_scored}")
        return

    print("Usage:")
    print("  python score.py --match MATCH_ID --result 2-1")
    print("  python score.py --date 2026-06-11")
    print("  python score.py --date 2026-06-11 --results 'Mexico_Poland_2026-06-11 2-1'")


if __name__ == "__main__":
    main()
