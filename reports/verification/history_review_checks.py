"""Independent fictional checks; no NFL rows, data acquisition or optimization fits."""
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from nfl_v2.history import Observation, Origin, Query, RunManifest, SourceAdmission, run


def check():
    source=SourceAdmission('fixture-review','qualified_asof_reconstruction',
        'invented earlier availability; no claim about NFL facts',('rush_yd',),
        'fixture explicit signed full-game yards','fixture played','fixture position',
        'fictional source; no license needed')
    m=RunManifest('review-only','fixture-panel','fixture-cohort',('fixture-review',),
        (2022,2023,2024,2025,2026),4,20,20,120,120,10000)
    q=Query('q','fixture-review','future','player','RB','rush_yd',2026,2,'2026-09-13T18:00:00Z')
    a=Observation('a','fixture-review','old-game','player','RB','rush_yd',2024,1,
        '2024-09-01T18:00:00Z','2024-09-03T18:00:00Z',2)
    b=replace(a,observation_id='b',game_id='recent-game',season=2025,
        kickoff_utc='2025-09-01T18:00:00Z',available_utc='2025-09-03T18:00:00Z',value=8)
    c=replace(a,observation_id='c',game_id='current-game',season=2026,
        kickoff_utc='2026-09-01T18:00:00Z',available_utc='2026-09-03T18:00:00Z',value=20)
    origin=Origin('o','2026-09-13T16:30:00Z',(q,),(a,b,c))
    result=run((origin,),(source,),m)
    n=0
    def ok(condition):
        nonlocal n
        assert condition
        n+=1
    def rejection(obj=origin,manifest=m,admission=source):
        try:run((obj,),(admission,),manifest)
        except ValueError:return True
        return False
    points={(r['history_regime'],r['product']):r['forecast'] for r in result['rows']}
    for arm,mean,median in [('H-CURRENT',20,20),('H-RECENT',14,8),('H-MULTI',10,8)]:
        ok(points[(arm,'empirical_mean')]==mean)
        ok(points[(arm,'lower_median')]==median)
    ok({r['query_id'] for r in result['rows']}=={'q'})
    ok(result['forecast_cells']==6 and result['scores']==0 and result['optimization_fits']==0)
    strict=run((origin,),(source,),m,strict_current=True)
    ok(len(strict['rows'])==2)
    ok(all(r['training_observation_ids']==['c'] and r['forecast']==20 for r in strict['rows']))
    ok(strict['policy_run_sha256']!=result['policy_run_sha256'])
    canonical=json.dumps([asdict(origin)],sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    ok(result['origin_inputs_sha256']==hashlib.sha256(canonical).hexdigest())
    changed=run((replace(origin,observations=(replace(a,value=200),b,c)),),(source,),m)
    other={(r['history_regime'],r['product']):r['forecast'] for r in changed['rows']}
    ok(other[('H-CURRENT','empirical_mean')]==20)
    ok(other[('H-RECENT','empirical_mean')]==14)
    ok(other[('H-MULTI','empirical_mean')]==76)
    startup=run((replace(origin,observations=(a,b)),),(source,),m,strict_current=True)
    ok(all(r['forecast']==0 and r['used_n']==0 and r['fallback']=='constant_zero_startup' for r in startup['rows']))
    for bad in [replace(c,available_utc=origin.cutoff_utc),
                replace(c,available_utc='2026-09-20T00:00:00Z'),
                replace(c,available_utc='2026-09-03T18:00:00'),
                replace(c,game_id=q.game_id),replace(c,value=None),
                replace(c,participation='unknown'),replace(c,source_id='not-qualified')]:
        ok(rejection(replace(origin,observations=(bad,))))
    ok(rejection(replace(origin,observations=(c,replace(c,observation_id='duplicate')))))
    ok(rejection(manifest=replace(m,max_forecast_cells=5)))
    ok(rejection(manifest=replace(m,max_candidate_row_checks=1)))
    ok(rejection(admission=replace(source,availability_basis='')))
    fb=replace(q,position='FB')
    fb_rows=run((replace(origin,queries=(fb,)),),(source,),m)['rows']
    ok(all(r['position']=='FB' and r['fallback']=='constant_zero_startup' for r in fb_rows))
    # IDs/contracts do not bind values. Input digests must discriminate the changed value.
    static_keys={'manifest_sha256','source_admissions_sha256','query_membership_sha256'}
    changed_digest_keys=[k for k in result if k.endswith('sha256') and result[k]!=changed[k]]
    source_binding=bool(set(changed_digest_keys)-static_keys)
    ok(source_binding)
    return {'status':'PASS_SOFTWARE_ONLY','independent_fictional_checks':n,
        'input_value_change_discriminated_by':changed_digest_keys,
        'history_source_sha256':hashlib.sha256((ROOT/'nfl_v2/history.py').read_bytes()).hexdigest(),
        'nfl_observations':0,'optimization_fits':0,'nfl_forecasts':0,'nfl_scores':0}


if __name__=='__main__':
    result=check()
    (ROOT/'reports/verification/HISTORY_ENGINE_CHECKS.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
