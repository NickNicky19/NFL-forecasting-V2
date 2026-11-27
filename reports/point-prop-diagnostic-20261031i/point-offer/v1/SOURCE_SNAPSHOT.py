"""Finite retained-point diagnostics; never fits, predicts or changes a pick."""
import argparse,collections,csv,gc,gzip,hashlib,json,math,resource,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2 import full_provider_prop_replay as core,scoring
from nfl_v2.shared_subgroups import canonical,now,sha,write,packet_rows
from nfl_v2.paired_uncertainty import paired_losses
from tools.numerical_championship import normalize,csvwrite

VERSION='v2-point-offer-disagreement-retained-diagnostic-20261031i-v1'
HGB='hgb-direct-history-controls-v1:';BASE='v2-distribution-controls-reconstruction-v2:';C02='v2-c02-explicit-lag-block-removal-leaf-cdf-v1';D='v2-qualified-position-defense-information-wave-v1:'
FOCAL={'pass_yd':(HGB+'absolute_error_point','H-MULTI','absolute_error_point'),'pass_cmp':(D+'D1','H-MULTI','lower_median')}
RECIPES=[('empirical-player-history-control-v1','H-MULTI','lower_median'),('empirical-player-history-control-v1','H-MULTI','mean'),(HGB+'absolute_error_point','H-MULTI','absolute_error_point'),(HGB+'squared_error_mean','H-MULTI','squared_error_mean'),(BASE+'ordered_leaf_cdf','H-MULTI','lower_median'),(C02,'H-MULTI','lower_median'),(C02,'H-MULTI','mean'),(D+'D1','H-MULTI','lower_median'),(D+'D1','H-MULTI','mean'),(D+'D2','H-MULTI','lower_median'),(BASE+'regularized_glm_law','H-MULTI','lower_median'),(BASE+'ordered_leaf_cdf:strict-current-inputs','H-CURRENT','lower_median'),(C02+':strict-current-inputs','H-CURRENT','lower_median'),(C02+':strict-current-inputs','H-CURRENT','mean'),(D+'D2:strict-current-inputs','H-CURRENT','mean'),('v2-chronological-category-selector:EARLIER_AVAILABLE_2026_SCORE_MEMORY','H-MULTI','selected_point')]
CONTROLS=(core.RAW,core.ADJUSTED)
STATES=('WIN','LOSS','PUSH','VOID','PENDING','MISSING_ACTUAL','UNKNOWN_PARTICIPATION','UNRESOLVED_CONTRACT')

def locations(a,w):
 if w==5:return a.root/'reports/baselines-coverage-20261031h/actual-method-w5/method-comparison-v1',a.private_root/'baselines-coverage-20261031h-w5-method-comparison-v1'
 return a.root/f'reports/completion-20261031g/roster/w{w}-rolling-method-comparison-v1',a.private_root/f'completion-20261031g-w{w}-rolling-method-comparison-v1'
def ident(k):return hashlib.sha256(canonical(k)).hexdigest()[:24]
def quantiles(vals):
 vals=sorted(vals)
 def q(p):
  n=(len(vals)-1)*p;i=int(n);j=min(i+1,len(vals)-1);return vals[i]+(vals[j]-vals[i])*(n-i)
 return dict(n=len(vals),mean=math.fsum(vals)/len(vals),minimum=vals[0],**{'p'+str(int(p*100)):q(p) for p in(.05,.1,.25,.5,.75,.9,.95)},maximum=vals[-1]) if vals else dict(n=0,mean=None,null_reason='NO_SUPPORTED_VALUES')

def prepare(a):
 if a.output.exists() or a.private_output.exists():raise ValueError('fresh diagnostic destinations required')
 a.output.mkdir(parents=True);a.private_output.mkdir(parents=True);bindings=[];roster=[];masks=[]
 for week in(5,6,7):
  public,private=locations(a,week);f=private/'FROZEN_SELECTIONS_AND_K.json.gz';plans=json.loads(gzip.decompress(f.read_bytes()));lookup={tuple(v['recipe']):(tag,v) for tag,v in plans['plans'].items() if v['rule']=='P1'}
  for file in(f,private/'GRADED_METHOD_ROWS.json.gz',public/'SCORES.json'):
   bindings.append(dict(week=week,source_id=private.name if file.parent==private else public.relative_to(a.root).as_posix(),member=file.name,sha256=sha(file)))
  for target,focal in FOCAL.items():
   ftag,fp=lookup[target,*focal];fmask={r['source_row_index'] for r in fp['rows'] if r['admitted'] and r['point'] is not None};fl={r['source_row_index'] for r in fp['rows'] if r['admitted'] and r['point'] is not None and r['fallback']=='none'}
   for recipe in RECIPES:
    tag,plan=lookup[target,*recipe];own={r['source_row_index'] for r in plan['rows'] if r['admitted'] and r['point'] is not None};learned={r['source_row_index'] for r in plan['rows'] if r['admitted'] and r['point'] is not None and r['fallback']=='none'}
    roster.append(dict(week=week,target=target,recipe=list(recipe),method_id=tag,kind='V2_POINT'))
    masks.append(dict(week=week,target=target,recipe=list(recipe),own_ids=sorted(own),focal_common_ids=sorted(own&fmask),common_learned_ids=sorted(learned&fl)))
   for control in CONTROLS:
    link=next(z for z in plans['baseline_links'] if z['method_id']==ftag and z['control']==control)
    roster.append(dict(week=week,target=target,recipe=[control,'ARCHIVED','saved_precision_point'],method_id=link['control_id'],kind='SAVED_POINT_MATCHED_TO_FOCAL'))
    masks.append(dict(week=week,target=target,recipe=[control,'ARCHIVED','saved_precision_point'],own_ids=sorted(fmask),focal_common_ids=sorted(fmask),common_learned_ids=None,point_nonmissing_requires_saved_grade_projection=True))
 raw=next(x for x in json.loads((a.root/'reports/championship-20261030f/numerical-v2/FROZEN_PROTOCOL.json').read_bytes())['sources'] if x['season']==2026)
 broad=[r for r in raw['members'] if r['source_id']=='defense' or(r['source_id']=='hgb' and any(f'W{w:02}-pass_yd-H-MULTI-absolute_error_point' in r['member'] for w in(5,6,7)))]
 for r in broad:
  if sha(a.private_root/r['member'])!=r['sha256']:raise ValueError('retained broad source changed')
 protocol=dict(version=VERSION,state='FROZEN_BEFORE_NEW_POINT_OFFER_DIAGNOSTIC_METRICS',at=now(),code_sha256=sha(__file__),metric_helper_sha256=sha(scoring.__file__),bootstrap_helper_sha256=sha(core.pilot.__file__),paired_helper_sha256=sha(a.root/'nfl_v2/paired_uncertainty.py'),normalization_helper_sha256=sha(a.root/'tools/numerical_championship.py'),root_protocol_sha256=sha(a.root/'reports/point-prop-diagnostic-20261031i/FROZEN_PROTOCOL.json'),source_bindings=bindings,roster=roster,preoutcome_admission_masks=masks,broad_sources=broad,focals={t:list(k) for t,k in FOCAL.items()},period=[2026,5,6,7],
  design='Own eligible full-system, each comparator versus focal on identical decision-eligible offer rows, and both-known-learned overlap. Saved raw/adjusted controls already frozen on focal masks; their model fallback is unknown, so learned-only comparison is not applicable. Keep unavailable/unknown rows in coverage. Deduplicate identical recipe/mask evaluations with explicit context aliases.',
  population='For focal only: same42source-covered games duringW5-7, all original qualified primary QBparticipant forecasts versus offeredplayer subset using unchanged kickoff-source forecasts, then earlier-decision eligible overlap. These kickoff population views are not authenticated T90issuance. Common saved points must equal earlier qualified method ranking_point; no new vector/inference.',
  metrics='MAE/MSE/RMSE/bias/P90/P95/max; explicit exact and strict/inclusive1/5/10unit tolerances; forecast-minus-line and actual-minus-line quantiles5/10/25/50/75/90/95 plus mean/min/max; original selected-Over/Under/Combined states and correctly weighted hit rates. No percentage-of-actual error. Paired MAElosses on exact common rows with game sensitivity;3weeks insufficient for registered weekCI.',
  adapter='Method point is retained ranking_point/frozen plan point, NOT joined prediction (which is saved adjusted-site point). Raw forecast source prediction is its model point. Raw and adjusted controls preserve their saved precision; lost internal digits not invented.',
  functional='HGB L1 is direct absolute-error objective. D1lower median comes from squared-error forest partitions plus5%prior, not direct L1fitting. Mean/median views are distinct outputs of shared mechanism, not independent learners.',
  inference_limit='Measured population, residual and line-gap changes are descriptive; do not attribute causally to backups, L1, role or modelbug without new isolated test. No inversion, posthoc routing, calibration or selected-case deletion.',
  chronology='Inherited current-vintage7day NFLsource reconstruction plus authenticated retained threshold/context source clocks; exact existing G/Hadmission masks reused. No Week8labels decoded. All historical labels previously exposed.',
  worked_examples='Privately retain first chronological(sourceweek,index) WIN and LOSS for each available selected side per focal, solely explanatory; no new selection rule.',
  budget=dict(wall_seconds=300,max_RSS_bytes=1073741824,max_private_bytes=4194304,max_threads=1,new_fits=0,new_inference=0,new_probabilities=0,new_capture=0))
 write(a.output/'FROZEN_PROTOCOL.json',protocol);(a.output/'SOURCE_SNAPSHOT.py').write_bytes(Path(__file__).read_bytes());print(json.dumps(dict(protocol_sha256=sha(a.output/'FROZEN_PROTOCOL.json'),weekly_roster=len(roster),broad_members=len(broad))))

def run(a):
 p=json.loads((a.output/'FROZEN_PROTOCOL.json').read_bytes());start=time.monotonic();cpu=time.process_time()
 if sha(__file__)!=p['code_sha256']:raise ValueError('frozen executor changed')
 def guard():
  if time.monotonic()-start>300 or resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>1073741824:raise RuntimeError('point diagnostic resource limit')
 data=collections.defaultdict(dict);full={};covered_games=set();sources={}
 for week in(5,6,7):
  public,private=locations(a,week);file=private/'GRADED_METHOD_ROWS.json.gz'
  if sha(file)!=next(s['sha256'] for s in p['source_bindings'] if s['week']==week and s['member']==file.name):raise ValueError('retained grade source changed')
  g=json.loads(gzip.decompress(file.read_bytes()))
  for spec in[r for r in p['roster'] if r['week']==week]:
   target=spec['target'];recipe=tuple(spec['recipe']);key=(target,*recipe);tag=spec['method_id'];rows=g['graded'][tag];full[target,week]=len(rows)
   for r in rows:
    if r['game_id']:covered_games.add(r['game_id'])
    point=r.get('ranking_point');available=bool(r['admitted'] and point is not None and math.isfinite(float(point)))
    row=dict(week=week,source_row_index=r['source_row_index'],game_id=r['game_id'],player_id=r['player_id'],target=target,position=r['position'],line=float(r['line']),actual=r['actual'],point=float(point) if point is not None else None,admitted=available,selected_side=r['selected_side'],statistical_state=r['statistical_state'],participation=r['participation'],fallback=r.get('fallback') if spec['kind']=='V2_POINT' else None,origin='V2_RETAINED_POINT' if spec['kind']=='V2_POINT' else 'SAVED_POINT_METADATA_LIMITED',decision_time=r.get('source_server_clock',r.get('server_retained_by')),kickoff=r['kickoff'],source_method_id=tag,source_field='ranking_point',source_id=private.name)
    if available:
     expected='over' if point>float(r['line']) else 'under' if point<float(r['line']) else None
     if expected!=row['selected_side']:raise ValueError('frozen point-versus-line direction mismatch')
    data[key][week,r['source_row_index']]=row
  del g;gc.collect();guard()
 # Metadata frozen masks are verified before new metrics.
 for mask in p['preoutcome_admission_masks']:
  k=(mask['target'],*mask['recipe']);own={idx for(w,idx),r in data[k].items() if w==mask['week'] and r['admitted']}
  planned=set(mask['own_ids'])
  if mask.get('point_nonmissing_requires_saved_grade_projection'):
   if not own<=planned:raise ValueError('saved control escaped focal mask')
  elif own!=planned:raise ValueError('admitted mask changed')
 scores=[];metricrows=[];pairs=[];contextmap=[];dedup={};private_rows=[]
 def emit(key,rows,context,outer=None,offer=True):
  target,proc,arm,product=key;rr=[r for r in rows if r['admitted']];supported=[r for r in rr if r['actual'] is not None and r['participation']=='VERIFIED_PLAYED_POSITIVE_PHYSICAL'];maskhash=hashlib.sha256(canonical([(r['week'],r['source_row_index']) for r in sorted(rr,key=lambda r:(r['week'],r['source_row_index']))])).hexdigest();dedupkey=(key,maskhash,offer)
  if dedupkey in dedup:contextmap.append(dict(context=context,record_id=dedup[dedupkey],same_mask_alias=True));return dedup[dedupkey]
  rid='I-POINT-'+ident(dedupkey);dedup[dedupkey]=rid;outer=len(rows) if outer is None else outer
  met=scoring.point_metrics([r['point'] for r in supported],[r['actual'] for r in supported],target);precision={}
  for tol in(1,5,10):
   for inclusive in(False,True):
    name=f"abs_{'le' if inclusive else'lt'}_{tol}";num=sum(abs(r['point']-r['actual'])<=tol if inclusive else abs(r['point']-r['actual'])<tol for r in supported);precision[name]=dict(numerator=num,denominator=len(supported),rate=num/len(supported) if supported else None)
  precision['exact_rate']=dict(numerator=sum(r['point']==r['actual'] for r in supported),denominator=len(supported),rate=sum(r['point']==r['actual'] for r in supported)/len(supported) if supported else None)
  knownfallback=None if proc in CONTROLS else sum(r['fallback']!='none' for r in rr);row=dict(record_id=rid,record_kind='forecast_evaluation_view',procedure_id=proc,history_regime=arm,product_id=product,target=target,evaluation_panel_id=VERSION,evaluation_seasons=[2026],evaluation_weeks=[5,6,7],season=2026,week='ALL',population=context,horizon_id='RETAINED_DECISION_ELIGIBLE_KNOWN_TARGET_TIME' if offer else 'SAME_SAVED_KICKOFF_POPULATION_DIAGNOSTIC',forecast_rows=len(rr),outer_opportunities=outer,unavailable_forecasts=outer-len(rr),missing_actuals=len(rr)-len(supported),fallback_rows=knownfallback,fallback_rate=knownfallback/len(rr) if knownfallback is not None and rr else None,fallback_scope='Known V2 source fallback; archived saved-control model metadata unknown',precision_counts=precision,unique_games=len({r['game_id'] for r in supported}),unique_players=len({r['player_id'] for r in supported}),membership_sha256=maskhash,evidence='NEW_DIAGNOSTIC_FROM_RETAINED_POINTS_AND_OUTCOMES',**met)
  if offer:
   row.update(forecast_minus_line=quantiles([r['point']-r['line'] for r in rr]),actual_minus_line=quantiles([r['actual']-r['line'] for r in supported]),point_above_line=sum(r['point']>r['line'] for r in rr),point_below_line=sum(r['point']<r['line'] for r in rr),point_equal_line=sum(r['point']==r['line'] for r in rr),actual_over_frequency=sum(r['actual']>r['line'] for r in supported)/len(supported) if supported else None)
  scores.append(row);metricrows.append(row);contextmap.append(dict(context=context,record_id=rid,same_mask_alias=False))
  if offer:
   trip=[]
   for side in('over','under','Combined'):
    chosen=[r for r in rr if r['selected_side'] and(side=='Combined' or r['selected_side']==side)];v=core.score_row(chosen,rows,strategy=proc,target=target,cohort=context,side=side);v.update(record_id='I-SIDE-'+ident([dedupkey,side]),procedure_id=proc,history_regime=arm,product_id=product,decision_rule='P1',season=2026,week='ALL',evaluation_seasons=[2026],evaluation_weeks=[5,6,7],evaluation_panel_id=VERSION,time_panel_id='2026W5_W7_RETAINED_POINT_DIAGNOSTIC',horizon_id=row['horizon_id'],selection_evidence='RETROSPECTIVE_RULE_REPLAY',membership_sha256=maskhash);v['selection_metrics'].update(selection_pool_count=outer,selection_coverage=len(chosen)/outer if outer else None,admitted_forecast_opportunities=len(rr),unavailable_forecast_opportunities=outer-len(rr),admitted_rule_abstentions=sum(r['selected_side'] is None for r in rr));scores.append(v);trip.append(v)
   core.check_triplet(trip)
  return rid
 for key,dd in sorted(data.items()):
  target=key[0];fkey=(target,*FOCAL[target]);aa=data[fkey];own=[r for q,r in sorted(dd.items()) if r['admitted']];commonq=sorted(q for q in set(dd)&set(aa) if dd[q]['admitted'] and aa[q]['admitted']);common=[dd[q] for q in commonq];learnq=[q for q in commonq if dd[q]['fallback']=='none' and aa[q]['fallback']=='none' and key[1] not in CONTROLS];outer=sum(full[target,w] for w in(5,6,7))
  for q in commonq:
   if any(dd[q][k]!=aa[q][k] for k in('game_id','player_id','target','line','actual','decision_time')):raise ValueError('focal/comparator identity, label or cutoff differs')
  emit(key,own,'OWN_DECISION_ELIGIBLE_FULL_SYSTEM',outer)
  for context,qq in [('FOCAL_COMMON_FULL_SYSTEM',commonq),('FOCAL_COMMON_LEARNED_ONLY',learnq)]:
   if key[1] in CONTROLS and context.endswith('LEARNED_ONLY'):continue
   cand=[dd[q] for q in qq];foc=[aa[q] for q in qq];emit(key,cand,context,len(qq));emit(fkey,foc,context+':COMPARATOR='+key[1]+':'+key[3],len(qq));valid=[q for q in qq if dd[q]['actual'] is not None and dd[q]['participation']=='VERIFIED_PLAYED_POSITIVE_PHYSICAL'];u=paired_losses([abs(dd[q]['point']-dd[q]['actual']) for q in valid],[abs(aa[q]['point']-aa[q]['actual']) for q in valid],[q[0] for q in valid],[dd[q]['game_id'] for q in valid]);pairs.append(dict(target=target,candidate_recipe=list(key[1:]),comparator_recipe=list(fkey[1:]),context=context,metric='MAE',**u))
  private_rows.extend(dict(recipe=list(key),**r) for r in dd.values())
 # Same-game QB participant selection uses original unchanged kickoff predictions.
 broad=collections.defaultdict(dict);read=0
 for source in p['broad_sources']:
  file=a.private_root/source['member']
  if sha(file)!=source['sha256']:raise ValueError('broad source changed')
  for r in packet_rows(file):
   read+=1
   if read%10000==0:guard()
   if int(r['week']) not in(5,6,7) or r['game_id'] not in covered_games:continue
   norm=normalize(r,source['source_id'],2026)
   if norm is None:continue
   k,w=norm
   if k[0] not in FOCAL or k!=(k[0],*FOCAL[k[0]]):continue
   q=(r['game_id'],r['player_id'],r['target']);actual=None if r.get('actual') in(None,'') else float(r['actual']);point=None if r.get('prediction') in(None,'') else float(r['prediction']);broad[k][q]=dict(week=w,source_row_index=ident(q),game_id=r['game_id'],player_id=r['player_id'],target=r['target'],position=r['position'],line=None,actual=actual,point=point,admitted=point is not None,participation='VERIFIED_PLAYED_POSITIVE_PHYSICAL' if actual is not None else 'UNKNOWN',fallback=r['fallback'],source_id=source['source_id'],source_member_sha256=source['sha256'])
  guard()
 population=[];examples=[]
 for target,focal in FOCAL.items():
  key=(target,*focal);br=broad[key];offered={(r['game_id'],r['player_id'],target) for r in data[key].values()};admitted={(r['game_id'],r['player_id'],target):r for r in data[key].values() if r['admitted']};selected=[r for q,r in br.items() if q in offered];eligible=[r for q,r in br.items() if q in admitted]
  for q,r in br.items():
   if q in admitted and(r['point']!=admitted[q]['point'] or r['actual']!=admitted[q]['actual']):raise ValueError('same saved kickoff point/label differs from qualified offer reconstruction')
  for name,rr in [('BROAD_SAME_42_GAME_QB_PARTICIPANTS',list(br.values())),('SAME_KICKOFF_FORECASTS_OFFERED_PLAYER_SUBSET',selected),('SAME_KICKOFF_FORECASTS_DECISION_ELIGIBLE_SUBSET',eligible)]:population.append(dict(target=target,context=name,record_id=emit(key,rr,name,offer=False)))
  for side in('over','under'):
   for state in('WIN','LOSS'):
    available=sorted((r for r in data[key].values() if r['admitted'] and r['selected_side']==side and r['statistical_state']==state),key=lambda r:(r['week'],r['source_row_index']));examples.append(dict(target=target,side=side,state=state,example=available[0] if available else None,reason=None if available else 'NO_CASE_IN_THIS_FROZEN_BUCKET'))
  private_rows.extend(dict(recipe=list(key),population_diagnostic=True,**r) for r in br.values())
 write(a.output/'SCORES.json',scores);write(a.output/'PAIRED_MAE_COMPARISONS.json',pairs);csvwrite(a.output/'PAIRED_MAE_COMPARISONS.csv',pairs);write(a.output/'CONTEXT_TO_DEDUPLICATED_SCORE.json',contextmap);write(a.output/'POPULATION_COMPARISON_BINDINGS.json',population);csvwrite(a.output/'POINT_METRICS_AND_GAPS.csv',metricrows)
 blob=gzip.compress(canonical(dict(rows=private_rows,worked_examples=examples)),mtime=0)
 if len(blob)>4194304:raise ValueError('private diagnostic cap')
 with(a.private_output/'POINT_DIAGNOSTIC_ROWS.json.gz').open('xb') as f:f.write(blob)
 write(a.output/'RUN_RECEIPT.json',dict(state='COMPLETE_RETAINED_POINT_OFFER_DIAGNOSTIC',at=now(),protocol_sha256=sha(a.output/'FROZEN_PROTOCOL.json'),score_sha256=sha(a.output/'SCORES.json'),canonical_score_views=len(scores),point_metric_views=len(metricrows),context_bindings=len(contextmap),paired_MAE_comparisons=len(pairs),retained_recipe_offer_rows=sum(len(v) for v in data.values()),broad_raw_rows_scanned=read,covered_games=len(covered_games),private_sha256=sha(a.private_output/'POINT_DIAGNOSTIC_ROWS.json.gz'),private_bytes=len(blob),new_fits=0,new_model_inference=0,new_probabilities=0,new_capture=0,new_NFL_observations=0,resources=dict(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)))
 print(json.dumps(dict(scores=len(scores),metrics=len(metricrows),pairs=len(pairs),private_bytes=len(blob),wall_seconds=time.monotonic()-start)))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=('prepare','run'));p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--private-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--private-output',type=Path,required=True);a=p.parse_args();prepare(a) if a.action=='prepare' else run(a)
