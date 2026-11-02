"""Source-bound coverage, representative histogram arithmetic and report checks."""
import argparse,collections,csv,datetime,gzip,hashlib,json,math,pickle,sys,time
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch
import numpy as np
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE));from check_saved_library_and_laws import read,sha,canon,stream,key,gid,mid,eq,countside
ROOT=HERE.parents[2];sys.path.insert(0,str(ROOT))
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--private-root',type=Path,required=True);a=ap.parse_args();q=a.private_root;p=HERE.parent;start=time.monotonic()
 offers={key(r):r for r in stream(q/'ORIGINAL_JOINED_ROWS_V1.json.gz')if r['panel']=='ORIGINAL_PROVIDER_T90'};groups=collections.defaultdict(dict);meta={}
 for r in stream(q/'CAPTURED_LIBRARY_NUMERIC_ROWS_V1.json.gz'):
  m=mid(gid(r));meta[m]=gid(r);groups[m][key(r)]=(r['original_forecast_issued'],r['T90_eligible'],r['fallback'],r['error'],r['prediction'])
 cover=read(p/'checkpoint-summary-v1/OUTER_FORECAST_COVERAGE_V2.json');assert {r['method_key']for r in cover}==set(groups)
 for r in cover:
  gg=groups[r['method_key']];outer=[k for k in offers if k[-1]==r['target']];shared={k:v for k,v in gg.items()if k in offers};issued=sum(v[0]and v[1]for v in shared.values())
  expected={'outer_provider_offer_rows':len(outer),'outer_final_rows':sum(offers[k]['outcome_state']=='final'for k in outer),'outer_pending_rows':sum(offers[k]['outcome_state']=='pending'for k in outer),'query_and_offer_identity_present':len(shared),'issued_T90_forecasts_on_offers':issued,'missing_query_opportunities':len(outer)-len(shared),'captured_query_unissued_rows':sum(not v[0]for v in shared.values()),'captured_issued_late_for_T90_rows':sum(v[0]and not v[1]for v in shared.values()),'unavailable_against_outer':len(outer)-issued,'known_fallback_forecasts':sum(v[0]and v[1]and v[2]not in(None,False,'none','NONE','UNKNOWN_NOT_RETAINED')for v in shared.values()),'fallback_unknown_forecasts':sum(v[0]and v[1]and v[2]=='UNKNOWN_NOT_RETAINED'for v in shared.values())}
  for k,v in expected.items():
   if k not in r or r[k]is None:assert not shared and k in ('outer_final_rows','outer_pending_rows','captured_query_unissued_rows','captured_issued_late_for_T90_rows'),(k,v)
   else:assert r[k]==v,(k,r[k],v)
  eq(r['forecast_coverage_over_outer'],issued/len(outer)if outer else None)
 primary=set(read(p/'captured-library-v2/COMMON_PANEL_DEFINITION.json')['primary_captures']);masks=collections.defaultdict(list)
 for m,gg in groups.items():
  if meta[m][0]in primary and any(v[0]and v[1]for v in gg.values()):masks[meta[m][-1]].append({k for k,v in gg.items()if v[1]and v[3]is not None})
 common={t:set.intersection(*v)for t,v in masks.items()};original=list(stream(q/'ORIGINAL_AND_TOP_GRADED_ROWS_V1.json.gz'));controls=read(p/'checkpoint-summary-v1/CONTROL_SCORES.json')
 for s in controls:
  rr=[r for r in original if r['panel']=='ORIGINAL_PROVIDER_T90'and r['strategy']==s['strategy']and r['target']==s['target']and key(r)in common.get(r['target'],set())];countside(rr,s)
 nums=read(p/'comparable-products-v3/SCORES.json');ownside={r['procedure_id'].rsplit(':',1)[-1]:r for r in read(p/'comparable-products-v3/SELECTION_SIDE_TABLE.json')};winners=read(p/'checkpoint-summary-v1/TABLE_C_NUMERICAL_LEADERS_OWN_SELECTIONS.json')
 for row in winners:
  n=row['numeric'];rr=[r for r in nums if r['target']==n['target']and r['n']];metric='brier'if n['target']=='anytime_td'else'mae';best=min(r[metric]for r in rr);eq(n[metric],best);assert n in rr;assert row['tie_count']==sum(math.isclose(r[metric],best,rel_tol=0,abs_tol=1e-12)for r in rr)
  assert row['selection']==ownside.get(n['method_key'])
 assert len(winners)==sum(sum(math.isclose(r['brier'if t=='anytime_td'else'mae'],min(z['brier'if t=='anytime_td'else'mae']for z in nums if z['target']==t and z['n']),abs_tol=1e-12,rel_tol=0)for r in nums if r['target']==t and r['n'])for t in common)
 contrasts=read(p/'frozen-ablation-grading-v1/PAIRED_FROZEN_CONTRASTS.json')
 for r in contrasts:
  aa=groups[r['candidate_method_key']];bb=groups[r['comparator_method_key']];kk=[k for k,v in aa.items()if k in bb and v[1]and bb[k][1]and v[3]is not None and bb[k][3]is not None];assert len(kk)==r['n'];f=(lambda v:v[3]**2)if r['metric']=='Brier'else(lambda v:abs(v[3]));av=sum(f(aa[k])for k in kk)/len(kk);bv=sum(f(bb[k])for k in kk)/len(kk);eq(av,r['candidate_error']);eq(bv,r['comparator_error']);eq(av-bv,r['delta'])
 # Exact private detail V2 provenance: unchanged fields, correction only raw control point and its gaps.
 manifest=read(p/'checkpoint-summary-v1/RIGHT_AND_WRONG_SAFE_MANIFEST_V2.json');f=q/'WEEK8_RIGHT_AND_WRONG_DETAILS_V2.csv.gz';assert sha(f)==manifest['sha256'];n=0;buckets=collections.Counter();changed=0
 with gzip.open(f,'rt')as ff,gzip.open(q/'WEEK8_RIGHT_AND_WRONG_DETAILS_V1.csv.gz','rt')as oo:
  for r,old in zip(csv.DictReader(ff),csv.DictReader(oo)):
   n+=1;delta={k for k in r if r[k]!=old[k]};assert delta<= {'forecast','forecast_minus_line','forecast_minus_actual'};changed+=bool(delta)
   for left,right,name in [('forecast','line','forecast_minus_line'),('actual','line','actual_minus_line'),('forecast','actual','forecast_minus_actual')]:
    expected=str(Decimal(r[left])-Decimal(r[right]))if r[left]and r[right]else'';assert r[name]==expected
   buckets[r['target'],r['track'],r['selected_side'],r['grade']]+=1
 assert n==manifest['rows']==91292 and changed==manifest['corrected_rows']==1220
 assert buckets==collections.Counter({(r['target'],r['track'],r['selected_side'],r['grade']):r['rows']for r in manifest['bucket_counts']})
 # Separately written CDF / saved-leaf arithmetic. Trusted models opened only after exact hash.
 laws=list(stream(q/'WEEK8_ORIGINAL_LAW_THRESHOLD_ROWS_V2.json.gz'));selected=[]
 for t in('pass_yd','pass_cmp','rush_yd','pass_int'):
  selected.append(next(r for r in laws if r['target']==t and 'leaf_ids'in r['saved_law_reference']))
 selected+= [r for r in laws if 'parametric'in r['saved_law_reference']or'fallback_prior'in r['saved_law_reference']]
 from scipy.stats import poisson
 def pcdf(par,x):
  kind=par['kind'];x=math.floor(x)
  if kind=='zero':return float(x>=0)
  if kind=='bernoulli':return 0. if x<0 else 1-par['p']if x<1 else 1.
  if kind=='geometric':return 0. if x<0 else 1-par['q']**(x+1)
  if kind=='poisson':return float(poisson.cdf(x,par['mean']))
  assert kind=='signed';d=x-par['center'];return par['q']**(-d)/(1+par['q'])if d<0 else 1-par['q']**(d+1)/(1+par['q'])
 from sklearn.ensemble import ExtraTreesRegressor
 from nfl_v2.distribution_wave_v2 import FittedLawModel,Design
 def forbidden(*args,**kwargs):raise AssertionError('NO_ESTIMATOR_OR_TRANSFORM_CALLS_PERMITTED')
 models={};proof=[]
 with patch.object(ExtraTreesRegressor,'predict',forbidden),patch.object(ExtraTreesRegressor,'apply',forbidden),patch.object(ExtraTreesRegressor,'fit',forbidden),patch.object(FittedLawModel,'predict',forbidden),patch.object(Design,'transform',forbidden):
  for r in selected:
   fit=read(ROOT/r['fit_receipt']);prior=fit['prior_parameters'][r['position']];ref=r['saved_law_reference'];L=Decimal(str(r['line']));k=math.floor(L)
   if 'leaf_ids'in ref:
    rel=fit['model'].get('bundle_name',fit['model'].get('name'));root=Path(read(q/'LOCAL_INPUT_BINDINGS_V1.json')['private_evidence_root']);sub='distribution-wave-v2'if r['capture_version']=='DISTRIBUTION_WAVE'else'c02-future-shadow-v1'if r['capture_version']=='C02'else'qualified-defense-information-v1';path=root/sub/rel
    if not path.exists()and sub=='distribution-wave-v2':path=root/'distribution-wave-v1'/rel
    assert sha(path)==r['model_sha256']==fit['model']['sha256'];model=pickle.loads(gzip.decompress(path.read_bytes()));assert len(model.hist)==len(ref['leaf_ids'])==32
    weight=np.mean(np.asarray([h[leaf].toarray().ravel()for h,leaf in zip(model.hist,ref['leaf_ids'])]),axis=0);weight/=weight.sum();assert abs(weight.sum()-1)<1e-12
    cdf=lambda x:.95*float(weight[np.asarray(model.support)<=x].sum())+.05*pcdf(prior,x)
    proof.append({'target':r['target'],'model_sha256':sha(path),'fit_receipt_sha256':sha(ROOT/r['fit_receipt']),'support_n':len(model.support),'trees':32})
   else:
    params=ref.get('parametric',ref.get('fallback_prior'));cdf=lambda x:pcdf(params,x)
   c0,c1,c2=cdf(k-1),cdf(k),cdf(k+1);assert c0<=c1+1e-12 and c1<=c2+1e-12
   pp={'over':1-c1,'under':c0 if L==k else c1,'push':c1-c0 if L==k else 0.}
   for side,v in pp.items():eq(v,r['probabilities'][side])
   priorp={'over':1-pcdf(prior,k),'under':pcdf(prior,k-1)if L==k else pcdf(prior,k),'push':pcdf(prior,k)-pcdf(prior,k-1)if L==k else 0.}
   for side,v in priorp.items():eq(v,r['prior_probabilities'][side])
 prob=read(p/'checkpoint-summary-v1/THRESHOLD_PROBABILITY_LEADERS_AND_BASELINES.json');allprob=read(p/'saved-laws-v2/SCORES.json');winadverse=[]
 for r in prob:
  w=r['winner'];assert w in allprob;population=[v for v in allprob if v['target']==w['target']and v['reference']=='FOOTBALL_ORIGINAL_LAW'and v['evaluation_panel_id']==w['evaluation_panel_id']and v['n']];eq(w['brier'],min(v['brier']for v in population));refs={v['reference']:v for v in r['matched_references']};assert all(v in allprob and v['method_key']==w['method_key']and v['n']==w['n']for v in refs.values());winadverse.append({'target':w['target'],'n':w['n'],'best_law_brier':w['brier'],'neutral_brier':refs['NEUTRAL_50_50']['brier'],'earlier_prior_brier':refs['EARLIER_FIT_ROLE_PRIOR']['brier']})
 out={'state':'PASS_INDEPENDENT_OUTER_COVERAGE_CONTROL_MASKS_DETAILS_AND_REPRESENTATIVE_LAW_RECOVERY','at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checker_sha256':sha(__file__),'seconds':time.monotonic()-start,'outer_coverage_views_checked':len(cover),'same_key_control_side_views_checked':len(controls),'native_tied_leader_own_selection_bindings_checked':len(winners),'frozen_ablation_contrasts_checked':len(contrasts),'private_detail_rows_checked':n,'raw_control_detail_metadata_changes':changed,'source_parametric_and_fallback_CDF_rows_checked':len(selected)-4,'independent_histogram_CDF_witnesses':proof,'best_and_adverse_probability_results':winadverse,'scope':'Independent complete outer offer coverage and matched controls from saved grades; correct own-procedure side results, all frozen ablation losses, exact private detail metadata identity. Separately written pure CDF arithmetic checks all parametric/fallback law rows and four signed/count histogram witnesses with estimator calls forbidden. No inferred distribution from points. No new forecasts, fits, labels, or model inference. One exposed partial week, not selection-adjusted or a production-release certificate.','bindings':{str(f.relative_to(p)):sha(f)for f in[p/'checkpoint-summary-v1/OUTER_FORECAST_COVERAGE_V2.json',p/'checkpoint-summary-v1/CONTROL_SCORES.json',p/'checkpoint-summary-v1/TABLE_C_NUMERICAL_LEADERS_OWN_SELECTIONS.json',p/'frozen-ablation-grading-v1/PAIRED_FROZEN_CONTRASTS.json',p/'saved-laws-v2/SCORES.json']}}
 dest=HERE/'COVERAGE_CONTROLS_ABLATIONS_AND_LOOKUP_REVIEW_V1.json';dest.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:out[k]for k in('state','outer_coverage_views_checked','same_key_control_side_views_checked','frozen_ablation_contrasts_checked','private_detail_rows_checked','seconds')}))
if __name__=='__main__':main()
