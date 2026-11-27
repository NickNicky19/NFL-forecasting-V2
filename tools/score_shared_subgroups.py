"""Immutable saved-row C02 cohort extension; no fitting or future labels."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2.shared_subgroups import prepare,run
p=argparse.ArgumentParser();p.add_argument('action',choices=('prepare','run'));p.add_argument('--private-root',type=Path,required=True);p.add_argument('--public-root',type=Path,required=True);p.add_argument('--leader-file',type=Path);p.add_argument('--candidate-minima',type=Path)
a=p.parse_args();args=vars(a);action=args.pop('action')
if action=='run':args.pop('leader_file');args.pop('candidate_minima')
print(json.dumps((prepare if action=='prepare'else run)(**args),sort_keys=True))
