"""
usa_win_prob.py — Ask each model to estimate USA's probability of winning WC2026.
"""
import json, os, re, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from forecast import _call_model

with open(os.path.join(os.path.dirname(__file__), 'config.json'), encoding='utf-8') as f:
    config = json.load(f)

# Build model cfg list from config
all_models = {m['short']: m for m in config['models']}

PROMPT = """You are a probabilistic football forecaster. Estimate the probability that the USA wins the 2026 FIFA World Cup.

## Tournament context
- 48-team format: top 2 from each of 12 groups + 8 best third-placed = 32 teams in R32
- USA finished 1st in Group D: 6pts, +4 GD, 8 goals (beat Paraguay 4-1, beat Australia 2-0, lost to Turkey 2-3)
- USA is the host nation with home crowd advantage throughout the tournament
- Tournament requires winning 4 knockout matches: R32, R16, QF, SF, Final

## Squad context
- Key players: Pulisic (captain), Reyna, Weah, McKennie, Turner (GK)
- Strong but not elite vs top-8 nations; best WC result was 3rd place in 1930
- Home crowd advantage historically worth ~10-15% uplift in win probability per match

## Competition landscape
- Top contenders: France, Brazil, England, Spain, Germany, Argentina (all ~8-15% win probability each)
- USA as host: market implies ~10-14% tournament win probability
- Likely R32 opponent: a 3rd-place group finisher (beatable)
- R16 likely draws from Groups E/F — could face Portugal, Netherlands, Mexico

Provide your estimate as JSON only, no other text:
{
  "win_probability": <float 0.0-1.0>,
  "low_case": <float, pessimistic>,
  "high_case": <float, optimistic>,
  "reasoning": "<2-3 sentences>",
  "most_likely_path": "<R32 -> R16 -> QF -> SF -> Final opponents>",
  "biggest_threat": "<team name and one-line reason>"
}"""

TARGET_SHORTS = ['sonnet', 'opus', 'gem25flash', 'gem25pro', 'gpt5', 'gpt54', 'sonarpro']

results = []
for short in TARGET_SHORTS:
    model_cfg = all_models.get(short)
    if not model_cfg:
        print(f"{short}: not found in config, skipping")
        continue
    try:
        resp = _call_model(model_cfg, PROMPT, config)
        raw = resp.get('raw_response', '')
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        if m:
            d = json.loads(m.group())
            d['model'] = short
            results.append(d)
            wp = d.get('win_probability', 0) * 100
            lo = d.get('low_case', 0) * 100
            hi = d.get('high_case', 0) * 100
            print(f"{short}: {wp:.1f}%  (range {lo:.1f}%-{hi:.1f}%)")
            print(f"  Path:   {d.get('most_likely_path','')}")
            print(f"  Threat: {d.get('biggest_threat','')}")
            print(f"  Why:    {d.get('reasoning','')[:140]}")
            print()
        else:
            print(f"{short}: could not parse JSON from: {raw[:300]}")
    except Exception as e:
        print(f"{short}: ERROR {e}")

if results:
    avg = sum(r.get('win_probability', 0) for r in results) / len(results)
    lo_avg  = sum(r.get('low_case', 0) for r in results) / len(results)
    hi_avg  = sum(r.get('high_case', 0) for r in results) / len(results)
    print("=" * 50)
    print(f"ENSEMBLE ESTIMATE: {avg*100:.1f}%  (range {lo_avg*100:.1f}%-{hi_avg*100:.1f}%)")
    threats = [r.get('biggest_threat','') for r in results if r.get('biggest_threat')]
    from collections import Counter
    threat_counts = Counter(t.split()[0] for t in threats if t)
    print(f"Most cited threats: {threat_counts.most_common(3)}")
