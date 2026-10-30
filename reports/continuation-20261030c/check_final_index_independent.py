"""Stream public index/source/CSV invariants; no private rows, fits or outcomes."""
import csv,hashlib,json,math,resource,subprocess,sys,time
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];HERE=ROOT/'reports/continuation-20261030c'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb')as f:
  for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
 return h.hexdigest()
def close(a,b):
 if b is None:assert a in(None,''),(a,b)
 else:assert a not in(None,'')and math.isclose(float(a),float(b),rel_tol=2e-10,abs_tol=1e-9),(a,b)
def verify():
 start,cpu=time.monotonic(),time.process_time();manifest=HERE/'results-index/INDEX_MANIFEST.json';m=json.loads(manifest.read_text());oldpath=ROOT/m['previous_sharded_checkpoint']['artifact'];old=json.loads(oldpath.read_text());assert sha(oldpath)==m['previous_sharded_checkpoint']['sha256'];accepted='fcfe6063e851582212cc63b055d6921fa17637ad';oldbytes=subprocess.run(['git','show',accepted+':'+oldpath.relative_to(ROOT).as_posix()],cwd=ROOT,check=True,capture_output=True).stdout;assert hashlib.sha256(oldbytes).hexdigest()==sha(oldpath);assert m['shards'][:len(old['shards'])]==old['shards'];pointer=json.loads((ROOT/'registries/CURRENT_RESULTS_INDEX.json').read_text());assert pointer['manifest']==manifest.relative_to(ROOT).as_posix();c=Counter();seen=set();kinds=Counter();sources=Counter();csvexpected={};statecounts=Counter();sourcecache=None;sourceartifact=None;sourceindex=0
 for item in m['input_manifests']:assert sha(ROOT/item['source_artifact'])==item['sha256'];c['frozen_input_hashes']+=1
 for index,part in enumerate(m['shards']):
  path=ROOT/part['path'];assert path.stat().st_size==part['bytes']and sha(path)==part['sha256'];rows=json.loads(path.read_text());assert len(rows)==part['records'];c['shard_hashes_and_censuses']+=1
  isnew=index>=len(old['shards'])
  for r in rows:
   ident=r['test_id'];assert ident not in seen;seen.add(ident);kinds[r['kind']]+=1;sources[r['source_artifact']]+=1
   if r['kind']=='software_verification':assert r.get('n')is None and r.get('games')is None and r.get('metrics')is None and r.get('precision_metrics')is None and r.get('nfl_accuracy_from_software_tests')is None;c['software_no_NFL_denominator_or_accuracy']+=1;continue
   assert r['primary_metric']==('brier'if r['category']=='anytime_td'else'mae');assert r['primary_error']==r['metrics'][r['primary_metric']]
   if r['n']is not None:assert isinstance(r['n'],int)and r['n']>=0
   if r['category']=='anytime_td':assert r['accuracy_status']=='not_applicable_without_registered_binary_decision_rule';c['probability_residual_not_classification_checks']+=1
   for metric,p in(r.get('precision_metrics')or{}).items():
    if p['numerator']is not None:assert p['denominator']==r['n']and isinstance(p['numerator'],int)and 0<=p['numerator']<=p['denominator'];close(p['rate'],p['numerator']/p['denominator']);assert p.get('numerator_provenance');c['precision_numerator_denominator_rate_checks']+=1
   if not isnew:continue
   artifact=r['source_artifact']
   if artifact!=sourceartifact:
    if sourceartifact is not None:assert sourceindex==len(sourcecache)
    sourceartifact=artifact;sourcecache=json.loads((ROOT/artifact).read_text());assert isinstance(sourcecache,list);sourceindex=0
   raw=sourcecache[sourceindex];sourceindex+=1;assert r['source_aggregate_fields']==raw;c['new_source_aggregate_exact_objects']+=1;assert sha_cached(artifact)==r['source_artifact_sha256']
   if raw.get('infinite_NLL',0):assert r['metrics']['nll']is None and r['metric_status']['nll']=='positive_infinite_loss';c['true_infinite_NLL_status_checks']+=1
   for metric,field in r['metric_source_fields'].items():
    if not field:continue
    if r['metric_status'][metric]=='positive_infinite_loss':assert r['metrics'][metric]is None;continue
    close(r['metrics'][metric],raw[field]);c['exact_native_source_metric_fields']+=1
   if raw.get('evaluation_weeks')==[]and r['n']==0:assert r['weeks']==[]and r['dates_missing_reason']=='zero_supported_rows_no_scored_weeks';c['empty_support_no_invented_date_checks']+=1
   if r.get('score_version_state'):statecounts[r['score_version_state']]+=1
   comp=r.get('reporting_comparison')or raw.get('comparison');expected={}
   if comp and comp.get('status')=='PAIRED_RETAINED_ROWS':
    assert comp['paired_n']==r['n']and comp['membership_sha256']and comp['comparator_procedure_id'];metric=comp['metric'];a,b=comp['candidate_error'],comp['comparator_error'];close(r['metrics'][metric],a);assert a>=0 and b>=0;expected=dict(status='SCORING_CORRECTION_NOT_PREDICTIVE_GAIN'if raw.get('correction_kind')else'PAIRED_RETAINED_ROWS',metric=metric,candidate=a,comparator=b,delta=a-b,relative=(a-b)/b if b else None,n=r['n'],membership=comp['membership_sha256']);c['paired_comparison_metric_and_binding_checks']+=1
   csvexpected[ident]=dict(comparison=expected,source=artifact,n=r['n'],metrics=r['metrics'],precision=r.get('precision_metrics')or{},version_state=r.get('score_version_state'),fallback=r.get('fallback_rows'),offered=r.get('forecast_or_offered_rows'))
 if sourceartifact is not None:assert sourceindex==len(sourcecache)
 assert len(seen)==m['record_count']and dict(kinds)==m['by_kind'];assert sum(s['records']for s in old['shards'])==old['record_count']==47398
 csvcount=0;csvseen=set();paired=zero=0
 for part in m['csv_parts']:
  path=ROOT/part['path'];assert sha(path)==part['sha256']and path.stat().st_size==part['bytes'];n=0
  with path.open(newline='')as f:
   for row in csv.DictReader(f):
    ident=row['test_id'];assert ident in seen and ident not in csvseen;csvseen.add(ident);n+=1;csvcount+=1
    if row['kind']=='software_verification':assert row['n']==row['games']==row['primary_error']=='';assert row['comparison_status']=='NOT_APPLICABLE_SOFTWARE';continue
    if ident not in csvexpected:continue
    value=csvexpected[ident];close(row['n'],value['n']);assert row['source_artifact']==value['source']
    for k,v in value['metrics'].items():close(row[k],v);c['CSV_native_error_readbacks']+=1
    for k,v in value['precision'].items():close(row[k+'_rate'],v['rate']);close(row[k+'_numerator'],v['numerator']);close(row[k+'_denominator'],v['denominator']);c['CSV_precision_readbacks']+=3
    comparison=value['comparison']
    if comparison:
     assert row['comparison_status']==comparison['status']and row['comparison_metric']==comparison['metric'];assert row['comparison_membership_sha256']==comparison['membership'];close(row['paired_n'],comparison['n']);close(row['comparator_error'],comparison['comparator']);close(row['absolute_error_change'],comparison['delta']);close(row['relative_error_change'],comparison['relative']);paired+=1
     if comparison['comparator']==0:assert row['relative_error_missing_reason']=='zero_comparator_error_denominator';zero+=1
    else:assert row['comparison_status']=='UNESTABLISHED'and row['absolute_error_change']==row['relative_error_change']==''
    if value['version_state']:assert row['score_version_state']==value['version_state']
    if value['fallback']is not None and value['offered']and value['fallback']<=value['offered']:close(row['fallback_rate'],value['fallback']/value['offered'])
    if 'server-retained-R0'in value['source']:assert row['live_website_comparison_status']=='UNESTABLISHED'
  assert n==part['rows'];c['CSV_part_hashes_and_censuses']+=1
 assert csvcount==len(csvseen)==len(seen);assert statecounts['INVALIDATED_REQUESTED_SHARED_MASK_REFERENCE_ALIAS']==1844;assert sum(v for k,v in statecounts.items()if k!='INVALIDATED_REQUESTED_SHARED_MASK_REFERENCE_ALIAS')==176
 diff=subprocess.run(['git','diff','--name-only',accepted,'--','reports/continuation-20261029','reports/continuation-20261030','reports/continuation-20261030b'],cwd=ROOT,check=True,capture_output=True,text=True).stdout;assert not diff.strip()
 counts=json.loads((HERE/'CHECKPOINT_COUNTS.json').read_text());assert counts['new_nfl_fit_calls']==13398 and counts['older_season_actual_fits']==12725 and counts['complete_older_score_views']==59080 and counts['older_unique_games']==1087 and counts['older_target_queries']==177690
 return dict(state='PASS_FINAL_STREAMING_INDEX_SOURCE_PRECISION_COMPARISON_AND_OLD_BYTE_READBACK',manifest_sha256=sha(manifest),record_count=len(seen),by_kind=dict(kinds),shards=len(m['shards']),prior_unchanged_records=old['record_count'],new_source_objects=c['new_source_aggregate_exact_objects'],CSV_rows=csvcount,CSV_paired_comparisons=paired,CSV_zero_control_denominator_guards=zero,version_state_counts=dict(statecounts),checks=dict(c),source_counts=counts,scope='Allshard/inputhashes,allold47398recordsretainedbyexactshardbytes,allnewsourceaggregateobjects/nativefields/precisioncounts,allCSVdeltas/membershipbindings/softwareclassification. Numericalsourceauditsareseparate;indexpublicationisnotdeployment. No privateNFLrowsorcurrentWeek8outcomesread.',resource=dict(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024),new_fits=0,new_forecasts=0,current2026_week8_outcomes_read=0)
_hashes={}
def sha_cached(path):
 if path not in _hashes:_hashes[path]=sha(ROOT/path)
 return _hashes[path]
if __name__=='__main__':
 r=verify();(HERE/'FINAL_INDEX_INDEPENDENT_REVIEW.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items()if k!='source_counts'}))
