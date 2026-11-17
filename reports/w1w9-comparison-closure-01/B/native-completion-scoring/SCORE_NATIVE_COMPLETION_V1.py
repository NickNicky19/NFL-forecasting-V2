"""Saved-output B adapter into the unchanged pinned C grader. No fitting/acquisition.

FTN-derived B2 forecasts: FTN Data via nflverse, CC-BY-SA-4.0.
Private actual offers and per-opportunity calculations remain owner-local.
"""
import argparse
import collections
import gzip
import hashlib
import importlib.util
import json
import math
import resource
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


def read(p):
    p=Path(p); body=p.read_bytes()
    return json.loads(gzip.decompress(body) if p.suffix=='.gz' else body)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def digest(x):
    return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def write(p,x):
    p=Path(p)
    if p.exists():raise FileExistsError(p.name)
    p.parent.mkdir(parents=True,exist_ok=True)
    body=(json.dumps(x,separators=(',',':'),allow_nan=False)+'\n').encode()
    p.write_bytes(gzip.compress(body,mtime=0) if p.suffix=='.gz' else body)


def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('action',choices=['prepare','score'])
    for name in ['sources','scorer-source','interval-source','private-output']:
        ap.add_argument('--'+name,type=Path,required=True)
    a=ap.parse_args();out=Path(__file__).resolve().parent;base=out.parent;repo=out.parents[3]
    sys.path.insert(0,str(repo))
    from tools import score_player_context_wave as b
    from nfl_v2 import player_context_matchup as ctx
    from nfl_v2.distribution_laws import Law
    from nfl_v2.paired_uncertainty import paired_losses
    adapter=module(base/'common-intake/COMMON_SCORER_PARITY_ADAPTER_V1.py','pinned_common_adapter')
    status,summary,interval=adapter.load_common_functions(a.scorer_source,a.interval_source)
    legacy=base/'legacy-completion-extension'
    modern=base/'modern-completion-extension'
    ftndir=repo/'reports/information-first-20261112-01/B/completion-wave-v1'
    olddir=repo/'reports/player-context-matchup-01/B/qb-wave-v1'
    aligned=repo/'reports/profile-increment-closure-next-02/B/aligned-wave-v1'
    sourcepaths={int(w):Path(p)for w,p in read(a.sources).items()}
    prediction_paths=(sorted((ftndir/'predictions').glob('2026-W*.json.gz'))+
        sorted((olddir/'predictions').glob('2026-W*.json.gz'))+
        sorted((aligned/'predictions').glob('2026-W*.json.gz'))+
        [modern/'PREDICTIONS_2026_W09.json.gz',legacy/'OLD_W1_W7_PREDICTIONS_V1.json.gz',legacy/'PREDICTIONS_W8_W9_V1.json.gz'])
    required=[base/'roster/FROZEN_B_CONTRIBUTION_ROSTER_V1.json',base/'source-policy/FROZEN_NAMED_COMPLETION_PANEL_V1.json',
        base/'source-policy/NATIVE_W5_W9_SOURCE_QUALIFICATION_V1.json',legacy/'ALIAS_AND_HISTORY_POLICY_BINDINGS_V2.json',
        base/'common-intake/COMMON_SCORER_PARITY_ADAPTER_V1.py',repo/'tools/score_player_context_wave.py',
        repo/'nfl_v2/player_context_matchup.py',repo/'nfl_v2/distribution_laws.py',repo/'nfl_v2/scoring.py',
        repo/'reports/player-context-matchup-01/B/independent/inventory_retained_qb_offers_v1.py',
        ftndir/'QB_CONTEXT_W1_W9_INPUTS_V1.json.gz']+prediction_paths
    protocolpath=out/'FROZEN_NATIVE_SCORING_PROTOCOL_V1.json'
    if a.action=='prepare':
        protocol=dict(id='B_NATIVE142_EXISTING_COMPLETION_FIXED_ROSTER_SCORES_v1',registered_UTC=now(),owner='B',coordinator='C',
            state='FROZEN_BEFORE_NEW_COMPARATIVE_SCORES',code_SHA256=sha(__file__),
            source_bindings=[dict(week=w,SHA256=sha(p),bytes=p.stat().st_size)for w,p in sorted(sourcepaths.items())],
            public_input_bindings=[dict(path=str(p.relative_to(repo)),SHA256=sha(p),bytes=p.stat().st_size)for p in required],
            C_scorer_SHA256=sha(a.scorer_source),C_interval_SHA256=sha(a.interval_source),
            panel='2026REGW5-9 native142 retained source-labelled real completion lines;141DK+1SleeperPicks;quote clocks unknown;main/alternate unclassified',
            methods=['B0','B1_EXACT_B0_ALIAS','B2','E3','F2','P1','C02_WHOLE_BOARD_CONTINUATION','DIRECT_GLM_WHOLE_BOARD_CONTINUATION','C02_KNOWN_TARGET_TIME','DIRECT_GLM_KNOWN_TARGET_TIME'],
            controls=['SAVED_ADJUSTED','SAVED_RAW','ORIGINAL_SOURCE_LEAN','ALWAYS_OVER','ALWAYS_UNDER','EARLIER_LINE_PREVALENCE'],
            direction='Existing P1 unrounded strict mean/lower median vs exact line, equality abstains; P2 exact Over/Under mass argmax, ties abstain; P90 unchanged selected-side mass>=0.90.',
            legacy_contract='Whole-board weekly-kickoff retrospective continuation IDs are DISTINCT from known-target-time IDs. Original alias mask96/142:W5=28,W6=27,W7=25,W8=16,W9=0; technical exclusion is unavailable, not abstention.',
            probabilities='Exact law only, no point-derived probability. Half multiclass Over/Under/Push Brier plus strict binary P(Y>line) Brier, three-state logloss, native confidence bins and separate width0.1 Over bins. No averaging AUC or incompatible Brier contracts.',
            numerical='Only typed point policies/point controls receive point errors on same offered rows. No mean/median silently assigned to a law-direction/P90 output.',
            selective='Existing P90 all main laws; existing per-week/side-pool chronological kickoff-batch Top6/10/20 only B0/B2 and two legacy whole-board laws. No new threshold, mapping, side inversion or quota.',
            intervals='Pinned unchanged C status/summary/interval; existing B paired_losses for same-case model/control differences. Exposed retrospective diagnostics, not untouched future evidence.',
            timing='Current-vintage chronological reconstruction, no original issuance, authenticated quote clocks, pregame roster or primary admission claimed.',
            canonical='B1 exact alias included in human/machine tables, omitted from duplicate canonical score list. Root alone registers canonical artifacts and assembles early union.',
            budgets=dict(CPU_seconds=600,wall_seconds=900,public_bytes=8388608,new_HTTP=0,new_fits=0),
            retention='Private offer/grade rows remain owner-local. Public output aggregates/hashes only; FTN Data via nflverse CC-BY-SA-4.0 attribution retained.')
        write(protocolpath,protocol);print(json.dumps(dict(state=protocol['state'],SHA256=sha(protocolpath))));return
    start=time.monotonic();cpu=time.process_time();protocol=read(protocolpath)
    assert protocol['code_SHA256']==sha(__file__)
    for p in protocol['public_input_bindings']:assert sha(repo/p['path'])==p['SHA256'],p['path']
    for p in protocol['source_bindings']:assert sha(sourcepaths[p['week']])==p['SHA256']
    adapter.boundary_fixtures(status)
    inventory=module(repo/'reports/player-context-matchup-01/B/independent/inventory_retained_qb_offers_v1.py','native_inventory')
    offers=[r for w,p in sorted(sourcepaths.items())for r in inventory.iter_offers(p,w)if r['target']=='pass_cmp']
    assert len(offers)==142 and len({b.key(r)for r in offers})==142
    assert all(r['participation']=='VERIFIED_PLAYED_POSITIVE_PHYSICAL'and r['label_state']=='SUPPORTED'and r['actual']is not None for r in offers)
    index={};source_for={}
    for p in prediction_paths:
        rows=read(p)['rows']
        for r in rows:
            if r['target']!='pass_cmp' or r['season']!=2026 or r['week']not in range(5,10):continue
            method=r['method']
            if method not in ('B0','B1','B2','E3','F2','P1','C02','DIRECT_GLM'):continue
            # Only F2 from the aligned wave; legacy E3/P1 come from original wave.
            if p.parent==aligned/'predictions' and method!='F2':continue
            if p.parent==olddir/'predictions' and method not in ('E3','P1'):continue
            if p.parent==ftndir/'predictions' and method not in ('B0','B1','B2'):continue
            k=method,b.key(r)
            if k in index:raise ValueError('Ambiguous duplicate saved prediction')
            index[k]=r;source_for[k]=sha(p)
    aliases=read(legacy/'ALIAS_AND_HISTORY_POLICY_BINDINGS_V2.json')
    alias_rows={(r['method'],r['game_id'],r['player_id']):r for r in aliases['rows']}
    ids={r['method']:r for r in aliases['mapping']}
    assert len(alias_rows)==284
    queries=ctx.load_inputs(ftndir/'QB_CONTEXT_W1_W9_INPUTS_V1.json.gz')
    history=ctx.ContextHistory(queries,8,20)
    querymap={(r['game_id'],r['player_id']):r for r in queries}
    def law_of(d):
        kind=d['kind']
        if kind=='gamma_poisson_count':return ctx.CountLaw(d['mean'],d['shape'])
        if kind=='leaf_mixture':return Law('mixture',support=d['support'],weights=d['weights'],prior=law_of(d['prior']),mixture=d['mixture'])
        if kind not in ('zero','geometric','poisson'):raise ValueError('Unregistered law kind')
        return Law(**d)
    model_defs=[(m,m,None)for m in ('B0','B1','B2','E3','F2','P1')]
    model_defs += [(m+'_WHOLE_BOARD',m,'whole')for m in ('C02','DIRECT_GLM')]+[(m+'_KNOWN_TARGET_TIME',m,'known')for m in ('C02','DIRECT_GLM')]
    allrows={};law_checks=0
    for key,method,scope in model_defs:
        pid=(ids[method]['whole_board_reconstruction_continuation_id'] if scope=='whole' else ids[method]['known_target_time_id'])if scope else next(v['procedure_id']for(k,v)in index.items()if k[0]==method)
        for policy in ('P1_MEAN','P1_LOWER_MEDIAN','P2_STATISTICAL_LAW','P90'):
            gg=[]
            for offer in offers:
                pred=index.get((method,b.key(offer)));probs=None;point=None;sd=None;reason=None
                if pred is None:reason='SAVED_PREDICTION_NOT_AVAILABLE'
                elif scope=='known'and alias_rows[method,offer['game_id'],offer['player_id']]['state']!='EXACT_KNOWN_TARGET_TIME_PARITY':reason='NOT_AN_ALIAS_AT_THIS_DECISION'
                else:
                    if pred.get('actual')is not None and pred['actual']!=offer['actual']:raise ValueError('Saved forecast/qualified outcome mismatch')
                    law=law_of(pred['law']);probs=ctx.exact_probabilities(law,offer['line'])
                    if not all(math.isfinite(v)and v>=0 for v in probs.values())or not math.isclose(sum(probs.values()),1,abs_tol=1e-10):raise ValueError('Invalid probability law')
                    if abs(law.mean-pred['mean'])>1e-8:raise ValueError('Typed mean/law mean mismatch')
                    law_checks+=1
                    if policy.startswith('P1_'):
                        point=pred['mean'if policy=='P1_MEAN'else'lower_median'];sd=b.sidepoint(point,offer['line'])
                    else:
                        sd='over'if probs['over']>probs['under']else'under'if probs['under']>probs['over']else None
                        if policy=='P90'and(sd is None or probs[sd]<.90):sd=None
                row=adapter.common_row(offer,sd.upper()if sd else None if reason else'ABSTAIN',appearance='PLAYED',status='UNAVAILABLE_FORECAST'if reason else'ABSTAIN'if sd is None else'READY')
                row.update(model_key=key,procedure_id=pid,policy=policy,probs=probs,point=point,available=reason is None,
                    unavailable_reason=reason,fallback=pred.get('fallback')if pred and reason is None else None,
                    attribution='fallback'if pred and reason is None and b.isfallback(pred)else'learned'if pred and reason is None else'unavailable',
                    line_from=offer['line_from'],kickoff=offer['kickoff'],technical_unavailable=reason is not None,source_forecast_SHA256=source_for.get((method,b.key(offer))),
                    evidence_tier='KNOWN_TARGET_TIME_CONDITIONAL_ALIAS'if scope=='known'else'KICKOFF_RECONSTRUCTION_DIAGNOSTIC',original_issuance=False)
                row['status']=status(row);gg.append(row)
            allrows[key,policy]=gg
    for control in ('SAVED_ADJUSTED','SAVED_RAW','ORIGINAL_SOURCE_LEAN','ALWAYS_OVER','ALWAYS_UNDER','EARLIER_LINE_PREVALENCE'):
        gg=[]
        for offer in offers:
            point=None;probs=None;sd=None;reason=None
            if control in ('SAVED_ADJUSTED','SAVED_RAW'):
                point=offer.get('prediction'if control=='SAVED_ADJUSTED'else'raw_prediction')
                if point is None or not math.isfinite(float(point)):reason='SAVED_POINT_NOT_AVAILABLE';point=None
                else:sd=b.sidepoint(point,offer['line'])
            elif control=='ORIGINAL_SOURCE_LEAN':
                orig=str(offer.get('original_side')or'').lower()
                if orig in ('over','under'):sd=orig
                elif orig in ('none','flat','neutral','push','abstain',''):sd=None
                else:raise ValueError('Unrecognized source lean')
            elif control in ('ALWAYS_OVER','ALWAYS_UNDER'):sd='over'if control=='ALWAYS_OVER'else'under'
            else:
                q=querymap[offer['game_id'],offer['player_id']]
                earlier=history.eligible(q['kickoff'],q['season']-1)
                yy=[r['official_completions']for r in earlier]
                whole=float(offer['line']).is_integer();den=len(yy)+(3 if whole else 2)
                probs=dict(over=(sum(y>offer['line']for y in yy)+1)/den,under=(sum(y<offer['line']for y in yy)+1)/den,push=(sum(y==offer['line']for y in yy)+1)/den if whole else 0.)
                sd='over'if probs['over']>probs['under']else'under'if probs['under']>probs['over']else None
            row=adapter.common_row(offer,sd.upper()if sd else None if reason else'ABSTAIN',appearance='PLAYED',status='UNAVAILABLE_FORECAST'if reason else'ABSTAIN'if sd is None else'READY')
            row.update(model_key=control,procedure_id='B_EXISTING_CONTROL:'+control,policy='REGISTERED_DIRECTION',point=point,probs=probs,available=reason is None,unavailable_reason=reason,
                fallback=None,attribution='reference'if reason is None else'unavailable',line_from=offer['line_from'],kickoff=offer['kickoff'],technical_unavailable=reason is not None)
            row['status']=status(row);gg.append(row)
        allrows[control,'REGISTERED_DIRECTION']=gg
    def probability(rr):
        good=[r for r in rr if r['probs']is not None and r['actual']is not None]
        lower=[dict(r,selected_side=r['selected_side'].lower()if r['selected_side']in('OVER','UNDER')else None)for r in good]
        old=b.probability_stats(lower)
        overbins=[]
        for i in range(10):
            lo=i/10;hi=(i+1)/10
            ss=[r for r in good if lo<=r['probs']['over'] and(r['probs']['over']<hi or i==9 and r['probs']['over']==1)]
            overbins.append(dict(lower=lo,upper=hi,n=len(ss),mean_predicted=sum(r['probs']['over']for r in ss)/len(ss)if ss else None,observed_over=sum(r['actual']>r['line']for r in ss)/len(ss)if ss else None))
        return dict(events=len(good),Brier=sum((r['probs']['over']-int(r['actual']>r['line']))**2 for r in good)/len(good)if good else None,
            binary_event='STRICT_Y_GREATER_THAN_LINE;PUSH_IS_NOT_OVER',three_state_Brier=old['brier'],three_state_log_loss=old['log_loss'],infinite_log_loss_cases=old['infinite_log_losses'],
            Over_event_AUC=old.get('over_event_AUC'),reliability_fixed_binsOver=overbins,reliability_selected_confidence=old.get('reliability'),probability_direction_ties=old.get('probability_direction_ties'),
            score_contract='HALF_MULTICLASS_OVER_UNDER_PUSH_AND_SEPARATE_STRICT_BINARY_OVER',conditioning='MODELED_APPEARANCE')
    def table(key,policy,window,rr):
        result=summary(rr);good=[r for r in rr if r['point']is not None and r['actual']is not None]
        errors=[r['point']-r['actual']for r in good]
        result.update(model_key=key,procedure_id=rr[0]['procedure_id']if rr else allrows[key,policy][0]['procedure_id'],policy=policy,week_view=str(window),
            available=sum(r['available']for r in rr),unavailable=sum(not r['available']for r in rr),unknown=sum(r['status']not in('WIN','LOSS','PUSH','ABSTAIN','UNAVAILABLE_FORECAST')for r in rr),
            selected=result['COMBINED']['selected'],decided=result['COMBINED']['decided'],fallback_states=dict(collections.Counter(str(r['fallback'])for r in rr if r['available'])),
            unavailable_reasons=dict(collections.Counter(r['unavailable_reason']for r in rr if not r['available'])),attribution=dict(collections.Counter(r['attribution']for r in rr)),
            learned_selected=sum(r['attribution']=='learned'and r['selected_side']in('OVER','UNDER')for r in rr),fallback_selected=sum(r['attribution']=='fallback'and r['selected_side']in('OVER','UNDER')for r in rr),
            numerical=dict(scored=len(good),MAE=sum(abs(e)for e in errors)/len(errors)if errors else None,MSE=sum(e*e for e in errors)/len(errors)if errors else None,
                bias=sum(errors)/len(errors)if errors else None,max_absolute_error=max(map(abs,errors))if errors else None,absolute_error_p90=float(np.quantile(np.abs(errors),.9))if errors else None,
                output='mean'if policy=='P1_MEAN'else'lower_median'if policy=='P1_LOWER_MEDIAN'else'RETAINED_SOURCE_POINT'if good else'NOT_A_POINT_PRODUCT'),
            probability=probability(rr),membership_SHA256=digest(sorted((r['game_id'],r['player_id'],r['line'])for r in rr)),
            grade_calculations_SHA256=digest([{k:r.get(k)for k in('game_id','player_id','line','selected_side','actual','status','probs','point','fallback','unavailable_reason')}for r in rr]),
            evidence_tier='TIER_B_RETAINED_REAL_SOURCE_LABELLED_LINES;QUOTE_CLOCK_UNKNOWN;CURRENT_VINTAGE_CHRONOLOGICAL_DIAGNOSTIC',alias_of='B0'if key=='B1'else None,
            distinct_scored_weeks=sorted({r['week']for r in rr if r['status']in('WIN','LOSS')}),scheduled_week_domain=[5,6,7,8,9])
        return result
    tables=[]
    for(key,policy),gg in allrows.items():
        if time.process_time()-cpu>600 or time.monotonic()-start>900:raise RuntimeError('Frozen resource budget reached')
        windows=[('ALL',gg)]+[(str(w),[r for r in gg if r['week']==w])for w in range(5,10)]
        windows += [('DK_ONLY',[r for r in gg if str(r['line_from']).lower()=='dk']),('SLEEPER_ONLY',[r for r in gg if str(r['line_from']).lower()=='sleeper'])]
        windows += [('LEARNED_ONLY',[r for r in gg if r['attribution']=='learned']),('FALLBACK_ONLY',[r for r in gg if r['attribution']=='fallback'])]
        for window,rr in windows:tables.append(table(key,policy,window,rr))
    # Frozen chronological per-week selection, not a new ranking policy.
    top=[]
    for key in ('B0','B2','C02_WHOLE_BOARD','DIRECT_GLM_WHOLE_BOARD'):
        gg=allrows[key,'P2_STATISTICAL_LAW']
        for pool in ('Combined','over','under'):
            for K in (6,10,20):
                cumulative=[]
                for w in range(5,10):
                    weekly=[r for r in gg if r['week']==w];chosen=[];slots=K
                    for kickoff in sorted({r['kickoff']for r in weekly}):
                        eligible=[r for r in weekly if r['kickoff']==kickoff and r['selected_side']in('OVER','UNDER')and(pool=='Combined'or r['selected_side'].lower()==pool)]
                        eligible.sort(key=lambda r:(-r['probs'][r['selected_side'].lower()],r['game_id'],r['player_id'],str(r['line'])))
                        add=eligible[:slots];chosen+=add;slots-=len(add)
                    chosenkeys={(r['game_id'],r['player_id'])for r in chosen}
                    ranked=[]
                    for r in weekly:
                        t=dict(r)
                        if(r['game_id'],r['player_id'])not in chosenkeys and t['available']:t.update(selected_side='ABSTAIN',status='ABSTAIN')
                        ranked.append(t)
                    cumulative+=ranked
                    v=table(key,'P2_STATISTICAL_LAW',str(w),ranked);v.update(policy='REGISTERED_CHRONOLOGICAL_TOP_K_DIAGNOSTIC',pool=pool,K=K,component_policy='P2_STATISTICAL_LAW');top.append(v)
                v=table(key,'P2_STATISTICAL_LAW','ALL',cumulative);v.update(policy='REGISTERED_CHRONOLOGICAL_TOP_K_DIAGNOSTIC',pool=pool,K=K,component_policy='P2_STATISTICAL_LAW');top.append(v)
    pairs=[]
    for key in ('B2','E3','F2','P1','C02_WHOLE_BOARD','DIRECT_GLM_WHOLE_BOARD','C02_KNOWN_TARGET_TIME','DIRECT_GLM_KNOWN_TARGET_TIME'):
        for policy in ('P1_MEAN','P1_LOWER_MEDIAN','P2_STATISTICAL_LAW'):
            for cm,cp in [('B0',policy),('SAVED_ADJUSTED','REGISTERED_DIRECTION'),('EARLIER_LINE_PREVALENCE','REGISTERED_DIRECTION'),('ALWAYS_OVER','REGISTERED_DIRECTION'),('ALWAYS_UNDER','REGISTERED_DIRECTION')]:
                control={b.key(dict(r,target='pass_cmp')):r for r in allrows[cm,cp]}
                same=[(r,control[b.key(dict(r,target='pass_cmp'))])for r in allrows[key,policy]if r['status']in('WIN','LOSS')and control[b.key(dict(r,target='pass_cmp'))]['status']in('WIN','LOSS')]
                z=paired_losses([int(r['status']=='LOSS')for r,s in same],[int(s['status']=='LOSS')for r,s in same],[(2026,r['week'])for r,s in same],[r['game_id']for r,s in same])
                pairs.append(dict(candidate=key,policy=policy,control=cm,control_policy=cp,common_decided=len(same),candidate_wins=sum(r['status']=='WIN'for r,s in same),control_wins=sum(s['status']=='WIN'for r,s in same),side_disagreements=sum(r['selected_side']!=s['selected_side']for r,s in same),membership_SHA256=digest(sorted((r['game_id'],r['player_id'])for r,s in same)),**z))
    private=dict(protocol_SHA256=sha(protocolpath),rows=[r for gg in allrows.values()for r in gg],top_membership_scope='Top-K deterministic from retained full law rows and frozen schedule')
    write(a.private_output,private)
    write(out/'NATIVE_TABLES.json',tables)
    write(out/'SELECTIVE_NATIVE_TABLES.json',top)
    canonical=[]
    for v in tables+top:
        if v['model_key']=='B1':continue
        v=dict(v,record_kind='actual_offer_direction_evaluation',target='pass_cmp',category='pass_cmp',season=2026,actual_weeks=v['weeks'],
            record_id='B-NATIVE142-'+digest([v['model_key'],v['procedure_id'],v['policy'],v['week_view'],v.get('pool'),v.get('K')])[:24],
            evaluation_panel_id='ABC-W1W9-CMP-ANNUAL1_4-NATIVE5_9-DIAGNOSTIC-v1:NATIVE142',source_vintage='CURRENT_VINTAGE_CHRONOLOGICAL_RECONSTRUCTION',primary_admission='LOCAL_NOT_C_ADMITTED')
        canonical.append(v)
    write(out/'NATIVE_SCORES.json',canonical)
    write(out/'PAIRED_NATIVE_COMPARISONS.json',pairs)
    write(out/'GRADE_COMMITMENTS_V1.json',[dict(model_key=k,policy=p,rows=len(gg),grade_calculations_SHA256=digest([{f:r.get(f)for f in('game_id','player_id','line','selected_side','actual','status','probs','point','fallback','unavailable_reason')}for r in gg]))for(k,p),gg in allrows.items()])
    publicbytes=sum(p.stat().st_size for p in out.iterdir()if p.is_file())
    if publicbytes>8388608:raise RuntimeError('Frozen public retention budget exceeded')
    receipt=dict(state='COMPLETE_NATIVE142_PINNED_C_SAVED_OUTPUT_COMPARISON_LOCAL_NOT_C_ADMITTED',completed_UTC=now(),protocol_SHA256=sha(protocolpath),
        code_SHA256=sha(__file__),offers=142,weeks=[5,6,7,8,9],models=len(model_defs),main_views=len(tables),selective_views=len(top),canonical_records=len(canonical),
        paired_records=len(pairs),law_checks=law_checks,private_rows=len(private['rows']),private_grade_SHA256=sha(a.private_output),
        C_scorer_SHA256=protocol['C_scorer_SHA256'],C_interval_SHA256=protocol['C_interval_SHA256'],new_fits=0,new_HTTP=0,new_forecasts=0,new_NFL_observations=0,
        wall_seconds=time.monotonic()-start,CPU_seconds=time.process_time()-cpu,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,public_bytes=publicbytes,
        output_bindings=[dict(path=p.name,SHA256=sha(p),bytes=p.stat().st_size)for p in out.iterdir()if p.is_file()],
        scope='Actual source-labelled line diagnostic only; no original quote clocks/main-line authentication, private A84 parity, nine-week global champion, production admission or served use inferred.')
    write(out/'RUN_RECEIPT_V1.json',receipt)
    print(json.dumps({k:v for k,v in receipt.items()if k!='output_bindings'}))


if __name__=='__main__':main()
