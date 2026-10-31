#!/usr/bin/env python3
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2.availability_c_guard import run
p=argparse.ArgumentParser();p.add_argument('--source-root',required=True,type=Path);p.add_argument('--public',required=True,type=Path);p.add_argument('--private',required=True,type=Path);a=p.parse_args();print(json.dumps(run(a.source_root,a.public,a.private)))
