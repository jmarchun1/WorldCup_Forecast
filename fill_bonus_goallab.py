"""
fill_bonus_goallab.py — Fill GoalLab WC2026 bonus questions tab.

Loads consensus forecasts from results/bonus/*_CONSENSUS.json and fills
the bonus questions in the GoalLab UI.

Usage:
    python fill_bonus_goallab.py              # fill all bonus questions
    python fill_bonus_goallab.py --inspect    # inspect DOM only, no fill
"""

import asyncio
import json
import os
import sys
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BONUS_RESULTS_DIR = os.path.join(BASE_DIR, "results", "bonus")
SCREENSHOTS_DIR = os.path.join(BASE_DIR, "screenshots")
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

GOALLAB_OUTER_URL = (
    "https://sapit-home-prod-004.launchpad.cfapps.eu10.hana.ondemand.com/"
    "site#GoalLab-Tipping?mobilestart.tile.hidden=true"
    "&sap-ui-app-id-hint=304119ff-b2b0-403e-8d0a-fa638a0bed6d"
    "&/tournamentDetail/WC2026/?tab=bonusQuestions"
)

GOALLAB_APP_URL = (
    "https://sapit-hr-prod-bear.launchpad.cfapps.eu10.hana.ondemand.com/"
    "ad170241-3021-4e9d-9d8a-e7b0609aeff4.GoalLab.comsaptipit/ui5appwz.html"
    "?sap-ui-app-id=ABC&sap-locale=en&sap-shell=FLP&sap-theme=sap_horizon"
    "#GoalLab-Tipping?mobilestart.tile.hidden=true"
    "&sap-ui-app-id-hint=304119ff-b2b0-403e-8d0a-fa638a0bed6d"
    "&/tournamentDetail/WC2026/?tab=bonusQuestions"
)

PROFILE_DIR = os.path.join(
    os.path.expanduser("~"),
    "AppData", "Local", "Microsoft", "Edge", "User Data", "Playwright-GoalLab2"
)

PROOF_URL = "https://pages.github.tools.sap/I846720/WCFCST/"


def load_consensus():
    """Load all bonus consensus answers keyed by question_id."""
    data = {}
    for fname in os.listdir(BONUS_RESULTS_DIR):
        if not fname.endswith("_CONSENSUS.json"):
            continue
        with open(os.path.join(BONUS_RESULTS_DIR, fname), encoding="utf-8") as f:
            rec = json.load(f)
        data[rec["question_id"]] = rec
    return data


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


async def inspect_bonus_tab(page):
    """Print DOM structure of bonus questions tab."""
    ts = time.strftime("%Y%m%d_%H%M%S")
    await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, f"bonus_inspect_{ts}.png"), full_page=True)
    print(f"Screenshot saved: bonus_inspect_{ts}.png")

    # Find all text inputs
    text_inputs = await page.query_selector_all('input[type="text"]')
    print(f"\nText inputs: {len(text_inputs)}")
    for i, inp in enumerate(text_inputs[:20]):
        try:
            val = await inp.get_attribute("value") or ""
            ph = await inp.get_attribute("placeholder") or ""
            visible = await inp.is_visible()
            print(f"  [{i}] visible={visible} value={val!r} placeholder={ph!r}")
        except Exception as e:
            print(f"  [{i}] error: {e}")

    # Find number inputs
    num_inputs = await page.query_selector_all('input[type="number"]')
    print(f"\nNumber inputs: {len(num_inputs)}")
    for i, inp in enumerate(num_inputs[:10]):
        try:
            val = await inp.get_attribute("value") or ""
            visible = await inp.is_visible()
            print(f"  [{i}] visible={visible} value={val!r}")
        except Exception as e:
            print(f"  [{i}] error: {e}")

    # Find all comboboxes
    combos = await page.query_selector_all('[role="combobox"]')
    print(f"\nComboboxes: {len(combos)}")
    for i, cb in enumerate(combos[:15]):
        try:
            txt = (await cb.inner_text()).strip()[:60]
            visible = await cb.is_visible()
            print(f"  [{i}] visible={visible} text={txt!r}")
        except Exception as e:
            print(f"  [{i}] error: {e}")

    # Print page text to understand question labels
    body_text = await page.evaluate("() => document.body.innerText")
    lines = [l.strip() for l in body_text.split('\n') if l.strip()]
    print(f"\nPage text (first 60 lines):")
    for line in lines[:60]:
        print(f"  {line}")


async def fill_bonus_questions(page, consensus, inspect_only=False):
    """Fill bonus question inputs on the page."""
    if inspect_only:
        await inspect_bonus_tab(page)
        return {}

    ts = time.strftime("%Y%m%d_%H%M%S")
    await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, f"bonus_start_{ts}.png"))

    # Questions appear in this fixed order in the GoalLab UI
    QUESTION_ORDER = [
        "first_goal_team",
        "most_goals_team",
        "tournament_winner",
        "total_red_cards",
        "penalty_shootout_games",
        "total_goals",
        "final_goals",
    ]

    answers = {qid: consensus.get(qid, {}).get("consensus_answer", "") for qid in QUESTION_ORDER}
    print("\nBonus answers to fill:")
    for qid in QUESTION_ORDER:
        print(f"  {qid}: {answers[qid]!r}")

    # All 7 bonus fields are text inputs — fill only visible + enabled ones
    all_text = await page.query_selector_all('input[type="text"]')
    visible_text = []
    for inp in all_text:
        if await inp.is_visible():
            visible_text.append(inp)

    print(f"\nVisible text inputs found: {len(visible_text)}")

    # Build list of editable (enabled) inputs — locked questions are disabled
    editable_inputs = []
    for inp in visible_text:
        enabled = await inp.is_enabled()
        val = (await inp.get_attribute("value") or "").strip()
        print(f"  input: enabled={enabled} value={val!r}")
        if enabled:
            editable_inputs.append(inp)

    print(f"  Editable inputs: {len(editable_inputs)}")

    # Map editable inputs positionally to questions that aren't locked
    # Locked = disabled input (question deadline passed or already answered & locked)
    editable_questions = []
    idx_editable = 0
    all_text2_check = []
    for inp in visible_text:
        all_text2_check.append(await inp.is_enabled())

    # Re-map: skip disabled slots in the question order
    ei = 0
    filled = 0
    for i, qid in enumerate(QUESTION_ORDER):
        if i >= len(visible_text):
            print(f"  [{i}] {qid}: NO INPUT")
            continue
        inp = visible_text[i]
        if not await inp.is_enabled():
            print(f"  [{i}] {qid}: LOCKED, skipping")
            continue
        ans = answers[qid]
        if not ans:
            print(f"  [{i}] {qid}: no answer")
            continue
        await set_text_input(inp, ans)
        print(f"  [{i}] {qid}: filled {ans!r}")
        filled += 1

    # Set Tier 3: Agentic on all 7 tier comboboxes
    # Comboboxes pattern: [answer_input, tier_combobox] per question (pairs at indices 3,5,7,9,11,13)
    print("\nSetting Tier 3 on all bonus questions...")
    all_combos = await page.query_selector_all('[role="combobox"]')
    visible_combos = []
    for cb in all_combos:
        if await cb.is_visible():
            visible_combos.append(cb)

    print(f"  Visible comboboxes: {len(visible_combos)}")
    tier_set = 0
    for i, cb in enumerate(visible_combos):
        try:
            txt = (await cb.inner_text()).strip()
            print(f"  combo [{i}]: {txt!r}")
        except Exception:
            pass

    # Try to set Tier 3 on comboboxes that show "gut feeling" or tier-related text
    for i, cb in enumerate(visible_combos):
        try:
            txt = (await cb.inner_text()).strip()
            if "gut feeling" in txt.lower() or "tier" in txt.lower() or "1x" in txt:
                await cb.scroll_into_view_if_needed()
                await asyncio.sleep(0.2)
                try:
                    await cb.click(force=True, timeout=5000)
                except Exception:
                    await cb.evaluate("e => e.click()")
                await asyncio.sleep(1)

                options = await page.query_selector_all('[role="option"]')
                visible_opts = [o for o in options if await o.is_visible()]
                if not visible_opts:
                    # Wait longer and retry click
                    await asyncio.sleep(1.5)
                    try:
                        await cb.click(force=True, timeout=5000)
                    except Exception:
                        await cb.evaluate("e => e.click()")
                    await asyncio.sleep(1.5)
                    options = await page.query_selector_all('[role="option"]')
                    visible_opts = [o for o in options if await o.is_visible()]
                tier3_found = False
                for opt in visible_opts:
                    try:
                        opt_txt = (await opt.inner_text()).strip()
                        if "tier 3" in opt_txt.lower() or "agentic" in opt_txt.lower():
                            await opt.click()
                            await asyncio.sleep(0.5)
                            tier3_found = True
                            tier_set += 1
                            print(f"  combo [{i}]: set to Tier 3 ok")
                            break
                    except Exception:
                        pass
                if not tier3_found:
                    await page.keyboard.press("Escape")
                    await asyncio.sleep(0.3)
                    if visible_opts:
                        print(f"  combo [{i}]: Tier 3 not found (options: {[await o.inner_text() for o in visible_opts[:5]]})")
                    else:
                        print(f"  combo [{i}]: no visible options")
        except Exception as e:
            print(f"  combo [{i}]: error {e}")

    print(f"\nTier 3 set on {tier_set} comboboxes, filled {filled} answer fields")

    # Set proof URL on any visible text input that looks like a proof/URL field
    # Re-query inputs in case DOM updated after tier setting
    all_text2 = await page.query_selector_all('input[type="text"]')
    for inp in all_text2:
        try:
            if not await inp.is_visible():
                continue
            ph = (await inp.get_attribute("placeholder") or "").lower()
            val = (await inp.get_attribute("value") or "")
            # Only fill proof field if it looks like a URL/proof field
            if "proof" in ph or "url" in ph or "http" in val or ("link" in ph):
                await set_text_input(inp, PROOF_URL)
                print(f"  Proof URL set (ph={ph!r})")
        except Exception:
            pass

    return answers


async def click_save(page):
    buttons = await page.query_selector_all("button")
    save_keywords = ("save", "i'm lucky today", "im lucky today", "submit", "confirm")
    for btn in buttons:
        try:
            text = (await btn.inner_text()).strip().lower()
            if any(kw in text for kw in save_keywords):
                if await btn.is_visible():
                    print(f"Clicking save: {text!r}")
                    await btn.click()
                    await asyncio.sleep(4)
                    return True
        except Exception:
            pass
    for btn in buttons:
        try:
            aria = (await btn.get_attribute("aria-label") or "").lower()
            cls = (await btn.get_attribute("class") or "").lower()
            if "save" in aria or "save" in cls:
                if await btn.is_visible():
                    print(f"Clicking save (aria/class): aria={aria!r}")
                    await btn.click()
                    await asyncio.sleep(4)
                    return True
        except Exception:
            pass
    print("WARNING: Save button not found!")
    return False


async def run(inspect_only=False):
    consensus = load_consensus()
    print(f"Loaded {len(consensus)} bonus consensus answers:")
    for qid, rec in consensus.items():
        print(f"  {qid}: {rec['consensus_answer']!r} (n={rec['model_count']}, conf={rec['avg_confidence']})")

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

        print("\nLoading outer launchpad for session auth...")
        await page.goto(GOALLAB_OUTER_URL, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(8)

        print("Navigating to GoalLab bonus questions tab...")
        await page.goto(GOALLAB_APP_URL, wait_until="domcontentloaded", timeout=60000)
        print("Waiting 25s for UI5 bootstrap...")
        await asyncio.sleep(25)

        ts = time.strftime("%Y%m%d_%H%M%S")
        await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, f"bonus_loaded_{ts}.png"), full_page=True)

        answer_map = await fill_bonus_questions(page, consensus, inspect_only=inspect_only)

        if not inspect_only and answer_map:
            ts = time.strftime("%Y%m%d_%H%M%S")
            await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, f"bonus_done_{ts}.png"), full_page=True)
            print("Final screenshot saved.")

        print("\nDone! Press Enter to close browser.")
        try:
            input()
        except EOFError:
            await asyncio.sleep(3)
        await context.close()


def main():
    inspect_only = "--inspect" in sys.argv
    asyncio.run(run(inspect_only=inspect_only))


if __name__ == "__main__":
    main()
