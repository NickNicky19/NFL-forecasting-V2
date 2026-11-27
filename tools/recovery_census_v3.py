#!/usr/bin/env python3
"""Strict restoration-object proof gate over the unchanged v1 census algorithm."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools import recovery_census_v2 as entrypoint
from nfl_v2.recovery_proof_v3 import load_allowlist
if __name__=='__main__':
 entrypoint.load_allowlist=load_allowlist
 entrypoint.main()
