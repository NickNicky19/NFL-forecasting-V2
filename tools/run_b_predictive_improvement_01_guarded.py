"""Future execution hardening; the six original calibration fits are retained.

Requires a separately prepared, unused output directory and its registration.
This entrypoint was not used for the original v1 results.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from threadpoolctl import threadpool_limits
from tools.run_b_predictive_improvement_01 import run


if __name__ == '__main__':
    private, output = map(Path, sys.argv[1:3])
    if (output / 'SCORES.json').exists():
        raise SystemExit('Do not refit or overwrite completed evidence')
    with threadpool_limits(limits=2):
        run(private, output)
