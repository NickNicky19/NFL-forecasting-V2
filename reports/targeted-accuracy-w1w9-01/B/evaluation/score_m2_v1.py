"""Owner-local M2 joins into the existing pinned C grader; no new fit or collector.

Public output is aggregates and commitments only. Existing protected offers and
row calculations are retained in memory, never copied to a public artifact.
"""
from __future__ import annotations
import argparse, collections, copy, gzip, hashlib, importlib.util, json, math
import pathlib, resource, sys, time
from datetime import datetime, timedelta, timezone
import numpy as np

HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[3]
METHODS=('M2_P2_BIN','M2_P2_BB','M2_C1_BIN','M2_C1_BB','M2_C2_BIN','M2_C2_BB','D_M2')
PROTOCOL='FROZEN_EVALUATION_PROTOCOL_V1.json'

def read(path):
    p=pathlib.Path(path);b=p.read_bytes()
    return json.loads(gzip.decompress(b) if p.suffix=='.gz' else b)

def sha(path):return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def write(path,x):
    p=pathlib.Path(path)
    if p.exists():raise FileExistsError(p.name)
    p.parent.mkdir(parents=True,exist_ok=True)
    b=(json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
    p.write_bytes(gzip.compress(b,mtime=0) if p.suffix=='.gz' else b)

def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m

def dt(x):
    if isinstance(x,(int,float)):
        if not math.isfinite(x):raise ValueError('Nonfinite epoch source time')
        return datetime.fromtimestamp(x,timezone.utc)
    d=datetime.fromisoformat(x.replace('Z','+00:00'))
    if d.tzinfo is None:raise ValueError('Naive source time')
    return d.astimezone(timezone.utc)

def key(r):return r['game_id'],r['player_id'],r.get('target',r.get('category'))
def fallback(value):
    if isinstance(value,bool):return value
    return value not in (None,'none','NONE','learned','NOT_APPLICABLE')

def lawside(probs):
    return 'OVER' if probs['over']>probs['under'] else 'UNDER' if probs['under']>probs['over'] else 'ABSTAIN'

def rankkey(r):return (-r['probs'][r['selected_side'].lower()],r['game_id'],r['player_id'],r['category'])

def choose_fraction(rows,num,den):
    """Cumulative eligible-to-date capacity; never inspect later batch scores."""
    chosen=set();seen=0
    for kickoff in sorted({r['kickoff'] for r in rows},key=dt):
        batch=[r for r in rows if r['kickoff']==kickoff];seen+=len(batch)
        capacity=max(0,(num*seen)//den-len(chosen))
        good=[r for r in batch if r['available'] and r['selected_side'] in ('OVER','UNDER')]
        good.sort(key=rankkey)
        chosen.update(key(r) for r in good[:capacity])
    return chosen

def choose_top(rows,K,pool):
    chosen=set()
    for kickoff in sorted({r['kickoff'] for r in rows},key=dt):
        good=[r for r in rows if r['kickoff']==kickoff and r['available'] and r['selected_side'] in ('OVER','UNDER') and (pool=='Combined' or r['selected_side']==pool)]
        good.sort(key=rankkey);chosen.update(key(r) for r in good[:max(0,K-len(chosen))])
    return chosen

def calibrated(rows,origin):
    result=[]
    for r in rows:
        t=dict(r);t['raw_probs']=r['probs'];t['calibration_n']=0;t['calibration_correct']=0
        if r['probs'] is not None and r['selected_side'] in ('OVER','UNDER'):
            side=r['selected_side'].lower();confidence=r['probs'][side];bi=min(9,int(confidence*10))
            eligible=[s for s in rows if dt(s['kickoff'])+timedelta(days=7)<origin and s['status'] in ('WIN','LOSS') and s['selected_side'] in ('OVER','UNDER') and min(9,int(s['probs'][s['selected_side'].lower()]*10))==bi]
            n=len(eligible);correct=sum(s['status']=='WIN' for s in eligible)
            value=(correct+20*confidence)/(n+20)
            t['calibrated_selected_confidence']=value;t['calibration_n']=n;t['calibration_correct']=correct
            over=value if side=='over' else 1-value
            t['calibrated_probs']={'over':over,'under':1-over,'push':0.}
        else:t['calibrated_selected_confidence']=None;t['calibrated_probs']=None
        result.append(t)
    return result

def probstats(rr,field='probs'):
    good=[r for r in rr if r.get(field) is not None and r['actual'] is not None and r['appearance']=='PLAYED']
    binary=[];multi=[];logs=[];infinite=0
    for r in good:
        p=r[field];ev='over' if r['actual']>r['line'] else 'under' if r['actual']<r['line'] else 'push'
        binary.append((p['over']-int(ev=='over'))**2)
        multi.append(sum((p[s]-int(s==ev))**2 for s in ('over','under','push'))/2)
        if p[ev]>0:logs.append(-math.log(p[ev]))
        else:infinite+=1
    bins=[];sidebins=[]
    for i in range(10):
        lo=i/10;hi=(i+1)/10
        z=[r for r in good if lo<=r[field]['over'] and (r[field]['over']<hi or i==9)]
        bins.append(dict(lower=lo,upper=hi,n=len(z),mean_predicted=sum(r[field]['over']for r in z)/len(z)if z else None,observed_over=sum(r['actual']>r['line']for r in z)/len(z)if z else None))
        z=[r for r in good if r['selected_side']in('OVER','UNDER')and lo<=r[field][r['selected_side'].lower()]and(r[field][r['selected_side'].lower()]<hi or i==9)]
        sidebins.append(dict(lower=lo,upper=hi,n=len(z),mean_predicted=sum(r[field][r['selected_side'].lower()]for r in z)/len(z)if z else None,observed_correct=sum(r['status']=='WIN'for r in z)/len(z)if z else None))
    return dict(events=len(good),strict_binary_Over_Brier=sum(binary)/len(binary)if binary else None,half_three_state_Brier=sum(multi)/len(multi)if multi else None,log_loss='Infinity' if infinite else sum(logs)/len(good)if good else None,infinite_logloss_cases=infinite,Over_event_reliability=bins,selected_side_reliability=sidebins,typing='RAW_COUNT_LAW_EXACT_EVENT'if field=='probs'else'EXACT_LINE_CALIBRATED_SELECTED_SIDE_BERNOULLI;NOT_COUNT_CDF',conditioning='QUALIFIED_PLAYED_STATISTICAL_CROSSING_NOT_VENUE_NONVOID')

def numeric(rr):
    good=[r for r in rr if r.get('point')is not None and r['actual']is not None]
    errors=[r['point']-r['actual']for r in good]
    return dict(scored=len(good),MAE=sum(abs(e)for e in errors)/len(errors)if errors else None,MSE=sum(e*e for e in errors)/len(errors)if errors else None,bias=sum(errors)/len(errors)if errors else None,max_absolute_error=max(map(abs,errors),default=None),absolute_error_p90=float(np.quantile(np.abs(errors),.9))if errors else None,absolute_error_p95=float(np.quantile(np.abs(errors),.95))if errors else None)

def apply_selection(rows,chosen):
    out=[]
    for r in rows:
        t=dict(r)
        if key(r) not in chosen and r['available']:t.update(selected_side='ABSTAIN',status='ABSTAIN')
        out.append(t)
    return out

def main():
    ap=argparse.ArgumentParser()
    for name in ('sources','new-predictions','model-module','scorer-source','interval-source','existing-cmp-grades','existing-att-grades','C-points'):
        ap.add_argument('--'+name,type=pathlib.Path,required=True)
    a=ap.parse_args();sys.path.insert(0,str(ROOT))
    from nfl_v2 import player_context_matchup as ctx
    from nfl_v2.paired_uncertainty import paired_losses
    from tools import score_player_context_wave as old
    adapter=module(ROOT/'reports/w1w9-comparison-closure-01/B/common-intake/COMMON_SCORER_PARITY_ADAPTER_V1.py','M2_PINNED_COMMON_ADAPTER')
    status,summary,interval=adapter.load_common_functions(a.scorer_source,a.interval_source)
    fixture_checks=adapter.boundary_fixtures(status)
    model=module(a.model_module,'nfl_v2._targeted_qb_m2_eval')
    inv=module(ROOT/'reports/player-context-matchup-01/B/independent/inventory_retained_qb_offers_v1.py','M2_EXISTING_OFFER_ITERATOR')
    source_paths={int(w):pathlib.Path(p)for w,p in read(a.sources).items()}
    offers=[r for w,p in sorted(source_paths.items())for r in inv.iter_offers(p,w)]
    assert len(offers)==284 and len({key(r)for r in offers})==284
    assert all(r['actual']is not None and r['label_state']=='SUPPORTED'and r['participation']=='VERIFIED_PLAYED_POSITIVE_PHYSICAL'and float(r['line'])%1==.5 for r in offers)
    files=sorted(a.new_predictions.glob('*.json.gz'));predictions=[]
    for path in files:predictions+=read(path)['rows']
    current=[r for r in predictions if r['season']==2026 and r['week']in range(1,10)]
    queries=ctx.load_inputs(ROOT/'reports/information-first-20261112-01/B/completion-wave-v1/QB_CONTEXT_W1_W9_INPUTS_V1.json.gz')
    querymap={(r['game_id'],r['player_id']):r for r in queries}
    origins={(2026,w):min(dt(r.get('kickoff',r.get('kickoff_UTC')))for r in current if r['week']==w)for w in range(1,10)}
    bindings={'protocol':sha(HERE/PROTOCOL),'code':sha(__file__),'model_code':sha(a.model_module),'prediction_files':[{'file':p.name,'sha256':sha(p)}for p in files],'source_files':[{'week':w,'sha256':sha(p)}for w,p in source_paths.items()],'C_points_sha256':sha(a.C_points),'existing_CMP_grade_sha256':sha(a.existing_cmp_grades),'existing_ATT_grade_sha256':sha(a.existing_att_grades),'C_scorer_sha256':sha(a.scorer_source),'C_interval_sha256':sha(a.interval_source)}
    write(HERE/'EXECUTION_INPUT_BINDINGS_V1.json',bindings)
    started=time.monotonic();cpu=time.process_time();raw={};broad=[];law_checks=0;law_cache={}
    predmap={(r['method'],key(r)):r for r in current}
    assert len(predmap)==len(current),'Duplicate prediction identity'
    def restored(pr):
        k=pr['method'],key(pr)
        if k not in law_cache:law_cache[k]=model.restore_law(pr['law'])
        return law_cache[k]
    def row(offer,method,policy,pr=None):
        sd=None;probs=None;point=None;reason=None
        if pr is None:reason='MISSING_EXACT_NEW_PROCEDURE_FORECAST'
        else:
            if pr.get('actual')is not None and pr['actual']!=offer['actual']:raise ValueError('Current forecast/qualified offer label mismatch')
            law=restored(pr);probs=ctx.exact_probabilities(law,offer['line'])
            if any(not math.isfinite(v)or v<0 or v>1 for v in probs.values())or abs(sum(probs.values())-1)>1e-9:raise ValueError('Invalid exact probability law')
            if abs(law.mean-pr['mean'])>1e-7:raise ValueError('Wrong typed mean')
            if policy=='MEAN':point=pr['mean'];sd=old.sidepoint(point,offer['line'])
            elif policy=='MEDIAN':point=pr['lower_median'];sd=old.sidepoint(point,offer['line'])
            else:sd=lawside(probs).lower() if lawside(probs)!='ABSTAIN' else None
        disp_fallback=pr.get('conversion_components',{}).get('new_dispersion_model_fallback')if pr else None
        r=dict(game_id=offer['game_id'],player_id=offer['player_id'],category=offer['target'],target=offer['target'],position='QB',season=2026,week=offer['week'],actual=offer['actual'],line=offer['line'],selected_side=sd.upper()if sd else None if reason else'ABSTAIN',appearance='PLAYED',status='UNAVAILABLE_FORECAST'if reason else'ABSTAIN'if sd is None else'READY',comparator='STRICT_OVER_UNDER',period='FULL_GAME_INCLUDING_OT',scoring_contract_id='OFFICIAL_FULL_GAME_PASS_COMPLETIONS'if offer['target']=='pass_cmp'else'OFFICIAL_FULL_GAME_PASS_ATTEMPTS',kickoff=offer['kickoff'],line_from=offer['line_from'],point=point,probs=probs,available=reason is None,unavailable_reason=reason,fallback=pr.get('fallback')if pr else None,parent_fallback=bool(pr and fallback(pr.get('fallback'))),dispersion_fallback=disp_fallback,attribution='fallback'if pr and(fallback(pr.get('fallback'))or disp_fallback is not None)else'learned'if pr else'unavailable',method=method,procedure_id=pr.get('procedure_id',method)if pr else method,component_policy=policy,original_issuance=False)
        r['status']=status(r);return r
    for method in METHODS:
        for policy in ('MEAN','MEDIAN','LAW'):
            raw[method,policy]=[row(o,method,policy,predmap.get((method,key(o))))for o in offers if o['target']=='pass_cmp']
            law_checks+=sum(r['probs']is not None for r in raw[method,policy])
    # The unchanged attempt law is a complete-pipeline control, not a new opportunity arm.
    att_methods=sorted({r['method']for r in current if r['target']=='pass_att'})
    if len(att_methods)!=1:raise ValueError('Expected one unchanged attempt procedure')
    for policy in ('MEAN','MEDIAN','LAW'):
        raw['UNCHANGED_ATT',policy]=[row(o,'UNCHANGED_ATT',policy,predmap.get((att_methods[0],key(o))))for o in offers if o['target']=='pass_att']
    # Existing point/law/control vectors are reused under their original scope.
    existing=read(a.existing_cmp_grades)['rows']
    required={'B0','B2','E3','F2','P1','C02_WHOLE_BOARD','C02_KNOWN_TARGET_TIME','SAVED_ADJUSTED','SAVED_RAW','ALWAYS_OVER','ALWAYS_UNDER','EARLIER_LINE_PREVALENCE'}
    for r in existing:
        if r['model_key']not in required or r['policy']=='P90':continue
        t=dict(r,category='pass_cmp',target='pass_cmp',method='RETAINED_'+r['model_key'],component_policy=r['policy'])
        raw.setdefault((t['method'],t['component_policy']),[]).append(t)
    for r in read(a.existing_att_grades)['rows']:
        if r['model_key']=='COMMON_EXPOSURE' or r['policy']=='P90':continue
        t=dict(r,category='pass_att',target='pass_att',method='ATT_RETAINED_'+r['model_key'],component_policy=r['policy'],attribution='reference')
        raw.setdefault((t['method'],t['component_policy']),[]).append(t)
    cp=read(a.C_points);cm={(r['game_id'],r['player_id']):r for r in cp['rows']}
    for output in ('mean','median'):
        gg=[]
        for o in offers:
            if o['target']!='pass_cmp':continue
            p=cm.get((o['game_id'],o['player_id']));point=p[output]if p else None;sd=old.sidepoint(point,o['line'])if p else None
            r=dict(game_id=o['game_id'],player_id=o['player_id'],category='pass_cmp',target='pass_cmp',position='QB',season=2026,week=o['week'],actual=o['actual'],line=o['line'],selected_side=sd.upper()if sd else'ABSTAIN'if p else None,appearance='PLAYED',status='READY'if sd else'ABSTAIN'if p else'UNAVAILABLE_FORECAST',comparator='STRICT_OVER_UNDER',period='FULL_GAME_INCLUDING_OT',scoring_contract_id='OFFICIAL_FULL_GAME_PASS_COMPLETIONS',kickoff=o['kickoff'],line_from=o['line_from'],point=point,probs=None,available=p is not None,unavailable_reason=None if p else'C_POINT_NOT_AVAILABLE',fallback=p['fallback']if p else None,attribution='fallback'if p and fallback(p['fallback'])else'learned'if p else'unavailable',method='RETAINED_C_E0_ENV',procedure_id=cp['procedure'],component_policy=output.upper(),original_issuance=False)
            r['status']=status(r);gg.append(r)
        raw['RETAINED_C_E0_ENV',output.upper()]=gg
    def table(method,policy,window,rr,*,mode='RAW',canonical=True):
        result=summary(rr);selected=[r for r in rr if r['selected_side']in('OVER','UNDER')];decided=[r for r in selected if r['status']in('WIN','LOSS')]
        domain=[int(window)]if str(window).isdigit()else list(range(5,10))
        week_counts={str(w):sum(r['week']==w for r in selected)for w in domain}
        representative=rr[0]if rr else next(v[0]for(k,p),v in raw.items()if k==method and v)
        unresolved=len(selected)-len(decided)-sum(r['status']=='PUSH'for r in selected)
        result.update(method=method,procedure_id=rr[0]['procedure_id']if rr else method,policy=policy,window=window,category=rr[0]['category']if rr else'pass_cmp',target=rr[0]['category']if rr else'pass_cmp',season=2026,
            record_kind='actual_offer_direction_evaluation',available=sum(r['available']for r in rr),unavailable=sum(not r['available']for r in rr),selected=len(selected),decided=len(decided),unknown=sum(r['status']not in('WIN','LOSS','PUSH','ABSTAIN','UNAVAILABLE_FORECAST')for r in rr),selected_unique_games=len({r['game_id']for r in selected}),selected_unique_players=len({r['player_id']for r in selected}),selected_unique_player_games=len({key(r)for r in selected}),selected_by_week=week_counts,zero_selection_weeks=[int(w)for w,n in week_counts.items()if not n],fallback_selected=sum(r['attribution']=='fallback'for r in selected),fallback_fraction=sum(r['attribution']=='fallback'for r in selected)/len(selected)if selected else None,attribution=dict(collections.Counter(r['attribution']for r in rr)),unavailable_reasons=dict(collections.Counter(r.get('unavailable_reason')for r in rr if not r['available'])),numerical=numeric(rr),probability=probstats(rr,'calibrated_probs'if mode=='CALIBRATED_RELIABILITY'else 'probs'),selected_probability=probstats(selected,'calibrated_probs'if mode=='CALIBRATED_RELIABILITY'else'probs'))
        result.update(procedure_id=representative['procedure_id'],category=representative['category'],target=representative['category'],actual_weeks=sorted({r['week']for r in rr}),distinct_scored_weeks=sorted({r['week']for r in decided}),scheduled_week_domain=list(range(1,10)),missing_actual_line_weeks=[1,2,3,4],evidence_tier='TIER_B_CURRENT_VINTAGE_CHRONOLOGICAL_RETAINED_ACTUAL_SOURCE_LINES;QUOTE_CLOCK_UNKNOWN;MAIN_ALT_UNCLASSIFIED',primary_admission='LOCAL_NOT_C_ADMITTED',calibration_mode=mode,canonical_source_view=canonical,
            evaluation_panel_id='B-M2-2026-NATIVE-QB142-'+representative['category'],membership_SHA256=digest(sorted(key(r)for r in rr)),selected_membership_SHA256=digest(sorted(key(r)for r in selected)),grade_commitment_SHA256=digest([{k:r.get(k)for k in('game_id','player_id','category','line','actual','selected_side','status','point','probs','calibrated_probs','fallback')}for r in rr]),calibration_support=dict(counts=dict(collections.Counter(r.get('calibration_n',0)for r in rr)),rule='Same-method/category confidencebin earlier qualified nativeoffers only, prior20; rawdirectionfixed'),component_fallback=dict(parent=sum(r.get('parent_fallback',False)for r in selected),dispersion=dict(collections.Counter(r.get('dispersion_fallback')for r in selected if r.get('dispersion_fallback')is not None))),accuracy_targets={str(q):{'observed_hit_rate_at_least_target':result['COMBINED']['rate']>=q if result['COMBINED']['decided']else None,'supported_accuracy_claim':'NOT_ESTABLISHED','reason':'Exposed retrospective selection, limited dependent week/game support; no IID or multiple-search guarantee.'}for q in(.75,.8,.9)},unique_decided_milestones={str(n):len({key(r)for r in decided})>=n for n in(50,100,200)},unknown_sensitivity={'observed_decided':len(decided),'unresolved_selected':unresolved,'all_unknown_losses_rate':(result['COMBINED']['wins'] or 0)/(len(decided)+unresolved)if len(decided)+unresolved else None,'all_unknown_wins_rate':((result['COMBINED']['wins'] or 0)+unresolved)/(len(decided)+unresolved)if len(decided)+unresolved else None})
        result['record_id']='B-M2-EVAL-'+digest([method,policy,window,result['category'],mode])[:24]
        result['week_view']=str(window)
        result['population']='FULL_DECLARED_NATIVE_QB_OFFER_BOARD;CONDITIONAL_QUALIFIED_PLAYED_LABELS'
        result['history_regime']='H-MULTI'if method=='RETAINED_C_E0_ENV'else'STRICT-CURRENT-INFORMATION'if'C02_'in method else'UNKNOWN_ARCHIVED_SOURCE_PROCEDURE'if any(z in method for z in('SAVED_ADJUSTED','SAVED_RAW'))else'H-RECENT'
        # Preserve probability scores at every view; reliability bins belong to
        # cumulative views and are not duplicated across every weekly selector.
        if window!='ALL':
            for field in ('probability','selected_probability'):
                result[field].pop('Over_event_reliability',None)
                result[field].pop('selected_side_reliability',None)
        if policy not in ('MEAN','MEDIAN','LAW','P1_MEAN','P1_LOWER_MEDIAN','P2_STATISTICAL_LAW','REGISTERED_DIRECTION'):
            result['probability'].pop('Over_event_reliability',None)
            result['probability'].pop('selected_side_reliability',None)
            result['probability']['full_board_source']='Same method raw LAW full-board record; calibration mode separately typed.'
        return result

    tables=[];new_rows={};selective=[];selected_frames={};calibration_trace=[]
    for (method,policy),gg in raw.items():
        isnew=method in METHODS or method=='UNCHANGED_ATT'
        for window,rr in [('ALL',gg)]+[(str(w),[r for r in gg if r['week']==w])for w in range(5,10)]:
            tables.append(table(method,policy,window,rr,canonical=isnew or method=='RETAINED_C_E0_ENV'))
        if not isnew and method!='RETAINED_C_E0_ENV':continue
        for window,rr in [('DK_ONLY',[r for r in gg if r['line_from']=='dk']),('SLEEPER_ONLY',[r for r in gg if r['line_from']=='sleeper']),('LEARNED_ONLY',[r for r in gg if r['attribution']=='learned']),('FALLBACK_ONLY',[r for r in gg if r['attribution']=='fallback'])]:
            tables.append(table(method,policy,window,rr))
    for method in list(METHODS)+['UNCHANGED_ATT','RETAINED_B0']:
        component='P2_STATISTICAL_LAW'if method=='RETAINED_B0'else'LAW'
        gg=raw[method,component]
        # All native lines are half points; calibration is a distinct threshold
        # Bernoulli view. It does not edit the model's count/joint law.
        cal=[]
        for w in range(5,10):
            z=[r for r in calibrated(gg,origins[2026,w])if r['week']==w];cal+=z
            calibration_trace.append(dict(method=method,category=gg[0]['category'],week=w,origin=origins[2026,w].isoformat(),calibration_n_min=min((r['calibration_n']for r in z),default=0),calibration_n_max=max((r['calibration_n']for r in z),default=0),identity_startups=sum(r['calibration_n']==0 for r in z),raw_side_never_changed=True))
        for num,den,name in [(1,1,'COVERAGE_100'),(1,2,'COVERAGE_50'),(1,4,'COVERAGE_25'),(1,10,'COVERAGE_10')]:
            pp=[]
            for w in range(5,10):
                rr=[r for r in gg if r['week']==w];pp+=apply_selection(rr,choose_fraction(rr,num,den))
            selected_frames[method,name]=pp
        for K in (6,10,20):
            for pool in ('Combined','OVER','UNDER'):
                pp=[]
                for w in range(5,10):
                    rr=[r for r in gg if r['week']==w];pp+=apply_selection(rr,choose_top(rr,K,pool))
                selected_frames[method,f'TOP_{K}_{pool}']=pp
        for q in (.75,.8,.9):
            for mode,rows in [('RAW',gg),('CALIBRATED_RELIABILITY',cal)]:
                chosen={key(r)for r in rows if r['available']and r['selected_side']in('OVER','UNDER')and(r['calibrated_selected_confidence']if mode!='RAW'else r['probs'][r['selected_side'].lower()])>=q}
                name=f'THRESHOLD_{int(q*100)}_{mode}';selected_frames[method,name]=apply_selection(rows,chosen)
        for (m,policy),rr in list(selected_frames.items()):
            if m!=method:continue
            mode='CALIBRATED_RELIABILITY'if policy.endswith('CALIBRATED_RELIABILITY')else'RAW'
            for window,rows in [('ALL',rr)]+[(str(w),[r for r in rr if r['week']==w])for w in range(5,10)]:
                selective.append(table(method,policy,window,rows,mode=mode))
    # Broad numerical evaluation is independent of matching market rows.
    for season in (2025,2026):
      for method in METHODS+tuple(att_methods):
        group=[r for r in predictions if r['method']==method and r['season']==season]
        if not group:continue
        for output in ('mean','lower_median'):
            for window in ['ALL']+sorted({r['week']for r in group}):
                rr=group if window=='ALL'else[r for r in group if r['week']==window];scorable=[];unknown=0;count_ll=[];infinite=0
                for r in rr:
                    q=querymap.get((r['game_id'],r['player_id']))
                    if q is None or not q.get('physical_participation')or not q.get('target_parity'):unknown+=1;continue
                    actual=q['official_completions'if r['target']=='pass_cmp'else'official_attempts']
                    if actual is None:unknown+=1;continue
                    scorable.append(dict(point=r[output],actual=actual))
                    law=restored(r);v=law.logpmf(actual)if hasattr(law,'logpmf')else math.log(law.pmf(actual))if law.pmf(actual)>0 else-math.inf
                    if math.isfinite(v):count_ll.append(-v)
                    else:infinite+=1
                broad.append(dict(record_id='B-M2-NUMERIC-'+digest([method,output,window,season])[:24],record_kind='forecast_evaluation_view',method=method,procedure_id=group[0].get('procedure_id',method),target=group[0]['target'],category=group[0]['target'],season=season,actual_weeks=sorted({r['week']for r in rr}),window=str(window),week_view=str(window),output=output,eligible=len(rr),available=len(rr),unavailable=0,unknown=unknown,games=len({r['game_id']for r in rr}),player_games=len({key(r)for r in rr}),numerical=numeric(scorable),count_log_loss='Infinity'if infinite else sum(count_ll)/len(count_ll)if count_ll else None,infinite_count_logloss_cases=infinite,law_events=len(count_ll)+infinite,fallback_states=dict(collections.Counter(str(r.get('fallback'))for r in rr)),history_regime='H-RECENT',evidence_tier='CURRENT_VINTAGE_7DAY_CHRONOLOGICAL_RECONSTRUCTION;STAT_ROW_CONDITIONAL_QUERY_UNIVERSE;NO_OFFER_REQUIRED',primary_admission='LOCAL_NOT_C_ADMITTED',evaluation_panel_id=f'B-M2-{season}-QB-STAT-ROW-NUMERICAL'))
    for output in ('mean','median'):
      for window in ['ALL']+list(range(1,10)):
        group=cp['rows']if window=='ALL'else[r for r in cp['rows']if r['week']==window];good=[];unknown=0
        for r in group:
            q=querymap.get((r['game_id'],r['player_id']))
            if q is None or not q.get('physical_participation')or not q.get('target_parity'):unknown+=1;continue
            if dt(r['fit_origin_UTC'])>dt(r['kickoff_UTC']):raise ValueError('C point fit cutoff after game')
            good.append(dict(point=r[output],actual=q['official_completions']))
        broad.append(dict(record_id='B-M2-C-NUMERIC-'+digest([output,window])[:24],record_kind='forecast_evaluation_view',method='RETAINED_C_E0_ENV',procedure_id=cp['procedure'],target='pass_cmp',category='pass_cmp',season=2026,actual_weeks=sorted({r['week']for r in group}),window=str(window),week_view=str(window),output=output,eligible=len(group),available=len(group),unavailable=0,unknown=unknown,games=len({r['game_id']for r in group}),player_games=len({(r['game_id'],r['player_id'])for r in group}),numerical=numeric(good),count_log_loss=None,law_events=0,probability_missing_reason='C exported typed points only; no invented count law.',fallback_states=dict(collections.Counter(str(r['fallback'])for r in group)),history_regime='H-MULTI',evidence_tier='CURRENT_VINTAGE_7DAY_CHRONOLOGICAL_RECONSTRUCTION;STAT_ROW_CONDITIONAL_QUERY_UNIVERSE;NO_OFFER_REQUIRED',primary_admission='LOCAL_NOT_C_ADMITTED',evaluation_panel_id='B-M2-2026-QB-STAT-ROW-NUMERICAL'))
    pairs=[]
    contrasts=[('M2_P2_BB','M2_P2_BIN'),('M2_C1_BB','M2_C1_BIN'),('M2_C2_BB','M2_C2_BIN'),('M2_C2_BB','M2_C1_BB'),('M2_C2_BIN','M2_C1_BIN'),('D_M2','M2_P2_BIN')]
    controls=[('RETAINED_B0','P2_STATISTICAL_LAW'),('RETAINED_SAVED_ADJUSTED','REGISTERED_DIRECTION'),('RETAINED_EARLIER_LINE_PREVALENCE','REGISTERED_DIRECTION'),('RETAINED_ALWAYS_OVER','REGISTERED_DIRECTION'),('RETAINED_ALWAYS_UNDER','REGISTERED_DIRECTION')]
    def pair(candidate,policy,cc,control,cp,dd,scope):
        lookup={key(r):r for r in dd};same=[(r,lookup[key(r)])for r in cc if key(r)in lookup and r['status']in('WIN','LOSS')and lookup[key(r)]['status']in('WIN','LOSS')]
        z=paired_losses([int(r['status']=='LOSS')for r,s in same],[int(s['status']=='LOSS')for r,s in same],[(2026,r['week'])for r,s in same],[r['game_id']for r,s in same])
        return dict(candidate=candidate,procedure_id=cc[0]['procedure_id']if cc else candidate,policy=policy,control=control,comparator_procedure_id=dd[0]['procedure_id']if dd else control,control_policy=cp,target=cc[0]['category']if cc else'pass_cmp',scope=scope,metric='SELECTION_LOSS_RATE',history_regime='H-RECENT',candidate_selected=sum(r['selected_side']in('OVER','UNDER')for r in cc),common_decided=len(same),candidate_wins=sum(r['status']=='WIN'for r,s in same),control_wins=sum(s['status']=='WIN'for r,s in same),side_disagreements=sum(r['selected_side']!=s['selected_side']for r,s in same),membership_SHA256=digest(sorted(key(r)for r,s in same)),**z)
    for candidate,control in contrasts:
        for policy in ('MEAN','MEDIAN','LAW'):pairs.append(pair(candidate,policy,raw[candidate,policy],control,policy,raw[control,policy],'MATCHED_COMPLETE_PIPELINE'))
        aa=raw[candidate,'LAW'];bb={key(r):r for r in raw[control,'LAW']};same=[(r,bb[key(r)])for r in aa if r['probs']is not None and bb[key(r)]['probs']is not None]
        for metric in ('STRICT_BINARY_OVER_BRIER','EXACT_LINE_LOG_LOSS'):
            def loss(r):
                if metric=='STRICT_BINARY_OVER_BRIER':return(r['probs']['over']-int(r['actual']>r['line']))**2
                event='over'if r['actual']>r['line']else'under'if r['actual']<r['line']else'push';p=r['probs'][event]
                return-math.log(p)if p>0 else math.inf
            z=paired_losses([loss(r)for r,s in same],[loss(s)for r,s in same],[(2026,r['week'])for r,s in same],[r['game_id']for r,s in same])
            pairs.append(dict(candidate=candidate,procedure_id=aa[0]['procedure_id'],policy='LAW',control=control,comparator_procedure_id=bb[key(aa[0])]['procedure_id'],control_policy='LAW',target='pass_cmp',scope='MATCHED_COMPLETE_PIPELINE_PROBABILITY',metric=metric,history_regime='H-RECENT',membership_SHA256=digest(sorted(key(r)for r,s in same)),**z))
    for method in METHODS:
        for policy in ('MEAN','MEDIAN','LAW'):
            for control,cp in controls:pairs.append(pair(method,policy,raw[method,policy],control,cp,raw[control,cp],'MATCHED_FULL_BOARD'))
        for (m,policy),rr in selected_frames.items():
            if m!=method:continue
            for control,cp in controls:
                pairs.append(pair(method,policy,rr,control,cp,raw[control,cp],'CANDIDATE_OWN_SELECTED_CASES_CONTROL_BROAD_SIDES'))
    # Independent future-outcome mutation of the evaluation selector/calibrator.
    fixture=raw[METHODS[0],'LAW'];before=calibrated(fixture,origins[2026,7]);changed=copy.deepcopy(fixture)
    for r in changed:
        if r['week']==9:r['actual']=r['actual']+1000;r['status']='LOSS'if r['status']=='WIN'else'WIN'
    after=calibrated(changed,origins[2026,7]);assert [r.get('calibrated_probs')for r in before if r['week']<=7]==[r.get('calibrated_probs')for r in after if r['week']<=7]
    for q in (1,2,4,10):
        for w in range(5,10):
            rr=[r for r in fixture if r['week']==w];chosen=choose_fraction(rr,1,q)
            assert len(chosen)<=len(rr)//q
            for kickoff in sorted({r['kickoff']for r in rr},key=dt):
                prefix=[r for r in rr if dt(r['kickoff'])<=dt(kickoff)]
                assert choose_fraction(prefix,1,q)=={k for k in chosen if any(key(r)==k for r in prefix)}
    proper=[]
    for method in list(METHODS)+['UNCHANGED_ATT']:
      for mode in ('RAW','CALIBRATED_RELIABILITY'):
        frames=raw[method,'LAW']if mode=='RAW'else selected_frames[method,'THRESHOLD_75_CALIBRATED_RELIABILITY']
        for window,rr in [('ALL',frames)]+[(str(w),[r for r in frames if r['week']==w])for w in range(5,10)]:
            stat=probstats(rr,'probs'if mode=='RAW'else'calibrated_probs')
            proper.append(dict(record_id='B-M2-PROB-'+digest([method,mode,window])[:24],record_kind='prop_threshold_probability_evaluation',method=method,procedure_id=rr[0]['procedure_id'],target=rr[0]['category'],category=rr[0]['category'],season=2026,actual_weeks=sorted({r['week']for r in rr}),window=window,week_view=window,policy='RAW_EXACT_LINE_LAW'if mode=='RAW'else'CALIBRATED_RAW_SIDE_CORRECTNESS_BERNOULLI',population='FULL_DECLARED_NATIVE_QB_OFFER_BOARD;CONDITIONAL_QUALIFIED_PLAYED_LABELS',probability_conditioning='MODELED_APPEARANCE',probability_score_contract='HALF_MULTICLASS_BRIER_OVER_UNDER_PUSH_V1',n=stat['events'],probability_events=stat['events'],brier=stat['half_three_state_Brier'],strict_binary_Over_Brier=stat['strict_binary_Over_Brier'],log_loss=stat['log_loss'],infinite_logloss_cases=stat['infinite_logloss_cases'],points=None,eligible=len(rr),available=sum(r['available']for r in rr),unavailable=sum(not r['available']for r in rr),games=len({r['game_id']for r in rr}),player_games=len({key(r)for r in rr}),calibration_mode=mode,calibration_support=dict(collections.Counter(r.get('calibration_n',0)for r in rr)),joint_scope='CALIBRATED_RELIABILITY_IS_NOT_A_COUNT_OR_JOINT_DISTRIBUTION'if mode!='RAW'else'STANDALONE_DIRECT_CMP_NO_JOINT_CLAIM'if method=='D_M2'else'RAW_STRUCTURED_COMPLETION_OR_ATTEMPT_LAW',evidence_tier='TIER_B_CURRENT_VINTAGE_CHRONOLOGICAL_RETAINED_ACTUAL_SOURCE_LINES;QUOTE_CLOCK_UNKNOWN;MAIN_ALT_UNCLASSIFIED',primary_admission='LOCAL_NOT_C_ADMITTED',history_regime='H-RECENT',evaluation_panel_id='B-M2-2026-NATIVE-QB142-'+rr[0]['category'],membership_SHA256=digest(sorted(key(r)for r in rr))))
    write(HERE/'MAIN_TABLES_V1.json.gz',tables)
    write(HERE/'SELECTIVE_TABLES_V1.json.gz',selective)
    write(HERE/'BROAD_NUMERICAL_TABLES_V1.json.gz',broad)
    write(HERE/'PAIRED_COMPARISONS_V1.json',pairs)
    write(HERE/'CALIBRATION_SUPPORT_TRACE_V1.json',calibration_trace)
    write(HERE/'PROBABILITY_TABLES_V1.json.gz',proper)
    canonical=[r for r in tables if r['canonical_source_view']]+selective+broad+proper
    assert len({r['record_id']for r in canonical})==len(canonical)
    write(HERE/'SCORES.json',canonical)
    write(HERE/'MEMBERSHIP_COMMITMENTS_V1.json',[{'method':m,'policy':p,'category':rr[0]['category'],'selected_keys_sha256':digest(sorted(key(r)for r in rr if r['selected_side']in('OVER','UNDER'))),'selected':sum(r['selected_side']in('OVER','UNDER')for r in rr)}for(m,p),rr in selected_frames.items()])
    publicbytes=sum(p.stat().st_size for p in HERE.iterdir()if p.is_file())
    if publicbytes>8388608:raise RuntimeError('Frozen8MiB evaluation-public-retention cap exceeded; preserve completed outputs and qualify a repair separately.')
    if time.process_time()-cpu>600 or time.monotonic()-started>900:raise RuntimeError('Frozen evaluation runtime cap exceeded')
    write(HERE/'RUN_RECEIPT_V1.json',dict(state='EXECUTED_NEW_M2_LOCAL_NOT_C_ADMITTED',at_UTC=datetime.now(timezone.utc).isoformat(),protocol_sha256=sha(HERE/PROTOCOL),code_sha256=sha(__file__),models=list(METHODS),native_CMP_offers=142,native_ATT_offers=142,actual_offer_weeks=[5,6,7,8,9],missing_offer_weeks=[1,2,3,4],source_reads_by_execution=0,new_fits=0,new_NFL_observations=0,original_pregame_selections=0,main_views=len(tables),selective_views=len(selective),broad_numeric_views=len(broad),proper_probability_views=len(proper),canonical_views=len(canonical),paired_views=len(pairs),law_checks=law_checks,boundary_fixtures=fixture_checks,future_outcome_mutation='PASS_EARLIER_CALIBRATION_UNCHANGED',batch_prefix_invariance='PASS',CPU_seconds=time.process_time()-cpu,wall_seconds=time.monotonic()-started,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,private_restricted_rows_written=0,public_bytes=publicbytes,C_or_website_admission=False))
    print(json.dumps({'state':'EXECUTED','canonical_views':len(canonical),'pairs':len(pairs),'seconds':time.process_time()-cpu}))

if __name__=='__main__':
    from threadpoolctl import threadpool_limits
    with threadpool_limits(limits=2):main()
