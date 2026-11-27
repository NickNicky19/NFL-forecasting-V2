"""Independent metadata-only source-clock/ancillary attribution index audit."""
import argparse,collections,gzip,hashlib,json
from datetime import datetime,timezone
from pathlib import Path
def load(p):
    b=p.read_bytes();return json.loads(gzip.decompress(b)if p.suffix=='.gz'else b)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(repo,out,qualification,index):
    q=load(qualification);bindings=load(out/'SOURCE_AND_CLOCK_BINDINGS.json');sourcebindinghash=sha(out/'SOURCE_AND_CLOCK_BINDINGS.json');original={};notes={};annotation_counts={};borrowed=0
    previous_receipts=[load(out/'INDEPENDENT_SUPPLEMENT_CONTROLS_COHORTS_AND_TYPING_V1.json'),load(out/'INDEPENDENT_POLICY_COHORT_PARTITIONS_V1.json')]
    priorhashes={}
    for r in previous_receipts:
        if 'artifact_sha256'in r:priorhashes.update({str(out.relative_to(repo)/(k+'.json')):v for k,v in r['artifact_sha256'].items()})
    priorhashes[str(out.relative_to(repo)/'SCORES.json')]=previous_receipts[0]['source_scores_sha256'];priorhashes[str(out.relative_to(repo)/'POLICY_COHORT_SCORES.json')]=previous_receipts[1]['score_sha256']
    targethorizon={'pass_td':'B_ORIGINAL_EARLY_CAPTURE_PLUS_RETAINED_LATER_T90_THRESHOLDS','rec':'C_KICKOFF_RECONSTRUCTION'}
    for b in q['bindings']:
        src=repo/b['source'];np=repo/b['annotations'];assert sha(src)==b['source_sha256']==priorhashes[b['source']]and sha(np)==b['annotations_sha256'];ss=load(src);nn=load(np);assert nn['source_score_sha256']==sha(src)and nn['source_binding_sha256']==sourcebindinghash and len(ss)==len(nn['rows'])==b['rows'];note={n['source_row_index']:n for n in nn['rows']};assert set(note)==set(range(len(ss)));annotation_counts[src.name]=len(ss)
        for i,s in enumerate(ss):
            n=note[i];t=s['target'];assert n['record_id']==s['record_id']and n['correction_kind']=='SOURCE_VINTAGE_METADATA_ONLY'and n['original_source_vintage']==s.get('source_vintage');h=n['source_horizon_qualification'];assert h['kind']=='TARGET_SPECIFIC_BOUND_SOURCE_CLOCKS'and h['original_horizon_id']==s.get('horizon_id')and h['horizon_id']==('B_ORIGINAL_EARLY_CAPTURE_NUMERICAL_MEAN'if s['record_kind']=='forecast_evaluation_view'else targethorizon[t])and h['source_binding']=='SOURCE_AND_CLOCK_BINDINGS.json'
            if t=='pass_td':assert 'B_PROVIDER_LABELLED_THRESHOLD_CLOCK_UNVERIFIED'in n['source_vintage']and 'FOOTBALL_SOURCE_VINTAGES_UNAUTHENTICATED'in n['source_vintage']and 'PINNACLE'not in n['source_vintage']
            else:assert 'PINNACLE_LAST_RECORDED_QUOTE_CLOCK_UNVERIFIED'in n['source_vintage']and 'CURRENT_REVISED'in n['source_vintage']
            if s['record_kind']=='prop_selection_evaluation'and(s.get('mae')is not None or s.get('bias')is not None):
                borrowed+=1;assert n['ancillary_point_attribution']['kind']=='ORIGINAL_B0_MEAN_REFERENCE_NOT_THIS_EVENT_PRODUCT';assert n['ancillary_point_attribution']['original_metrics']=={k:s.get(k)for k in('mae','mse','rmse','bias','p90_abs','p95_abs','max_abs')}
            if s.get('strategy','').startswith('ROLLING_K'):
                k,side=s['strategy'].split('_')[1:];assert n['registered_rolling_rank']==dict(K=int(k[1:]),side_pool=side,rank_scope='PER_CATEGORY_PER_WEEK_ROLLING_DECISION_BATCHES')
            key=(b['source'],s['record_id']);assert key not in original;original[key]=s;notes[key]=n
    assert len(original)==7893
    manifest=load(index);prev=load(repo/manifest['previous_sharded_checkpoint']['artifact']);assert manifest['previous_sharded_checkpoint']['sha256']==sha(repo/manifest['previous_sharded_checkpoint']['artifact'])and prev['record_count']==594308 and manifest['record_count']==602201
    assert manifest['shards'][:len(prev['shards'])]==prev['shards'];assert manifest['streaming_build']['previous_records_reused']==594308 and manifest['streaming_build']['new_records']==7893
    seen=set();numericremoved=0;selectionchecks=0;properchecks=0;cohortnumericremoved=0;missinghorizon=collections.Counter()
    for part in manifest['shards'][len(prev['shards']):]:
        p=repo/part['path'];assert p.stat().st_size==part['bytes']and sha(p)==part['sha256'];raw=gzip.decompress(p.read_bytes())if part.get('compression')=='gzip'else p.read_bytes();assert len(raw)==part.get('uncompressed_bytes',len(raw))and hashlib.sha256(raw).hexdigest()==part.get('uncompressed_sha256',hashlib.sha256(raw).hexdigest());rr=json.loads(raw);assert len(rr)==part['records']
        for r in rr:
            key=r['source_artifact'],r['source_record_id'];assert key in original and key not in seen;seen.add(key);s=original[key];n=notes[key];assert r['source_artifact_sha256']==priorhashes[key[0]]and r['source_aggregate_fields']==s;assert r['source_vintage']==n['source_vintage'];missinghorizon[r['kind']]+=int(r.get('horizon',r.get('horizon_id'))is None);assert r.get('horizon',r.get('horizon_id'))==('B_ORIGINAL_EARLY_CAPTURE_NUMERICAL_MEAN'if s['record_kind']=='forecast_evaluation_view'else targethorizon[s['target']])
            assert(r['n'],r['procedure_id'],r['category'])==(s['n'],s['procedure_id'],s['target'])
            if s['record_kind']=='prop_selection_evaluation':
                selectionchecks+=1;assert r['side']==s['side']and r['strategy']==s['strategy']
                for k,v in s['selection_metrics'].items():assert r['selection_metrics'][k]==v,(key,k)
                if s.get('mae')is not None or s.get('bias')is not None:
                    assert all(r['metrics'][k]is None for k in('mae','mse','rmse','bias','p90_abs','p95_abs','max_abs'));numericremoved+=1;cohortnumericremoved+=int(key[0].endswith('COMMON_COHORT_SCORES.json'))
                if s['strategy'].startswith('ROLLING_K'):
                    k,side=s['strategy'].split('_')[1:];assert r['K']==int(k[1:])and r['rank_scope']=='PER_CATEGORY_PER_WEEK_ROLLING_DECISION_BATCHES'
            elif s['record_kind']=='prop_threshold_probability_evaluation':
                properchecks+=1;assert r['metrics']['brier']==s['brier']and r['metrics']['log_loss']==s['log_loss']
            else:assert r['product_id']=='original_mean_ancillary_not_repaired_probability_law_mean'and r['metrics']['mae']==s['mae']
    assert seen==set(original)and numericremoved==borrowed and cohortnumericremoved>0 and not any(missinghorizon.values())
    pointer=load(repo/'registries/CURRENT_RESULTS_INDEX.json');assert pointer['manifest']==str(index.relative_to(repo))
    # Exact source/capture/calibration clocks verified in preceding independent row audit.
    pref=load(out/'INDEPENDENT_PROBABILITY_SOURCE_BINDINGS_V1.json');assert bindings['pass_td']['base_capture_sha256']=='8c86b837d061dc6964907e7c900289dc452f7afb92aece7a2f4f2e48d1f5d886'and bindings['pass_td']['calibration_freeze_epoch']==1793300133.0;assert bindings['rec']['actual_weeks']==[2,3]and bindings['pass_td']['actual_weeks']==[8]
    report=(out/'B_PREDICTIVE_IMPROVEMENT_REPORT.md').read_text();assert 'Do **not recommend a production switch from this repair**'in report and 'still lost the matched **0.25 neutral reference**'in report and 'not newly C-admitted'in report and 'not demonstrably enforced'in report
    result=dict(state='PASS_SOURCE_CLOCK_AND_ARTIFACT_WIDE_ANCILLARY_PROJECTION',at_utc=datetime.now(timezone.utc).isoformat(),verification_code_sha256=sha(Path(__file__)),qualification_sha256=sha(qualification),source_bindings_sha256=sourcebindinghash,default_index_manifest=str(index.relative_to(repo)),index_manifest_sha256=sha(index),current_index_pointer_sha256=sha(repo/'registries/CURRENT_RESULTS_INDEX.json'),source_artifacts_unchanged_vs_independent_numeric_audits=True,annotation_rows_by_source=annotation_counts,new_index_rows_checked=len(seen),selection_rows_checked=selectionchecks,proper_probability_rows_checked=properchecks,missing_top_level_horizon_by_kind=dict(missinghorizon),horizon_discoverability_limit="All normalized kinds expose the exact target/product-specific bound horizon at top level; superseded draft omission remains in V3 receipt.",borrowed_point_metrics_removed_from_native_rankings=numericremoved,common_cohort_borrowed_native_metrics_removed=cohortnumericremoved,prior_immutable_index_rows_retained=594308,total_audit_views=602201,source_clock_contracts={'rec':'C current/revised kickoff reconstruction, Pinnacle last-recorded quote clocks unverified; W2-W3 only.','pass_td':'Original early partial W8 C02 capture plus retained later provider-labelled T90 threshold; W5/W6/W7 calibration transfer and current final labels. Not C Pinnacle or new original B1 issuance.'},report_sha256=sha(out/'B_PREDICTIVE_IMPROVEMENT_REPORT.md'),recommendation='Retain current owner selection; do not advance this repair on these adverse/uncertain results. Existing independently eligible provisional policy is unaffected.',new_fits=0,new_scores=0,limits=['This fixes source-vintage/horizon and borrowed-point attribution metadata in the default projection, preserving all original source SCORES and superseded draft indices. It does not authenticate missing historical quote clocks or source publication vintages.','Representative original row/capture bindings and all source arithmetic were independently checked in preceding receipts; this audit checks metadata bindings and all new projected rows without refitting or rescoring.','Counts are overlapping evaluation views, not additional methods, NFL games or original selections.','Declared earlier thread cap remains unverified; no silent rerun or enforcement claim.'])
    (out/'INDEPENDENT_SOURCE_CLOCK_AND_INDEX_PROJECTION_V4.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('repo',type=Path);p.add_argument('out',type=Path);p.add_argument('qualification',type=Path);p.add_argument('index',type=Path);a=p.parse_args();run(a.repo.resolve(),a.out.resolve(),a.qualification.resolve(),a.index.resolve())
