#!/usr/bin/env python3
"""Execute the report-specified software counterexample, not an NFL backtest."""
import argparse
import hashlib
import json
import math
import platform
import resource
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import sklearn
from threadpoolctl import threadpool_limits
from nfl_v2.hgb_control import make_estimator, PARAMS
from nfl_v2.hgb_output_diagnostics import point_output_profile


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True, type=Path)
    a = ap.parse_args()
    if a.out.exists():
        raise ValueError('immutable verification output already exists')
    if sklearn.__version__ != '1.8.0':
        raise ValueError('report counterexample requires exact sklearn1.8.0; register another version separately')
    start, cpu = time.monotonic(), time.process_time()
    x = np.arange(1000, dtype=float).reshape(-1, 1)
    y = np.where(x[:, 0] < 650, 0., 15.)
    outputs = []
    with threadpool_limits(limits=2):
        for objective in ('absolute_error_point', 'squared_error_mean'):
            model = make_estimator('rush_att', objective).fit(x, y)
            values = model.predict(x)
            nodes = model._predictors[0][0].nodes
            first = nodes[0]
            gradient = model._loss.gradient(y_true=np.array([0., 1., 10.]), raw_prediction=np.zeros(3))
            outputs.append(dict(objective=objective, loss=model.loss, parameters=PARAMS,
                profile=point_output_profile(values, y),
                fitted_iterations=int(model.n_iter_),
                initial_prediction=float(model._baseline_prediction.ravel()[0]),
                first_tree_nodes=len(nodes), first_split_feature=int(first['feature_idx']),
                first_split_threshold=float(first['num_threshold']),
                first_split_gain=float(first['gain']),
                loss_gradient_at_prediction_zero_for_targets_0_1_10=gradient.tolist(),
                prediction_vector_sha256=hashlib.sha256(values.tobytes()).hexdigest()))
    assert outputs[0]['profile']['zero_outputs'] == 1000
    assert outputs[0]['profile']['mae'] == 5.25
    assert outputs[1]['profile']['mae'] < .31
    assert outputs[1]['profile']['maximum'] > 14.5
    r = dict(schema='B-report-specified-HGB-software-counterexample-v1',
        state='REPRODUCED_KNOWN_L1_LEARNING_PATHOLOGY_NOT_A_SUCCESSFUL_LEARNER',
        at_utc=datetime.now(timezone.utc).isoformat(),
        audit_TXT_sha256='720b464f8077d3a483a4a73245690071866b7757fb6d20763c2ea8d931061795',
        fixture=dict(rows=1000, x='arange(1000).reshape(-1,1)',
                     target='0 if x<650 else15; perfectly separating predictor',
                     zero_target_fraction=.65, synthetic=True),
        estimator_factory='nfl_v2.hgb_control.make_estimator',
        factory_code_sha256=hashlib.sha256(Path('nfl_v2/hgb_control.py').read_bytes()).hexdigest(),
        reproduction_code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        outputs=outputs, software_fit_calls=2, new_NFL_fit_calls=0,
        new_NFL_forecasts=0, new_NFL_observations=0, new_NFL_test_weeks=0,
        legitimate_zero_control=point_output_profile([0., 0.], [0., 0.]),
        no_library_or_original_forecast_change=True,
        lost_NFL_accuracy_not_inferred_from_synthetic_fixture=True,
        environment=dict(python=platform.python_version(), sklearn=sklearn.__version__, numpy=np.__version__),
        resources=dict(wall_seconds=time.monotonic()-start, cpu_seconds=time.process_time()-cpu,
                       peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024, max_threads=2))
    with a.out.open('x') as f:
        f.write(json.dumps(r, sort_keys=True, indent=2)+'\n')
    print(json.dumps(dict(state=r['state'], software_fits=2, new_NFL_fits=0,
                         profile_by_objective={o['objective']:o['profile'] for o in outputs})))


if __name__ == '__main__':
    main()
