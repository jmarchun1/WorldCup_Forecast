"""
make_linkedin_table.py — Generate a LinkedIn-ready PNG of remaining match predictions vs prediction market.
Each row shows model probs and market probs spelled out as "Home Draw Away" with team names.
"""
from PIL import Image, ImageDraw, ImageFont
import os

OUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs", "linkedin_predictions.png")

# (home, away, pred, home_model%, draw_model%, away_model%, home_mkt%, draw_mkt%, away_mkt%, edge)
JUN26 = [
    ("Egypt",       "Iran",         "1 – 1", 41, 33, 26, 39, 36, 25, ""),
    ("New Zealand", "Belgium",      "0 – 3",  8, 16, 76,  6, 14, 80, ""),
    ("Cape Verde",  "Saudi Arabia", "1 – 1", 34, 35, 31, 39, 28, 33, "Draw underpriced"),
    ("Uruguay",     "Spain",        "1 – 2", 24, 32, 44, 13, 23, 64, "Models favour Uruguay"),
    ("Norway",      "France",       "1 – 1", 25, 43, 32, 21, 22, 57, "Draw massively underpriced"),
    ("Senegal",     "Iraq",         "1 – 1", 39, 39, 22, 78, 15,  7, "Biggest divergence"),
]
JUN27 = [
    ("Algeria",   "Austria",    "1 – 1", 30, 32, 38, 24, 43, 33, "Market overweights draw"),
    ("Jordan",    "Argentina",  "0 – 2",  9, 25, 65,  6, 12, 82, "Models see it closer"),
    ("Colombia",  "Portugal",   "1 – 1", 28, 30, 42, 24, 25, 51, ""),
    ("DR Congo",  "Uzbekistan", "1 – 1", 38, 35, 27, 55, 23, 22, "Draw underpriced"),
    ("Panama",    "England",    "0 – 2",  8, 18, 74,  6, 12, 82, ""),
    ("Croatia",   "Ghana",      "1 – 1", 46, 32, 22, 53, 30, 17, ""),
]

# --- Styling ---
BG       = (13, 17, 23)
HDR_BG   = (22, 27, 34)
DAY_BG   = (26, 32, 42)
ROW_ALT  = (19, 24, 30)
ROW_NORM = (13, 17, 23)
BORDER   = (48, 54, 61)
WHITE    = (230, 237, 243)
BLUE     = (88, 166, 255)
GREEN    = (63, 185, 80)
ORANGE   = (210, 153, 34)
GREY     = (139, 148, 158)
DIM      = (80, 90, 100)

PAD     = 14
ROW_H   = 52   # taller — two lines of prob text
HDR_H   = 40
DAY_H   = 32
TITLE_H = 56
FOOTER_H= 34

# Column layout: Match | Pred | Models | Market | Edge
COL_W = [260, 80, 270, 270, 200]
COLS  = ["Match", "Pred", "LLM Models", "Prediction Market", "Edge"]

total_w = sum(COL_W) + PAD * 2

def load_font(size, bold=False):
    candidates = ["C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf"]
    bold_c     = ["C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/arialbd.ttf"]
    for path in (bold_c if bold else candidates):
        if os.path.exists(path):
            try: return ImageFont.truetype(path, size)
            except: pass
    return ImageFont.load_default()

font_title  = load_font(19, bold=True)
font_hdr    = load_font(13, bold=True)
font_day    = load_font(12, bold=True)
font_body   = load_font(13)
font_small  = load_font(11)
font_prob   = load_font(11)
font_edge   = load_font(11)
font_footer = load_font(10)

def col_x(ci):
    x = PAD
    for i in range(ci): x += COL_W[i]
    return x

def prob_line(home, draw, away, ph, pd, pa):
    """Render three labelled probability segments into a row, return as formatted string."""
    return f"{home} {ph}%   Draw {pd}%   {away} {pa}%"

def total_h_calc(rows26, rows27):
    return TITLE_H + HDR_H + DAY_H + len(rows26)*ROW_H + DAY_H + len(rows27)*ROW_H + FOOTER_H + 4

total_h = total_h_calc(JUN26, JUN27)
img = Image.new("RGB", (total_w, total_h), BG)
draw = ImageDraw.Draw(img)

def dt(x, y, text, font, color, anchor="lm"):
    draw.text((x, y), text, font=font, fill=color, anchor=anchor)

# Title bar
draw.rectangle([0, 0, total_w, TITLE_H], fill=HDR_BG)
draw.line([0, TITLE_H-1, total_w, TITLE_H-1], fill=(247,129,102), width=2)
dt(PAD, TITLE_H//2, "WC2026 LLM Forecast  ·  Remaining Group Stage Predictions", font_title, WHITE)

# Header row
y = TITLE_H
draw.rectangle([0, y, total_w, y+HDR_H-1], fill=HDR_BG)
draw.line([0, y+HDR_H-1, total_w, y+HDR_H-1], fill=BORDER, width=1)
for ci, col in enumerate(COLS):
    dt(col_x(ci)+8, y+HDR_H//2, col, font_hdr, BLUE)
y += HDR_H

def draw_day(y, label):
    draw.rectangle([0, y, total_w, y+DAY_H-1], fill=DAY_BG)
    draw.line([0, y+DAY_H-1, total_w, y+DAY_H-1], fill=BORDER, width=1)
    dt(PAD, y+DAY_H//2, label, font_day, ORANGE)
    return y+DAY_H

def draw_data_row(y, row, alt):
    home, away, pred, ph_m, pd_m, pa_m, ph_k, pd_k, pa_k, edge = row
    bg = ROW_ALT if alt else ROW_NORM
    draw.rectangle([0, y, total_w, y+ROW_H-1], fill=bg)
    draw.line([0, y+ROW_H-1, total_w, y+ROW_H-1], fill=BORDER, width=1)

    mid_y = y + ROW_H//2
    line1_y = y + ROW_H//2 - 9   # upper line
    line2_y = y + ROW_H//2 + 9   # lower line (prob detail)

    # Match name — centred vertically
    dt(col_x(0)+8, mid_y, f"{home} vs {away}", font_body, WHITE)

    # Prediction score — big, centred
    dt(col_x(1)+8, mid_y, pred, font_hdr, GREEN)

    # LLM Models — line1: win label, line2: draw label
    mx = col_x(2)+8
    dt(mx, line1_y, f"{home} {ph_m}%   Draw {pd_m}%", font_prob, GREY)
    dt(mx, line2_y, f"{away} {pa_m}%", font_prob, GREY)

    # Prediction Market
    kx = col_x(3)+8
    dt(kx, line1_y, f"{home} {ph_k}%   Draw {pd_k}%", font_prob, GREY)
    dt(kx, line2_y, f"{away} {pa_k}%", font_prob, GREY)

    # Edge
    ex = col_x(4)+8
    ec = ORANGE if edge else DIM
    dt(ex, mid_y, edge if edge else "—", font_edge, ec)

    return y + ROW_H

y = draw_day(y, "  JUNE 26")
for i, row in enumerate(JUN26):
    y = draw_data_row(y, row, i%2==1)

y = draw_day(y, "  JUNE 27")
for i, row in enumerate(JUN27):
    y = draw_data_row(y, row, i%2==1)

# Footer
draw.rectangle([0, total_h-FOOTER_H, total_w, total_h], fill=HDR_BG)
dt(PAD, total_h-FOOTER_H//2, "12 LLM models · Anthropic · OpenAI · Google · Perplexity  ·  Bayesian-weighted ensemble probabilities", font_footer, GREY)
dt(total_w-PAD, total_h-FOOTER_H//2, "Prediction market = vig-removed implied probabilities", font_footer, GREY, anchor="rm")

# Column dividers
for ci in range(1, len(COLS)):
    x = col_x(ci)
    draw.line([x, TITLE_H, x, total_h-FOOTER_H], fill=BORDER, width=1)

img.save(OUT_PATH, "PNG")
print(f"Saved: {OUT_PATH}  ({total_w}x{total_h})")
