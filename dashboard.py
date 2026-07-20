"""
dashboard.py — Live dashboard server for the 2026 FIFA World Cup Forecasting App.

Serves a single-page dashboard at http://localhost:7676/
Auto-refreshes data every 30 seconds.

Usage:
    python dashboard.py
    python dashboard.py --port 7676
"""

import json
import os
import sys
import threading
from collections import defaultdict
from datetime import date
from http.server import BaseHTTPRequestHandler, HTTPServer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
FORECASTS_DIR = os.path.join(BASE_DIR, "results", "forecasts")
SCORED_DIR = os.path.join(BASE_DIR, "results", "scored")

FIXTURES = [
    {"date":"2026-06-11","home":"Mexico","away":"Poland","venue":"SoFi Stadium, Los Angeles","stage":"Group A"},
    {"date":"2026-06-11","home":"Saudi Arabia","away":"Argentina","venue":"MetLife Stadium, New York","stage":"Group A"},
    {"date":"2026-06-15","home":"Poland","away":"Saudi Arabia","venue":"AT&T Stadium, Dallas","stage":"Group A"},
    {"date":"2026-06-15","home":"Argentina","away":"Mexico","venue":"MetLife Stadium, New York","stage":"Group A"},
    {"date":"2026-06-19","home":"Poland","away":"Argentina","venue":"SoFi Stadium, Los Angeles","stage":"Group A"},
    {"date":"2026-06-19","home":"Saudi Arabia","away":"Mexico","venue":"Levi's Stadium, San Francisco","stage":"Group A"},
    {"date":"2026-06-12","home":"USA","away":"Wales","venue":"SoFi Stadium, Los Angeles","stage":"Group B"},
    {"date":"2026-06-12","home":"England","away":"Iran","venue":"MetLife Stadium, New York","stage":"Group B"},
    {"date":"2026-06-16","home":"Wales","away":"Iran","venue":"Ahmed bin Ali Stadium, Qatar","stage":"Group B"},
    {"date":"2026-06-16","home":"USA","away":"England","venue":"AT&T Stadium, Dallas","stage":"Group B"},
    {"date":"2026-06-20","home":"Wales","away":"England","venue":"MetLife Stadium, New York","stage":"Group B"},
    {"date":"2026-06-20","home":"Iran","away":"USA","venue":"Levi's Stadium, San Francisco","stage":"Group B"},
    {"date":"2026-06-12","home":"Argentina","away":"Iceland","venue":"MetLife Stadium, New York","stage":"Group C"},
    {"date":"2026-06-12","home":"France","away":"Australia","venue":"AT&T Stadium, Dallas","stage":"Group C"},
    {"date":"2026-06-16","home":"Iceland","away":"Australia","venue":"SoFi Stadium, Los Angeles","stage":"Group C"},
    {"date":"2026-06-16","home":"France","away":"Argentina","venue":"MetLife Stadium, New York","stage":"Group C"},
    {"date":"2026-06-20","home":"Iceland","away":"France","venue":"AT&T Stadium, Dallas","stage":"Group C"},
    {"date":"2026-06-20","home":"Australia","away":"Argentina","venue":"Levi's Stadium, San Francisco","stage":"Group C"},
    {"date":"2026-06-13","home":"Denmark","away":"Tunisia","venue":"Levi's Stadium, San Francisco","stage":"Group D"},
    {"date":"2026-06-13","home":"Brazil","away":"Serbia","venue":"AT&T Stadium, Dallas","stage":"Group D"},
    {"date":"2026-06-17","home":"Tunisia","away":"Serbia","venue":"MetLife Stadium, New York","stage":"Group D"},
    {"date":"2026-06-17","home":"Brazil","away":"Denmark","venue":"SoFi Stadium, Los Angeles","stage":"Group D"},
    {"date":"2026-06-21","home":"Tunisia","away":"Brazil","venue":"AT&T Stadium, Dallas","stage":"Group D"},
    {"date":"2026-06-21","home":"Serbia","away":"Denmark","venue":"Levi's Stadium, San Francisco","stage":"Group D"},
    {"date":"2026-06-13","home":"Spain","away":"Costa Rica","venue":"MetLife Stadium, New York","stage":"Group E"},
    {"date":"2026-06-13","home":"Germany","away":"Japan","venue":"SoFi Stadium, Los Angeles","stage":"Group E"},
    {"date":"2026-06-17","home":"Japan","away":"Costa Rica","venue":"AT&T Stadium, Dallas","stage":"Group E"},
    {"date":"2026-06-17","home":"Spain","away":"Germany","venue":"Levi's Stadium, San Francisco","stage":"Group E"},
    {"date":"2026-06-21","home":"Japan","away":"Spain","venue":"MetLife Stadium, New York","stage":"Group E"},
    {"date":"2026-06-21","home":"Costa Rica","away":"Germany","venue":"SoFi Stadium, Los Angeles","stage":"Group E"},
    {"date":"2026-06-14","home":"Morocco","away":"Croatia","venue":"AT&T Stadium, Dallas","stage":"Group F"},
    {"date":"2026-06-14","home":"Belgium","away":"Canada","venue":"Levi's Stadium, San Francisco","stage":"Group F"},
    {"date":"2026-06-18","home":"Croatia","away":"Canada","venue":"MetLife Stadium, New York","stage":"Group F"},
    {"date":"2026-06-18","home":"Morocco","away":"Belgium","venue":"SoFi Stadium, Los Angeles","stage":"Group F"},
    {"date":"2026-06-22","home":"Croatia","away":"Belgium","venue":"AT&T Stadium, Dallas","stage":"Group F"},
    {"date":"2026-06-22","home":"Canada","away":"Morocco","venue":"Levi's Stadium, San Francisco","stage":"Group F"},
    {"date":"2026-06-14","home":"Switzerland","away":"Cameroon","venue":"SoFi Stadium, Los Angeles","stage":"Group G"},
    {"date":"2026-06-14","home":"Uruguay","away":"South Korea","venue":"MetLife Stadium, New York","stage":"Group G"},
    {"date":"2026-06-18","home":"Cameroon","away":"South Korea","venue":"AT&T Stadium, Dallas","stage":"Group G"},
    {"date":"2026-06-18","home":"Switzerland","away":"Uruguay","venue":"Levi's Stadium, San Francisco","stage":"Group G"},
    {"date":"2026-06-22","home":"Cameroon","away":"Uruguay","venue":"MetLife Stadium, New York","stage":"Group G"},
    {"date":"2026-06-22","home":"South Korea","away":"Switzerland","venue":"SoFi Stadium, Los Angeles","stage":"Group G"},
    {"date":"2026-06-15","home":"Portugal","away":"Ghana","venue":"SoFi Stadium, Los Angeles","stage":"Group H"},
    {"date":"2026-06-15","home":"Netherlands","away":"Senegal","venue":"AT&T Stadium, Dallas","stage":"Group H"},
    {"date":"2026-06-19","home":"Ghana","away":"Senegal","venue":"Levi's Stadium, San Francisco","stage":"Group H"},
    {"date":"2026-06-19","home":"Portugal","away":"Netherlands","venue":"MetLife Stadium, New York","stage":"Group H"},
    {"date":"2026-06-23","home":"Ghana","away":"Netherlands","venue":"AT&T Stadium, Dallas","stage":"Group H"},
    {"date":"2026-06-23","home":"Senegal","away":"Portugal","venue":"SoFi Stadium, Los Angeles","stage":"Group H"},
]

FLAGS = {
    "Mexico":"🇲🇽","Poland":"🇵🇱","Saudi Arabia":"🇸🇦","Argentina":"🇦🇷",
    "USA":"🇺🇸","Wales":"🏴󠁧󠁢󠁷󠁬󠁳󠁿","England":"🏴󠁧󠁢󠁥󠁮󠁧󠁿","Iran":"🇮🇷",
    "France":"🇫🇷","Australia":"🇦🇺","Iceland":"🇮🇸",
    "Denmark":"🇩🇰","Tunisia":"🇹🇳","Brazil":"🇧🇷","Serbia":"🇷🇸",
    "Spain":"🇪🇸","Costa Rica":"🇨🇷","Germany":"🇩🇪","Japan":"🇯🇵",
    "Morocco":"🇲🇦","Croatia":"🇭🇷","Belgium":"🇧🇪","Canada":"🇨🇦",
    "Switzerland":"🇨🇭","Cameroon":"🇨🇲","Uruguay":"🇺🇾","South Korea":"🇰🇷",
    "Portugal":"🇵🇹","Ghana":"🇬🇭","Netherlands":"🇳🇱","Senegal":"🇸🇳",
}

def _mid(home, away, d):
    def s(x): return x.replace(" ","_").replace("'","").replace("/","")
    return f"{s(home)}_{s(away)}_{d}"


# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------

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
        except Exception:
            pass
    return records


def _load_data():
    scored    = _load_dir(SCORED_DIR)
    forecasts = [r for r in _load_dir(FORECASTS_DIR) if not r.get("match_id","").endswith("_CONSENSUS")]
    consensus = [r for r in _load_dir(FORECASTS_DIR)
                 if os.path.exists(os.path.join(FORECASTS_DIR,
                     next((f for f in os.listdir(FORECASTS_DIR)
                           if f.endswith("_CONSENSUS.json") and r.get("match_id","") in f), "x")))]

    # reload consensus properly
    consensus = []
    for fname in sorted(os.listdir(FORECASTS_DIR)) if os.path.exists(FORECASTS_DIR) else []:
        if fname.endswith("_CONSENSUS.json"):
            try:
                with open(os.path.join(FORECASTS_DIR, fname), encoding="utf-8") as f:
                    consensus.append(json.load(f))
            except Exception:
                pass

    match_data = {}
    if os.path.exists(DATA_DIR):
        for fname in os.listdir(DATA_DIR):
            if fname.endswith(".json"):
                try:
                    with open(os.path.join(DATA_DIR, fname), encoding="utf-8") as f:
                        md = json.load(f)
                    match_data[md.get("match_id","")] = md
                except Exception:
                    pass

    return scored, forecasts, consensus, match_data


_WEB_SEARCH_MODELS = {"sonar", "sonarpro"}

def _is_tainted(r: dict) -> bool:
    if r.get("model_short") not in _WEB_SEARCH_MODELS:
        return False
    forecast_date = r.get("forecast_date", "")
    match_id = r.get("match_id", "")
    match_date = match_id[-10:] if len(match_id) >= 10 else ""
    return bool(forecast_date and match_date and forecast_date >= match_date)


def _leaderboard(scored):
    models = defaultdict(lambda: {"pts":0,"n":0,"cost":0.0,"brier":0.0,"bn":0,"exact":0,"correct":0})
    for r in scored:
        if _is_tainted(r):
            continue
        m = r.get("model_short","?")
        models[m]["pts"]   += r.get("points",0)
        models[m]["n"]     += 1
        models[m]["cost"]  += r.get("cost_usd",0.0)
        if r.get("brier_score") is not None:
            models[m]["brier"] += r["brier_score"]
            models[m]["bn"]    += 1
        if r.get("score_breakdown") == "exact_score": models[m]["exact"] += 1
        if r.get("points",0) > 0: models[m]["correct"] += 1
    rows = []
    for m,d in models.items():
        avg = d["pts"]/d["n"] if d["n"] else 0
        brier = d["brier"]/d["bn"] if d["bn"] else None
        ppd = d["pts"]/d["cost"] if d["cost"] else None
        rows.append({"model":m,"pts":d["pts"],"n":d["n"],"avg":round(avg,2),
                     "exact":d["exact"],"correct":d["correct"],"cost":d["cost"],
                     "ppd":ppd,"brier":brier})
    rows.sort(key=lambda x:(-x["pts"],-x["avg"]))
    return rows


# ---------------------------------------------------------------------------
# HTML page
# ---------------------------------------------------------------------------

def _build_page(scored, forecasts, consensus, match_data):
    today = date.today().isoformat()

    # Index structures
    scored_by_match  = defaultdict(list)
    for r in scored: scored_by_match[r["match_id"]].append(r)
    actual_by_match  = {mid: recs[0] for mid,recs in scored_by_match.items() if recs}
    cons_by_match    = {c["match_id"]: c for c in consensus}
    forecast_by_match = defaultdict(list)
    for r in forecasts: forecast_by_match[r["match_id"]].append(r)
    fetched_mids = set(match_data.keys())

    lb = _leaderboard(scored)
    total_pts  = sum(r["pts"] for r in lb)
    total_cost = sum(r["cost"] for r in lb)
    n_scored   = len(set(r["match_id"] for r in scored))
    n_fetched  = len(fetched_mids)
    n_total_matches = len(FIXTURES)
    n_consensus_ready = len(consensus)
    exact_scored = sum(r["n"] for r in lb)  # total clean scored forecasts
    exact_total  = sum(r["exact"] for r in lb)

    # Group fixtures by date
    by_date = defaultdict(list)
    for f in FIXTURES: by_date[f["date"]].append(f)

    def flag(team): return FLAGS.get(team,"🏳")
    def pts_cls(p): return {4:"pts4",2:"pts2",1:"pts1",0:"pts0"}.get(p,"pts0")
    def ev_span(v):
        if v is None: return "—"
        cls = "ev-pos" if v>0 else "ev-neg"
        return f'<span class="{cls}">{v:+.3f}</span>'

    # ---- Schedule HTML ----
    sched_html = ""
    for d in sorted(by_date.keys()):
        is_today = d == today
        is_past  = d < today
        label = "TODAY" if is_today else ("PAST" if is_past else "")
        day_label = f'<div class="day-header">{d} <span class="day-tag">{label}</span></div>'
        sched_html += day_label + '<div class="fixture-grid">'
        for f in sorted(by_date[d], key=lambda x: x["stage"]):
            mid = _mid(f["home"], f["away"], f["date"])
            has_data     = mid in fetched_mids
            has_forecast = mid in forecast_by_match or mid in cons_by_match
            has_score    = mid in actual_by_match
            status_dot   = ('<span class="dot dot-scored">●</span>' if has_score else
                            '<span class="dot dot-forecast">●</span>' if has_forecast else
                            '<span class="dot dot-data">●</span>' if has_data else
                            '<span class="dot dot-none">○</span>')
            cons = cons_by_match.get(mid)
            act  = actual_by_match.get(mid)

            score_block = ""
            if act:
                ah, aa = act.get("actual_home","?"), act.get("actual_away","?")
                score_block = f'<div class="act-score">{ah} – {aa}</div>'
            elif cons:
                ch = cons.get("consensus_home_goals","?")
                ca = cons.get("consensus_away_goals","?")
                score_block = f'<div class="cons-score">{ch} – {ca}</div><div class="cons-label">consensus</div>'

            vb_html = ""
            if cons and cons.get("value_bets"):
                for b in cons["value_bets"]:
                    out = b["outcome"].replace("_"," ").upper()
                    vb_html += f'<span class="vb-tag">EV +{b["ev"]:.3f} {out}</span>'

            md_info = match_data.get(mid,{})
            odds = md_info.get("odds",{})
            odds_html = ""
            if odds:
                odds_html = (f'<div class="odds-row">'
                             f'<span>H {odds.get("home_win","—")}</span>'
                             f'<span>D {odds.get("draw","—")}</span>'
                             f'<span>A {odds.get("away_win","—")}</span>'
                             f'</div>')

            sched_html += f"""
<div class="fixture-card {'scored' if has_score else 'forecast' if has_forecast else 'upcoming'}">
  <div class="fc-top">
    <span class="stage-badge">{f['stage']}</span>
    {status_dot}
  </div>
  <div class="fc-teams">
    <span class="team home-team">{flag(f['home'])} {f['home']}</span>
    <span class="vs">vs</span>
    <span class="team away-team">{f['away']} {flag(f['away'])}</span>
  </div>
  {score_block}
  {odds_html}
  {vb_html}
  <div class="venue">{f['venue']}</div>
</div>"""
        sched_html += '</div>'

    # ---- Leaderboard HTML ----
    if lb:
        lb_rows = ""
        for i,r in enumerate(lb,1):
            brier = f"{r['brier']:.4f}" if r["brier"] else "—"
            ppd   = f"{r['ppd']:.0f}" if r["ppd"] else "—"
            bar_w = int(r["pts"] / max(x["pts"] for x in lb) * 100) if lb else 0
            lb_rows += f"""<tr>
<td class="rank">{i}</td>
<td class="model-name">{r['model']}</td>
<td><div class="bar-wrap"><div class="pts-bar" style="width:{bar_w}%"></div><span class="pts-val">{r['pts']}</span></div></td>
<td>{r['avg']}</td>
<td class="pts4">{r['exact']}</td>
<td>{r['correct']}/{r['n']}</td>
<td>{brier}</td>
<td>${r['cost']:.4f}</td>
<td>{ppd}</td>
</tr>"""
        lb_html = f"""<table class="data-table">
<thead><tr><th>#</th><th>Model</th><th>Points</th><th>Avg/Match</th>
<th>Exact ⭐</th><th>Correct</th><th>Brier↓</th><th>Cost $</th><th>Pts/$</th></tr></thead>
<tbody>{lb_rows}</tbody></table>"""
    else:
        lb_html = '<div class="empty">No scored matches yet — check back after June 11.</div>'

    # ---- EV Picks HTML ----
    if consensus:
        ev_rows = ""
        for c in sorted(consensus, key=lambda x: x.get("match_date","")):
            mid = c.get("match_id","")
            home, away = c.get("home",""), c.get("away","")
            ch = c.get("consensus_home_goals","?")
            ca = c.get("consensus_away_goals","?")
            hw = c.get("avg_home_win_prob")
            dp = c.get("avg_draw_prob")
            aw = c.get("avg_away_win_prob")
            vbs = c.get("value_bets",[])
            act = actual_by_match.get(mid)
            actual_html = "—"
            if act:
                out = act.get("actual_outcome","")
                clr = {"home_win":"ev-pos","draw":"pts2","away_win":"pts2"}.get(out,"")
                actual_html = f'<span class="{clr}">{out.replace("_"," ").upper()}</span>'

            vb_html = " ".join(
                f'<span class="vb-tag">+{b["ev"]:.3f} {b["outcome"].replace("_"," ").upper()} @{b.get("odds","")}</span>'
                for b in vbs
            ) or '<span style="color:#6e7681">none</span>'

            ev_rows += f"""<tr>
<td><strong>{flag(home)} {home}</strong> vs <strong>{away} {flag(away)}</strong></td>
<td>{c.get('match_date','')}</td>
<td>{c.get('models_included',0)}/12</td>
<td class="pts4"><strong>{ch}–{ca}</strong></td>
<td>{f"{hw:.0%}" if hw else "—"}</td>
<td>{f"{dp:.0%}" if dp else "—"}</td>
<td>{f"{aw:.0%}" if aw else "—"}</td>
<td>{ev_span(c.get('ev_home_win'))}</td>
<td>{ev_span(c.get('ev_draw'))}</td>
<td>{ev_span(c.get('ev_away_win'))}</td>
<td>{vb_html}</td>
<td>{actual_html}</td>
</tr>"""
        ev_html = f"""<table class="data-table">
<thead><tr><th>Match</th><th>Date</th><th>Models</th><th>Consensus</th>
<th>H%</th><th>D%</th><th>A%</th>
<th>EV Home</th><th>EV Draw</th><th>EV Away</th>
<th>Value Bets</th><th>Actual</th></tr></thead>
<tbody>{ev_rows}</tbody></table>"""
    else:
        ev_html = '<div class="empty">EV picks appear here once fixtures are fetched — run: <code>python run_match_day.py --date 2026-06-11</code></div>'

    # ---- Match Log HTML ----
    if scored:
        log_html = ""
        for mid in sorted(scored_by_match.keys(), reverse=True):
            recs = sorted(scored_by_match[mid], key=lambda x: -x.get("points",0))
            act  = recs[0]
            ah, aa = act.get("actual_home","?"), act.get("actual_away","?")
            home_part = mid.split("_")[0]
            away_part = mid.split("_")[1] if "_" in mid else ""
            log_html += f"""
<div class="match-card">
<div class="mc-header">
  <span class="mc-title">{home_part} vs {away_part}</span>
  <span class="mc-score">{ah} – {aa}</span>
  <span class="mc-date">{act.get('match_date','')} · <em>{act.get('actual_outcome','').replace('_',' ')}</em></span>
</div>
<table class="inner-table"><thead>
<tr><th>Model</th><th>Predicted</th><th>Pts</th><th>Breakdown</th>
<th>H%</th><th>D%</th><th>A%</th><th>Brier</th><th>Reasoning</th></tr>
</thead><tbody>"""
            for r in recs:
                ph,pa = r.get("predicted_home","?"), r.get("predicted_away","?")
                p = r.get("points",0)
                hw = r.get("home_win_prob"); dp2 = r.get("draw_prob"); aw2 = r.get("away_win_prob")
                br = r.get("brier_score")
                rsn = (r.get("reasoning") or "")[:100]
                log_html += f"""<tr>
<td><strong>{r.get('model_short','?')}</strong></td>
<td>{ph}–{pa}</td>
<td class="{pts_cls(p)}"><strong>{p}</strong></td>
<td><small>{r.get('score_breakdown','')}</small></td>
<td>{f"{hw:.0%}" if hw is not None else "—"}</td>
<td>{f"{dp2:.0%}" if dp2 is not None else "—"}</td>
<td>{f"{aw2:.0%}" if aw2 is not None else "—"}</td>
<td>{f"{br:.4f}" if br else "—"}</td>
<td class="reasoning">{rsn}</td>
</tr>"""
            log_html += "</tbody></table></div>"
    else:
        log_html = '<div class="empty">Match log appears here after results are scored.</div>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>⚽ World Cup 2026 — LLM Forecast Dashboard</title>
<meta http-equiv="refresh" content="60">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#0d1117;color:#e6edf3;font-family:-apple-system,'Segoe UI',sans-serif;font-size:13px;line-height:1.5}}
a{{color:#58a6ff;text-decoration:none}}

/* Header */
.header{{background:#161b22;border-bottom:1px solid #30363d;padding:16px 24px;display:flex;align-items:center;justify-content:space-between}}
.header h1{{font-size:1.3em;color:#fff}}
.header h1 span{{color:#f78166}}
.header-meta{{color:#8b949e;font-size:0.8em}}
.refresh-dot{{display:inline-block;width:8px;height:8px;border-radius:50%;background:#3fb950;margin-right:6px;animation:pulse 2s infinite}}
@keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:0.3}}}}

/* KPI strip */
.kpi-strip{{display:flex;gap:12px;padding:16px 24px;background:#0d1117;border-bottom:1px solid #21262d;flex-wrap:wrap}}
.kpi{{background:#161b22;border:1px solid #21262d;border-radius:8px;padding:10px 16px;min-width:120px}}
.kpi-label{{color:#8b949e;font-size:0.75em;margin-bottom:2px}}
.kpi-value{{font-size:1.4em;font-weight:700;color:#e6edf3}}
.kpi-value.green{{color:#3fb950}}
.kpi-value.blue{{color:#58a6ff}}
.kpi-value.orange{{color:#d29922}}

/* Tabs */
.tabs{{display:flex;background:#161b22;border-bottom:1px solid #30363d;padding:0 24px}}
.tab{{padding:10px 18px;cursor:pointer;border-bottom:2px solid transparent;color:#8b949e;font-weight:500;font-size:0.9em;transition:all 0.15s}}
.tab:hover{{color:#e6edf3}}
.tab.active{{color:#58a6ff;border-bottom-color:#58a6ff}}
.tab-content{{display:none;padding:16px 24px}}
.tab-content.active{{display:block}}

/* Schedule */
.day-header{{color:#8b949e;font-size:0.85em;font-weight:600;letter-spacing:0.08em;padding:12px 0 6px;display:flex;align-items:center;gap:8px}}
.day-tag{{background:#1a4d2e;color:#3fb950;padding:1px 8px;border-radius:10px;font-size:0.75em}}
.fixture-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:10px;margin-bottom:8px}}
.fixture-card{{background:#161b22;border:1px solid #21262d;border-radius:8px;padding:12px;transition:border-color 0.15s}}
.fixture-card:hover{{border-color:#30363d}}
.fixture-card.scored{{border-left:3px solid #3fb950}}
.fixture-card.forecast{{border-left:3px solid #58a6ff}}
.fixture-card.upcoming{{border-left:3px solid #21262d}}
.fc-top{{display:flex;justify-content:space-between;align-items:center;margin-bottom:6px}}
.stage-badge{{background:#21262d;color:#8b949e;font-size:0.72em;padding:1px 6px;border-radius:4px;font-weight:600}}
.fc-teams{{display:flex;align-items:center;gap:6px;margin:6px 0}}
.team{{font-weight:600;font-size:0.95em;flex:1}}
.home-team{{text-align:left}}
.away-team{{text-align:right}}
.vs{{color:#6e7681;font-size:0.8em}}
.act-score{{font-size:1.3em;font-weight:700;color:#3fb950;text-align:center;margin:4px 0}}
.cons-score{{font-size:1.1em;font-weight:600;color:#58a6ff;text-align:center;margin:4px 0}}
.cons-label{{color:#8b949e;font-size:0.72em;text-align:center}}
.odds-row{{display:flex;justify-content:space-around;margin:4px 0;color:#8b949e;font-size:0.8em}}
.venue{{color:#6e7681;font-size:0.75em;margin-top:6px}}
.vb-tag{{display:inline-block;background:#1a4d2e;color:#3fb950;padding:2px 6px;border-radius:4px;font-size:0.72em;font-weight:700;margin:2px 2px 0 0}}
.dot{{font-size:0.7em;margin-left:4px}}
.dot-scored{{color:#3fb950}}
.dot-forecast{{color:#58a6ff}}
.dot-data{{color:#d29922}}
.dot-none{{color:#30363d}}

/* Tables */
.data-table{{width:100%;border-collapse:collapse;margin-top:8px}}
.data-table th{{background:#161b22;color:#8b949e;font-weight:600;padding:7px 10px;text-align:left;border-bottom:1px solid #30363d;font-size:0.78em;letter-spacing:0.05em;white-space:nowrap}}
.data-table td{{padding:6px 10px;border-bottom:1px solid #161b22;vertical-align:middle}}
.data-table tr:hover td{{background:#161b22}}
.rank{{color:#8b949e;font-weight:700;width:28px}}
.model-name{{font-weight:700}}
.pts4{{color:#3fb950;font-weight:700}}
.pts2{{color:#58a6ff}}
.pts1{{color:#d29922}}
.pts0{{color:#6e7681}}
.ev-pos{{color:#3fb950;font-weight:600}}
.ev-neg{{color:#6e7681}}
.bar-wrap{{display:flex;align-items:center;gap:8px;min-width:140px}}
.pts-bar{{height:8px;background:linear-gradient(90deg,#3fb950,#58a6ff);border-radius:4px;min-width:4px;transition:width 0.3s}}
.pts-val{{font-weight:700;color:#3fb950;min-width:28px}}
.reasoning{{color:#8b949e;max-width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}

/* Match log cards */
.match-card{{background:#161b22;border:1px solid #21262d;border-radius:8px;margin-bottom:12px;overflow:hidden}}
.mc-header{{display:flex;align-items:center;gap:16px;padding:10px 14px;background:#0d1117;border-bottom:1px solid #21262d}}
.mc-title{{font-weight:700;font-size:1em;flex:1}}
.mc-score{{font-size:1.1em;font-weight:700;color:#3fb950}}
.mc-date{{color:#8b949e;font-size:0.82em}}
.inner-table{{width:100%;border-collapse:collapse}}
.inner-table th{{background:#161b22;color:#8b949e;font-size:0.75em;padding:5px 10px;text-align:left;border-bottom:1px solid #21262d}}
.inner-table td{{padding:5px 10px;border-bottom:1px solid #0d1117;vertical-align:middle;font-size:0.88em}}

/* Misc */
.empty{{color:#6e7681;padding:32px;text-align:center;font-style:italic;background:#161b22;border-radius:8px;margin-top:8px}}
.empty code{{background:#21262d;padding:2px 6px;border-radius:4px;font-style:normal;color:#e6edf3}}
.section-note{{color:#8b949e;font-size:0.82em;margin-bottom:8px}}
</style>
</head>
<body>

<div class="header">
  <h1>⚽ World Cup 2026 — <span>LLM Forecast Dashboard</span></h1>
  <div class="header-meta">
    <span class="refresh-dot"></span>Auto-refresh every 60s · {today} · 12 models · 48 group stage matches
  </div>
</div>

<div class="kpi-strip">
  <div class="kpi"><div class="kpi-label">Matches Scored</div><div class="kpi-value green">{n_scored} / {n_total_matches}</div></div>
  <div class="kpi"><div class="kpi-label">Forecasts Ready</div><div class="kpi-value blue">{n_consensus_ready} / {n_total_matches}</div></div>
  <div class="kpi"><div class="kpi-label">Exact Scores ⭐</div><div class="kpi-value orange">{exact_total} / {exact_scored}</div></div>
  <div class="kpi"><div class="kpi-label">Total Cost</div><div class="kpi-value">${total_cost:.3f}</div></div>
</div>

<div class="tabs">
  <div class="tab active" onclick="showTab('schedule',this)">📅 Schedule (48)</div>
  <div class="tab" onclick="showTab('leaderboard',this)">🏆 Leaderboard</div>
  <div class="tab" onclick="showTab('ev',this)">📊 EV Picks</div>
  <div class="tab" onclick="showTab('log',this)">📋 Match Log</div>
</div>

<div id="schedule" class="tab-content active">
  <p class="section-note">
    ● <span style="color:#3fb950">scored</span> &nbsp;
    ● <span style="color:#58a6ff">forecast ready</span> &nbsp;
    ● <span style="color:#d29922">data fetched</span> &nbsp;
    ○ upcoming
  </p>
  {sched_html}
</div>

<div id="leaderboard" class="tab-content">
  {lb_html}
</div>

<div id="ev" class="tab-content">
  <p class="section-note">Consensus scoreline + EV across all 12 models. Value bet = model probability exceeds bookmaker implied by &gt;5pp.</p>
  {ev_html}
</div>

<div id="log" class="tab-content">
  {log_html}
</div>

<script>
function showTab(id, el) {{
  document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  el.classList.add('active');
}}
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# HTTP server
# ---------------------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # suppress request logging

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            scored, forecasts, consensus, match_data = _load_data()
            html = _build_page(scored, forecasts, consensus, match_data)
            body = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", len(body))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()


def main():
    port = 7676
    for i, arg in enumerate(sys.argv):
        if arg == "--port" and i + 1 < len(sys.argv):
            port = int(sys.argv[i + 1])

    server = HTTPServer(("localhost", port), Handler)
    url = f"http://localhost:{port}"
    print(f"Dashboard running at {url}")
    print("Press Ctrl+C to stop.")

    import webbrowser
    threading.Timer(0.5, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
