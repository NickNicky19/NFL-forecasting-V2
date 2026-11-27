"""Prepare or execute bounded saved-row carry comparisons; no fit action."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2.carry_older_pairs import prepare,run
p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=('prepare','run'))
p.add_argument('--manifest',required=True,type=Path);p.add_argument('--public-root',required=True,type=Path)
a=vars(p.parse_args());action=a.pop('action');print(json.dumps({'prepare':prepare,'run':run}[action](**a),sort_keys=True))
