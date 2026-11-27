"""Independent arithmetic verification of frozen native adapter outputs.

This is a verification calculation, not a common scorer or new policy.
"""
import argparse
import collections
from decimal import Decimal
import gzip
import hashlib
import json
from pathlib import Path
from datetime import datetime,timezone


def digest(x):
    return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--private-rows',type=Path,required=True);a=ap.parse_args()
    out=Path(__file__).resolve().parent
    data=json.loads(gzip.decompress(a.private_rows.read_bytes()))['rows']
    groups=collections.defaultdict(list)
    grade_checks=0
    for r in data:
        groups[r['model_key'],r['policy']].append(r)
        s=r['selected_side']
        if s in ('OVER','UNDER'):
            actual,line=Decimal(str(r['actual'])),Decimal(str(r['line']))
            expected='PUSH'if actual==line else'WIN'if(actual>line)==(s=='OVER')else'LOSS'
        elif s=='ABSTAIN':expected='ABSTAIN'
        else:expected='UNAVAILABLE_FORECAST'
        assert expected==r['status'];grade_checks+=1
        if r.get('probs')is not None:
            p=r['probs'];assert all(0<=x<=1 for x in p.values())and abs(sum(p.values())-1)<1e-10
        if r['model_key'].endswith('KNOWN_TARGET_TIME'):
            assert r['available']==(r['unavailable_reason']is None)
    tables=json.loads((out/'NATIVE_TABLES.json').read_bytes());aggregates=0;numerical=0;probability=0
    def subset(gg,window):
        if window=='ALL':return gg
        if window.isdigit():return[r for r in gg if r['week']==int(window)]
        if window in('DK_ONLY','SLEEPER_ONLY'):return[r for r in gg if str(r['line_from']).lower()==('dk'if window=='DK_ONLY'else'sleeper')]
        return[r for r in gg if r['attribution']==('learned'if window=='LEARNED_ONLY'else'fallback')]
    for t in tables:
        rows=subset(groups[t['model_key'],t['policy']],t['week_view'])
        assert len(rows)==t['eligible']
        assert sum(r['available']for r in rows)==t['available']
        assert sum(not r['available']for r in rows)==t['unavailable']
        assert sum(r['selected_side']=='ABSTAIN'for r in rows)==t['abstentions']
        for side in('OVER','UNDER','COMBINED'):
            selected=[r for r in rows if r['selected_side']in('OVER','UNDER')and(side=='COMBINED'or r['selected_side']==side)]
            w=sum(r['status']=='WIN'for r in selected);l=sum(r['status']=='LOSS'for r in selected);old=t[side]
            assert old['selected']==len(selected)and old['decided']==w+l
            assert old['wins']==(w if w+l else None)and old['losses']==(l if w+l else None)
            assert old['rate']==(w/(w+l)if w+l else None);aggregates+=1
        points=[r for r in rows if r['point']is not None]
        err=[r['point']-r['actual']for r in points];n=t['numerical'];assert n['scored']==len(err)
        if err:
            assert abs(n['MAE']-sum(map(abs,err))/len(err))<1e-12
            assert abs(n['MSE']-sum(e*e for e in err)/len(err))<1e-12
            assert abs(n['bias']-sum(err)/len(err))<1e-12
        else:assert n['MAE']is None and n['MSE']is None and n['bias']is None
        numerical+=1
        good=[r for r in rows if r['probs']is not None];p=t['probability'];assert p['events']==len(good)
        if good:
            brier=sum((r['probs']['over']-int(r['actual']>r['line']))**2 for r in good)/len(good)
            assert abs(brier-p['Brier'])<1e-12
            assert sum(b['n']for b in p['reliability_fixed_binsOver'])==len(good)
        else:assert p['Brier']is None and p['three_state_Brier']is None
        probability+=1
    alias_checks=0
    for policy in('P1_MEAN','P1_LOWER_MEDIAN','P2_STATISTICAL_LAW','P90'):
        left=groups['B0',policy];right=groups['B1',policy]
        fields=('game_id','player_id','actual','line','point','probs','selected_side','status','fallback','available')
        assert[{k:r[k]for k in fields}for r in left]==[{k:r[k]for k in fields}for r in right];alias_checks+=len(left)
    mask={}
    for model in('C02_KNOWN_TARGET_TIME','DIRECT_GLM_KNOWN_TARGET_TIME'):
        gg=groups[model,'P1_MEAN'];counts={w:sum(r['available']for r in gg if r['week']==w)for w in range(5,10)}
        assert list(counts.values())==[28,27,25,16,0];mask[model]=counts
    top=json.loads((out/'SELECTIVE_NATIVE_TABLES.json').read_bytes());membership_checks=0
    for t in top:
        if t['week_view']=='ALL':continue
        gg=[r for r in groups[t['model_key'],'P2_STATISTICAL_LAW']if r['week']==int(t['week_view'])]
        chosen=[];slots=t['K']
        for batch in sorted({r['kickoff']for r in gg}):
            eligible=[r for r in gg if r['kickoff']==batch and r['selected_side']in('OVER','UNDER')and(t['pool']=='Combined'or r['selected_side'].lower()==t['pool'])]
            eligible=sorted(eligible,key=lambda r:(-r['probs'][r['selected_side'].lower()],r['game_id'],r['player_id'],str(r['line'])))
            chosen.extend(eligible[:slots]);slots-=len(eligible[:slots])
        w=sum(r['status']=='WIN'for r in chosen);l=sum(r['status']=='LOSS'for r in chosen)
        assert t['COMBINED']['wins']==(w if w+l else None)and t['COMBINED']['losses']==(l if w+l else None)
        assert t['COMBINED']['selected']==len(chosen);membership_checks+=1
    canonical=json.loads((out/'NATIVE_SCORES.json').read_bytes())
    assert len({r['record_id']for r in canonical})==len(canonical)
    assert not any(r['model_key']=='B1'for r in canonical)
    receipt=dict(id='B_NATIVE142_INDEPENDENT_ARITHMETIC_VERIFICATION_v1',at_UTC=datetime.now(timezone.utc).isoformat(),state='PASS_WITH_SOURCE_SCOPE_LIMITS',
        grade_checks=grade_checks,aggregate_side_checks=aggregates,numerical_views=numerical,strict_binary_Brier_views=probability,
        B0_B1_alias_rows=alias_checks,legacy_known_time_mask=mask,weekly_selective_membership_checks=membership_checks,
        canonical_unique_records=len(canonical),private_rows_SHA256=hashlib.sha256(a.private_rows.read_bytes()).hexdigest(),
        exact_C_scorer_reused=True,source_clock_authentication=False,private_A84_parity=False,new_NFL_observations=0,new_fits=0,new_HTTP=0,
        source_lean_limit='102 explicit source lean sides;40 explicit null source lean values have no selected side. Missing-versus-declared-abstention semantics not independently established. Do not call40 nulls intentional policy abstentions without source contract.',
        verified_scope='Separate Decimal threshold grade calculation plus independent aggregate/metric sums and frozen-batch membership reconstruction; source provenance/training-fit parity not newly established.')
    p=out/'INDEPENDENT_VERIFICATION_V1.json'
    if p.exists():raise FileExistsError(p.name)
    p.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))


if __name__=='__main__':main()
