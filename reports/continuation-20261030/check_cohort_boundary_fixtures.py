"""Independent explicit expected-value fixtures; zero NFL observations/fits."""
import json,hashlib
from pathlib import Path
from nfl_v2.pregame_views import PriorWorkload,memberships,band

def run():
    checks=0
    def check(test):
        nonlocal checks
        if not test:raise AssertionError('cohort boundary fixture')
        checks+=1
    rows=[dict(player_id='a',game_id=str(i),available=t,workload=dict(attempts=v,carries=v,targets=v))
        for i,(t,v)in enumerate([(0.,99.),(1.,8.),(10.,2.),(20.,None),(100.,999.),(110.,9999.)])]
    h=PriorWorkload(rows);p=h.at('a','rush_att',100.)
    check(p==dict(mean=5.,supported_slots=2,history_slots=3,latest_available=20.))
    check(h.at('a','rush_att',100.0001)['mean']==500.5)
    check(band('rush_att',5.)=='low');check(band('rush_att',12.)=='middle')
    check(band('rush_att',0.)=='zero');check(band('rush_att',None)=='unknown')
    rows=[dict(player_id=f'p{i:02}',game_id='prior',available=1.,workload=dict(attempts=1.,carries=1.,targets=1.))for i in range(25)]
    queries=[dict(player_id=f'p{i:02}',game_id='future',week=1,target='rush_att',population='fictional')for i in reversed(range(25))]
    queries.append(dict(player_id=None,query_id='blocked-fictional',game_id='future',week=1,target='rush_att',population='fictional'))
    member,_=memberships(queries,PriorWorkload(rows),{1:2.})
    check(member[('future','p00','rush_att','fictional')]['rank']==1)
    check(member[('future','p24','rush_att','fictional')]['rank']==25)
    check([sum('top'+str(k)in m['cohorts']for m in member.values())for k in(10,15,20)]==[10,15,20])
    check([sum(b in m['cohorts']for m in member.values())for b in('rank1_10','rank11_15','rank16_20','rank21plus','unranked')]==[10,5,5,5,1])
    check(member[('future','UNQUALIFIED_QUERY:blocked-fictional','rush_att','fictional')]['mean']is None)
    return dict(status='PASS',tests_run=checks,new_fits=0,new_forecasts=0,nfl_outcomes=0,scope='Fictional exactavailabilityleftlimit,missing-slotfreshness,bandedges,lexicalties,nestedtopsets,disjointbands,blockedunknownidentity',code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())

if __name__=='__main__':
    result=run();path=Path('reports/continuation-20261030/PREGAME_COHORT_BOUNDARY_FIXTURES.json')
    with path.open('x')as f:json.dump(result,f,indent=2,sort_keys=True);f.write('\n')
    print(json.dumps(result))
