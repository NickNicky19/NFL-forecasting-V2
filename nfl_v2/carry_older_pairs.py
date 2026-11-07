"""Bounded older-season paired replay of retained carry-role specialization.

No model import, fit, inference, acquisition, 2026 replay or future-label read.
Inputs bind exact retained flat bytes, the 2025 correction and frozen cohorts.
"""
from __future__ import annotations
import collections
import csv
import gzip
import hashlib
import json
import math
import resource
import time
from datetime import datetime, timezone
from pathlib import Path
from . import paired_uncertainty

VERSION='v2-retained-carry-training-role-older-robustness-pairs-v1'
ROLE='v2-hgb-rush-att-qb-rb-specialization-v1'
ORIGINAL='hgb-direct-history-controls-v1:absolute_error_point'
POLICIES=('H-CURRENT-COMMON','H-RECENT-COMMON','H-MULTI-COMMON','H-CURRENT-STRICT')
ARMS=dict(zip(POLICIES,('H-CURRENT','H-RECENT','H-MULTI','H-CURRENT')))
COHORTS=('all','top10','top15','top20')

def now():return datetime.now(timezone.utc).isoformat()
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(path):return json.loads(Path(path).read_bytes())
def write(path,x):
    with Path(path).open('xb')as f:f.write(canonical(x))
def spec(r):return r['procedure_id'],r['history_regime'],r['product_id']
def identity(r):return tuple(r[k]for k in('game_id','player_id','target','population'))
def candidate_spec(policy):return ROLE+(':'+('strict-current-feature-memory'if policy.endswith('STRICT')else'common-feature-memory')),ARMS[policy],'absolute_loss_point'
def original_spec(policy):return ORIGINAL+(':'+('strict-current-inputs'if policy.endswith('STRICT')else'common-feature-memory')),ARMS[policy],'absolute_error_point'

def strongest(scores):
    rr=[r for r in scores if r['target']=='rush_att'and r['week']=='ALL'and r['position']=='ALL'
        and r['fallback_view']=='ALL'and r['population']=='primary'and not r['procedure_id'].startswith(ROLE)
        and r.get('mae')is not None]
    n=max(r['n']for r in rr)
    r=min((r for r in rr if r['n']==n),key=lambda r:(r['mae'],spec(r)))
    return dict(procedure_id=r['procedure_id'],history_regime=r['history_regime'],product_id=r['product_id'],
                observed_full_primary_mae=r['mae'],observed_full_primary_n=r['n'],
                selection='strongest observed same-season full-primary point MAE; fixed across every subgroup/policy; exposed benchmark, not earlier routing')

def prepare(*,manifest,public_root):
    manifest,public_root=Path(manifest),Path(public_root)
    if public_root.exists():raise ValueError('fresh immutable output required')
    inputs=load(manifest)
    if sorted(x['season']for x in inputs)!=[2022,2023,2024,2025]:raise ValueError('exact four older seasons required')
    safe=[]
    for s in sorted(inputs,key=lambda x:-x['season']):
        if (s['season']==2025)!=bool(s.get('role_overlay')):raise ValueError('2025 entire corrected RA overlay required')
        if s['season']==2023 and'complete-replay'not in Path(s['flat']).parent.name:raise ValueError('complete2023only; partialW1-16 forbidden')
        scores=load(s['scores']);over=load(s['overlay_scores'])if s.get('overlay_scores')else[]
        if over:scores=[r for r in scores if not r['procedure_id'].startswith(ROLE)]+over
        full=[r for r in scores if r['target']=='rush_att'and r['week']=='ALL'and r['position']=='ALL'and r['fallback_view']=='ALL'and r['population']=='primary']
        for policy in POLICIES:
            if not any(spec(r)==candidate_spec(policy)for r in full)or not any(spec(r)==original_spec(policy)for r in full):raise ValueError('exact candidate/original products missing')
        files={k:dict(artifact_id='RETAINED-'+sha(s[k]),sha256=sha(s[k]),bytes=Path(s[k]).stat().st_size)
               for k in('flat','scores','memberships','role_overlay','overlay_scores')if s.get(k)}
        safe.append(dict(season=s['season'],files=files,strongest_reference=strongest(scores)))
    public_root.mkdir(parents=True)
    p=dict(version=VERSION,state='FROZEN_BEFORE_PAIRED_REPLAY',registered_at_utc=now(),
        code_sha256=sha(__file__),uncertainty_helper_sha256=sha(paired_uncertainty.__file__),seasons=safe,
        hypothesis='Does the existing QB/RB-only L1 training repair remain useful in older seasons against both exact same-policy broad-training HGB L1 and strongest observed full-primary same-season carry control?',
        chronology='Reuse unchanged earlier-only seasonal model forecasts; no refit or recreated historical issuance. Core fit windows use common within-origin feature memory; strict is a separate complete-information-policy comparison.2022RECENT lacks2021and is source-limited proxy, not a completed requested recent-history arm.',
        candidate='Existing retained absolute-loss point procedure; no new learner, median-law, fitted result or parameter claim.',
        overlay='Drop every2025base role-specialization row and replace with entire corrected24148-row packet; preserve source labels/product absolute_loss_point/QB-RB-only fallback.2023usesfull18-week recombination only.',
        comparator='Samehistory/commonfeaturepolicy original HGBL1 plus fixed strongest whole-primary same-season non-specialization point procedure. Strongest history/product not reselected within QB/RB/WR/TE/top-player bands; latter is an exposed practical benchmark, not an isolated same-input learner comparison.',
        cohort='Exact existing frozen carry memberships. Retrospective observed stat-row/physical-appearance diagnostic, not exante starters/props. Last3 earlier available opportunity slots rank top10/15/20; missing consumes slots; earliestweeklykickoff-90 and assumed7dayavailability. No reranking from outcomes.',
        role_views='PrimaryALL,QB,RB; extendedALL,WR,TE. Top10/15/20 onlyALLposition, same memberships for every competitor.',
        fallback_views=['full_system','own_learned_only','all_three_common_learned','candidate_fallback_only','any_model_fallback'],
        metrics='Point MAEprimary, MSE/RMSE/bias/tails diagnostic. Paired candidate-minus-control native and relative MAE delta; wholeweek500drawbootstrapseed1703 and game-cluster sensitivity. Exact shared IDs/labels/position; missing actuals never zero.',
        uncertainty='Descriptive exposed same-season contrasts, not adjusted for candidate/control selection or multiplicity; neither player counts nor mean/median outputs are independent games.',
        prior_2026='reports/continuation-20261030b/carry-strong-control-comparison-v1; accepted2026analysis linked, not rerun',
        budget=dict(wall_seconds=180,cpu_seconds=180,max_peak_memory_bytes=1073741824,max_threads=1,
                    max_pair_views=2500,max_public_bytes=33554432,max_fit_calls=0,max_inference_calls=0),
        new_fits=0,new_forecasts=0,new_univariate_score_views=0,current2026_week8_outcomes_read=0)
    write(public_root/'FROZEN_PROTOCOL.json',p)
    return p

def number(x):
    if x in('',None):return None
    v=float(x)
    if not math.isfinite(v):raise ValueError('nonfinite retained carry value')
    return v

def validate_pair(a,b):
    if identity(a)!=identity(b)or(a['actual'],a['position'],a['week'],a['season'])!=(b['actual'],b['position'],b['week'],b['season']):raise ValueError('exact pair identity/label/position/week mismatch')

def point_summary(rows):
    finite=[r for r in rows if r['prediction']is not None and r['actual']is not None]
    n=len(finite);out=dict(query_rows=len(rows),n=n,missing_actual_rows=sum(r['actual']is None for r in rows),
        missing_prediction_rows=sum(r['prediction']is None for r in rows),fallback_rows=sum(r['fallback']!='none'for r in rows),
        mae=None,mse=None,rmse=None,bias=None,p90_abs=None,p95_abs=None,max_abs=None)
    if not n:return out
    errors=[r['prediction']-r['actual']for r in finite];absolute=sorted(abs(e)for e in errors)
    def q(prob):
        at=(n-1)*prob;lo=int(at);return absolute[lo]+(absolute[min(lo+1,n-1)]-absolute[lo])*(at-lo)
    mse=math.fsum(e*e for e in errors)/n;fb=[r for r in finite if r['fallback']!='none'];learn=[r for r in finite if r['fallback']=='none']
    out.update(mae=math.fsum(absolute)/n,mse=mse,rmse=math.sqrt(mse),bias=math.fsum(errors)/n,p90_abs=q(.9),p95_abs=q(.95),max_abs=absolute[-1],
        scored_fallback_rows=len(fb),learned_rows=len(learn),
        fallback_loss_sum=math.fsum(abs(r['prediction']-r['actual'])for r in fb),
        learned_loss_sum=math.fsum(abs(r['prediction']-r['actual'])for r in learn),
        fallback_full_error_contribution=math.fsum(abs(r['prediction']-r['actual'])for r in fb)/n)
    return out

def analyze(candidate,original,leader,members,*,season,policy,guard):
    expected=set(members)
    if set(candidate)!=expected or set(original)!=expected or set(leader)!=expected:raise ValueError('full retained carry queries must match frozen cohort IDs')
    groups=collections.defaultdict(list)
    for key,r in candidate.items():
        a,b=original[key],leader[key];validate_pair(r,a);validate_pair(r,b)
        views=['full_system','own_learned_only'if r['fallback']=='none'else'candidate_fallback_only']
        if all(x['fallback']=='none'and x['prediction']is not None and x['actual']is not None for x in(r,a,b)):views.append('all_three_common_learned')
        if any(x['fallback']!='none'for x in(r,a,b)):views.append('any_model_fallback')
        for c in members[key]['cohorts']:
            if c not in COHORTS:continue
            for role in (('ALL',r['position'])if c=='all'else('ALL',)):
                for view in views:groups[r['population'],c,role,view].append(key)
    pairs=[]
    for dims,keys in sorted(groups.items()):
        guard();population,cohort,role,view=dims;aa=[candidate[k]for k in keys]
        for reference,lookup in (('same_policy_original_broad_HGB_L1',original),('strongest_observed_same_season_full_primary_control',leader)):
            bb=[lookup[k]for k in keys];supported=[(a,b)for a,b in zip(aa,bb)if a['prediction']is not None and b['prediction']is not None and a['actual']is not None]
            uncertainty=paired_uncertainty.paired_losses([abs(a['prediction']-a['actual'])for a,b in supported],
                [abs(b['prediction']-b['actual'])for a,b in supported],[a['week']for a,b in supported],[a['game_id']for a,b in supported])
            candidate_points=point_summary([a for a,b in supported]);control_points=point_summary([b for a,b in supported])
            pairs.append(dict(pair_id='CARRY-OLDER-'+hashlib.sha256(canonical([VERSION,season,policy,dims,reference])).hexdigest()[:24],
                season=season,history_regime=ARMS[policy],policy_id=policy,population=population,cohort_id=cohort,position=role,fallback_view=view,
                comparison=reference,candidate_procedure_id=aa[0]['procedure_id'],candidate_product_id=aa[0]['product_id'],
                comparator_procedure_id=bb[0]['procedure_id'],comparator_product_id=bb[0]['product_id'],comparator_history_regime=bb[0]['history_regime'],
                query_rows=len(keys),paired_n=len(supported),unresolved_rows=len(keys)-len(supported),
                metric_population='identical supported paired rows; whole query coverage retained in query_rows/unresolved_rows',
                query_membership_sha256=hashlib.sha256(canonical(sorted(keys))).hexdigest(),
                paired_membership_sha256=hashlib.sha256(canonical(sorted(identity(a)for a,b in supported))).hexdigest(),
                candidate_metrics=candidate_points,comparator_metrics=control_points,
                uncertainty=uncertainty,native_error_delta=uncertainty['delta'],relative_error_delta=uncertainty['relative_error_change'],
                game_count=len({a['game_id']for a,b in supported}),week_count=len({a['week']for a,b in supported}),
                source_panel='CURRENT_VINTAGE_RETROSPECTIVE_PARTICIPANT_DIAGNOSTIC',
                history_limit='2022RECENTsource-limited2022proxy;2021unsupported'if season==2022 and ARMS[policy]=='H-RECENT'else None))
    return pairs

def run(*,manifest,public_root):
    public_root=Path(public_root);p=load(public_root/'FROZEN_PROTOCOL.json');inputs=load(manifest)
    if p['code_sha256']!=sha(__file__)or p['uncertainty_helper_sha256']!=sha(paired_uncertainty.__file__):raise ValueError('frozen paired-analysis code changed')
    start,cpu=time.monotonic(),time.process_time();completed=[];remaining=[2025,2024,2023,2022];failures=[];totalpairs=total_selected=total_source=0
    def guard():
        if time.monotonic()-start>p['budget']['wall_seconds']or time.process_time()-cpu>p['budget']['cpu_seconds']:raise RuntimeError('SAVED_ROW_TIME_BUDGET')
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>p['budget']['max_peak_memory_bytes']:raise RuntimeError('SAVED_ROW_MEMORY_BUDGET')
    for frozen in p['seasons']:
        year=frozen['season'];s=next(x for x in inputs if x['season']==year)
        try:
            guard()
            for role,binding in frozen['files'].items():
                if sha(s[role])!=binding['sha256']:raise ValueError('retained source binding changed')
            members={tuple(x['key']):x for x in json.loads(gzip.decompress(Path(s['memberships']).read_bytes()))if x['key'][2]=='rush_att'}
            want={candidate_spec(policy)for policy in POLICIES}|{original_spec(policy)for policy in POLICIES}|{spec(frozen['strongest_reference'])}
            index=collections.defaultdict(dict);scanned=selected=0
            def consume(path,overlay=False):
                nonlocal scanned,selected
                with gzip.open(path,'rt',newline='')as handle:
                    reader=csv.reader(handle);header=next(reader);ix={k:header.index(k)for k in('procedure_id','product_id','history_regime','target','season','week','game_id','player_id','population','position','prediction','actual','fallback')}
                    for raw in reader:
                        scanned+=1
                        if scanned%4096==0:guard()
                        # Filter season/week/target before numeric label parsing.
                        if raw[ix['season']]!=str(year)or not 1<=int(raw[ix['week']])<=18 or raw[ix['target']]!='rush_att':continue
                        proc=raw[ix['procedure_id']]
                        if s.get('role_overlay')and proc.startswith(ROLE)and not overlay:continue
                        k=proc,raw[ix['history_regime']],raw[ix['product_id']]
                        if k not in want:continue
                        r={f:raw[j]for f,j in ix.items()};r.update(season=year,week=int(r['week']),actual=number(r['actual']),prediction=number(r['prediction']))
                        if r['actual']is not None and(r['actual']<0 or r['actual']!=int(r['actual'])):raise ValueError('carry count support violation')
                        if r['prediction']is not None and r['prediction']<0:raise ValueError('negative carry point prediction')
                        key=identity(r)
                        if key in index[k]:raise ValueError('duplicate retained procedure/query')
                        index[k][key]=r;selected+=1
            consume(s['flat'])
            if s.get('role_overlay'):consume(s['role_overlay'],True)
            pairs=[]
            for policy in POLICIES:pairs.extend(analyze(index[candidate_spec(policy)],index[original_spec(policy)],index[spec(frozen['strongest_reference'])],members,season=year,policy=policy,guard=guard))
            guard()
            if totalpairs+len(pairs)>p['budget']['max_pair_views']:raise RuntimeError('SAVED_ROW_PAIR_BUDGET')
            out=dict(version=VERSION,season=year,state='COMPLETE_RETAINED_ROW_PAIRS',protocol_sha256=sha(public_root/'FROZEN_PROTOCOL.json'),source_bindings=frozen['files'],
                strongest_reference=frozen['strongest_reference'],scanned_source_views=scanned,selected_retained_views=selected,query_cells=len(members),
                pair_views=len(pairs),new_fits=0,new_forecasts=0,new_univariate_score_views=0,rows=pairs)
            if sum(x.stat().st_size for x in public_root.iterdir()if x.is_file())+len(canonical(out))>p['budget']['max_public_bytes']:raise RuntimeError('SAVED_ROW_PUBLIC_BYTES_BUDGET')
            write(public_root/f'PAIR_ANALYSIS_{year}.json',out);completed.append(year);remaining.remove(year);totalpairs+=len(pairs);total_selected+=selected;total_source+=scanned
        except Exception as exc:
            failures.append(dict(season=year,type=type(exc).__name__,reason=str(exc)[:240]));break
    receipt=dict(version=VERSION,state='COMPLETE'if not remaining else'PARTIAL_STOPPED',completed_at_utc=now(),protocol_sha256=sha(public_root/'FROZEN_PROTOCOL.json'),
        code_sha256=sha(__file__),completed_seasons=completed,remaining_seasons=remaining,
        pair_views=totalpairs,scanned_source_views=total_source,selected_retained_views=total_selected,
        resource=dict(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,max_threads=1),
        failures=failures,new_fits=0,new_forecasts=0,new_univariate_score_views=0,current2026_week8_outcomes_read=0)
    write(public_root/'RUN_RECEIPT.json',receipt);return receipt
