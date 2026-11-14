#!/usr/bin/env python3
"""Summarize saved availability forecasts; never acquire labels or fit models."""
import argparse,collections,csv,gzip,hashlib,json,math,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2 import availability_wave as wave

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--public',type=Path,required=True);p.add_argument('--private',type=Path,required=True);a=p.parse_args();pub,private=a.public,a.private
    protocol=json.loads((pub/'FROZEN_PROTOCOL.json').read_text());allrows=[];packets=[]
    for stage in ('AB','C'):
        receipt=json.loads((pub/(stage+'-RUN_RECEIPT.json')).read_text());path=private/receipt['packet']['bundle_name']
        if wave.sha(path)!=receipt['packet']['sha256']:raise ValueError('packet binding')
        rows=json.loads(gzip.decompress(path.read_bytes()))['rows'];allrows+=rows;packets.append(dict(stage=stage,sha256=wave.sha(path),rows=len(rows)))
    if any(r['actual'] is not None for r in allrows):raise ValueError('unexpected outcome')
    def key(r):return tuple(r[k] for k in ('query_id','family','history_regime','product_id','procedure_id'))
    arms={arm:{key(r):r for r in allrows if r['availability_arm']==arm} for arm in ('A','B','C')}
    if not(set(arms['A'])==set(arms['B'])==set(arms['C'])):raise ValueError('different ABC memberships')
    grouped=collections.defaultdict(list);samefallback=0;samefixedbinding=0
    for k,ra in arms['A'].items():
        rb,rc=arms['B'][k],arms['C'][k]
        if ra['fallback']!=rb['fallback']:raise ValueError('AB fallback changed')
        samefallback+=1
        if ra.get('fixed_model_artifact_id')!=rb.get('fixed_model_artifact_id'):raise ValueError('fixed model mismatch')
        samefixedbinding+=1
        for contrast,left,right in [('B-A',ra,rb),('C-B',rb,rc)]:
            g=tuple(left[k] for k in ('target','family','history_regime','product_id'))+(contrast,)
            grouped[g].append((left,right))
    result=[]
    for (target,family,history,product,contrast),pairs in sorted(grouped.items()):
        good=[(x,y) for x,y in pairs if x['prediction'] is not None and y['prediction'] is not None];d=[y['prediction']-x['prediction'] for x,y in good]
        result.append(dict(target=target,family=family,history_regime=history,product_id=product,contrast=contrast,query_cells=len(pairs),paired_issued=len(good),abstained=len(pairs)-len(good),prediction_changed_n=sum(x!=0 for x in d),mean_signed_prediction_change=sum(d)/len(d) if d else None,mean_absolute_prediction_change=sum(abs(x) for x in d)/len(d) if d else None,max_absolute_prediction_change=max(map(abs,d),default=None),later_fallback_changed_n=sum(x['fallback']!=y['fallback'] for x,y in good),score_state='PENDING_WEEK8_OUTCOMES',forecast_skill_established=False))
    wave.emp.write_csv(pub/'FORECAST_CHANGE_SUMMARY.csv',result);wave.save_json(pub/'FORECAST_CHANGE_SUMMARY.json',result)
    changes=json.loads(gzip.decompress((private/'features'/'QUERY_FEATURE_CHANGES.json.gz').read_bytes()));features=[]
    for target in wave.TARGETS:
        r=[q for q in changes if q['target']==target];counts=collections.Counter(c for q in r for c in q['changed_columns']);features.append(dict(target=target,query_cells=len(r),queries_with_feature_change=sum(bool(q['changed_columns']) for q in r),changed_columns=dict(counts)))
    wave.save_json(pub/'FEATURE_CHANGE_SUMMARY.json',features)
    fits=[json.loads(p.read_text()) for p in sorted(pub.glob('C-FIT-*.json'))];wave.emp.write_csv(pub/'REFIT_TRAINING_SUMMARY.csv',fits)
    fields=['query_id','game_id','player_id','sleeper_id','target','population','position','season','week','availability_arm','family','procedure_id','history_regime','product_id','prediction','actual','actual_status','fallback','status','abstention_reason','feature_cutoff_utc','actual_generated_at','latest_feature_available','fit_binding','fit_state','fixed_model_artifact_id','new_fit']
    path=private/'all-availability-predictions.csv.gz'
    with path.open('xb') as raw:
        with gzip.GzipFile(fileobj=raw,mode='wb',mtime=0) as handle:
            import io
            text=io.TextIOWrapper(handle,encoding='utf-8',newline='');writer=csv.DictWriter(text,fieldnames=fields,extrasaction='ignore');writer.writeheader();writer.writerows(allrows);text.flush();text.detach()
    wave.save_json(pub/'REPORT_RECEIPT.json',dict(state='SAVED_ROW_REPORT_COMPLETE_NO_SKILL_CLAIM',actual_completed_at=wave.now(),code_sha256=wave.sha(__file__),source_packets=packets,ABC_comparable_keys=len(arms['A']),same_AB_fallback_checks=samefallback,same_AB_fixed_model_checks=samefixedbinding,forecast_contrast_views=len(result),feature_query_checks=len(changes),private_flat=dict(artifact_id='AVAIL-FLAT-'+wave.sha(path),bundle_name=path.name,sha256=wave.sha(path),bytes=path.stat().st_size,rows=len(allrows)),Week8_actuals_read=0,new_fits=0,score_views=0))
    wave.save_json(pub/'METADATA_SEMANTICS.json',dict(new_fit_field='C-stage identity only, not a successful-fit counter; use fit_state plus actual_fit_calls/retained_models in C receipt',scientific_limit='Prediction-change ablation pending future outcomes; no evidence yet that fresh features or refits improve skill',fixed_model_provenance='Original HGB fit23:16Oct29; original Leaf fit origin00:27Oct30; A/B uses exactsame byteswithinprocedure, different families have different retained training cutoffs',official_capture=False,owner_admission='PENDING',old_evidence_unchanged=True))
    lines=['# Availability A/B/C research shadows','',f"New as-of: **{protocol['fixed_feature_origin_utc']}**. The same {protocol['query_cells']:,} frozen query cells cover thirteen future games. Forecast changes are measured; Week 8 skill remains pending. No Week 8 outcomes were read.",'','A refreshes the conservative seven-day features using retained models. B admits already-retained Week 7 statistics into query features while holding every model byte, prior and fallback route/value fixed. C uses the same fresh queries and separately refits with currently known Week 7 labels; historical training features keep their conservative seven-day clocks. This does not reconstruct earlier publication times.','', 'The current snapshot had303position-qualified Week7rows. The old23:16cutoff excluded303; the prior00:27cutoff excluded282. At this new as-of A still excludes282; B/C admit all303. Chart labels retain the qualified partial16-component contract and unknown rare credits.','', '| Target | Frozen queries | Queries with changed features |','|---|---:|---:|']
    lines += [f"|{r['target']}|{r['query_cells']}|{r['queries_with_feature_change']}|" for r in features]
    lines += ['', 'The saved change summary reports every family, history regime and product for B−A and C−B, including unchanged outputs and abstentions. It reports native-unit prediction differences, not forecast errors. Empirical C updates an arithmetic sample pool with zero optimizer fits. Chart HGB is explicitly unsupported because no retained chart HGB model exists; empirical and Leaf cover chart. Mean/median views and history regimes do not create new method families.','', 'All packets are staged research shadows with actual generation and persistence times and deadline checks. Retained-owner official admission is pending. Original captures, models, scores and availability policies remain unchanged. Future paired grading uses the frozen protocol on identical qualified labels; no method/side selection or ROI rule is introduced.']
    with (pub/'README.md').open('x') as f:f.write('\n'.join(lines)+'\n')
    print(json.dumps(dict(rows=len(allrows),paired_keys=len(arms['A']),forecast_contrasts=len(result),features=features)))
if __name__=='__main__':main()
