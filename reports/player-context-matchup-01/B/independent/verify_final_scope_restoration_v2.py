"""Read-only scope metadata and fresh retained-byte verification, no NFL replay."""
import argparse,collections,copy,hashlib,importlib.util,json
from pathlib import Path
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_bytes())
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--repo',type=Path,required=True);ap.add_argument('--restored',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();b=a.repo/'reports/player-context-matchup-01/B'
 overlay=read(b/'CURRENT_COVERAGE_SCOPE_V3.json');reader=a.repo/'nfl_v2/context_scope_metadata.py';assert sha(reader)==overlay['code_sha256']
 sp=importlib.util.spec_from_file_location('bound_metadata_reader',reader);mod=importlib.util.module_from_spec(sp);sp.loader.exec_module(mod)
 count=collections.Counter();scoped=0
 for source in overlay['sources']:
  path=a.repo/source['source_artifact'];assert sha(path)==source['source_sha256'];original=read(path);current=list(mod.qualified_rows(path,overlay));assert len(current)==len(original);idx={x['source_row_index']:x for x in source['rows']};assert len(idx)==len(source['rows'])
  assert all(type(i)is int and 0<=i<len(original)for i in idx)
  for i,(old,new)in enumerate(zip(original,current)):
   if i not in idx:assert old==new;continue
   c=idx[i];assert c['record_id']==old['record_id']and c['original_technical_unavailable']==old['technical_unavailable'];assert c['full_system_query_rows']==c['reported_scope_rows']+c['outside_reported_scope']and old['forecast_rows']==c['reported_scope_rows']and old['technical_unavailable']==c['outside_reported_scope']
   assert new['technical_unavailable']==0 and new['outside_reported_scope']==c['outside_reported_scope'];assert new['full_system_forecast_coverage']==dict(query_rows=c['full_system_query_rows'],available_forecasts=c['full_system_query_rows'],technical_unavailable=0)
   removed={'technical_unavailable','outside_reported_scope','full_system_forecast_coverage','scope_metadata_note'};assert{k:v for k,v in new.items()if k not in removed}=={k:v for k,v in old.items()if k not in removed}
   if old['record_kind']=='right_and_wrong_prediction_diagnostic':assert c['full_system_query_rows']==112 and old['default_rank_eligible']is False;count['outcome_conditioned_bucket']+=1
   else:
    assert old['record_kind']=='forecast_evaluation_view'and old['fallback_view']in('LEARNED','FALLBACK');full=next(r for r in original if r['record_kind']=='forecast_evaluation_view'and r['fallback_view']=='FULL_SYSTEM'and(r['procedure_id'],r['target'],r['season'],r['week'],r['product_id'])==(old['procedure_id'],old['target'],old['season'],old['week'],old['product_id']));assert full['forecast_rows']==c['full_system_query_rows']and full['technical_unavailable']==0;count['native_learned_fallback_scope']+=1
   scoped+=1
  # Exact-source, record-ID and partition guards; injected metric metadata
  # is ignored and can never overwrite the source's n/MAE.
  c0=source['rows'][0];bad=copy.deepcopy(overlay);badsource=next(x for x in bad['sources']if x['source_sha256']==source['source_sha256']);badsource['rows'][0]['record_id']='WRONG'
  try:list(mod.qualified_rows(path,bad));raise AssertionError('bad record accepted')
  except ValueError:pass
  bad=copy.deepcopy(overlay);next(x for x in bad['sources']if x['source_sha256']==source['source_sha256'])['source_sha256']='0'*64
  try:list(mod.qualified_rows(path,bad));raise AssertionError('bad source accepted')
  except ValueError:pass
  bad=copy.deepcopy(overlay);next(x for x in bad['sources']if x['source_sha256']==source['source_sha256'])['rows'][0]['reported_scope_rows']+=1
  try:list(mod.qualified_rows(path,bad));raise AssertionError('bad scope accepted')
  except ValueError:pass
  extra=copy.deepcopy(overlay);next(x for x in extra['sources']if x['source_sha256']==source['source_sha256'])['rows'][0].update(n=999999,mae=-123)
  out=list(mod.qualified_rows(path,extra));assert out[c0['source_row_index']].get('n')==original[c0['source_row_index']].get('n')and out[c0['source_row_index']].get('mae')==original[c0['source_row_index']].get('mae')
 assert scoped==800 and count==dict(outcome_conditioned_bucket=80,native_learned_fallback_scope=720)
 v1=read(b/'FULL_ARTIFACT_MANIFEST_V1.json');v2=read(b/'FULL_ARTIFACT_MANIFEST_V2.json');receipt=read(b/'FULL_GITHUB_RESTORATION_RECEIPT_V2.json');assert receipt['corrected_manifest_sha256']==sha(b/'FULL_ARTIFACT_MANIFEST_V2.json')
 omitted={r['path']for r in v2['excluded_non_source_runtime_entries']};assert len(omitted)==2 and all(p.endswith('.pyc')and'/__pycache__/'in p for p in omitted)
 assert v2['files']==[r for r in v1['files']if r['path']not in omitted]
 expected={r['path']:r for r in v2['files']};assert len(expected)==v2['required_files']==receipt['restored_files']==1139;assert len(receipt['files'])==len(expected)
 total=0
 for f in receipt['files']:
  p=a.restored/f['path'];bb=p.read_bytes();bound=expected[f['path']];assert sha(p)==bound['sha256']==f['sha256']and len(bb)==bound['bytes']==f['bytes'];total+=len(bb)
 assert total==v2['required_bytes']==receipt['restored_bytes']==50046384
 pointer=read(a.repo/'registries/CURRENT_RESULTS_INDEX.json');bound=pointer['player_context_matchup']['scoped_coverage_view'];assert bound['sha256']==sha(a.repo/bound['path'])and bound['reader']=='nfl_v2/context_scope_metadata.py:qualified_rows'
 license=(b/'DATA_LICENSES_AND_ATTRIBUTION_V2.md').read_text();assert 'qb-charting-wave-v1/'in license and'qb-charting-scores-v1/'in license and'CC BY-SA 4.0'in license
 report=(b/'B_PLAYER_CONTEXT_MATCHUP_REPORT.md').read_text();assert 'outside' in report and'CURRENT_COVERAGE_SCOPE_V3' in report
 out=dict(state='PASS_FINAL_SCOPED_COVERAGE_METADATA_AND_COMPLETE_PUBLIC_RESTORATION',supersedes_pending_item_in='FINAL_REPORT_AND_INDEX_REVIEW_V1.json',scope_overlay_sha256=sha(b/'CURRENT_COVERAGE_SCOPE_V3.json'),reader_sha256=sha(reader),qualified_rows=scoped,scope_counts=dict(count),all_forecast_grade_side_loss_n_MAE_fields_unchanged=True,metadata_reader_guards='SourceSHA,recordIDandpartitionmismatchrejected;injectedn/MAEcannotoverwriteanyscores;allactualcorrectionindicesvalid.',corrected_manifest_sha256=sha(b/'FULL_ARTIFACT_MANIFEST_V2.json'),restoration_receipt_sha256=sha(b/'FULL_GITHUB_RESTORATION_RECEIPT_V2.json'),independently_rehashed_fresh_files=len(expected),independently_rehashed_fresh_bytes=total,producer_commit=v2['producer_commit'],excluded_only_ignored_python_runtime_caches=sorted(omitted),source_licenses_sha256=sha(b/'DATA_LICENSES_AND_ATTRIBUTION_V2.md'),current_pointer_requires_metadata_reader=True,source_scores_and_all_previous_independent_arithmetic_receipts_unchanged=True,scientific_limit='Fullnewpublicbytepackageisrecoverable;oldrestricted38part796917760Bdependencyunchanged. ThisisnotNFLaccuracyvalidation,browserexecution,admissionordeployment. Rawsubsettechnical_unavailablefieldrequiresboundcurrentmetadatareader.',new_fits=0,new_forecasts=0,new_NFL_scoring=0,unsafe_model_deserialization=0,private_artifact_publication=0)
 if a.output.exists():raise FileExistsError(a.output)
 a.output.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(dict(state=out['state'],sha256=sha(a.output),files=len(expected),bytes=total)))
if __name__=='__main__':main()
