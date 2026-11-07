#!/usr/bin/env python3
"""Run a frozen, supplied-source current-vintage empirical history diagnostic."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2.empirical_benchmark import run

if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-root',type=Path,required=True)
    p.add_argument('--protocol',type=Path,required=True)
    p.add_argument('--public-root',type=Path,required=True)
    p.add_argument('--private-root',type=Path,required=True)
    a=p.parse_args()
    result=run(a.source_root,a.protocol,a.public_root,a.private_root)
    print(json.dumps(result,sort_keys=True,indent=2))
