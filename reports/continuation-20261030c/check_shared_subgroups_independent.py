"""Independent saved-row subgroup/error/control replay, never fits or fetches."""
import argparse,csv,gzip,hashlib,json,math,resource,sys,time
from collections import Counter,defaultdict
from decimal import Decimal
from pathlib import Path
from typing import NamedTuple
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'reports/continuation-20261030c';PUB=OUT/'shared-subgroups-2026-v1';CORR=OUT/'shared-subgroup-comparator-correction-v1'
FILES={'football_membership':'pregame-cohort-scorecards-v2/memberships.json.gz','football_future_membership':'pregame-cohort-scorecards-v2/future-memberships.json.gz','chart_membership':'chart-cohort-scorecards-v1/memberships.json.gz','chart_future_membership':'chart-cohort-scorecards-v1/future-memberships.json.gz','candidate':'ordered-information-ablation-v1/ALL_PREDICTIONS.json.gz','football_laws':'distribution-wave-v2/all-predictions.csv.gz','chart_controls':'chart-wave-v1/all-chart-predictions.csv.gz','empirical':'empirical-history-diagnostic-v1/predictions.csv.gz','count_role':'count-ablation-wave-v1/PREDICTIONS_FLAT.csv.gz'}
def sha(p):
 h=hashlib.sha256()
 with p.open('rb')as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def close(a,b):
 if b==math.inf:assert a in('Infinity',math.inf);return
 assert(a is None and b is None)or(a is not None and b is not None and math.isclose(float(a),float(b),rel_tol=5e-10,abs_tol=5e-10)),(a,b)
def packet(path):
 decoder=json.JSONDecoder();buffer='';started=False
 with gzip.open(path,'rt')as f:
  while True:
   data=f.read(65536);buffer+=data
   if not started:
    pos=buffer.find('"rows":')
    if pos<0:assert data;continue
    opening=buffer.find('[',pos)
    if opening<0:assert data;continue
    buffer=buffer[opening+1:];started=True
   while True:
    buffer=buffer.lstrip(' \r\n\t,')
    if buffer.startswith(']'):return
    try:r,end=decoder.raw_decode(buffer)
    except json.JSONDecodeError:assert data;break
    assert isinstance(r,dict);yield r;buffer=buffer[end:]
class Row(NamedTuple):
 id:tuple;position:str;week:int;p:float|None;y:float|None;fallback:str;distribution:dict|None
def grid(x):
 d=Decimal(str(x))*50;assert d==d.to_integral_value();return int(d)
def primary_metric(target):return'brier'if target=='anytime_td'else'mae'
def loss(r,metric):
 if r.p is None or r.y is None:return None
 if metric=='crps':return r.distribution.get('crps')if r.distribution else None
 return(r.p-r.y)**2 if metric in('mse','brier')else abs(r.p-r.y)
def verify(private):
 start,cpu=time.monotonic(),time.process_time();p=json.loads((CORR/'FROZEN_PROTOCOL.json').read_text());v1=json.loads((PUB/'FROZEN_PROTOCOL.json').read_text());receipt=json.loads((CORR/'RUN_RECEIPT.json').read_text());checks=Counter()
 assert sha(PUB/'SCORES.json')==receipt['score_sha256'];assert sha(CORR/'PAIRED_COMPARISONS.json')==receipt['comparison_sha256']
 for spec in v1['source_bindings']:assert sha(private/FILES[spec['artifact_id']])==spec['sha256'];checks['source_hashes']+=1
 for spec in v1['hgb_chunk_bindings']:assert sha(private/'hgb-history-v1/prediction-chunks'/spec['artifact_id'])==spec['sha256'];checks['source_hashes']+=1
 members={}
 for name in('football_membership','chart_membership'):
  for r in json.loads(gzip.decompress((private/FILES[name]).read_bytes())):
   k=tuple(r['key']);assert k not in members;members[k]=r
 assert len(members)==17968
 oldleader=ROOT/'reports/continuation-20261030/TOP5_BY_CATEGORY_PRODUCT.csv';frozen=[]
 with oldleader.open(newline='')as f:
  seen=set()
  for r in csv.DictReader(f):
   k=r['target'],r['ranking_product'],r['family']
   if k in seen:continue
   seen.add(k);frozen.append((r['target'],r['ranking_product'],r['family'],r['procedure_id'],r['history_regime'],r['product']))
 for t in('pass_td','pass_cmp','pass_att','pass_int','rush_att','rec'):frozen.append((t,'intended_mean','HGB_POISSON_COUNT_POINT','v2-hgb-poisson-count-point-reconstruction-v1:common-feature-memory','H-MULTI','poisson_intended_mean_point'))
 specs=p['comparators'];assert[(s['target'],s['purpose'],s['family'],s['procedure_id'],s['history_regime'],s['product_id'])for s in specs]==frozen
 assert all('v2-c02-'not in s['procedure_id']for s in specs);needed={(s['procedure_id'],s['history_regime'],s['product_id'])for s in specs};identities={k:k for k in members};summaries={};own=defaultdict(dict);controls=defaultdict(dict);candidate_metadata={}
 def admit(raw,kind,candidate=False):
  if int(raw.get('season',2026))!=2026 or not 1<=int(raw['week'])<=7:return
  proc='empirical-player-history-control-v1'if kind=='empirical'else'hgb-direct-history-controls-v1:'+raw['objective']if kind=='hgb'else raw['procedure_id'];product=raw.get('product_id')or raw.get('product')or raw.get('objective');model=(proc,raw['history_regime'],product)
  if not candidate and model not in needed and'ordered_leaf_cdf:'not in proc:return
  k=tuple(raw[x]for x in('game_id','player_id','target','population'));assert k in identities;k=identities[k]
  num=lambda v:None if v in('',None)else float(v);d=raw.get('distribution_summary');d=json.loads(d)if isinstance(d,str)and d else d or None
  if candidate and d:
   dk=(proc,raw['history_regime'],k);d=summaries.setdefault(dk,d)
  elif d:d={'crps':d['crps']}
  r=Row(k,raw['position'],int(raw['week']),num(raw.get('prediction')),num(raw.get('actual')),raw['fallback'],d);destination=own if candidate else controls;assert k not in destination[model];destination[model][k]=r
  if candidate:candidate_metadata[model]=raw['policy_id'],raw['information_policy']
 for r in packet(private/FILES['candidate']):admit(r,'candidate',True)
 for name in('football_laws','chart_controls','empirical','count_role'):
  with gzip.open(private/FILES[name],'rt',newline='')as f:
   for r in csv.DictReader(f):admit(r,name)
 for spec in v1['hgb_chunk_bindings']:
  for r in packet(private/'hgb-history-v1/prediction-chunks'/spec['artifact_id']):admit(r,'hgb')
 assert sum(map(len,own.values()))==134168 and sum(map(len,controls.values()))==364926
 labels={}
 for rs in own.values():
  for k,r in rs.items():
   if k in labels:assert labels[k]==(r.y,r.position)
   labels[k]=(r.y,r.position)
 for rs in controls.values():
  for k,r in rs.items():assert labels[k]==(r.y,r.position);checks['control_label_position_joins']+=1
 masks=defaultdict(list)
 for rs in own.values():
  grouped=defaultdict(set)
  for k,r in rs.items():
   if r.y is not None and r.p is not None and r.fallback=='none':grouped[k[2:]].add(k)
  for group,ids in grouped.items():masks[group].append(ids)
 for s in specs:
  rs=controls[s['procedure_id'],s['history_regime'],s['product_id']];grouped=defaultdict(set)
  for k,r in rs.items():
   if k[2]==s['target']and r.y is not None and r.p is not None and r.fallback=='none':grouped[k[2:]].add(k)
  for group,ids in grouped.items():masks[group].append(ids)
 shared={g:set.intersection(*ss)for g,ss in masks.items()};core={}
 for proc,arm,product in own:
  if proc.endswith(':strict-current-inputs'):continue
  core[proc,product]=set.intersection(*[{k for k,r in own[proc,a,product].items()if r.y is not None and r.p is not None and r.fallback=='none'}for a in('H-CURRENT','H-RECENT','H-MULTI')])
 groups=defaultdict(list)
 for model,rs in own.items():
  for k,r in rs.items():
   views=['full_system','own_learned_only'if r.fallback=='none'else'fallback_only']
   if k in shared[k[2:]]:views.append('selected_controls_and_all_four_candidate_policies_learned_overlap')
   if k in core.get((model[0],model[2]),set()):views.append('three_core_history_learned_overlap')
   for cohort in members[k]['cohorts']:
    for view in views:groups[model+(k[2],k[3],cohort,view)].append(r)
 scores=json.loads((PUB/'SCORES.json').read_text());assert len(scores)==len(groups)==7458;byrecord={}
 for s in scores:
  key=(s['procedure_id'],s['history_regime'],s['product_id'],s['target'],s['population'],s['cohort_id'],s['fallback_view']);rs=groups[key];byrecord[s['record_id']]=rs;selected=[r for r in rs if r.y is not None and r.p is not None];n=len(selected)
  values=dict(n=n,scored_n=n,forecast_rows=len(rs),forecast_games=len({r.id[0]for r in rs}),unique_games=len({r.id[0]for r in selected}),fallback_rows=sum(r.fallback!='none'for r in rs),scored_fallback_rows=sum(r.fallback!='none'for r in selected),missing_actual_n=sum(r.y is None for r in rs))
  if n:
   errors=[r.p-r.y for r in selected];a=sorted(map(abs,errors));mse=math.fsum(e*e for e in errors)/n;q=lambda p:(lambda x:a[math.floor(x)]+(a[math.ceil(x)]-a[math.floor(x)])*(x-math.floor(x)))((n-1)*p)
   values.update(mae=math.fsum(a)/n,mse=mse,rmse=math.sqrt(mse),bias=math.fsum(errors)/n,p90_abs=q(.9),p95_abs=q(.95),max_abs=a[-1],exact_rate=sum(e==0 for e in errors)/n)
   ae=[abs(grid(r.p)-grid(r.y))for r in selected]if s['target']=='nick-chart-ppr-v1'and s['product_id']=='lower_median'else a;unit=50 if s['target']=='nick-chart-ppr-v1'and s['product_id']=='lower_median'else 1
   for t in(1,5,10):values['abs_lt_'+str(t)]=sum(x<t*unit for x in ae)/n;values['abs_le_'+str(t)]=sum(x<=t*unit for x in ae)/n
   ds=[r.distribution for r in selected];inf=sum(d['infinite_nll']for d in ds);values.update(CRPS=math.fsum(d['crps']for d in ds)/n,NLL=None if inf else math.fsum(d['nll']for d in ds)/n,infinite_NLL=inf,interval90_width=math.fsum(d['interval90_width']for d in ds)/n,interval90_coverage=sum(d['interval90_covered']for d in ds)/n,mean_zero_mass=math.fsum(d['zero_mass']for d in ds)/n)
   if s['target']=='anytime_td':values.update(brier=mse,prevalence=math.fsum(r.y for r in selected)/n,log_loss=math.fsum(-math.log(r.p if r.y else 1-r.p)if(r.p if r.y else 1-r.p)>0 else math.inf for r in selected)/n)
  else:values.update(mae=None,mse=None,rmse=None,bias=None)
  for field,v in values.items():close(s[field],v);checks['native_law_coverage_precision_aggregates']+=1
  assert s['cohort_membership_sha256']==hashlib.sha256(canonical(sorted(r.id for r in rs))).hexdigest();assert s['scored_membership_sha256']==hashlib.sha256(canonical(sorted(r.id for r in selected))).hexdigest();checks['score_membership_hashes']+=2
 def compare(c,rows):
  if c['status']=='UNESTABLISHED':return
  rs=controls[c['comparator_procedure_id'],c['comparator_history_regime'],c['comparator_product_id']];pairs=[]
  for r in rows:
   other=rs.get(r.id)
   if other is None:continue
   a,b=loss(r,c['metric']),loss(other,c['metric'])
   if a is not None and b is not None:pairs.append((r,other,a,b))
  assert len(pairs)==c['paired_n'];assert c['membership_sha256']==hashlib.sha256(canonical(sorted(r.id for r,_,_,_ in pairs))).hexdigest();n=len(pairs);a=math.fsum(v[2]for v in pairs)/n;b=math.fsum(v[3]for v in pairs)/n;delta=a-b
  for field,value in [('candidate_error',a),('comparator_error',b),('absolute_error_delta',delta),('relative_error_delta',delta/b if b else None)]:close(c[field],value);checks['paired_metric_and_membership_checks']+=1
  games,weeks=defaultdict(list),defaultdict(list)
  for r,o,a,b in pairs:games[r.id[0]].append(a-b);weeks[r.week].append(a-b)
  se=math.sqrt(len(games)/(len(games)-1)*math.fsum((math.fsum(v)-len(v)*delta)**2 for v in games.values())/n**2)if len(games)>=8 else None;close(c['uncertainty']['game_cluster_sensitivity_se'],se);assert c['uncertainty']['week_interval']is None
  for w,vs in weeks.items():close(c['uncertainty']['week_mean_deltas'][str(w)],math.fsum(vs)/len(vs));checks['paired_week_and_game_checks']+=1
  checks['paired_metric_and_membership_checks']+=2;checks['paired_week_and_game_checks']+=1
 for s in scores:compare(s['comparison'],byrecord[s['record_id']])
 comps=json.loads((CORR/'PAIRED_COMPARISONS.json').read_text());assert comps['source_score_sha256']==sha(PUB/'SCORES.json');assert len(comps['rows'])==52780
 for c in comps['rows']:compare(c,byrecord[c['source_record_id']])
 return dict(status='PASS_INDEPENDENT_FROZEN_COHORT_NATIVE_LAW_AND_CORRECTED_CONTROL_REPLAY',candidate_rows=134168,control_reference_rows=364926,cohort_query_memberships=17968,score_views=len(scores),corrected_pair_views=len(comps['rows']),checks=dict(checks),shared_learned_counts={':'.join(k):len(v)for k,v in shared.items()},score_sha256=sha(PUB/'SCORES.json'),corrected_pair_sha256=sha(CORR/'PAIRED_COMPARISONS.json'),prior_incomplete_comparator_sidecar='preserved/superseded; pre-C02fullpanelchoices verified for correction',resource=dict(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024),limitations='All7exposedweeks; historicalparticipantqueryuniverse, old-memory selectors, chartscorehistory notworkload; no selection/price/ROI or sourcevintageclaim. Corrected sourcechoices heldfixed across subgroups.',new_fits=0,new_forecasts=0,week8_outcomes_read=0)
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--private-root',type=Path,required=True);args=parser.parse_args();r=verify(args.private_root);OUT.joinpath('SHARED_SUBGROUP_INDEPENDENT_REVIEW.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
