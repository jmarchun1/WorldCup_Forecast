"""
report.py — Generate HTML report for the 2026 FIFA World Cup Forecasting App.

Five sections:
  1. Model Leaderboard — total points, cost, Brier, points per dollar
  2. Match-by-Match Log — all scored matches, model predictions vs actual
  3. Consensus EV Picks — pre-match EV signal table (from CONSENSUS files)
  4. Calibration — how well model probabilities track actual outcomes
  5. Cost Tracker — cumulative cost per model

Usage:
    python report.py
"""

import json
import os
from collections import defaultdict
from datetime import date
from typing import Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCORED_DIR = os.path.join(BASE_DIR, "results", "scored")
FORECASTS_DIR = os.path.join(BASE_DIR, "results", "forecasts")
DATA_DIR = os.path.join(BASE_DIR, "data")
REPORT_DIR = os.path.join(BASE_DIR, "report")
os.makedirs(REPORT_DIR, exist_ok=True)


def load_all_scored() -> list[dict]:
    records = []
    for fname in sorted(os.listdir(SCORED_DIR)):
        if not fname.endswith(".json"):
            continue
        with open(os.path.join(SCORED_DIR, fname), encoding="utf-8") as f:
            records.append(json.load(f))
    return records


def load_all_forecasts() -> list[dict]:
    records = []
    for fname in sorted(os.listdir(FORECASTS_DIR)):
        if not fname.endswith(".json") or fname.endswith("_CONSENSUS.json"):
            continue
        with open(os.path.join(FORECASTS_DIR, fname), encoding="utf-8") as f:
            records.append(json.load(f))
    return records


def load_all_consensus() -> list[dict]:
    records = []
    for fname in sorted(os.listdir(FORECASTS_DIR)):
        if not fname.endswith("_CONSENSUS.json"):
            continue
        with open(os.path.join(FORECASTS_DIR, fname), encoding="utf-8") as f:
            records.append(json.load(f))
    return records


def load_match_data(match_id: str) -> Optional[dict]:
    path = os.path.join(DATA_DIR, f"{match_id}.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Data aggregation
# ---------------------------------------------------------------------------

def _leaderboard(scored: list[dict]) -> list[dict]:
    models = defaultdict(lambda: {
        "points": 0, "matches": 0, "cost_usd": 0.0,
        "brier_sum": 0.0, "brier_count": 0,
        "exact": 0, "correct": 0, "ev_bets": 0, "ev_correct": 0,
    })
    for rec in scored:
        m = rec.get("model_short", "?")
        models[m]["points"] += rec.get("points", 0)
        models[m]["matches"] += 1
        models[m]["cost_usd"] += rec.get("cost_usd", 0.0)
        if rec.get("brier_score") is not None:
            models[m]["brier_sum"] += rec["brier_score"]
            models[m]["brier_count"] += 1
        if rec.get("score_breakdown") == "exact_score":
            models[m]["exact"] += 1
        if rec.get("points", 0) > 0:
            models[m]["correct"] += 1
        if rec.get("ev_value_bet"):
            models[m]["ev_bets"] += 1
            if rec.get("ev_correct"):
                models[m]["ev_correct"] += 1

    rows = []
    for short, d in models.items():
        avg_pts = d["points"] / d["matches"] if d["matches"] else 0
        brier_avg = d["brier_sum"] / d["brier_count"] if d["brier_count"] else None
        pts_per_dollar = d["points"] / d["cost_usd"] if d["cost_usd"] else None
        ev_rate = d["ev_correct"] / d["ev_bets"] if d["ev_bets"] else None
        rows.append({
            "model": short,
            "points": d["points"],
            "matches": d["matches"],
            "avg_pts": round(avg_pts, 2),
            "exact": d["exact"],
            "correct": d["correct"],
            "cost_usd": round(d["cost_usd"], 4),
            "pts_per_dollar": round(pts_per_dollar, 1) if pts_per_dollar else None,
            "brier": round(brier_avg, 4) if brier_avg is not None else None,
            "ev_bets": d["ev_bets"],
            "ev_correct": d["ev_correct"],
            "ev_rate": round(ev_rate, 2) if ev_rate is not None else None,
        })

    rows.sort(key=lambda x: (-x["points"], -x["avg_pts"]))
    return rows


def _match_log(scored: list[dict]) -> dict:
    """Group scored records by match_id."""
    by_match = defaultdict(list)
    for rec in scored:
        by_match[rec["match_id"]].append(rec)
    return dict(by_match)


# ---------------------------------------------------------------------------
# HTML helpers
# ---------------------------------------------------------------------------

CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: #0d1117; color: #e6edf3; font-family: -apple-system, 'Segoe UI', monospace; font-size: 13px; line-height: 1.5; }
h1 { font-size: 1.6em; color: #58a6ff; padding: 24px 32px 8px; }
h2 { font-size: 1.1em; color: #79c0ff; padding: 20px 32px 8px; border-top: 1px solid #21262d; margin-top: 16px; }
h3 { font-size: 0.95em; color: #8b949e; padding: 12px 32px 4px; }
.meta { padding: 4px 32px 16px; color: #8b949e; font-size: 0.85em; }
table { width: calc(100% - 64px); margin: 8px 32px 16px; border-collapse: collapse; }
th { background: #161b22; color: #8b949e; font-weight: 600; padding: 6px 10px; text-align: left; border-bottom: 1px solid #30363d; font-size: 0.8em; letter-spacing: 0.05em; }
td { padding: 5px 10px; border-bottom: 1px solid #161b22; vertical-align: top; }
tr:hover td { background: #161b22; }
.pts-4 { color: #3fb950; font-weight: 700; }
.pts-2 { color: #58a6ff; }
.pts-1 { color: #d29922; }
.pts-0 { color: #6e7681; }
.ev-pos { color: #3fb950; font-weight: 600; }
.ev-neg { color: #6e7681; }
.tag { display: inline-block; padding: 1px 6px; border-radius: 10px; font-size: 0.78em; font-weight: 600; margin: 1px; }
.tag-value { background: #1a4d2e; color: #3fb950; }
.tag-draw { background: #2d2d0a; color: #d29922; }
.tag-away { background: #1d2d4d; color: #58a6ff; }
.tag-home { background: #1a4d2e; color: #3fb950; }
.section { padding-bottom: 24px; }
.summary-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 12px; padding: 12px 32px; }
.kpi { background: #161b22; border-radius: 8px; padding: 12px 16px; border: 1px solid #21262d; }
.kpi-label { color: #8b949e; font-size: 0.78em; margin-bottom: 4px; }
.kpi-value { font-size: 1.3em; font-weight: 700; color: #e6edf3; }
.match-card { background: #161b22; border: 1px solid #21262d; border-radius: 8px; margin: 8px 32px; padding: 12px 16px; }
.match-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.match-title { font-size: 1.05em; color: #e6edf3; font-weight: 600; }
.match-score { font-size: 1.2em; font-weight: 700; color: #58a6ff; }
.match-meta { color: #8b949e; font-size: 0.8em; }
.no-data { color: #6e7681; padding: 12px 32px; font-style: italic; }
"""

def _fmt_pts(pts: int) -> str:
    cls = {4: "pts-4", 2: "pts-2", 1: "pts-1", 0: "pts-0"}.get(pts, "pts-0")
    return f'<span class="{cls}">{pts}</span>'

def _fmt_ev(ev: Optional[float]) -> str:
    if ev is None:
        return "—"
    cls = "ev-pos" if ev > 0 else "ev-neg"
    return f'<span class="{cls}">{ev:+.3f}</span>'

def _outcome_tag(outcome: str) -> str:
    label = {"home_win": "HOME WIN", "draw": "DRAW", "away_win": "AWAY WIN"}.get(outcome, outcome)
    cls = {"home_win": "tag-home", "draw": "tag-draw", "away_win": "tag-away"}.get(outcome, "tag-value")
    return f'<span class="tag {cls}">{label}</span>'


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------

def _section_summary(scored: list[dict], consensus_list: list[dict]) -> str:
    total_forecasts = len(scored)
    matches_scored = len(set(r["match_id"] for r in scored))
    total_pts = sum(r.get("points", 0) for r in scored)
    exact_count = sum(1 for r in scored if r.get("score_breakdown") == "exact_score")
    total_cost = sum(r.get("cost_usd", 0.0) for r in scored)
    value_bets = sum(1 for c in consensus_list if c.get("value_bets"))

    return f"""
<div class="summary-grid">
  <div class="kpi"><div class="kpi-label">Matches Scored</div><div class="kpi-value">{matches_scored}</div></div>
  <div class="kpi"><div class="kpi-label">Total Predictions</div><div class="kpi-value">{total_forecasts}</div></div>
  <div class="kpi"><div class="kpi-label">Total Points (all models)</div><div class="kpi-value">{total_pts}</div></div>
  <div class="kpi"><div class="kpi-label">Exact Scores</div><div class="kpi-value">{exact_count}</div></div>
  <div class="kpi"><div class="kpi-label">Total Cost</div><div class="kpi-value">${total_cost:.4f}</div></div>
  <div class="kpi"><div class="kpi-label">Value Bet Signals</div><div class="kpi-value">{value_bets}</div></div>
</div>"""


def _section_leaderboard(scored: list[dict]) -> str:
    if not scored:
        return '<p class="no-data">No scored matches yet.</p>'
    rows = _leaderboard(scored)
    header = """<table>
<thead><tr>
<th>#</th><th>Model</th><th>Points</th><th>Avg/Match</th><th>Exact</th>
<th>Correct</th><th>Brier↓</th><th>Cost $</th><th>Pts/$</th>
<th>EV Bets</th><th>EV Hit%</th>
</tr></thead><tbody>"""
    body = ""
    for i, r in enumerate(rows, 1):
        brier = f"{r['brier']:.4f}" if r["brier"] is not None else "—"
        pts_dollar = f"{r['pts_per_dollar']:.0f}" if r["pts_per_dollar"] else "—"
        ev_rate = f"{r['ev_rate']:.0%}" if r["ev_rate"] is not None else "—"
        body += f"""<tr>
<td>{i}</td>
<td><strong>{r['model']}</strong></td>
<td class="pts-4"><strong>{r['points']}</strong></td>
<td>{r['avg_pts']}</td>
<td>{r['exact']}</td>
<td>{r['correct']}/{r['matches']}</td>
<td>{brier}</td>
<td>${r['cost_usd']:.4f}</td>
<td>{pts_dollar}</td>
<td>{r['ev_bets']}</td>
<td>{ev_rate}</td>
</tr>"""
    return header + body + "</tbody></table>"


def _section_match_log(scored: list[dict]) -> str:
    if not scored:
        return '<p class="no-data">No scored matches yet.</p>'
    by_match = _match_log(scored)
    html = ""
    for mid in sorted(by_match.keys()):
        recs = sorted(by_match[mid], key=lambda x: -x.get("points", 0))
        if not recs:
            continue
        first = recs[0]
        ah = first.get("actual_home", "?")
        aa = first.get("actual_away", "?")
        home, away = mid.split("_")[0], mid.split("_")[1]
        match_date = first.get("match_date", "")

        html += f"""<div class="match-card">
<div class="match-header">
  <span class="match-title">{home} vs {away}</span>
  <span class="match-score">{ah} – {aa}</span>
  <span class="match-meta">{match_date} · {first.get('actual_outcome','')}</span>
</div>
<table style="margin:0;width:100%">
<thead><tr><th>Model</th><th>Predicted</th><th>Points</th><th>Breakdown</th>
<th>HWin%</th><th>Draw%</th><th>AWin%</th><th>Brier</th><th>Reasoning</th></tr></thead>
<tbody>"""
        for r in recs:
            ph = r.get("predicted_home", "?")
            pa = r.get("predicted_away", "?")
            pts = r.get("points", 0)
            bdown = r.get("score_breakdown", "")
            hw = r.get("home_win_prob")
            dp = r.get("draw_prob")
            aw = r.get("away_win_prob")
            brier = r.get("brier_score")
            reasoning = (r.get("reasoning") or "")[:120]
            html += f"""<tr>
<td><strong>{r.get('model_short','?')}</strong></td>
<td>{ph}–{pa}</td>
<td>{_fmt_pts(pts)}</td>
<td><small>{bdown}</small></td>
<td>{f"{hw:.0%}" if hw is not None else "—"}</td>
<td>{f"{dp:.0%}" if dp is not None else "—"}</td>
<td>{f"{aw:.0%}" if aw is not None else "—"}</td>
<td>{f"{brier:.4f}" if brier is not None else "—"}</td>
<td><small style="color:#8b949e">{reasoning}</small></td>
</tr>"""
        html += "</tbody></table></div>\n"
    return html


def _section_ev_picks(consensus_list: list[dict]) -> str:
    if not consensus_list:
        return '<p class="no-data">No consensus forecasts yet.</p>'

    # Load scored data to check actual outcomes
    scored_by_match = {}
    for fname in os.listdir(SCORED_DIR):
        if not fname.endswith(".json"):
            continue
        with open(os.path.join(SCORED_DIR, fname), encoding="utf-8") as f:
            rec = json.load(f)
        mid = rec.get("match_id")
        if mid and mid not in scored_by_match:
            scored_by_match[mid] = rec.get("actual_outcome")

    html = """<table>
<thead><tr>
<th>Match</th><th>Date</th><th>Models</th>
<th>Cons. Score</th>
<th>HWin%</th><th>Draw%</th><th>AWin%</th>
<th>EV Home</th><th>EV Draw</th><th>EV Away</th>
<th>Value Bets</th><th>Actual</th>
</tr></thead><tbody>"""

    for c in sorted(consensus_list, key=lambda x: x.get("match_date", "")):
        mid = c.get("match_id", "")
        home = c.get("home", "")
        away = c.get("away", "")
        ch = c.get("consensus_home_goals", "?")
        ca = c.get("consensus_away_goals", "?")
        hw = c.get("avg_home_win_prob")
        dp = c.get("avg_draw_prob")
        aw = c.get("avg_away_win_prob")
        ev_h = c.get("ev_home_win")
        ev_d = c.get("ev_draw")
        ev_a = c.get("ev_away_win")
        value_bets = c.get("value_bets", [])
        actual_outcome = scored_by_match.get(mid)

        vb_html = " ".join(
            f'<span class="tag tag-value">+{b["ev"]:.3f} {b["outcome"].replace("_"," ").upper()} @ {b.get("odds","")}</span>'
            for b in value_bets
        ) or "—"

        actual_html = _outcome_tag(actual_outcome) if actual_outcome else "—"

        html += f"""<tr>
<td><strong>{home} v {away}</strong></td>
<td>{c.get('match_date','')}</td>
<td>{c.get('models_included',0)}</td>
<td><strong>{ch}–{ca}</strong></td>
<td>{f"{hw:.0%}" if hw is not None else "—"}</td>
<td>{f"{dp:.0%}" if dp is not None else "—"}</td>
<td>{f"{aw:.0%}" if aw is not None else "—"}</td>
<td>{_fmt_ev(ev_h)}</td>
<td>{_fmt_ev(ev_d)}</td>
<td>{_fmt_ev(ev_a)}</td>
<td>{vb_html}</td>
<td>{actual_html}</td>
</tr>"""
    html += "</tbody></table>"
    return html


def _section_calibration(scored: list[dict]) -> str:
    if not scored:
        return '<p class="no-data">No scored matches yet.</p>'
    by_model = defaultdict(lambda: {"brier_sum": 0.0, "count": 0, "correct_prob": []})
    for r in scored:
        m = r.get("model_short", "?")
        if r.get("brier_score") is not None:
            by_model[m]["brier_sum"] += r["brier_score"]
            by_model[m]["count"] += 1
        actual = r.get("actual_outcome")
        if actual == "home_win":
            by_model[m]["correct_prob"].append(r.get("home_win_prob") or 0)
        elif actual == "draw":
            by_model[m]["correct_prob"].append(r.get("draw_prob") or 0)
        elif actual == "away_win":
            by_model[m]["correct_prob"].append(r.get("away_win_prob") or 0)

    rows = []
    for m, d in by_model.items():
        brier_avg = d["brier_sum"] / d["count"] if d["count"] else None
        avg_correct_conf = sum(d["correct_prob"]) / len(d["correct_prob"]) if d["correct_prob"] else None
        rows.append((m, brier_avg, avg_correct_conf, d["count"]))
    rows.sort(key=lambda x: (x[1] or 9))

    html = """<table>
<thead><tr><th>Model</th><th>Avg Brier↓</th><th>Avg Correct-Outcome Prob↑</th><th>Predictions</th></tr></thead>
<tbody>"""
    for m, brier, conf, n in rows:
        brier_str = f"{brier:.4f}" if brier is not None else "—"
        conf_str = f"{conf:.1%}" if conf is not None else "—"
        html += f"<tr><td><strong>{m}</strong></td><td>{brier_str}</td><td>{conf_str}</td><td>{n}</td></tr>\n"
    html += "</tbody></table>"
    return html


def _section_cost(scored: list[dict], forecasts: list[dict]) -> str:
    by_model = defaultdict(lambda: {"cost": 0.0, "calls": 0})
    for r in forecasts:
        m = r.get("model_short", "?")
        by_model[m]["cost"] += r.get("cost_usd", 0.0)
        by_model[m]["calls"] += 1
    # Augment with scored cost if forecasts not all loaded
    for r in scored:
        m = r.get("model_short", "?")
        if by_model[m]["calls"] == 0:
            by_model[m]["cost"] += r.get("cost_usd", 0.0)

    rows = sorted(by_model.items(), key=lambda x: -x[1]["cost"])
    total = sum(d["cost"] for _, d in rows)
    html = f"""<table>
<thead><tr><th>Model</th><th>Calls</th><th>Total Cost $</th><th>Cost/Call $</th><th>% of Total</th></tr></thead>
<tbody>"""
    for m, d in rows:
        cpc = d["cost"] / d["calls"] if d["calls"] else 0
        pct = d["cost"] / total * 100 if total else 0
        html += f"<tr><td><strong>{m}</strong></td><td>{d['calls']}</td><td>${d['cost']:.5f}</td><td>${cpc:.5f}</td><td>{pct:.1f}%</td></tr>\n"
    html += f"<tr style='font-weight:700;border-top:1px solid #30363d'><td colspan='2'>TOTAL</td><td>${total:.5f}</td><td>—</td><td>100%</td></tr>"
    html += "</tbody></table>"
    return html


# ---------------------------------------------------------------------------
# Main HTML assembly
# ---------------------------------------------------------------------------

def generate_html(scored: list[dict], forecasts: list[dict], consensus_list: list[dict]) -> str:
    now = date.today().isoformat()
    n_matches = len(set(r["match_id"] for r in scored)) if scored else 0
    n_consensus = len(consensus_list)

    body = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>2026 FIFA World Cup — LLM Forecasting</title>
<style>{CSS}</style>
</head>
<body>

<h1>2026 FIFA World Cup — LLM Forecasting</h1>
<p class="meta">Report generated: {now} · 12 models · 4/2/1/1 fantasy points scoring · {n_matches} matches scored · {n_consensus} consensus EV analyses</p>

<div class="section">
{_section_summary(scored, consensus_list)}
</div>

<h2>1. Model Leaderboard</h2>
<div class="section">
{_section_leaderboard(scored)}
</div>

<h2>2. Consensus EV Picks</h2>
<p class="meta">Consensus scoreline + EV signals across all 12 models. Value bet = model probability exceeds bookmaker implied by &gt;5pp.</p>
<div class="section">
{_section_ev_picks(consensus_list)}
</div>

<h2>3. Match-by-Match Log</h2>
<div class="section">
{_section_match_log(scored)}
</div>

<h2>4. Probability Calibration</h2>
<p class="meta">Brier score (lower = better). Avg correct-outcome probability (higher = better).</p>
<div class="section">
{_section_calibration(scored)}
</div>

<h2>5. Cost Tracker</h2>
<div class="section">
{_section_cost(scored, forecasts)}
</div>

</body>
</html>"""
    return body


def main():
    scored = load_all_scored()
    forecasts = load_all_forecasts()
    consensus_list = load_all_consensus()
    html = generate_html(scored, forecasts, consensus_list)
    out_path = os.path.join(REPORT_DIR, "index.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Report written to {out_path} ({len(scored)} scored, {len(consensus_list)} consensus, {len(forecasts)} forecasts)")
    return out_path


if __name__ == "__main__":
    main()
