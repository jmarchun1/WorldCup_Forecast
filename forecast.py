"""
forecast.py — Prompt all 12 LLMs for World Cup match scoreline predictions.

Usage:
    python forecast.py                        # forecast all upcoming matches
    python forecast.py --date 2026-06-14      # forecast matches on a specific date
    python forecast.py --match "Mexico_Poland_2026-06-11"  # forecast one match
    python forecast.py --force                # re-run even if forecasts exist
"""

import json
import logging
import os
import re
import shutil
import statistics
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone
from typing import Optional

import anthropic
import openai as openai_lib

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
FORECASTS_DIR = os.path.join(BASE_DIR, "results", "forecasts")
ARCHIVE_DIR   = os.path.join(BASE_DIR, "results", "forecasts", "archive")
WEIGHTS_FILE  = os.path.join(BASE_DIR, "model_weights.json")
os.makedirs(FORECASTS_DIR, exist_ok=True)

_model_weights_cache: dict | None = None

def _load_model_weights() -> dict:
    """Load Bayesian model weights from model_weights.json. Returns empty dict if not found."""
    global _model_weights_cache
    if _model_weights_cache is not None:
        return _model_weights_cache
    if os.path.exists(WEIGHTS_FILE):
        with open(WEIGHTS_FILE, encoding="utf-8") as f:
            data = json.load(f)
        _model_weights_cache = data.get("weights", {})
        logger.info("Loaded model weights from %s (%d models)", WEIGHTS_FILE, len(_model_weights_cache))
    else:
        _model_weights_cache = {}
    return _model_weights_cache


# Historical WC base-rate prior (group stage, 1990-2022, n≈432 matches)
# Updated with WC2026 in-tournament actuals through MD3 (66 matches: avg 2.9 goals, SD 1.4)
WC_BASE_RATE_PRIOR = (
    "Historical World Cup group-stage base rates (1990-2022): "
    "most common scorelines are 1-0 (18%), 1-1 (14%), 2-0 (11%), 2-1 (10%), 0-0 (7%). "
    "When Elo rating gap exceeds 150 points, the stronger team wins ~70% of the time. "
    "Goals per match average 2.6 historically; WC2026 through match day 3 averages 2.9 goals (SD 1.4). "
    "Your predicted scoreline should reflect a total near 2.5-3.0 goals unless specific context "
    "suggests a defensive match. Under-predicting goals is the most common AI forecasting error in this tournament."
)

WC_BASE_RATE_KNOCKOUT = (
    "Historical World Cup knockout-stage base rates (1990-2022, 90-minute result only): "
    "home/away win ~45%/35%, draw after 90 min ~20% (proceeds to extra time/penalties). "
    "Most common 90-min scorelines: 1-0 (22%), 2-1 (14%), 2-0 (12%), 1-1 (11%), 0-0 (5%). "
    "Goals per match average 2.4; higher-stakes matches are slightly lower-scoring than group stage."
)

# Knockout stage indicators — any stage name containing these substrings
_KNOCKOUT_STAGES = ("round of 16", "round of 32", "quarter", "semi", "final", "r16", "ro16", "r32", "ro32", "3rd place")


def _is_knockout(stage: str) -> bool:
    return any(k in stage.lower() for k in _KNOCKOUT_STAGES)


def _get_base_rate_prior(stage: str) -> str:
    return WC_BASE_RATE_KNOCKOUT if _is_knockout(stage) else WC_BASE_RATE_PRIOR


def _get_draw_reminder(stage: str) -> str:
    if _is_knockout(stage):
        return (
            "Draw base rate reminder: In World Cup knockout matches, ~20% of games are drawn after 90 minutes "
            "(proceeding to extra time and potentially penalties). "
            "The predicted scoreline should reflect 90-minute play only — do NOT factor in extra time or penalties. "
            "A draw prediction is valid and represents ~20% probability; assign draw_prob accordingly. "
            "Do not suppress draw_prob below 0.10 unless one team is a heavy favourite."
        )
    return (
        "Draw base rate reminder: World Cup group-stage matches end in a draw ~26% of the time. "
        "When both teams have implied win probabilities between 0.28 and 0.45, "
        "a draw is the single most likely outcome — but choose the most contextually appropriate "
        "scoreline (0-0, 1-1, 2-2) rather than defaulting to 1-1. "
        "Do not assign draw_prob below 0.15 unless one team is a clear favourite."
    )

# Key injury absences confirmed for WC 2026 (sourced ESPN injury tracker, 2026-06-20)
WC2026_INJURIES = (
    "Key confirmed absences for WC 2026: "
    "Brazil: Rodrygo (ACL), Estevao (hamstring), E.Militao (hamstring); "
    "Netherlands: Xavi Simons (ACL), J.Timber (groin), de Ligt (back), Schouten (ACL); "
    "Germany: Gnabry (adductor), ter Stegen (thigh); "
    "France: Ekitiike (Achilles), Saliba (cleared); "
    "Spain: Fermin Lopez (metatarsal); "
    "Japan: Mitoma (hamstring), Minamino (ACL); "
    "USA: Cardoso (ankle surgery), Agyemang (Achilles); "
    "USA vs Turkey (2026-06-25): USA have already qualified and are resting 4 starters "
    "with yellow card suspensions — expect heavily rotated squad, reduced motivation; "
    "Turkey are eliminated but playing for pride with full-strength lineup; "
    "Argentina: C.Romero (MCL - questionable), Messi (thigh overload - doubtful). "
    "Injury context is most relevant for matches involving these teams."
)

# PELE Tilt ratings — attacking/defensive style tendency (Nate Silver PELE methodology)
# Positive tilt: teams whose games tend toward higher goal totals
# Negative tilt: teams whose games tend toward lower totals and draws
# draw_pct: approximate draw rate in last 20 competitive matches
WC2026_TILT = {
    "Germany":      ("+high", "attacking 4-2-3-1 (Nagelsmann) — high press, games tend 3+ goals total", 0.20),
    "Norway":       ("+high", "attacking 4-3-3 (Haaland-driven) — direct, games tend 3+ goals", 0.18),
    "Netherlands":  ("+high", "attacking 4-3-3 (Koeman) — possession + press, 3+ goals", 0.20),
    "England":      ("+high", "attacking 4-2-3-1 (Southgate/successor) — set piece reliant, 3+ goals", 0.22),
    "France":       ("+mid",  "4-3-3 (Deschamps) — counter-attack, disciplined, 2.5–3 goals", 0.25),
    "Brazil":       ("+mid",  "4-2-3-1 (Ancelotti) — technical, moderately attacking, 2.5–3 goals", 0.22),
    "Argentina":    ("+mid",  "4-3-3 (Scaloni) — possession + Messi creativity, 2.5–3 goals", 0.20),
    "Spain":        ("+mid",  "4-3-3 (de la Fuente) — high possession tiki-taka, 2.5–3 goals", 0.25),
    "USA":          ("+mid",  "4-3-3 (Berhalter/successor) — athletic pressing, 2.5–3 goals", 0.25),
    "Sweden":       ("+mid",  "4-4-2 (Andersson) — organised, direct, 2.5–3 goals", 0.28),
    "Portugal":     ("+mid",  "4-3-3 (Martinez) — Ronaldo-centric attack, 2.5–3 goals", 0.22),
    "Belgium":      ("+mid",  "4-2-3-1 (Tedesco) — experienced squad, 2.5–3 goals", 0.25),
    "Croatia":      ("+mid",  "4-3-3 (Dalic) — midfield control, draws frequently, 2+ goals", 0.32),
    "Colombia":     ("-low",  "4-4-2 (Lorenzo) — disciplined low-block, draws and under 2.5 goals", 0.35),
    "Senegal":      ("-low",  "4-3-3 (Cissé) — defensive solidity, draws and under 2.5 goals", 0.30),
    "Morocco":      ("-low",  "4-1-4-1 (Regragui) — elite low-block, highest draw rate in tournament", 0.40),
    "Saudi Arabia": ("-low",  "4-3-3 (Renard) — organised defensive block, under 2.5 goals", 0.30),
    "Iran":         ("-low",  "4-5-1 (Queiroz) — deep defensive structure, very low scoring", 0.38),
    "Egypt":        ("-low",  "4-2-3-1 (Koller successor) — defensive, counter-reliant, draws common", 0.35),
    "Algeria":      ("-low",  "4-3-3 (Belmadi) — defensive mid-block, draws ~35% of games", 0.35),
    "Uruguay":      ("-low",  "4-4-2 (Bielsa) — defensive but direct, low scoring", 0.30),
    "Japan":        ("-low",  "4-2-3-1 (Moriyasu) — organised low-block counter, draws ~30%", 0.30),
    "Australia":    ("-low",  "4-3-3 (Arnold) — physical, defensive away from home", 0.28),
    "Turkey":       ("-low",  "4-2-3-1 (Montella) — compact, counter-attacking, draws ~30%", 0.30),
    "Ecuador":      ("-low",  "4-3-3 (Sánchez) — pragmatic, low-block, under 2.5 goals", 0.30),
    "Tunisia":      ("-low",  "4-3-3 (Kadri) — disciplined defensive block, draws ~35%", 0.35),
    "Paraguay":     ("-low",  "4-4-2 (Garnero) — physical, counter-attacking, draws common", 0.32),
    "Ghana":        ("-low",  "4-2-3-1 (Addo) — direct, physical, draws ~28%", 0.28),
    "Cape Verde":   ("-low",  "4-3-3 (Brito) — organised, defensive away, draws ~30%", 0.30),
    "DR Congo":     ("-low",  "4-3-3 (Ibenge) — technical but inconsistent, draws ~30%", 0.30),
    "Uzbekistan":   ("-low",  "4-3-3 (Babayev) — young squad, improving, physical", 0.25),
    "Panama":       ("-low",  "4-5-1 (Thomas) — ultra-defensive, low block, highest draw rate", 0.38),
    "Ivory Coast":  ("+mid",  "4-3-3 (Gasset/successor) — attacking, 2.5+ goals", 0.25),
    "Iraq":         ("-low",  "4-4-2 (Jesus Casas) — defensive, counter-attacking", 0.30),
    "Curacao":      ("-low",  "4-4-2 — organised, defensive, limited squad depth", 0.28),
    "New Zealand":  ("-low",  "4-4-2 (Aloisi) — defensive, counter-attacking, under 2 goals", 0.35),
    "Jordan":       ("-low",  "4-5-1 (Jaradat) — defensive low-block, draws ~35%", 0.35),
    "Austria":      ("+mid",  "4-3-3 (Rangnick) — high press, direct, 2.5+ goals", 0.22),
}


def _compute_group_standings(group: str, home: str, away: str) -> dict:
    """Read scored files for the same group to derive pre-match points tables from actual results."""
    scored_dir = os.path.join(BASE_DIR, "results", "scored")
    if not os.path.exists(scored_dir):
        return {}

    # Collect all teams in this group from data/
    data_dir = os.path.join(BASE_DIR, "data")
    group_teams: set = set()
    for fname in os.listdir(data_dir):
        if not fname.endswith(".json"):
            continue
        try:
            d = json.load(open(os.path.join(data_dir, fname), encoding="utf-8"))
        except Exception:
            continue
        if d.get("stage") == group:
            group_teams.add(d["home"])
            group_teams.add(d["away"])

    if not group_teams:
        return {}

    # Gather one actual result per match_id (first scored file wins)
    match_results: dict = {}
    for fname in os.listdir(scored_dir):
        if not fname.endswith(".json"):
            continue
        try:
            d = json.load(open(os.path.join(scored_dir, fname), encoding="utf-8"))
        except Exception:
            continue
        mid = d.get("match_id", "")
        if mid in match_results:
            continue
        ah = d.get("actual_home")
        aa = d.get("actual_away")
        if ah is None or aa is None:
            continue
        # Parse home/away from match_id: Team1_Team2_YYYY-MM-DD
        parts = mid.split("_")
        date_idx = next((i for i, p in enumerate(parts) if len(p) == 10 and p[4:5] == "-"), len(parts))
        h_name = "_".join(parts[:date_idx - 1]) if date_idx > 1 else ""
        a_name = parts[date_idx - 1] if date_idx >= 1 else ""
        # Check if both teams are in this group
        if h_name not in group_teams or a_name not in group_teams:
            continue
        # Skip the match we're predicting
        if {h_name, a_name} == {home, away}:
            continue
        match_results[mid] = (h_name, a_name, int(ah), int(aa))

    standings: dict = {t: {"pts": 0, "gf": 0, "ga": 0, "played": 0} for t in group_teams}
    for h_name, a_name, ah, aa in match_results.values():
        standings[h_name]["played"] += 1
        standings[a_name]["played"] += 1
        standings[h_name]["gf"] += ah
        standings[h_name]["ga"] += aa
        standings[a_name]["gf"] += aa
        standings[a_name]["ga"] += ah
        if ah > aa:
            standings[h_name]["pts"] += 3
        elif ah == aa:
            standings[h_name]["pts"] += 1
            standings[a_name]["pts"] += 1
        else:
            standings[a_name]["pts"] += 3
    return standings


def _get_dead_rubber_context(match_data: dict) -> Optional[str]:
    """Return incentive/pressure context for MD3 group matches.

    Handles three scenarios:
    - Both teams settled (clinched or eliminated): full dead-rubber warning
    - One team settled, one competing: pressure asymmetry warning
    - Both competing: no injection
    """
    group = match_data.get("stage", "")
    home = match_data["home"]
    away = match_data["away"]

    if not group.startswith("Group"):
        return None

    standings = _compute_group_standings(group, home, away)
    if not standings:
        return None

    # Only apply when both teams have played exactly 2 prior group matches
    home_s = standings.get(home, {})
    away_s = standings.get(away, {})
    if home_s.get("played", 0) < 2 or away_s.get("played", 0) < 2:
        return None

    def _classify(s: dict) -> str:
        pts = s["pts"]
        gd = s["gf"] - s["ga"]
        if pts >= 6:
            return "clinched"
        if pts == 0 and gd <= -3:
            return "eliminated"
        return "competing"

    home_status = _classify(home_s)
    away_status = _classify(away_s)

    labels = {
        "clinched": "already clinched qualification (top 2 in group)",
        "eliminated": "already been eliminated from the tournament",
    }

    if home_status == "competing" and away_status == "competing":
        return None  # both still have something to play for

    if home_status != "competing" and away_status != "competing":
        # Both settled — full dead-rubber
        lines = [
            "=== MATCH-DAY 3 INCENTIVE WARNING ===",
            f"{home} has {labels[home_status]}. {away} has {labels[away_status]}.",
            "Research on World Cup dead-rubber matches shows:",
            "- Draw probability rises ~10 percentage points above bookmaker implied rate",
            "- Goals per match drops ~0.4 below normal (squad rotation of 4-6 starters is typical)",
            "- When both teams have qualified, a comfortable 1-1 or 0-0 is often the rational outcome",
            "- When both teams are eliminated, effort levels drop but unpredictable scorelines are common",
            "Adjust your prediction to account for reduced competitive incentive in this match.",
        ]
        return "\n".join(lines)

    # One team settled, one competing — pressure asymmetry
    if home_status != "competing":
        settled_team, settled_status = home, home_status
        pressure_team = away
    else:
        settled_team, settled_status = away, away_status
        pressure_team = home

    settled_label = labels[settled_status]
    if settled_status == "clinched":
        settled_note = (
            f"{settled_team} ({settled_label}) will likely rotate 3-5 starters — "
            "reduced intensity, squad freshness priority. Effective lineup quality estimate: -10 to -15%."
        )
        pressure_note = (
            f"{pressure_team} is in a MUST-WIN or must-not-lose situation. "
            "Teams under qualification pressure at WC historically underperform their Elo expectation by ~6% "
            "due to elevated anxiety and conservative tactics."
        )
    else:  # eliminated
        settled_note = (
            f"{settled_team} ({settled_label}) plays freely with no pressure — "
            "historical 'free-wheeling' effect: slight positive performance signal in ~30% of cases."
        )
        pressure_note = (
            f"{pressure_team} must win or get a result to advance — "
            "high-pressure scenario; teams in must-qualify WC matches win 48% vs expected 54%."
        )

    lines = [
        "=== MATCH-DAY 3 PRESSURE ASYMMETRY ===",
        settled_note,
        pressure_note,
        "Net effect: the settled team's reduced motivation partially offsets their quality advantage. "
        "Adjust win probabilities to account for this asymmetry before applying other factors.",
    ]
    return "\n".join(lines)


def _load_config() -> dict:
    with open(os.path.join(BASE_DIR, "config.json")) as f:
        return json.load(f)


def build_prompt(match_data: dict) -> str:
    home = match_data["home"]
    away = match_data["away"]
    stage = match_data["stage"]
    venue = match_data["venue"]
    match_date = match_data["date"]
    odds = match_data.get("odds", {})
    context = match_data.get("context", "")
    today = date.today().isoformat()

    home_odds = odds.get("home_win", 2.50)
    draw_odds = odds.get("draw", 3.20)
    away_odds = odds.get("away_win", 2.80)
    implied_home = odds.get("implied_home", 0.38)
    implied_draw = odds.get("implied_draw", 0.30)
    implied_away = odds.get("implied_away", 0.34)

    lines = [
        f"You are a football/soccer analyst. Today is {today}.",
        "",
        f"Match: {home} vs {away}",
        f"Stage: {stage} — {venue}",
        f"Match date: {match_date}",
        "",
        "=== HISTORICAL BASE RATES ===",
        _get_base_rate_prior(stage),
        "",
        "=== KEY INJURY ABSENCES (WC 2026) ===",
        WC2026_INJURIES,
        "",
    ]

    # PELE Tilt — inject when either team has a known style rating
    home_tilt = WC2026_TILT.get(home)
    away_tilt = WC2026_TILT.get(away)
    if home_tilt or away_tilt:
        lines += ["=== TEAM STYLE (PELE TILT RATINGS) ==="]
        if home_tilt:
            lines.append(f"  {home}: {home_tilt[1]}")
            if len(home_tilt) > 2:
                lines.append(f"  {home} draw rate (last 20 competitive matches): ~{home_tilt[2]:.0%}")
        if away_tilt:
            lines.append(f"  {away}: {away_tilt[1]}")
            if len(away_tilt) > 2:
                lines.append(f"  {away} draw rate (last 20 competitive matches): ~{away_tilt[2]:.0%}")
        lines.append("")

    lines += [
        "=== CURRENT BOOKMAKER ODDS ===",
        f"  {home} win: {home_odds} (implied {implied_home:.1%})",
        f"  Draw: {draw_odds} (implied {implied_draw:.1%})",
        f"  {away} win: {away_odds} (implied {implied_away:.1%})",
        "",
        "=== MATCH CONTEXT (ODDS, FORM, HEAD-TO-HEAD) ===",
        context or "No additional context available.",
        "",
    ]

    # Dead-rubber injection for MD3 games
    dead_rubber = _get_dead_rubber_context(match_data)
    if dead_rubber:
        lines += [dead_rubber, ""]

    # Knockout stage: 90-min scoring rules + contest draw detection (v-contest)
    if _is_knockout(stage):
        lines += [
            "=== KNOCKOUT STAGE: SCORING RULES ===",
            "IMPORTANT: This competition scores on the 90-MINUTE result only. Extra time and penalty shootouts",
            "are ignored entirely. A match that ends 1-1 after 90 minutes and goes to penalties is scored as",
            "a 1-1 draw — predicting 1-1 would earn the full 4 points.",
            "If you think a match is evenly balanced and likely to be tight, predict a DRAW scoreline.",
            "",
            "=== DRAW DETECTION (KNOCKOUT) ===",
            "Draws after 90 minutes occur in ~20% of WC knockout matches. THINK THROUGH these internally,",
            "do NOT output your analysis — only output the final JSON. Mentally answer these three questions:",
            "  1. Are both teams within 80 Elo points of each other (roughly equal quality)?",
            "  2. Is the bookmaker draw implied probability above 22% (draw odds below 4.5)?",
            "  3. Does either team have a defensive playing style that tends toward low-scoring draws",
            "     (e.g. Morocco 40% draw rate, Japan 30%, Colombia 35%, Croatia 32%)?",
            "If 2 or more answers are YES, your prediction SHOULD be a draw scoreline (0-0 or 1-1).",
            "For lopsided matchups (implied win >65%), back the favourite with a decisive scoreline.",
            "Do NOT predict 1-1 as a hedge on dominant-favourite matches — reserve it for genuine 50/50s.",
            "",
            "=== 0-0 / LOW-SCORING DETECTOR ===",
            "Predict 0-0 or 1-0 when ALL of the following apply:",
            "  - Both teams are defensively elite (Morocco, Japan, Uruguay, Iran, Colombia, Croatia, Panama)",
            "  - The bookmaker total goals line is below 2.0 (or implied draw odds below 3.2)",
            "  - Match context suggests both sides will play cautiously and protect a narrow result",
            "0-0 occurred in ~9% of WC2026 group matches. It is a valid prediction — do not suppress it.",
            "",
            "=== CONTEST SCORING ===",
            "Scoring: exact scoreline = 4 pts, correct goal-difference = 2 pts, correct result direction = 1 pt, wrong = 0 pts.",
            "OPTIMAL STRATEGY: commit to your single most likely scoreline. Do NOT hedge toward 1-1 or 1-0 as a safe default.",
            "Pick the MODE (most probable outcome), not the mean. A 30% confident 2-1 beats a 15% confident 1-1.",
            "",
        ]
    else:
        lines += [
            "=== DRAW DETECTION ===",
            "Draws occur in ~28% of WC2026 group matches. Before finalising, check explicitly:",
            "  - Are these teams within 80 Elo points of each other (roughly equal quality)?",
            "  - Does the match context (form, H2H, advancement stakes) point to a cautious, low-risk approach?",
            "ONLY predict a draw if BOTH conditions are clearly satisfied AND the bookmaker draw odds are below 3.5.",
            "If the favourite has implied win probability above 55%, do NOT predict a draw — back the favourite.",
            "The 1-1 scoreline is over-predicted by AI models at 2x its actual rate. Only predict 1-1 when",
            "both teams are genuinely evenly matched. Otherwise predict 1-0, 2-0, 2-1, or 0-1.",
            "",
            "=== CONTEST SCORING ===",
            "Scoring: exact scoreline = 4 pts, correct goal-difference = 2 pts, correct result direction = 1 pt, wrong = 0 pts.",
            "OPTIMAL STRATEGY: commit to your single most likely scoreline. Do NOT hedge toward 1-1 or 1-0 as a safe default.",
            "Pick the MODE (most probable outcome), not the mean. A 30% confident 2-1 beats a 15% confident 1-1.",
            "",
        ]

    lines += [
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
        _get_draw_reminder(stage),
        "",
        "1. GOAL VOLUME: WC2026 matches average 2.9 goals. Under-predicting goals is the "
        "single most common AI forecasting error. If your total is below 2, reconsider.",
        "",
        "2. BRIER SCORING: Assign at least 10% probability to every outcome unless there "
        "is an overwhelming structural reason to exclude it.",
        "",
        f"State your predicted scoreline in your reasoning as: 'Predicted score: X-Y'. Then output the JSON.",
        "",
        "Respond ONLY with valid JSON:",
        json.dumps({
            "home_goals": 0,
            "away_goals": 0,
            "home_win_prob": 0.0,
            "draw_prob": 0.0,
            "away_win_prob": 0.0,
            "confidence": 0,
            "reasoning": "...",
        }, indent=2),
    ]
    return "\n".join(lines)


def _extract_json(text: str) -> Optional[dict]:
    """Extract JSON from model response with 4 repair passes."""
    text = text.strip()
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if fence_match:
        text = fence_match.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    candidate = match.group(0) if match else text
    # Repair 1: missing opening quote on key
    repaired = re.sub(r'(?<!["\w])(\w+)":', r'"\1":', candidate)
    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        pass
    # Repair 2: stray non-JSON char before { in array
    repaired2 = re.sub(r'(,\s*)\S+(\s+\{)', r'\1\2', candidate)
    try:
        return json.loads(repaired2)
    except json.JSONDecodeError:
        pass
    # Repair 3: unescaped quotes inside reasoning string values
    def _fix_reasoning_quotes(s: str) -> str:
        lines = s.split('\n')
        out = []
        for line in lines:
            m = re.match(r'^(\s*"reasoning"\s*:\s*")(.*)(")(\s*,?)$', line)
            if m:
                inner_fixed = re.sub(r'(?<!\\)"', '\\"', m.group(2))
                out.append(f'{m.group(1)}{inner_fixed}"{m.group(4)}')
            else:
                out.append(line)
        return '\n'.join(out)
    repaired3 = _fix_reasoning_quotes(candidate)
    try:
        return json.loads(repaired3)
    except json.JSONDecodeError:
        pass
    # Repair 4: multi-line reasoning value (e.g. GPT-5 free-form text) — collapse to single line
    def _collapse_multiline_reasoning(s: str) -> str:
        return re.sub(
            r'("reasoning"\s*:\s*")([^"]*(?:"(?![\s,}\]])[^"]*)*)(")(\s*[,}])',
            lambda m: m.group(1) + m.group(2).replace('\n', ' ').replace('\r', '') + '"' + m.group(4),
            s,
            flags=re.DOTALL,
        )
    repaired4 = _collapse_multiline_reasoning(candidate)
    try:
        return json.loads(repaired4)
    except json.JSONDecodeError:
        pass
    return None


def _archive_forecasts() -> str:
    """Copy current forecasts/ JSON files to a timestamped archive subfolder."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
    dest = os.path.join(ARCHIVE_DIR, stamp)
    if os.path.exists(dest):
        return dest
    os.makedirs(dest, exist_ok=True)
    for fname in os.listdir(FORECASTS_DIR):
        fpath = os.path.join(FORECASTS_DIR, fname)
        if os.path.isfile(fpath) and fname.endswith(".json"):
            shutil.copy2(fpath, os.path.join(dest, fname))
    logger.info("Archived %d forecast files to %s", len(os.listdir(dest)), dest)
    return dest


def _is_contaminated(match_date: str, context_fetched_at: Optional[str]) -> bool:
    """Return True if context was fetched on or after match kickoff date."""
    if not context_fetched_at:
        return False
    try:
        # match_date is YYYY-MM-DD; context_fetched_at is ISO timestamp
        fetch_date = context_fetched_at[:10]
        return fetch_date >= match_date
    except Exception:
        return False

def _call_model(model_cfg: dict, prompt: str, config: dict) -> dict:
    """Call one model (Anthropic or LiteLLM) and return result with token/cost metadata."""
    model_id = model_cfg["id"]
    sdk = model_cfg.get("sdk", "anthropic")
    vendor = model_cfg.get("vendor", "")

    try:
        if sdk == "anthropic":
            api_key = (os.environ.get("ANTHROPIC_API_KEY")
                       or os.environ.get("ANTHROPIC_AUTH_TOKEN")
                       or os.environ.get("HAI_API_KEY"))
            base_url = os.environ.get("ANTHROPIC_BASE_URL")
            client = anthropic.Anthropic(api_key=api_key, base_url=base_url) if base_url else anthropic.Anthropic(api_key=api_key)
            response = client.messages.create(
                model=model_id,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens

        else:  # litellm — OpenAI-compatible
            hai_key = os.environ.get("HAI_API_KEY", os.environ.get("ANTHROPIC_API_KEY", ""))
            litellm_url = config.get("litellm_base_url", "http://localhost:6655/litellm/v1")
            client = openai_lib.OpenAI(api_key=hai_key, base_url=litellm_url)
            # gpt-5 needs more tokens — it uses thinking tokens before JSON output
            openai_max = 4096 if model_cfg.get("tier") == "flagship" else 1024
            extra = {"max_completion_tokens": openai_max} if vendor == "openai" else {"max_tokens": 1024}
            if vendor == "openai":
                # Force structured JSON output to prevent multi-line reasoning parse failures
                try:
                    response = client.chat.completions.create(
                        model=model_id,
                        messages=[{"role": "user", "content": prompt}],
                        response_format={"type": "json_object"},
                        **extra,
                    )
                except Exception:
                    response = client.chat.completions.create(
                        model=model_id,
                        messages=[{"role": "user", "content": prompt}],
                        **extra,
                    )
            else:
                response = client.chat.completions.create(
                    model=model_id,
                    messages=[{"role": "user", "content": prompt}],
                    **extra,
                )
            raw = response.choices[0].message.content
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens

        cost_usd = (
            input_tokens / 1_000_000 * model_cfg["input_cost_per_million"]
            + output_tokens / 1_000_000 * model_cfg["output_cost_per_million"]
        )
        parsed = _extract_json(raw or "")
        error = None

        if parsed is None:
            return {
                "raw_response": raw,
                "home_goals": None,
                "away_goals": None,
                "home_win_prob": None,
                "draw_prob": None,
                "away_win_prob": None,
                "confidence": None,
                "reasoning": None,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost_usd": cost_usd,
                "error": "parse_error",
            }

        # Normalise probabilities to sum to 1.0
        hw = float(parsed.get("home_win_prob") or 0)
        dp = float(parsed.get("draw_prob") or 0)
        aw = float(parsed.get("away_win_prob") or 0)
        total = hw + dp + aw
        if total > 0:
            hw, dp, aw = hw / total, dp / total, aw / total

        return {
            "raw_response": raw,
            "home_goals": int(parsed["home_goals"]) if parsed.get("home_goals") is not None else None,
            "away_goals": int(parsed["away_goals"]) if parsed.get("away_goals") is not None else None,
            "home_win_prob": round(hw, 4),
            "draw_prob": round(dp, 4),
            "away_win_prob": round(aw, 4),
            "confidence": int(parsed.get("confidence") or 50),
            "reasoning": parsed.get("reasoning", ""),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": cost_usd,
            "error": "null_goals" if (parsed.get("home_goals") is None or parsed.get("away_goals") is None) else error,
        }

    except Exception as e:
        logger.error("Error calling model %s: %s", model_id, e, exc_info=True)
        return {
            "raw_response": None,
            "home_goals": None,
            "away_goals": None,
            "home_win_prob": None,
            "draw_prob": None,
            "away_win_prob": None,
            "confidence": None,
            "reasoning": None,
            "input_tokens": 0,
            "output_tokens": 0,
            "cost_usd": 0.0,
            "error": str(e),
        }


# Per-vendor concurrency semaphores
_VENDOR_SEMAPHORES: dict[str, threading.Semaphore] = {}
_VENDOR_SEMAPHORE_LOCK = threading.Lock()


def _vendor_semaphore(vendor: str, config: dict) -> threading.Semaphore:
    with _VENDOR_SEMAPHORE_LOCK:
        if vendor not in _VENDOR_SEMAPHORES:
            limits = config.get("settings", {}).get("vendor_concurrency", {})
            limit = limits.get(vendor, 2)
            _VENDOR_SEMAPHORES[vendor] = threading.Semaphore(limit)
        return _VENDOR_SEMAPHORES[vendor]


def _forecast_one(model_cfg: dict, match_data: dict, prompt: str,
                  forecast_date: str, config: dict, force: bool) -> dict:
    """Call one model for one match, respecting per-vendor concurrency. Thread-safe."""
    mid = match_data["match_id"]
    short = model_cfg.get("short", model_cfg["id"])
    vendor = model_cfg.get("vendor", "")
    out_path = os.path.join(FORECASTS_DIR, f"{mid}_{short}.json")

    if os.path.exists(out_path) and not force:
        return {"path": out_path, "skipped": True}

    sem = _vendor_semaphore(vendor, config)
    with sem:
        logger.info("Calling %s for %s...", model_cfg["id"], mid)
        result = _call_model(model_cfg, prompt, config)

    record = {
        "match_id": mid,
        "forecast_date": forecast_date,
        "match_date": match_data["date"],
        "context_fetched_at": match_data.get("context_fetched_at"),
        "model_short": short,
        "model_id": model_cfg["id"],
        "vendor": vendor,
        "prompt_version": "v-contest",
        **result,
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)

    logger.info("Saved %s (cost: $%.5f, error: %s)", out_path, result["cost_usd"], result.get("error"))
    return {"path": out_path, "skipped": False, "error": result.get("error")}


def _compute_consensus(match_data: dict, forecast_date: str, config: dict) -> Optional[dict]:
    """Load all model forecasts for a match and compute consensus + EV."""
    mid = match_data["match_id"]
    records = []
    for model_cfg in config["models"]:
        short = model_cfg.get("short", model_cfg["id"])
        path = os.path.join(FORECASTS_DIR, f"{mid}_{short}.json")
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as f:
            rec = json.load(f)
        if rec.get("error") or rec.get("home_goals") is None:
            continue
        records.append(rec)

    if not records:
        return None

    match_date_str = match_data.get("date", "")

    # Separate clean vs contaminated records
    clean_records = [r for r in records if not _is_contaminated(match_date_str, r.get("context_fetched_at"))]
    contaminated_records = [r for r in records if _is_contaminated(match_date_str, r.get("context_fetched_at"))]
    if contaminated_records:
        logger.warning("  %d contaminated model(s) excluded from consensus for %s: %s",
                       len(contaminated_records), match_data["match_id"],
                       [r["model_short"] for r in contaminated_records])
    # Use only clean records for consensus; fall back to all if all are contaminated
    voting_records = clean_records if clean_records else records

    # Load Bayesian weights (inverse-Brier, normalised). Fall back to equal weights.
    model_weights = _load_model_weights()
    def _w(r: dict) -> float:
        return model_weights.get(r["model_short"], 1.0 / len(voting_records))

    total_w = sum(_w(r) for r in voting_records)

    home_goals_list = [r["home_goals"] for r in voting_records]
    away_goals_list = [r["away_goals"] for r in voting_records]

    # Weighted probability averages
    avg_hw = sum(_w(r) * r["home_win_prob"] for r in voting_records) / total_w
    avg_dp = sum(_w(r) * r["draw_prob"]     for r in voting_records) / total_w
    avg_aw = sum(_w(r) * r["away_win_prob"] for r in voting_records) / total_w

    # v12: goal rescaling — models systematically underpredict goals (2.3 predicted vs 2.98 actual).
    # Apply a calibrated multiplier so predicted total goal volume matches tournament average.
    # Rescale: round each model's goals using a multiplier, preserving result direction.
    goal_rescale = config.get("goal_rescale_factor", 0.0)
    if goal_rescale > 0:
        rescaled_home, rescaled_away = [], []
        for h, a in zip(home_goals_list, away_goals_list):
            total = h + a
            new_total = total * goal_rescale
            if h == a:
                # Draw: scale evenly
                g = round(new_total / 2)
                rescaled_home.append(g)
                rescaled_away.append(g)
            elif h > a:
                # Home win: preserve GD, lift total
                ratio = h / total if total > 0 else 0.6
                new_h = max(round(new_total * ratio), h)
                new_a = max(round(new_total * (1 - ratio)), a)
                rescaled_home.append(new_h)
                rescaled_away.append(new_a)
            else:
                ratio = a / total if total > 0 else 0.6
                new_a = max(round(new_total * ratio), a)
                new_h = max(round(new_total * (1 - ratio)), h)
                rescaled_home.append(new_h)
                rescaled_away.append(new_a)
        home_goals_list = rescaled_home
        away_goals_list = rescaled_away

    # Weighted scoreline vote (weight each model's predicted scoreline by its weight)
    from collections import Counter, defaultdict as _dd
    scoreline_counts = Counter(zip(home_goals_list, away_goals_list))  # raw counts for display
    scoreline_weights: dict = _dd(float)
    for r, h_g, a_g in zip(voting_records, home_goals_list, away_goals_list):
        scoreline_weights[(h_g, a_g)] += _w(r)

    # v12: EV commit rule — pick scoreline with highest contest EV, not just highest frequency.
    # EV(S) = P(S exact)*4 + P(same GD)*2 + P(same result)*1
    # P(same GD/result) estimated from scoreline weight distribution.
    use_ev_commit = config.get("ev_commit", False)
    if use_ev_commit:
        total_sw = sum(scoreline_weights.values())

        def _scoreline_ev(h: int, a: int) -> float:
            p_exact = scoreline_weights.get((h, a), 0.0) / total_sw
            gd = h - a
            p_same_gd = sum(w for (sh, sa), w in scoreline_weights.items()
                            if sh - sa == gd and (sh, sa) != (h, a)) / total_sw
            result = (1 if h > a else (-1 if h < a else 0))
            p_same_result = sum(w for (sh, sa), w in scoreline_weights.items()
                                if (1 if sh > sa else (-1 if sh < sa else 0)) == result
                                and sh - sa != gd) / total_sw
            return p_exact * 4 + p_same_gd * 2 + p_same_result * 1

        best_ev_scoreline = max(scoreline_weights.keys(), key=lambda s: _scoreline_ev(s[0], s[1]))
        mode_home, mode_away = best_ev_scoreline
        logger.debug("  EV commit for %s: %d-%d (EV=%.3f)",
                     mid, mode_home, mode_away, _scoreline_ev(mode_home, mode_away))
    else:
        best_scoreline = max(scoreline_weights.items(), key=lambda x: x[1])
        # Check for ties in weighted vote
        top_w = best_scoreline[1]
        top_scorelines = [s for s, w in scoreline_weights.items() if abs(w - top_w) < 1e-9]
        if len(top_scorelines) == 1:
            mode_home, mode_away = top_scorelines[0]
        else:
            # Tiebreak by probability-weighted result direction
            if avg_hw > avg_aw:
                top_scorelines.sort(key=lambda s: s[0] - s[1], reverse=True)
            else:
                top_scorelines.sort(key=lambda s: s[1] - s[0], reverse=True)
            mode_home, mode_away = top_scorelines[0]
    consensus_home = mode_home
    consensus_away = mode_away

    using_weights = bool(model_weights)
    if using_weights:
        logger.debug("  Bayesian weights applied for %s (top model weight: %.4f)",
                     mid, max(_w(r) for r in voting_records))

    # v5: draw override — if avg draw probability exceeds threshold, force draw scoreline.
    # Calibrated via backtest on 50 completed matches: 0.35 is the optimal threshold.
    draw_override_threshold = config.get("draw_prob_threshold", 0.0)
    if draw_override_threshold > 0 and avg_dp >= draw_override_threshold and consensus_home != consensus_away:
        all_goals = home_goals_list + away_goals_list
        tie_g = round(statistics.mean(all_goals) / 2) if all_goals else 1
        consensus_home = tie_g
        consensus_away = tie_g
        logger.info("  draw override applied for %s (avg_dp=%.2f >= %.2f): %d-%d",
                    mid, avg_dp, draw_override_threshold, consensus_home, consensus_away)

    # v12: draw floor — prevent draw under-detection after contest-v2 suppression.
    # If Kalshi implied draw > ensemble draw_prob by > 0.10 and favourite not dominant,
    # force a draw scoreline. Guards against over-correcting the 1-1 attractor fix.
    odds = match_data.get("odds", {})
    draw_floor_gap = config.get("draw_floor_gap", 0.0)  # default off
    if draw_floor_gap > 0 and consensus_home != consensus_away:
        implied_draw = odds.get("implied_draw", 0.0)
        if implied_draw > 0 and (implied_draw - avg_dp) >= draw_floor_gap:
            # Market prices a draw more strongly than the ensemble — override
            all_goals = home_goals_list + away_goals_list
            tie_g = round(statistics.mean(all_goals) / 2) if all_goals else 1
            consensus_home = tie_g
            consensus_away = tie_g
            logger.info("  draw floor applied for %s (implied_draw=%.2f, avg_dp=%.2f, gap=%.2f): %d-%d",
                        mid, implied_draw, avg_dp, implied_draw - avg_dp,
                        consensus_home, consensus_away)

    # EV = model_prob × payout − (1 − model_prob); payout = decimal_odds − 1
    odds = match_data.get("odds", {})
    ev_threshold = config.get("ev_threshold", 0.05)

    def ev(model_prob: float, decimal_odds: float) -> float:
        if decimal_odds <= 1:
            return 0.0
        return round(model_prob * (decimal_odds - 1) - (1 - model_prob), 4)

    ev_home = ev(avg_hw, odds.get("home_win", 2.50))
    ev_draw = ev(avg_dp, odds.get("draw", 3.20))
    ev_away = ev(avg_aw, odds.get("away_win", 2.80))

    value_bets = []
    if ev_home > ev_threshold:
        value_bets.append({"outcome": "home_win", "ev": ev_home, "odds": odds.get("home_win")})
    if ev_draw > ev_threshold:
        value_bets.append({"outcome": "draw", "ev": ev_draw, "odds": odds.get("draw")})
    if ev_away > ev_threshold:
        value_bets.append({"outcome": "away_win", "ev": ev_away, "odds": odds.get("away_win")})

    consensus = {
        "match_id": mid,
        "forecast_date": forecast_date,
        "match_date": match_data["date"],
        "home": match_data["home"],
        "away": match_data["away"],
        "models_included": len(voting_records),
        "models_contaminated": len(contaminated_records),
        "consensus_home_goals": consensus_home,
        "consensus_away_goals": consensus_away,
        "scoreline_votes": {f"{h}-{a}": c for (h,a),c in scoreline_counts.most_common()},
        "avg_home_win_prob": round(avg_hw, 4),
        "avg_draw_prob": round(avg_dp, 4),
        "avg_away_win_prob": round(avg_aw, 4),
        "bayesian_weighted": using_weights,
        "ev_home_win": ev_home,
        "ev_draw": ev_draw,
        "ev_away_win": ev_away,
        "value_bets": value_bets,
        "implied_home": odds.get("implied_home"),
        "implied_draw": odds.get("implied_draw"),
        "implied_away": odds.get("implied_away"),
    }

    out_path = os.path.join(FORECASTS_DIR, f"{mid}_CONSENSUS.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(consensus, f, indent=2, ensure_ascii=False)
    return consensus


def forecast_match(match_data: dict, config: dict, force: bool = False) -> list:
    """Run all 12 models for one match in parallel. Returns list of result dicts."""
    mid = match_data["match_id"]
    forecast_date = date.today().isoformat()
    prompt = build_prompt(match_data)
    logger.info("Forecasting %s with %d models...", mid, len(config["models"]))

    max_workers = min(len(config["models"]), 12)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_forecast_one, model_cfg, match_data, prompt, forecast_date, config, force): model_cfg
            for model_cfg in config["models"]
        }
        results = []
        for future in as_completed(futures):
            model_cfg = futures[future]
            try:
                results.append(future.result())
            except Exception as e:
                logger.error("Unhandled error for %s/%s: %s", model_cfg["id"], mid, e, exc_info=True)
                results.append({"skipped": False, "error": str(e)})

    consensus = _compute_consensus(match_data, forecast_date, config)
    if consensus:
        logger.info("Consensus for %s: %d-%d (EV home=%.3f draw=%.3f away=%.3f)",
                    mid, consensus["consensus_home_goals"], consensus["consensus_away_goals"],
                    consensus["ev_home_win"], consensus["ev_draw"], consensus["ev_away_win"])
    return results


def forecast_matches(match_data_list: list, config: dict, force: bool = False) -> list:
    """Run all matches × all models in parallel with per-vendor concurrency."""
    forecast_date = date.today().isoformat()
    tasks = []
    for match_data in match_data_list:
        prompt = build_prompt(match_data)
        for model_cfg in config["models"]:
            tasks.append((model_cfg, match_data, prompt))

    if not tasks:
        return []

    max_workers = min(len(tasks), 48)
    all_results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_forecast_one, model_cfg, match_data, prompt, forecast_date, config, force): (model_cfg["id"], match_data["match_id"])
            for model_cfg, match_data, prompt in tasks
        }
        for future in as_completed(futures):
            model_id, mid = futures[future]
            try:
                all_results.append(future.result())
            except Exception as e:
                logger.error("Unhandled error for %s/%s: %s", model_id, mid, e, exc_info=True)
                all_results.append({"skipped": False, "error": str(e)})

    # Compute consensus for each match
    for match_data in match_data_list:
        _compute_consensus(match_data, forecast_date, config)

    return all_results


def load_match_data(match_id: str) -> Optional[dict]:
    """Load match data JSON from data/ directory."""
    path = os.path.join(DATA_DIR, f"{match_id}.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    config = _load_config()

    filter_date = None
    filter_match = None
    force = "--force" in sys.argv

    if "--date" in sys.argv:
        idx = sys.argv.index("--date")
        filter_date = sys.argv[idx + 1]
    if "--match" in sys.argv:
        idx = sys.argv.index("--match")
        filter_match = sys.argv[idx + 1]

    # Find data files to forecast
    if filter_match:
        data_files = [os.path.join(DATA_DIR, f"{filter_match}.json")]
    elif filter_date:
        data_files = [
            os.path.join(DATA_DIR, f)
            for f in os.listdir(DATA_DIR)
            if f.endswith(".json") and filter_date in f
        ]
    else:
        today = date.today().isoformat()
        data_files = [
            os.path.join(DATA_DIR, f)
            for f in os.listdir(DATA_DIR)
            if f.endswith(".json") and not f.endswith("_CONSENSUS.json")
        ]

    data_files = [p for p in data_files if os.path.exists(p)]
    if not data_files:
        logger.warning("No match data files found. Run fixtures.py first.")
        return

    match_data_list = []
    for path in data_files:
        with open(path, encoding="utf-8") as f:
            match_data_list.append(json.load(f))

    logger.info("Forecasting %d match(es)...", len(match_data_list))

    if force:
        archive_path = _archive_forecasts()
        logger.info("Archived existing forecasts to %s before --force re-run", archive_path)

    results = forecast_matches(match_data_list, config, force=force)

    n_skipped = sum(1 for r in results if r.get("skipped"))
    n_errors = sum(1 for r in results if r.get("error") and not r.get("skipped"))
    logger.info("Done: %d total, %d skipped, %d errors.", len(results), n_skipped, n_errors)


if __name__ == "__main__":
    main()
