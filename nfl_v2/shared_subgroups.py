"""New C02 subgroup views on immutable earlier-feature-defined memberships.

No fit, prediction, outcome acquisition or membership reconstruction occurs here.
Old competitors are paired references, not newly counted univariate score views.
"""
from __future__ import annotations
import collections,csv,gzip,hashlib,json,math,time
from datetime import datetime,timezone
from pathlib import Path
from statistics import fmean
from .scoring import point_metrics
from .precision_grid import chart_median_precision

VERSION='v2-c02-shared-frozen-subgroups-2026-v1'
CHART='nick-chart-ppr-v1'
CORE=('H-CURRENT','H-RECENT','H-MULTI')
C02='v2-c02-explicit-lag-block-removal-leaf-cdf-v1'
FILES={
 'football_membership':('pregame-cohort-scorecards-v2/memberships.json.gz','json'),
 'football_future_membership':('pregame-cohort-scorecards-v2/future-memberships.json.gz','json'),
 'chart_membership':('chart-cohort-scorecards-v1/memberships.json.gz','json'),
 'chart_future_membership':('chart-cohort-scorecards-v1/future-memberships.json.gz','json'),
 'candidate':('ordered-information-ablation-v1/ALL_PREDICTIONS.json.gz','packet'),
 'football_laws':('distribution-wave-v2/all-predictions.csv.gz','csv'),
 'chart_controls':('chart-wave-v1/all-chart-predictions.csv.gz','csv'),
 'empirical':('empirical-history-diagnostic-v1/predictions.csv.gz','csv'),
 'count_role':('count-ablation-wave-v1/PREDICTIONS_FLAT.csv.gz','csv'),
}
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def digest(x):return hashlib.sha256(canonical(x)).hexdigest()
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb')as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def load(path):return json.loads(Path(path).read_bytes())
def write(path,x):
 with Path(path).open('xb')as f:f.write(canonical(x))
def now():return datetime.now(timezone.utc).isoformat()
def identity(r):return tuple(r[k]for k in('game_id','player_id','target','population'))
def modelkey(r):return(r['procedure_id'],r['history_regime'],r['product_id'])
def number(v):
 if v in(None,''):return None
 v=float(v)
 if not math.isfinite(v):raise ValueError('nonfinite retained number')
 return v

def packet_rows(path):
 """Incrementally decode the existing top-level rows array; bounded memory."""
 decoder=json.JSONDecoder()
 with gzip.open(path,'rt')as f:
  buf='';started=False;done=False
  while not done:
   extra=f.read(65536)
   if extra:buf+=extra
   elif not buf.strip():break
   if not started:
    i=buf.find('"rows":')
    if i<0:
     if len(buf)>65536 or not extra:raise ValueError('rows packet required')
     continue
    j=buf.find('[',i+7)
    if j<0:continue
    buf=buf[j+1:];started=True
   while True:
    buf=buf.lstrip(' \n\r\t,')
    if buf.startswith(']'):done=True;break
    try:r,end=decoder.raw_decode(buf)
    except json.JSONDecodeError:
     if not extra:raise ValueError('truncated packet')
     break
    if not isinstance(r,dict):raise ValueError('row object required')
    yield r;buf=buf[end:]
   if not extra and not done:raise ValueError('truncated rows array')
  if not started:raise ValueError('missing rows array')

def normalize(r,kind):
 # The historical filter must precede actual/distribution decoding.
 if int(r.get('season',2026))!=2026 or not 1<=int(r['week'])<=7:return None
 proc=r.get('procedure_id')
 if kind=='empirical':proc='empirical-player-history-control-v1'
 if kind=='hgb':proc='hgb-direct-history-controls-v1:'+r['objective']
 product=r.get('product_id')or r.get('product')or r.get('objective')
 if not proc or not product or not r.get('fallback'):raise ValueError('explicit procedure/product/fallback required')
 d=r.get('distribution_summary')
 if isinstance(d,str):d=json.loads(d)if d else None
 return {**{k:r[k]for k in('game_id','player_id','target','population','position','history_regime','fallback')},'procedure_id':proc,'product_id':product,'policy_id':r.get('policy_id'),'season':2026,'week':int(r['week']),'prediction':number(r.get('prediction')),'actual':number(r.get('actual')),'distribution_summary':d,'procedure_family_id':r.get('procedure_family_id')or r.get('family')or kind,'information_policy':r.get('information_policy')or('PER-ARM-OUTCOME-HISTORY'if kind=='empirical'else'COMMON-2022-MEMORY')}

def selected_specs(leader_file):
 with Path(leader_file).open()as f:old=list(csv.DictReader(f))
 specs=[]
 for r in old:
  # The old family representative was chosen on the exposed full primary panel,
  # never on these new subgroup errors. Ties retain the first frozen row.
  category=r['ranking_product'];key=(r['target'],category,r['family'])
  if any(tuple(s[k]for k in('target','purpose','family'))==key for s in specs):continue
  specs.append(dict(target=r['target'],purpose=category,family=r['family'],procedure_id=r['procedure_id'],history_regime=r['history_regime'],product_id=r['product'],prior_full_error=float(r['ranking_loss']),old_rank=int(r['rank']),source_artifact=r['source_artifact']))
 # Poisson point reconstruction is a distinct applicable control, not a PMF.
 for t in('pass_td','pass_cmp','pass_att','pass_int','rush_att','rec'):
  specs.append(dict(target=t,purpose='intended_mean',family='HGB_POISSON_COUNT_POINT',procedure_id='v2-hgb-poisson-count-point-reconstruction-v1:common-feature-memory',history_regime='H-MULTI',product_id='poisson_intended_mean_point',prior_full_error=None,old_rank=None,source_artifact='reports/continuation-20261030/count-ablation-wave-v1/SCORES.json'))
 return specs

def prepare(private_root,public_root,leader_file,candidate_minima):
 private_root,public_root,leader_file,candidate_minima=map(Path,(private_root,public_root,leader_file,candidate_minima))
 if public_root.exists():raise ValueError('fresh immutable output directory required')
 bindings=[]
 for aid,(name,kind)in FILES.items():
  p=private_root/name;bindings.append(dict(artifact_id=aid,format=kind,sha256=sha(p),bytes=p.stat().st_size))
 hgb=private_root/'hgb-history-v1/prediction-chunks';chunks=[]
 for p in sorted(hgb.glob('W0[1-7]-*.json.gz')):chunks.append(dict(artifact_id=p.name,sha256=sha(p),bytes=p.stat().st_size))
 if len(chunks)!=441:raise ValueError('441 original historical HGB chunks required')
 public_root.mkdir(parents=True)
 p=dict(version=VERSION,state='FROZEN_BEFORE_NEW_SUBGROUP_LOSS_DECODE',registered_at_utc=now(),code_sha256=sha(__file__),scoring_code_sha256=sha(Path(__file__).with_name('scoring.py')),precision_code_sha256=sha(Path(__file__).with_name('precision_grid.py')),source_bindings=bindings,hgb_chunk_bindings=chunks,old_leader_artifact=leader_file.as_posix(),old_leader_sha256=sha(leader_file),candidate_minima_artifact=candidate_minima.as_posix(),candidate_minima_sha256=sha(candidate_minima),comparators=selected_specs(leader_file),membership='Exact original football15574/chart2394 historical query memberships and original1795/434 future membership bytes reused; no reranking or future labels decoded',selectors='Football prior attempts/carries/targets/carries+targets; chart signed prior chart points, NOT workload. Last3 earlier AVAILABLE slots; unknown slots consume window; week-earliest kickoff minus90minutes, seven-day strict availability assumption. Same memberships for every competitor.',views=['full_system','own_learned_only','three_core_history_learned_overlap','selected_controls_and_all_four_candidate_policies_learned_overlap','fallback_only'],shared_mask='Per target/population, intersect nonfallback supported query IDs for every retained comparator selection and all4C02policies/products. Strict included explicitly. Strict-only procedures have no three-core-history view.',comparisons='Same-policy/product original ordered-CDF primary comparison, plus frozen earlier full-panel family representatives for native MAE/Brier, intended-mean MSE and genuine-law CRPS; all paired on identical current-view IDs. No new old-control univariate view count.',chart='Qualified partial chart labels;35unknowncurrentlabels retained. Median tolerancecounts use exact0.02integer grid, means unrounded.',evidence='NEW_EXPERIMENT saved-row current-vintage retrospective participant diagnostic; seven exposed 2026weeks, not authenticated exante population or selected-pick/ROI skill. Common older selector memory constrains strict subgroup purity.',budget=dict(max_prediction_rows=600000,max_score_views=15000,max_comparison_rows=200000,wall_seconds=900,max_threads=1,max_peak_memory_bytes=2147483648),new_fits=0,new_forecasts=0,week8_outcomes_read=0)
 write(public_root/'FROZEN_PROTOCOL.json',p);return p

def loss(r,metric):
 if r['actual']is None or r['prediction']is None:return None
 if metric=='crps':return (r.get('distribution_summary')or{}).get('crps')
 return (r['prediction']-r['actual'])**2 if metric in('mse','brier')else abs(r['prediction']-r['actual'])

def paired(rows,other,metric):
 pairs=[]
 for r in rows:
  o=other.get(identity(r))
  if o is None:continue
  if r['actual']!=o['actual']or r['position']!=o['position']:raise ValueError('paired source label/role mismatch')
  a,b=loss(r,metric),loss(o,metric)
  if a is not None and b is not None:pairs.append((r,o,a,b))
 if not pairs:return dict(status='UNESTABLISHED',reason='no jointly supported paired metric rows',metric=metric,paired_n=0)
 n=len(pairs);a=math.fsum(p[2]for p in pairs)/n;b=math.fsum(p[3]for p in pairs)/n;delta=a-b;games=collections.defaultdict(list);weeks=collections.defaultdict(list)
 for r,o,x,y in pairs:games[r['game_id']].append(x-y);weeks[r['week']].append(x-y)
 g=len(games);se=math.sqrt(g/(g-1)*math.fsum((math.fsum(v)-len(v)*delta)**2 for v in games.values())/n**2)if g>=8 else None
 return dict(status='PAIRED_RETAINED_ROWS',metric=metric,candidate_error=a,comparator_error=b,absolute_error_delta=delta,relative_error_delta=delta/b if b else None,paired_n=n,unique_games=g,membership_sha256=digest(sorted(identity(p[0])for p in pairs)),comparator_procedure_id=pairs[0][1]['procedure_id'],comparator_history_regime=pairs[0][1]['history_regime'],comparator_product_id=pairs[0][1]['product_id'],candidate_fallback_n=sum(p[0]['fallback']!='none'for p in pairs),comparator_fallback_n=sum(p[1]['fallback']!='none'for p in pairs),cutoff_policy='Original per-game feature/weekly model origins retained, strict7day availability reconstruction. Comparator may use a different declared fit-history policy; not automatically a same-information learner ablation.',uncertainty=dict(week_clusters=len(weeks),week_interval=None,reason='fewer than8exposedweekclusters; no selection/multiplicity adjustment',game_cluster_sensitivity_se=se,game_cluster_normal95_sensitivity=[delta-1.96*se,delta+1.96*se]if se is not None else None,week_mean_deltas={str(k):fmean(v)for k,v in sorted(weeks.items())}))

def metrics(rows,target,product):
 scored=[r for r in rows if r['prediction']is not None and r['actual']is not None];p=[r['prediction']for r in scored];y=[r['actual']for r in scored];out=point_metrics(p,y,target)
 if out.get('log_loss')==math.inf:out['log_loss']='Infinity'
 out.update(forecast_rows=len(rows),forecast_games=len({r['game_id']for r in rows}),scored_n=len(scored),n=len(scored),unique_games=len({r['game_id']for r in scored}),fallback_rows=sum(r['fallback']!='none'for r in rows),scored_fallback_rows=sum(r['fallback']!='none'for r in scored),missing_actual_n=sum(r['actual']is None for r in rows),fallback_source_counts=dict(collections.Counter(r['fallback']for r in rows if r['fallback']!='none')))
 ds=[r.get('distribution_summary')for r in scored]
 if ds and all(d is not None for d in ds):
  inf=sum(bool(d['infinite_nll'])for d in ds);out.update(CRPS=fmean(d['crps']for d in ds),NLL=None if inf else fmean(d['nll']for d in ds),infinite_NLL=inf,NLL_state='INFINITE'if inf else'FINITE',interval90_width=fmean(d['interval90_width']for d in ds),interval90_coverage=fmean(d['interval90_covered']for d in ds),mean_zero_mass=fmean(d['zero_mass']for d in ds))
 elif not ds:out.update(CRPS=None,NLL=None,infinite_NLL=0,NLL_state='NO_SCORED_ROWS',interval90_width=None,interval90_coverage=None,mean_zero_mass=None)
 if target==CHART and product=='lower_median'and scored:
  exact=chart_median_precision(p,y,product_id=product);out.update({k:v['rate']for k,v in exact.items()});out['precision_counts_exact_grid']=exact
 metric='brier'if target=='anytime_td'else'mae';fb=[r for r in scored if r['fallback']!='none'];learn=[r for r in scored if r['fallback']=='none'];n=len(scored)
 out['fallback_decomposition']=dict(metric=metric,full_n=n,fallback_n=len(fb),learned_n=len(learn),fallback_loss_sum=math.fsum(loss(r,metric)for r in fb),learned_loss_sum=math.fsum(loss(r,metric)for r in learn),fallback_contribution=math.fsum(loss(r,metric)for r in fb)/n if n else None,learned_contribution=math.fsum(loss(r,metric)for r in learn)/n if n else None)
 return out

def evaluate(candidates,controls,membership,protocol_sha,specs):
 indexed={};labels={};own=collections.defaultdict(dict)
 for r in candidates:
  k=modelkey(r);ident=identity(r)
  if ident not in membership:raise ValueError('candidate outside frozen membership')
  if ident in own[k]:raise ValueError('duplicate candidate view')
  own[k][ident]=r
  if ident in labels and labels[ident]!=(r['actual'],r['position']):raise ValueError('candidate labels differ')
  labels[ident]=(r['actual'],r['position'])
 for r in controls:
  ident=identity(r)
  if ident not in membership:raise ValueError('control outside frozen historical query')
  if labels.get(ident)!=(r['actual'],r['position']):raise ValueError('control label/role mismatch')
  k=modelkey(r)
  if ident in indexed.setdefault(k,{}):raise ValueError('duplicate control view')
  indexed[k][ident]=r
 # Freeze a balanced all-selected-controls learned mask independent of errors.
 panels=collections.defaultdict(list)
 for k,rs in own.items():
  for t,pop in {(r['target'],r['population'])for r in rs.values()}:panels[t,pop].append({i for i,r in rs.items()if(r['target'],r['population'])==(t,pop)and r['fallback']=='none'and r['prediction']is not None and r['actual']is not None})
 for s in specs:
  rs=indexed.get((s['procedure_id'],s['history_regime'],s['product_id']),{})
  for t,pop in {(r['target'],r['population'])for r in rs.values()if r['target']==s['target']}:
   panels[t,pop].append({i for i,r in rs.items()if(r['target'],r['population'])==(t,pop)and r['fallback']=='none'and r['prediction']is not None and r['actual']is not None})
 shared={k:set.intersection(*v)for k,v in panels.items()};core={}
 for proc,arm,product in own:
  if proc.endswith(':strict-current-inputs'):continue
  if all((proc,a,product)in own for a in CORE):core[proc,product]=set.intersection(*({i for i,r in own[proc,a,product].items()if r['fallback']=='none'and r['prediction']is not None and r['actual']is not None}for a in CORE))
 grouped=collections.defaultdict(list)
 for r in candidates:
  i=identity(r);views=['full_system']
  if r['fallback']=='none':views.append('own_learned_only')
  else:views.append('fallback_only')
  if i in shared[r['target'],r['population']]:views.append('selected_controls_and_all_four_candidate_policies_learned_overlap')
  if i in core.get((r['procedure_id'],r['product_id']),set()):views.append('three_core_history_learned_overlap')
  for cohort in membership[i]['cohorts']:
   for view in views:grouped[(*modelkey(r),r['target'],r['population'],cohort,view)].append(r)
 output=[];comparisons=[];dates=[]
 for dims,rows in sorted(grouped.items()):
  proc,arm,product,target,pop,cohort,view=dims;record='C02-SUBGROUP-'+digest(dims)[:24];scored=[r for r in rows if r['actual']is not None and r['prediction']is not None];policy=rows[0]['policy_id'];strict=proc.endswith(':strict-current-inputs');oldproc=('v2-qualified-partial-chart-direct-wave-v1:'if target==CHART else'v2-distribution-controls-reconstruction-v2:')+'ordered_leaf_cdf:'+('strict-current-inputs'if strict else'common-feature-memory');primary=paired(rows,indexed.get((oldproc,arm,product),{}),'brier'if target=='anytime_td'else'mae')
  out=dict(record_id=record,procedure_id=proc,procedure_family_id='ordered_leaf_cdf',product_id=product,target=target,population=pop,history_regime=arm,policy_id=policy,information_policy=rows[0]['information_policy'],cohort_id=cohort,fallback_view=view,season=2026,week='ALL',position='ALL',evaluation_seasons=[2026],evaluation_weeks=sorted({r['week']for r in scored}),evaluation_panel_id=VERSION,record_kind='NEW_EXPERIMENT_CURRENT_VINTAGE_PARTICIPANT_DIAGNOSTIC',evidence='NEW_EXPERIMENT',source_vintage='current_vintage_reconstruction',cohort_membership_sha256=digest(sorted(identity(r)for r in rows)),scored_membership_sha256=digest(sorted(identity(r)for r in scored)),cohort_protocol_sha256=protocol_sha,cohort_limit='Retrospective observed-stat-row universe; same inherited earlier-feature-defined ranks. Chart point history is not workload; common older selector means strict subgroup system is not information-pure.',selector_quantity='prior_chart_point_mean_last3_slots'if target==CHART else'prior_opportunity_mean_last3_slots',comparison=primary,**metrics(rows,target,product))
  if target==CHART:out.update(point_grid_denominator=50,chart_source_policy='v2-nick-chart-ppr-nflverse-explicit-zero-subset-v2')
  output.append(out)
  dates.append(dict(source_row_index=len(output)-1,evaluation_seasons=[2026],evaluation_weeks=out['evaluation_weeks'],actual_scored_weeks=out['evaluation_weeks'],forecast_query_weeks=sorted({r['week']for r in rows}),registered_panel_weeks=list(range(1,8))))
  for s in specs:
   if s['target']!=target:continue
   if s['purpose']=='intended_mean'and product!='mean':continue
   if s['purpose']=='forecast_law'and product not in('mean','event_probability'):continue
   metric=('brier'if target=='anytime_td'else'mae')if s['purpose']=='display_point'else'mse'if s['purpose']=='intended_mean'else'brier'if target=='anytime_td'else'crps'
   c=paired(rows,indexed.get((s['procedure_id'],s['history_regime'],s['product_id']),{}),metric)
   comparisons.append(dict(source_record_id=record,purpose=s['purpose'],comparator_family=s['family'],old_full_primary_rank=s['old_rank'],selector='Frozen previous full-primary family representative, held fixed across subgroups; exposed descriptive comparator, not pregame routing',**c))
 return output,comparisons,dates,{f'{t}:{p}':len(v)for(t,p),v in shared.items()}

def run(private_root,public_root):
 private_root,public_root=map(Path,(private_root,public_root));started=time.monotonic();p=load(public_root/'FROZEN_PROTOCOL.json')
 if p['code_sha256']!=sha(__file__)or p['scoring_code_sha256']!=sha(Path(__file__).with_name('scoring.py'))or p['precision_code_sha256']!=sha(Path(__file__).with_name('precision_grid.py')):raise ValueError('registered code changed')
 for b in p['source_bindings']:
  if sha(private_root/FILES[b['artifact_id']][0])!=b['sha256']:raise ValueError('retained source hash changed')
 for b in p['hgb_chunk_bindings']:
  if sha(private_root/'hgb-history-v1/prediction-chunks'/b['artifact_id'])!=b['sha256']:raise ValueError('retained HGB chunk changed')
 if sha(p['old_leader_artifact'])!=p['old_leader_sha256']or sha(p['candidate_minima_artifact'])!=p['candidate_minima_sha256']:raise ValueError('frozen comparator choice changed')
 checks=load(public_root/'SOFTWARE_CHECKS.json')
 if checks['status']!='PASS'or checks['code_sha256']!=sha(__file__):raise ValueError('exact-code software checks required')
 write(public_root/'EXECUTION_REGISTRATION.json',dict(version=VERSION,started_at_utc=now(),protocol_sha256=sha(public_root/'FROZEN_PROTOCOL.json'),new_fits=0,new_forecasts=0,week8_outcomes_read=0))
 members={};future_counts={}
 for aid in('football_membership','chart_membership'):
  for m in json.loads(gzip.decompress((private_root/FILES[aid][0]).read_bytes())):
   k=tuple(m['key'])
   if k in members:raise ValueError('duplicate frozen membership')
   members[k]={k:v for k,v in m.items()if k!='key'}
 for aid in('football_future_membership','chart_future_membership'):
  ms=json.loads(gzip.decompress((private_root/FILES[aid][0]).read_bytes()));future_counts[aid]=dict(frozen_queries=len(ms),unique_games=len({r['key'][0]for r in ms}),status='REUSED_FROZEN_UNSCORED; NO_FUTURE_OUTCOME_OR_FORECAST_DECODE',unranked=sum(r['rank']is None for r in ms))
 candidates=[normalize(r,'candidate')for r in packet_rows(private_root/FILES['candidate'][0])];candidates=[r for r in candidates if r is not None]
 need={(s['procedure_id'],s['history_regime'],s['product_id'])for s in p['comparators']}
 # All original ordered laws are needed for exact same-policy C02 comparisons.
 controls=[]
 for aid in('football_laws','chart_controls','empirical','count_role'):
  with gzip.open(private_root/FILES[aid][0],'rt',newline='')as f:
   for raw in csv.DictReader(f):
    if int(raw.get('season',2026))!=2026 or not 1<=int(raw['week'])<=7:continue
    r=normalize(raw,aid)
    if modelkey(r)in need or 'ordered_leaf_cdf:'in r['procedure_id']:controls.append(r)
 for b in p['hgb_chunk_bindings']:
  for raw in packet_rows(private_root/'hgb-history-v1/prediction-chunks'/b['artifact_id']):
   r=normalize(raw,'hgb')
   if r is not None and modelkey(r)in need:controls.append(r)
 if len(candidates)+len(controls)>p['budget']['max_prediction_rows']:raise RuntimeError('PREDICTION_REPLAY_BUDGET')
 scores,comp,dates,overlap=evaluate(candidates,controls,members,sha(public_root/'FROZEN_PROTOCOL.json'),p['comparators'])
 if len(scores)>p['budget']['max_score_views']or len(comp)>p['budget']['max_comparison_rows']or time.monotonic()-started>p['budget']['wall_seconds']:raise RuntimeError('OUTPUT_REPLAY_BUDGET')
 write(public_root/'SCORES.json',scores);write(public_root/'PAIRED_COMPARISONS.json',dict(source_score_sha256=sha(public_root/'SCORES.json'),rows=comp));write(public_root/'SCORE_DATE_PROJECTION.json',dict(source_score_sha256=sha(public_root/'SCORES.json'),source_row_unit='zero-basedindexinimmutableSCORES.json',rows=dates))
 for name,rs in [('SCORES.csv',scores),('PAIRED_COMPARISONS.csv',comp)]:
  with(public_root/name).open('x',newline='')as f:
   keys=list(dict.fromkeys(k for r in rs for k in r));w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows({k:json.dumps(v,sort_keys=True,separators=(',',':'))if isinstance(v,(dict,list))else v for k,v in r.items()}for r in rs)
 receipt=dict(version=VERSION,state='COMPLETE_SAVED_ROW_SUBGROUP_EXTENSION',completed_at_utc=now(),protocol_sha256=sha(public_root/'FROZEN_PROTOCOL.json'),code_sha256=sha(__file__),query_cells=len(members),football_query_cells=sum(k[2]!=CHART for k in members),chart_query_cells=sum(k[2]==CHART for k in members),unique_games=len({k[0]for k in members}),unique_player_games=len({k[:2]for k in members}),candidate_retained_prediction_views=len(candidates),control_retained_reference_views=len(controls),new_score_views=len(scores),new_comparison_views=len(comp),score_sha256=sha(public_root/'SCORES.json'),comparison_sha256=sha(public_root/'PAIRED_COMPARISONS.json'),shared_learned_query_counts=overlap,future_membership_reuse=future_counts,new_fits=0,new_forecasts=0,week8_outcomes_read=0,wall_seconds=time.monotonic()-started,old_univariate_score_views_recounted=0,private_new_artifacts=0,private_sources='Reused source and membership bytes already in approved root-managed private companion; new backup receipt binds this public protocol.')
 write(public_root/'RUN_RECEIPT.json',receipt);return receipt
