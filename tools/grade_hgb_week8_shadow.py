#!/usr/bin/env python3
"""Offline HGB shadow grading. Prepare/trust capture bindings before final labels."""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2.hgb_shadow_grading import collect_bindings, grade_files
from nfl_v2.shadow_grading import canonical, digest

if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest="command",required=True)
    prepare=commands.add_parser("prepare-bindings",help="collect original receipts; independently retain/check emitted hash")
    prepare.add_argument("--metadata-root",required=True,type=Path)
    prepare.add_argument("--output",required=True,type=Path)
    grade=commands.add_parser("grade")
    for option in ("forecasts","capture-receipt","capture-protocol","frozen-queries","capture-bindings",
                   "artifact-root","labels","public-output","private-output"):
        grade.add_argument("--"+option,required=True,type=Path)
    for option in ("expected-forecast-sha256","expected-capture-receipt-sha256","expected-protocol-sha256","expected-bindings-sha256","run-id"):
        grade.add_argument("--"+option,required=True)
    grade.add_argument("--asof-utc",default=datetime.now(timezone.utc).isoformat())
    args=vars(parser.parse_args());command=args.pop("command")
    if command=="prepare-bindings":
        body=canonical(collect_bindings(args["metadata_root"]))
        with args["output"].open("xb") as handle:handle.write(body)
        print(json.dumps(dict(bytes=len(body),sha256=digest(body),state="REQUIRES_INDEPENDENT_TRUSTED_HASH_RETENTION")))
    else:
        print(json.dumps(grade_files(**args),indent=2,sort_keys=True))
