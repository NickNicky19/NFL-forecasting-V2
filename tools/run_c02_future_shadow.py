#!/usr/bin/env python3
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2 import c02_future_shadow as wave
p=argparse.ArgumentParser();p.add_argument('action',choices=('prepare','run'))
for name in ('public','private','source-root'):p.add_argument('--'+name,type=Path,required=True)
for name in ('football-public','chart-public','queries','verifier-receipt'):p.add_argument('--'+name,type=Path)
p.add_argument('--private-roots',nargs='+',type=Path);a=p.parse_args()
result=wave.prepare(a.public,a.private,a.source_root,a.football_public,a.chart_public,a.private_roots,a.queries) if a.action=='prepare' else wave.run(a.source_root,a.public,a.private,a.verifier_receipt)
print(json.dumps(result))
