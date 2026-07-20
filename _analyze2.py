import json, os
from collections import defaultdict

BASE = r'C:\Users\I846720\world-cup-forecasting\results'
SCORED_DIR = os.path.join(BASE, 'scored')
CONSENSUS_DIR = os.path.join(BASE, 'forecasts')

# Load consensus files
consensus = {}
for fname in os.listdir(CONSENSUS_DIR):
    if fname.endswith('_CONSENSUS.json'):
        with open(os.path.join(CONSENSUS_DIR, fname), encoding='utf-8') as f:
            rec = json.load(f)
        consensus[rec.get('match_id','')] = rec

# Load scored files, build per-match actual results and per-model scores
actuals = {}  # match_id -> {home, away}
model_scores = defaultdict(lambda: defaultdict(dict))  # match_id -> model -> scored rec

for fname in sorted(os.listdir(SCORED_DIR)):
    if not fname.endswith('.json'): continue
    with open(os.path.join(SCORED_DIR, fname), encoding='utf-8') as f:
        r = json.load(f)
    mid = r.get('match_id','')
    model = r.get('model_short','')
    actuals[mid] = {'home': r.get('actual_home'), 'away': r.get('actual_away')}
    model_scores[mid][model] = r

print(f"Played matches: {len(actuals)}\n")

# Consensus prediction vs actual for each match
print("=== CONSENSUS PREDICTIONS vs ACTUAL ===\n")
pts_by_scoring = {'exact_score':0,'correct_result_exact_gd':0,'correct_result':0,'wrong':0}
total_pts = 0
match_detail = []

for mid in sorted(actuals.keys()):
    actual = actuals[mid]
    ah, aa = actual['home'], actual['away']
    if ah is None: continue

    cons = consensus.get(mid, {})
    ch = cons.get('consensus_home_goals')
    ca = cons.get('consensus_away_goals')

    if ch is None or ca is None:
        result = 'NO_CONSENSUS'
        pts = 0
        bd = 'no_consensus'
    else:
        ch, ca = int(ch), int(ca)
        ah, aa = int(ah), int(aa)
        if ch == ah and ca == aa:
            pts, bd = 4, 'exact_score'
        elif (ch-ca) == (ah-aa):
            pts, bd = 2, 'correct_result_exact_gd'
        elif (ch > ca and ah > aa) or (ch < ca and ah < aa) or (ch == ca and ah == aa):
            pts, bd = 1, 'correct_result'
        else:
            pts, bd = 0, 'wrong'

    total_pts += pts
    if bd in pts_by_scoring:
        pts_by_scoring[bd] += 1

    # What did the BEST model score on this match?
    best_model_pts = max((v.get('points',0) or 0 for v in model_scores[mid].values()), default=0)
    # What did the MAJORITY of models score?
    all_pts = [v.get('points',0) or 0 for v in model_scores[mid].values()
               if v.get('model_short') not in ('sonar','sonarpro')]
    modal_pts = max(set(all_pts), key=all_pts.count) if all_pts else 0

    match_detail.append({
        'mid': mid, 'actual': f"{ah}-{aa}",
        'consensus': f"{ch}-{ca}" if ch is not None else '?-?',
        'pts': pts, 'bd': bd,
        'best_pts': best_model_pts,
        'modal_pts': modal_pts,
        'left_on_table': best_model_pts - pts,
    })

ppg = total_pts / len(match_detail) if match_detail else 0
print(f"Consensus P/G: {ppg:.2f}  Total pts: {total_pts}  over {len(match_detail)} matches\n")
print(f"  Exact:          {pts_by_scoring['exact_score']:>3}")
print(f"  Correct+GD:     {pts_by_scoring['correct_result_exact_gd']:>3}")
print(f"  Correct result: {pts_by_scoring['correct_result']:>3}")
print(f"  Wrong:          {pts_by_scoring['wrong']:>3}")

# Missed opportunities — matches where consensus was wrong but models got it
print(f"\n=== MISSED OPPORTUNITIES (consensus wrong, models did better) ===\n")
missed = [m for m in match_detail if m['left_on_table'] > 0]
missed.sort(key=lambda x: -x['left_on_table'])
for m in missed:
    # which models got it right?
    mid = m['mid']
    right_models = [mod for mod, d in model_scores[mid].items()
                    if (d.get('points',0) or 0) > m['pts']
                    and mod not in ('sonar','sonarpro')]
    print(f"  {mid[-30:]:30s}  actual={m['actual']}  cons={m['consensus']}({m['pts']}pts)  "
          f"best={m['best_pts']}pts  models={right_models[:4]}")

print(f"\n=== CONSENSUS EXACT SCORES ===\n")
for m in match_detail:
    if m['bd'] == 'exact_score':
        print(f"  {m['mid']:45s}  {m['consensus']} OK")

# How does consensus P/G compare to individual models?
print(f"\n=== CONSENSUS vs MODELS P/G COMPARISON ===\n")
model_ppg = {}
all_mids = list(actuals.keys())
for mid in all_mids:
    for model, d in model_scores[mid].items():
        if model in ('sonar','sonarpro'): continue
        if model not in model_ppg:
            model_ppg[model] = {'pts':0,'g':0}
        model_ppg[model]['pts'] += d.get('points',0) or 0
        model_ppg[model]['g'] += 1

print(f"  {'CONSENSUS':<18} {ppg:.2f} P/G  ({total_pts} pts / {len(match_detail)} games)")
for model, d in sorted(model_ppg.items(), key=lambda x: -(x[1]['pts']/x[1]['g'] if x[1]['g'] else 0)):
    if d['g'] >= 20:
        print(f"  {model:<18} {d['pts']/d['g']:.2f} P/G  ({d['pts']} pts / {d['g']} games)")
