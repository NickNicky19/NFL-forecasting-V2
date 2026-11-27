"""No-fit scheduled-window audit. Roots are explicit; receipts use safe hashes."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nfl_v2.scheduled_defense_audit import prepare, audit

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('action', choices=('prepare', 'audit'))
for key in ('original-public', 'original-private', 'source-root', 'public-root'):
    parser.add_argument('--'+key, required=True, type=Path)
parser.add_argument('--leader-table', type=Path)
parser.add_argument('--membership-root', type=Path)
args = vars(parser.parse_args())
action = args.pop('action')
if action == 'audit':
    args.pop('leader_table'); args.pop('membership_root')
elif args['leader_table'] is None or args['membership_root'] is None:
    parser.error('prepare requires --leader-table and --membership-root')
print(json.dumps({'prepare':prepare, 'audit':audit}[action](**args), sort_keys=True))
