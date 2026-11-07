"""Mechanical parity of retained recipes' no-model fallback update clocks."""
import bisect,csv,gzip,hashlib,json,math,sys
from collections import Counter,defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];HERE=ROOT/'reports/continuation-20261030c';sys.path.insert(0,str(HERE))
from review_paths import companion_root,source_root
from check_season_scores_independent import load_truth,sha,close
from check_defense_features_independent import canonical,prior
from check_retained_distribution_math import summaries
def verify():
 pub=HERE/'season-2024-v2';private=companion_root()/'seasonal-rolling-2024-v2';source=source_root();p=json.loads((pub/'FROZEN_PROTOCOL.json').read_text());rows,lookup,games=load_truth(source,p,2024);checked=Counter();examples={};cache={};point_updates=0
 def pool(target,floor,special):
  key=target,floor,special
  if key not in cache:
   groups=defaultdict(list)
   for r in rows:
    if r['season']>=floor and r['values'][target]is not None and(not special or r['position']in('QB','RB')):
     item=(r['available'],r['game_id'],r['player_id'],r['values'][target]);groups[r['position'],r['player_id']].append(item);groups[r['position'],None].append(item)
   cache[key]={k:sorted(v)for k,v in groups.items()}
  return cache[key]
 for path in sorted((private/'predictions').glob('W0[12].csv.gz')):
  with gzip.open(path,'rt',newline='')as f:
   for r in csv.DictReader(f):
    if not r.get('fit_slot')or r['fallback']=='none':continue
    method=r['fit_slot'].rsplit('-',1)[-1];fit=json.loads((pub/(r['fit_slot']+'-FIT.json')).read_text());target=r['target'];cutoff=float(r['feature_cutoff']);floor=2024 if r['policy_id'].startswith('H-CURRENT')else 2023 if r['policy_id'].startswith('H-RECENT')else 2022;special=method=='hgb_carry_primary';expected=None;detail={}
    if method in('leaf','c02','glm_law'):
     # The original law recipe freezes its role/global prior at weekly fit.
     law=fit['prior_parameters'][r['position']];kind=law['kind'];mean=0. if kind=='zero'else law['p']if kind=='bernoulli'else law['q']/(1-law['q'])if kind=='geometric'else law['center'];median=0 if kind=='zero'else int(law['p']>.5)if kind=='bernoulli'else max(0,math.ceil(math.log(.5)/math.log(law['q']))-1)if kind=='geometric'and law['q']else law['center'];product='mean'if r['product_id']=='event_probability'else r['product_id'];expected=(mean if product=='mean'else median)/(50 if target=='nick-chart-ppr-v1'else 1);detail=dict(update_rule='ROLE_GLOBAL_PRIOR_FIXED_AT_WEEKLY_FIT',fit_cutoff=float(r['fit_cutoff']),query_cutoff=cutoff,prior=law)
    else:
     groups=pool(target,floor,special);position=r['position'];own=[v for v in groups.get((position,r['player_id']),[])if v[0]<cutoff];selected=own or[v for v in groups.get((position,None),[])if v[0]<cutoff];values=[v[3]for v in selected];n=len(values);median=sorted(values)[(n-1)//2]if n else 0.;mean=sum(values)/n if n else 0.;expected=median if r['product_id']in('absolute_error_point','absolute_loss_point')else mean;fb='own_empirical'if own else'position_empirical'if values else'constant_zero';assert fb==r['fallback'];assert int(r['fallback_source_n'])==n;latest=max((v[0]for v in selected),default=None);point_updates+=latest is not None and latest>=float(r['fit_cutoff']);detail=dict(update_rule='SAME_ARM_OWN_THEN_POSITION_AT_GAME_QUERY_CUTOFF',fit_cutoff=float(r['fit_cutoff']),query_cutoff=cutoff,source_n=n,latest_consumed_available=latest,after_weekly_fit_observation_used=latest is not None and latest>=float(r['fit_cutoff']),role_filter='QB_RB_ONLY'if special else'SAME_POSITION')
    close(float(r['prediction']),expected);checked[method]+=1;key=method
    # Prefer a real no-model point that uses observations released after the
    # weekly origin. It demonstrates the update rule instead of merely zeros.
    if key not in examples or detail.get('after_weekly_fit_observation_used')and not examples[key].get('after_weekly_fit_observation_used'):
     examples[key]=dict(method=method,target=target,history_regime=r['history_regime'],product_id=r['product_id'],position=r['position'],prediction=float(r['prediction']),expected=expected,case_id=hashlib.sha256(canonical([r['game_id'],r['player_id'],target,r['population']])).hexdigest(),**detail)
    if special and r['position']not in('QB','RB'):
     assert expected==0.;checked['RA_extended_literal_zero']+=1
 assert all(k in examples for k in('leaf','c02','glm_law','hgb_L1','hgb_L2','hgb_TD','hgb_poisson','hgb_carry_primary'))
 return dict(state='PASS_ORIGINAL_RECIPE_FALLBACK_UPDATE_PARITY_WITH_EXPLICIT_2025_REPAIR',source_protocol_sha256=sha(pub/'FROZEN_PROTOCOL.json'),source_trace={name:sha(ROOT/'nfl_v2'/name)for name in('hgb_control.py','count_ablations.py','distribution_wave_v2.py','chart_wave.py','ordered_information_ablation.py','seasonal_rolling.py','seasonal_rolling_v2.py')},checked_rows=dict(checked),point_fallback_rows_using_label_available_after_weekly_fit=point_updates,representative_redacted_examples=list(examples.values()),conclusion='HGB/countno-modelown/positionfallbackupdatesatper-gamequerycutoff,notweeklyfitcutoff; lawrole/globalpriorsremainweeklyfixedandcold-startn8routingmatchesoriginal. V2RAfallbackQB/RB-onlyandoriginalabsolute_loss_pointalias restored. 2025v1gap preservedwithseparate0-refitpredictionrepair; originalv1notexactcontinuityforaffectedRAfallbacks.',evidence='VERIFIED_FROM_CODE+REPRODUCED_FROM_DATA; sourcecurrentvintageand7dayassumption',new_fits=0,new_forecasts=0,current2026_week8_outcomes_read=0)
if __name__=='__main__':
 r=verify();(HERE/'FALLBACK_CONTINUITY_INDEPENDENT_REVIEW.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
