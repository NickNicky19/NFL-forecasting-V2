"""Explicit zero-fit older-season cohort replay; no scheduler or live sources."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2.seasonal_subgroup_scores import prepare,run
p=argparse.ArgumentParser();p.add_argument('action',choices=('prepare','run'));p.add_argument('--year',type=int,required=True)
for k in('season-public','season-private','cohort-public','cohort-private','leader-file','candidate-minima','candidate-scores','public-root','repair-public','repair-private'):p.add_argument('--'+k,type=Path)
a=vars(p.parse_args());action=a.pop('action');a={k:v for k,v in a.items()if v is not None}
if action=='run':
 for k in('leader_file','candidate_minima','candidate_scores'):a.pop(k,None)
print(json.dumps((prepare if action=='prepare'else run)(**a),sort_keys=True))
