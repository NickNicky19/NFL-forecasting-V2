#!/usr/bin/env python3
"""Positive-proof-gated recovery census; original v1 payloads stay immutable.

Use all original recovery_census.py CLI roots plus --restoration-proof FILE.
--validate-proof-only checks proof bindings without rereading/repacking data.
"""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from nfl_v2.recovery_proof import load_allowlist
from tools import recovery_census as original

def main():
 parser=argparse.ArgumentParser(description=__doc__,add_help=False);parser.add_argument('--restoration-proof',type=Path);parser.add_argument('--public-root',type=Path);parser.add_argument('--validate-proof-only',action='store_true');a,remaining=parser.parse_known_args()
 if '--help'in remaining:
  print(__doc__);sys.argv=[sys.argv[0],'--help'];original.main();return
 if a.restoration_proof is None or a.public_root is None:parser.error('--restoration-proof and --public-root required')
 approved=load_allowlist(a.public_root,a.restoration_proof)
 if a.validate_proof_only:print(json.dumps(dict(status='PASS',affirmatively_proved_objects=len(approved),data_repacked=False,newfits=0)));return
 # Only the admission gate changes. Archive bytes, missing-part arithmetic,
 # file hashes and deduplication retain the versioned original implementation.
 original.restored_digests=lambda index,public_root:approved
 sys.argv=[sys.argv[0],*remaining,'--public-root',str(a.public_root)];original.main()
if __name__=='__main__':main()
