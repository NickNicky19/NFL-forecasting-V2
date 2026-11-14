"""Independent saved-output arithmetic and source-feature audit; never fit/load models."""
import argparse, collections, importlib.util, json, math
from pathlib import Path
import numpy as np
spec=importlib.util.spec_from_file_location('independent_primitives',Path(__file__).with_name('verify_qb_scores_v1.py'))
v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
FLAGS=('is_catchable_ball','is_contested_ball','is_drop')
def main():
 ap=argparse.ArgumentParser()
 for f in('repo','wave','base-wave','scores','inputs','chart','output'):ap.add_argument('--'+f,type=Path,required=True)
 for w in range(5,9):ap.add_argument('--week'+str(w),type=Path,required=True)
 a=ap.parse_args();read=v.read;sha=v.sha;eq=v.eq
 protocol=read(a.wave/'FROZEN_PROTOCOL.json');assert sha(a.inputs)==protocol['inputs_sha256']and sha(a.chart)==protocol['chart_sha256']
 assert sha(a.repo/'tools/run_qb_charting_context_wave.py')==protocol['code_sha256']
 src=sorted(read(a.inputs),key=lambda r:(r['kickoff'],r['game_id'],r['player_id']));chart=read(a.chart);cb={(r['game_id'],r['player_id']):r for r in chart};qby={(r['game_id'],r['player_id']):r for r in src}
 assert len(cb)==len(chart)
 for c in chart:
  assert 0<=c['matched_chart_rows']<=c['eligible_throws']
  for z in c['flags'].values():assert 0<=z['positive']<=z['known']<=c['eligible_throws']
 pred=[r for p in sorted((a.wave/'predictions').glob('*.json.gz'))for r in read(p)['rows']];base=[r for p in sorted((a.base_wave/'predictions').glob('*.json.gz'))for r in read(p)['rows']if r['method']=='E1'];bm={v.k(r):r for r in base}
 assert len(pred)==1882 and len({(r['method'],v.k(r))for r in pred})==1882
 fits={};good=[r for r in src if r['physical_participation']and r['target_parity']]
 for p in sorted((a.wave/'fits').glob('*.json.gz')):
  f=read(p);s=int(f['slot'].split('-')[0]);t=[r for r in good if r['season']>=s-1 and r['available']<f['fit_cutoff']]
  assert f['training_rows']==len(t)and f['latest_training_label']==max(r['available']for r in t)<f['fit_cutoff'];fits[f['slot']]=f
 assert len(fits)==52
 feature_checks=typed_checks=0;cached={};max_roundoff=0.
 # All features rebuilt from earlier source aggregates; no root feature function.
 for r in pred:
  q=qby[r['game_id'],r['player_id']];key=(r['game_id'],r['player_id']);d=r['charted_feature_support'];b=bm[v.k(r)]
  assert r['actual']==b['actual']and r['feature_cutoff']==q['kickoff']and r['fit_cutoff']<=q['kickoff']
  assert r['fallback']=='none'and not r['original_issuance']
  if key not in cached:
   eligible=[(p,cb[p['game_id'],p['player_id']])for p in src if p['physical_participation']and(p['game_id'],p['player_id'])in cb and p['available']<q['kickoff']]
   own=[(p,c)for p,c in eligible if p['player_id']==q['player_id']][-8:];n=sum(c['eligible_throws']for p,c in own);support=[float(len(own)),math.log1p(n)];rates=[];detail={}
   for flag in FLAGS:
    known=sum(c['flags'][flag]['known']for p,c in own);positive=sum(c['flags'][flag]['positive']for p,c in own);pk=sum(c['flags'][flag]['known']for p,c in eligible);pp=sum(c['flags'][flag]['positive']for p,c in eligible)
    observed=[p for p,c in own if c['flags'][flag]['known']>0];age=(q['kickoff']-max(p['available']for p in observed))/86400 if observed else None
    support += [known/n if n else None,math.log1p(known),age,float(not known)];rates += [(positive+20*(pp+1)/(pk+2))/(known+20)if known else None]
    detail[flag]=dict(known=known,positive=positive,eligible_throws=n,global_known=pk,global_positive=pp,latest_own_source_age_days=age)
   cached[key]=(support,rates,detail,max([p['available']for p,c in eligible],default=None),len(own))
  support,rates,detail,latest,num=cached[key]
  assert d['flags']==detail and d['own_games']==num and d['latest_feature_available']==latest
  assert latest is None or latest<q['kickoff'];expected=b['features']+support+(rates if r['method']=='F2'else[])
  assert len(expected)==len(r['features']);assert np.allclose(np.asarray(expected,float),np.asarray(r['features'],float),equal_nan=True,rtol=1e-12,atol=1e-12);feature_checks+=1
  # One query per fit, all 52 exact typed trees, independent manual traversal.
  f=fits[r['model_slot']]
  if f.get('_checked'):continue
  f['_checked']=True;m=f['model'];raw=np.asarray(r['features'],float);med=np.asarray(m['design']['median']);xx=np.r_[np.where(np.isfinite(raw),raw,med),~np.isfinite(raw)].astype(np.float32);support_y=np.asarray(m['support']);weights=np.zeros(len(support_y))
  for tree in m['trees']:
   node=0
   while tree['left'][node]!=-1:node=tree['left'][node]if xx[tree['feature'][node]]<=tree['threshold'][node]else tree['right'][node]
   h=tree['leaf_histogram']
   for nn,cc,z in zip(h['rows'],h['columns'],h['values']):
    if nn==node:weights[cc]+=z/len(m['trees'])
  weights/=weights.sum();assert np.allclose(weights,r['law']['weights'],atol=1e-12,rtol=1e-12)
  tr=[p for p in good if p['season']>=r['season']-1 and p['available']<r['fit_cutoff']];mu=max(.05,sum(p['official_completions']for p in tr)/len(tr));qgeo=mu/(1+mu);eq(r['law']['prior']['q'],qgeo)
  mean=.95*float(weights@support_y)+.05*mu;eq(mean,r['mean']);max_roundoff=max(max_roundoff,abs(mean-r['mean']));median=next(n for n in range(1000)if .95*float(weights[support_y<=n].sum())+.05*(1-qgeo**(n+1))>=.5);assert r['lower_median']==median;typed_checks+=1
 offers=[]
 for w in range(5,9):
  for r in read(getattr(a,'week'+str(w)))['rows']:
   if r.get('target')!='pass_cmp':continue
   if w==8 and not(r.get('panel')=='ORIGINAL_PROVIDER_T90'and r.get('strategy')=='original'and not r.get('method_key')):continue
   assert r['actual']is not None and r['label_state']=='SUPPORTED';offers.append(r)
 assert len(offers)==112
 indexed={(r['method'],v.k(r)):r for r in pred+base};gr={};commits=[]
 for method in('F1','F2','E1'):
  for policy in('P1_MEAN','P1_LOWER_MEDIAN','P2_STATISTICAL_LAW','P90'):
   rows=[]
   for ordinal,r in enumerate(offers):
    p=indexed[method,v.k(r)];assert p['actual']==r['actual'];prob=v.probs(p['law'],r['line']);point=p['mean'if policy=='P1_MEAN'else'lower_median'];side=v.direction(point,r['line'])if policy.startswith('P1_')else'over'if prob['over']>prob['under']else'under'if prob['under']>prob['over']else None
    if policy=='P90'and(side is None or prob[side]<.9):side=None
    rows.append(dict(r,ordinal=ordinal,selected_side=side,statistical_state=v.crossing(r['actual'],r['line'],side),probs=prob))
   gr[method,policy]=rows
   if method!='E1':commits.append(dict(method=method,policy=policy,rows=len(rows),row_calculations_sha256=v.dig([{k:r.get(k)for k in('game_id','player_id','target','line','selected_side','actual','statistical_state','probs')}for r in rows]),restricted_rows_exported=False))
 assert commits==read(a.scores/'OWNER_LOCAL_CALCULATION_COMMITMENTS.json')
 side=numeric=proper=top=0
 for s in read(a.scores/'SCORES.json'):
  method=s['procedure_id'].split(':')[-1];window=s['week'];kind=s['record_kind']
  if kind=='forecast_evaluation_view':
   rr=[r for r in pred if r['method']==method and r['season']==s['season']and(window=='ALL'or(window=='W1_4'and r['week']<=4)or(window=='W5_PLUS'and r['week']>=5)or r['week']==window)];vals=[r for r in rr if r['actual']is not None];e=[r[s['product_id']]-r['actual']for r in vals];ab=[abs(x)for x in e];n=len(e)
   assert s['n']==n and s['fallback_rows']==0 and s['forecast_rows']==len(rr)
   for f,z in [('mae',sum(ab)/n),('mse',sum(x*x for x in e)/n),('bias',sum(e)/n),('rmse',math.sqrt(sum(x*x for x in e)/n)),('max_abs',max(ab)),('p90_abs',v.quantile(ab,.9)),('p95_abs',v.quantile(ab,.95)),('NLL',sum(-v.logmass(r['law'],r['actual'])for r in vals)/n)]:eq(s[f],z)
   for name,z in s['precision_counts'].items():
    hits=sum(x==0 for x in e)if name=='exact_rate'else sum(x<int(name.split('_')[-1])if name.split('_')[1]=='lt'else x<=int(name.split('_')[-1])for x in ab);assert z['numerator']==hits and z['denominator']==n
   numeric+=1;continue
  policy=s['product_id'];rr=gr[method,'P2_STATISTICAL_LAW'if policy in('EXACT_LINE_OVER_UNDER_PUSH','ROLLING_TOP_K_DIAGNOSTIC')else policy];rr=[r for r in rr if window=='ALL'or r['week']==window]
  if kind=='prop_threshold_probability_evaluation':
   z=v.probability_metrics(rr)
   for f in('n','brier','log_loss','infinite_log_losses'):eq(z[f],s[f])
   proper+=1;continue
  if policy=='ROLLING_TOP_K_DIAGNOSTIC':
   remaining=s['K'];chosen=set()
   for batch in sorted({r['kickoff']for r in rr}):
    cc=[r for r in rr if r['kickoff']==batch and r['selected_side']and(s['rank_scope']=='Combined'or r['selected_side']==s['rank_scope'])];cc.sort(key=lambda r:(-r['probs'][r['selected_side']],r['game_id'],r['player_id'],str(r['line'])));chosen.update(r['ordinal']for r in cc[:remaining]);remaining-=min(remaining,len(cc))
   rr=[dict(r,selected_side=r['selected_side']if r['ordinal']in chosen else None,statistical_state=r['statistical_state']if r['ordinal']in chosen else'ABSTAIN')for r in rr];top+=1
  selected=[r for r in rr if r['selected_side']and(s['side']=='Combined'or r['selected_side']==s['side'])];c=collections.Counter(r['statistical_state']for r in selected);n=c['WIN']+c['LOSS'];z=s['selection_metrics'];assert s['n']==n and s['forecast_rows']==len(selected)and z['selection_pool_count']==len(rr)and s['technical_unavailable']==0 and s['fallback_rows']==0
  for f in('WIN','LOSS','PUSH'):assert z[f]==c[f]
  eq(z['hit_rate'],c['WIN']/n if n else None);eq(z['selection_coverage'],len(selected)/len(rr));assert z['admitted_rule_abstentions']==sum(r['selected_side']is None for r in rr);side+=1
 pairchecks=0
 for z in read(a.scores/'PAIRED_COMPARISONS.json'):
  if z['kind']=='NUMERICAL_PAIRED_MAE':
   aa=[r for r in pred if r['procedure_id']==z['candidate']and r['season']==z['season']];bb={v.k(r):r for r in pred+base if r['method']==z['control']};same=[(r,bb[v.k(r)])for r in aa if r['actual']is not None];av=[abs(r[z['product']]-r['actual'])for r,b in same];bv=[abs(b[z['product']]-b['actual'])for r,b in same]
  else:
   aa=gr[z['candidate'],z['policy']];bb={v.k(r):r for r in gr[z['control'],z['policy']]};same=[(r,bb[v.k(r)])for r in aa if(z['window']=='ALL'or r['week']==z['window'])and r['statistical_state']in('WIN','LOSS')and bb[v.k(r)]['statistical_state']in('WIN','LOSS')];av=[float(r['statistical_state']=='LOSS')for r,b in same];bv=[float(b['statistical_state']=='LOSS')for r,b in same];assert z['candidate_wins']==sum(r['statistical_state']=='WIN'for r,b in same)and z['control_wins']==sum(b['statistical_state']=='WIN'for r,b in same)
  n=len(same);assert n==z['n']
  if n:
   delta=sum(x-y for x,y in zip(av,bv))/n;eq(z['candidate_error'],sum(av)/n);eq(z['comparator_error'],sum(bv)/n);eq(z['delta'],delta)
  else:assert z['delta']is None
  pairchecks+=1
 headline=[]
 for m in('E1','F1','F2'):
  rr=gr[m,'P2_STATISTICAL_LAW'];headline.append(dict(method=m,n=len(rr),over_wins=sum(r['selected_side']=='over'and r['statistical_state']=='WIN'for r in rr),over_losses=sum(r['selected_side']=='over'and r['statistical_state']=='LOSS'for r in rr),under_wins=sum(r['selected_side']=='under'and r['statistical_state']=='WIN'for r in rr),under_losses=sum(r['selected_side']=='under'and r['statistical_state']=='LOSS'for r in rr),wins=sum(r['statistical_state']=='WIN'for r in rr),brier=v.probability_metrics(rr)['brier']))
 assert [h['wins']for h in headline]==[54,51,54]and all(h['brier']>.25 for h in headline)
 assert all(not any(r['selected_side']for r in rr)for(m,p),rr in gr.items()if p=='P90')
 out=dict(state='PASS_INDEPENDENT_SOURCE_FEATURE_TYPED_OUTPUT_AND_ARITHMETIC',source_scores_sha256=sha(a.scores/'SCORES.json'),source_pairs_sha256=sha(a.scores/'PAIRED_COMPARISONS.json'),protocol_sha256=sha(a.wave/'FROZEN_PROTOCOL.json'),source_input_sha256=sha(a.inputs),source_chart_sha256=sha(a.chart),fit_chronology_receipts_checked=len(fits),source_feature_rows_checked=feature_checks,primitive_typed_tree_outputs_checked=typed_checks,max_point_roundoff=max_roundoff,numeric_views_checked=numeric,selection_views_checked=side,probability_views_checked=proper,rolling_topK_views_checked=top,paired_views_checked=pairchecks,exact_commitments=len(commits),headline_same_112_CMP_rows=headline,source_flag_bounds_checked=len(chart),source_eligible_throws=sum(r['eligible_throws']for r in chart),source_matched_chart_rows=sum(r['matched_chart_rows']for r in chart),scope='FTN derived public source aggregates, all frozen52 fit lineage receipts and1882 predicted feature records; one primitive JSON-tree traversal per fit, all474score views and72paired point estimates. Historical vintage and quote timing remain reconstructed/unverified; retrospective participant membership. Fouractual-offerweeksnotfive. ExistingE1reusedwithoutfits.',qualifications=['F1latest_feature_availableglobalupperbound;itsactuallyconsumedchartfeaturesareownsupport/age;F2also consumesearlierglobalratepriors','Throwdenominatorincludesunmatchedleftjoinedofficialthrows;known/allthrowsiscoverage;positive/knownrate,notsilentlyfalsemissing','No .90 selections; empty rates N/A','No actual venue settlement, odds/ROI, original issuance or C admission established'],new_fits=0,scorer_invocations=0,model_deserializations=0,private_row_exports=0)
 if a.output.exists():raise FileExistsError(a.output)
 a.output.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(dict(state=out['state'],sha256=sha(a.output),views=numeric+side+proper,pairs=pairchecks)))
if __name__=='__main__':main()
