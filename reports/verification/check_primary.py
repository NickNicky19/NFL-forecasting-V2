"""Compare separately calculated aggregates and hand-worked contracts to V2."""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from nfl_v2 import scoring


def check():
    independent = json.loads((ROOT/'reports/verification/INDEPENDENT_REPLAY.json').read_text())
    primary = json.loads((ROOT/'reports/replay/REPLAY_SCORES.json').read_text())
    lookup = {(r['target'],r['procedure_id']): r for r in primary if r['population']=='primary_roles'}
    count, max_delta = 0, 0.
    for row in independent['summaries']:
        other = lookup[(row['target'],row['model'])]
        assert row['n']==other['n']; count += 1
        for metric in ['mae','mse','bias']:
            delta=abs(float(row[metric])-other[metric]); max_delta=max(delta,max_delta)
            assert math.isclose(float(row[metric]),other[metric],rel_tol=2e-14,abs_tol=2e-12)
            count += 1
    contract_checks = 0
    def ok(condition):
        nonlocal contract_checks
        assert condition
        contract_checks += 1
    # Chart arithmetic by hand: 10+8-1-.4+6+5+4+6-1+6+24=66.6.
    components={k:0 for k in scoring.CHART_WEIGHTS}
    components.update(passing_yards=250,passing_TD=2,interceptions_thrown=1,
        rushing_yards=-4,rushing_TD=1,receptions=5,receiving_yards=40,receiving_TD=1,
        fumbles_lost=1,passing_2pt=1,rushing_2pt=1,receiving_2pt=1,
        offensive_fumble_recovery_TD=1,kick_return_TD=1,punt_return_TD=1,field_goal_return_TD=1)
    ok(math.isclose(scoring.chart_points(components),66.6))
    components['field_goal_return_TD']=None
    ok(scoring.chart_points(components) is None)
    ok(scoring.chart_points({}) is None)
    for pair, expected in [((1,None),1),((0,0),0),((None,0),None),
                           ((None,None),None),((.5,0),None),((1,-1),None),((True,0),None)]:
        ok(scoring.anytime_td(*pair)==expected)
    p=scoring.point_metrics([0,1,2],[1,1,1],'pass_yd')
    ok(math.isclose(p['mae'],2/3));ok(math.isclose(p['mse'],2/3))
    ok(p['bias']==0);ok(math.isclose(p['abs_lt_1'],1/3));ok(p['abs_le_1']==1)
    ok(scoring.quantile([0,1,1,5,10],.9)==8)
    ok(math.isclose(scoring.quantile([0,1,1,5,10],.95),9))
    for line, expected in [(.5,dict(over=.5,under=.5,push=0.)),(1,dict(over=.2,under=.5,push=.3))]:
        ps=scoring.event_probabilities([0,1,2],[.5,.3,.2],line)
        for key,val in expected.items():ok(math.isclose(ps[key],val))
        ok(math.isclose(sum(ps.values()),1))
    for y in [0,1]:
        a=scoring.point_metrics([.7],[y],'anytime_td')
        b=scoring.point_metrics([.3],[1-y],'anytime_td')
        ok(math.isclose(a['brier'],b['brier']))
        ok(math.isclose(a['log_loss'],b['log_loss']))
    ok(math.isclose(scoring.expected_net(.2,.5,4),.1))
    for args,expected in [((2,1,'over',4),('win',3)),((0,1,'over',4),('loss',-1)),
        ((1,1,'over',4),('push',0)),((None,1,'under',4,'void'),('void',0)),
        ((None,1,'under',4,'unknown'),('unresolved',None)),
        ((None,1,'under',4,'dnp'),('unresolved',None))]:
        ok(scoring.settle(*args)==expected)
    return {'metric_checks':count,'metric_cells':len(independent['summaries']),
        'max_absolute_metric_difference':max_delta,'hand_contract_checks':contract_checks,
        'status':'PASS_WITH_STATED_EVIDENCE_LIMITS',
        'reviewed_primary_scorer_sha256':hashlib.sha256((ROOT/'nfl_v2/scoring.py').read_bytes()).hexdigest(),
        'reviewed_primary_runner_sha256':hashlib.sha256((ROOT/'tools/replay_retained.py').read_bytes()).hexdigest()}


if __name__=='__main__':
    result=check()
    (ROOT/'reports/verification/PRIMARY_COMPARISON.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
