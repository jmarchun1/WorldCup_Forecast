"""
fetch_kalshi_odds.py — Pull live Kalshi odds for all upcoming WC matches and patch CONSENSUS files.

Ticker format: KXWCGAME-26JUN25TURUSA  (KXWCGAME-YYMMMDDteam1team2)

Usage:
    python fetch_kalshi_odds.py              # fetch all upcoming matches
    python fetch_kalshi_odds.py --show       # print table, don't patch
    python fetch_kalshi_odds.py --date 2026-06-26  # specific date only

Auth: Kalshi uses RSA private key signing.
  config.json: "kalshi_api_key_id": "<key-id>"
  kalshi_private_key.pem: RSA private key file in same directory
Market data is publicly accessible without auth; auth enables higher rate limits.
"""

import base64
import json
import os
import sys
import time
import urllib.request
from datetime import date, datetime
from typing import Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FORECASTS_DIR = os.path.join(BASE_DIR, "results", "forecasts")
KALSHI_BASE = "https://api.elections.kalshi.com/trade-api/v2"
KEY_FILE = os.path.join(BASE_DIR, "kalshi_private_key.pem")

# Map our team names -> Kalshi 3-letter codes used in tickers
TEAM_CODES = {
    "Mexico":              "MEX",
    "South Africa":        "RSA",
    "South Korea":         "KOR",
    "Czech Republic":      "CZE",
    "Canada":              "CAN",
    "Switzerland":         "SUI",
    "Qatar":               "QAT",
    "Bosnia & Herzegovina":"BIH",
    "Brazil":              "BRA",
    "Morocco":             "MAR",
    "Scotland":            "SCO",
    "Haiti":               "HAI",
    "USA":                 "USA",
    "Paraguay":            "PAR",
    "Turkey":              "TUR",
    "Australia":           "AUS",
    "Germany":             "GER",
    "Ecuador":             "ECU",
    "Ivory Coast":         "CIV",
    "Curacao":             "CUW",
    "Netherlands":         "NED",
    "Japan":               "JPN",
    "Tunisia":             "TUN",
    "Sweden":              "SWE",
    "Belgium":             "BEL",
    "Iran":                "IRN",
    "Egypt":               "EGY",
    "New Zealand":         "NZL",
    "Spain":               "ESP",
    "Saudi Arabia":        "KSA",
    "Uruguay":             "URU",
    "France":              "FRA",
    "Senegal":             "SEN",
    "Norway":              "NOR",
    "Iraq":                "IRQ",
    "Argentina":           "ARG",
    "Austria":             "AUT",
    "Algeria":             "ALG",
    "Jordan":              "JOR",
    "Portugal":            "POR",
    "Colombia":            "COL",
    "Uzbekistan":          "UZB",
    "DR Congo":            "COD",
    "England":             "ENG",
    "Croatia":             "CRO",
    "Panama":              "PAN",
    "Ghana":               "GHA",
    "Cape Verde":          "CPV",
}


def _build_auth_headers(method: str, path: str, api_key_id: str) -> dict:
    """Build Kalshi RSA-signed auth headers."""
    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding
    except ImportError:
        print("  [auth] cryptography package not installed — falling back to unauthenticated")
        return {}

    try:
        with open(KEY_FILE, "rb") as f:
            private_key = serialization.load_pem_private_key(f.read(), password=None)
    except Exception as e:
        print(f"  [auth] Could not load private key: {e}")
        return {}

    ts_ms = str(int(time.time() * 1000))
    msg = ts_ms + method.upper() + path
    signature = private_key.sign(msg.encode("utf-8"), padding.PKCS1v15(), hashes.SHA256())
    sig_b64 = base64.b64encode(signature).decode("utf-8")

    return {
        "KALSHI-ACCESS-KEY":       api_key_id,
        "KALSHI-ACCESS-TIMESTAMP": ts_ms,
        "KALSHI-ACCESS-SIGNATURE": sig_b64,
    }


def _safe(s: str) -> str:
    return s.replace(" ", "_").replace("'", "").replace("/", "").replace("&", "and")


def _match_id(home: str, away: str, match_date: str) -> str:
    return f"{_safe(home)}_{_safe(away)}_{match_date}"


def _kalshi_date(match_date: str) -> str:
    """'2026-06-25' -> '26JUN25'"""
    d = datetime.strptime(match_date, "%Y-%m-%d")
    return d.strftime("%y%b%d").upper()


def _kalshi_ticker(home: str, away: str, match_date: str) -> Optional[str]:
    h = TEAM_CODES.get(home)
    a = TEAM_CODES.get(away)
    if not h or not a:
        return None
    return f"KXWCGAME-{_kalshi_date(match_date)}{h}{a}"


def _fetch_json(url: str, api_key_id: Optional[str] = None) -> Optional[dict]:
    headers = {"Accept": "application/json"}
    if api_key_id and os.path.exists(KEY_FILE):
        # Extract path portion for signing
        from urllib.parse import urlparse
        parsed = urlparse(url)
        path = parsed.path
        auth_headers = _build_auth_headers("GET", path, api_key_id)
        headers.update(auth_headers)
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.load(r)
    except Exception as e:
        return None


def fetch_odds_for_match(home: str, away: str, match_date: str, api_key_id: Optional[str] = None) -> Optional[dict]:
    """Returns {"home": decimal_odds, "draw": decimal_odds, "away": decimal_odds} or None."""
    ticker = _kalshi_ticker(home, away, match_date)
    if not ticker:
        print(f"  No ticker mapping for {home} or {away}")
        return None

    data = _fetch_json(f"{KALSHI_BASE}/events/{ticker}", api_key_id)
    if not data or "markets" not in data:
        # Try swapped order (ticker may use away-home order)
        alt = f"KXWCGAME-{_kalshi_date(match_date)}{TEAM_CODES.get(away,'')}{TEAM_CODES.get(home,'')}"
        data = _fetch_json(f"{KALSHI_BASE}/events/{alt}", api_key_id)
        if not data or "markets" not in data:
            print(f"  No Kalshi event found: {ticker} or {alt}")
            return None

    markets = data["markets"]

    # Parse markets: yes_bid_dollars is the implied probability (0-1)
    odds = {}
    for m in markets:
        sub = m.get("no_sub_title", "").strip().lower()  # e.g. "Turkiye", "USA", "Tie"
        yes_bid = float(m.get("yes_bid_dollars", 0) or 0)
        no_bid = float(m.get("no_bid_dollars", 0) or 0)
        # Midpoint of bid/ask for best estimate
        mid = (yes_bid + (1 - no_bid)) / 2 if no_bid else yes_bid
        if mid <= 0:
            mid = yes_bid
        if mid <= 0:
            continue
        decimal = round(1 / mid, 3)

        # Classify outcome
        home_lower = home.lower()
        away_lower = away.lower()
        # Aliases for teams Kalshi names differently
        ALIASES = {
            "turkey": ["turkiye", "türkiye"],
            "ivory coast": ["cote d'ivoire", "côte d'ivoire"],
            "south korea": ["korea"],
            "usa": ["united states"],
        }
        def _matches_team(team_name: str, subtitle: str) -> bool:
            words = team_name.split()
            if any(w in subtitle for w in words):
                return True
            for alias in ALIASES.get(team_name, []):
                if alias in subtitle:
                    return True
            return False

        if "tie" in sub or "draw" in sub:
            odds["draw"] = decimal
        elif _matches_team(home_lower, sub):
            odds["home"] = decimal
        elif _matches_team(away_lower, sub):
            odds["away"] = decimal
        else:
            rules = m.get("rules_primary", "").lower()
            if "tie" in rules:
                odds["draw"] = decimal
            elif _matches_team(home_lower, rules):
                odds["home"] = decimal
            elif _matches_team(away_lower, rules):
                odds["away"] = decimal

    if len(odds) < 3:
        print(f"  Incomplete odds for {ticker}: {odds}")
        return None

    return odds


def patch_consensus(match_id: str, odds: dict) -> None:
    """Write kalshi_odds + recompute EV on the CONSENSUS file."""
    path = os.path.join(FORECASTS_DIR, f"{match_id}_CONSENSUS.json")
    if not os.path.exists(path):
        return

    with open(path, encoding="utf-8") as f:
        cons = json.load(f)

    hp = cons.get("avg_home_win_prob", 0)
    dp = cons.get("avg_draw_prob", 0)
    ap = cons.get("avg_away_win_prob", 0)

    def ev(p, o): return round(p * (o - 1) - (1 - p), 4)

    ev_h = ev(hp, odds["home"])
    ev_d = ev(dp, odds["draw"])
    ev_a = ev(ap, odds["away"])

    value_bets = []
    threshold = 0.05
    if ev_h > threshold:
        value_bets.append({"outcome": "home", "ev": ev_h, "odds": odds["home"], "our_prob": round(hp, 4)})
    if ev_d > threshold:
        value_bets.append({"outcome": "draw", "ev": ev_d, "odds": odds["draw"], "our_prob": round(dp, 4)})
    if ev_a > threshold:
        value_bets.append({"outcome": "away", "ev": ev_a, "odds": odds["away"], "our_prob": round(ap, 4)})
    value_bets.sort(key=lambda x: -x["ev"])

    cons["kalshi_odds"] = {**odds, "fetched_date": date.today().isoformat()}
    cons["kalshi_ev_home_win"] = ev_h
    cons["kalshi_ev_draw"] = ev_d
    cons["kalshi_ev_away_win"] = ev_a
    cons["kalshi_value_bets"] = value_bets

    # Write implied_* fields so dashboard + EV analysis see real prices
    def _implied(decimal_odds): return round(1 / decimal_odds, 4) if decimal_odds else 0
    cons["implied_home"] = _implied(odds["home"])
    cons["implied_draw"] = _implied(odds["draw"])
    cons["implied_away"] = _implied(odds["away"])

    with open(path, "w", encoding="utf-8") as f:
        json.dump(cons, f, indent=2, ensure_ascii=False)


def main():
    from fixtures import FIXTURES

    config_path = os.path.join(BASE_DIR, "config.json")
    with open(config_path, encoding="utf-8") as f:
        config = json.load(f)
    api_key_id = config.get("kalshi_api_key_id")

    show_only = "--show" in sys.argv
    filter_date = None
    if "--date" in sys.argv:
        filter_date = sys.argv[sys.argv.index("--date") + 1]

    today = date.today().isoformat()
    fixtures = [f for f in FIXTURES if f["date"] >= today]
    if filter_date:
        fixtures = [f for f in fixtures if f["date"] == filter_date]

    print(f"Fetching Kalshi odds for {len(fixtures)} matches...")
    print(f"{'Match':<35} {'Home':>6} {'Draw':>6} {'Away':>6}  {'EV bets'}")
    print("-" * 75)

    all_ev = []
    for fix in fixtures:
        mid = _match_id(fix["home"], fix["away"], fix["date"])
        odds = fetch_odds_for_match(fix["home"], fix["away"], fix["date"], api_key_id)
        if not odds:
            continue

        if not show_only:
            patch_consensus(mid, odds)

        cons_path = os.path.join(FORECASTS_DIR, f"{mid}_CONSENSUS.json")
        ev_str = ""
        if os.path.exists(cons_path):
            with open(cons_path, encoding="utf-8") as f:
                cons = json.load(f)
            vb = cons.get("kalshi_value_bets", [])
            if vb:
                ev_str = " | ".join(f"{b['outcome']} EV={b['ev']:+.2f}" for b in vb)
                all_ev.extend(vb)

        label = f"{fix['home']} vs {fix['away']}"
        print(f"  {label:<33} {odds['home']:>6.2f} {odds['draw']:>6.2f} {odds['away']:>6.2f}  {ev_str}")
        time.sleep(0.3)

    if all_ev:
        all_ev.sort(key=lambda x: -x["ev"])
        print(f"\nTop EV bets (consensus):")
        for b in all_ev[:10]:
            print(f"  {b.get('match',''):<33} {b['outcome']:<6} EV={b['ev']:+.3f} odds={b['odds']:.2f} our_p={b['our_prob']:.1%}")


if __name__ == "__main__":
    main()
