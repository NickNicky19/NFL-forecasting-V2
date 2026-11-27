"""FTN context addition: reuse frozen outputs and the existing local scorer."""
import argparse,collections,importlib.util,json,math,sys,time,resource
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools import score_player_context_wave as s
from nfl_v2 import player_context_matchup as ctx
from nfl_v2.paired_uncertainty import paired_losses

def main():
    ap=argparse.ArgumentParser();ap.add_argument('action',choices=['prepare','score']);ap.add_argument('--wave',type=Path,required=True);ap.add_argument('--base-wave',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    for w in range(5,9):ap.add_argument('--week'+str(w),type=Path,required=True)
    a=ap.parse_args()
    if a.action=='prepare':
        a.out.mkdir(parents=True,exist_ok=False)
        s.write(a.out/'FROZEN_SCORING_PROTOCOL.json',dict(id='B-FTN-CONTEXT-SCORING-v1',at_utc=s.now(),code_sha256=s.sha(__file__),
            reused_adapter_sha256=s.sha(s.__file__),wave_sha256=s.sha(a.wave/'RUN_RECEIPT.json'),
            sources=[dict(week=w,sha256=s.sha(getattr(a,'week'+str(w))))for w in range(5,9)],
            scope='F1support/age versus same-data E1 frozen control;F2charted values versusF1andE1. All2025/2026weeks. Actual-line W5-8,112completionoffers.',
            selection='Same P1mean/median,exact-line physical-panel law direction,P90threshold and chronological game-batchTopK6/10/20 as frozen base. No evaluated-outcome calibration.',
            license='CC-BY-SA-4.0;FTN Data via nflverse. Restricted offer rows not exported.',
            budget=dict(new_fits=0,new_forecasts=0,new_private_derivatives=0,wall_seconds=180,max_RSS_bytes=1073741824,public_retention_bytes=8388608),
            evidence=s.TIER,admission='LOCAL_NOT_C_ADMITTED;only4offeredweeks,notfive-weekprimary-qualified'))
        print('FROZEN');return
    start=time.monotonic();p=s.read(a.out/'FROZEN_SCORING_PROTOCOL.json');assert p['code_sha256']==s.sha(__file__)and p['reused_adapter_sha256']==s.sha(s.__file__)
    rows=[r for path in sorted((a.wave/'predictions').glob('*.json.gz'))for r in s.read(path)['rows']]
    base=[r for path in sorted((a.base_wave/'predictions').glob('*.json.gz'))for r in s.read(path)['rows']if r['method']=='E1']
    controls={s.key(r):r for r in base};by=collections.defaultdict(list);numeric=[];pairs=[];player=[]
    for r in rows:by[r['season'],r['procedure_id']].append(r)
    for(season,method),rr in sorted(by.items()):
        for window,subset in [('ALL',rr),('W1_4',[r for r in rr if r['week']<=4]),('W5_PLUS',[r for r in rr if r['week']>=5])]+[(w,[r for r in rr if r['week']==w])for w in sorted({r['week']for r in rr})]:
            for product in('mean','lower_median'):numeric.append(s.pointview(subset,subset,season,window,method,product))
        for pid in sorted({r['player_id']for r in rr}):
            own=[r for r in rr if r['player_id']==pid and r['actual']is not None]
            for product in('mean','lower_median'):
                player.append(dict(season=season,procedure_id=method,player_id=pid,product=product,**s.scoring.point_metrics([r[product]for r in own],[r['actual']for r in own],'pass_cmp'),
                    charting_license='CC-BY-SA-4.0',sample_limit='Sparse player-only outcomes do not establish a personal champion.'))
        for product in('mean','lower_median'):
            for cm in ['E1']+(['F1']if rr[0]['method']=='F2'else[]):
                bb=controls if cm=='E1'else{s.key(r):r for r in rows if r['method']=='F1'}
                same=[(r,bb[s.key(r)])for r in rr if r['actual']is not None and s.key(r)in bb]
                z=paired_losses([abs(r[product]-r['actual'])for r,b in same],[abs(b[product]-b['actual'])for r,b in same],[(r['season'],r['week'])for r,b in same],[r['game_id']for r,b in same])
                pairs.append(dict(kind='NUMERICAL_PAIRED_MAE',season=season,target='pass_cmp',candidate=method,control=cm,product=product,scope='FULL_SYSTEM_IDENTICAL_ROWS',**z))
    spec=importlib.util.spec_from_file_location('inventory',s.BASE/'independent/inventory_retained_qb_offers_v1.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    offers=[r for w in range(5,9)for r in mod.iter_offers(getattr(a,'week'+str(w)),w)if r['target']=='pass_cmp'];assert len(offers)==112
    indexed={(r['method'],s.key(r)):r for r in rows+base};scores=[];probviews=[];grades={};commitments=[]
    for method in('F1','F2','E1'):
        for policy in('P1_MEAN','P1_LOWER_MEDIAN','P2_STATISTICAL_LAW','P90'):
            gg=[]
            for ix,r in enumerate(offers):
                pred=indexed[method,s.key(r)];assert pred['actual']==r['actual']
                probs=ctx.exact_probabilities(s.law(pred),r['line']);point=pred['mean'if policy=='P1_MEAN'else'lower_median']
                side=s.sidepoint(point,r['line'])if policy.startswith('P1_')else'over'if probs['over']>probs['under']else'under'if probs['under']>probs['over']else None
                if policy=='P90'and(side is None or probs[side]<.9):side=None
                state='ABSTAIN'if side is None else s.scoring.threshold_crossing(r['actual'],r['line'],side,target='pass_cmp')
                gg.append(dict(r,source_row_index=ix,selected_side=side,statistical_state=state,settlement_state='UNRESOLVED_CONTRACT',net_return=None,strategy=policy,ranking_point=point,
                    technical_unavailable=False,probs=probs,fallback='none',pregame_role_band=pred['pregame_role_band'],source_cohorts=[],forecast_method=pred['procedure_id']))
            grades[method,policy]=gg
            if method=='E1':continue # Existing scores are controls, not duplicated observations.
            proc=next(r['procedure_id']for r in rows if r['method']==method)
            for window,subset in [('ALL',gg)]+[(w,[r for r in gg if r['week']==w])for w in range(5,9)]:
                vv=s.summary(subset,2026,window,proc,policy,'pass_cmp')
                for v in vv:v['time_panel_id']='B_FTN_QB_2026_W5_W8_RETAINED_OFFERS:'+str(window)
                scores+=vv
                if policy=='P2_STATISTICAL_LAW':
                    z=s.probability_stats(subset);z.update(s.panelmeta(subset,2026,window),record_kind='prop_threshold_probability_evaluation',target='pass_cmp',procedure_id=proc,
                        product_id='EXACT_LINE_OVER_UNDER_PUSH',record_id='FTN-PROB-'+s.digest([method,window])[:24],forecast_rows=z['n'],outer_offer_rows=len(subset),
                        unique_games=len({r['game_id']for r in subset}),probability_conditioning='MODELED_APPEARANCE',probability_score_contract='HALF_MULTICLASS_BRIER_OVER_UNDER_PUSH_V1',mae=None,mse=None,evidence=s.TIER)
                    probviews.append(z)
            if policy=='P2_STATISTICAL_LAW':
                for w in range(5,9):
                    weekly=[r for r in gg if r['week']==w]
                    for poolside in('Combined','over','under'):
                        for K in(6,10,20):
                            slots=K;chosen=[]
                            for batch in sorted({r['kickoff']for r in weekly}):
                                eligible=[r for r in weekly if r['kickoff']==batch and r['selected_side']and(poolside=='Combined'or r['selected_side']==poolside)]
                                eligible.sort(key=lambda r:(-r['probs'][r['selected_side']],r['game_id'],r['player_id'],str(r['line'])))
                                chosen+=eligible[:slots];slots-=min(len(eligible),slots)
                            ids={r['source_row_index']for r in chosen};ranked=[dict(r,selected_side=r['selected_side']if r['source_row_index']in ids else None,statistical_state=r['statistical_state']if r['source_row_index']in ids else'ABSTAIN')for r in weekly]
                            vv=s.summary(ranked,2026,w,proc,'ROLLING_TOP_K_DIAGNOSTIC','pass_cmp',rank_scope=poolside,K=K)
                            for v in vv:v['time_panel_id']='B_FTN_QB_2026_W5_W8_RETAINED_OFFERS:'+str(w)
                            scores+=vv
            commitments.append(dict(method=method,policy=policy,rows=len(gg),row_calculations_sha256=s.digest([{k:r.get(k)for k in('game_id','player_id','target','line','selected_side','actual','statistical_state','probs')}for r in gg]),restricted_rows_exported=False))
    for method in('F1','F2'):
        for policy in('P1_MEAN','P1_LOWER_MEDIAN','P2_STATISTICAL_LAW','P90'):
            for cm in ['E1']+(['F1']if method=='F2'else[]):
                bb={s.key(r):r for r in grades[cm,policy]}
                for window in ['ALL',5,6,7,8]:
                    same=[(r,bb[s.key(r)])for r in grades[method,policy]if(window=='ALL'or r['week']==window)and r['statistical_state']in('WIN','LOSS')and bb[s.key(r)]['statistical_state']in('WIN','LOSS')]
                    z=paired_losses([float(r['statistical_state']=='LOSS')for r,b in same],[float(b['statistical_state']=='LOSS')for r,b in same],[(2026,r['week'])for r,b in same],[r['game_id']for r,b in same])
                    pairs.append(dict(kind='OFFER_DIRECTION_PAIRED_LOSS',season=2026,window=window,target='pass_cmp',candidate=method,control=cm,policy=policy,
                        candidate_wins=sum(r['statistical_state']=='WIN'for r,b in same),control_wins=sum(b['statistical_state']=='WIN'for r,b in same),scope='COMMON_DECIDED_SELECTED_POOL',**z))
    s.write(a.out/'SCORES.json',numeric+scores+probviews);s.write(a.out/'PAIRED_COMPARISONS.json',pairs);s.write(a.out/'PER_PLAYER_NUMERICAL.json',player);s.write(a.out/'OWNER_LOCAL_CALCULATION_COMMITMENTS.json',commitments)
    s.write(a.out/'RUN_RECEIPT.json',dict(state='COMPLETE_FTN_CONTEXT_CONTRAST_NOT_C_ADMITTED',at_utc=s.now(),new_fits=0,new_forecasts=0,numerical_views=len(numeric),selection_views=len(scores),probability_views=len(probviews),paired_views=len(pairs),
        unique_completion_offers=112,actual_offer_weeks=[5,6,7,8],full_numerical_years=[2025,2026],forecast_records=len(rows),wall_seconds=time.monotonic()-start,RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
        five_week_direction_probability_status='NOT_QUALIFIED_FOUR_DISTINCT_OFFER_WEEKS',license='CC-BY-SA-4.0;FTN Data via nflverse',prices_roi_clv=None))
    print(json.dumps(s.read(a.out/'RUN_RECEIPT.json')))
if __name__=='__main__':main()
