import os, json
from collections import defaultdict
scored_dir = r'C:\Users\I846720\world-cup-forecasting\results\scored'
stats = defaultdict(lambda: {'exact':0, 'gd':0, 'result':0, 'zero':0, 'total':0, 'games':0})
for f in os.listdir(scored_dir):
    if not f.endswith('.json'): continue
    with open(os.path.join(scored_dir, f)) as fh:
        d = json.load(fh)
    m = stats[d['model_short']]
    m['games'] += 1
    m['total'] += (d['points'] or 0)
    bd = d.get('score_breakdown','')
    if bd == 'exact_score': m['exact'] += 1
    elif bd == 'correct_result_exact_gd': m['gd'] += 1
    elif bd == 'correct_result': m['result'] += 1
    else: m['zero'] += 1

print(f"{'Model':<22} {'Pts':>4} {'G':>3} {'Exact':>6} {'GD':>4} {'Result':>7} {'Zero':>5}")
print('-'*55)
for model, s in sorted(stats.items(), key=lambda x: -x[1]['total']):
    print(f"{model:<22} {s['total']:>4} {s['games']:>3} {s['exact']:>6} {s['gd']:>4} {s['result']:>7} {s['zero']:>5}")
