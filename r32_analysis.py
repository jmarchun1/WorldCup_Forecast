"""R32 analysis — correct model short names and match IDs."""
import json
import os

BASE_DIR = "C:/Users/I846720/world-cup-forecasting"
SCORED_DIR = os.path.join(BASE_DIR, "results", "scored")
FORECASTS_DIR = os.path.join(BASE_DIR, "results", "forecasts")

# R32 match IDs as they actually appear in scored files
R32_IDS = [
    "South_Africa_Canada_2026-06-28",
    "Germany_Paraguay_2026-06-29",
    "Brazil_Japan_2026-06-29",
    "Netherlands_Morocco_2026-06-29",
    "Netherlands_Morocco_2026-06-30",
    "France_Sweden_2026-06-30",
    "Ivory_Coast_Norway_2026-06-30",
    "Mexico_Ecuador_2026-07-01",
]

CLEAN_MODELS = ["opus", "sonnet", "haiku", "gpt5", "gpt5mini", "gem25flash", "gem25flashlite", "gem25pro", "CONSENSUS"]

def load_scored():
    rows = []
    for f in os.listdir(SCORED_DIR):
        if not f.endswith(".json"):
            continue
        with open(os.path.join(SCORED_DIR, f)) as fp:
            try:
                rows.append(json.load(fp))
            except Exception:
                pass
    return rows

def main():
    all_scored = load_scored()

    by_match = {}
    for r in all_scored:
        mid = r.get("match_id", "")
        if mid in R32_IDS:
            by_match.setdefault(mid, []).append(r)

    print("=== R32 MATCH-BY-MATCH ANALYSIS ===\n")

    model_totals = {}
    completed = []

    for mid in R32_IDS:
        rows = by_match.get(mid, [])
        if not rows:
            print(f"  {mid}: NO SCORED DATA")
            continue

        completed.append(mid)
        actual_h = rows[0].get("actual_home", "?")
        actual_a = rows[0].get("actual_away", "?")
        print(f"{mid}  (actual {actual_h}-{actual_a})")

        model_rows = {r.get("model_short", ""): r for r in rows}
        for model in CLEAN_MODELS:
            row = model_rows.get(model)
            if not row:
                print(f"    {model:20s} - no data")
                continue
            ph = row.get("predicted_home", "?")
            pa = row.get("predicted_away", "?")
            pts = row.get("points", 0) or 0
            dir_ok = row.get("directional_correct", 0)
            model_totals.setdefault(model, []).append(pts)
            note = " <-- DRAW HIT" if (ph == pa and actual_h == actual_a) else ""
            note2 = " <-- DRAW MISSED" if (ph != pa and actual_h == actual_a) else ""
            print(f"    {model:20s}  pred={ph}-{pa}  pts={pts}  dir={dir_ok}{note}{note2}")
        print()

    print("=== MODEL PPG ON R32 ===\n")
    for model in CLEAN_MODELS:
        pts_list = model_totals.get(model, [])
        if not pts_list:
            print(f"  {model:20s}  no data")
            continue
        avg = sum(pts_list) / len(pts_list)
        total = sum(pts_list)
        print(f"  {model:20s}  PPG={avg:.3f}  total={total}  n={len(pts_list)}")

    print("\n=== DRAW BLINDNESS CHECK ===\n")
    draw_matches = [mid for mid in completed if by_match[mid][0].get("actual_home") == by_match[mid][0].get("actual_away")]
    if not draw_matches:
        print("  No draws yet in completed R32 matches.")
    for mid in draw_matches:
        rows = by_match[mid]
        model_rows = {r.get("model_short", ""): r for r in rows}
        draw_preds = sum(1 for m in CLEAN_MODELS if model_rows.get(m) and model_rows[m].get("predicted_home") == model_rows[m].get("predicted_away"))
        total_models = sum(1 for m in CLEAN_MODELS if model_rows.get(m))
        actual_h = rows[0].get("actual_home")
        actual_a = rows[0].get("actual_away")
        print(f"  DRAW: {mid} {actual_h}-{actual_a} -> {draw_preds}/{total_models} models predicted draw")
        for m in CLEAN_MODELS:
            r = model_rows.get(m)
            if r:
                print(f"    {m:20s}  pred={r.get('predicted_home')}-{r.get('predicted_away')}  pts={r.get('points',0)}")

if __name__ == "__main__":
    main()
