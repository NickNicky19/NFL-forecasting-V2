"""Pairwise AUC/reliability checks; no rankdata, fitting or calibration."""
import datetime,hashlib,importlib.util,json,math,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT));b=ROOT/'reports/player-context-completion-decision-01/B';ind=b/'independent'
spec=importlib.util.spec_from_file_location('independent_score_primitives',ind/'verify_full_scores_v1.py');v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
start=time.monotonic();offers=[]
for w,p in v.read(Path('/tmp/b-context-offer-sources.json')).items():
 for r in v.read(Path(p))['rows']:
  if r.get('target')!='pass_cmp':continue
  if int(w)==8 and not(r.get('panel')=='ORIGINAL_PROVIDER_T90'and r.get('strategy')=='original'and not r.get('method_key')):continue
  offers.append(r)
rows=[r for p in (b/'depth-wave-v2/predictions').glob('2026-*.json.gz')for r in v.read(p)['rows']];by={(r['procedure_id'],v.key(r)):r for r in rows};scores=v.read(b/'depth-scores-v2/SCORES.json');out=[]
for s in scores:
 if s['record_kind']!='prop_threshold_probability_evaluation':continue
 rr=[]
 for q in offers:
  if s['week']!='ALL'and q['week']!=s['week']:continue
  pr=v.probs(by[s['procedure_id'],v.key(q)]['law'],q['line']);rr.append(dict(actual=q['actual'],line=q['line'],probs=pr))
 pos=[r['probs']['over']for r in rr if r['actual']>r['line']];neg=[r['probs']['over']for r in rr if r['actual']<r['line']];auc=math.fsum(float(a>b)+.5*float(a==b)for a in pos for b in neg)/(len(pos)*len(neg))if pos and neg else None;v.eq(s['over_event_AUC'],auc)
 rel=[]
 for lo,hi in [(0,.5),(.5,.6),(.6,.7),(.7,.8),(.8,.9),(.9,1.0000001)]:
  chosen=[]
  for r in rr:
   pr=r['probs'];confidence=max(pr['over'],pr['under']);side='over'if pr['over']>pr['under']else'under'if pr['under']>pr['over']else None
   if lo<=confidence<hi and side is not None:chosen.append((confidence,v.grade(r['actual'],r['line'],side)=='WIN'))
  z=next(x for x in s['reliability']if x['lower']==lo);assert z['n']==len(chosen);v.eq(z['mean_predicted'],math.fsum(c for c,y in chosen)/len(chosen)if chosen else None);v.eq(z['correct_direction_rate'],sum(y for c,y in chosen)/len(chosen)if chosen else None);rel.append(dict(lower=lo,upper=min(hi,1),n=len(chosen),correct=sum(y for c,y in chosen)))
 out.append(dict(procedure=s['procedure_id'],window=s['week'],n=len(rr),over_event_pairwise_AUC=auc,reliability=rel))
assert len(out)==20
r={'id':'B-DEPTH-PROBABILITY-RANKING-INDEPENDENT-v1','at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASS','source_scores_sha256':v.sha(b/'depth-scores-v2/SCORES.json'),'proper_probability_views_checked':20,'method':'Every positive-negative over-event probability pair with half credit for ties; explicit frozenconfidencebin membership and selected-side grades; notauthorrankdata/summaryfunction.','rows':out,'P90_limit':'C1andC2 eachoneUnderwin onthe same112offerboard andsamecase; observed1/1 isnotvalidated90% accuracy, addsonegame/week notindependentdoubleevidence. D1/D2emptyN/A; oldgatesunchanged.','fits':0,'new_original_forecasts':0,'new_NFL_observations':0,'runtime_seconds':time.monotonic()-start}
(ind/'PROBABILITY_RANKING_REVIEW_V1.json').write_text(json.dumps(r,indent=2,allow_nan=False)+'\n');print(json.dumps({'status':'PASS','properviews':20,'runtime':r['runtime_seconds']}))
