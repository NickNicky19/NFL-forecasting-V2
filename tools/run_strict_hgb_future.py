#!/usr/bin/env python3
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2 import strict_hgb_future as s
p=argparse.ArgumentParser();p.add_argument('action',choices=('prepare','run'))
for name in ('public','private','source-root'):p.add_argument('--'+name,type=Path,required=True)
for name in ('old-protocol','queries','verifier'):p.add_argument('--'+name,type=Path)
a=p.parse_args();result=s.prepare(a.public,a.private,a.source_root,a.old_protocol,a.queries) if a.action=='prepare' else s.run(a.public,a.private,a.source_root,a.verifier);print(json.dumps(result))
