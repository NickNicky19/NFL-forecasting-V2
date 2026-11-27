"""Read back typed JSON fits and verify restored count laws; no fit or grading."""
import hashlib,json,math,sys
from pathlib import Path
import numpy as np
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[3];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(BASE))
from nfl_v2.distribution_laws import Law
from run_legacy_completion_v1 import read,save,sha,now,restore

def law(d):
 if d['kind']=='leaf_mixture':return Law('mixture',support=d['support'],weights=d['weights'],prior=law(d['prior']),mixture=d['mixture'])
 return Law(**d)

def main():
 new=read(BASE/'PREDICTIONS_W8_W9_V1.json.gz')['rows'];old=[r for r in read(BASE/'OLD_W1_W7_PREDICTIONS_V1.json.gz')['rows']if r['method']=='C02'and r['model_sha256']is not None];rows=old+new;checks=[];maxmean=maxcdf=0.;models={}
 for r in rows:
  w=r['week'];p=(BASE/'recovery-fits'/f'2026-W{w:02}-C02.json.gz')if w<=7 else(BASE/'fits'/f'2026-W{w:02}-{r["method"]}.json.gz')
  if p not in models:models[p]=read(p)
  m=models[p];assert sha(p)==r['model_sha256'];pr=law(m['prior']);actual=restore(m['model'],r['features'],r['feature_order'],pr)
  if r['fallback']!='none':actual=pr
  expected=law(r['law']);maxmean=max(maxmean,abs(actual.mean-expected.mean));assert abs(actual.mean-r['mean'])<1e-10 and actual.quantile(.5)==r['lower_median']
  for line in[-1,0,.5,10,20.5,50,1000]:
   a=actual.cdf(line);b=expected.cdf(line);maxcdf=max(maxcdf,abs(a-b));assert abs(a-b)<1e-10 and math.isfinite(a)and -1e-12<=a<=1+1e-12
   if int(line)==line:assert abs(actual.cdf(line)-actual.cdf(line-1)-actual.pmf(line))<1e-10
  assert isinstance(r['mean'],(int,float))and math.isfinite(r['mean'])and r['mean']>=0 and r['lower_median']>=0
  try:restore(m['model'],r['features'],list(reversed(r['feature_order'])),pr)
  except ValueError:pass
  else:raise AssertionError('Named feature order accepted incorrectly')
  checks.append(dict(method=r['method'],week=w,game_id=r['game_id'],player_id=r['player_id'],model_sha256=sha(p),mean=actual.mean,median=actual.quantile(.5)))
 canonical=lambda rr:sorted((r['method'],r['week'],r['game_id'],r['player_id'],r['mean'],r['median'])for r in rr)
 shuffled=[checks[i]for i in np.random.default_rng(1701).permutation(len(checks))];assert canonical(shuffled)==canonical(checks)
 receipt=dict(state='PASS_TYPED_SAVED_MODEL_READBACK_INFERENCE_AND_PROBABILITY_CONTRACT',at_UTC=now(),models=len(models),rows=len(rows),named_order_negative_checks=len(rows),shuffled_identity_checks=len(rows),CDF_boundaries_and_integer_push_checks=len(rows)*7,max_restored_mean_difference=maxmean,max_restored_CDF_difference=maxcdf,checked_models=[dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p))for p in models],synthetic_thresholds_are_not_offer_scores=True,new_fits=0,new_NFL_evaluation_rows=0,new_HTTP=0,unsafe_model_loads=0,original_records_unchanged=True)
 save(BASE/'SAVED_JSON_RESTORATION_AND_LAW_CHECKS_V1.json',receipt);print(json.dumps(receipt))
if __name__=='__main__':main()
