"""
run_match_day.py — Orchestrator for the 2026 FIFA World Cup Forecasting App.

Pre-match mode (run before a match day):
    python run_match_day.py --date 2026-06-11

    Steps:
      1. Fetch fixture context + odds from Perplexity Sonar for that date's matches
      2. Run all 12 models in parallel for each match
      3. Fetch live Kalshi odds and patch consensus files with real implied probabilities
      4. Compute consensus + EV signals
      5. Generate/update report

Post-match mode (run after results are in):
    python run_match_day.py --score --date 2026-06-11
    python run_match_day.py --score --date 2026-06-11 --results "Mexico_Poland_2026-06-11 2-1,Saudi_Arabia_Argentina_2026-06-11 0-3"

    Steps:
      1. Parse actual scores
      2. Score all model forecasts for that date's matches
      3. Update report

Full pipeline (fetch + forecast + open report):
    python run_match_day.py --date 2026-06-11 --open

Force re-fetch:
    python run_match_day.py --date 2026-06-11 --force
"""

import json
import logging
import os
import subprocess
import sys
from datetime import date

import fixtures as fix_module
import forecast as forecast_module
import score as score_module
import report as report_module
import fetch_kalshi_odds as kalshi_module

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")


def _load_config() -> dict:
    with open(os.path.join(BASE_DIR, "config.json")) as f:
        return json.load(f)


def _open_report():
    report_path = os.path.join(BASE_DIR, "report", "index.html")
    if os.path.exists(report_path):
        try:
            if sys.platform == "win32":
                os.startfile(report_path)
            elif sys.platform == "darwin":
                subprocess.run(["open", report_path])
            else:
                subprocess.run(["xdg-open", report_path])
            print(f"Opened: {report_path}")
        except Exception as e:
            print(f"Report at: {report_path} (could not auto-open: {e})")
    else:
        print(f"Report not found at {report_path}")


def run_pre_match(match_date: str, config: dict, force: bool = False):
    """Fetch context, run 12 models, compute consensus, generate report."""
    print(f"\n=== Pre-match pipeline for {match_date} ===")

    # Step 1: fetch fixture context for this date
    today_fixtures = fix_module.get_fixtures_for_date(match_date)
    if not today_fixtures:
        print(f"No fixtures found for {match_date}.")
        return

    print(f"Fetching context for {len(today_fixtures)} fixture(s)...")
    fetched_paths = []
    for fixture in today_fixtures:
        path = fix_module.fetch_match(fixture, config, force=force)
        if path:
            fetched_paths.append(path)

    if not fetched_paths:
        print("No match data files available. Exiting.")
        return

    # Step 2: load match data and run forecasts
    match_data_list = []
    for path in fetched_paths:
        with open(path, encoding="utf-8") as f:
            match_data_list.append(json.load(f))

    print(f"\nForecasting {len(match_data_list)} match(es) with 12 models each...")
    results = forecast_module.forecast_matches(match_data_list, config, force=force)

    n_ok = sum(1 for r in results if not r.get("error") and not r.get("skipped"))
    n_skip = sum(1 for r in results if r.get("skipped"))
    n_err = sum(1 for r in results if r.get("error") and not r.get("skipped"))
    print(f"Forecast complete: {n_ok} new, {n_skip} skipped, {n_err} errors")

    # Step 3: fetch live Kalshi odds and patch consensus files
    print("\nFetching Kalshi odds...")
    api_key_id = config.get("kalshi_api_key_id")
    kalshi_patched = 0
    for fixture in today_fixtures:
        mid = kalshi_module._match_id(fixture["home"], fixture["away"], fixture["date"])
        odds = kalshi_module.fetch_odds_for_match(fixture["home"], fixture["away"], fixture["date"], api_key_id)
        if odds:
            kalshi_module.patch_consensus(mid, odds)
            kalshi_patched += 1
            print(f"  {fixture['home']} vs {fixture['away']}: H={1/odds['home']:.0%} D={1/odds['draw']:.0%} A={1/odds['away']:.0%}")
        else:
            print(f"  {fixture['home']} vs {fixture['away']}: no Kalshi odds available")
    print(f"Kalshi odds patched: {kalshi_patched}/{len(today_fixtures)}")

    # Step 4: generate report
    print("\nGenerating report...")
    out = report_module.main()
    print(f"Report: {out}")


def run_post_match(match_date: str, results_str: str = None):
    """Score completed matches, update report."""
    print(f"\n=== Post-match scoring for {match_date} ===")

    # Find match IDs for this date
    match_ids = []
    for fname in os.listdir(DATA_DIR):
        if fname.endswith(".json") and match_date in fname:
            match_ids.append(fname.replace(".json", ""))

    if not match_ids:
        print(f"No match data files found for {match_date}")
        return

    # Parse results
    result_map = {}
    if results_str:
        for part in results_str.split(","):
            part = part.strip()
            # "Mexico_Poland_2026-06-11 2-1" or "Mexico_Poland 2-1"
            tokens = part.rsplit(" ", 1)
            if len(tokens) == 2:
                id_fragment = tokens[0].strip().replace(" ", "_")
                score_str = tokens[1].strip()
                matched = None
                for mid in match_ids:
                    if id_fragment in mid or mid.startswith(id_fragment):
                        matched = mid
                        break
                if matched:
                    result_map[matched] = score_str
                else:
                    # Assign to next unscored match
                    for mid in match_ids:
                        if mid not in result_map:
                            result_map[mid] = score_str
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
            res = input(f"Result for {mid} (e.g. 2-1, blank to skip): ").strip()
            if not res:
                continue
        try:
            ah, aa = score_module._parse_result_string(res)
        except ValueError as e:
            print(f"  Skipping {mid}: {e}")
            continue
        scored = score_module.score_match(mid, ah, aa)
        total_scored += len(scored)
        print(f"  {mid}: {ah}-{aa} → scored {len(scored)} model forecasts")
        for s in sorted(scored, key=lambda x: -x["points"])[:3]:
            print(f"    {s['model_short']:15s} predicted {s['predicted_home']}-{s['predicted_away']} → {s['points']}pts ({s['score_breakdown']})")

    print(f"\nTotal scored: {total_scored}")

    # Regenerate report
    print("\nUpdating report...")
    out = report_module.main()
    print(f"Report: {out}")


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    config = _load_config()

    match_date = None
    is_score = "--score" in sys.argv
    force = "--force" in sys.argv
    open_report = "--open" in sys.argv
    results_str = None

    if "--date" in sys.argv:
        idx = sys.argv.index("--date")
        match_date = sys.argv[idx + 1]
    if "--results" in sys.argv:
        idx = sys.argv.index("--results")
        results_str = sys.argv[idx + 1]

    if not match_date:
        match_date = date.today().isoformat()
        print(f"No --date provided, using today: {match_date}")

    if is_score:
        run_post_match(match_date, results_str)
    else:
        run_pre_match(match_date, config, force=force)

    if open_report:
        _open_report()


if __name__ == "__main__":
    main()
