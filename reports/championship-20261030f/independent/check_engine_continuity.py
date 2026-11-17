"""Bind retained settlement/timing checks and verify current probability math."""
import argparse
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import sys


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();sys.path.insert(0,str(a.repo_root.resolve()))
    from nfl_v2.scoring import event_probabilities,expected_value,threshold_crossing
    old=a.repo_root/'reports/prop-grading-20261030e';core=json.loads((old/'EXACT_CORE_INDEPENDENT_REVIEW_V2.json').read_bytes());timing=json.loads((old/'TIMING_SELECTION_INDEPENDENT_REVIEW.json').read_bytes())
    for path,digest in core['code_sha256'].items():assert sha(a.repo_root/path)==digest
    assert sha(a.repo_root/'nfl_v2/prop_selection.py')==timing['source_sha256']
    checks=[]
    for target,line,under,over in [('pass_td','1.5',(0,1),(2,5)),('pass_cmp','19.5',(0,19),(20,33)),('rec','4.5',(0,4),(5,11)),('rush_yd','49.5',(-3,49),(50,170))]:
        for y in under+over:
            for side in('over','under'):
                expected='WIN'if(y>Decimal(line)if side=='over'else y<Decimal(line))else'LOSS'
                assert threshold_crossing(y,line,side,target=target)==expected
                checks.append(dict(target=target,line=line,actual=y,side=side,expected=expected))
    assert threshold_crossing('4.28','4.28','over',target='nick-chart-ppr-v1')=='PUSH'
    support=[-2,0,1,2];mass=[.1,.4,.3,.2];previous_over=1.;previous_under=0.
    for line in('-2','-1.5','0','.5','1','1.5','2'):
        probability=event_probabilities(support,mass,line)
        expected={name:math.fsum(p for y,p in zip(support,mass)if condition(Decimal(y),Decimal(line)))for name,condition in [('over',lambda y,l:y>l),('under',lambda y,l:y<l),('push',lambda y,l:y==l)]}
        for name in expected:assert math.isclose(probability[name],expected[name],abs_tol=1e-12)
        assert math.isclose(sum(probability.values()),1,abs_tol=1e-12)
        assert probability['over']<=previous_over and probability['under']>=previous_under
        previous_over,previous_under=probability['over'],probability['under']
    integer=event_probabilities(support,mass,'1');half=event_probabilities(support,mass,'1.5')
    assert math.isclose(integer['push'],.3)and half['push']==0
    assert math.isclose(integer['over'],half['over'])
    conditional=expected_value('.5','.2','2',conditioning='conditional_nonvoid',p_nonvoid='.9')
    unconditional=expected_value('.45','.18','2',conditioning='unconditional_placed')
    assert conditional=={'EV_nonvoid':Decimal('.3'),'EV_placed':Decimal('.27')}
    assert unconditional['EV_placed']==conditional['EV_placed']and unconditional['EV_nonvoid']is None
    for y,p in[(0,.2),(1,.2),(0,.8),(1,.8)]:
        assert math.isclose((p-y)**2,((1-p)-(1-y))**2,abs_tol=1e-15)
        q=p if y else 1-p;mirrored=(1-p)if not y else p
        assert -math.log(q)==-math.log(mirrored)
    report=dict(state='PASS_CURRENT_ENGINE_CONTINUITY_AND_PROBABILITY_CONTRACTS',checked_at_utc=datetime.now(timezone.utc).isoformat(),unchanged_source_hashes=core['code_sha256'],retained_core_fixture_checks=core['passed_checks'],retained_timing_fixture_checks=timing['passed'],retained_fixture_scope='Synthetic win/loss/push/void, fractional grid, malformed contracts, conditional/unconditional EV, forecast/quote clock violations, duplicate selections and fixed-versus-rolling K. These are software checks, not actual NFL wins/voids.',new_explicit_half_point_cases=checks,current_probability_law_fixtures=7,current_fractional_grid_push_fixture=1,current_conditional_unconditional_EV_bridge=True,current_complement_and_monotonicity=True,real_panel_push_or_verified_voids=0,new_fits=0,new_forecasts=0,new_NFL_observations=0,current2026_Week8_outcomes_read=0,limitations='No probability or executable price is inferred for a retained point-only forecast or provider-labelled threshold.')
    with a.output.open('x')as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps({k:report[k]for k in('state','retained_core_fixture_checks','retained_timing_fixture_checks','current_probability_law_fixtures')}))


if __name__=='__main__':main()
