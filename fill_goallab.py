"""
fill_goallab.py — Fill all 72 World Cup match predictions in GoalLab.

For each match row, sets:
  - Home score (consensus prediction)
  - Away score (consensus prediction)
  - Tier 3: Agentic (2.5x)
  - Proof URL: https://pages.github.tools.sap/I846720/WCFCST/

The page shows matches one match-day at a time via a dropdown.
We iterate through all match days (1-N) and fill each.

Usage:
    python fill_goallab.py              # fill all matches
    python fill_goallab.py --dry-run    # print predictions only
    python fill_goallab.py --inspect    # inspect DOM, no fill
"""

import asyncio
import json
import os
import sys
import time
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FORECASTS_DIR = os.path.join(BASE_DIR, "results", "forecasts")
ARCHIVE_DIR   = os.path.join(BASE_DIR, "results", "forecasts", "archive")

GOALLAB_OUTER_URL = (
    "https://sapit-home-prod-004.launchpad.cfapps.eu10.hana.ondemand.com/"
    "site#GoalLab-Tipping?mobilestart.tile.hidden=true"
    "&sap-ui-app-id-hint=304119ff-b2b0-403e-8d0a-fa638a0bed6d"
    "&/tournamentDetail/WC2026/?tab=matches"
)

GOALLAB_APP_URL = (
    "https://sapit-hr-prod-bear.launchpad.cfapps.eu10.hana.ondemand.com/"
    "ad170241-3021-4e9d-9d8a-e7b0609aeff4.GoalLab.comsaptipit/ui5appwz.html"
    "?sap-ui-app-id=ABC&sap-locale=en&sap-shell=FLP&sap-theme=sap_horizon"
    "#GoalLab-Tipping?mobilestart.tile.hidden=true"
    "&sap-ui-app-id-hint=304119ff-b2b0-403e-8d0a-fa638a0bed6d"
    "&/tournamentDetail/WC2026/?tab=matches"
)

PROFILE_DIR = os.path.join(
    os.path.expanduser("~"),
    "AppData", "Local", "Microsoft", "Edge", "User Data", "Playwright-GoalLab2"
)

PROOF_URL = "https://pages.github.tools.sap/I846720/WCFCST/"

SCREENSHOTS_DIR = os.path.join(BASE_DIR, "screenshots")
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

TEAM_ALIASES = {
    "MEX": "Mexico", "RSA": "South Africa", "KOR": "South Korea",
    "CZE": "Czech Republic", "CAN": "Canada", "BIH": "Bosnia & Herzegovina",
    "USA": "USA", "PAR": "Paraguay", "QAT": "Qatar", "SUI": "Switzerland",
    "BRA": "Brazil", "MAR": "Morocco", "HAI": "Haiti", "SCO": "Scotland",
    "AUS": "Australia", "TUR": "Turkey", "GER": "Germany", "CUW": "Curacao",
    "CIV": "Ivory Coast", "ECU": "Ecuador", "NED": "Netherlands", "JPN": "Japan",
    "SWE": "Sweden", "TUN": "Tunisia", "BEL": "Belgium", "EGY": "Egypt",
    "IRN": "Iran", "NZL": "New Zealand", "ESP": "Spain", "CPV": "Cape Verde",
    "KSA": "Saudi Arabia", "URU": "Uruguay", "FRA": "France", "SEN": "Senegal",
    "IRQ": "Iraq", "NOR": "Norway", "ARG": "Argentina", "AUT": "Austria",
    "ALG": "Algeria", "JOR": "Jordan", "POR": "Portugal", "COL": "Colombia",
    "UZB": "Uzbekistan", "COD": "DR Congo", "ENG": "England", "CRO": "Croatia",
    "PAN": "Panama", "GHA": "Ghana", "URY": "Uruguay",
    "Bosnia-Herzegovina": "Bosnia & Herzegovina",
    "Bosnia & Herzegovina": "Bosnia & Herzegovina",
    "Bosnia and Herzegovina": "Bosnia & Herzegovina",
    "Ivory Coast": "Ivory Coast",
    "DR Congo": "DR Congo", "Congo DR": "DR Congo", "DRC": "DR Congo",
    "Cabo Verde": "Cape Verde", "Korea Republic": "South Korea",
}


def normalize_team(name):
    return TEAM_ALIASES.get(name.strip(), name.strip())


def load_consensus_predictions(forecasts_dir=None):
    if forecasts_dir is None:
        forecasts_dir = FORECASTS_DIR
    predictions = {}
    for fname in sorted(os.listdir(forecasts_dir)):
        if not fname.endswith("_CONSENSUS.json"):
            continue
        fpath = os.path.join(forecasts_dir, fname)
        try:
            with open(fpath, encoding="utf-8") as f:
                rec = json.load(f)
        except Exception:
            continue
        home = rec.get("home", "")
        away = rec.get("away", "")
        predictions[(home, away)] = {
            "home_goals": int(rec.get("consensus_home_goals", 1)),
            "away_goals": int(rec.get("consensus_away_goals", 0)),
            "match_date": rec.get("match_date", ""),
        }
    return predictions


async def set_number_input(el, value):
    await el.click()
    await asyncio.sleep(0.05)
    await el.evaluate("e => { e.value = ''; e.dispatchEvent(new Event('input')); }")
    await el.fill(str(value))
    await el.press("Tab")
    await asyncio.sleep(0.15)


async def set_text_input(el, value):
    current = await el.get_attribute("value") or ""
    if current.strip() == value.strip():
        return
    await el.click()
    await asyncio.sleep(0.05)
    await el.evaluate("e => { e.value = ''; e.dispatchEvent(new Event('input')); }")
    await el.fill(value)
    await el.press("Tab")
    await asyncio.sleep(0.15)


async def set_tier3_for_row(page, row_idx):
    """Set the tier dropdown for a given match row to Tier 3: Agentic (2.5x)."""
    number_inputs = await page.query_selector_all('input[type="number"]')
    h_idx = row_idx * 2
    if h_idx >= len(number_inputs):
        return False

    home_input = number_inputs[h_idx]
    await home_input.scroll_into_view_if_needed()
    await asyncio.sleep(0.3)

    # Find the tier combobox within the same row container
    combo = await home_input.evaluate_handle("""el => {
        let node = el.parentElement;
        for (let d = 0; d < 15 && node; d++) {
            const combo = node.querySelector('[role="combobox"]');
            if (combo) return combo;
            node = node.parentElement;
        }
        return null;
    }""")

    if combo is None:
        print(f"    tier: no combobox found for row {row_idx}")
        return False

    combo_el = combo.as_element()
    if combo_el is None:
        print(f"    tier: combobox is null element for row {row_idx}")
        return False

    try:
        current_text = (await combo_el.inner_text()).strip()
    except Exception:
        current_text = ""

    if "Tier 3" in current_text or "Agentic" in current_text:
        return True  # already set

    await combo_el.scroll_into_view_if_needed()
    await asyncio.sleep(0.2)
    try:
        await combo_el.click(force=True, timeout=5000)
    except Exception:
        await combo_el.evaluate("e => e.click()")
    await asyncio.sleep(1)

    # Only look at VISIBLE options — UI5 leaves stale options in DOM from prior opens
    options = await page.query_selector_all('[role="option"]')
    visible_options = []
    for opt in options:
        try:
            if await opt.is_visible():
                visible_options.append(opt)
        except Exception:
            pass

    for opt in visible_options:
        try:
            txt = (await opt.inner_text()).strip()
            if "Tier 3" in txt or "Agentic" in txt:
                await opt.click()
                await asyncio.sleep(0.5)
                return True
        except Exception:
            pass

    await page.keyboard.press("Escape")
    await asyncio.sleep(0.3)
    print(f"    tier: no Tier 3 option (total={len(options)}, visible={len(visible_options)})")
    return False


async def read_match_rows(page):
    """Extract team codes and input indices for visible match rows."""
    return await page.evaluate("""
    () => {
        const results = [];
        const numberInputs = Array.from(document.querySelectorAll('input[type="number"]'));

        for (let i = 0; i < numberInputs.length; i += 2) {
            const inp = numberInputs[i];
            if (!numberInputs[i+1]) break;

            let node = inp.parentElement;
            let rowText = '';
            let abbrList = [];
            for (let d = 0; d < 20 && node; d++) {
                const t = (node.innerText || '').trim();
                const abbrs = (t.match(/\\b([A-Z]{2,3})\\b/g) || [])
                    .filter(a => !['Tier','Day','Match','UTC'].includes(a) || a === 'USA');
                if (abbrs.length >= 2) {
                    abbrList = abbrs;
                    rowText = t.substring(0, 200);
                    break;
                }
                node = node.parentElement;
            }

            results.push({
                rowIdx: i / 2,
                homeCode: abbrList[0] || '',
                awayCode: abbrList[1] || '',
                rowText: rowText.replace(/\\n/g, ' '),
                currentHome: numberInputs[i].value,
                currentAway: numberInputs[i+1].value,
            });
        }
        return results;
    }
    """)


async def fill_visible_matches(page, predictions, filled_log, set_tier=False, scores_only=False):
    """Fill all match rows currently visible on the page. Returns (filled, skipped) counts."""
    # Scroll to load all rows on this match day
    for _ in range(15):
        await page.keyboard.press("PageDown")
        await asyncio.sleep(0.2)
    await page.keyboard.press("Control+Home")
    await asyncio.sleep(1)

    match_rows = await read_match_rows(page)
    print(f"  Visible rows: {len(match_rows)}")

    filled = 0
    skipped = 0

    for m in match_rows:
        home_code = m['homeCode']
        away_code = m['awayCode']
        row_idx = m['rowIdx']

        home_team = normalize_team(home_code)
        away_team = normalize_team(away_code)

        pred = predictions.get((home_team, away_team))
        if not pred:
            # Fuzzy match
            for (h, a), p in predictions.items():
                hn = h[:5].lower()
                an = a[:5].lower()
                if (home_team[:5].lower() == hn or home_code.lower() in h.lower()) and \
                   (away_team[:5].lower() == an or away_code.lower() in a.lower()):
                    pred = p
                    home_team, away_team = h, a
                    break

        if not pred:
            print(f"  [{row_idx}] NO PRED: {home_code!r}/{home_team} vs {away_code!r}/{away_team}")
            skipped += 1
            continue

        match_key = f"{home_team}_vs_{away_team}"
        if match_key in filled_log:
            continue

        home_goals = pred["home_goals"]
        away_goals = pred["away_goals"]

        # Re-query inputs fresh for each fill
        number_inputs = await page.query_selector_all('input[type="number"]')

        h_idx = row_idx * 2
        a_idx = row_idx * 2 + 1

        if h_idx >= len(number_inputs):
            print(f"  [{row_idx}] index OOB ({len(number_inputs)} total)")
            skipped += 1
            continue

        # Skip locked/disabled inputs (match already started or closed)
        try:
            is_disabled = await number_inputs[h_idx].is_disabled()
            if is_disabled:
                print(f"  [{row_idx}] LOCKED: {home_team} vs {away_team} — skipping")
                skipped += 1
                continue
        except Exception:
            pass

        await set_number_input(number_inputs[h_idx], home_goals)
        await set_number_input(number_inputs[a_idx], away_goals)

        # Set Tier 3 (optional — slow due to popup interaction)
        tier_status = "tier skipped"
        if set_tier:
            tier_ok = await set_tier3_for_row(page, row_idx)
            tier_status = "tier3 ok" if tier_ok else "tier FAILED"

        # Proof URL: find the text input within the same row container
        proof_status = "no proof field"
        try:
            proof_input = await number_inputs[h_idx].evaluate_handle("""el => {
                let node = el.parentElement;
                for (let d = 0; d < 15 && node; d++) {
                    const inp = node.querySelector('input[type="text"]');
                    if (inp) return inp;
                    node = node.parentElement;
                }
                return null;
            }""")
            proof_el = proof_input.as_element() if proof_input else None
            if proof_el:
                await set_text_input(proof_el, PROOF_URL)
                proof_status = "proof ok"
        except Exception:
            pass

        print(f"  [{row_idx}] {home_team} {home_goals}-{away_goals} {away_team}  ({tier_status}, {proof_status})")
        filled_log.add(match_key)
        filled += 1

        if filled % 8 == 0:
            await asyncio.sleep(0.5)

    return filled, skipped


async def click_save(page):
    """Find and click the Save button (sticky footer — green, not 'I'm lucky today')."""
    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    await asyncio.sleep(1)

    # Target only the green Save button — explicitly exclude 'I'm lucky today'
    clicked = await page.evaluate("""
    () => {
        const buttons = Array.from(document.querySelectorAll('button'));
        const saveBtn = buttons.find(b => {
            const t = (b.innerText || b.textContent || '').trim().toLowerCase();
            const a = (b.getAttribute('aria-label') || '').toLowerCase();
            // Must match 'save' but NOT 'lucky'
            return (t === 'save' || a === 'save') && !t.includes('lucky');
        });
        if (saveBtn) {
            saveBtn.scrollIntoView();
            saveBtn.click();
            return saveBtn.innerText || saveBtn.textContent || 'save';
        }
        return null;
    }
    """)

    if clicked:
        print(f"Clicked Save button via JS: {clicked!r}")
        await asyncio.sleep(4)
        return True

    # Playwright fallback — force click, exclude lucky button
    buttons = await page.query_selector_all("button")
    for btn in buttons:
        try:
            text = (await btn.inner_text()).strip().lower()
            if text == "save":
                print(f"Clicking Save button (force): {text!r}")
                await btn.scroll_into_view_if_needed()
                await asyncio.sleep(0.3)
                await btn.click(force=True)
                await asyncio.sleep(4)
                return True
        except Exception:
            pass

    print("WARNING: Save button not found!")
    return False


async def select_all_matches(page):
    """Click the Match Day UI5 Select dropdown and choose 'All matches' option."""
    select_el = None

    for selector in [
        '[class*="sapMSlt"][class*="sapMSltDefault"]',
        '[class*="sapMSlt"]',
        '[role="combobox"]',
    ]:
        candidates = await page.query_selector_all(selector)
        for el in candidates:
            try:
                visible = await el.is_visible()
                if visible:
                    txt = (await el.inner_text()).strip()
                    if "Day" in txt or "Match" in txt or "All" in txt:
                        select_el = el
                        print(f"  Found visible select: {txt!r}")
                        break
            except Exception:
                pass
        if select_el:
            break

    if not select_el:
        elements = await page.query_selector_all("*")
        for el in elements:
            try:
                visible = await el.is_visible()
                if not visible:
                    continue
                txt = (await el.inner_text()).strip()
                if txt.startswith("Match Day") and len(txt) < 20:
                    tag = await el.evaluate("e => e.tagName")
                    select_el = el
                    print(f"  Found by text: {tag} {txt!r}")
                    break
            except Exception:
                pass

    if not select_el:
        print("  No dropdown found")
        return False

    print("  Clicking dropdown...")
    await select_el.click()
    await asyncio.sleep(2)

    ts = time.strftime("%Y%m%d_%H%M%S")
    await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, f"dropdown_open_{ts}.png"))

    option_selectors = [
        '[role="option"]',
        '[class*="sapMSelectListItem"]',
        'li[class*="sapMSLI"]',
        '[class*="sapMLIB"]',
    ]
    for sel in option_selectors:
        options = await page.query_selector_all(sel)
        if options:
            print(f"  Found {len(options)} options with {sel!r}")
            for opt in options:
                try:
                    txt = (await opt.inner_text()).strip()
                    if "all" in txt.lower():
                        print(f"  Selecting 'All': {txt!r}")
                        await opt.click()
                        await asyncio.sleep(3)
                        return True
                except Exception:
                    pass
            break

    await page.keyboard.press("Escape")
    return False


async def fill_goallab(dry_run=False, inspect_only=False, forecasts_dir=None):
    predictions = load_consensus_predictions(forecasts_dir)
    print(f"Loaded {len(predictions)} consensus predictions from {forecasts_dir or FORECASTS_DIR}")

    if dry_run:
        for (h, a), pred in sorted(predictions.items(), key=lambda x: x[1]["match_date"]):
            print(f"  {pred['match_date']}  {h} {pred['home_goals']}-{pred['away_goals']} {a}")
        return

    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            PROFILE_DIR,
            channel="msedge",
            headless=False,
            accept_downloads=True,
            args=["--start-maximized"],
            no_viewport=True,
        )

        page = context.pages[0] if context.pages else await context.new_page()

        print("Loading outer launchpad for session auth...")
        await page.goto(GOALLAB_OUTER_URL, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(8)

        print("Navigating to GoalLab inner app URL...")
        await page.goto(GOALLAB_APP_URL, wait_until="domcontentloaded", timeout=60000)
        print("Waiting 25s for UI5 bootstrap...")
        await asyncio.sleep(25)

        ts = time.strftime("%Y%m%d_%H%M%S")
        await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, f"fill_start_{ts}.png"))

        if inspect_only:
            rows = await read_match_rows(page)
            print(f"Visible rows: {len(rows)}")
            for r in rows[:6]:
                print(f"  {r['homeCode']} {r['currentHome']}-{r['currentAway']} {r['awayCode']}  text={r['rowText'][:60]!r}")
            print("Looking for visible dropdowns...")
            for selector in ['[class*="sapMSlt"]', '[role="combobox"]']:
                candidates = await page.query_selector_all(selector)
                for el in candidates:
                    try:
                        visible = await el.is_visible()
                        txt = (await el.inner_text()).strip()[:50]
                        print(f"  {selector}: visible={visible} text={txt!r}")
                    except Exception:
                        pass

            switched = await select_all_matches(page)
            print(f"Dropdown switch result: {switched}")
            print("\nPress Enter to close.")
            input()
            await context.close()
            return

        # Switch to "All matches" view
        print("Switching to All matches view...")
        switched = await select_all_matches(page)
        if switched:
            print("All matches view selected. Waiting for render...")
            await asyncio.sleep(5)
        else:
            print("Could not switch to All view -- will process current view only")

        filled_log = set()
        total_filled = 0
        total_skipped = 0

        f, s = await fill_visible_matches(page, predictions, filled_log, set_tier=True)
        total_filled += f
        total_skipped += s

        print(f"\nTotal: filled={total_filled}, skipped={total_skipped}")

        # SAVE
        if total_filled > 0 or total_skipped == 0:
            print("Saving...")
            saved = await click_save(page)
            if not saved:
                print("WARNING: Save may have failed — check GoalLab manually")
        else:
            print("Nothing filled — skipping save")

        ts = time.strftime("%Y%m%d_%H%M%S")
        await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, f"fill_done_{ts}.png"), full_page=True)
        print("Final screenshot saved.")

        print("\nDone! Press Enter to close browser.")
        try:
            input()
        except EOFError:
            await asyncio.sleep(3)
        await context.close()


def main():
    dry_run = "--dry-run" in sys.argv
    inspect_only = "--inspect" in sys.argv

    # --version <stamp>  e.g. --version 20260620-1452 to use a specific archive
    forecasts_dir = None
    if "--version" in sys.argv:
        idx = sys.argv.index("--version")
        if idx + 1 < len(sys.argv):
            stamp = sys.argv[idx + 1]
            forecasts_dir = os.path.join(ARCHIVE_DIR, stamp)
            if not os.path.isdir(forecasts_dir):
                print(f"ERROR: archive not found: {forecasts_dir}")
                sys.exit(1)
            print(f"Using archive version: {stamp}")

    asyncio.run(fill_goallab(dry_run=dry_run, inspect_only=inspect_only, forecasts_dir=forecasts_dir))


if __name__ == "__main__":
    main()
