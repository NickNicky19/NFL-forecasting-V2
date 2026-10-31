"""Default metadata-only preflight; execution requires external admitted receipts."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nfl_v2 import defense_season_executor as runner


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=('preflight', 'baseline', 'prepare', 'execute'), nargs='?', default='preflight')
    p.add_argument('--season', type=int, default=2025)
    p.add_argument('--contract', type=Path)
    for name in ('public', 'private', 'source-root', 'queries-path', 'baseline-path',
                 'source-protocol-path', 'baseline-evidence-root', 'restoration-gate',
                 'verifier-receipt', 'software-receipt', 'worker-release',
                 'fit-index-path', 'retained-receipt-root', 'metadata-worker-release'):
        p.add_argument('--' + name, type=Path)
    a = p.parse_args(argv)
    if a.action == 'preflight':
        result = runner.metadata_plan(a.season)
    elif a.action == 'baseline':
        keys = ('source_root', 'source_protocol_path', 'queries_path', 'fit_index_path',
                'retained_receipt_root', 'private', 'restoration_gate', 'metadata_worker_release')
        if any(getattr(a, k) is None for k in keys):
            p.error('baseline requires exact source/query/retained-fit inputs, factual restoration and separate metadata-only release')
        result = runner.reconstruct_baseline_metadata(**{k: getattr(a, k) for k in keys})
    elif a.action == 'prepare':
        if a.contract is None or a.public is None:
            p.error('prepare requires --contract and fresh --public')
        result = runner.prepare(contract=json.loads(a.contract.read_text()), public=a.public)
    else:
        keys = ('public', 'private', 'source_root', 'queries_path', 'baseline_path',
                'source_protocol_path', 'baseline_evidence_root', 'restoration_gate',
                'verifier_receipt', 'software_receipt', 'worker_release')
        if any(getattr(a, k) is None for k in keys):
            p.error('execute requires every exact input, factual gate, review and separate root worker-release path')
        result = runner.execute(**{k: getattr(a, k) for k in keys})
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
