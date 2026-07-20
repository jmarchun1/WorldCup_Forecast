"""
replay_consensus.py — Re-apply consensus logic to existing backtest outputs.

Tests post-processing improvements (goal rescaling, EV commit, draw floor)
against the 66-match scored corpus without making new API calls.

Usage:
    python replay_consensus.py --variant contest
    python replay_consensus.py --variant contest --goal-rescale 1.30
    python replay_consensus.py --variant contest --ev-commit --goal-rescale 1.20
    python replay_consensus.py --variant contest --ev-commit --goal-rescale 1.20 --draw-floor-gap 0.10
"""

import argparse
import collections
import json
import os
import statistics
import sys
from typing import Optional

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
BACKTEST_DIR = os.path.join(BASE_DIR, "results", "backtest_prompts")
DATA_DIR    = os.path.join(BASE_DIR, "data")


def _result(h, a):
    if h > a: return "home_win"
    if a > h: return "away_win"
    return "draw"


def _fantasy_points(ph, pa, ah, aa):
    if ph == ah and pa == aa:
        return 4
    pr = _result(ph, pa)
    ar = _result(ah, aa)
    if pr != ar:
        return 0
    if ar != "draw" and abs(ph - pa) == abs(ah - aa):
        return 2
    return 1


def _brier(hw, dp, aw, actual_outcome):
    o = {"home_win": (1,0,0), "draw": (0,1,0), "away_win": (0,0,1)}[actual_outcome]
    return (hw - o[0])**2 + (dp - o[1])**2 + (aw - o[2])**2


def _rescale_goals(home_goals_list, away_goals_list, factor):
    """Rescale predicted goals by factor, preserving result direction."""
    out_h, out_a = [], []
    for h, a in zip(home_goals_list, away_goals_list):
        total = h + a
        if total == 0:
            out_h.append(h)
            out_a.append(a)
            continue
        new_total = total * factor
        if h == a:
            g = max(0, round(new_total / 2))
            out_h.append(g)
            out_a.append(g)
        elif h > a:
            ratio = h / total
            new_h = max(h, round(new_total * ratio))
            new_a = max(a, round(new_total * (1 - ratio)))
            out_h.append(new_h)
            out_a.append(new_a)
        else:
            ratio = a / total
            new_a = max(a, round(new_total * ratio))
            new_h = max(h, round(new_total * (1 - ratio)))
            out_h.append(new_h)
            out_a.append(new_a)
    return out_h, out_a


def _compute_consensus(records, goal_rescale=0.0, ev_commit=False,
                       draw_floor_gap=0.0, draw_override_threshold=0.0,
                       match_data: Optional[dict] = None):
    """Compute consensus scoreline from a list of per-model records."""
    home_goals_list = [r["home_goals"] for r in records]
    away_goals_list = [r["away_goals"] for r in records]

    # Weighted probability averages (equal weights — same as backtest default)
    n = len(records)
    avg_hw = sum(r["home_win_prob"] for r in records) / n
    avg_dp = sum(r["draw_prob"]     for r in records) / n
    avg_aw = sum(r["away_win_prob"] for r in records) / n

    # Goal rescaling
    if goal_rescale > 0:
        home_goals_list, away_goals_list = _rescale_goals(
            home_goals_list, away_goals_list, goal_rescale
        )

    # Scoreline weights (equal weights)
    scoreline_weights = collections.defaultdict(float)
    for h_g, a_g in zip(home_goals_list, away_goals_list):
        scoreline_weights[(h_g, a_g)] += 1.0 / n

    # EV commit rule
    if ev_commit:
        total_sw = sum(scoreline_weights.values())

        def _ev(h, a):
            p_exact = scoreline_weights.get((h, a), 0.0) / total_sw
            gd = h - a
            p_same_gd = sum(w for (sh, sa), w in scoreline_weights.items()
                            if sh - sa == gd and (sh, sa) != (h, a)) / total_sw
            result = (1 if h > a else (-1 if h < a else 0))
            p_same_result = sum(w for (sh, sa), w in scoreline_weights.items()
                                if (1 if sh > sa else (-1 if sh < sa else 0)) == result
                                and sh - sa != gd) / total_sw
            return p_exact * 4 + p_same_gd * 2 + p_same_result * 1

        mode_home, mode_away = max(scoreline_weights.keys(), key=lambda s: _ev(s[0], s[1]))
    else:
        best = max(scoreline_weights.items(), key=lambda x: x[1])
        top_w = best[1]
        top = [s for s, w in scoreline_weights.items() if abs(w - top_w) < 1e-9]
        if len(top) == 1:
            mode_home, mode_away = top[0]
        else:
            if avg_hw > avg_aw:
                top.sort(key=lambda s: s[0] - s[1], reverse=True)
            else:
                top.sort(key=lambda s: s[1] - s[0], reverse=True)
            mode_home, mode_away = top[0]

    consensus_home, consensus_away = mode_home, mode_away

    # Draw override (existing logic)
    if draw_override_threshold > 0 and avg_dp >= draw_override_threshold and consensus_home != consensus_away:
        all_goals = home_goals_list + away_goals_list
        tie_g = round(statistics.mean(all_goals) / 2) if all_goals else 1
        consensus_home = tie_g
        consensus_away = tie_g

    # Draw floor (new v12 logic)
    if draw_floor_gap > 0 and consensus_home != consensus_away and match_data:
        implied_draw = match_data.get("odds", {}).get("implied_draw", 0.0) or 0.0
        if implied_draw > 0 and (implied_draw - avg_dp) >= draw_floor_gap:
            all_goals = home_goals_list + away_goals_list
            tie_g = round(statistics.mean(all_goals) / 2) if all_goals else 1
            consensus_home = tie_g
            consensus_away = tie_g

    return consensus_home, consensus_away, avg_hw, avg_dp, avg_aw


def load_match_data(match_id: str) -> Optional[dict]:
    path = os.path.join(DATA_DIR, f"{match_id}.json")
    if os.path.exists(path):
        return json.load(open(path, encoding="utf-8"))
    return None


def run(variant: str, goal_rescale: float = 0.0, ev_commit: bool = False,
        draw_floor_gap: float = 0.0, draw_override_threshold: float = 0.35,
        verbose: bool = False):
    variant_dir = os.path.join(BACKTEST_DIR, variant)
    if not os.path.exists(variant_dir):
        print(f"ERROR: no backtest data at {variant_dir}")
        sys.exit(1)

    # Group records by match_id
    by_match = collections.defaultdict(list)
    for fname in os.listdir(variant_dir):
        if not fname.endswith(".json"):
            continue
        rec = json.load(open(os.path.join(variant_dir, fname), encoding="utf-8"))
        if rec.get("error") or rec.get("home_goals") is None:
            continue
        # Skip corrupted probability records
        for field in ("home_win_prob", "draw_prob", "away_win_prob"):
            if (rec.get(field) or 0) > 1.0:
                break
        else:
            by_match[rec["match_id"]].append(rec)

    # Collect original per-model stats for comparison
    orig_total_pts = 0
    orig_n = 0
    new_total_pts = 0
    new_n = 0
    changes = []

    for match_id, records in sorted(by_match.items()):
        if not records:
            continue
        actual_home = records[0]["actual_home"]
        actual_away = records[0]["actual_away"]
        actual_outcome = _result(actual_home, actual_away)

        # Original consensus (equal weights, no rescaling)
        orig_h, orig_a, _, _, _ = _compute_consensus(
            records,
            goal_rescale=0.0, ev_commit=False,
            draw_floor_gap=0.0, draw_override_threshold=draw_override_threshold,
        )

        # New consensus with requested improvements
        match_data = load_match_data(match_id)
        new_h, new_a, avg_hw, avg_dp, avg_aw = _compute_consensus(
            records,
            goal_rescale=goal_rescale, ev_commit=ev_commit,
            draw_floor_gap=draw_floor_gap,
            draw_override_threshold=draw_override_threshold,
            match_data=match_data,
        )

        orig_pts = _fantasy_points(orig_h, orig_a, actual_home, actual_away)
        new_pts  = _fantasy_points(new_h,  new_a,  actual_home, actual_away)

        orig_total_pts += orig_pts
        orig_n += 1
        new_total_pts += new_pts
        new_n += 1

        if orig_h != new_h or orig_a != new_a:
            delta = new_pts - orig_pts
            changes.append({
                "match_id": match_id,
                "actual": f"{actual_home}-{actual_away}",
                "orig": f"{orig_h}-{orig_a} ({orig_pts}pts)",
                "new": f"{new_h}-{new_a} ({new_pts}pts)",
                "delta": delta,
                "avg_dp": round(avg_dp, 3),
            })

    orig_ppg = orig_total_pts / orig_n if orig_n else 0
    new_ppg  = new_total_pts  / new_n  if new_n  else 0

    print(f"\n=== Replay: {variant} | goal_rescale={goal_rescale} ev_commit={ev_commit} draw_floor_gap={draw_floor_gap} ===")
    print(f"Matches: {orig_n}")
    print(f"Original consensus PPG: {orig_ppg:.3f}  ({orig_total_pts}pts)")
    print(f"New consensus PPG:      {new_ppg:.3f}  ({new_total_pts}pts)  d={new_ppg - orig_ppg:+.3f}")
    print(f"Changed predictions: {len(changes)}")

    if changes:
        gains   = [c for c in changes if c["delta"] > 0]
        losses  = [c for c in changes if c["delta"] < 0]
        neutral = [c for c in changes if c["delta"] == 0]
        print(f"  Gained: {len(gains)}  Lost: {len(losses)}  Neutral: {len(neutral)}")
        if verbose:
            print("\nAll changes:")
            for c in sorted(changes, key=lambda x: -abs(x["delta"])):
                print(f"  {c['match_id']:45s}  actual={c['actual']}  {c['orig']} -> {c['new']}  dp={c['avg_dp']}  Δ={c['delta']:+d}")
        else:
            if gains:
                print("\nTop gains:")
                for c in sorted(gains, key=lambda x: -x["delta"])[:10]:
                    print(f"  {c['match_id']:45s}  actual={c['actual']}  {c['orig']} -> {c['new']}  dp={c['avg_dp']}")
            if losses:
                print("\nLosses:")
                for c in sorted(losses, key=lambda x: x["delta"])[:10]:
                    print(f"  {c['match_id']:45s}  actual={c['actual']}  {c['orig']} -> {c['new']}  dp={c['avg_dp']}")
    return new_ppg - orig_ppg


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--variant", default="contest")
    p.add_argument("--goal-rescale", type=float, default=0.0,
                   help="Goal total multiplier e.g. 1.30")
    p.add_argument("--ev-commit", action="store_true",
                   help="Use EV commit rule instead of modal scoreline")
    p.add_argument("--draw-floor-gap", type=float, default=0.0,
                   help="Override to draw when implied_draw > avg_dp by this gap")
    p.add_argument("--draw-override-threshold", type=float, default=0.35,
                   help="Existing draw override threshold (default 0.35)")
    p.add_argument("--grid-search", action="store_true",
                   help="Run a grid search over rescale factors")
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args()

    if args.grid_search:
        print("Grid search over goal_rescale and ev_commit...")
        best_delta = 0.0
        best_cfg = {}
        for rescale in [0.0, 1.10, 1.20, 1.25, 1.30, 1.35, 1.40]:
            for ev in [False, True]:
                for dfg in [0.0, 0.08, 0.10, 0.12]:
                    delta = run(args.variant, goal_rescale=rescale, ev_commit=ev,
                                draw_floor_gap=dfg,
                                draw_override_threshold=args.draw_override_threshold)
                    if delta > best_delta:
                        best_delta = delta
                        best_cfg = {"rescale": rescale, "ev_commit": ev, "draw_floor_gap": dfg}
        print(f"\nBest config: {best_cfg}  delta={best_delta:+.3f}")
    else:
        run(args.variant,
            goal_rescale=args.goal_rescale,
            ev_commit=args.ev_commit,
            draw_floor_gap=args.draw_floor_gap,
            draw_override_threshold=args.draw_override_threshold,
            verbose=args.verbose)


if __name__ == "__main__":
    main()
