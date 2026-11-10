"""New output adapter through existing graders; private offers never exported."""
import argparse, collections, importlib.util, json, math, resource, sys, time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools import score_player_context_wave as s
from nfl_v2 import player_context_matchup as ctx
from nfl_v2.paired_uncertainty import paired_losses
from nfl_v2.empirical_benchmark import Series

BASE=ROOT/'reports/player-context-matchup-01/B'
NEW=('D1','D2','C1','C2')
POLICIES=('P1_MEAN','P1_LOWER_MEDIAN','P2_STATISTICAL_LAW','P90')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('action',choices=['prepare','score']);ap.add_argument('--wave',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--sources',type=Path,required=True);ap.add_argument('--old-predictions',type=Path,nargs='*',default=[]);a=ap.parse_args();a.out=a.out.resolve()
    paths={int(w):Path(p)for w,p in s.read(a.sources).items()}
    if a.action=='prepare':
        a.out.mkdir(parents=True,exist_ok=False)
        s.write(a.out/'FROZEN_SCORING_PROTOCOL.json',dict(id='B-DEPTH-CATCHABILITY-SCORES-v1',at_utc=s.now(),code_sha256=s.sha(__file__),
            grader_sha256=s.sha(ROOT/'nfl_v2/scoring.py'),reused_adapter_sha256=s.sha(s.__file__),producer_protocol_sha256=s.sha(a.wave/'FROZEN_PROTOCOL.json'),
            sources=[dict(week=w,sha256=s.sha(p),bytes=p.stat().st_size)for w,p in paths.items()],
            old_sources=[dict(sha256=s.sha(p),bytes=p.stat().st_size)for p in a.old_predictions],
            targets=['pass_cmp'],numeric='2025full and2026W1-8, eachweek, W1-4, W5+, W1-8. Separate2026matched112offers and129coveredgamequeries.',
            offers='Existing exact112CMPoffers W5-8 only. Controls E1/P1/E3/F2, raw/adjusted,constants, earlierprevalence,neutral. No fabricated2025lines.',
            own_information='Reuse empirical_benchmark.Series on own last8 eligible outcomes only; own mean/lower median, no shared prior/features. No ownhistory => unavailable, not confidence abstention. This small control is not another learner or probability law.',
            policies=POLICIES,topK='Reuse frozen perweek/percategory/per-sidepool chronological kickoffbatch6/10/20; no forced replacement, quote-timeunverified diagnostic only.',
            budget=dict(fits=0,new_private_derivative_bytes=0,wall_seconds=600,max_RSS_bytes=2147483648,public_bytes=16777216),
            stopping='All registered methods/periods once; no evaluated-outcome rule/window tuning. Four offeredweeks do not meetfiveweekprimaryfloor.',evidence=s.TIER))
        print('FROZEN_SCORING');return
    start=time.monotonic();p=s.read(a.out/'FROZEN_SCORING_PROTOCOL.json');assert p['code_sha256']==s.sha(__file__)and p['grader_sha256']==s.sha(ROOT/'nfl_v2/scoring.py')
    assert s.read(a.wave/'RUN_RECEIPT.json')['state']=='COMPLETE'
    for r in p['sources']:assert s.sha(paths[r['week']])==r['sha256']
    inputs=ctx.load_inputs(BASE/'source-fields-v3/DERIVED_QB_GAME_INPUTS.json.gz');history=ctx.ContextHistory(inputs,8,20);qmap={(q['game_id'],q['player_id']):q for q in inputs}
    rows=[r for f in sorted((a.wave/'predictions').glob('*.json.gz'))for r in s.read(f)['rows']]
    controls=[r for f in sorted((BASE/'qb-wave-v1/predictions').glob('*.json.gz'))for r in s.read(f)['rows']if r['method']in('E1','P1','E3')]
    controls += [r for f in sorted((BASE/'qb-charting-wave-v1/predictions').glob('*.json.gz'))for r in s.read(f)['rows']if r['method']=='F2']
    # A genuine own-information point control, using the existing exact Series.
    for q in inputs:
        if q['season']not in(2025,2026):continue
        own=history.player_rows(q['player_id'],q['kickoff']);z=Series([(r['available'],r['game_id'],r['official_completions'])for r in own]).at(q['kickoff'])
        controls.append(dict(procedure_id='B-OWN-INFORMATION-EMPIRICAL8-v1',method='OWN8',game_id=q['game_id'],player_id=q['player_id'],target='pass_cmp',season=q['season'],week=q['week'],mean=z[1],lower_median=z[2],actual=q['official_completions']if q['physical_participation']else None,
            own_prior_games=z[0],fallback='none',unavailability_reason=None if z[0]else'NO_OWN_HISTORY',pregame_role_band='OWN_ONLY_NO_SHARED_INPUTS'))
    indexed={(r['method'],s.key(r)):r for r in rows+controls}
    spec=importlib.util.spec_from_file_location('retained_offer_inventory',BASE/'independent/inventory_retained_qb_offers_v1.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    offers=[r for w in range(5,9)for r in m.iter_offers(paths[w],w)if r['target']=='pass_cmp'];assert len(offers)==112 and len({s.key(r)for r in offers})==112
    keys={s.key(r)for r in offers};games={r['game_id']for r in offers};old=s.old_predictions(a.old_predictions,{s.key(r)for r in rows})if a.old_predictions else{}
    scores=[];pairs=[];perplayer=[];by=collections.defaultdict(list)
    for r in rows+[r for r in controls if r['method']=='OWN8']:by[r['season'],r['method']].append(r)
    for(season,method),rr in sorted(by.items()):
        proc=rr[0]['procedure_id']
        windows=[('ALL',rr),('W1_4',[r for r in rr if r['week']<=4]),('W5_PLUS',[r for r in rr if r['week']>=5]),('W1_8',[r for r in rr if r['week']<=8])]+[(w,[r for r in rr if r['week']==w])for w in sorted({r['week']for r in rr})]
        if season==2026:windows += [('MATCHED_OFFERS_W5_W8',[r for r in rr if s.key(r)in keys]),('COVERED_GAMES_W5_W8',[r for r in rr if r['game_id']in games])]
        for window,sub in windows:
            for product in('mean','lower_median'):
                for scope,rs in [('FULL_SYSTEM',[r for r in sub if r.get(product)is not None]),('LEARNED',[r for r in sub if r.get(product)is not None and not s.isfallback(r)]),('FALLBACK',[r for r in sub if s.isfallback(r)])]:
                    v=s.pointview(rs,sub,season,window,proc,product,scope)
                    if method=='OWN8':v['history_regime']='OWN_LAST8_EXPANDING_2022_NO_POOLING';v['technical_unavailable']=len(sub)-sum(r.get(product)is not None for r in sub)
                    scores.append(v)
        for product in('mean','lower_median'):
            rr=[r for r in rr if r.get(product)is not None] if method=='OWN8' else rr
            for pid in sorted({r['player_id']for r in rr}):
                own=[r for r in rr if r['player_id']==pid and r['actual']is not None]
                perplayer.append(dict(season=season,method=proc,player_id=pid,product=product,**s.scoring.point_metrics([r[product]for r in own],[r['actual']for r in own],'pass_cmp')))
            for cm in ['E1','P1','E3','F2','OWN8']+(['D1']if method=='D2'else['C1']if method=='C2'else[]):
                for scope in('FULL_SYSTEM','COMMON_LEARNED'):
                    same=[(r,indexed[cm,s.key(r)])for r in rr if r['actual']is not None and indexed[cm,s.key(r)].get(product)is not None and(scope=='FULL_SYSTEM'or not s.isfallback(r)and not s.isfallback(indexed[cm,s.key(r)]))]
                    pairs.append(dict(kind='NUMERICAL_PAIRED_MAE',season=season,candidate=proc,control=cm,product=product,scope=scope,**paired_losses([abs(r[product]-r['actual'])for r,b in same],[abs(b[product]-b['actual'])for r,b in same],[(season,r['week'])for r,b in same],[r['game_id']for r,b in same])))
            for oldid,dd in old.items():
                same=[(r,dd[s.key(r),product])for r in rr if r['actual']is not None and(s.key(r),product)in dd]
                if same:pairs.append(dict(kind='NUMERICAL_PAIRED_MAE',season=season,candidate=proc,control=oldid,product=product,scope='EXACT_COMPATIBLE_RETAINED_POINT_MASK',**paired_losses([abs(r[product]-r['actual'])for r,b in same],[abs(b['prediction']-b['actual'])for r,b in same],[(season,r['week'])for r,b in same],[r['game_id']for r,b in same])))
    grades={};tables=[];commitments=[]
    methods=list(NEW)+['E1','P1','E3','F2','OWN8','SAVED_ADJUSTED','SAVED_RAW','ALWAYS_OVER','ALWAYS_UNDER','EARLIER_LINE_PREVALENCE','NEUTRAL_HALFPOINT']
    for method in methods:
        policies=POLICIES if method in NEW or method in('E1','P1','E3','F2')else('P1_MEAN','P1_LOWER_MEDIAN')if method=='OWN8'else('REGISTERED_DIRECTION',)
        for policy in policies:
            gg=[]
            for i,r in enumerate(offers):
                pred=indexed.get((method,s.key(r)));point=None;probs=None;sd=None;fallback='none';unavailable=False
                if pred:
                    assert pred['actual']==r['actual'];point=pred['mean'if policy=='P1_MEAN'else'lower_median'];fallback=pred['fallback']
                    if pred.get('law'):probs=ctx.exact_probabilities(s.law(pred),r['line'])
                    unavailable=point is None
                    sd=s.sidepoint(point,r['line'])if policy.startswith('P1_')else'over'if probs['over']>probs['under']else'under'if probs['under']>probs['over']else None
                    if policy=='P90'and(sd is None or probs[sd]<.9):sd=None
                elif method in('SAVED_ADJUSTED','SAVED_RAW'):
                    point=r.get('prediction'if method=='SAVED_ADJUSTED'else'raw_prediction');sd=s.sidepoint(point,r['line']);unavailable=point is None
                elif method in('ALWAYS_OVER','ALWAYS_UNDER'):sd='over'if method=='ALWAYS_OVER'else'under'
                elif method=='NEUTRAL_HALFPOINT':
                    if float(r['line'])%1==.5:probs=dict(over=.5,under=.5,push=0.)
                else:
                    q=qmap[r['game_id'],r['player_id']];earlier=history.eligible(q['kickoff'],2025);yy=[x['official_completions']for x in earlier];whole=float(r['line']).is_integer();den=len(yy)+(3 if whole else 2)
                    probs=dict(over=(sum(y>r['line']for y in yy)+1)/den,under=(sum(y<r['line']for y in yy)+1)/den,push=(sum(y==r['line']for y in yy)+1)/den if whole else 0.)
                    sd='over'if probs['over']>probs['under']else'under'if probs['under']>probs['over']else None
                state='ABSTAIN'if sd is None else s.scoring.threshold_crossing(r['actual'],r['line'],sd,target='pass_cmp')
                gg.append(dict(r,source_row_index=i,selected_side=sd,statistical_state=state,settlement_state='UNRESOLVED_CONTRACT',net_return=None,strategy=policy,ranking_point=point,technical_unavailable=unavailable,probs=probs,fallback=fallback,pregame_role_band=pred['pregame_role_band']if pred else'CONTROL_SCOPE',source_cohorts=[],forecast_method=method))
            grades[method,policy]=gg
            proc=next(r['procedure_id']for r in rows if r['method']==method)if method in NEW else'B-OWN-INFORMATION-EMPIRICAL8-v1'if method=='OWN8'else method
            for window,sub in [('ALL',gg)]+[(w,[r for r in gg if r['week']==w])for w in range(5,9)]:
                vv=s.summary(sub,2026,window,proc,policy,'pass_cmp')
                tables.append(dict(method=proc,policy=policy,window=window,sides=[dict(side=v['side'],metrics=v['selection_metrics'])for v in vv],probability=s.probability_stats(sub),games=len({r['game_id']for r in sub})))
                if method in NEW or method=='OWN8':
                    if method=='OWN8':
                        for v in vv:v['history_regime']='OWN_LAST8_EXPANDING_2022_NO_POOLING'
                    scores+=vv
                    if policy=='P2_STATISTICAL_LAW':
                        z=s.probability_stats(sub);scores.append(dict(s.panelmeta(sub,2026,window),**z,record_kind='prop_threshold_probability_evaluation',target='pass_cmp',procedure_id=proc,product_id='EXACT_LINE_OVER_UNDER_PUSH',record_id='DEPTH-PROB-'+s.digest([method,window])[:24],forecast_rows=z['n'],outer_offer_rows=len(sub),probability_conditioning='MODELED_APPEARANCE',probability_score_contract='HALF_MULTICLASS_BRIER_OVER_UNDER_PUSH_V1',mae=None,mse=None,evidence=s.TIER))
            if method in NEW and policy=='P2_STATISTICAL_LAW':
                for w in range(5,9):
                    weekly=[r for r in gg if r['week']==w]
                    for pool in('Combined','over','under'):
                        for K in(6,10,20):
                            slots=K;chosen=[]
                            for t in sorted({r['kickoff']for r in weekly}):
                                ee=[r for r in weekly if r['kickoff']==t and r['selected_side']and(pool=='Combined'or r['selected_side']==pool)]
                                ee.sort(key=lambda r:(-r['probs'][r['selected_side']],r['game_id'],r['player_id'],str(r['line'])));chosen+=ee[:slots];slots-=min(slots,len(ee))
                            ids={r['source_row_index']for r in chosen};ranked=[dict(r,selected_side=r['selected_side']if r['source_row_index']in ids else None,statistical_state=r['statistical_state']if r['source_row_index']in ids else'ABSTAIN')for r in weekly]
                            scores+=s.summary(ranked,2026,w,proc,'ROLLING_TOP_K_DIAGNOSTIC','pass_cmp',rank_scope=pool,K=K)
            commitments.append(dict(method=proc,policy=policy,rows=len(gg),calculations_sha256=s.digest([{k:r.get(k)for k in('game_id','player_id','target','line','selected_side','actual','statistical_state','probs')}for r in gg]),restricted_rows_exported=False))
    for method in NEW:
        for cm in ['E1','P1','E3','F2','SAVED_ADJUSTED','SAVED_RAW','ALWAYS_OVER','ALWAYS_UNDER','EARLIER_LINE_PREVALENCE']+(['D1']if method=='D2'else['C1']if method=='C2'else[]):
            policy='P2_STATISTICAL_LAW';bp=policy if(cm,policy)in grades else'REGISTERED_DIRECTION'
            for window in('ALL',5,6,7,8):
                same=[(r,b)for r,b in zip(grades[method,policy],grades[cm,bp])if(window=='ALL'or r['week']==window)and r['statistical_state']in('WIN','LOSS')and b['statistical_state']in('WIN','LOSS')]
                pairs.append(dict(kind='OFFER_DIRECTION_PAIRED_LOSS',season=2026,window=window,candidate=method,control=cm,policy=policy,candidate_wins=sum(r['statistical_state']=='WIN'for r,b in same),control_wins=sum(b['statistical_state']=='WIN'for r,b in same),**paired_losses([float(r['statistical_state']=='LOSS')for r,b in same],[float(b['statistical_state']=='LOSS')for r,b in same],[(2026,r['week'])for r,b in same],[r['game_id']for r,b in same])))
    s.write(a.out/'SCORES.json',scores);s.write(a.out/'COMMON_CONTROL_TABLE.json',tables);s.write(a.out/'PAIRED_COMPARISONS.json',pairs);s.write(a.out/'PER_PLAYER_NUMERICAL.json',perplayer);s.write(a.out/'OWNER_LOCAL_COMMITMENTS.json',commitments)
    s.write(a.out/'RUN_RECEIPT.json',dict(state='COMPLETE_LOCAL_NOT_C_ADMITTED',at_utc=s.now(),new_fits=0,new_forecasts=0,canonical_views=len(scores),paired_views=len(pairs),new_offer_weeks=0,actual_offer_weeks=[5,6,7,8],unique_offers=112,unique_games=56,new_private_row_derivative_bytes=0,wall_seconds=time.monotonic()-start,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024))
    print(json.dumps(s.read(a.out/'RUN_RECEIPT.json')))

if __name__=='__main__':main()
