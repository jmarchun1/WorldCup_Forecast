"""Reconcile GoalLab posted scores vs our v4 archive consensus predictions."""
import json, os

arch_dir = 'results/forecasts/archive/20260620-1452'

def safe(s):
    return s.replace(' ','_').replace('&','and').replace("'",'').replace('/','')

# GoalLab results as pasted by user: (home, away, actual_h, actual_a, goallab_pts)
goallab = [
    # MD1
    ('Mexico','South Africa', 2,0, 4),
    ('South Korea','Czech Republic', 2,1, 0),
    ('Canada','Bosnia and Herzegovina', 1,1, 0),
    ('USA','Paraguay', 4,1, 1),
    ('Qatar','Switzerland', 1,1, 0),
    ('Brazil','Morocco', 1,1, 0),
    ('Haiti','Scotland', 0,1, 1),
    ('Australia','Turkey', 2,0, 0),
    ('Germany','Curacao', 7,1, 1),
    ('Netherlands','Japan', 2,2, 0),
    ('Ivory Coast','Ecuador', 1,0, 0),
    ('Sweden','Tunisia', 5,1, 1),
    ('Spain','Cape Verde', 0,0, 0),
    ('Belgium','Egypt', 1,1, 0),
    ('Saudi Arabia','Uruguay', 1,1, 0),
    ('Iran','New Zealand', 2,2, 0),
    ('France','Senegal', 3,1, 1),
    ('Iraq','Norway', 1,4, 1),
    ('Argentina','Algeria', 3,0, 1),
    ('Austria','Jordan', 3,1, 2),
    ('Portugal','DR Congo', 1,1, 0),
    ('England','Croatia', 4,2, 1),
    ('Ghana','Panama', 1,0, 0),
    ('Uzbekistan','Colombia', 1,3, 2),
    # MD2
    ('Czech Republic','South Africa', 1,1, 0),
    ('Switzerland','Bosnia and Herzegovina', 4,1, 1),
    ('Canada','Qatar', 6,0, 1),
    ('Mexico','South Korea', 1,0, 2),
    ('USA','Australia', 2,0, 1),
    ('Scotland','Morocco', 0,1, 0),
    ('Brazil','Haiti', 3,0, 1),
    ('Turkey','Paraguay', 0,1, 0),
    ('Netherlands','Sweden', 5,1, 1),
    ('Germany','Ivory Coast', 2,1, 4),
    ('Ecuador','Curacao', 0,0, 0),
    ('Tunisia','Japan', 0,4, 1),
    ('Spain','Saudi Arabia', 4,0, 1),
    ('Belgium','Iran', 0,0, 0),
    ('Uruguay','Cape Verde', 2,2, 0),
    ('New Zealand','Egypt', 1,3, 1),
    ('Argentina','Austria', 2,0, 4),
    ('France','Iraq', 3,0, 1),
    ('Norway','Senegal', 3,2, 0),
    ('Jordan','Algeria', 1,2, 2),
    ('Portugal','Uzbekistan', 5,0, 1),
    ('England','Ghana', 0,0, 0),
    ('Panama','Croatia', 0,1, 1),
    ('Colombia','DR Congo', 1,0, 1),
    # MD3
    ('Bosnia and Herzegovina','Qatar', 3,1, 1),
    ('Switzerland','Canada', 2,1, 2),
]

# Load archive consensus
cons = {}
for f in os.listdir(arch_dir):
    if not f.endswith('_CONSENSUS.json'):
        continue
    r = json.load(open(os.path.join(arch_dir, f), encoding='utf-8'))
    cons[r['match_id']] = r

print(f'GoalLab total: {sum(p for *_,p in goallab)} pts across {len(goallab)} matches')
print()

print(f"{'Match':<40} {'Pred':>5} {'Act':>5} {'OUR':>4} {'GL':>4}  diff")
print('-'*65)

our_total = 0
gl_total = 0
mismatches = []

for home, away, ah, aa, gl_pts in goallab:
    # Search for matching consensus file
    found_mid = None
    found_rec = None
    for mid, rec in cons.items():
        base = mid[:-11]  # strip _YYYY-MM-DD
        if base == f'{safe(home)}_{safe(away)}' or base == f'{safe(away)}_{safe(home)}':
            found_mid = mid
            found_rec = rec
            break

    if not found_rec:
        print(f"  NOT FOUND: {home} vs {away}")
        continue

    ph = round(found_rec.get('consensus_home_goals') or 0)
    pa = round(found_rec.get('consensus_away_goals') or 0)

    # Swap if stored away/home reversed
    if found_mid[:-11] == f'{safe(away)}_{safe(home)}':
        ph, pa = pa, ph

    pred_out = 'H' if ph>pa else ('D' if ph==pa else 'A')
    act_out  = 'H' if ah>aa else ('D' if ah==aa else 'A')
    our_pts = 4 if (ph==ah and pa==aa) else (1 if pred_out==act_out else 0)

    our_total += our_pts
    gl_total += gl_pts
    diff = our_pts - gl_pts

    flag = ' <== MISMATCH' if diff != 0 else ''
    print(f"{home[:18]+' v '+away[:16]:<40} {ph}-{pa:>1}  {ah}-{aa:>1}  {our_pts:>3}  {gl_pts:>3}{flag}")
    if diff != 0:
        mismatches.append((home, away, ph, pa, ah, aa, our_pts, gl_pts))

print()
print(f'Our calculation: {our_total} pts')
print(f'GoalLab total:   {gl_total} pts')
print(f'Difference:      {our_total - gl_total} pts')
print(f'Mismatches:      {len(mismatches)}')
