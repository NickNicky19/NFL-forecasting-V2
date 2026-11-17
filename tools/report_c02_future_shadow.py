#!/usr/bin/env python3
"""Report saved future-only C02 shadows without fitting or reading outcomes."""
import argparse,collections,csv,gzip,io,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2 import c02_future_shadow as w
p=argparse.ArgumentParser();p.add_argument('--public',type=Path,required=True);p.add_argument('--private',type=Path,required=True);a=p.parse_args();public,private=a.public,a.private
receipt=json.loads((public/'RUN_RECEIPT.json').read_text());protocol=json.loads((public/'FROZEN_PROTOCOL.json').read_text());path=private/receipt['packet']['bundle_name']
if w.sha(path)!=receipt['packet']['sha256']:raise ValueError('packet changed')
rows=json.loads(gzip.decompress(path.read_bytes()))['rows']
if any(r['actual'] is not None for r in rows):raise ValueError('unexpected future outcomes')
def key(r):return tuple(r[k] for k in ('query_id','target','policy_id','product_id'))
control={key(r):r for r in rows if r['variant']=='retained_ordered_control'};candidate={key(r):r for r in rows if r['variant']=='c02_explicit_lag_block_removed'}
if set(control)!=set(candidate):raise ValueError('unmatched keys')
groups=collections.defaultdict(list)
for k,r in control.items():
 s=candidate[k]
 if r['fallback']!=s['fallback']:raise ValueError('fallback route changed')
 if r['feature_cutoff_utc']!=s['feature_cutoff_utc'] or r['training_fit_cutoff_utc']!=s['training_fit_cutoff_utc']:raise ValueError('cutoff mismatch')
 groups[(r['target'],r['policy_id'],r['history_regime'],r['product_id'])].append((r,s))
summary=[]
for (target,policy,history,product),pairs in sorted(groups.items()):
 good=[(r,s) for r,s in pairs if r['prediction'] is not None and s['prediction'] is not None];d=[s['prediction']-r['prediction'] for r,s in good]
 summary.append(dict(target=target,policy_id=policy,history_regime=history,product_id=product,query_cells=len(pairs),paired_issued=len(good),abstained=len(pairs)-len(good),changed_predictions=sum(v!=0 for v in d),mean_signed_prediction_change=sum(d)/len(d) if d else None,mean_absolute_prediction_change=sum(abs(v) for v in d)/len(d) if d else None,max_absolute_prediction_change=max(map(abs,d),default=None),score_state='PENDING_WEEK8_OUTCOMES',new_family_count=0))
w.write(public/'FORECAST_CHANGE_SUMMARY.json',summary);w.src.empirical.write_csv(public/'FORECAST_CHANGE_SUMMARY.csv',summary)
fields=['query_id','game_id','player_id','sleeper_id','target','population','position','season','week','variant','family','procedure_id','history_regime','policy_id','information_policy','product_id','prediction','actual','actual_status','status','abstention_reason','fallback','feature_cutoff_utc','latest_feature_available','training_fit_cutoff_utc','actual_generated_at','issued_at_utc','actual_horizon_seconds','fit_state','model_artifact_id']
flat=private/'all-c02-future-predictions.csv.gz'
with flat.open('xb') as raw:
 with gzip.GzipFile(fileobj=raw,mode='wb',mtime=0) as handle:
  text=io.TextIOWrapper(handle,encoding='utf-8',newline='');writer=csv.DictWriter(text,fieldnames=fields,extrasaction='ignore');writer.writeheader();writer.writerows(rows);text.flush();text.detach()
files=[dict(artifact_id='C02-FUTURE-RETAINED-'+w.sha(f),bundle_name=f.relative_to(private).as_posix(),sha256=w.sha(f),bytes=f.stat().st_size) for f in sorted(private.rglob('*')) if f.is_file()]
w.write(public/'PUBLIC_ARTIFACT_MANIFEST.json',dict(state='LOCAL_READBACK_OFFHOST_RESTORATION_PENDING',actual_created_at=w.now(),files=len(files),total_bytes=sum(f['bytes'] for f in files),artifacts=files,logical_name_contract='Portable archive member names are public-safe artifact IDs, not private storage locators'))
w.write(public/'REPORT_RECEIPT.json',dict(state='SAVED_ROW_REPORT_COMPLETE',actual_completed_at=w.now(),code_sha256=w.sha(__file__),source_packet_sha256=w.sha(path),paired_keys=len(control),paired_issued=sum(r['paired_issued'] for r in summary),fallback_match_checks=len(control),cutoff_match_checks=len(control),changed_predictions=sum(r['changed_predictions'] for r in summary),forecast_contrast_views=len(summary),new_fit_calls=0,Week8_outcomes_read=0,score_views=0,private_flat=dict(bundle_name=flat.name,sha256=w.sha(flat),bytes=flat.stat().st_size,rows=len(rows))))
w.write(public/'SCORE_STATE.json',dict(state='FORECASTED_UNSCORED',score_views=0,Week8_outcomes_read=0,canonical_scores_file='NOT_EMITTED_NO_EVALUATIONS',later_grading='Frozen in FROZEN_PROTOCOL.json before inference; no forecast-change number is an error or skill score'))
lines=['# Future C02 versus ordered Leaf-CDF research shadows','',f"New common query cutoff: **{protocol['fixed_query_asof_utc']}**. Both variants use the same 2,229 frozen queries across thirteen games and the conservative seven-day availability policy. No Week 8 outcome was read.",'',f"The run completed **{receipt['actual_fit_calls']} new C02 fits**, retaining {receipt['retained_new_models']} models. The {receipt['retained_control_models']} ordered control models were reused unchanged. Every C02 fit matched its control’s training membership, original training cutoff, labels, same-arm priors and feature-memory policy before removing the explicit lag block.",'','C02 removes the four individual value/age/missing lag triplets and their imputation flags. It retains recent means, counts and positions. Thus this tests the extra lag block; it does not remove every use of order or recency. The three common-memory history regimes and separate strict-current policy retain their original definitions.','',f"There are {receipt['output_views']:,} output views: {receipt['issued']:,} issued research shadows and {receipt['abstained']} abstentions. The two variants have {sum(r['paired_issued'] for r in summary):,} matched issued procedure/product/policy rows; {sum(r['changed_predictions'] for r in summary):,} predictions differ. Mean, lower-median and TD probability views do not add independent NFL observations or method families.",'',f"The aggregate packet persisted at **{receipt['actual_aggregate_persistence_completed_at']}**; immutable slot receipts retain their actual earlier persistence times. Deadline checks apply to every issued row. These are early-before-deadline snapshots, not exact T-minus-90 observations.",'','The saved CSV/JSON reports all target, history-policy and product differences in native units. Forecast error and comparative skill remain pending. Later grading follows the frozen protocol, including PMF log scores, proper distribution scores and exact chart-median precision coordinates. Chart retains its qualified partial 16-component contract; missing rare credits stay missing.','',f"Active execution used {receipt['resource']['wall_seconds']:.2f} wall seconds and {receipt['resource']['cpu_seconds']:.2f} CPU seconds, with at most two threads. Official owner admission is pending. No production, old capture, old score, scheduler or historical C02 artifact was changed."]
with (public/'README.md').open('x') as f:f.write('\n'.join(lines)+'\n')
print(json.dumps(dict(rows=len(rows),paired=len(control),paired_issued=sum(r['paired_issued'] for r in summary),changed=sum(r['changed_predictions'] for r in summary),private_files=len(files),private_bytes=sum(f['bytes'] for f in files))))
