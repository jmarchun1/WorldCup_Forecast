"""
make_results_image.py — Generate a results PNG carousel + PDF for a given match date.

Usage:
    python make_results_image.py --date 2026-06-26 --results "Egypt_Iran 1-1, New_Zealand_Belgium 0-3, Cape_Verde_Saudi_Arabia 1-1, Uruguay_Spain 1-2, Norway_France 0-1, Senegal_Iraq 2-0"

Each result entry: <home>_<away> <score>  OR  <partial_match_id> <score>
The script matches against known match IDs for that date.

Output: docs/results_<date>_card*.png  +  docs/results_<date>_carousel.pdf
Upload the PDF to LinkedIn as a Document post — it renders as a swipeable carousel.
"""

import argparse
import json
import os
import re
import sys
import img2pdf
from PIL import Image, ImageDraw, ImageFont

BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
FORECASTS_DIR = os.path.join(BASE_DIR, "results", "forecasts")
SCORED_DIR    = os.path.join(BASE_DIR, "results", "scored")
OUT_DIR       = os.path.join(BASE_DIR, "docs")
os.makedirs(OUT_DIR, exist_ok=True)

# Model display names + cost tier
MODEL_META = {
    "gem25pro":       ("Gemini 2.5 Pro",      "expensive"),
    "gem25flash":     ("Gemini 2.5 Flash",     "cheap"),
    "gem25flashlite": ("Gemini 2.5 Flash-Lite","cheap"),
    "gem31flashlite": ("Gemini 3.1 Flash-Lite","cheap"),
    "gpt5":           ("GPT-5",               "expensive"),
    "gpt54":          ("GPT-4o",              "mid"),
    "gpt5mini":       ("GPT-4o mini",         "cheap"),
    "haiku":          ("Claude Haiku",        "cheap"),
    "opus":           ("Claude Opus",         "expensive"),
    "sonnet":         ("Claude Sonnet",       "mid"),
    "sonar":          ("Sonar",               "mid"),
    "sonarpro":       ("Sonar Pro",           "mid"),
}

# --- Colour palette ---
BG        = (13, 17, 23)
HDR_BG    = (22, 27, 34)
MATCH_BG  = (26, 32, 44)
ROW_ALT   = (19, 24, 30)
ROW_NORM  = (13, 17, 23)
BORDER    = (48, 54, 61)
WHITE     = (230, 237, 243)
BLUE      = (88, 166, 255)
GREEN     = (63, 185, 80)
RED       = (248, 81, 73)
ORANGE    = (210, 153, 34)
GREY      = (139, 148, 158)
DIM       = (60, 70, 80)
YELLOW    = (230, 200, 60)
PURPLE    = (180, 120, 255)

TIER_COL  = {"cheap": GREEN, "mid": BLUE, "expensive": ORANGE}

def load_font(size, bold=False):
    candidates = ["C:/Windows/Fonts/segoeui.ttf",  "C:/Windows/Fonts/arial.ttf"]
    bold_c     = ["C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/arialbd.ttf"]
    for path in (bold_c if bold else candidates):
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()

F_TITLE   = load_font(18, bold=True)
F_MATCH   = load_font(14, bold=True)
F_HDR     = load_font(11, bold=True)
F_BODY    = load_font(11)
F_SMALL   = load_font(10)
F_FOOTER  = load_font(9)


def _result(h, a):
    if h > a: return "home_win"
    if a > h: return "away_win"
    return "draw"


def _brier(probs, outcome):
    outcomes = ["home_win", "draw", "away_win"]
    return round(sum((probs.get(o, 0) - (1 if o == outcome else 0)) ** 2 for o in outcomes), 3)


def _fantasy(pred_h, pred_a, act_h, act_a):
    if pred_h == act_h and pred_a == act_a:
        return 4, "Exact score"
    pr = _result(pred_h, pred_a)
    ar = _result(act_h, act_a)
    if pr != ar:
        return 0, "Wrong result"
    if ar != "draw" and abs(pred_h - pred_a) == abs(act_h - act_a):
        return 2, "Correct GD"
    if ar == "draw":
        return 1, "Correct draw"
    return 1, "Correct result"


def load_match_data(date: str) -> list[dict]:
    """Load consensus + per-model forecasts for all matches on a date."""
    matches = []
    for f in sorted(os.listdir(FORECASTS_DIR)):
        if not f.endswith("_CONSENSUS.json") or date not in f:
            continue
        mid = f.replace("_CONSENSUS.json", "")
        cons = json.load(open(os.path.join(FORECASTS_DIR, f), encoding="utf-8"))

        # Load per-model forecasts
        models = []
        for mf in sorted(os.listdir(FORECASTS_DIR)):
            if not mf.startswith(mid + "_") or mf.endswith("_CONSENSUS.json"):
                continue
            if not mf.endswith(".json"):
                continue
            rec = json.load(open(os.path.join(FORECASTS_DIR, mf), encoding="utf-8"))
            if rec.get("home_goals") is None:
                continue
            models.append(rec)

        matches.append({"mid": mid, "consensus": cons, "models": models})
    return matches


def parse_results(results_str: str, match_ids: list[str]) -> dict[str, tuple[int, int]]:
    result_map = {}
    for part in results_str.split(","):
        part = part.strip()
        tokens = part.rsplit(" ", 1)
        if len(tokens) != 2:
            continue
        key, score = tokens
        key = key.strip().replace(" ", "_")
        # Find best matching match_id
        matched = None
        for mid in match_ids:
            if key in mid or mid.startswith(key):
                matched = mid
                break
        if not matched:
            # fuzzy: check if key appears anywhere
            for mid in match_ids:
                if key.lower() in mid.lower():
                    matched = mid
                    break
        if matched:
            parts = score.strip().split("-")
            if len(parts) == 2:
                result_map[matched] = (int(parts[0]), int(parts[1]))
    return result_map


# ─── Layout constants ──────────────────────────────────────────────────────────
PAD      = 12
TITLE_H  = 50
FOOTER_H = 28

# Per-match block
MATCH_H  = 32   # match header bar
MODEL_H  = 20   # per-model row height
GAP      = 6    # gap between match blocks

# Column widths:  Model | Predicted | Points | Brier | LLM probs | Market probs | Edge
COL_W = [140, 70, 50, 56, 210, 210, 130]
COLS  = ["Model", "Predicted", "Pts", "Brier", "LLM Probs (H · D · A)", "Market (H · D · A)", "Edge / Value"]

total_w = sum(COL_W) + PAD * 2


def col_x(ci):
    x = PAD
    for i in range(ci):
        x += COL_W[i]
    return x


CARD_W  = 1080   # LinkedIn carousel optimal width
HDR_H_C = 80     # match title bar
COL_H   = 26     # column header
ROW_H_C = 36     # per-model row (taller for readability)
FOOT_H  = 38

# Card column layout: Model | Predicted | Result | Pts | Brier | LLM probs | Market | Edge
CARD_COLS = ["Model", "Predicted", "Actual", "Pts", "Brier", "LLM (H · D · A)", "Market (H · D · A)", "Edge"]
CARD_CW   = [170,      80,          80,       44,    58,      200,             200,                   168]

F2_TITLE  = load_font(22, bold=True)
F2_SUB    = load_font(14)
F2_HDR    = load_font(12, bold=True)
F2_BODY   = load_font(13)
F2_SMALL  = load_font(12)
F2_FOOT   = load_font(10)


def _card_col_x(ci):
    x = PAD
    for i in range(ci):
        x += CARD_CW[i]
    return x


def draw_card(match: dict, card_num: int, total_cards: int) -> Image.Image:
    mid      = match["mid"]
    cons     = match["consensus"]
    models   = match["models"]
    act_h, act_a = match.get("actual", (None, None))
    home     = cons.get("home", mid.split("_")[0])
    away     = cons.get("away", mid.split("_")[-2])
    mkt_h    = cons.get("implied_home", 0)
    mkt_d    = cons.get("implied_draw", 0)
    mkt_a    = cons.get("implied_away", 0)

    n        = len(models)
    card_h   = HDR_H_C + COL_H + n * ROW_H_C + FOOT_H

    img = Image.new("RGB", (CARD_W, card_h), BG)
    d   = ImageDraw.Draw(img)

    def dt(x, y, text, font, color, anchor="lm"):
        d.text((x, y), str(text), font=font, fill=color, anchor=anchor)

    # Header
    d.rectangle([0, 0, CARD_W, HDR_H_C], fill=HDR_BG)
    d.line([0, HDR_H_C - 2, CARD_W, HDR_H_C - 2], fill=(247, 129, 102), width=2)

    # Card counter top-right
    dt(CARD_W - PAD, 14, f"{card_num}/{total_cards}", F2_FOOT, GREY, anchor="rm")

    # Match title
    dt(PAD, 26, f"{home}  vs  {away}", F2_TITLE, WHITE)

    # Actual result or pending
    if act_h is not None:
        result_label = f"Final:  {act_h} – {act_a}"
        act_outcome  = _result(act_h, act_a)
        outcome_word = {"home_win": f"{home} win", "away_win": f"{away} win", "draw": "Draw"}[act_outcome]
        dt(PAD, 56, result_label, F2_SUB, GREEN)
        dt(PAD + 200, 56, f"({outcome_word})", F2_SUB, GREY)
    else:
        dt(PAD, 56, "Result pending", F2_SUB, GREY)

    # Consensus badge right
    cpred = f"Consensus  {cons['consensus_home_goals']}–{cons['consensus_away_goals']}"
    dt(CARD_W - PAD, 38, cpred, F2_HDR, YELLOW, anchor="rm")
    mkt_line = f"Market  {home} {mkt_h:.0%}  ·  Draw {mkt_d:.0%}  ·  {away} {mkt_a:.0%}"
    dt(CARD_W - PAD, 58, mkt_line, F2_FOOT, GREY, anchor="rm")

    # Column headers
    y = HDR_H_C
    d.rectangle([0, y, CARD_W, y + COL_H - 1], fill=(30, 35, 45))
    d.line([0, y + COL_H - 1, CARD_W, y + COL_H - 1], fill=BORDER, width=1)
    for ci, col in enumerate(CARD_COLS):
        dt(_card_col_x(ci) + 4, y + COL_H // 2, col, F2_HDR, BLUE)
    y += COL_H

    # Sort: correct first then by brier
    def sort_key(rec):
        ph, pa = rec["home_goals"], rec["away_goals"]
        pts = 0
        if act_h is not None:
            pts, _ = _fantasy(ph, pa, act_h, act_a)
        probs = {"home_win": rec.get("home_win_prob", 0),
                 "draw":     rec.get("draw_prob", 0),
                 "away_win": rec.get("away_win_prob", 0)}
        br = _brier(probs, _result(act_h, act_a)) if act_h is not None else 0.667
        return (-pts, br)

    sorted_models = sorted(models, key=sort_key)

    for i, rec in enumerate(sorted_models):
        ms     = rec.get("model_short", "?")
        ph, pa = rec["home_goals"], rec["away_goals"]
        hw     = rec.get("home_win_prob", 0)
        dp_    = rec.get("draw_prob", 0)
        aw     = rec.get("away_win_prob", 0)
        tier   = MODEL_META.get(ms, ("?", "mid"))[1]
        name   = MODEL_META.get(ms, (ms, "mid"))[0]

        row_bg = ROW_ALT if i % 2 == 1 else ROW_NORM
        d.rectangle([0, y, CARD_W, y + ROW_H_C - 1], fill=row_bg)
        mid_y = y + ROW_H_C // 2

        pts_str = "–"; brier_str = "–"
        pts_col = GREY; brier_col = GREY; pred_col = GREY; actual_col = GREY

        if act_h is not None:
            act_outcome = _result(act_h, act_a)
            pts, _      = _fantasy(ph, pa, act_h, act_a)
            probs       = {"home_win": hw, "draw": dp_, "away_win": aw}
            br          = _brier(probs, act_outcome)
            pts_str     = str(pts)
            brier_str   = f"{br:.3f}"
            pts_col     = GREEN if pts >= 4 else (BLUE if pts >= 2 else (ORANGE if pts == 1 else RED))
            brier_col   = GREEN if br < 0.4 else (ORANGE if br < 0.6 else RED)
            pred_col    = GREEN if pts > 0 else RED
            actual_col  = GREEN

        # Model
        dt(_card_col_x(0) + 4, mid_y, name, F2_BODY, TIER_COL.get(tier, GREY))
        # Predicted
        dt(_card_col_x(1) + 4, mid_y, f"{ph}–{pa}", F2_BODY, pred_col)
        # Actual
        act_str = f"{act_h}–{act_a}" if act_h is not None else "–"
        dt(_card_col_x(2) + 4, mid_y, act_str, F2_BODY, actual_col)
        # Pts
        dt(_card_col_x(3) + CARD_CW[3]//2, mid_y, pts_str, F2_BODY, pts_col, anchor="mm")
        # Brier
        dt(_card_col_x(4) + CARD_CW[4]//2, mid_y, brier_str, F2_SMALL, brier_col, anchor="mm")
        # LLM probs
        dt(_card_col_x(5) + 4, mid_y, f"{home} {hw:.0%}  D {dp_:.0%}  {away} {aw:.0%}", F2_SMALL, GREY)
        # Market probs
        dt(_card_col_x(6) + 4, mid_y, f"{home} {mkt_h:.0%}  D {mkt_d:.0%}  {away} {mkt_a:.0%}", F2_SMALL, DIM)
        # Edge
        dh = hw - mkt_h; dd = dp_ - mkt_d; da = aw - mkt_a
        biggest = max([("H", dh, home), ("D", dd, "Draw"), ("A", da, away)], key=lambda x: abs(x[1]))
        _, diff, lname = biggest
        if abs(diff) >= 0.05:
            sign = "+" if diff > 0 else ""
            edge_str = f"{lname} {sign}{diff:.0%}"
            edge_col = GREEN if diff > 0 else ORANGE
        else:
            edge_str = "—"; edge_col = DIM
        dt(_card_col_x(7) + 4, mid_y, edge_str, F2_SMALL, edge_col)

        y += ROW_H_C

    # Column dividers
    for ci in range(1, len(CARD_COLS)):
        x = _card_col_x(ci)
        d.line([x, HDR_H_C, x, card_h - FOOT_H], fill=BORDER, width=1)

    # Footer
    d.rectangle([0, card_h - FOOT_H, CARD_W, card_h], fill=HDR_BG)
    dt(PAD, card_h - FOOT_H // 2,
       "12 LLM models · Anthropic · OpenAI · Google · Perplexity  ·  Brier: 0=perfect 0.667=random  ·  Pts: 4=exact 2=correct-GD 1=correct",
       F2_FOOT, GREY)
    dt(CARD_W - PAD, card_h - FOOT_H // 2, "WC2026 LLM Forecast", F2_FOOT, DIM, anchor="rm")

    return img


def draw_image(matches_with_results: list[dict], date: str) -> list[str]:
    total = len(matches_with_results)
    paths = []
    for i, match in enumerate(matches_with_results, 1):
        mid   = match["mid"]
        img   = draw_card(match, i, total)
        fname = f"results_{date}_card{i:02d}_{mid}.png"
        out   = os.path.join(OUT_DIR, fname)
        img.save(out, "PNG")
        paths.append(out)
    return paths


def draw_summary_card(matches: list[dict], date: str) -> Image.Image:
    """Card 1: big visual pop — one row per match showing result vs consensus at a glance."""
    W       = CARD_W
    T_H     = 90        # title area
    ROW_S   = 80        # per-match row
    FOOT_S  = 36
    n       = len(matches)
    H       = T_H + n * ROW_S + FOOT_S

    img = Image.new("RGB", (W, H), BG)
    d   = ImageDraw.Draw(img)

    def dt(x, y, text, font, color, anchor="lm"):
        d.text((x, y), str(text), font=font, fill=color, anchor=anchor)

    # Title bar
    d.rectangle([0, 0, W, T_H], fill=HDR_BG)
    d.line([0, T_H - 2, W, T_H - 2], fill=(247, 129, 102), width=2)
    dt(PAD, 30, f"WC2026 LLM Forecast  ·  {date}  ·  Results", load_font(20, bold=True), WHITE)
    dt(PAD, 62, "How did 12 AI models do? Swipe for per-match breakdown →", load_font(13), GREY)

    y = T_H
    for i, match in enumerate(matches):
        mid      = match["mid"]
        cons     = match["consensus"]
        models   = match["models"]
        act_h, act_a = match.get("actual", (None, None))
        home     = cons.get("home", "")
        away     = cons.get("away", "")
        c_h      = cons["consensus_home_goals"]
        c_a      = cons["consensus_away_goals"]

        row_bg = ROW_ALT if i % 2 == 1 else ROW_NORM
        d.rectangle([0, y, W, y + ROW_S - 1], fill=row_bg)
        d.line([0, y + ROW_S - 1, W, y + ROW_S - 1], fill=BORDER, width=1)

        mid_y  = y + ROW_S // 2
        line1  = y + ROW_S // 2 - 12
        line2  = y + ROW_S // 2 + 10

        # Match name
        dt(PAD, mid_y, f"{home}  vs  {away}", load_font(15, bold=True), WHITE)

        # Consensus prediction (centre-left)
        cx = 320
        dt(cx, line1, "Consensus", load_font(10), GREY)
        dt(cx, line2, f"{c_h} – {c_a}", load_font(18, bold=True), BLUE)

        # Actual result (centre)
        ax = 460
        if act_h is not None:
            dt(ax, line1, "Actual", load_font(10), GREY)
            cons_outcome = _result(c_h, c_a)
            act_outcome  = _result(act_h, act_a)
            match_col    = GREEN if cons_outcome == act_outcome else RED
            dt(ax, line2, f"{act_h} – {act_a}", load_font(18, bold=True), match_col)
        else:
            dt(ax, line2, "Pending", load_font(14), GREY)

        # How many models correct
        if act_h is not None:
            correct = sum(1 for r in models
                         if _result(r["home_goals"], r["away_goals"]) == _result(act_h, act_a))
            exact   = sum(1 for r in models
                         if r["home_goals"] == act_h and r["away_goals"] == act_a)
            dt(620, line1, "Models correct", load_font(10), GREY)
            dt(620, line2, f"{correct}/12 result  ·  {exact}/12 exact", load_font(13), ORANGE)

        # Biggest edge call
        mkt_h = cons.get("implied_home", 0)
        mkt_d = cons.get("implied_draw", 0)
        mkt_a = cons.get("implied_away", 0)
        avg_h = sum(r.get("home_win_prob", 0) for r in models) / max(len(models), 1)
        avg_d = sum(r.get("draw_prob", 0) for r in models) / max(len(models), 1)
        avg_a = sum(r.get("away_win_prob", 0) for r in models) / max(len(models), 1)
        diffs = [(home, avg_h - mkt_h), ("Draw", avg_d - mkt_d), (away, avg_a - mkt_a)]
        biggest_label, biggest_diff = max(diffs, key=lambda x: abs(x[1]))
        if abs(biggest_diff) >= 0.05:
            sign = "+" if biggest_diff > 0 else ""
            dt(860, line1, "LLM vs Market", load_font(10), GREY)
            ecol = GREEN if biggest_diff > 0 else ORANGE
            dt(860, line2, f"{biggest_label} {sign}{biggest_diff:.0%}", load_font(13, bold=True), ecol)

        y += ROW_S

    # Footer
    d.rectangle([0, H - FOOT_S, W, H], fill=HDR_BG)
    dt(PAD, H - FOOT_S // 2, "12 LLM models · Anthropic · OpenAI · Google · Perplexity", load_font(10), GREY)
    dt(W - PAD, H - FOOT_S // 2, "Swipe → for per-match model breakdown", load_font(10), DIM, anchor="rm")

    return img


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="Match date e.g. 2026-06-26")
    parser.add_argument("--results", default="",
                        help="Comma-separated results e.g. 'Egypt_Iran 1-1, New_Zealand_Belgium 0-3'")
    args = parser.parse_args()

    matches = load_match_data(args.date)
    if not matches:
        print(f"No matches found for {args.date}")
        sys.exit(1)

    mid_list = [m["mid"] for m in matches]
    result_map = parse_results(args.results, mid_list) if args.results else {}

    for m in matches:
        m["actual"] = result_map.get(m["mid"], (None, None))
        if m["actual"] == (None, None):
            for sf in os.listdir(SCORED_DIR):
                if sf.startswith(m["mid"] + "_") and sf.endswith(".json"):
                    rec = json.load(open(os.path.join(SCORED_DIR, sf), encoding="utf-8"))
                    ah, aa = rec.get("actual_home"), rec.get("actual_away")
                    if ah is not None:
                        m["actual"] = (ah, aa)
                    break

    # Card 1: summary pop
    summary = draw_summary_card(matches, args.date)
    summary_path = os.path.join(OUT_DIR, f"results_{args.date}_card00_summary.png")
    summary.save(summary_path, "PNG")
    print(f"Card 1 (summary): {summary_path}")

    # Cards 2–N: per-match detail
    paths = draw_image(matches, args.date)
    for p in paths:
        print(f"  Detail: {p}")

    all_cards = [summary_path] + paths

    # Build LinkedIn carousel PDF
    pdf_path = os.path.join(OUT_DIR, f"results_{args.date}_carousel.pdf")
    with open(pdf_path, "wb") as f:
        f.write(img2pdf.convert(all_cards))
    print(f"\nLinkedIn carousel PDF: {pdf_path}")
    print(f"Total: {len(all_cards)} cards  ->  upload the PDF as a LinkedIn Document post")


if __name__ == "__main__":
    main()
