import json, os
from collections import defaultdict

SCORED_DIR = r'C:\Users\I846720\world-cup-forecasting\results\scored'

model_acc = defaultdict(lambda: {'pts':0,'games':0,'exact':0,'gd':0,'result':0,'zero':0,'brier_sum':0.0})
per_match = defaultdict(dict)

for fname in sorted(os.listdir(SCORED_DIR)):
    if not fname.endswith('.json'): continue
    with open(os.path.join(SCORED_DIR, fname), encoding='utf-8') as f:
        r = json.load(f)
    m = r.get('model_short','?')
    pts = r.get('points',0) or 0
    bd = r.get('score_breakdown','')
    brier = r.get('brier_score',0.0) or 0.0
    mid = r.get('match_id','')
    pred = f"{r.get('home_goals','-')}-{r.get('away_goals','-')}"
    actual = f"{r.get('actual_home','-')}-{r.get('actual_away','-')}"

    model_acc[m]['pts'] += pts
    model_acc[m]['games'] += 1
    model_acc[m]['brier_sum'] += brier
    if bd == 'exact_score':               model_acc[m]['exact']  += 1
    elif bd == 'correct_result_exact_gd': model_acc[m]['gd']     += 1
    elif bd == 'correct_result':          model_acc[m]['result']  += 1
    else:                                 model_acc[m]['zero']    += 1

    per_match[mid][m] = {'pts': pts, 'pred': pred, 'actual': actual, 'bd': bd}

ranked = sorted(model_acc.items(), key=lambda x: -x[1]['pts'])
n_matches = len(per_match)

print(f"\n=== MODEL LEADERBOARD ({n_matches} matches played) ===\n")
print(f"{'Model':<18} {'Pts':>4} {'P/G':>5} {'Exact':>5} {'+GD':>4} {'Res':>4} {'Zero':>5} {'Brier':>7}")
print('-'*62)
for model, m in ranked:
    g = m['games']
    brier_avg = m['brier_sum']/g if g else 0
    ppg = m['pts']/g if g else 0
    print(f"{model:<18} {m['pts']:>4} {ppg:>5.2f} {m['exact']:>5} {m['gd']:>4} {m['result']:>4} {m['zero']:>5} {brier_avg:>7.4f}")

# exact score breakdown across all matches
print(f"\n=== EXACT SCORES (4 pts) ===")
for mid, models in sorted(per_match.items()):
    exacters = [mod for mod, d in models.items() if d['bd'] == 'exact_score']
    if exacters:
        sample = list(models.values())[0]
        print(f"  {mid:40s} actual={sample['actual']}  models={exacters}")

print(f"\n=== ZERO POINT RATE BY MODEL ===")
for model, m in ranked:
    g = m['games']
    zero_pct = 100*m['zero']/g if g else 0
    print(f"  {model:<18} zero={m['zero']:>2}/{g}  ({zero_pct:.0f}%)")

# contamination check — how many sonar/sonarpro exact scores are from played matches?
print(f"\n=== SONAR EXACT SCORES (contamination check) ===")
for mid, models in sorted(per_match.items()):
    for mod in ('sonar','sonarpro'):
        if mod in models and models[mod]['bd'] == 'exact_score':
            print(f"  {mod:<10} {mid:40s} pred={models[mod]['pred']} actual={models[mod]['actual']}")
