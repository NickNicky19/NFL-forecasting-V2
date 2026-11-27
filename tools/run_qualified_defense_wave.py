"""Explicit prepare/history/future actions; no unattended scheduler."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2.qualified_defense_wave import prepare,run_historical,run_future
p=argparse.ArgumentParser();p.add_argument('action',choices=('prepare','historical','future'))
for k in('source-root','control-public','control-private','chart-public','chart-private','future-queries','frozen-board','public-root','private-root','verifier-receipt'):p.add_argument('--'+k,type=Path)
p.add_argument('--private-model-root',type=Path,action='append');p.add_argument('--sole-worker-confirmed',action='store_true')
a=vars(p.parse_args());action=a.pop('action');a={k:v for k,v in a.items()if v is not None};roots=a.pop('private_model_root',None)
if action=='prepare':a.pop('sole_worker_confirmed');a['private_model_roots']=roots or[]
elif action=='historical':
 for k in('future_queries','frozen_board'):a.pop(k,None)
else:
 for k in('control_public','control_private','chart_public','chart_private','future_queries','frozen_board'):a.pop(k,None)
print(json.dumps({'prepare':prepare,'historical':run_historical,'future':run_future}[action](**a),sort_keys=True))
