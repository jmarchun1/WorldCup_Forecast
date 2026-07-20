import json, os, glob
from collections import defaultdict

scored_dir = r"C:\Users\I846720\world-cup-forecasting\results\scored"
forecast_dir = r"C:\Users\I846720\world-cup-forecasting\results\forecasts"

files = glob.glob(os.path.join(scored_dir, "*.json"))
records = []
for f in files:
    with open(f, encoding="utf-8") as fp:
        records.append(json.load(fp))

# All scored records (group stage = before R32 which starts Jun 29)
# South_Africa_Canada = Jun 28 = first R32, but treat Jun 11-27 as group stage
# Actually let's use all scored records since only group stage is scored
print(f"Total scored records: {len(records)}")
matches = set(r["match_id"] for r in records)
print(f"Unique matches scored: {len(matches)}")
models = sorted(set(r["model_short"] for r in records))
print(f"Models: {models}")
print()

# --- PPG by model ---
model_pts = defaultdict(list)
model_brier = defaultdict(list)
model_cost = defaultdict(float)
for r in records:
    m = r["model_short"]
    model_pts[m].append(r["points"])
    model_brier[m].append(r.get("brier_score", None))
    model_cost[m] += r.get("cost_usd", 0)

print("=== PPG by model ===")
model_ppg = {}
for m in models:
    pts = model_pts[m]
    ppg = sum(pts) / len(pts)
    model_ppg[m] = ppg
    brier_scores = [b for b in model_brier[m] if b is not None]
    avg_brier = sum(brier_scores) / len(brier_scores) if brier_scores else None
    brier_str = f"{avg_brier:.4f}" if avg_brier else "N/A"
    print(f"  {m:20s}: {ppg:.3f} PPG  ({sum(pts):3d} pts / {len(pts):2d} matches)  "
          f"Brier {brier_str}  Cost ${model_cost[m]:.2f}")
print()

# --- Consensus (using per-match majority vote result) ---
# Load consensus forecasts for all scored matches
consensus_pts = []
for mid in sorted(matches):
    cf = os.path.join(forecast_dir, mid + "_CONSENSUS.json")
    if not os.path.exists(cf):
        continue
    with open(cf, encoding="utf-8") as fp:
        c = json.load(fp)
    # find actual from any scored record for this match
    actual_recs = [r for r in records if r["match_id"] == mid]
    if not actual_recs:
        continue
    actual_home = actual_recs[0]["actual_home"]
    actual_away = actual_recs[0]["actual_away"]
    ph = c["consensus_home_goals"]
    pa = c["consensus_away_goals"]
    # score
    if ph == actual_home and pa == actual_away:
        pts = 4
    elif (ph - pa) == (actual_home - actual_away):
        pts = 2
    elif (ph > pa) == (actual_home > actual_away) or (ph < pa) == (actual_home < actual_away):
        pts = 1
    elif actual_home == actual_away and ph == pa:
        pts = 2  # draw exact diff
    else:
        pts = 0
    consensus_pts.append(pts)

print(f"=== Consensus ===")
print(f"  Matches with consensus: {len(consensus_pts)}")
print(f"  Total pts: {sum(consensus_pts)}  PPG: {sum(consensus_pts)/len(consensus_pts):.3f}")
print()

# --- Score distribution ---
print("=== Points distribution (all models) ===")
for pts_val in [4, 2, 1, 0]:
    count = sum(1 for r in records if r["points"] == pts_val)
    pct = count / len(records) * 100
    label = {4: "Exact score", 2: "Correct margin", 1: "Correct result", 0: "Wrong"}[pts_val]
    print(f"  {label}: {count:4d} ({pct:.1f}%)")
print()

# --- Actual results distribution ---
actual_outcomes = [r["actual_outcome"] for r in records if "actual_outcome" in r]
# de-dup per match
per_match_outcomes = {}
for r in records:
    if "actual_outcome" in r:
        per_match_outcomes[r["match_id"]] = r["actual_outcome"]
outcome_counts = defaultdict(int)
for v in per_match_outcomes.values():
    outcome_counts[v] += 1
total_m = len(per_match_outcomes)
print(f"=== Match outcomes (actual) ===")
for k, v in sorted(outcome_counts.items(), key=lambda x: -x[1]):
    print(f"  {k}: {v} ({v/total_m*100:.1f}%)")
print()

# --- Predicted draw rate ---
draw_pred = sum(1 for r in records if r.get("predicted_home") == r.get("predicted_away"))
print(f"=== Draw prediction ===")
print(f"  Predicted draws: {draw_pred}/{len(records)} ({draw_pred/len(records)*100:.1f}%)")
draw_actual = sum(1 for r in per_match_outcomes.items() if r[1] == "draw") 
print(f"  Actual draws: {draw_actual}/{total_m} ({draw_actual/total_m*100:.1f}%)")

# How many actual draws were correctly predicted (by any single model)?
draw_match_ids = [mid for mid, o in per_match_outcomes.items() if o == "draw"]
draw_correct_by_model = defaultdict(int)
for r in records:
    if r["match_id"] in draw_match_ids:
        ph, pa = r.get("predicted_home"), r.get("predicted_away")
        if ph is not None and ph == pa:
            draw_correct_by_model[r["model_short"]] += 1
print(f"  Draw correct predictions by model:")
for m, cnt in sorted(draw_correct_by_model.items(), key=lambda x: -x[1]):
    n_draw_matches = len([r for r in records if r["match_id"] in draw_match_ids and r["model_short"] == m])
    print(f"    {m}: {cnt}/{n_draw_matches}")
print()

# --- Goals analysis ---
pred_goals = [(r.get("predicted_home",0) + r.get("predicted_away",0)) for r in records]
actual_goals_per_match = {}
for r in records:
    actual_goals_per_match[r["match_id"]] = r["actual_home"] + r["actual_away"]
avg_pred = sum(pred_goals) / len(pred_goals)
avg_actual = sum(actual_goals_per_match.values()) / len(actual_goals_per_match)
print(f"=== Goals ===")
print(f"  Avg predicted total goals: {avg_pred:.2f}")
print(f"  Avg actual total goals: {avg_actual:.2f}")
print(f"  Undercount ratio: {(avg_actual - avg_pred)/avg_actual*100:.1f}%")
print()

# --- Most common predicted scorelines ---
from collections import Counter
pred_lines = Counter(f"{r.get('predicted_home')}-{r.get('predicted_away')}" for r in records)
print("=== Top predicted scorelines ===")
for line, cnt in pred_lines.most_common(8):
    print(f"  {line}: {cnt} ({cnt/len(records)*100:.1f}%)")
print()

# --- Most common actual scorelines ---
actual_lines_per_match = {}
for r in records:
    actual_lines_per_match[r["match_id"]] = f"{r['actual_home']}-{r['actual_away']}"
actual_line_counts = Counter(actual_lines_per_match.values())
print("=== Top actual scorelines ===")
for line, cnt in actual_line_counts.most_common(8):
    print(f"  {line}: {cnt}")
print()

# --- Cost analysis ---
total_cost = sum(r.get("cost_usd", 0) for r in records)
print(f"=== Cost ===")
print(f"  Total cost all models: ${total_cost:.2f}")
print(f"  Cost per scored record: ${total_cost/len(records):.4f}")
print()
print("  Cost vs PPG:")
for m in sorted(models, key=lambda x: -model_ppg.get(x, 0)):
    print(f"    {m:20s}: PPG {model_ppg[m]:.3f}  cost ${model_cost[m]:.2f}")
