#!/usr/bin/env python3
"""One finite qualified chart run; no network, publication or scheduler."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from nfl_v2.chart_wave import prepare,run
p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['prepare','run'])
for key in ['source-root','public-root','private-root']:p.add_argument('--'+key,type=Path,required=True)
for key in ['previous-queries','old-protocol','policy-path','durability-path']:p.add_argument('--'+key,type=Path)
p.add_argument('--shared-asof');a=p.parse_args()
if a.command=='prepare':
 for key in ['previous_queries','old_protocol','policy_path','durability_path','shared_asof']:
  if getattr(a,key) is None:p.error('prepare requires --'+key.replace('_','-'))
 out=prepare(a.source_root,a.previous_queries,a.old_protocol,a.public_root,a.private_root,a.policy_path,a.durability_path,a.shared_asof);out={k:out[k] for k in ['version','registered_at_utc','code_sha256','historical_query_cells','current_2026_query_cells','future_query_cells','future_games','expected_output_views','budget']}
else:out=run(a.source_root,a.public_root,a.private_root)
print(json.dumps(out,indent=2))
