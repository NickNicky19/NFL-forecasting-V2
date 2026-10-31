#!/usr/bin/env python3
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2.strict_hgb_2026_design import prepare
p=argparse.ArgumentParser()
for n in('queries','base-protocol','output','private-output'):p.add_argument('--'+n,type=Path,required=True)
print(json.dumps(prepare(**{k:v for k,v in vars(p.parse_args()).items()})))
