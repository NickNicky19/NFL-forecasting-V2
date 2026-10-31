#!/usr/bin/env python3
"""Continue only missing cells using frozen v1 model/forecast bytes. No network."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from nfl_v2.distribution_wave_v2 import run
p=argparse.ArgumentParser(description=__doc__)
for key in ['source-root','public-root','private-root','reuse-public','reuse-private']:p.add_argument('--'+key,type=Path,required=True)
a=p.parse_args();print(json.dumps(run(a.source_root,a.public_root,a.private_root,a.reuse_public,a.reuse_private),indent=2))
