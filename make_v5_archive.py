"""
make_v5_archive.py — Recompute consensus from v4 per-model forecasts applying v5 improvements:
  - Draw override: if avg_draw_prob >= 0.35, force draw scoreline

Reads per-model forecasts from v4 archive, applies v5 consensus logic,
writes new CONSENSUS.json files to a v5 archive directory.
Copies per-model forecast files as-is (unchanged).
"""
import json, os, shutil, statistics
from collections import Counter
from datetime import datetime

V4_ARCH = 'results/forecasts/archive/20260620-1452'
STAMP = datetime.now().strftime('%Y%m%d-%H%M')
V5_ARCH = f'results/forecasts/archive/{STAMP}'
DRAW_THRESH = 0.35
WEB_SEARCH_MODELS = {'sonar', 'sonarpro'}

os.makedirs(V5_ARCH, exist_ok=True)

# Group per-model forecasts by match_id
from collections import defaultdict
forecasts_by_match = defaultdict(list)
for f in os.listdir(V4_ARCH):
    if f.endswith('_CONSENSUS.json') or not f.endswith('.json'):
        continue
    rec = json.load(open(os.path.join(V4_ARCH, f), encoding='utf-8'))
    mid = rec.get('match_id')
    if not mid:
        continue
    # Copy file to v5 archive unchanged
    shutil.copy(os.path.join(V4_ARCH, f), os.path.join(V5_ARCH, f))
    # Skip web-search models if forecast was after match
    mdate = mid[-10:] if len(mid) >= 10 else ''
    fdate = rec.get('forecast_date', '')
    if rec.get('model_short') in WEB_SEARCH_MODELS and fdate and mdate and fdate > mdate:
        continue
    if rec.get('home_goals') is None or rec.get('away_goals') is None:
        continue
    if rec.get('error') and rec.get('error') != 'missing horizons':
        continue
    forecasts_by_match[mid].append(rec)

# Load v4 CONSENSUS files for odds/meta fields
v4_cons_meta = {}
for f in os.listdir(V4_ARCH):
    if not f.endswith('_CONSENSUS.json'):
        continue
    rec = json.load(open(os.path.join(V4_ARCH, f), encoding='utf-8'))
    mid = rec.get('match_id')
    if mid:
        v4_cons_meta[mid] = rec

overrides = 0
total = 0

for mid, models in sorted(forecasts_by_match.items()):
    v4_meta = v4_cons_meta.get(mid, {})

    home_goals_list = [r['home_goals'] for r in models]
    away_goals_list = [r['away_goals'] for r in models]
    hw_list = [r.get('home_win_prob') or 0.33 for r in models]
    dp_list = [r.get('draw_prob') or 0.33 for r in models]
    aw_list = [r.get('away_win_prob') or 0.33 for r in models]

    avg_hw = statistics.mean(hw_list)
    avg_dp = statistics.mean(dp_list)
    avg_aw = statistics.mean(aw_list)

    # Mode scoreline (same as v4)
    scoreline_counts = Counter(zip(home_goals_list, away_goals_list))
    top_count = scoreline_counts.most_common(1)[0][1]
    top_scorelines = [s for s, c in scoreline_counts.items() if c == top_count]
    if len(top_scorelines) == 1:
        mode_home, mode_away = top_scorelines[0]
    else:
        if avg_hw > avg_aw:
            top_scorelines.sort(key=lambda s: s[0] - s[1], reverse=True)
        else:
            top_scorelines.sort(key=lambda s: s[1] - s[0], reverse=True)
        mode_home, mode_away = top_scorelines[0]

    consensus_home = mode_home
    consensus_away = mode_away
    draw_override_applied = False

    # v5 draw override
    if avg_dp >= DRAW_THRESH and consensus_home != consensus_away:
        all_goals = home_goals_list + away_goals_list
        tie_g = round(statistics.mean(all_goals) / 2) if all_goals else 1
        print(f"  DRAW OVERRIDE: {mid}  {consensus_home}-{consensus_away} -> {tie_g}-{tie_g}  (dp={avg_dp:.2f})")
        consensus_home = tie_g
        consensus_away = tie_g
        draw_override_applied = True
        overrides += 1

    # Preserve EV/odds fields from v4
    consensus = {
        "match_id": mid,
        "version": "v5",
        "version_notes": "v5: draw override — predict draw when avg_draw_prob >= 0.35 (backtest: +4pts/+0.08 P/G on 50 matches vs v4 baseline). Per-model forecasts unchanged from v4 archive 20260620-1452.",
        "forecast_date": v4_meta.get("forecast_date", "2026-06-24"),
        "match_date": v4_meta.get("match_date", mid[-10:]),
        "home": v4_meta.get("home", ""),
        "away": v4_meta.get("away", ""),
        "models_included": len(models),
        "models_contaminated": v4_meta.get("models_contaminated", 0),
        "consensus_home_goals": consensus_home,
        "consensus_away_goals": consensus_away,
        "scoreline_votes": {f"{h}-{a}": c for (h, a), c in scoreline_counts.most_common()},
        "avg_home_win_prob": round(avg_hw, 4),
        "avg_draw_prob": round(avg_dp, 4),
        "avg_away_win_prob": round(avg_aw, 4),
        "ev_home_win": v4_meta.get("ev_home_win"),
        "ev_draw": v4_meta.get("ev_draw"),
        "ev_away_win": v4_meta.get("ev_away_win"),
        "value_bets": v4_meta.get("value_bets", []),
        "implied_home": v4_meta.get("implied_home"),
        "implied_draw": v4_meta.get("implied_draw"),
        "implied_away": v4_meta.get("implied_away"),
        "v5_draw_override": draw_override_applied,
    }

    out_path = os.path.join(V5_ARCH, f"{mid}_CONSENSUS.json")
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(consensus, f, indent=2, ensure_ascii=False)
    total += 1

print(f"\nv5 archive created: {V5_ARCH}")
print(f"Total matches: {total}  |  Draw overrides applied: {overrides}")
print(f"\nUpdate memory: stamp = {STAMP}")
