"""Gated147-opportunity2026 strict-current HGB reconstruction.

Readiness/freeze never fit or decode NFL labels. Execution requires a fresh
retention gate and independent exact-code/protocol review; no future capture.
"""
from __future__ import annotations
import collections,csv,gzip,hashlib,io,json,math,os,pickle,platform,re,resource,time
from pathlib import Path
import numpy as np
import sklearn
from threadpoolctl import threadpool_limits
from . import hgb_control as source,empirical_benchmark as empirical
from . import strict_hgb_2026_design as design,seasonal_rolling_v2 as score
VERSION='v2-original-hgb-2026-strict-current-execution-v1'
from . import expanded_retention_gate as retention
GATE_STATE=retention.GATE_STATE
PREFIT_STATE='PASS_STRICT_HGB_2026_PREFIT_REVIEW'
require_retention=retention.require_retention
sha=source.sha;now=source.now;write=source.immutable_json;canonical=source.canonical
FIELDS=('run_id','query_id','game_id','player_id','target','population','position','season','week','procedure_id','procedure_family_id','product_id','objective','history_regime','policy_id','information_policy','prediction','actual','actual_status','fallback','fallback_source','fallback_source_n','status','fit_slot','fit_state','model_artifact_id','feature_cutoff','fit_cutoff','latest_training_label_available','latest_training_feature_available','latest_feature_available','actual_generated_at','evidence_tier')
class ResourceBudget(RuntimeError):pass

def planned_grid():
 return [dict(slot=f'W{w:02}-{t}-{o}',week=w,target=t,objective=o,state='NOT_RUN',forecast_state='NOT_RUN')for w in range(1,8)for t in source.TARGETS for o in source.objectives(t)]


def readiness(*,prepared_public,prepared_private,source_root,retention_gate=None,repository=None):
 prepared_public,prepared_private,source_root=map(Path,(prepared_public,prepared_private,source_root));p=json.loads((prepared_public/'PREPARED_PROTOCOL_NO_FITS.json').read_text());checks=[]
 if p['code_sha256']!=sha(design.__file__)or p['params']!=source.PARAMS:raise ValueError('PREPARED_ADAPTER_OR_ORIGINAL_PARAMETERS_CHANGED')
 for name,h in p['helpers'].items():
  if sha(Path(__file__).with_name(name))!=h:raise ValueError('PREPARED_HELPER_CHANGED')
 for item in p['source_ids']:checks.append(dict(source_id=item['name'],hash_matches=(source_root/item['name']).is_file()and sha(source_root/item['name'])==item['sha256']))
 q=prepared_private/'FROZEN_QUERY_METADATA.json';query_ok=q.is_file()and sha(q)==p['frozen_historical_query_sha256'];retention=False;reason=None
 try:require_retention(retention_gate,repository or Path(__file__).resolve().parents[1]);retention=True
 except(ValueError,OSError)as exc:reason=str(exc)
 return dict(state='READY_FOR_PROTOCOL_FREEZE'if retention and query_ok and all(r['hash_matches']for r in checks)else'BLOCKED_NO_EXECUTION',runner_code_sha256=sha(__file__),prepared_protocol_sha256=sha(prepared_public/'PREPARED_PROTOCOL_NO_FITS.json'),query_hash_matches=query_ok,source_checks=checks,retention_verified=retention,retention_reason=reason,nominal_cells=len(planned_grid()),actual_fit_calls=0,actual_forecasts=0,labels_decoded=0)

def freeze(*,prepared_public,prepared_private,source_root,retention_gate,repository,public,private,software_checks):
 check=readiness(prepared_public=prepared_public,prepared_private=prepared_private,source_root=source_root,retention_gate=retention_gate,repository=repository)
 if check['state']!='READY_FOR_PROTOCOL_FREEZE':raise ValueError('RETENTION_SOURCE_READINESS_GATE')
 software=json.loads(Path(software_checks).read_text())
 if software.get('state')!='PASS_NO_NFL_FIXTURES'or software.get('runner_code_sha256')!=sha(__file__):raise ValueError('RUNNER_FIXTURE_BINDING_REQUIRED')
 public,private=Path(public),Path(private)
 if public.exists()or private.exists():raise ValueError('FRESH_IMMUTABLE_RUN_FOLDERS_REQUIRED')
 public.mkdir(parents=True);private.mkdir(parents=True);prepared=json.loads((Path(prepared_public)/'PREPARED_PROTOCOL_NO_FITS.json').read_text());blob=(Path(prepared_private)/'FROZEN_QUERY_METADATA.json').read_bytes()
 with(private/'FROZEN_QUERY_METADATA.json').open('xb')as f:f.write(blob)
 p=dict(prepared,version=VERSION,run_id=VERSION+':2026W1-W7',state='FROZEN_AFTER_POSITIVE_RETENTION_BEFORE_NFL_LABEL_FEATURE_DECODE_OR_FITS',registered_at=now(),code_sha256=sha(__file__),prepared_protocol_sha256=sha(Path(prepared_public)/'PREPARED_PROTOCOL_NO_FITS.json'),helper_sha256={Path(m.__file__).name:sha(m.__file__)for m in(source,empirical,design,score,retention)},retention_gate_sha256=sha(retention_gate),retention_gate_state=GATE_STATE,software_checks_sha256=sha(software_checks),grid=planned_grid(),budget=dict(max_fit_calls=147,wall_seconds=600,cpu_seconds=900,max_threads=2,max_rss_bytes=2147483648,max_private_bytes=268435456,max_source_rows=200000,max_forecast_rows=28754,private_reserve_bytes=4194304),output='Immutablecellmodels/queryfeatures/trainingmemberships/labels/forecastpackets,flatCSV; nativeMAE/MSE/RMSE/bias/tails/exacttolerances;Brier/properbinarylogloss/prevalence/reliability;fullsystem/learned/fallbackviews; numericpointsarenotdistributions',chart_not_applicable=True,actual_fit_calls=0,new_future_forecasts=0)
 write(public/'FROZEN_PROTOCOL.json',p);return p

class Budget:
 def __init__(self,p,private):self.p=p;self.private=Path(private);self.start=time.monotonic();self.cpu=time.process_time();self.bytes=sum(f.stat().st_size for f in self.private.rglob('*')if f.is_file())
 def guard(self):
  if time.monotonic()-self.start>self.p['wall_seconds']or time.process_time()-self.cpu>self.p['cpu_seconds']:raise ResourceBudget('TIME_BUDGET')
  if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>self.p['max_rss_bytes']:raise ResourceBudget('RSS_BUDGET')
  if self.bytes>self.p['max_private_bytes']-self.p['private_reserve_bytes']:raise ResourceBudget('PRIVATE_BUDGET')
 def save(self,path,value,raw=False):
  self.guard();blob=gzip.compress(value if raw else canonical(value),mtime=0);self.guard()
  if self.bytes+len(blob)>self.p['max_private_bytes']-self.p['private_reserve_bytes']:raise ResourceBudget('PRIVATE_BUDGET_BEFORE_WRITE')
  with Path(path).open('xb')as f:f.write(blob);f.flush();os.fsync(f.fileno())
  self.bytes+=len(blob);return dict(artifact_id='STRICT2026-'+sha(path),bundle_name=Path(path).relative_to(self.private).as_posix(),sha256=sha(path),bytes=len(blob))
 def csv(self,path,rows):
  self.guard();remaining=self.p['max_private_bytes']-self.bytes-self.p['private_reserve_bytes']
  class Checked:
   def __init__(self,raw):self.raw=raw
   def write(self,data):
    if self.raw.tell()+len(data)>remaining:raise ResourceBudget('CSV_PRIVATE_BUDGET_BEFORE_WRITE')
    return self.raw.write(data)
   def __getattr__(self,k):return getattr(self.raw,k)
  with Path(path).open('xb')as raw:
   with gzip.GzipFile(fileobj=Checked(raw),mode='wb',mtime=0)as compressed:
    text=io.TextIOWrapper(compressed,encoding='utf-8',newline='');w=csv.DictWriter(text,fieldnames=FIELDS,extrasaction='ignore');w.writeheader()
    for i,r in enumerate(rows):
     w.writerow(r)
     if i%1000==0:text.flush();self.guard()
    text.flush();text.detach()
  self.bytes+=Path(path).stat().st_size;return dict(bundle_name=Path(path).name,sha256=sha(path),bytes=Path(path).stat().st_size)
 def resources(self):return dict(wall_seconds=time.monotonic()-self.start,cpu_seconds=time.process_time()-self.cpu,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,max_threads=2)

def load_current(source_root,p):
 root=Path(source_root);games=source.schedules(root/'games.csv');final={}
 with(root/'games.csv').open()as f:
  for r in csv.DictReader(f):
   if r['game_type']!='REG'or r['season']!='2026'or not 1<=int(r['week'])<=7:continue
   h,a,result,total=[empirical.numeric(r[k])for k in('home_score','away_score','result','total')];final[r['game_id']]=empirical.valid_count(h)and empirical.valid_count(a)and result==h-a and total==h+a
 needed=set(empirical.MAP.values())|set(empirical.PHYSICAL_COUNTS)|set(empirical.PHYSICAL_YARDS)|{'rushing_tds','receiving_tds'};rows=[];seen=set();counts=collections.Counter()
 with(root/'stats_player_week_2026.csv').open()as f:
  reader=csv.DictReader(f)
  if not needed<=set(reader.fieldnames):raise ValueError('SOURCE_SCHEMA')
  for r in reader:
   counts['source_rows']+=1
   if counts['source_rows']>p['budget']['max_source_rows']:raise ResourceBudget('SOURCE_ROW_BUDGET')
   if r['season_type']!='REG'or r['season']!='2026'or not 1<=int(r['week'])<=7 or r['position']not in source.POSITIONS:continue
   if not re.fullmatch(r'00-\d{7}',r['player_id']):raise ValueError('GSIS_BINDING')
   g=games.get(r['game_id']);key=r['game_id'],r['player_id']
   if key in seen or not g or g['season']!=2026 or g['week']!=int(r['week']):raise ValueError('SOURCE_GAME_IDENTITY')
   if(r['team'],r['opponent_team'])not in((g['home'],g['away']),(g['away'],g['home'])):raise ValueError('SOURCE_TEAM_IDENTITY')
   seen.add(key);v={k:empirical.numeric(r[k])for k in needed};played=any(empirical.valid_count(v[k])and v[k]>0 for k in empirical.PHYSICAL_COUNTS)or any(v[k]is not None and v[k]!=0 for k in empirical.PHYSICAL_YARDS);valid=bool(played and final.get(r['game_id'],False));counts['supported_appearance_finality'if valid else'unknown_appearance_or_finality']+=1
   rows.append(dict(season=2026,week=int(r['week']),game_id=r['game_id'],player_id=r['player_id'],position=r['position'],kickoff=g['kickoff'],available=g['kickoff']+7*86400,played=played,final=bool(final.get(r['game_id'])),values={t:empirical.target_value(t,v)if valid else None for t in source.TARGETS}))
 return rows,games,dict(counts)

def join_labels(queries,rows,p):
 lookup={(r['game_id'],r['player_id']):r for r in rows};out=[];seen=set()
 for raw in queries:
  q=design.canonical_query(raw);key=(q['game_id'],q['player_id'],q['target'],q['population'])
  if key in seen:raise ValueError('DUPLICATE_FROZEN_QUERY')
  seen.add(key);r=lookup.get(key[:2])
  if not r or r['position']!=q['position']or r['week']!=q['week']or q['position']not in p['source_role_contract'][q['population']].get(q['target'],[]):raise ValueError('FROZEN_QUERY_LABEL_ROLE_BINDING')
  value=r['values'][q['target']];out.append(dict(q,query_id=hashlib.sha256(canonical(q)).hexdigest(),actual=value,actual_status='SUPPORTED_OFFICIAL_PHYSICAL_STAT'if value is not None else'PARTICIPATION_OR_LABEL_UNKNOWN',cutoff=r['kickoff'],kickoff=r['kickoff']))
 return out

def reliability(rows):
 bins=[dict(n=0,sum_probability=0.,events=0.)for _ in range(10)]
 for r in rows:
  if r['actual']is None:continue
  p=r['prediction'];i=min(9,int(p*10));bins[i]['n']+=1;bins[i]['sum_probability']+=p;bins[i]['events']+=r['actual']
 return[dict(lower=i/10,upper=(i+1)/10,inclusive_upper=i==9,n=b['n'],mean_probability=b['sum_probability']/b['n']if b['n']else None,event_rate=b['events']/b['n']if b['n']else None)for i,b in enumerate(bins)]

def _execute(*,source_root,public,private,retention_gate,repository,prefit_review,sole_fit_worker=False):
 public,private=Path(public),Path(private);p=json.loads((public/'FROZEN_PROTOCOL.json').read_text());v=json.loads(Path(prefit_review).read_text())
 require_retention(retention_gate,repository)
 if not sole_fit_worker:raise ValueError('EXPLICIT_ROOT_SOLE_WORKER_COORDINATION_REQUIRED')
 if p['code_sha256']!=sha(__file__)or p['retention_gate_sha256']!=sha(retention_gate)or v.get('state')!=PREFIT_STATE or v.get('protocol_sha256')!=sha(public/'FROZEN_PROTOCOL.json')or v.get('code_sha256')!=sha(__file__):raise ValueError('EXACT_PREFIT_PROTOCOL_CODE_RETENTION_BINDING')
 for name,h in p['helper_sha256'].items():
  if sha(Path(__file__).with_name(name))!=h:raise ValueError('HELPER_BINDING')
 for item in p['source_ids']:
  if sha(Path(source_root)/item['name'])!=item['sha256']:raise ValueError('SOURCE_HASH')
 if sha(private/'FROZEN_QUERY_METADATA.json')!=p['frozen_historical_query_sha256']:raise ValueError('QUERY_HASH')
 write(public/'EXECUTION_REGISTRATION.json',dict(actual_started_at=now(),protocol_sha256=sha(public/'FROZEN_PROTOCOL.json'),independent_prefit_sha256=sha(prefit_review),retention_gate_sha256=sha(retention_gate),sole_fit_worker=True,actual_fit_calls=0,environment=dict(python=platform.python_version(),numpy=np.__version__,sklearn=sklearn.__version__)))
 b=Budget(p['budget'],private);rows,games,sourcecounts=load_current(source_root,p);queries=join_labels(json.loads((private/'FROZEN_QUERY_METADATA.json').read_text()),rows,p)
 if len(queries)!=15574 or len({q['game_id']for q in queries})!=107:raise ValueError('FIXED_QUERY_POPULATION')
 for d in('models','query-features','training-memberships','prediction-chunks'):(private/d).mkdir()
 labels=b.save(private/'QUALIFIED_QUERY_LABELS.json.gz',queries);history=source.FeatureHistory(rows);datasets={};allrows=[];fits=[];failures=[];grid=planned_grid();gridmap={r['slot']:r for r in grid};fitcalls=retained=0;terminal='COMPLETE';last_slot=None
 for target in source.TARGETS:
  b.guard();eligible=[r for r in rows if r['position']in source.allowed_roles(p,target)and r['values'][target]is not None];x=[];mx=[]
  for r in eligible:
   f,m=history.get(r['player_id'],r['position'],target,r['kickoff'])
   if m is not None and m>=r['kickoff']:raise ValueError('TRAIN_FEATURE_LEAKAGE')
   x.append(f);mx.append(m)
  datasets[target]=(eligible,np.asarray(x),np.asarray([r['values'][target]for r in eligible]),mx)
 with threadpool_limits(limits=2):
  try:
   for week in range(1,8):
    origin=min(g['kickoff']for g in games.values()if g['season']==2026 and g['week']==week)
    for target in source.TARGETS:
     b.guard();qr=[q for q in queries if q['week']==week and q['target']==target];qx=[];qm=[]
     for q in qr:
      f,m=history.get(q['player_id'],q['position'],target,q['cutoff']);qx.append(f);qm.append(m)
      if m is not None and m>=q['cutoff']:raise ValueError('QUERY_FEATURE_LEAKAGE')
     qx=np.asarray(qx);featurepacket=b.save(private/'query-features'/f'W{week:02}-{target}.json.gz',[dict(query_id=q['query_id'],features=source.json_features(f),latest_feature_available=m)for q,f,m in zip(qr,qx,qm)]);rs,tx,ty,tm=datasets[target];ix=np.asarray([i for i,r in enumerate(rs)if r['available']<origin],dtype=int);y=ty[ix];members=[(rs[i]['game_id'],rs[i]['player_id'])for i in ix];memberpacket=b.save(private/'training-memberships'/f'W{week:02}-{target}.json.gz',members);labelmax=max((rs[i]['available']for i in ix),default=None);featuremax=max((tm[i]for i in ix if tm[i]is not None),default=None)
     if labelmax is not None and labelmax>=origin:raise ValueError('TRAIN_LABEL_LEAKAGE')
     for objective in source.objectives(target):
      b.guard();slot=f'W{week:02}-{target}-{objective}';last_slot=slot;cell=gridmap[slot];model=None;modelpacket=None;fitstate='NO_FIT_INSUFFICIENT_TRAINING';began=ended=None;audit=dict(slot=slot,target=target,objective=objective,week=week,history_regime='H-CURRENT',policy_id='H-CURRENT-STRICT',training_n=len(ix),training_seasons=sorted({rs[i]['season']for i in ix}),feature_floor=2026,fit_cutoff=origin,training_membership_sha256=hashlib.sha256(canonical(members)).hexdigest(),training_membership=memberpacket,latest_training_label_available=labelmax,latest_training_feature_available=featuremax,query_features=featurepacket)
      try:
       if design.fit_eligible(y,target):
        if fitcalls>=147:raise ResourceBudget('FIT_CALL_BUDGET')
        fitcalls+=1;began=now();cell['state']='FIT_STARTED'
        try:model=source.make_estimator(target,objective);model.fit(tx[ix],y);ended=now();b.guard();modelpacket=b.save(private/'models'/(slot+'.pickle.gz'),pickle.dumps(model,protocol=5),True);retained+=1;fitstate='FITTED_RETAINED'
        except ResourceBudget:cell['state']='FIT_STOPPED_RESOURCE';raise
        except Exception as exc:model=None;ended=now();fitstate='FIT_FAILED_FALLBACK';failures.append(dict(slot=slot,stage='fit',type=type(exc).__name__,reason=str(exc)[:200]))
       elif target=='anytime_td'and len(y)>=40:fitstate='NO_FIT_SINGLE_CLASS_BINARY'
       predicted=None
       if model is not None:
        try:predicted=model.predict_proba(qx)[:,list(model.classes_).index(1.)]if target=='anytime_td'else model.predict(qx);b.guard()
        except ResourceBudget:cell['state']='INFERENCE_STOPPED_RESOURCE';raise
        except Exception as exc:predicted=None;fitstate='FITTED_RETAINED_INFERENCE_FAILED_FALLBACK';failures.append(dict(slot=slot,stage='inference',type=type(exc).__name__,reason=str(exc)[:200]))
       generated=now();records=[]
       for j,q in enumerate(qr):
        fb='none';count=None;fbsource=None
        if predicted is None:summ=design.fallback(rows,target,q['player_id'],q['position'],q['cutoff'],objective);value=summ['value'];fb=summ['fallback'];count=summ['n'];fbsource=fb
        else:value=source.project_point(target,predicted[j])
        if not math.isfinite(float(value))or target=='anytime_td'and not 0<=value<=1:raise ValueError('INVALID_PREDICTION_SUPPORT')
        records.append(dict(q,run_id=p['run_id'],procedure_id='hgb-direct-history-controls-v1:'+objective+':strict-current-inputs',procedure_family_id='HGB_DIRECT_HISTORY_CONTROL',product_id=objective,objective=objective,history_regime='H-CURRENT',policy_id='H-CURRENT-STRICT',information_policy='CURRENT_2026_DATA_ONLY_SETTINGS_EXPOSED',prediction=float(value),fallback=fb,fallback_source=fbsource,fallback_source_n=count,status='RECONSTRUCTED_RESEARCH_FORECAST',fit_slot=slot,fit_state=fitstate,model_artifact_id=None if modelpacket is None else modelpacket['artifact_id'],feature_cutoff=q['cutoff'],fit_cutoff=origin,latest_training_label_available=labelmax,latest_training_feature_available=featuremax,latest_feature_available=qm[j],actual_generated_at=generated,evidence_tier='current_vintage_historical_reconstruction'))
       if len(allrows)+len(records)>p['budget']['max_forecast_rows']:raise ResourceBudget('FORECAST_ROW_BUDGET')
       packet=b.save(private/'prediction-chunks'/(slot+'.json.gz'),dict(schema=VERSION,rows=records));persisted=now();allrows.extend(records);cell.update(state=fitstate,forecast_state='PERSISTED',forecast_rows=len(records));write(public/(slot+'-FORECAST.json'),dict(slot=slot,packet=packet,actual_persistence_completed_at=persisted,forecast_rows=len(records),original_pregame_issuance=False));b.guard()
      except ResourceBudget:
       audit.update(state=cell['state'],model=modelpacket,actual_fit_started_at=began,actual_fit_completed_at=ended);write(public/(slot+'-FIT.json'),audit);fits.append(audit);raise
      except Exception:
       cell['state']='FORECAST_CELL_FAILED_STOPPED';audit.update(state=cell['state'],model=modelpacket,actual_fit_started_at=began,actual_fit_completed_at=ended);write(public/(slot+'-FIT.json'),audit);fits.append(audit);raise
      audit.update(state=fitstate,model=modelpacket,actual_fit_started_at=began,actual_fit_completed_at=ended);write(public/(slot+'-FIT.json'),audit);fits.append(audit)
  except Exception as exc:terminal='PARTIAL_STOPPED';failures.append(dict(slot=last_slot,type=type(exc).__name__,reason=str(exc)[:200]))
 meters=collections.defaultdict(score.Meter);binary=collections.defaultdict(list)
 for r in allrows:
  dims=r['procedure_id'],r['target'],r['population'],r['product_id']
  for week,pos,view in [('ALL','ALL','ALL'),(str(r['week']),'ALL','ALL'),('ALL',r['position'],'ALL'),('ALL','ALL','LEARNED_ONLY'if r['fallback']=='none'else'FALLBACK_ONLY')]:
   k=dims+(week,pos,view);meters[k].add(r)
   if r['target']=='anytime_td':binary[k].append(r)
 scores=[]
 for k,m in sorted(meters.items()):
  proc,target,pop,product,week,pos,view=k;result=m.result();row=dict(procedure_id=proc,procedure_family_id='HGB_DIRECT_HISTORY_CONTROL',target=target,population=pop,product_id=product,objective=product,season=2026,evaluation_seasons=[2026],week=int(week)if week.isdigit()else week,position=pos,fallback_view=view,history_regime='H-CURRENT',policy_id='H-CURRENT-STRICT',information_policy='CURRENT_2026_DATA_ONLY_SETTINGS_EXPOSED',feature_memory_policy='Only2026labels/features/priors/transforms; architecture/settingsresearch-exposed',evaluation_panel_id=p['run_id'],period='REG',record_kind='NEW_EXPERIMENT_CURRENT_VINTAGE_PARTICIPANT_DIAGNOSTIC',evidence='NEW_EXPERIMENT',point_functional='fittedL1point'if product=='absolute_error_point'else'intendedmean'if product=='squared_error_mean'else'Bernoullieventprobability',source_vintage='current-vintage;seven-dayhistoricalavailabilityassumption',**result)
  if target=='anytime_td':row.update(binary_law='Bernoulli probability law for at least one rushing-or-receiving TD',reliability=reliability(binary[k]),numeric_distribution_claim=False)
  scores.append(row)
 write(public/'SCORES.json',scores);empirical.write_csv(public/'SCORES.csv',scores);write(public/'GRID_STATUS.json',grid);write(public/'FAILURES.json',failures)
 flat=None
 try:b.guard();flat=b.csv(private/'predictions.csv.gz',allrows);b.guard()
 except ResourceBudget as exc:terminal='PARTIAL_STOPPED';failures.append(dict(stage='flat',type=type(exc).__name__,reason=str(exc)));write(public/'FLAT_PERSISTENCE_FAILURE.json',failures[-1])
 receipt=dict(version=VERSION,run_id=p['run_id'],state=terminal,actual_completed_at=now(),protocol_sha256=sha(public/'FROZEN_PROTOCOL.json'),actual_fit_calls=fitcalls,retained_models=retained,failed_fits=sum(r.get('stage')=='fit'for r in failures),completed_cells=sum(c['forecast_state']=='PERSISTED'for c in grid),nominal_cells=147,forecast_output_views=len(allrows),score_views=len(scores),query_cells=len(queries),unique_player_games=len({(q['game_id'],q['player_id'])for q in queries}),unique_games=len({q['game_id']for q in queries}),labels=labels,private_flat=flat,private_output_bytes=sum(f.stat().st_size for f in private.rglob('*')if f.is_file()),private_bytes_charged=b.bytes,source_counts=sourcecounts,resource=b.resources(),new_family_count=0,new_future_forecasts=0,CURRENT_2026_Week8_outcomes_read=0,restoration='Localnewoutputsneedseparatefreshprivatebackup; parentretentiongatecoversprerequisites')
 write(public/'RUN_RECEIPT.json',receipt);return receipt


def execute(**kwargs):
 """Finalize a full147-cell failed grid even when source initialization stops."""
 public=Path(kwargs['public']);private=Path(kwargs['private'])
 try:return _execute(**kwargs)
 except Exception as exc:
  if not(public/'EXECUTION_REGISTRATION.json').exists()or(public/'RUN_RECEIPT.json').exists():raise
  p=json.loads((public/'FROZEN_PROTOCOL.json').read_text());grid=planned_grid();fit_receipts={}
  for file in public.glob('*-FIT.json'):
   item=json.loads(file.read_text());fit_receipts[item['slot']]=item
  forecasts={}
  for file in public.glob('*-FORECAST.json'):
   item=json.loads(file.read_text());forecasts[item['slot']]=item
  for c in grid:
   fit=fit_receipts.get(c['slot']);forecast=forecasts.get(c['slot'])
   c['state']=fit['state']if fit else'NOT_RUN_AFTER_INITIALIZATION_FAILURE'
   c['forecast_state']='PERSISTED'if forecast else'NOT_RUN'
  reason=str(exc)[:200]
  if '/'in reason:reason='Filesystem failure; private path retained only in local diagnostic context'
  failure=dict(stage='initialization_or_finalization',type=type(exc).__name__,reason=reason)
  for name,value in [('GRID_STATUS.json',grid),('FAILURES.json',[failure]),('SCORES.json',[])]:
   if not(public/name).exists():write(public/name,value)
  receipt=dict(version=VERSION,run_id=p['run_id'],state='PARTIAL_STOPPED',failure_stage='INITIALIZATION_OR_FINALIZATION',actual_completed_at=now(),protocol_sha256=sha(public/'FROZEN_PROTOCOL.json'),actual_fit_calls=sum(f.get('actual_fit_started_at')is not None for f in fit_receipts.values()),retained_models=sum(bool(f.get('model'))for f in fit_receipts.values()),failed_fits=sum(f.get('state')=='FIT_FAILED_FALLBACK'for f in fit_receipts.values()),completed_cells=len(forecasts),nominal_cells=147,forecast_output_views=sum(f['forecast_rows']for f in forecasts.values()),score_views=len(json.loads((public/'SCORES.json').read_text())),query_cells_registered=p['query_cells'],query_cells_joined=None,private_output_bytes=sum(f.stat().st_size for f in private.rglob('*')if f.is_file()),new_future_forecasts=0,CURRENT_2026_Week8_outcomes_read=0,failure=failure)
  write(public/'RUN_RECEIPT.json',receipt);return receipt
