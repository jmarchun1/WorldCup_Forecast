"""
backtest_v5.py — Backtest v5 improvement ideas against 50 completed matches.

Ideas tested:
  A) Brier-weighted ensemble (drop bottom models, weight by recent Brier)
  B) Extremize probabilities before averaging (alpha tuning)
  C) Draw probability floor (boost draws when p_home - p_away < threshold)
  D) Drop weak models (gpt5mini, haiku) from consensus
  E) Combined: A + B + C (best composite)

Baseline: v4 consensus (round(consensus_home_goals), round(consensus_away_goals))

Scoring: 4=exact, 2=correct result + exact GD (non-draw), 1=correct result or correct draw, 0=wrong
"""

import json, os, math, sys
sys.stdout.reconfigure(encoding='utf-8')
from collections import defaultdict

ARCH_DIR = 'results/forecasts/archive/20260620-1452'
SCORED_DIR = 'results/scored'
WEB_SEARCH_MODELS = {'sonar', 'sonarpro'}
WEAK_MODELS = {'gpt5mini', 'haiku'}

# ─── helpers ────────────────────────────────────────────────────────────────

def fantasy_pts(ph, pa, ah, aa):
    if ph == ah and pa == aa:
        return 4, 'exact'
    pr = result(ph, pa); ar = result(ah, aa)
    if pr != ar:
        return 0, 'wrong'
    if ar != 'draw' and abs(ph - pa) == abs(ah - aa):
        return 2, 'gd'
    if ar == 'draw':
        return 1, 'draw'
    return 1, 'result'

def result(h, a):
    return 'home' if h > a else ('away' if a > h else 'draw')

def extremize(p_vec, alpha):
    """Extremize a probability vector: p' = p^alpha / sum(p^alpha)."""
    powered = [p ** alpha for p in p_vec]
    s = sum(powered)
    return [p / s for p in powered]

def softmax_weights(briers):
    """Inverse-Brier softmax weights (lower Brier = higher weight)."""
    inv = [1.0 / max(b, 0.001) for b in briers]
    s = sum(inv)
    return [w / s for w in inv]

# ─── load all per-model forecasts from archive ──────────────────────────────

def load_archive_forecasts():
    """Returns dict: match_id -> list of per-model forecast dicts."""
    forecasts = defaultdict(list)
    for f in os.listdir(ARCH_DIR):
        if f.endswith('_CONSENSUS.json') or not f.endswith('.json'):
            continue
        rec = json.load(open(os.path.join(ARCH_DIR, f), encoding='utf-8'))
        mid = rec.get('match_id')
        if not mid:
            continue
        # Skip web-search models when forecast_date > match_date
        mdate = mid[-10:] if len(mid) >= 10 else ''
        fdate = rec.get('forecast_date', '')
        if rec.get('model_short') in WEB_SEARCH_MODELS and fdate and mdate and fdate > mdate:
            continue
        if rec.get('home_goals') is None or rec.get('away_goals') is None:
            continue
        if rec.get('error') and rec.get('error') != 'missing horizons':
            continue
        forecasts[mid].append(rec)
    return forecasts

def load_actuals():
    """Returns dict: match_id -> (actual_home, actual_away) from scored files."""
    actuals = {}
    for f in os.listdir(SCORED_DIR):
        if not f.endswith('.json'):
            continue
        rec = json.load(open(os.path.join(SCORED_DIR, f), encoding='utf-8'))
        mid = rec.get('match_id')
        if mid and 'actual_home' in rec:
            actuals[mid] = (rec['actual_home'], rec['actual_away'])
    return actuals

def load_v4_consensus():
    """Returns dict: match_id -> (pred_home, pred_away) from v4 CONSENSUS files."""
    cons = {}
    for f in os.listdir(ARCH_DIR):
        if not f.endswith('_CONSENSUS.json'):
            continue
        rec = json.load(open(os.path.join(ARCH_DIR, f), encoding='utf-8'))
        mid = rec.get('match_id')
        if mid and rec.get('consensus_home_goals') is not None:
            cons[mid] = (round(rec['consensus_home_goals']), round(rec['consensus_away_goals']))
    return cons

# ─── compute consensus variants ─────────────────────────────────────────────

def consensus_from_models(models, drop_weak=False, alpha=None, draw_boost=None):
    """
    Build a consensus prediction from a list of per-model forecast dicts.
    Returns (pred_home, pred_away, avg_draw_prob)
    """
    recs = [m for m in models if not (drop_weak and m.get('model_short') in WEAK_MODELS)]
    if not recs:
        return None

    probs_h = [r.get('home_win_prob') or 0.33 for r in recs]
    probs_d = [r.get('draw_prob') or 0.33 for r in recs]
    probs_a = [r.get('away_win_prob') or 0.33 for r in recs]

    # Extremize each model's probs before averaging
    if alpha is not None:
        ext = [extremize([probs_h[i], probs_d[i], probs_a[i]], alpha) for i in range(len(recs))]
        probs_h = [e[0] for e in ext]
        probs_d = [e[1] for e in ext]
        probs_a = [e[2] for e in ext]

    avg_h = sum(probs_h) / len(probs_h)
    avg_d = sum(probs_d) / len(probs_d)
    avg_a = sum(probs_a) / len(probs_a)

    # Draw boost: if match is close (home - away margin < threshold), raise draw prob
    if draw_boost is not None:
        threshold, boost = draw_boost
        if abs(avg_h - avg_a) < threshold:
            avg_d = min(avg_d + boost, 0.6)
            total = avg_h + avg_d + avg_a
            avg_h /= total; avg_d /= total; avg_a /= total

    # Consensus scoreline: average goals from all model predictions
    avg_gh = sum(r.get('home_goals', 0) for r in recs) / len(recs)
    avg_ga = sum(r.get('away_goals', 0) for r in recs) / len(recs)

    # Adjust scoreline for draw-boosted matches: if draw is now most likely, force tie
    win_outcome = max([('home', avg_h), ('draw', avg_d), ('away', avg_a)], key=lambda x: x[1])[0]
    ph = round(avg_gh)
    pa = round(avg_ga)
    # Reconcile scoreline with probability winner
    if win_outcome == 'draw' and ph != pa:
        # Force closest draw
        mid_g = round((avg_gh + avg_ga) / 2)
        ph = pa = mid_g
    elif win_outcome == 'home' and ph <= pa:
        ph = pa + 1
    elif win_outcome == 'away' and pa <= ph:
        pa = ph + 1

    return ph, pa, avg_d

def consensus_brier_weighted(models, scored_by_model, alpha=None, draw_boost=None, drop_weak=False):
    """
    Build consensus weighting each model by its recent Brier score (rolling last 10).
    Returns (pred_home, pred_away, avg_draw_prob) or None.
    """
    recs = [m for m in models if not (drop_weak and m.get('model_short') in WEAK_MODELS)]
    if not recs:
        return None

    weights = []
    for r in recs:
        ms = r.get('model_short')
        recent = scored_by_model.get(ms, [])[-10:]  # last 10 matches
        if recent:
            avg_brier = sum(s['brier_score'] for s in recent) / len(recent)
        else:
            avg_brier = 0.2  # default
        weights.append(1.0 / max(avg_brier, 0.001))

    sw = sum(weights)
    weights = [w / sw for w in weights]

    probs_h = [r.get('home_win_prob') or 0.33 for r in recs]
    probs_d = [r.get('draw_prob') or 0.33 for r in recs]
    probs_a = [r.get('away_win_prob') or 0.33 for r in recs]

    if alpha is not None:
        ext = [extremize([probs_h[i], probs_d[i], probs_a[i]], alpha) for i in range(len(recs))]
        probs_h = [e[0] for e in ext]
        probs_d = [e[1] for e in ext]
        probs_a = [e[2] for e in ext]

    avg_h = sum(w * probs_h[i] for i, w in enumerate(weights))
    avg_d = sum(w * probs_d[i] for i, w in enumerate(weights))
    avg_a = sum(w * probs_a[i] for i, w in enumerate(weights))

    if draw_boost is not None:
        threshold, boost = draw_boost
        if abs(avg_h - avg_a) < threshold:
            avg_d = min(avg_d + boost, 0.6)
            total = avg_h + avg_d + avg_a
            avg_h /= total; avg_d /= total; avg_a /= total

    avg_gh = sum(weights[i] * recs[i].get('home_goals', 0) for i in range(len(recs)))
    avg_ga = sum(weights[i] * recs[i].get('away_goals', 0) for i in range(len(recs)))

    win_outcome = max([('home', avg_h), ('draw', avg_d), ('away', avg_a)], key=lambda x: x[1])[0]
    ph = round(avg_gh)
    pa = round(avg_ga)
    if win_outcome == 'draw' and ph != pa:
        mid_g = round((avg_gh + avg_ga) / 2)
        ph = pa = mid_g
    elif win_outcome == 'home' and ph <= pa:
        ph = pa + 1
    elif win_outcome == 'away' and pa <= ph:
        pa = ph + 1

    return ph, pa, avg_d

# ─── main backtest ───────────────────────────────────────────────────────────

def main():
    print("Loading data...")
    arch_forecasts = load_archive_forecasts()
    actuals = load_actuals()
    v4_consensus = load_v4_consensus()

    # Build scored_by_model lookup: model_short -> list of scored records (sorted by match date)
    scored_by_model = defaultdict(list)
    for f in os.listdir(SCORED_DIR):
        if not f.endswith('.json'):
            continue
        rec = json.load(open(os.path.join(SCORED_DIR, f), encoding='utf-8'))
        ms = rec.get('model_short')
        if ms and 'brier_score' in rec:
            scored_by_model[ms].append(rec)
    for ms in scored_by_model:
        scored_by_model[ms].sort(key=lambda r: r['match_id'])

    # Only backtest on matches that have both archive forecasts AND actuals
    match_ids = sorted(set(arch_forecasts.keys()) & set(actuals.keys()))
    print(f"Backtest matches: {len(match_ids)}\n")

    configs = {
        'v4_baseline':   dict(method='simple'),
        'D_drop_weak':   dict(method='simple', drop_weak=True),
        'B_extremize65': dict(method='simple', alpha=0.65),
        'B_extremize70': dict(method='simple', alpha=0.70),
        'B_extremize75': dict(method='simple', alpha=0.75),
        'C_draw_boost':  dict(method='simple', draw_boost=(0.20, 0.08)),
        'C_draw_boost2': dict(method='simple', draw_boost=(0.15, 0.10)),
        'A_brier_wt':    dict(method='brier'),
        'A_brier_nodrop':dict(method='brier', drop_weak=False),
        'E_combined':    dict(method='brier', alpha=0.70, draw_boost=(0.20, 0.08), drop_weak=True),
        'E_combined2':   dict(method='brier', alpha=0.65, draw_boost=(0.15, 0.10), drop_weak=True),
    }

    results = {k: {'pts': 0, 'exact': 0, 'gd': 0, 'result': 0, 'draw': 0, 'wrong': 0, 'n': 0}
               for k in configs}

    per_match_detail = defaultdict(dict)

    for mid in match_ids:
        ah, aa = actuals[mid]
        models = arch_forecasts[mid]

        # v4 baseline from CONSENSUS file
        v4_ph, v4_pa = v4_consensus.get(mid, (None, None))
        if v4_ph is None:
            continue

        v4_pts, v4_bd = fantasy_pts(v4_ph, v4_pa, ah, aa)
        results['v4_baseline']['pts'] += v4_pts
        results['v4_baseline'][v4_bd] += 1
        results['v4_baseline']['n'] += 1
        per_match_detail[mid]['v4_baseline'] = (v4_ph, v4_pa, v4_pts)

        for name, cfg in configs.items():
            if name == 'v4_baseline':
                continue
            method = cfg.get('method', 'simple')
            alpha = cfg.get('alpha')
            draw_boost = cfg.get('draw_boost')
            drop_weak = cfg.get('drop_weak', True)  # default drop weak

            if method == 'brier':
                out = consensus_brier_weighted(models, scored_by_model,
                                               alpha=alpha, draw_boost=draw_boost, drop_weak=drop_weak)
            else:
                out = consensus_from_models(models, drop_weak=drop_weak,
                                            alpha=alpha, draw_boost=draw_boost)

            if out is None:
                continue
            ph, pa, avg_d = out
            pts, bd = fantasy_pts(ph, pa, ah, aa)
            results[name]['pts'] += pts
            results[name][bd] += 1
            results[name]['n'] += 1
            per_match_detail[mid][name] = (ph, pa, pts)

    # ─── print summary ───────────────────────────────────────────────────────
    n_ref = results['v4_baseline']['n']
    print(f"{'Config':<20} {'Pts':>5} {'P/G':>6} {'dPts':>6} {'exact':>6} {'gd':>5} {'res':>5} {'drw':>5} {'wrg':>5}")
    print('─' * 75)
    v4_pts = results['v4_baseline']['pts']

    order = sorted(results.items(), key=lambda x: -x[1]['pts'])
    for name, r in order:
        n = r['n']
        if n == 0:
            continue
        ppg = r['pts'] / n
        delta = r['pts'] - v4_pts
        print(f"{name:<20} {r['pts']:>5}  {ppg:>5.3f}  {delta:>+6}   {r['exact']:>4}  {r['gd']:>4}  {r['result']:>4}  {r['draw']:>4}  {r['wrong']:>4}")

    print()
    print("── Draw calibration check ──")
    draw_rate_actual = sum(1 for mid in match_ids if actuals[mid][0] == actuals[mid][1]) / len(match_ids)
    v4_draw_pred = sum(1 for mid in match_ids
                       if mid in v4_consensus and v4_consensus[mid][0] == v4_consensus[mid][1]) / len(match_ids)
    print(f"Actual draw rate:   {draw_rate_actual:.1%}")
    print(f"v4 draws predicted: {v4_draw_pred:.1%}")

    print()
    print("── Per-model Brier scores (avg across completed matches) ──")
    model_briers = {}
    for ms, recs in scored_by_model.items():
        match_recs = [r for r in recs if r['match_id'] in match_ids]
        if match_recs:
            model_briers[ms] = sum(r['brier_score'] for r in match_recs) / len(match_recs)
    for ms, b in sorted(model_briers.items(), key=lambda x: x[1]):
        tag = ' ← weak' if ms in WEAK_MODELS else ''
        print(f"  {ms:<20} {b:.4f}{tag}")

    # ─── best variant detail ─────────────────────────────────────────────────
    best_name = max((k for k in results if k != 'v4_baseline'), key=lambda k: results[k]['pts'])
    print(f"\n── Matches where {best_name} differs from v4_baseline ──")
    print(f"{'Match':<45} {'v4':>8}  {'best':>8}  {'actual':>7}  {'v4p':>4}  {'bp':>4}")
    for mid in match_ids:
        if mid not in per_match_detail:
            continue
        v4d = per_match_detail[mid].get('v4_baseline')
        bd = per_match_detail[mid].get(best_name)
        if v4d and bd and (v4d[0] != bd[0] or v4d[1] != bd[1]):
            ah, aa = actuals[mid]
            print(f"{mid:<45} {v4d[0]}-{v4d[1]:>1}  {bd[0]}-{bd[1]:>1}  {ah}-{aa}  {v4d[2]:>4}  {bd[2]:>4}")

if __name__ == '__main__':
    main()
