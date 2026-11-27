"""Read back immutable public outputs, then expose B's owner-local export.

No remote write except the separately authorized own-repository git push;
this script makes only public GitHub reads and local metadata writes.
"""
import concurrent.futures
import datetime as dt
import hashlib
import json
import subprocess
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REF='a487b3661d93b8ac3aad971c408cd295e6512453'
PREFIX='reports/post-wave-5w-v1/'
OUT=ROOT/PREFIX


def blob(path):return subprocess.check_output(['git','show',REF+':'+path],cwd=ROOT)
def sha(b):return hashlib.sha256(b).hexdigest()


def main():
    index=ROOT/'reports/abc-championship/EXPORT_INDEX.json'
    old=index.read_bytes();assert sha(old)=='81a9737a278882736b7d98054a559cef5137b9aeedc7fd0a424ec6a0f797054f'
    snap=index.with_name('EXPORT_INDEX_d835346c_V6.json')
    with snap.open('xb')as f:f.write(old)
    r=json.loads(old)
    paths=subprocess.check_output(['git','diff-tree','--no-commit-id','--name-only','-r',REF],cwd=ROOT).decode().splitlines()
    paths=[p for p in paths if p.startswith(PREFIX)or p.startswith(('tools/','nfl_v2/','tests/','config/'))or p in ['registries/CURRENT_RESULTS_INDEX.json','registries/RESULT_ARTIFACTS.json','registries/ANALYSIS_ARTIFACTS.json']]
    def verify(path):
        expected=blob(path);url=f'https://raw.githubusercontent.com/NickNicky19/NFL-forecasting-V2/{REF}/{path}'
        with urllib.request.urlopen(url,timeout=30)as response:actual=response.read()
        if actual!=expected:raise ValueError('Immutable GitHub readback mismatch: '+path)
        return dict(path=path,producer_commit=REF,retrieval_url=url,bytes=len(actual),sha256=sha(actual),readback_verified=True,
            kind='B_POST5W_PUBLIC_SAFE_CODE_AGGREGATE_OR_BINDING',
            rights='PUBLIC_SAFE_AGGREGATES_CODE_METADATA_ONLY;NO_RESTRICTED_ROWS_PRIVATE_LOCATORS_OR_MODEL_WEIGHTS',
            retention='IMMUTABLE_GITHUB_BYTES_READBACK_VERIFIED',admission='NEW_PACKAGE_NOT_C_ADMITTED')
    with concurrent.futures.ThreadPoolExecutor(max_workers=4)as pool:items=list(pool.map(verify,paths))
    bound={x['path']:x for x in items}
    for source in [PREFIX+'b-confidence-ordering-v1/SCORES.json',PREFIX+'B-111-RB-common-mask-v3/SCORES.json']:
        ann=str(Path(source).with_name('SOURCE_HORIZON_QUALIFICATION_V2.json'))
        bound[source]['required_reporting_annotations']=dict(producer_commit=REF,path=ann,sha256=bound[ann]['sha256'],
            rule='MUST_APPLY_SOURCE_SHA_AND_RECORD_ID_BOUND_HORIZON_QUALIFICATION;RAW_SCORES_METRICS_UNCHANGED')
    for x in items:
        if 'SOURCE_HORIZON_QUALIFICATION_V1' in x['path']or '/results-index-v1/'in x['path']or '/results-index-v2/'in x['path']or '/results-index-v3/'in x['path']:
            x['state']='AUDIT_OR_REJECTED_METADATA_STAGE_NOT_CURRENT_DEFAULT'
        elif x['path'].endswith('/SCORES.json'):
            x['state']='CURRENT_SOURCE_SCORE_BYTES_WITH_REQUIRED_METADATA_BINDINGS'
    receipt=dict(state='PASS_IMMUTABLE_PUBLIC_SOURCE_READBACK',producer_commit=REF,
        verified_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),artifacts=items,
        verified_files=len(items),verified_bytes=sum(i['bytes']for i in items),
        private_bytes_exported=0,new_fits=0,new_forecasts=0,new_NFL_observations=0,
        C_receipt_or_admission='NOT_ESTABLISHED_BY_B_PUBLICATION')
    with(OUT/'PUBLICATION_READBACK_SOURCE_V1.json').open('x')as f:json.dump(receipt,f,indent=2);f.write('\n')
    r.update(schema_version='B-ABC-EXPORT-INDEX-v7.0',at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
        previous_index=dict(repository='NickNicky19/NFL-forecasting-V2',ref='d835346c2cda1cf7d2ffcfb843b103cbcb489615',path='reports/abc-championship/EXPORT_INDEX.json',sha256=sha(old),preserved_copy='reports/abc-championship/EXPORT_INDEX_d835346c_V6.json'),
        latest_C_publication=dict(ref='3c3199209cc9bcf5bdffbdedb230dac1262004e9',protocol_id='ABC-ACTUAL-PROP-CHAMPIONSHIP-v2-C-1',protocol_sha256='fa19581487519a854948269bc1ce328cbbcdc734afee2464f1ff778d1ff241a1',scorer_sha256='2ba450f91bb5fac869ce3adde031099390ec70408a91204653869032b49b2bce',
            prior_B_index_received='d835346c2cda1cf7d2ffcfb843b103cbcb489615',prior_B_source_records_received=7413,prior_B_source_records_total=7893,prior_B_selection_triads_admitted=2444,prior_COMMON_COHORT_views_unreceived=480,
            limits='Scoped owner-local aggregate arithmetic; no private row/model/inference parity; newa487postwave not yet C-admitted.',
            evidence=PREFIX+'C_NEW_PRIOR_WAVE_ADMISSION_RECEIPT.json'),
        latest_B_post_wave=dict(assignment_id='POST-WAVE-5W-v1',producer_commit=REF,
            report=PREFIX+'B_POST_WAVE_REPORT_FINAL_V3.md',current_result_manifest=PREFIX+'results-index-v4/INDEX_MANIFEST.json',
            current_paired_manifest=PREFIX+'paired-analysis-index-gzip-v2/ANALYSIS_MANIFEST.json',
            new_canonical_score_views=1510,new_paired_views=512,new_selection_ranker_fits=5,new_football_fits=0,new_inference=0,new_issued_forecasts=0,new_NFL_observations=0,new_weeks=0,
            primary_replacement='NONE;EXACT_NEW_POLICY_REC2WEEKS_PT1WEEK;NEGATIVE_OR_TIED_CONTROLLED_RESULTS',
            observed_results='RecMATCHED50 G086/163/G185/163; PTboth5/13; fixed90empty; RB111fourstrictmedian65vsstrongestotherB/Under/role63, twoexposedweeks/55fallbacks',
            five_week_gate=dict(path='config/B-product-five-week-floor-v1.json',sha256=bound['config/B-product-five-week-floor-v1.json']['sha256']),
            B_only_qualification_contribution=PREFIX+'B-product-week-qualification-v3/B_PRODUCT_WEEK_QUALIFICATION.json.gz',
            actual_source_horizon_annotations=[dict(path=x,sha256=bound[x]['sha256'],producer_commit=REF)for x in [PREFIX+'b-confidence-ordering-v1/SOURCE_HORIZON_QUALIFICATION_V2.json',PREFIX+'B-111-RB-common-mask-v3/SOURCE_HORIZON_QUALIFICATION_V2.json']],
            all_private_retention_limits_preserved=True,C_admission='NOT_VERIFIED_FOR_NEW_PACKAGE'),
        existing_480_view_delivery=dict(producer_commit='7d286572aa41db434d93b7619f4bf1a6b0e33ad4',
            source='reports/abc-predictive-improvement-01/b-intercept-v1/COMMON_COHORT_SCORES.json',source_sha256='900af8e69d75bd534240c7db86e155ea63b266458bfb60817be93e0f76ff093e',
            annotation='reports/abc-predictive-improvement-01/b-intercept-v1/COMMON_COHORT_SCORES_SOURCE_CLOCK_AND_ATTRIBUTION_ANNOTATIONS_V3.json',annotation_sha256='403977b705cb043965822351f5a7c737dff48f7b0eaf710dee47f858279417a9',
            both_objects_B_readback_verified=True,C_receipt='UNRECEIVED_AT_C3c319920;C_NEXT_FETCH_ACTION_NO_B_REFIT',evidence=PREFIX+'C_480_VIEW_RETRIEVAL_DISPOSITION.json'))
    old_count=len(r['exports']);r['exports']+=items
    r['delivery']=dict(r.get('delivery')if isinstance(r.get('delivery'),dict)else{},
        latest_source_commit=REF,latest_readback_receipt=PREFIX+'PUBLICATION_READBACK_SOURCE_V1.json',
        files_verified_new=len(items),public_bytes_verified_new=sum(x['bytes']for x in items),
        publication_is_not_C_acknowledgement=True)
    index.write_text(json.dumps(r,indent=2)+'\n')
    with(OUT/'EXPORT_PUBLICATION_BINDINGS_V1.json').open('x')as f:
        json.dump(dict(source_commit=REF,new_index_sha256=sha(index.read_bytes()),new_index_schema=r['schema_version'],
            prior_export_count=old_count,new_export_count=len(items),total_export_count=len(r['exports']),
            required_annotation_bindings_verified=True,new_C_admission=False,private_rows_or_models_exported=0),f,indent=2);f.write('\n')
    print(json.dumps(dict(new_verified=len(items),bytes=sum(x['bytes']for x in items),total_exports=len(r['exports']),index_sha256=sha(index.read_bytes()))))


if __name__=='__main__':main()
