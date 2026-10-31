"""Bounded forty-row date-only amendment readback; no metric replay or fits."""
import argparse,copy,gzip,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'reports/continuation-20261030b'
INITIAL_NEW_SHARD_SHA256='4f7f7a0d525ab2ecca2cd9f3224b6376a991617c4f2e6c9b6fd0830b4db9ae8a'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def key(r):return tuple(r[k]for k in('game_id','player_id','target','population'))
def verify(private):
    pub=OUT/'carry-strong-control-comparison-v1';projection_path=pub/'SCORE_DATE_PROJECTION.json';projection=json.loads(projection_path.read_text());scores=json.loads((pub/'SCORES.json').read_text());assert projection['source_score_sha256']==sha(pub/'SCORES.json')=='0a0e60c53a3beb5336d379121fd9ef174657ff438c31ed4939466429494f6372'
    manifest_path=OUT/'results-index/INDEX_MANIFEST.json';manifest=json.loads(manifest_path.read_text());old=json.loads((ROOT/'reports/continuation-20261030/results-index/INDEX_MANIFEST.json').read_text());assert manifest['record_count']==47397 and manifest['shards'][:24]==old['shards'];assert len(manifest['input_manifests'])==42
    desc=manifest['shards'][-1];shard_path=ROOT/desc['path'];assert sha(shard_path)==desc['sha256'];allrows=json.loads(shard_path.read_text());indexed={r['source_record_id']:r for r in allrows if r['source_artifact']=='reports/continuation-20261030b/carry-strong-control-comparison-v1/SCORES.json'};assert len(indexed)==40 and len(projection['rows'])==40
    raw=json.loads(gzip.decompress((private/'carry-strong-control-comparison-v1/CARRY_CONTROL_ROWS.json.gz').read_bytes()))['methods'];records={name:{key(r):r for r in rs}for name,rs in raw.items()};shared=set.intersection(*[{k for k,r in rows.items()if r['actual']is not None and r['fallback']=='none'}for rows in records.values()]);empty=0;checks=0
    for source_index,(score,annotation)in enumerate(zip(scores,projection['rows'])):
        assert annotation['source_row_index']==source_index;row=indexed[score['record_id']];assert row['source_aggregate_fields']==score
        name=score['record_id'].split(':')[1];view=score['fallback_view'];rows=[r for k,r in records[name].items()if r['population']==score['population']and(view=='full_system'or view=='own_learned_only'and r['fallback']=='none'or view=='fallback_only'and r['fallback']!='none'or view=='all_five_learned_overlap'and k in shared)];selected=[r for r in rows if r['actual']is not None and r['prediction']is not None];weeks=sorted({r['week']for r in selected});forecast_weeks=sorted({r['week']for r in rows})
        assert annotation['actual_scored_weeks']==annotation['evaluation_weeks']==weeks;assert annotation['forecast_query_weeks']==forecast_weeks;assert row['weeks']==weeks
        assert row['evaluation_date_provenance']==dict(artifact='reports/continuation-20261030b/carry-strong-control-comparison-v1/SCORE_DATE_PROJECTION.json',source_row_index=source_index)
        assert row['n']==score['n']==len(selected);checks+=7
        if not selected:
            empty+=1;assert row['dates_missing_reason']=='zero_supported_rows_no_scored_weeks';assert row['primary_error']is None
    # Undo only the forty registered date fields/provenance. The resulting bytes
    # must equal the independently retained initial final-audit shard digest.
    before=copy.deepcopy(allrows)
    for row in before:
        if row['source_artifact']=='reports/continuation-20261030b/carry-strong-control-comparison-v1/SCORES.json':
            row['seasons']=[2026];row['weeks']=['ALL'];row['dates_missing_reason']=None;row.pop('evaluation_date_provenance',None)
    body=b'['+b','.join(json.dumps(r,separators=(',',':'),allow_nan=False).encode()for r in before)+b']\n';assert hashlib.sha256(body).hexdigest()==INITIAL_NEW_SHARD_SHA256
    return dict(status='PASS_EXACT_FORTY_DATE_ONLY_AMENDMENT',date_views=40,date_source_checks=checks,empty_views_with_explicit_no_scored_weeks=empty,all_metrics_and_ids_unchanged=True,all_other_new_records_byte_equivalent=True,old_24_shards_45706_records_unchanged=True,initial_new_shard_sha256=INITIAL_NEW_SHARD_SHA256,new_shard_sha256=desc['sha256'],new_manifest_sha256=sha(manifest_path),new_manifest_source_bindings=len(manifest['input_manifests']),projection_sha256=sha(projection_path),original_carry_scores_sha256=sha(pub/'SCORES.json'),initial_full_review_preserved_sha256=sha(OUT/'FINAL_PROJECTION_INDEPENDENT_REVIEW.json'),new_fits=0,new_forecasts=0,week8_outcomes_read=0)
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--private-root',type=Path,required=True);args=parser.parse_args();r=verify(args.private_root);OUT.joinpath('DATE_ANNOTATION_READBACK_REVIEW.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
