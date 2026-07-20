"""
open_goallab.py — Open the GoalLab SAP tipping competition page using
Edge persistent context (dedicated sub-profile to avoid lock conflicts).

First run: browser opens, complete SAP SSO login manually.
Subsequent runs: session reused automatically.

Usage:
    python open_goallab.py                    # open matches tab
    python open_goallab.py --tab bonus        # open bonus questions tab
    python open_goallab.py --screenshot       # screenshot and save
"""

import asyncio
import os
import sys
import time

GOALLAB_MATCHES_URL = (
    "https://sapit-home-prod-004.launchpad.cfapps.eu10.hana.ondemand.com/"
    "site#GoalLab-Tipping?mobilestart.tile.hidden=true"
    "&sap-ui-app-id-hint=304119ff-b2b0-403e-8d0a-fa638a0bed6d"
    "&/tournamentDetail/WC2026/?tab=matches"
)

GOALLAB_BONUS_URL = (
    "https://sapit-home-prod-004.launchpad.cfapps.eu10.hana.ondemand.com/"
    "site#GoalLab-Tipping?mobilestart.tile.hidden=true"
    "&sap-ui-app-id-hint=304119ff-b2b0-403e-8d0a-fa638a0bed6d"
    "&/tournamentDetail/WC2026/?tab=bonusQuestions"
)

PROFILE_DIR = os.path.join(
    os.path.expanduser("~"),
    "AppData", "Local", "Microsoft", "Edge", "User Data", "Playwright-GoalLab"
)

SCREENSHOTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "screenshots")
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)


async def wait_for_fiori_content(page, timeout_sec=120):
    """Poll until the GoalLab UI5 app renders meaningful content."""
    print(f"Polling for GoalLab content (up to {timeout_sec}s)...")
    deadline = time.time() + timeout_sec
    last_count = 0
    while time.time() < deadline:
        await asyncio.sleep(3)
        try:
            # Check for UI5 rendered content: match cards, score inputs, etc.
            content = await page.content()
            # Signs the GoalLab app has rendered:
            indicators = [
                "match", "score", "prediction", "Group", "WC2026",
                "sap-ui-core", "tournament", "tipping"
            ]
            hits = sum(1 for ind in indicators if ind.lower() in content.lower())

            # Count interactive elements as proxy for render progress
            inputs = await page.query_selector_all("input, select")
            btn_count = len(await page.query_selector_all("button"))

            print(f"  content hints={hits}/8, inputs={len(inputs)}, buttons={btn_count}")

            # GoalLab match predictions page should have score input fields
            if len(inputs) >= 4 or hits >= 5:
                print("GoalLab content detected!")
                await asyncio.sleep(3)  # let remaining renders settle
                return True

            # Check for login redirect
            if "logon" in content.lower() or "sign in" in content.lower():
                print("Login page detected — please complete SAP SSO login in the browser.")
                print("Press Enter here once you are logged in...")
                input()
                return False

        except Exception as e:
            print(f"  Poll error: {e}")

    print("Timeout waiting for content. Taking screenshot anyway.")
    return False


async def open_goallab(tab: str = "matches", take_screenshot: bool = False):
    from playwright.async_api import async_playwright

    url = GOALLAB_BONUS_URL if tab == "bonus" else GOALLAB_MATCHES_URL

    print(f"Profile dir: {PROFILE_DIR}")
    print(f"Navigating to: {url}")

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

        print("Navigating...")
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)

        content_loaded = await wait_for_fiori_content(page, timeout_sec=120)

        if take_screenshot:
            ts = time.strftime("%Y%m%d_%H%M%S")
            shot_path = os.path.join(SCREENSHOTS_DIR, f"goallab_{tab}_{ts}.png")
            await page.screenshot(path=shot_path, full_page=True)
            print(f"Screenshot saved: {shot_path}")

        # Extract page structure for understanding form fields
        print("\n--- Page title ---")
        print(await page.title())

        print("\n--- Interactive elements ---")
        inputs = await page.query_selector_all("input, select")
        print(f"Found {len(inputs)} input/select elements")
        for i, el in enumerate(inputs[:30]):
            tag = await el.evaluate("e => e.tagName")
            typ = await el.get_attribute("type") or ""
            name = await el.get_attribute("name") or ""
            placeholder = await el.get_attribute("placeholder") or ""
            val = await el.get_attribute("value") or ""
            cls = await el.get_attribute("class") or ""
            print(f"  [{i}] {tag} type={typ!r} name={name!r} placeholder={placeholder!r} value={val!r} class={cls[:60]!r}")

        print("\n--- Buttons ---")
        buttons = await page.query_selector_all("button")
        print(f"Found {len(buttons)} buttons")
        for i, btn in enumerate(buttons[:20]):
            text = (await btn.inner_text()).strip()[:80]
            cls = await btn.get_attribute("class") or ""
            print(f"  [{i}] {text!r} class={cls[:50]!r}")

        print("\nBrowser is open — inspect the page, then press Enter to close.")
        input()

        await context.close()


def main():
    tab = "matches"
    take_screenshot = False

    if "--tab" in sys.argv:
        idx = sys.argv.index("--tab")
        tab = sys.argv[idx + 1]
    if "--screenshot" in sys.argv:
        take_screenshot = True

    asyncio.run(open_goallab(tab=tab, take_screenshot=take_screenshot))


if __name__ == "__main__":
    main()
