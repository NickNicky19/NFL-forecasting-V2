#!/usr/bin/env python3
"""Seal or run a bounded retained-source availability shadow ablation."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2 import availability_wave as wave

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['prepare','fixed','refit'])
    for name in ('public','private','source-root'):p.add_argument('--'+name,type=Path,required=True)
    for name in ('old-public','queries','chart-queries','receipts'):p.add_argument('--'+name,type=Path)
    p.add_argument('--private-roots',type=Path,nargs='+');a=p.parse_args()
    result=wave.prepare(a.public,a.private,a.source_root,a.old_public,a.private_roots,a.queries,a.chart_queries,a.receipts) if a.action=='prepare' else wave.run(a.source_root,a.public,a.private,refits=a.action=='refit')
    print(json.dumps(result))
if __name__=='__main__':main()
