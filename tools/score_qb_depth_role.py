"""Adapt one QB-role wave through existing graders; keep offer rows private."""
import argparse
import collections
import importlib.util
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools import score_player_context_wave as s
from nfl_v2 import player_context_matchup as ctx
from nfl_v2.paired_uncertainty import paired_losses

VERSION='B-QB-SOURCE-DEPTH-ROLE-INCREMENT-v1'
TIER='CURRENT_VINTAGE_SOURCE_LOADED_DEPTH_RECONSTRUCTION_SEVEN_DAY_STAT_HISTORY_TIMING_UNVERIFIED_ACTUAL_LINE_DIAGNOSTIC'
BASE=ROOT/'reports/player-context-matchup-01/B'
POLICIES=('P1_MEAN','P1_LOWER_MEDIAN','P2_STATISTICAL_LAW','P90')


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('action',choices=['prepare','score'])
    ap.add_argument('--wave',type=Path,required=True); ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--sources',type=Path,required=True)
    a=ap.parse_args(); a.out=a.out.resolve()
    paths={int(w):Path(p)for w,p in s.read(a.sources).items()}
    if a.action=='prepare':
        a.out.mkdir(parents=True,exist_ok=False)
        s.write(a.out/'FROZEN_SCORING_PROTOCOL.json',dict(id=VERSION+':SCORES',registered_UTC=s.now(),state='FROZEN_BEFORE_NEW_SCORES',
            adapter_sha256=s.sha(__file__),reused_adapter_sha256=s.sha(s.__file__),grader_sha256=s.sha(ROOT/'nfl_v2/scoring.py'),
            wave_protocol_sha256=s.sha(a.wave/'FROZEN_PROTOCOL.json'),
            sources=[dict(week=w,sha256=s.sha(p),bytes=p.stat().st_size)for w,p in sorted(paths.items())],
            new_arms=['S1','S2'],reused_control='S0 exactR3',policies=POLICIES,
            numeric='2026W1-8 broad277 and identicaloffered112 plusW1-4/W5-8 weekly; no new2025testclaim.',
            offered='Exactold112CMPidentitymask W5-8, immutablewebsite source archives; newlynormalized representation, not recoveredoldnormalizedbytes. Quote timing staysunverified.',
            controls=['S0','E3','SAVED_ADJUSTED','SAVED_RAW','ALWAYS_OVER','ALWAYS_UNDER','EARLIER_LINE_PREVALENCE','NEUTRAL_HALFPOINT'],
            missing_control='Strongstrict-current84rowcontrol not silentlysubstituted; retainedold47/84record linked separately unless exactrowpredictions restored.',
            semantics='Existing scoring.threshold_crossing, exact_decimal, complete ownsidecombined denom and Law normalization/push mass. Physical appearance statistical crossing, no verifiedvenue settlement/EV.',
            comparison='S1-S0 support, S2-S1 values, S2-S0total. Allnamed controls on exactsame112board; never transfer A88privateannualscores to newrecipe.',
            selective='Reuse frozen P90 only; zero selections meansN/A. No newtopK/ranker/gate/search.',
            uncertainty='Existing paired_losses game/week helper;4weekclusterslimited/exposeddevelopment, no arbitraryposthoc threshold.',
            budget=dict(fits=0,wall_seconds=600,public_bytes=8388608,new_private_restricted_exports=0),evidence=TIER))
        print('FROZEN_SCORING');return
    p=s.read(a.out/'FROZEN_SCORING_PROTOCOL.json')
    assert p['adapter_sha256']==s.sha(__file__)and p['reused_adapter_sha256']==s.sha(s.__file__)
    assert p['grader_sha256']==s.sha(ROOT/'nfl_v2/scoring.py') and p['wave_protocol_sha256']==s.sha(a.wave/'FROZEN_PROTOCOL.json')
    assert s.read(a.wave/'RUN_RECEIPT.json')['state']=='COMPLETE'
    for r in p['sources']: assert s.sha(paths[r['week']])==r['sha256']
    spec=importlib.util.spec_from_file_location('retained_offers',BASE/'independent/inventory_retained_qb_offers_v1.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    offers=[r for w in range(5,9)for r in module.iter_offers(paths[w],w)if r['target']=='pass_cmp']
    assert len(offers)==len({s.key(r)for r in offers})==112
    rows=[r for f in sorted((a.wave/'predictions').glob('*.json.gz'))for r in s.read(f)['rows']]
    controls=[r for f in sorted((BASE/'qb-wave-v1/predictions').glob('2026-*.json.gz'))for r in s.read(f)['rows']if r['method']=='E3']
    indexed={(r['method'],s.key(r)):r for r in rows+controls}
    queries=ctx.load_inputs(BASE/'source-fields-v3/DERIVED_QB_GAME_INPUTS.json.gz');history=ctx.ContextHistory(queries,8,20)
    qmap={(q['game_id'],q['player_id']):q for q in queries}
    scores=[];tables=[];pairs=[];numeric_tables=[];grades={};commitments=[]
    keys={s.key(r)for r in offers}
    for method in ('S0','S1','S2'):
        rr=[r for r in rows if r['method']==method];proc=VERSION+':'+method
        for window,sub in [('ALL',rr),('W1_4',[r for r in rr if r['week']<=4]),('W5_8',[r for r in rr if r['week']>=5]),('MATCHED_OFFERS_W5_W8',[r for r in rr if s.key(r)in keys])]+[(w,[r for r in rr if r['week']==w])for w in range(1,9)]:
            for product in('mean','lower_median'):
                for scope,rs in [('FULL_SYSTEM',sub),('LEARNED',[r for r in sub if not s.isfallback(r)]),('FALLBACK',[r for r in sub if s.isfallback(r)])]:
                    v=s.pointview(rs,sub,2026,window,proc,product,scope)
                    v.update(source_vintage=TIER,evidence=TIER,profile_cohort='UNCHANGED_RETAINED_QUERY_PANEL',evaluation_panel_id=VERSION+':NUMERIC:'+str(window))
                    numeric_tables.append(v)
                    if method!='S0':scores.append(v)
        for product in('mean','lower_median'):
            for cm in ('S0','S1')if method=='S2'else('S0',)if method=='S1'else():
                for mask in ('BROAD','OFFERED'):
                    same=[(r,indexed[cm,s.key(r)])for r in rr if r['actual']is not None and(mask=='BROAD'or s.key(r)in keys)]
                    pairs.append(dict(kind='NUMERICAL_PAIRED_MAE',candidate=method,control=cm,product=product,mask=mask,
                        **paired_losses([abs(r[product]-r['actual'])for r,b in same],[abs(b[product]-b['actual'])for r,b in same],[(2026,r['week'])for r,b in same],[r['game_id']for r,b in same])))
    for method in ('S0','S1','S2','E3','SAVED_ADJUSTED','SAVED_RAW','ALWAYS_OVER','ALWAYS_UNDER','EARLIER_LINE_PREVALENCE','NEUTRAL_HALFPOINT'):
        for policy in POLICIES if method in('S0','S1','S2','E3')else('REGISTERED_DIRECTION',):
            gg=[]
            for i,r in enumerate(offers):
                pred=indexed.get((method,s.key(r)));point=None;probs=None;sd=None;unavailable=False
                if pred:
                    assert pred['actual']==r['actual']
                    point=pred['mean'if policy=='P1_MEAN'else'lower_median']
                    probs=ctx.exact_probabilities(s.law(pred),r['line'])
                    sd=s.sidepoint(point,r['line'])if policy.startswith('P1_')else'over'if probs['over']>probs['under']else'under'if probs['under']>probs['over']else None
                    if policy=='P90'and(sd is None or probs[sd]<.9):sd=None
                    unavailable=point is None
                elif method in('SAVED_ADJUSTED','SAVED_RAW'):
                    point=r.get('prediction'if method=='SAVED_ADJUSTED'else'raw_prediction');sd=s.sidepoint(point,r['line']);unavailable=point is None
                elif method in('ALWAYS_OVER','ALWAYS_UNDER'):sd='over'if method=='ALWAYS_OVER'else'under'
                elif method=='NEUTRAL_HALFPOINT':
                    if float(r['line'])%1==.5:probs=dict(over=.5,under=.5,push=0.)
                else:
                    q=qmap[r['game_id'],r['player_id']];ys=[x['official_completions']for x in history.eligible(q['kickoff'],2025)]
                    whole=float(r['line']).is_integer();den=len(ys)+(3 if whole else 2)
                    probs=dict(over=(sum(y>r['line']for y in ys)+1)/den,under=(sum(y<r['line']for y in ys)+1)/den,push=(sum(y==r['line']for y in ys)+1)/den if whole else 0.)
                    sd='over'if probs['over']>probs['under']else'under'if probs['under']>probs['over']else None
                gg.append(dict(r,source_row_index=i,selected_side=sd,statistical_state='ABSTAIN'if sd is None else s.scoring.threshold_crossing(r['actual'],r['line'],sd,target='pass_cmp'),
                    settlement_state='UNRESOLVED_CONTRACT',net_return=None,strategy=policy,ranking_point=point,technical_unavailable=unavailable,probs=probs,
                    fallback=pred.get('fallback','none')if pred else'none',pregame_role_band=pred.get('pregame_role_band')if pred else'CONTROL_SCOPE',source_cohorts=[]))
            grades[method,policy]=gg;proc=VERSION+':'+method if method.startswith('S')and method in('S0','S1','S2')else method
            for window,sub in [('ALL',gg)]+[(w,[r for r in gg if r['week']==w])for w in range(5,9)]:
                vv=s.summary(sub,2026,window,proc,policy,'pass_cmp')
                for v in vv:v.update(source_vintage=TIER,evidence=TIER,evaluation_panel_id=VERSION+':OFFER:'+str(window))
                tables.append(dict(method=method,procedure_id=proc,policy=policy,window=window,sides=[dict(side=v['side'],metrics=v['selection_metrics'])for v in vv],probability=s.probability_stats(sub),games=len({r['game_id']for r in sub})))
                if method in('S1','S2'):
                    scores+=vv
                    if policy=='P2_STATISTICAL_LAW':
                        z=s.probability_stats(sub)
                        scores.append(dict(s.panelmeta(sub,2026,window),**z,record_kind='prop_threshold_probability_evaluation',target='pass_cmp',procedure_id=proc,product_id='EXACT_LINE_OVER_UNDER_PUSH',
                            record_id='QB-DEPTH-ROLE-PROB-'+s.digest([method,window])[:24],forecast_rows=z['n'],outer_offer_rows=len(sub),probability_conditioning='MODELED_APPEARANCE',
                            probability_score_contract='HALF_MULTICLASS_BRIER_OVER_UNDER_PUSH_V1',mae=None,mse=None,evidence=TIER,source_vintage=TIER))
            commitments.append(dict(method=method,policy=policy,rows=len(gg),calculations_sha256=s.digest([{k:r.get(k)for k in('game_id','player_id','target','line','selected_side','actual','statistical_state','probs')}for r in gg]),restricted_rows_exported=False))
    for method in('S1','S2'):
        for cm in ('S0','S1','E3','SAVED_ADJUSTED','SAVED_RAW','ALWAYS_OVER','ALWAYS_UNDER','EARLIER_LINE_PREVALENCE'):
            if method==cm:continue
            for policy in ('P1_MEAN','P1_LOWER_MEDIAN','P2_STATISTICAL_LAW'):
                bp=policy if(cm,policy)in grades else'REGISTERED_DIRECTION'
                for window in('ALL',5,6,7,8):
                    same=[(r,b)for r,b in zip(grades[method,policy],grades[cm,bp])if(window=='ALL'or r['week']==window)and r['statistical_state']in('WIN','LOSS')and b['statistical_state']in('WIN','LOSS')]
                    cw=sum(r['statistical_state']=='WIN'for r,b in same);bw=sum(b['statistical_state']=='WIN'for r,b in same)
                    pairs.append(dict(kind='OFFER_DIRECTION_PAIRED_LOSS',candidate=method,control=cm,policy=policy,window=window,candidate_wins=cw,control_wins=bw,
                        candidate_only_wins=sum(r['statistical_state']=='WIN'and b['statistical_state']=='LOSS'for r,b in same),control_only_wins=sum(r['statistical_state']=='LOSS'and b['statistical_state']=='WIN'for r,b in same),
                        **paired_losses([float(r['statistical_state']=='LOSS')for r,b in same],[float(b['statistical_state']=='LOSS')for r,b in same],[(2026,r['week'])for r,b in same],[r['game_id']for r,b in same])))
    # Baseline restoration and re-normalized source must reproduce old scope.
    native=next(x for x in tables if(x['method'],x['policy'],x['window'])==('S0','P2_STATISTICAL_LAW','ALL'))
    assert next(x for x in native['sides']if x['side']=='Combined')['metrics']['WIN']==59
    s.write(a.out/'SCORES.json',scores);s.write(a.out/'COMMON_CONTROL_TABLE.json',tables)
    s.write(a.out/'NUMERICAL_TABLE.json',numeric_tables);s.write(a.out/'PAIRED_COMPARISONS.json',pairs)
    s.write(a.out/'OWNER_LOCAL_COMMITMENTS.json',commitments)
    s.write(a.out/'RUN_RECEIPT.json',dict(state='COMPLETE_LOCAL_NOT_C_ADMITTED',at_UTC=s.now(),new_fits=0,new_forecasts=0,canonical_views=len(scores),paired_views=len(pairs),
        actual_offer_weeks=[5,6,7,8],unique_offers=112,unique_games=len({r['game_id']for r in offers}),new_NFL_games_or_weeks=0,original_picks=0,restricted_rows_exported=0,evidence=TIER))
    print(json.dumps(s.read(a.out/'RUN_RECEIPT.json')))


if __name__=='__main__':main()
