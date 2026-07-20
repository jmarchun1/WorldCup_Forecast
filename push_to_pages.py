"""
push_to_pages.py — Build static dashboard and push to GitHub Pages repo.

Reads all forecast/scored/consensus JSON from world-cup-forecasting/,
injects into the HTML template, then commits and pushes to the WCFCST repo.

Usage:
    python push_to_pages.py
    python push_to_pages.py --no-push   # build only, don't git push
"""

import json
import os
import subprocess
import sys
from collections import defaultdict
from datetime import datetime

_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

# Paths
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
FORECASTS_DIR = os.path.join(BASE_DIR, "results", "forecasts")
ARCHIVE_DIR = os.path.join(BASE_DIR, "results", "forecasts", "archive")
SCORED_DIR  = os.path.join(BASE_DIR, "results", "scored")
BONUS_DIR   = os.path.join(BASE_DIR, "results", "bonus")
TEMPLATE    = os.path.join(BASE_DIR, "docs", "_template.html")
PAGES_REPO  = r"C:\Users\I846720\OneDrive\Github\WCFCST"
OUT_FILE    = os.path.join(PAGES_REPO, "index.html")

# Fixtures list (matches fixtures.py exactly)
from fixtures import FIXTURES


def _load_dir(path):
    records = []
    if not os.path.exists(path):
        return records
    for fname in sorted(os.listdir(path)):
        if not fname.endswith(".json"):
            continue
        try:
            with open(os.path.join(path, fname), encoding="utf-8") as f:
                records.append(json.load(f))
        except Exception as e:
            print(f"  Warning: could not load {fname}: {e}")
    return records


def _build_accuracy_stats(scored: list, consensus: list = None) -> dict:
    """Aggregate per-model accuracy stats from scored records.

    Returns a dict with:
      - model_stats: [{model, pts, games, exact, correct_gd, correct_result, zero, brier_sum, brier_avg}]
        The CONSENSUS ensemble row is prepended as the first entry.
      - phase_stats: {model: {phase: {pts, games, brier_sum}}}
      - overall: {pts, games, exact, brier_avg}
    """
    model_acc = defaultdict(lambda: {
        "pts": 0, "games": 0, "exact": 0, "correct_gd": 0,
        "correct_result": 0, "zero": 0, "brier_sum": 0.0,
    })
    phase_acc = defaultdict(lambda: defaultdict(lambda: {
        "pts": 0, "games": 0, "brier_sum": 0.0,
    }))

    for rec in scored:
        model = rec.get("model_short", "unknown")
        pts = rec.get("points") or 0
        bd = rec.get("score_breakdown", "")
        brier = rec.get("brier_score") or 0.0
        stage = rec.get("stage", "GROUP_STAGE")

        m = model_acc[model]
        m["pts"]   += pts
        m["games"] += 1
        m["brier_sum"] += brier
        if bd == "exact_score":            m["exact"]          += 1
        elif bd == "correct_result_exact_gd": m["correct_gd"]  += 1
        elif bd == "correct_result":        m["correct_result"] += 1
        else:                               m["zero"]           += 1

        p = phase_acc[model][stage]
        p["pts"]       += pts
        p["games"]     += 1
        p["brier_sum"] += brier

    model_stats = []
    for model, m in sorted(model_acc.items(), key=lambda x: -(x[1]["pts"])):
        g = m["games"]
        model_stats.append({
            "model": model,
            "pts": m["pts"],
            "games": g,
            "exact": m["exact"],
            "correct_gd": m["correct_gd"],
            "correct_result": m["correct_result"],
            "zero": m["zero"],
            "brier_avg": round(m["brier_sum"] / g, 4) if g else None,
            "pts_per_game": round(m["pts"] / g, 2) if g else None,
        })

    # Compute CONSENSUS row from live consensus files cross-referenced with actuals
    if consensus:
        actuals_by_mid = {}
        for rec in scored:
            mid = rec.get("match_id", "")
            if mid and mid not in actuals_by_mid and rec.get("actual_home") is not None:
                actuals_by_mid[mid] = (rec["actual_home"], rec["actual_away"])

        def _res(h, a):
            return "home_win" if h > a else ("away_win" if a > h else "draw")

        def _fp(ph, pa, ah, aa):
            if ph == ah and pa == aa: return 4, "exact_score"
            pr, ar = _res(ph, pa), _res(ah, aa)
            if pr != ar: return 0, "zero"
            if ar != "draw" and abs(ph - pa) == abs(ah - aa): return 2, "correct_result_exact_gd"
            if ar == "draw": return 1, "correct_draw"
            return 1, "correct_result"

        c_pts = c_games = c_exact = c_gd = c_result = c_zero = 0
        c_brier = 0.0
        for crec in consensus:
            mid = crec.get("match_id", "")
            if mid not in actuals_by_mid:
                continue
            ah, aa = actuals_by_mid[mid]
            ph = crec.get("consensus_home_goals")
            pa = crec.get("consensus_away_goals")
            if ph is None or pa is None:
                continue
            pts, bd = _fp(int(round(ph)), int(round(pa)), ah, aa)
            hw = crec.get("avg_home_win_prob") or 0.0
            dp = crec.get("avg_draw_prob") or 0.0
            aw = crec.get("avg_away_win_prob") or 0.0
            ao = _res(ah, aa)
            brier = ((hw - (1.0 if ao=="home_win" else 0.0))**2
                   + (dp - (1.0 if ao=="draw" else 0.0))**2
                   + (aw - (1.0 if ao=="away_win" else 0.0))**2)
            c_pts += pts; c_games += 1; c_brier += brier
            if bd == "exact_score":               c_exact  += 1
            elif bd == "correct_result_exact_gd": c_gd     += 1
            elif bd == "correct_result":          c_result += 1
            elif bd == "correct_draw":            c_result += 1
            else:                                 c_zero   += 1

        if c_games:
            consensus_row = {
                "model": "CONSENSUS",
                "pts": c_pts,
                "games": c_games,
                "exact": c_exact,
                "correct_gd": c_gd,
                "correct_result": c_result,
                "zero": c_zero,
                "brier_avg": round(c_brier / c_games, 4),
                "pts_per_game": round(c_pts / c_games, 2),
                "is_consensus": True,
            }
            model_stats.insert(0, consensus_row)

    # Phase breakdown: {model: [{phase, pts, games, brier_avg}]}
    phase_stats = {}
    for model, phases in phase_acc.items():
        phase_stats[model] = [
            {
                "phase": phase,
                "pts": p["pts"],
                "games": p["games"],
                "brier_avg": round(p["brier_sum"] / p["games"], 4) if p["games"] else None,
            }
            for phase, p in sorted(phases.items())
        ]

    total_games = sum(m["games"] for m in model_acc.values())
    total_pts   = sum(m["pts"]   for m in model_acc.values())
    brier_vals  = [m["brier_sum"] / m["games"] for m in model_acc.values() if m["games"]]

    return {
        "model_stats": model_stats,
        "phase_stats": phase_stats,
        "overall": {
            "pts": total_pts,
            "games_model": total_games,
            "brier_avg": round(sum(brier_vals) / len(brier_vals), 4) if brier_vals else None,
        },
    }


# Release notes keyed by archive stamp prefix (YYYYMMDD-HHMM or YYYYMMDD). First match wins.
RELEASE_NOTES = {
    "20260617-1332": (
        "v1: initial 12-model ensemble (Claude/GPT/Gemini/Perplexity). "
        "72 matches forecast. No scoreline output — probabilities only."
    ),
    "20260617-1659": (
        "v2: re-run same day to fix raw_response parse issues. "
        "No scoreline or probability changes vs v1."
    ),
    "20260620-1452": (
        "v3: fix null-goals scoring bug (Sonar/SonarPro null coercion), "
        "fix gpt5 parse errors (response_format json_object, 4096 token limit), "
        "draw base-rate reminder added to prompt (~26% WC draw rate), "
        "explicit scoreline instruction added ('Predicted score: X-Y'), "
        "WC 2026 key injury absences injected into prompt context. "
        "17 scoreline changes vs v2."
    ),
    "20260620-1509": (
        "v4: dead-rubber MD3 detection added (both-teams-qualified/eliminated warning), "
        "PELE Tilt style ratings injected for ~20 teams (attacking vs defensive tendency), "
        "cross-version accuracy comparison table added to dashboard. "
        "23 scoreline changes vs v3 — draw predictions increased."
    ),
    "20260624-1529": (
        "v5: full re-run with fresher pre-match context (Jun 24). "
        "22 scoreline changes vs v4 — reverted many draw predictions back to home wins."
    ),
    "20260624-2237": (
        "v6: prompt tuning — stronger draw-calibration signal and scoreline diversity instruction. "
        "Best PPG version (1.322). 26 scoreline changes vs v5; "
        "+6 exact score gains (Canada-Bosnia 1-1, Czech-S.Africa 1-1, France-Iraq 3-0, "
        "Germany-Ivory Coast 2-1, Colombia 1-0, Japan-Sweden 1-1)."
    ),
    "20260624-2308": (
        "v7: incremental prompt refinement. 6 scoreline changes vs v6 — "
        "shifted several 1-0 home wins to 1-1 draws (Norway-France, Senegal-Iraq)."
    ),
    "20260624-2349": (
        "v8: further prompt iteration. 8 scoreline changes vs v7 — "
        "reverted some draws back to decisive results."
    ),
    "20260625-1912": (
        "v9: re-run incorporating Jun 25 MD2 results as context. "
        "14 scoreline changes vs v8 — Curacao-Ivory Coast 0-3, Colombia-Portugal 1-1."
    ),
    "20260625-1914": (
        "v10: added USA-Turkey (Jun 25 late kick-off) — 73 matches total. "
        "Bayesian model weighting introduced in consensus. No other scoreline changes vs v9."
    ),
    "20260627-1652": (
        "v11 (Sprint A — prompt calibration): goal volume prior updated to WC2026 in-tournament average (2.9 goals/match). "
        "5-check calibration block added: goal volume audit, 1-1 attractor suppression (2x overrepresentation warning), "
        "explicit upset prior injection, minority scenario forcing, Brier-score loss framing. "
        "MD3 pressure asymmetry module: one team settled, one competing — injects rotation and free-wheeling context. "
        "Mean predicted goals jumped 1.94→2.60 on Jun 27 matches (+34% toward 2.9 tournament actual). "
        "13 Round of 32 fixtures added (Jun 28–Jul 3). USA name fix for GoalLab compatibility."
    ),
}


def _build_version_history() -> list:
    """Return list of archived forecast versions with metadata for the dashboard."""
    if not os.path.exists(ARCHIVE_DIR):
        return []
    versions = []
    for stamp in sorted(os.listdir(ARCHIVE_DIR)):
        stamp_dir = os.path.join(ARCHIVE_DIR, stamp)
        if not os.path.isdir(stamp_dir):
            continue
        files = [f for f in os.listdir(stamp_dir) if f.endswith(".json") and "_CONSENSUS" not in f]
        match_ids = set()
        for f in files:
            parts = f.replace(".json", "").rsplit("_", 1)
            if len(parts) == 2:
                match_ids.add(parts[0])
        # Find release notes
        notes = ""
        for prefix, note in RELEASE_NOTES.items():
            if stamp.startswith(prefix):
                notes = note
                break
        versions.append({
            "version_id": stamp,
            "archived_at": stamp,
            "n_forecasts": len(files),
            "n_matches": len(match_ids),
            "notes": notes,
        })
    return versions


def _build_cross_version_accuracy() -> list:
    """For each archive version, compute consensus accuracy metrics from its scored data.

    Reads the archive's CONSENSUS forecast files, cross-references with results/scored/
    to find actual outcomes, and returns per-version P/G, exact%, draw_pred%, Brier.
    Only versions with >=5 scored matches are included.
    """
    if not os.path.exists(ARCHIVE_DIR) or not os.path.exists(SCORED_DIR):
        return []

    # Build a lookup of actual results by match_id from the current scored dir
    actuals: dict = {}
    for fname in os.listdir(SCORED_DIR):
        if not fname.endswith(".json"):
            continue
        try:
            with open(os.path.join(SCORED_DIR, fname), encoding="utf-8") as f:
                rec = json.load(f)
            mid = rec.get("match_id", "")
            if mid and mid not in actuals:
                actuals[mid] = {
                    "actual_home": rec.get("actual_home"),
                    "actual_away": rec.get("actual_away"),
                    "actual_outcome": rec.get("actual_outcome"),
                }
        except Exception:
            continue

    results = []
    for stamp in sorted(os.listdir(ARCHIVE_DIR)):
        adir = os.path.join(ARCHIVE_DIR, stamp)
        if not os.path.isdir(adir):
            continue

        pts_total = 0
        exact = 0
        draw_pred = 0
        brier_sum = 0.0
        matches = 0

        for fname in os.listdir(adir):
            if not fname.endswith("_CONSENSUS.json"):
                continue
            try:
                with open(os.path.join(adir, fname), encoding="utf-8") as f:
                    rec = json.load(f)
            except Exception:
                continue

            mid = rec.get("match_id", "")
            actual = actuals.get(mid)
            if not actual or actual["actual_home"] is None:
                continue

            ah = actual["actual_home"]
            aa = actual["actual_away"]
            ph_raw = rec.get("consensus_home_goals")
            pa_raw = rec.get("consensus_away_goals")
            hw = rec.get("avg_home_win_prob") or 0.0
            dp = rec.get("avg_draw_prob") or 0.0
            aw = rec.get("avg_away_win_prob") or 0.0
            if ph_raw is None or pa_raw is None:
                continue
            ph = round(ph_raw)
            pa = round(pa_raw)

            matches += 1
            # Points (same logic as score.py)
            actual_outcome = "home_win" if ah > aa else ("draw" if ah == aa else "away_win")
            pred_outcome = "home_win" if ph > pa else ("draw" if ph == pa else "away_win")
            pts = 0
            if ph == ah and pa == aa:
                pts = 4
            elif pred_outcome == actual_outcome:
                if actual_outcome != "draw" and abs(ph - pa) == abs(ah - aa):
                    pts = 2
                else:
                    pts = 1
            pts_total += pts
            if ph == ah and pa == aa:
                exact += 1
            # Draw prediction: did the model give draw the highest prob?
            if dp >= hw and dp >= aw:
                draw_pred += 1
            # Brier score
            o_hw = 1.0 if actual_outcome == "home_win" else 0.0
            o_d = 1.0 if actual_outcome == "draw" else 0.0
            o_aw = 1.0 if actual_outcome == "away_win" else 0.0
            brier_sum += ((hw - o_hw) ** 2 + (dp - o_d) ** 2 + (aw - o_aw) ** 2)

        if matches < 5:
            continue

        notes = next((v for k, v in RELEASE_NOTES.items() if stamp.startswith(k)), "")
        results.append({
            "version_id": stamp,
            "matches": matches,
            "pts_per_game": round(pts_total / matches, 3),
            "exact_pct": round(exact / matches * 100, 1),
            "draw_pred_pct": round(draw_pred / matches * 100, 1),
            "brier_mean": round(brier_sum / matches, 4),
            "notes": notes,
        })

    return results


def _build_market_benchmark() -> dict:
    """Compare consensus model Brier vs Kalshi market implied Brier on completed matches.

    For each finished match that has kalshi_odds in its CONSENSUS file, compute:
      - market Brier: implied probs from decimal odds (vig-removed) vs actual outcome
      - model Brier:  avg_*_prob from consensus vs actual outcome
    Returns per-match rows + summary stats.
    """
    if not os.path.exists(FORECASTS_DIR) or not os.path.exists(SCORED_DIR):
        return {"rows": [], "summary": None}

    # Build actuals lookup
    actuals = {}
    for fname in os.listdir(SCORED_DIR):
        if not fname.endswith(".json"):
            continue
        try:
            with open(os.path.join(SCORED_DIR, fname), encoding="utf-8") as f:
                rec = json.load(f)
            mid = rec.get("match_id", "")
            if mid and mid not in actuals:
                actuals[mid] = rec.get("actual_outcome")
        except Exception:
            continue

    rows = []
    for fname in sorted(os.listdir(FORECASTS_DIR)):
        if not fname.endswith("_CONSENSUS.json"):
            continue
        try:
            with open(os.path.join(FORECASTS_DIR, fname), encoding="utf-8") as f:
                c = json.load(f)
        except Exception:
            continue

        mid = c.get("match_id", "")
        if not c.get("kalshi_odds") or mid not in actuals or not actuals[mid]:
            continue

        outcome = actuals[mid]
        odds = c["kalshi_odds"]

        # Vig-removed market implied probs
        raw_h = 1.0 / max(odds["home"], 1.01)
        raw_d = 1.0 / max(odds["draw"], 1.01)
        raw_a = 1.0 / max(odds["away"], 1.01)
        total = raw_h + raw_d + raw_a
        mkt_h, mkt_d, mkt_a = raw_h / total, raw_d / total, raw_a / total

        def _brier(ph, pd, pa, outcome):
            o_h = 1.0 if outcome == "home_win" else 0.0
            o_d = 1.0 if outcome == "draw" else 0.0
            o_a = 1.0 if outcome == "away_win" else 0.0
            return round(((ph - o_h)**2 + (pd - o_d)**2 + (pa - o_a)**2), 4)

        mkt_brier = _brier(mkt_h, mkt_d, mkt_a, outcome)
        mdl_h = c.get("avg_home_win_prob") or 0.0
        mdl_d = c.get("avg_draw_prob") or 0.0
        mdl_a = c.get("avg_away_win_prob") or 0.0
        mdl_brier = _brier(mdl_h, mdl_d, mdl_a, outcome)

        # Per-model Brier vs market — pull from scored files
        model_rows = []
        for sfname in os.listdir(SCORED_DIR):
            if not sfname.startswith(mid + "_") or sfname.endswith("_CONSENSUS.json"):
                continue
            try:
                with open(os.path.join(SCORED_DIR, sfname), encoding="utf-8") as sf:
                    sr = json.load(sf)
                if sr.get("kalshi_ev_home_win") is None:
                    continue
                m_h = sr.get("home_win_prob") or 0.0
                m_d = sr.get("draw_prob") or 0.0
                m_a = sr.get("away_win_prob") or 0.0
                model_rows.append({
                    "model": sr.get("model_short"),
                    "brier": _brier(m_h, m_d, m_a, outcome),
                })
            except Exception:
                continue

        rows.append({
            "match_id": mid,
            "match_date": mid[-10:] if len(mid) >= 10 else "",
            "outcome": outcome,
            "mkt_brier": mkt_brier,
            "mdl_brier": mdl_brier,
            "edge": round(mkt_brier - mdl_brier, 4),
            "mkt_h": round(mkt_h, 3), "mkt_d": round(mkt_d, 3), "mkt_a": round(mkt_a, 3),
            "mdl_h": round(mdl_h, 3), "mdl_d": round(mdl_d, 3), "mdl_a": round(mdl_a, 3),
            "model_briers": model_rows,
        })

    if not rows:
        return {"rows": [], "summary": None}

    n = len(rows)
    avg_mkt = round(sum(r["mkt_brier"] for r in rows) / n, 4)
    avg_mdl = round(sum(r["mdl_brier"] for r in rows) / n, 4)
    avg_edge = round(avg_mkt - avg_mdl, 4)
    beats = sum(1 for r in rows if r["edge"] > 0)

    # Per-model summary across all benchmark matches
    model_totals = defaultdict(list)
    for r in rows:
        for mr in r["model_briers"]:
            model_totals[mr["model"]].append(mr["brier"])
    model_summary = sorted(
        [{"model": m, "avg_brier": round(sum(v)/len(v), 4), "n": len(v),
          "beats_mkt": sum(1 for b in v if b < avg_mkt)}
         for m, v in model_totals.items()],
        key=lambda x: x["avg_brier"]
    )

    return {
        "rows": sorted(rows, key=lambda x: x["match_date"]),
        "summary": {
            "n_matches": n,
            "avg_market_brier": avg_mkt,
            "avg_model_brier": avg_mdl,
            "avg_edge": avg_edge,
            "model_beats_market": avg_edge > 0,
            "matches_beat": beats,
            "matches_lost": n - beats,
        },
        "model_summary": model_summary,
    }



    """Scan the archive directory and build a list of forecast versions with metadata."""
    versions = []
    if not os.path.exists(ARCHIVE_DIR):
        return versions
    for stamp in sorted(os.listdir(ARCHIVE_DIR)):
        adir = os.path.join(ARCHIVE_DIR, stamp)
        if not os.path.isdir(adir):
            continue
        n_files = len([f for f in os.listdir(adir) if f.endswith(".json")])
        n_consensus = len([f for f in os.listdir(adir) if f.endswith("_CONSENSUS.json")])
        notes = next((v for k, v in RELEASE_NOTES.items() if stamp.startswith(k)), "")
        versions.append({
            "version_id": stamp,
            "archived_at": stamp,
            "n_forecasts": n_files - n_consensus,
            "n_matches": n_consensus,
            "notes": notes,
        })
    return versions


def build():
    print("Loading data...")
    forecasts = [r for r in _load_dir(FORECASTS_DIR)
                 if not r.get("match_id", "").endswith("_CONSENSUS")
                 and "_CONSENSUS" not in os.path.basename(str(r.get("match_id","")))]
    # Reload properly
    forecasts, consensus = [], []
    for fname in sorted(os.listdir(FORECASTS_DIR)) if os.path.exists(FORECASTS_DIR) else []:
        if not fname.endswith(".json"):
            continue
        try:
            with open(os.path.join(FORECASTS_DIR, fname), encoding="utf-8") as f:
                rec = json.load(f)
            if fname.endswith("_CONSENSUS.json"):
                consensus.append(rec)
            else:
                forecasts.append(rec)
        except Exception as e:
            print(f"  Warning: {fname}: {e}")

    scored = _load_dir(SCORED_DIR)

    # Load bonus consensus (one file per question)
    bonus = []
    bonus_model_results = []
    if os.path.exists(BONUS_DIR):
        for fname in sorted(os.listdir(BONUS_DIR)):
            if not fname.endswith(".json"):
                continue
            try:
                with open(os.path.join(BONUS_DIR, fname), encoding="utf-8") as f:
                    rec = json.load(f)
                if fname.endswith("_CONSENSUS.json"):
                    bonus.append(rec)
                else:
                    bonus_model_results.append(rec)
            except Exception as e:
                print(f"  Warning: {fname}: {e}")

    print(f"  {len(forecasts)} forecasts, {len(consensus)} consensus, {len(scored)} scored, {len(bonus)} bonus ({len(bonus_model_results)} model results)")

    accuracy_stats = _build_accuracy_stats(scored, consensus)
    version_history = _build_version_history()
    cross_version = _build_cross_version_accuracy()
    market_benchmark = _build_market_benchmark()
    print(f"  Accuracy: {len(accuracy_stats['model_stats'])} models tracked, {len(version_history)} forecast version(s), {len(cross_version)} with scored data")
    print(f"  Market benchmark: {market_benchmark['summary']['n_matches'] if market_benchmark['summary'] else 0} matches vs Kalshi")

    build_time = datetime.now().strftime("%Y-%m-%d %H:%M")

    with open(TEMPLATE, encoding="utf-8") as f:
        html = f.read()

    html = html.replace("__FIXTURES_JSON__",       json.dumps(FIXTURES,            ensure_ascii=False))
    html = html.replace("__FORECASTS_JSON__",      json.dumps(forecasts,           ensure_ascii=False))
    html = html.replace("__SCORED_JSON__",         json.dumps(scored,              ensure_ascii=False))
    html = html.replace("__CONSENSUS_JSON__",      json.dumps(consensus,           ensure_ascii=False))
    html = html.replace("__BONUS_JSON__",          json.dumps(bonus,               ensure_ascii=False))
    html = html.replace("__BONUS_MODELS_JSON__",   json.dumps(bonus_model_results, ensure_ascii=False))
    html = html.replace("__ACCURACY_STATS_JSON__", json.dumps(accuracy_stats,      ensure_ascii=False))
    html = html.replace("__VERSION_HISTORY_JSON__",json.dumps(version_history,     ensure_ascii=False))
    html = html.replace("__CROSS_VERSION_JSON__",    json.dumps(cross_version,       ensure_ascii=False))
    html = html.replace("__MARKET_BENCHMARK_JSON__", json.dumps(market_benchmark,    ensure_ascii=False))
    html = html.replace('"__BUILD_TIME__"',        json.dumps(build_time))

    os.makedirs(PAGES_REPO, exist_ok=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Built: {OUT_FILE}")
    return build_time


def push(build_time):
    print(f"Pushing to {PAGES_REPO}...")

    def run(cmd, **kwargs):
        result = subprocess.run(cmd, cwd=PAGES_REPO, capture_output=True, text=True, creationflags=_NO_WINDOW, **kwargs)
        if result.returncode != 0:
            print(f"  Error: {result.stderr.strip()}")
        else:
            if result.stdout.strip():
                print(f"  {result.stdout.strip()}")
        return result.returncode == 0

    # Init repo if needed
    if not os.path.exists(os.path.join(PAGES_REPO, ".git")):
        print("  Initialising git repo...")
        run(["git", "init"])
        run(["git", "remote", "add", "origin", "https://github.tools.sap/I846720/WCFCST.git"])
        run(["git", "checkout", "-b", "gh-pages"])

    # Check current branch
    result = subprocess.run(["git", "branch", "--show-current"],
                            cwd=PAGES_REPO, capture_output=True, text=True, creationflags=_NO_WINDOW)
    branch = result.stdout.strip() or "gh-pages"
    if branch not in ("gh-pages", "main"):
        print(f"  Warning: on branch '{branch}', expected gh-pages")

    run(["git", "add", "index.html"])

    # Check if there's anything to commit
    status = subprocess.run(["git", "status", "--porcelain"],
                             cwd=PAGES_REPO, capture_output=True, text=True, creationflags=_NO_WINDOW)
    if not status.stdout.strip():
        print("  Nothing to commit — index.html unchanged.")
        return

    run(["git", "commit", "-m", f"Deploy WC2026 forecast dashboard [{build_time}]"])
    ok = run(["git", "push", "origin", branch])
    if ok:
        print(f"  Pushed to https://github.tools.sap/I846720/WCFCST (branch: {branch})")
    else:
        print("  Push failed — you may need to run: git push --set-upstream origin gh-pages")


def main():
    no_push = "--no-push" in sys.argv
    build_time = build()
    if not no_push:
        push(build_time)
    else:
        print("Skipped push (--no-push).")
    print("Done.")


if __name__ == "__main__":
    main()
