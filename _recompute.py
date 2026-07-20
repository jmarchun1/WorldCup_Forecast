import json, os, sys
sys.path.insert(0, r'C:\Users\I846720\world-cup-forecasting')
import forecast

config = forecast._load_config()
today = '2026-06-10'
data_dir = r'C:\Users\I846720\world-cup-forecasting\data'

for fname in os.listdir(data_dir):
    if not fname.endswith('.json'):
        continue
    with open(os.path.join(data_dir, fname)) as f:
        md = json.load(f)
    c = forecast._compute_consensus(md, today, config)
    if c:
        print(f"{md['match_id']}  =>  {c['consensus_home_goals']}-{c['consensus_away_goals']}")
        print(f"  votes: {c['scoreline_votes']}")
