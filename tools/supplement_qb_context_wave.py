"""Matched saved controls, offered-population and frozen-component diagnostics.

No refit or new forecast. Conditional component substitution is postgame diagnosis,
not an available predictor or a tested repair. Restricted thresholds stay local.
"""
import argparse,collections,importlib.util,math,sys,time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools import score_player_context_wave as s
from nfl_v2.paired_uncertainty import paired_losses
from nfl_v2.result_index import DIAGNOSTIC_KIND,RIGHT_WRONG_KIND

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--base-wave',type=Path,required=True);ap.add_argument('--chart-wave',type=Path,required=True);ap.add_argument('--inputs',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--old-predictions',type=Path,action='append',required=True)
    for w in range(5,9):ap.add_argument('--week'+str(w),type=Path,required=True)
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    s.write(a.out/'FROZEN_PROTOCOL.json',dict(id='B-QB-FROZEN-OUTPUT-SUPPLEMENT-v1',at_utc=s.now(),code_sha256=s.sha(__file__),
        purpose='New matched control/offer-population and right/wrong/component projections only, not new predictions or another grader.',
        old_sources=[dict(source_id='RETAINED_OLD_POINTS_'+str(i),sha256=s.sha(p),bytes=p.stat().st_size)for i,p in enumerate(a.old_predictions)],
        owner='B',new_fits=0,new_forecasts=0,restricted_derivative_bytes=0,source_scope='Same fixed clocks/role/label contracts as base, current revised source reconstruction.',
        diagnostics='Four side/outcome buckets; predeclared all rows, no favorable example selection. Conditional component errors and actual-exposure substitutions are nondeployable postgame descriptions.',
        license='Base public-derived outputs CC-BY4; FTN-dependent outputs/combined derivative CC-BY-SA4 with FTN Data attribution.',
        budget=dict(wall_seconds=180,RSS_bytes=1073741824,public_bytes=8388608)))
    start=time.monotonic();rows=[r for wave in(a.base_wave,a.chart_wave)for p in sorted((wave/'predictions').glob('*.json.gz'))for r in s.read(p)['rows']]
    inputs=s.ctx.load_inputs(a.inputs);truth={(q['game_id'],q['player_id']):q for q in inputs}
    by=collections.defaultdict(list)
    for r in rows:by[r['season'],r['target'],r['procedure_id']].append(r)
    old=s.old_predictions(a.old_predictions,{s.key(r)for r in rows});scores=[];pairs=[];joins=[]
    for(season,target,method),rr in sorted(by.items()):
        for oldproc,records in old.items():
            for product in('mean','lower_median'):
                same=[(r,records[s.key(r),product])for r in rr if(s.key(r),product)in records and r['actual']is not None]
                mismatch=sum(r['actual']!=b['actual']for r,b in same)
                joins.append(dict(season=season,target=target,procedure_id=method,comparator_id=oldproc,product=product,common=len(same),label_mismatches=mismatch,
                    candidate_full_rows=len(rr),control_fallback=sum(s.isfallback(b)for r,b in same),state='MATCHED'if not mismatch else'LABEL_CONTRACT_MISMATCH_NOT_SCORED'))
                if not same or mismatch:continue
                for scope in('FULL_SYSTEM','COMMON_LEARNED'):
                    pp=[(r,b)for r,b in same if scope=='FULL_SYSTEM'or not s.isfallback(r)and not s.isfallback(b)]
                    z=paired_losses([abs(r[product]-r['actual'])for r,b in pp],[abs(b['prediction']-b['actual'])for r,b in pp],[(r['season'],r['week'])for r,b in pp],[r['game_id']for r,b in pp])
                    pairs.append(dict(kind='NUMERICAL_PAIRED_MAE',season=season,target=target,candidate=method,control=oldproc,product=product,scope=scope,**z))
    spec=importlib.util.spec_from_file_location('qb_inventory',s.BASE/'independent/inventory_retained_qb_offers_v1.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    offers=[r for w in range(5,9)for r in mod.iter_offers(getattr(a,'week'+str(w)),w)];offerkeys={s.key(r)for r in offers};offerby={s.key(r):r for r in offers}
    for(season,target,method),rr in sorted(by.items()):
        if season!=2026:continue
        subset=[r for r in rr if s.key(r)in offerkeys]
        for product in('mean','lower_median'):
            v=s.pointview(subset,subset,season,'OFFERS_W5_W8',method,product);v.update(numerical_panel='Identical112offeredQBplayer-games W5-8, not full277QBparticipant population',source_vintage=s.TIER)
            scores.append(v)
        # Four right/wrong buckets, with the mean as a separately typed numerical reference.
        for policy in('P1_MEAN','P2_STATISTICAL_LAW'):
            for bucket in('OVER_WIN','OVER_LOSS','UNDER_WIN','UNDER_LOSS'):
                dd=[];dist=[]
                for r in subset:
                    o=offerby[s.key(r)];prob=s.ctx.exact_probabilities(s.law(r),o['line'])
                    side=s.sidepoint(r['mean'],o['line'])if policy=='P1_MEAN'else'over'if prob['over']>prob['under']else'under'if prob['under']>prob['over']else None
                    state=s.scoring.threshold_crossing(o['actual'],o['line'],side,target=target)if side else'ABSTAIN'
                    if side and side.upper()+'_'+state==bucket:dd.append(r);dist.append((r['mean']-o['line'],o['actual']-o['line']))
                v=s.pointview(dd,subset,season,'OFFERS_W5_W8',method,'mean',scope=policy+':'+bucket)
                v.update(record_kind=RIGHT_WRONG_KIND,product_id=policy+':ANCILLARY_MEAN_ERROR',diagnostic_only=True,default_rank_eligible=False,conditioning='SELECTED_SIDE_AND_REALIZED_OUTCOME',
                    diagnostic_bucket=bucket,diagnostic_dimension='REGISTERED_QB_OFFER_PANEL',diagnostic_band='ALL',outer_opportunities=len(subset),
                    error_pattern=dict(mean_forecast_minus_line=float(np.mean([x for x,y in dist]))if dist else None,mean_actual_minus_line=float(np.mean([y for x,y in dist]))if dist else None,
                        numerical_error_ge5_correct_side=sum(abs(r['mean']-r['actual'])>=5 for r in dd)if bucket.endswith('WIN')else None,
                        cause='UNRESOLVED;descriptive outcome-conditioned pattern, not a causal effect or validated offset.'),
                    representative_rule='All observations retained; permitted owner-local examples ordered game/player/target; no favorable subset.')
                scores.append(v)
    # Complete frozen component predictions, only for actual explicit component models.
    for(season,target,method),rr in sorted(by.items()):
        if rr[0]['method']not in('P1','P2','P3'):continue
        component=[];total_n=0;total_brier=0.;total_ll=0.
        for r in rr:
            q=truth[r['game_id'],r['player_id']];n=np.asarray(q['context_attempts']);c=np.asarray(q['context_completions']);p=np.asarray(r['components']['conditional_completion_probability']);mix=np.asarray(r['components']['predicted_context_mix'])
            total_n+=int(n.sum());total_brier+=float(np.sum(c*(1-p)**2+(n-c)*p**2));total_ll-=float(np.sum(c*np.log(p)+(n-c)*np.log1p(-p)))
            component.append(dict(exposure_error=r['components']['attempt_law']['mean']-q['official_attempts'],
                actual_exposure_substitution_abs_error=abs(q['official_attempts']*r['components']['integrated_completion_probability']-q['official_completions']),
                context_TV=.5*float(np.abs(mix-n/n.sum()).sum())if n.sum()else None))
        v=dict(s.panelmeta(rr,season,'ALL'),record_kind=DIAGNOSTIC_KIND,record_id='QB-COMP-'+s.digest([season,method])[:24],procedure_id=method,product_id='FROZEN_COMPONENT_POSTGAME_DIAGNOSTIC',target='pass_cmp',
            n=len(rr),forecast_rows=len(rr),unique_games=len({r['game_id']for r in rr}),diagnostic_only=True,default_rank_eligible=False,mae=None,mse=None,
            component_metrics=dict(exposure_MAE=float(np.mean([abs(r['exposure_error'])for r in component])),exposure_bias=float(np.mean([r['exposure_error']for r in component])),
                conditional_throw_Brier=total_brier/total_n if total_n else None,conditional_throw_log_loss=total_ll/total_n if total_n else None,throw_denominator=total_n,
                actual_exposure_substitution_MAE=float(np.mean([r['actual_exposure_substitution_abs_error']for r in component])),
                context_mix_TV=float(np.mean([r['context_TV']for r in component if r['context_TV']is not None]))),
            scope='Postgame component diagnosis. Actual exposure/context is never an input to retained fullgame predictions; dependent throws are not independent NFLgames. No component forecast invented for direct forests.')
        scores.append(v)
    # All current laws versus E0 on identical actual-line rows; no post-hoc inversion.
    e0={s.key(r):r for r in rows if r['method']=='E0'}
    for(season,target,method),rr in sorted(by.items()):
        if season!=2026 or target!='pass_cmp':continue
        same=[(r,e0[s.key(r)],offerby[s.key(r)])for r in rr if s.key(r)in offerkeys]
        aa=[];bb=[]
        for r,b,o in same:
            ap=s.ctx.exact_probabilities(s.law(r),o['line']);bp=s.ctx.exact_probabilities(s.law(b),o['line']);sd='over'if ap['over']>ap['under']else'under'if ap['under']>ap['over']else None;bs='over'if bp['over']>bp['under']else'under'if bp['under']>bp['over']else None
            if sd is None or bs is None:raise ValueError('Explicit tie comparison required')
            aa.append(float(s.scoring.threshold_crossing(o['actual'],o['line'],sd,target=target)=='LOSS'));bb.append(float(s.scoring.threshold_crossing(o['actual'],o['line'],bs,target=target)=='LOSS'))
        z=paired_losses(aa,bb,[(2026,r['week'])for r,b,o in same],[r['game_id']for r,b,o in same]);pairs.append(dict(kind='OFFER_DIRECTION_PAIRED_LOSS',season=2026,window='ALL',target=target,candidate=method,control=s.ctx.VERSION+':E0',policy='P2_STATISTICAL_LAW',scope='COMMON112FULL_BOARD',candidate_wins=len(aa)-int(sum(aa)),control_wins=len(bb)-int(sum(bb)),**z))
    s.write(a.out/'SCORES.json',scores);s.write(a.out/'PAIRED_COMPARISONS.json',pairs);s.write(a.out/'RETAINED_NUMERICAL_IDENTITY_AND_LABEL_JOINS.json',joins)
    s.write(a.out/'RUN_RECEIPT.json',dict(state='COMPLETE_NEW_DIAGNOSTIC_AND_MATCHED_SAVED_ROW_PROJECTIONS',at_utc=s.now(),new_fits=0,new_forecasts=0,new_original_picks=0,new_private_rows=0,score_views=len(scores),paired_views=len(pairs),wall_seconds=time.monotonic()-start,not_new_NFL_observations=True))
    print(s.read(a.out/'RUN_RECEIPT.json'))
if __name__=='__main__':main()
