"""
fixtures.py — Fetch 2026 FIFA World Cup match data.

For each match, retrieves team form, head-to-head history, current odds,
and a narrative context summary via Perplexity Sonar.

Usage:
    python fixtures.py                        # fetch all upcoming matches
    python fixtures.py --date 2026-06-14      # fetch matches on a specific date
    python fixtures.py --match "Mexico_South_Africa_2026-06-11"  # fetch one match
"""

import json
import os
import re
import sys
import time
from datetime import date, datetime
from typing import Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# 2026 FIFA World Cup — Full Group Stage Schedule (72 matches, 12 groups)
# Draw held December 5, 2025, Kennedy Center, Washington D.C.
#
# HOME/AWAY NOTE: FIFA assigned home/away by draw order, not venue.
# For forecasting, host-nation teams playing at their own country's stadiums
# must be listed as HOME regardless of FIFA's nominal assignment.
# Fixed in group stage: Mexico (Azteca/Akron), USA (SoFi), Canada (BC Place/BMO).
# KNOCKOUT STAGE: Apply the same fix — when building knockout fixtures, always
# assign the host nation (USA, Canada, Mexico) as HOME when the venue is in
# their country, regardless of which bracket slot they came from.
# ---------------------------------------------------------------------------
FIXTURES = [
    # Group A — Mexico, South Korea, Czech Republic, South Africa
    {"date": "2026-06-11", "home": "Mexico",         "away": "South Africa",   "venue": "Estadio Azteca, Mexico City",           "stage": "Group A"},
    {"date": "2026-06-11", "home": "South Korea",    "away": "Czech Republic", "venue": "Estadio Akron, Zapopan",                "stage": "Group A"},
    {"date": "2026-06-18", "home": "Czech Republic", "away": "South Africa",   "venue": "Mercedes-Benz Stadium, Atlanta",        "stage": "Group A"},
    {"date": "2026-06-18", "home": "Mexico",         "away": "South Korea",    "venue": "Estadio Akron, Zapopan",                "stage": "Group A"},
    {"date": "2026-06-24", "home": "Mexico",         "away": "Czech Republic", "venue": "Estadio Azteca, Mexico City",           "stage": "Group A"},
    {"date": "2026-06-24", "home": "South Africa",   "away": "South Korea",    "venue": "Estadio BBVA, Guadalupe",               "stage": "Group A"},
    # Group B — Canada, Switzerland, Qatar, Bosnia & Herzegovina
    {"date": "2026-06-12", "home": "Canada",         "away": "Bosnia & Herzegovina", "venue": "BMO Field, Toronto",             "stage": "Group B"},
    {"date": "2026-06-13", "home": "Qatar",          "away": "Switzerland",    "venue": "Levi's Stadium, Santa Clara",           "stage": "Group B"},
    {"date": "2026-06-18", "home": "Switzerland",    "away": "Bosnia & Herzegovina", "venue": "SoFi Stadium, Inglewood",        "stage": "Group B"},
    {"date": "2026-06-18", "home": "Canada",         "away": "Qatar",          "venue": "BC Place, Vancouver",                  "stage": "Group B"},
    {"date": "2026-06-24", "home": "Switzerland",    "away": "Canada",         "venue": "BC Place, Vancouver",                  "stage": "Group B"},
    {"date": "2026-06-24", "home": "Bosnia & Herzegovina", "away": "Qatar",    "venue": "Lumen Field, Seattle",                 "stage": "Group B"},
    # Group C — Brazil, Morocco, Scotland, Haiti
    {"date": "2026-06-13", "home": "Brazil",         "away": "Morocco",        "venue": "MetLife Stadium, East Rutherford",      "stage": "Group C"},
    {"date": "2026-06-13", "home": "Haiti",          "away": "Scotland",       "venue": "Gillette Stadium, Foxborough",          "stage": "Group C"},
    {"date": "2026-06-19", "home": "Scotland",       "away": "Morocco",        "venue": "Gillette Stadium, Foxborough",          "stage": "Group C"},
    {"date": "2026-06-19", "home": "Brazil",         "away": "Haiti",          "venue": "Lincoln Financial Field, Philadelphia", "stage": "Group C"},
    {"date": "2026-06-24", "home": "Scotland",       "away": "Brazil",         "venue": "Hard Rock Stadium, Miami Gardens",      "stage": "Group C"},
    {"date": "2026-06-24", "home": "Morocco",        "away": "Haiti",          "venue": "Mercedes-Benz Stadium, Atlanta",        "stage": "Group C"},
    # Group D — USA, Paraguay, Turkey, Australia
    {"date": "2026-06-12", "home": "USA",            "away": "Paraguay",       "venue": "SoFi Stadium, Inglewood",               "stage": "Group D"},
    {"date": "2026-06-13", "home": "Australia",      "away": "Turkey",         "venue": "BC Place, Vancouver",                   "stage": "Group D"},
    {"date": "2026-06-19", "home": "USA",            "away": "Australia",      "venue": "Lumen Field, Seattle",                  "stage": "Group D"},
    {"date": "2026-06-19", "home": "Turkey",         "away": "Paraguay",       "venue": "Levi's Stadium, Santa Clara",           "stage": "Group D"},
    {"date": "2026-06-25", "home": "USA",            "away": "Turkey",         "venue": "SoFi Stadium, Inglewood",               "stage": "Group D"},
    {"date": "2026-06-25", "home": "Paraguay",       "away": "Australia",      "venue": "Levi's Stadium, Santa Clara",           "stage": "Group D"},
    # Group E — Germany, Ecuador, Ivory Coast, Curacao
    {"date": "2026-06-14", "home": "Germany",        "away": "Curacao",        "venue": "NRG Stadium, Houston",                  "stage": "Group E"},
    {"date": "2026-06-14", "home": "Ivory Coast",    "away": "Ecuador",        "venue": "Lincoln Financial Field, Philadelphia", "stage": "Group E"},
    {"date": "2026-06-20", "home": "Germany",        "away": "Ivory Coast",    "venue": "BMO Field, Toronto",                   "stage": "Group E"},
    {"date": "2026-06-20", "home": "Ecuador",        "away": "Curacao",        "venue": "Arrowhead Stadium, Kansas City",        "stage": "Group E"},
    {"date": "2026-06-25", "home": "Curacao",        "away": "Ivory Coast",    "venue": "Lincoln Financial Field, Philadelphia", "stage": "Group E"},
    {"date": "2026-06-25", "home": "Ecuador",        "away": "Germany",        "venue": "MetLife Stadium, East Rutherford",      "stage": "Group E"},
    # Group F — Netherlands, Japan, Tunisia, Sweden
    {"date": "2026-06-14", "home": "Netherlands",    "away": "Japan",          "venue": "AT&T Stadium, Arlington",               "stage": "Group F"},
    {"date": "2026-06-14", "home": "Sweden",         "away": "Tunisia",        "venue": "Estadio BBVA, Guadalupe",               "stage": "Group F"},
    {"date": "2026-06-20", "home": "Netherlands",    "away": "Sweden",         "venue": "NRG Stadium, Houston",                  "stage": "Group F"},
    {"date": "2026-06-20", "home": "Tunisia",        "away": "Japan",          "venue": "Estadio BBVA, Guadalupe",               "stage": "Group F"},
    {"date": "2026-06-25", "home": "Japan",          "away": "Sweden",         "venue": "AT&T Stadium, Arlington",               "stage": "Group F"},
    {"date": "2026-06-25", "home": "Tunisia",        "away": "Netherlands",    "venue": "Arrowhead Stadium, Kansas City",        "stage": "Group F"},
    # Group G — Belgium, Iran, Egypt, New Zealand
    {"date": "2026-06-15", "home": "Belgium",        "away": "Egypt",          "venue": "Lumen Field, Seattle",                  "stage": "Group G"},
    {"date": "2026-06-15", "home": "Iran",           "away": "New Zealand",    "venue": "SoFi Stadium, Inglewood",               "stage": "Group G"},
    {"date": "2026-06-21", "home": "Belgium",        "away": "Iran",           "venue": "SoFi Stadium, Inglewood",               "stage": "Group G"},
    {"date": "2026-06-21", "home": "New Zealand",    "away": "Egypt",          "venue": "BC Place, Vancouver",                   "stage": "Group G"},
    {"date": "2026-06-26", "home": "Egypt",          "away": "Iran",           "venue": "Lumen Field, Seattle",                  "stage": "Group G"},
    {"date": "2026-06-26", "home": "New Zealand",    "away": "Belgium",        "venue": "BC Place, Vancouver",                   "stage": "Group G"},
    # Group H — Spain, Uruguay, Saudi Arabia, Cape Verde
    {"date": "2026-06-15", "home": "Spain",          "away": "Cape Verde",     "venue": "Mercedes-Benz Stadium, Atlanta",        "stage": "Group H"},
    {"date": "2026-06-15", "home": "Saudi Arabia",   "away": "Uruguay",        "venue": "Hard Rock Stadium, Miami Gardens",      "stage": "Group H"},
    {"date": "2026-06-21", "home": "Spain",          "away": "Saudi Arabia",   "venue": "Mercedes-Benz Stadium, Atlanta",        "stage": "Group H"},
    {"date": "2026-06-21", "home": "Uruguay",        "away": "Cape Verde",     "venue": "Hard Rock Stadium, Miami Gardens",      "stage": "Group H"},
    {"date": "2026-06-26", "home": "Cape Verde",     "away": "Saudi Arabia",   "venue": "NRG Stadium, Houston",                  "stage": "Group H"},
    {"date": "2026-06-26", "home": "Uruguay",        "away": "Spain",          "venue": "Estadio Akron, Zapopan",                "stage": "Group H"},
    # Group I — France, Senegal, Norway, Iraq
    {"date": "2026-06-16", "home": "France",         "away": "Senegal",        "venue": "MetLife Stadium, East Rutherford",      "stage": "Group I"},
    {"date": "2026-06-16", "home": "Iraq",           "away": "Norway",         "venue": "Gillette Stadium, Foxborough",          "stage": "Group I"},
    {"date": "2026-06-22", "home": "France",         "away": "Iraq",           "venue": "Lincoln Financial Field, Philadelphia", "stage": "Group I"},
    {"date": "2026-06-22", "home": "Norway",         "away": "Senegal",        "venue": "MetLife Stadium, East Rutherford",      "stage": "Group I"},
    {"date": "2026-06-26", "home": "Norway",         "away": "France",         "venue": "Gillette Stadium, Foxborough",          "stage": "Group I"},
    {"date": "2026-06-26", "home": "Senegal",        "away": "Iraq",           "venue": "BMO Field, Toronto",                   "stage": "Group I"},
    # Group J — Argentina, Austria, Algeria, Jordan
    {"date": "2026-06-16", "home": "Argentina",      "away": "Algeria",        "venue": "Arrowhead Stadium, Kansas City",        "stage": "Group J"},
    {"date": "2026-06-16", "home": "Austria",        "away": "Jordan",         "venue": "Levi's Stadium, Santa Clara",           "stage": "Group J"},
    {"date": "2026-06-22", "home": "Argentina",      "away": "Austria",        "venue": "AT&T Stadium, Arlington",               "stage": "Group J"},
    {"date": "2026-06-22", "home": "Jordan",         "away": "Algeria",        "venue": "Levi's Stadium, Santa Clara",           "stage": "Group J"},
    {"date": "2026-06-27", "home": "Algeria",        "away": "Austria",        "venue": "Arrowhead Stadium, Kansas City",        "stage": "Group J"},
    {"date": "2026-06-27", "home": "Jordan",         "away": "Argentina",      "venue": "AT&T Stadium, Arlington",               "stage": "Group J"},
    # Group K — Portugal, Colombia, Uzbekistan, DR Congo
    {"date": "2026-06-17", "home": "Portugal",       "away": "DR Congo",       "venue": "NRG Stadium, Houston",                  "stage": "Group K"},
    {"date": "2026-06-17", "home": "Uzbekistan",     "away": "Colombia",       "venue": "Estadio Azteca, Mexico City",           "stage": "Group K"},
    {"date": "2026-06-23", "home": "Portugal",       "away": "Uzbekistan",     "venue": "NRG Stadium, Houston",                  "stage": "Group K"},
    {"date": "2026-06-23", "home": "Colombia",       "away": "DR Congo",       "venue": "Estadio Akron, Zapopan",                "stage": "Group K"},
    {"date": "2026-06-27", "home": "Colombia",       "away": "Portugal",       "venue": "Hard Rock Stadium, Miami Gardens",      "stage": "Group K"},
    {"date": "2026-06-27", "home": "DR Congo",       "away": "Uzbekistan",     "venue": "Mercedes-Benz Stadium, Atlanta",        "stage": "Group K"},
    # Group L — England, Croatia, Panama, Ghana
    {"date": "2026-06-17", "home": "England",        "away": "Croatia",        "venue": "AT&T Stadium, Arlington",               "stage": "Group L"},
    {"date": "2026-06-17", "home": "Ghana",          "away": "Panama",         "venue": "BMO Field, Toronto",                   "stage": "Group L"},
    {"date": "2026-06-23", "home": "England",        "away": "Ghana",          "venue": "Gillette Stadium, Foxborough",          "stage": "Group L"},
    {"date": "2026-06-23", "home": "Panama",         "away": "Croatia",        "venue": "BMO Field, Toronto",                   "stage": "Group L"},
    {"date": "2026-06-27", "home": "Panama",         "away": "England",        "venue": "MetLife Stadium, East Rutherford",      "stage": "Group L"},
    {"date": "2026-06-27", "home": "Croatia",        "away": "Ghana",          "venue": "Lincoln Financial Field, Philadelphia", "stage": "Group L"},

    # ── Round of 32 (actual bracket per football-data.org, confirmed 2026-06-28) ──
    {"date": "2026-06-28", "home": "South Africa",          "away": "Canada",                    "venue": "SoFi Stadium, Inglewood",               "stage": "Round of 32"},
    {"date": "2026-06-29", "home": "Brazil",                "away": "Japan",                     "venue": "NRG Stadium, Houston",                  "stage": "Round of 32"},
    {"date": "2026-06-29", "home": "Germany",               "away": "Paraguay",                  "venue": "Gillette Stadium, Foxborough",           "stage": "Round of 32"},
    {"date": "2026-06-30", "home": "Netherlands",           "away": "Morocco",                   "venue": "Estadio BBVA, Guadalupe",               "stage": "Round of 32"},
    {"date": "2026-06-30", "home": "Ivory Coast",           "away": "Norway",                    "venue": "AT&T Stadium, Arlington",               "stage": "Round of 32"},
    {"date": "2026-06-30", "home": "France",                "away": "Sweden",                    "venue": "MetLife Stadium, East Rutherford",       "stage": "Round of 32"},
    {"date": "2026-07-01", "home": "Mexico",                "away": "Ecuador",                   "venue": "Estadio Azteca, Mexico City",            "stage": "Round of 32"},
    {"date": "2026-07-01", "home": "England",               "away": "DR Congo",                  "venue": "Mercedes-Benz Stadium, Atlanta",         "stage": "Round of 32"},
    {"date": "2026-07-01", "home": "Belgium",               "away": "Senegal",                   "venue": "Lincoln Financial Field, Philadelphia",  "stage": "Round of 32"},
    {"date": "2026-07-02", "home": "USA",                   "away": "Bosnia and Herzegovina",    "venue": "Levi's Stadium, Santa Clara",            "stage": "Round of 32"},
    {"date": "2026-07-02", "home": "Spain",                 "away": "Austria",                   "venue": "SoFi Stadium, Inglewood",               "stage": "Round of 32"},
    {"date": "2026-07-02", "home": "Portugal",              "away": "Croatia",                   "venue": "SoFi Stadium, Inglewood",               "stage": "Round of 32"},
    {"date": "2026-07-03", "home": "Switzerland",           "away": "Algeria",                   "venue": "BMO Field, Toronto",                    "stage": "Round of 32"},
    {"date": "2026-07-03", "home": "Australia",             "away": "Egypt",                     "venue": "AT&T Stadium, Arlington",               "stage": "Round of 32"},
    {"date": "2026-07-03", "home": "Argentina",             "away": "Cape Verde",                "venue": "Hard Rock Stadium, Miami Gardens",       "stage": "Round of 32"},
    {"date": "2026-07-04", "home": "Colombia",              "away": "Ghana",                     "venue": "BC Place, Vancouver",                   "stage": "Round of 32"},
    # ── Round of 16 (confirmed bracket, 2026-07-03) ──
    {"date": "2026-07-04", "home": "Canada",                "away": "Morocco",                   "venue": "Lincoln Financial Field, Philadelphia",  "stage": "Round of 16"},
    {"date": "2026-07-04", "home": "Paraguay",              "away": "France",                    "venue": "Lincoln Financial Field, Philadelphia",  "stage": "Round of 16"},
    {"date": "2026-07-05", "home": "Brazil",                "away": "Norway",                    "venue": "MetLife Stadium, East Rutherford",        "stage": "Round of 16"},
    {"date": "2026-07-06", "home": "Mexico",                "away": "England",                   "venue": "Estadio Azteca, Mexico City",             "stage": "Round of 16"},
    {"date": "2026-07-06", "home": "Portugal",              "away": "Spain",                     "venue": "AT&T Stadium, Arlington",                "stage": "Round of 16"},
    {"date": "2026-07-07", "home": "USA",                   "away": "Belgium",                   "venue": "Lumen Field, Seattle",                   "stage": "Round of 16"},
    {"date": "2026-07-07", "home": "Argentina",             "away": "Egypt",                     "venue": "Mercedes-Benz Stadium, Atlanta",          "stage": "Round of 16"},
    {"date": "2026-07-07", "home": "Switzerland",           "away": "Colombia",                  "venue": "BC Place, Vancouver",                    "stage": "Round of 16"},
    # ── Quarter-Finals (confirmed bracket, 2026-07-07) ──
    {"date": "2026-07-09", "home": "France",                "away": "Morocco",                   "venue": "AT&T Stadium, Arlington",                "stage": "Quarter-Finals"},
    {"date": "2026-07-10", "home": "Spain",                 "away": "Belgium",                   "venue": "MetLife Stadium, East Rutherford",        "stage": "Quarter-Finals"},
    {"date": "2026-07-11", "home": "Norway",                "away": "England",                   "venue": "Levi's Stadium, Santa Clara",             "stage": "Quarter-Finals"},
    {"date": "2026-07-12", "home": "Argentina",             "away": "Switzerland",               "venue": "Hard Rock Stadium, Miami Gardens",        "stage": "Quarter-Finals"},
    # ── Semi-Finals (full bracket confirmed 2026-07-13) ──
    {"date": "2026-07-15", "home": "France",                "away": "Spain",                     "venue": "MetLife Stadium, East Rutherford",        "stage": "Semi-Finals"},
    {"date": "2026-07-16", "home": "England",               "away": "Argentina",                 "venue": "AT&T Stadium, Arlington",                 "stage": "Semi-Finals"},
    # ── Third Place & Final (confirmed 2026-07-16) ──
    {"date": "2026-07-19", "home": "France",                "away": "England",                   "venue": "Levi's Stadium, Santa Clara",             "stage": "Third Place"},
    {"date": "2026-07-19", "home": "Spain",                 "away": "Argentina",                 "venue": "MetLife Stadium, East Rutherford",        "stage": "Final"},
]


def _match_id(home: str, away: str, match_date: str) -> str:
    def safe(s):
        return s.replace(" ", "_").replace("'", "").replace("/", "").replace("&", "and")
    return f"{safe(home)}_{safe(away)}_{match_date}"


def _load_config() -> dict:
    with open(os.path.join(BASE_DIR, "config.json")) as f:
        return json.load(f)


def _call_sonar(query: str, config: dict) -> tuple[str, float]:
    """Call Perplexity Sonar and return (text, cost_usd)."""
    try:
        import openai
        import os as _os
        hai_key = _os.environ.get("HAI_API_KEY", _os.environ.get("ANTHROPIC_API_KEY", "dummy"))
        client = openai.OpenAI(
            api_key=hai_key,
            base_url=config["litellm_base_url"],
        )
        resp = client.chat.completions.create(
            model=config["sonar_model_id"],
            max_tokens=1024,
            messages=[{"role": "user", "content": query}],
        )
        text = resp.choices[0].message.content or ""
        usage = resp.usage
        in_tok = getattr(usage, "prompt_tokens", 0)
        out_tok = getattr(usage, "completion_tokens", 0)
        sonar_cfg = next((m for m in config["models"] if m["short"] == "sonar"), None)
        cost = 0.0
        if sonar_cfg:
            cost = (
                in_tok / 1_000_000 * sonar_cfg["input_cost_per_million"]
                + out_tok / 1_000_000 * sonar_cfg["output_cost_per_million"]
            )
        return text, cost
    except Exception as e:
        return f"[Sonar unavailable: {e}]", 0.0


def fetch_match_context(fixture: dict, config: dict) -> dict:
    """Fetch enriched match context via two Sonar queries: stats/form + tactics/advanced."""
    home = fixture["home"]
    away = fixture["away"]
    match_date = fixture["date"]
    stage = fixture["stage"]

    # Query 1: stats, form, H2H, odds, injuries, qualification scenario
    query1 = (
        f"2026 FIFA World Cup match preview: {home} vs {away}, {stage}, {match_date}. "
        f"Provide ALL of the following with specific numbers: "
        f"(1) current bookmaker odds for home win, draw, away win as decimal odds; "
        f"(2) {home} last 5 competitive matches: date, opponent, score, xG for/against if available; "
        f"(3) {away} last 5 competitive matches: date, opponent, score, xG for/against if available; "
        f"(4) head-to-head last 5 meetings: date, score, competition, venue; "
        f"(5) confirmed injuries and suspensions for both teams; "
        f"(6) current group standings points table with GD and qualification scenario "
        f"(what each team needs from this match to qualify/advance); "
        f"(7) {home} draw rate in last 20 competitive matches (percentage); "
        f"(8) {away} draw rate in last 20 competitive matches (percentage). "
        f"Only cite verified facts, do not invent scores."
    )

    # Query 2: coach, tactics, player matchups, advanced context
    query2 = (
        f"2026 FIFA World Cup tactical preview: {home} vs {away}, {match_date}. "
        f"Provide: "
        f"(1) {home} head coach name, typical formation (e.g. 4-3-3), and defensive/attacking style — "
        f"are they high-press, low-block, counter-attacking, possession-based? "
        f"Average goals conceded per game this qualifying cycle; "
        f"(2) {away} head coach name, typical formation, and style — same detail; "
        f"(3) key player matchup: name the most important 1v1 battle in this match "
        f"(e.g. their striker vs our CB) and who has the edge; "
        f"(4) set piece threat: which team is more dangerous from corners/free kicks and why; "
        f"(5) fatigue/rotation risk: any players likely to be rested given qualification status; "
        f"(6) historically, does this fixture type (strong vs weak, must-win vs dead rubber) "
        f"tend toward more or fewer goals and draws at the World Cup; "
        f"(7) one sentence prediction: based purely on context, what is the most likely scoreline range."
    )

    text1, cost1 = _call_sonar(query1, config)
    text2, cost2 = _call_sonar(query2, config)

    combined = f"=== STATS, FORM & QUALIFICATION ===\n{text1}\n\n=== TACTICS, COACHES & MATCHUPS ===\n{text2}"
    odds = _parse_odds(text1, home, away)

    return {
        "context": combined,
        "context_cost_usd": cost1 + cost2,
        "odds": odds,
    }


def _parse_odds(text: str, home: str, away: str) -> dict:
    """Try to extract decimal odds from Sonar text. Falls back to neutral."""
    numbers = re.findall(r"\b(\d+\.\d{2})\b", text)
    floats = [float(n) for n in numbers if 1.01 <= float(n) <= 20.0]

    if len(floats) >= 3:
        home_odds, draw_odds, away_odds = floats[0], floats[1], floats[2]
    else:
        home_odds, draw_odds, away_odds = 2.50, 3.20, 2.80

    total_implied = 1 / home_odds + 1 / draw_odds + 1 / away_odds
    return {
        "home_win": round(home_odds, 2),
        "draw": round(draw_odds, 2),
        "away_win": round(away_odds, 2),
        "implied_home": round((1 / home_odds) / total_implied, 4),
        "implied_draw": round((1 / draw_odds) / total_implied, 4),
        "implied_away": round((1 / away_odds) / total_implied, 4),
    }


def fetch_match(fixture: dict, config: dict, force: bool = False) -> Optional[str]:
    """Fetch full match data and save to data/. Returns path or None if skipped."""
    home = fixture["home"]
    away = fixture["away"]
    match_date = fixture["date"]
    mid = _match_id(home, away, match_date)
    out_path = os.path.join(DATA_DIR, f"{mid}.json")

    if os.path.exists(out_path) and not force:
        print(f"  Already fetched: {mid}")
        return out_path

    print(f"  Fetching context for {home} vs {away} ({match_date})...")
    ctx = fetch_match_context(fixture, config)

    record = {
        "match_id": mid,
        "date": match_date,
        "home": home,
        "away": away,
        "venue": fixture["venue"],
        "stage": fixture["stage"],
        "odds": ctx["odds"],
        "context": ctx["context"],
        "context_cost_usd": ctx["context_cost_usd"],
        "fetched_date": date.today().isoformat(),
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)

    print(f"    -> Saved {out_path} (context cost: ${ctx['context_cost_usd']:.4f})")
    time.sleep(config["settings"]["api_call_delay_seconds"])
    return out_path


def get_fixtures_for_date(match_date: str) -> list[dict]:
    return [f for f in FIXTURES if f["date"] == match_date]


def get_all_fixtures() -> list[dict]:
    return FIXTURES


def main():
    config = _load_config()

    filter_date = None
    filter_match = None
    if "--date" in sys.argv:
        idx = sys.argv.index("--date")
        filter_date = sys.argv[idx + 1]
    if "--match" in sys.argv:
        idx = sys.argv.index("--match")
        filter_match = sys.argv[idx + 1]
    force = "--force" in sys.argv

    if filter_match:
        fixtures = [f for f in FIXTURES if _match_id(f["home"], f["away"], f["date"]) == filter_match]
    elif filter_date:
        fixtures = get_fixtures_for_date(filter_date)
    else:
        today = date.today().isoformat()
        fixtures = [f for f in FIXTURES if f["date"] >= today]

    print(f"Fetching {len(fixtures)} fixture(s)...")
    fetched = 0
    for fix in fixtures:
        path = fetch_match(fix, config, force=force)
        if path:
            fetched += 1

    print(f"\nDone: {fetched}/{len(fixtures)} fetched.")


if __name__ == "__main__":
    main()
