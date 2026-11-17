#!/usr/bin/env python3
"""Offline grading of frozen shadows after qualified final outcomes are available."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2.shadow_grading import grade_files

if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    for option in ("forecasts","capture-receipt","capture-protocol","labels","public-output","private-output"):
        parser.add_argument("--"+option,type=Path,required=True)
    for option in ("expected-forecast-sha256","expected-capture-receipt-sha256","run-id"):
        parser.add_argument("--"+option,required=True)
    parser.add_argument("--asof-utc",default=datetime.now(timezone.utc).isoformat())
    args=parser.parse_args()
    result=grade_files(**vars(args))
    print(json.dumps(result,indent=2,sort_keys=True))
