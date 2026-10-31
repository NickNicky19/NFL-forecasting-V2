#!/usr/bin/env python3
"""Prepare/run one finite distribution wave; no network, scheduler or publication."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from nfl_v2.distribution_wave import prepare,run
p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['prepare','run']);p.add_argument('--source-root',type=Path,required=True);p.add_argument('--public-root',type=Path,required=True);p.add_argument('--private-root',type=Path,required=True);p.add_argument('--previous-queries',type=Path);p.add_argument('--old-protocol',type=Path);p.add_argument('--provenance',type=Path)
a=p.parse_args()
if a.command=='prepare':
 for k in ['previous_queries','old_protocol','provenance']:
  if getattr(a,k) is None:p.error('prepare requires --'+k.replace('_','-'))
 result=prepare(a.source_root,a.previous_queries,a.old_protocol,a.public_root,a.private_root,json.loads(a.provenance.read_text()))
 print(json.dumps({k:result[k] for k in ['version','registered_at_utc','code_sha256','historical_query_cells','week8_open_t90_query_cells','week8_closed_t90_query_cells','budget']},indent=2))
else:print(json.dumps(run(a.source_root,a.public_root,a.private_root),indent=2))
