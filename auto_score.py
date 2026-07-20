"""
auto_score.py — Automated score fetcher, scorer, forecaster, and Pages deployer.

Fetches live World Cup results from football-data.org (the same API the Firebase
Cloud Function uses), scores any not-yet-scored finished matches, optionally runs
LLM forecasts for knockout matches, then rebuilds and pushes the GitHub Pages dashboard.

Usage:
    python auto_score.py              # score new results + push to Pages
    python auto_score.py --dry-run    # score only, skip push
    python auto_score.py --force      # re-score already-scored matches
    python auto_score.py --forecast   # also run forecasts for unforecasted upcoming matches

Schedule: run this every 30 minutes while the tournament is active (Jun 11 – Jul 19 2026).
The Windows Task Scheduler wrapper (auto_score_runner.vbs) calls this silently.
"""

import json
import logging
import os
import subprocess
import sys
from datetime import date, datetime, timezone

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(os.path.dirname(os.path.abspath(__file__)), "auto_score.log"), encoding="utf-8"),
    ]
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
DATA_DIR      = os.path.join(BASE_DIR, "data")
FORECASTS_DIR = os.path.join(BASE_DIR, "results", "forecasts")
SCORED_DIR    = os.path.join(BASE_DIR, "results", "scored")
os.makedirs(SCORED_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# football-data.org API
# ---------------------------------------------------------------------------
FOOTBALL_DATA_BASE = "https://api.football-data.org/v4"
COMPETITION        = "WC"

# API key — set FOOTBALL_DATA_API_KEY env var, or place in config.json as "football_data_api_key"
def _get_football_data_key() -> str:
    key = os.environ.get("FOOTBALL_DATA_API_KEY", "")
    if not key:
        cfg_path = os.path.join(BASE_DIR, "config.json")
        with open(cfg_path) as f:
            cfg = json.load(f)
        key = cfg.get("football_data_api_key", "")
    return key


# ---------------------------------------------------------------------------
# Team name normalisation: football-data.org → our fixture names
# ---------------------------------------------------------------------------
TEAM_NORM = {
    "Korea Republic":                    "South Korea",
    "IR Iran":                           "Iran",
    "Türkiye":                           "Turkey",
    "Côte d'Ivoire":                     "Ivory Coast",
    "Cote d'Ivoire":                     "Ivory Coast",
    "Congo DR":                          "DR Congo",
    "Democratic Republic of the Congo":  "DR Congo",
    "Bosnia and Herzegovina":            "Bosnia & Herzegovina",
    "Bosnia-Herzegovina":               "Bosnia & Herzegovina",
    "Cabo Verde":                        "Cape Verde",
    "Cape Verde Islands":               "Cape Verde",
    "Curaçao":                           "Curacao",
    "United States":                     "USA",
    "Czechia":                           "Czech Republic",
}

def _norm(name: str) -> str:
    return TEAM_NORM.get(name, name)

def _safe(s: str) -> str:
    return s.replace(" ", "_").replace("'", "").replace("/", "").replace("&", "and")

def _match_id(home: str, away: str, match_date: str) -> str:
    return f"{_safe(home)}_{_safe(away)}_{match_date}"


# ---------------------------------------------------------------------------
# Fetch finished matches from football-data.org
# ---------------------------------------------------------------------------
def fetch_finished_matches(api_key: str) -> list[dict]:
    """Return list of finished WC matches from football-data.org."""
    url = f"{FOOTBALL_DATA_BASE}/competitions/{COMPETITION}/matches"
    try:
        resp = requests.get(url, headers={"X-Auth-Token": api_key}, timeout=20)
        resp.raise_for_status()
    except Exception as e:
        logger.error("football-data.org API error: %s", e)
        return []

    matches = resp.json().get("matches", [])
    logger.info("football-data.org: %d total matches fetched", len(matches))

    finished = []
    for m in matches:
        if m.get("status") != "FINISHED":
            continue
        score = m.get("score", {})
        ft    = score.get("fullTime", {})
        home_g = ft.get("home")
        away_g = ft.get("away")
        if home_g is None or away_g is None:
            continue

        utc_date  = m.get("utcDate", "")
        match_date = utc_date[:10] if utc_date else ""
        home_name  = _norm(m.get("homeTeam", {}).get("name", ""))
        away_name  = _norm(m.get("awayTeam", {}).get("name", ""))

        # For knockout matches use 90-minute score only (regularTime when available)
        duration = score.get("duration", "REGULAR")
        if duration in ("EXTRA_TIME", "PENALTY_SHOOTOUT"):
            rt = score.get("regularTime", {})
            if rt.get("home") is not None:
                home_g = rt["home"]
                away_g = rt["away"]

        penalty_winner = None
        if duration == "PENALTY_SHOOTOUT":
            pen = score.get("penalties", {})
            if (pen.get("home") or 0) > (pen.get("away") or 0):
                penalty_winner = home_name
            elif (pen.get("away") or 0) > (pen.get("home") or 0):
                penalty_winner = away_name

        finished.append({
            "home":            home_name,
            "away":            away_name,
            "match_date":      match_date,
            "home_goals":      int(home_g),
            "away_goals":      int(away_g),
            "stage":           m.get("stage", ""),
            "penalty_winner":  penalty_winner,
        })

    logger.info("Finished matches: %d", len(finished))
    return finished


# ---------------------------------------------------------------------------
# Fixture index for match-id lookup
# ---------------------------------------------------------------------------
def _fixture_lookup() -> dict[str, dict]:
    from fixtures import FIXTURES
    return {_match_id(f["home"], f["away"], f["date"]): f for f in FIXTURES}


# ---------------------------------------------------------------------------
# Already-scored match IDs
# ---------------------------------------------------------------------------
def _already_scored_ids() -> set[str]:
    scored = set()
    if not os.path.exists(SCORED_DIR):
        return scored
    for fname in os.listdir(SCORED_DIR):
        if fname.endswith(".json"):
            parts = fname.rsplit("_", 1)
            if len(parts) == 2:
                scored.add(parts[0])
    return scored


# ---------------------------------------------------------------------------
# Core: score newly finished matches
# ---------------------------------------------------------------------------
def fetch_and_score(api_key: str, force: bool = False) -> list[dict]:
    finished = fetch_finished_matches(api_key)
    if not finished:
        return []

    fixture_index  = _fixture_lookup()
    already_scored = _already_scored_ids()

    import score as score_module
    newly_scored = []

    for m in finished:
        mid = _match_id(m["home"], m["away"], m["match_date"])

        # Try swapped home/away and adjacent dates if direct lookup fails.
        # Late kick-offs (e.g. 02:00 UTC) may have a UTC date one day ahead of the local fixture date.
        if mid not in fixture_index:
            from datetime import date, timedelta
            match_date_obj = date.fromisoformat(m["match_date"])
            candidates = [
                _match_id(m["away"], m["home"], m["match_date"]),
                _match_id(m["home"], m["away"], (match_date_obj - timedelta(days=1)).isoformat()),
                _match_id(m["away"], m["home"], (match_date_obj - timedelta(days=1)).isoformat()),
            ]
            found = next((c for c in candidates if c in fixture_index), None)
            if found:
                mid = found
            else:
                logger.debug("No fixture match for %s vs %s on %s", m["home"], m["away"], m["match_date"])
                continue

        if mid in already_scored and not force:
            continue

        logger.info("Scoring %s -> %d-%d", mid, m["home_goals"], m["away_goals"])
        scored = score_module.score_match(mid, m["home_goals"], m["away_goals"])
        if scored:
            newly_scored.extend(scored)
            logger.info("  Scored %d forecasts -- top: %s",
                        len(scored),
                        ", ".join(f"{s['model_short']} {s['predicted_home']}-{s['predicted_away']}->{s['points']}pts"
                                  for s in sorted(scored, key=lambda x: -(x["points"] or 0))[:3]))
        else:
            logger.warning("  No forecasts to score for %s (run pre-match first)", mid)

    scored_matches = len({s["match_id"] for s in newly_scored})
    logger.info("Newly scored: %d forecasts across %d matches", len(newly_scored), scored_matches)
    return newly_scored


# ---------------------------------------------------------------------------
# Knockout round forecasting
# ---------------------------------------------------------------------------
def run_knockout_forecasts():
    """
    Run LLM forecasts for any upcoming match in data/ that has no forecasts yet.
    Covers knockout rounds once their fixture files are created by fixtures.py.
    """
    import forecast as forecast_module

    with open(os.path.join(BASE_DIR, "config.json")) as f:
        config = json.load(f)

    today = date.today().isoformat()
    missing = []

    for fname in sorted(os.listdir(DATA_DIR)):
        if not fname.endswith(".json"):
            continue
        mid = fname[:-5]
        # Extract date from match_id suffix
        parts = mid.rsplit("_", 1)
        match_date = parts[-1] if len(parts) == 2 and len(parts[-1]) == 10 else ""
        if match_date and match_date < today:
            continue

        has_forecast = any(
            f.startswith(mid + "_") and not f.endswith("_CONSENSUS.json")
            for f in os.listdir(FORECASTS_DIR)
        )
        if not has_forecast:
            with open(os.path.join(DATA_DIR, fname), encoding="utf-8") as f:
                missing.append(json.load(f))

    if not missing:
        logger.info("No unforecasted upcoming matches.")
        return

    logger.info("Forecasting %d unforecasted match(es)...", len(missing))
    results = forecast_module.forecast_matches(missing, config)
    n_ok = sum(1 for r in results if not r.get("error") and not r.get("skipped"))
    logger.info("Forecast complete: %d new forecasts", n_ok)


# ---------------------------------------------------------------------------
# Push to GitHub Pages
# ---------------------------------------------------------------------------
def push_to_pages():
    logger.info("Rebuilding and pushing to GitHub Pages...")
    result = subprocess.run(
        [sys.executable, os.path.join(BASE_DIR, "push_to_pages.py")],
        capture_output=True, text=True, cwd=BASE_DIR
    )
    for line in result.stdout.strip().splitlines():
        logger.info("  pages: %s", line)
    for line in result.stderr.strip().splitlines():
        logger.warning("  pages err: %s", line)
    if result.returncode != 0:
        logger.error("push_to_pages.py failed (rc=%d)", result.returncode)
    else:
        logger.info("Pages deployed: https://pages.github.tools.sap/I846720/WCFCST/")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    dry_run     = "--dry-run"  in sys.argv
    force       = "--force"    in sys.argv
    do_forecast = "--forecast" in sys.argv

    logger.info("=== auto_score.py started (%s) ===",
                datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))

    api_key = _get_football_data_key()
    if not api_key:
        logger.error("No FOOTBALL_DATA_API_KEY found. Set env var or add to config.json.")
        sys.exit(1)

    # 1. Score newly finished matches
    newly_scored = fetch_and_score(api_key, force=force)

    # 2. Run forecasts for knockout matches not yet forecasted
    if do_forecast:
        run_knockout_forecasts()

    # 3. Push to Pages (even if nothing new — keeps the site fresh)
    if dry_run:
        logger.info("--dry-run: skipping push to Pages.")
    else:
        push_to_pages()

    logger.info("=== auto_score.py done ===")


if __name__ == "__main__":
    main()
