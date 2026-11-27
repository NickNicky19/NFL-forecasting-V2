#!/usr/bin/env python3
"""Run a previously sealed missing-week continuation; never reset parent runs."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2 import seasonal_rolling_continuation as s
p=argparse.ArgumentParser()
for name in ('source-root','public','private','empirical-predictions','empirical-chart-predictions','verifier-receipt'):p.add_argument('--'+name,type=Path,required=True)
a=p.parse_args()
r=s.run(source_root=a.source_root,public=a.public,private=a.private,empirical_predictions=a.empirical_predictions,empirical_chart_predictions=a.empirical_chart_predictions,verifier_receipt=a.verifier_receipt)
try:print(json.dumps(r))
except BrokenPipeError:pass
