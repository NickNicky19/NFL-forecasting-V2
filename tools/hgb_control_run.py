"""Run exactly the registered HGB reconstruction; no acquisition on this path."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2.hgb_control import prepare,run

p=argparse.ArgumentParser();p.add_argument('operation',choices=['prepare','run'])
p.add_argument('--sources',required=True);p.add_argument('--public',required=True);p.add_argument('--private',required=True)
p.add_argument('--empirical-private');p.add_argument('--week8-queries');p.add_argument('--empirical-protocol')
a=p.parse_args()
if a.operation=='prepare':
    if not all([a.empirical_private,a.week8_queries,a.empirical_protocol]):p.error('prepare requires frozen query/protocol inputs')
    r=prepare(a.sources,a.empirical_private,a.week8_queries,a.empirical_protocol,a.public,a.private)
    print(json.dumps({k:r[k] for k in ['version','registered_at_utc','historical_query_cells','week8_query_cells','historical_membership_sha256']},indent=2))
else:
    print(json.dumps(run(a.sources,a.public,a.private),indent=2))
