#!/usr/bin/env python3
"""Replay retained distribution chunks into flat private rows and paired reports.

No fitted-model loading, inference, source acquisition or new numerical fit.
"""
from __future__ import annotations
import argparse,collections,csv,gzip,hashlib,json,math,os,statistics
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--public',type=Path,required=True);p.add_argument('--private',type=Path,required=True);p.add_argument('--reuse-public',type=Path,required=True);p.add_argument('--reuse-private',type=Path,required=True);a=p.parse_args()
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def dump(path,obj):
 with path.open('x') as f:json.dump(obj,f,indent=2,allow_nan=False);f.write('\n')
def write(path,rows):
 rows=list(rows)
 with path.open('x',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
run=json.loads((a.public/'RUN_RECEIPT.json').read_text());assert run['state']=='COMPLETE'
records=[];artifacts={};source_paths={}
for receiptpath in sorted(a.public.glob('*-FORECAST.json')):
 receipt=json.loads(receiptpath.read_text());packet=receipt['packet'];reused=receipt.get('reused_from')=='v2-distribution-controls-reconstruction-v1';root=a.reuse_private if reused else a.private
 path=root/packet['bundle_name'];assert sha(path)==packet['sha256'];data=json.loads(gzip.decompress(path.read_bytes()));assert len(data['rows'])==receipt['output_views'];records.extend(data['rows'])
 artifact_id='ART-DIST-'+packet['sha256'];artifacts[artifact_id]=dict(artifact_id=artifact_id,bundle_name=packet['bundle_name'],source_run='distribution-wave-v1' if reused else 'distribution-wave-v2',bytes=path.stat().st_size,sha256=packet['sha256'],role='prediction_chunk');source_paths[artifact_id]=str(path)
for fitpath in sorted(a.public.glob('*-FIT.json')):
 fit=json.loads(fitpath.read_text())
 for role in ('model','query_features'):
  packet=fit.get(role)
  if not packet:continue
  reused=packet.get('reused_from')=='v2-distribution-controls-reconstruction-v1';root=a.reuse_private if reused else a.private;path=root/packet['bundle_name'];assert sha(path)==packet['sha256']
  artifact_id='ART-DIST-'+packet['sha256'];artifacts[artifact_id]=dict(artifact_id=artifact_id,bundle_name=packet['bundle_name'],source_run='distribution-wave-v1' if reused else 'distribution-wave-v2',bytes=path.stat().st_size,sha256=packet['sha256'],role=role);source_paths[artifact_id]=str(path)
assert len(records)==run['forecast_output_views'];rows=[]
for r in records:
 key={k:r.get(k) for k in ('game_id','player_id','target','population')};query_id=r.get('query_id') or hashlib.sha256(json.dumps(key,sort_keys=True,separators=(',',':')).encode()).hexdigest()
 base={k:r.get(k) for k in ('game_id','player_id','target','population','position','season','week','history_regime','policy_id','information_policy','family','procedure_id','product_id','prediction','actual','fallback','fallback_source','fallback_source_n','actual_status','status','abstention_reason','fit_slot','fit_state','latest_feature_available','cutoff','actual_generated_at','issued_at_utc','actual_horizon_seconds','owner_cutoff_status')}
 d=r['distribution_summary'] or {};base.update(query_id=query_id,evaluation_panel_id='distribution-controls-source-matched-observed-participant-2026-W1-W7-v1' if int(r['week'])<8 else 'new-genuine-open-T90-week8-shadow-v2',run_id=r['run_id'],distribution_id=hashlib.sha256(json.dumps([r['fit_slot'],query_id],separators=(',',':')).encode()).hexdigest(),distribution_summary=json.dumps(d,sort_keys=True,separators=(',',':')),law_reference=json.dumps(r.get('law_reference'),sort_keys=True,separators=(',',':')))
 for k in ('crps','nll','infinite_nll','q05','q95','interval90_width','interval90_covered','zero_mass'):base[k]=d.get(k)
 rows.append(base)
flat=a.private/'all-predictions.csv.gz'
with flat.open('xb') as raw:
 with gzip.GzipFile(fileobj=raw,filename='',mode='wb',mtime=0) as z:
  import io
  with io.TextIOWrapper(z,encoding='utf-8',newline='') as f:
   w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 raw.flush();os.fsync(raw.fileno())
# Independently paired saved-row loss differences; no hindsight selector.
group=collections.defaultdict(dict)
for r in records:
 if int(r['week'])==8:continue
 key=tuple(r[k] for k in ('family','target','population','product_id','game_id','player_id'))
 assert r['policy_id'] not in group[key];group[key][r['policy_id']]=r
contrasts=collections.defaultdict(list)
for key,policies in group.items():
 assert len(policies)==4
 baseline=policies['H-CURRENT-COMMON']
 if baseline['actual'] is None:continue
 metrics=['Brier'] if baseline['target']=='anytime_td' else ['MAE','MSE'] if baseline['product_id']=='mean' else ['MAE']
 for contender in ('H-RECENT-COMMON','H-MULTI-COMMON','H-CURRENT-STRICT'):
  r=policies[contender];assert r['actual']==baseline['actual']
  for metric in metrics+['CRPS','NLL']:
   if metric=='NLL' and (r['distribution_summary']['infinite_nll'] or baseline['distribution_summary']['infinite_nll']):continue
   def loss(row):
    if metric=='MAE':return abs(row['prediction']-row['actual'])
    if metric in ('MSE','Brier'):return (row['prediction']-row['actual'])**2
    return row['distribution_summary'][metric.lower()]
   delta=loss(r)-loss(baseline);learned=r['fallback']=='none' and baseline['fallback']=='none';k=key[:4]+(contender,metric)
   contrasts[k].append((int(r['week']),r['game_id'],delta,learned))
paired=[]
for key,values in sorted(contrasts.items()):
 weeks=collections.defaultdict(list)
 for wk,game,d,learned in values:weeks[wk].append(d)
 wm=[statistics.fmean(v) for _,v in sorted(weeks.items())];mean=statistics.fmean(wm);half=2.447*statistics.stdev(wm)/math.sqrt(7) if len(wm)==7 else None;overlap=[d for _,_,d,l in values if l]
 paired.append(dict(family=key[0],target=key[1],population=key[2],product_id=key[3],comparison=key[4]+'_minus_H-CURRENT-COMMON',metric=key[5],paired_rows=len(values),games=len({v[1] for v in values}),weeks=len(wm),micro_loss_difference=statistics.fmean(v[2] for v in values),week_balanced_loss_difference=mean,week_t95_low=None if half is None else mean-half,week_t95_high=None if half is None else mean+half,learned_only_overlap_rows=len(overlap),learned_only_overlap_micro_difference=statistics.fmean(overlap) if overlap else None,interpretation='STRICTchangescompleteinformationpolicy;otherwisecommonfeaturememoryfithistorycomparison',uncertainty='exposedresearchpostfit;7weekclustersweak;unadjusted;notqualification',nll_rule='onlyfinitepairedPMFNLL;reportinfinitecountsseparately' if key[5]=='NLL' else None))
write(a.public/'PAIRED_HISTORY_AND_INFORMATION_POLICY.csv',paired)
# Keep actual fixed-no-NFL startup counts separate from inherited legacy token name.
fallback=collections.Counter((r['family'],r['policy_id'],r['target'],r['product_id'],r['fallback'],int(r['week'])==8) for r in records if r['prediction'] is not None)
fallback_rows=[dict(family=k[0],policy_id=k[1],target=k[2],product_id=k[3],fallback=k[4],is_week8=k[5],output_views=v) for k,v in sorted(fallback.items())]
write(a.public/'FALLBACK_SOURCE_COUNTS.csv',fallback_rows)
dump(a.public/'FALLBACK_TOKEN_SEMANTICS.json',dict(state='ADDITIVE_DISCLOSURE_NOT_SCORING_REWRITE',legacy_constant_zero_n_definition='counts literal fallback token constant_zero inherited from empirical.Metrics; new fixed_no_NFL_startup token is separate and not included there',actual_fixed_startup_counts='FALLBACK_SOURCE_COUNTS.csv entries fixed_no_NFL_startup; SCORES.json fallback_source_counts retains correct exact tokens',all_fallback_counts='fallback_n/fallback_rows includes every non-none token correctly',numerical_errors_affected=False))
dump(a.public/'PUBLIC_ARTIFACT_MANIFEST.json',dict(state='PUBLIC_SAFE_LOGICAL_ARCHIVE_NAMES_NOT_STORAGE_LOCATORS',artifacts=list(artifacts.values())))
dump(a.private/'REPLAY_ARTIFACTS_PRIVATE.json',dict(artifact_ids_to_local_files=source_paths,flat_predictions=str(flat),flat_sha256=sha(flat)))
dump(a.public/'POSTRUN_REPLAY_RECEIPT.json',dict(state='SAVED_ROW_EXPORT_AND_PAIRED_REPORT_COMPLETE',forecast_output_views=len(records),historical_output_views=sum(int(r['week'])<8 for r in records),future_output_views=sum(int(r['week'])==8 for r in records),flat_prediction_sha256=sha(flat),flat_prediction_bytes=flat.stat().st_size,paired_contrasts=len(paired),source_artifacts=len(artifacts),source_unique_bytes=sum(r['bytes'] for r in artifacts.values()),historical_policy_query_keys=len(group),new_fits=0,new_forecasts=0,new_outcomes=0,script_sha256=sha(Path(__file__))))
print(json.dumps({'forecast_rows':len(records),'paired_contrasts':len(paired),'flat_sha256':sha(flat),'flat_bytes':flat.stat().st_size,'artifact_count':len(artifacts)},indent=2))
