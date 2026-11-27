#!/usr/bin/env python3
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2 import seasonal_rolling_v2 as s
p=argparse.ArgumentParser();p.add_argument('action',choices=('prepare','run'));p.add_argument('--year',type=int)
for name in ('source-root','public','private','empirical-predictions'):p.add_argument('--'+name,type=Path,required=True)
for name in ('base-protocol','chart-queries','empirical-chart-predictions','verifier-receipt'):p.add_argument('--'+name,type=Path)
a=p.parse_args()
result=s.prepare(year=a.year,source_root=a.source_root,base_protocol=a.base_protocol,empirical_predictions=a.empirical_predictions,empirical_chart_predictions=a.empirical_chart_predictions,chart_queries=a.chart_queries,public=a.public,private=a.private) if a.action=='prepare' else s.run(source_root=a.source_root,public=a.public,private=a.private,empirical_predictions=a.empirical_predictions,empirical_chart_predictions=a.empirical_chart_predictions,verifier_receipt=a.verifier_receipt)
print(json.dumps(result))
