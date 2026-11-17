"""Independent saved-row supplement audit; no producer scoring or model calls."""
import argparse,collections,csv,gzip,importlib.util,json,math
from pathlib import Path
sp=importlib.util.spec_from_file_location('primitive',Path(__file__).with_name('verify_qb_scores_v1.py'));v=importlib.util.module_from_spec(sp);sp.loader.exec_module(v)
def main():
 ap=argparse.ArgumentParser()
 for f in('base-wave','chart-wave','scores','inputs','output'):ap.add_argument('--'+f,type=Path,required=True)
 for w in range(5,9):ap.add_argument('--week'+str(w),type=Path,required=True)
 ap.add_argument('--old-predictions',type=Path,action='append',required=True);a=ap.parse_args()
 rows=[r for wave in(a.base_wave,a.chart_wave)for p in sorted((wave/'predictions').glob('*.json.gz'))for r in v.read(p)['rows']];source=v.read(a.inputs);qby={(r['game_id'],r['player_id']):r for r in source};group=collections.defaultdict(list)
 for r in rows:group[r['season'],r['target'],r['procedure_id']].append(r)
 keys={v.k(r)for r in rows};old=collections.defaultdict(dict);source_hashes=[]
 for path in a.old_predictions:
  source_hashes.append(v.sha(path))
  with gzip.open(path,'rt')as f:
   for r in csv.DictReader(f):
    if r['family']!='ordered_leaf_cdf'or r['target']not in('pass_cmp','pass_att')or r['position']!='QB'or r['history_regime']!='H-RECENT'or r['product_id']not in('mean','lower_median')or v.k(r)not in keys:continue
    if r.get('information_policy')not in(None,'','COMMON_FEATURE_MEMORY','COMMON','common-feature-memory')and'strict-current'in r['procedure_id']:continue
    z=dict(prediction=float(r['prediction']),actual=float(r['actual']),fallback=r['fallback']);key=v.k(r),r['product_id']
    if key in old[r['procedure_id']]:assert old[r['procedure_id']][key]==z
    old[r['procedure_id']][key]=z
 joins=v.read(a.scores/'RETAINED_NUMERICAL_IDENTITY_AND_LABEL_JOINS.json');jchecks=0
 for j in joins:
  rr=group[j['season'],j['target'],j['procedure_id']];records=old[j['comparator_id']];same=[(r,records[v.k(r),j['product']])for r in rr if(v.k(r),j['product'])in records and r['actual']is not None]
  assert j['common']==len(same)and j['candidate_full_rows']==len(rr)and j['label_mismatches']==sum(r['actual']!=b['actual']for r,b in same)==0
  assert j['control_fallback']==sum(v.fall(b)for r,b in same);jchecks+=1
 offers=[]
 for w in range(5,9):
  for r in v.read(getattr(a,'week'+str(w)))['rows']:
   if r.get('target')not in('pass_cmp','pass_att'):continue
   if w==8 and not(r.get('panel')=='ORIGINAL_PROVIDER_T90'and r.get('strategy')=='original'and not r.get('method_key')):continue
   offers.append(r)
 offer={v.k(r):r for r in offers};assert len(offer)==224
 sc=v.read(a.scores/'SCORES.json');counts=collections.Counter();partitions=collections.defaultdict(dict)
 for s in sc:
  rr=group[s['season'],s['target'],s['procedure_id']]
  if s.get('component_metrics')is not None:
   nthrow=0;bs=ll=0.;ex=[];sub=[];tv=[]
   for r in rr:
    q=qby[r['game_id'],r['player_id']];comp=r['components'];attempt=q['context_attempts'];complete=q['context_completions'];p=comp['conditional_completion_probability'];mix=comp['predicted_context_mix'];nthrow+=sum(attempt)
    bs+=sum(c*(1-z)**2+(n-c)*z*z for n,c,z in zip(attempt,complete,p));ll-=sum(c*math.log(z)+(n-c)*math.log1p(-z)for n,c,z in zip(attempt,complete,p));ex.append(comp['attempt_law']['mean']-q['official_attempts']);sub.append(abs(q['official_attempts']*comp['integrated_completion_probability']-q['official_completions']))
    if sum(attempt):tv.append(.5*sum(abs(z-n/sum(attempt))for z,n in zip(mix,attempt)))
   m=s['component_metrics'];assert m['throw_denominator']==nthrow and s['n']==len(rr)
   for f,z in [('exposure_MAE',sum(abs(x)for x in ex)/len(ex)),('exposure_bias',sum(ex)/len(ex)),('actual_exposure_substitution_MAE',sum(sub)/len(sub)),('conditional_throw_Brier',bs/nthrow),('conditional_throw_log_loss',ll/nthrow),('context_mix_TV',sum(tv)/len(tv))]:v.eq(m[f],z)
   assert s['diagnostic_only']and s['default_rank_eligible']is False and 'Postgame'in s['scope'];counts['component']+=1;continue
  rr=[r for r in rr if v.k(r)in offer]
  if s.get('diagnostic_bucket'):
   policy=s['product_id'].split(':')[0];bucket=s['diagnostic_bucket'];chosen=[];dist=[]
   for r in rr:
    o=offer[v.k(r)];p=v.probs(r['law'],o['line']);side=v.direction(r['mean'],o['line'])if policy=='P1_MEAN'else'over'if p['over']>p['under']else'under'if p['under']>p['over']else None;state=v.crossing(o['actual'],o['line'],side)
    if side and side.upper()+'_'+state==bucket:chosen.append(r);dist.append((r['mean']-o['line'],o['actual']-o['line']))
   assert s['outer_opportunities']==len(rr);rr=chosen;product='mean';e=s['error_pattern'];v.eq(e['mean_forecast_minus_line'],sum(x for x,y in dist)/len(dist)if dist else None);v.eq(e['mean_actual_minus_line'],sum(y for x,y in dist)/len(dist)if dist else None)
   if bucket.endswith('WIN'):assert e['numerical_error_ge5_correct_side']==sum(abs(r['mean']-r['actual'])>=5 for r in rr)
   partitions[s['procedure_id'],policy][bucket]=len(rr);assert s['diagnostic_only']and not s['default_rank_eligible'];counts['right_wrong']+=1
  else:product=s['product_id'];assert len(rr)==112;counts['offered_numeric']+=1
  errors=[r[product]-r['actual']for r in rr];ab=[abs(x)for x in errors];n=len(errors);assert s['n']==n
  for f,z in [('mae',sum(ab)/n if n else None),('mse',sum(x*x for x in errors)/n if n else None),('bias',sum(errors)/n if n else None),('rmse',math.sqrt(sum(x*x for x in errors)/n)if n else None),('max_abs',max(ab)if n else None),('p90_abs',v.quantile(ab,.9)if n else None),('p95_abs',v.quantile(ab,.95)if n else None)]:v.eq(s.get(f),z)
  for name,z in s['precision_counts'].items():
   hits=sum(x==0 for x in errors)if name=='exact_rate'else sum(x<int(name.split('_')[-1])if name.split('_')[1]=='lt'else x<=int(name.split('_')[-1])for x in ab);assert z['numerator']==hits and z['denominator']==n
 for key,buckets in partitions.items():assert len(buckets)==4 and sum(buckets.values())==112
 pairchecks=0;witness=[]
 for z in v.read(a.scores/'PAIRED_COMPARISONS.json'):
  aa=group[z['season'],z['target'],z['candidate']]
  if z['kind']=='NUMERICAL_PAIRED_MAE':
   same=[(r,old[z['control']][v.k(r),z['product']])for r in aa if(v.k(r),z['product'])in old[z['control']]and r['actual']is not None]
   if z['scope']=='COMMON_LEARNED':same=[(r,b)for r,b in same if not v.fall(r)and not v.fall(b)]
   av=[abs(r[z['product']]-r['actual'])for r,b in same];bv=[abs(b['prediction']-b['actual'])for r,b in same]
  else:
   bb={v.k(r):r for r in group[z['season'],z['target'],z['control']]};same=[(r,bb[v.k(r)])for r in aa if v.k(r)in offer];av=[];bv=[]
   for r,b in same:
    o=offer[v.k(r)]
    for data,arr in [(r,av),(b,bv)]:
     p=v.probs(data['law'],o['line']);side='over'if p['over']>p['under']else'under'if p['under']>p['over']else None;assert side is not None;arr.append(float(v.crossing(o['actual'],o['line'],side)=='LOSS'))
   assert z['candidate_wins']==len(av)-sum(av)and z['control_wins']==len(bv)-sum(bv)
   if z['candidate'].endswith(':E3'):witness.append(dict(candidate=z['candidate'],candidate_wins=z['candidate_wins'],control_wins=z['control_wins'],n=len(av),paired_change_pp=100*(sum(bv)-sum(av))/len(av)))
  n=len(same);assert z['n']==n
  if n:
   delta=sum(x-y for x,y in zip(av,bv))/n;v.eq(z['candidate_error'],sum(av)/n);v.eq(z['comparator_error'],sum(bv)/n);v.eq(z['delta'],delta)
   games=collections.defaultdict(list)
   for(r,b),x,y in zip(same,av,bv):games[r['game_id']].append(x-y)
   G=len(games);se=math.sqrt(G/(G-1)*sum((sum(g)-delta*len(g))**2 for g in games.values()))/n if G>=8 else None;v.eq(z['game_cluster_sensitivity_se'],se)
  pairchecks+=1
 assert counts==dict(offered_numeric=20,right_wrong=80,component=6)and pairchecks==129 and jchecks==80
 out=dict(state='PASS_INDEPENDENT_OFFER_POPULATION_COMPONENT_AND_RETAINED_CONTROL_ARITHMETIC',source_scores_sha256=v.sha(a.scores/'SCORES.json'),source_pairs_sha256=v.sha(a.scores/'PAIRED_COMPARISONS.json'),source_identity_label_joins_sha256=v.sha(a.scores/'RETAINED_NUMERICAL_IDENTITY_AND_LABEL_JOINS.json'),old_source_sha256=source_hashes,score_views_checked=dict(counts),paired_views_checked=pairchecks,identity_label_joins_checked=jchecks,right_wrong_full_112_partitions_checked=len(partitions),E3_vs_E0_P2_witness=witness,full2025_label_identity_join='All2025fullseasonretainedLeaf/C02mean/medianmatchingkeys,actuals,fallbackcountsverified;664rowsperfullmask;exactrecipesnotaliased.',postgame_component_limit='Frozenintegratedprobabilities/mix/exposurearepredictions. Realizedattempts/contextusedonlytodiagnose;actual-exposure-substitutionnotanavailableforecastorvalidatedrepair. Noactualcomponentsinsertedintoretainedpredictions.',cause='UNRESOLVED;outcome-conditionedfourbucketsandcomponentsaredescriptive,notcausalevidence.',new_fits=0,new_forecasts=0,parent_scorer_calls=0,private_row_exports=0)
 if a.output.exists():raise FileExistsError(a.output)
 a.output.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(dict(state=out['state'],sha256=v.sha(a.output))))
if __name__=='__main__':main()
