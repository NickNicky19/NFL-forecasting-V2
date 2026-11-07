import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2.seasonal_subgroups import prepare,run
p=argparse.ArgumentParser();p.add_argument('action',choices=('prepare','run'))
for k in('source-root','season-public-root','season-private-root','public-root','private-root'):p.add_argument('--'+k,type=Path,required=True)
a=vars(p.parse_args());action=a.pop('action');print(json.dumps((prepare if action=='prepare'else run)(**a),sort_keys=True))
