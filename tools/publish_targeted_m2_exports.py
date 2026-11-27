"""Append verified targeted M2 artifacts to the existing B export index."""
import datetime,gzip,hashlib,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
BASE=ROOT/'reports/targeted-accuracy-w1w9-01/B'
def sha(b):return hashlib.sha256(b).hexdigest()
def read(p):return json.loads(p.read_bytes())
def main():
    index=ROOT/'reports/abc-championship/EXPORT_INDEX.json';old=index.read_bytes();x=json.loads(old)
    assert len(x['exports'])==1849,'Existing export state changed; reconcile instead of overwrite'
    backup=BASE/'PREVIOUS_EXPORT_INDEX_V24.json.gz'
    if backup.exists():assert gzip.decompress(backup.read_bytes())==old,'Prior export bytes changed; reconcile'
    else:backup.write_bytes(gzip.compress(old,compresslevel=9,mtime=0))
    final=read(BASE/'retention/final-v1/MANIFEST.json');receipt=read(BASE/'retention/final-v1/READBACK.json');commit=receipt['commit']
    appended=[]
    def item(z,ref,phase,method,verified=True):
        p=z['path'];entry=dict(artifact_id='B-EXPORT-'+sha((ref+':'+p).encode())[:16],path=p,bytes=z['bytes'],sha256=z['sha256'],producer_commit=ref,
          retrieval_url=f'https://raw.githubusercontent.com/NickNicky19/NFL-forecasting-V2/{ref}/{p}',readback_verified=verified,readback_method=method,
          individual_raw_URL_GET=method=='DIRECT_IMMUTABLE_RAW_URL_BYTES',kind='TARGETED_M2_'+phase,rights=final['rights'],retention='IMMUTABLE_GITHUB_CAPSULE_MEMBER_BYTES_AND_COMMITTED_TREE_VERIFIED',
          admission='LOCAL_B_NOT_C_ADMITTED_OR_ORIGINAL_SITE_ACTIVATION',periods='2026W1–9numeric315;actualoffersW5–9CMP/ATT142each;2025W11–18numeric303;newearlyM2W1–4gradeabsent')
        appended.append(entry)
    for z in final['members']:item(z,commit,'EXECUTED_RESULTS','EXACT_IMMUTABLE_CAPSULE_MEMBER_BYTES')
    for phase in ('prefit-v1','prefit-v2','pilot-v1','final-v1'):
        d=BASE/'retention'/phase;m=read(d/'MANIFEST.json');r=read(d/'READBACK.json')
        for path in [d/'MANIFEST.json',d/'CAPSULE.tar.gz']:
            b=path.read_bytes();item(dict(path=str(path.relative_to(ROOT)),bytes=len(b),sha256=sha(b)),r['commit'],phase,'DIRECT_IMMUTABLE_RAW_URL_BYTES')
    oldids={r['artifact_id']for r in x['exports']if r.get('artifact_id')}
    assert not oldids&{r['artifact_id']for r in appended}
    assert len({r['artifact_id']for r in appended})==len(appended)
    assert not {(r.get('producer_commit'),r.get('path'))for r in x['exports']}&{(r['producer_commit'],r['path'])for r in appended}
    x['exports']+=appended;x['schema_version']='B-ABC-EXPORT-INDEX-v25';x['at_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    x['canonical_state']='TARGETED_M2_EXECUTED_LOCAL_NO_DIRECTION_GAIN_NATIVE5W;ALL12_COMMON_COMPARISON_PARTIAL;NO_NEW_PRIMARY_ACTIVATION'
    x['targeted_accuracy_w1w9_01']=dict(producer_commit=commit,report='reports/targeted-accuracy-w1w9-01/B/README.md',
      procedure='B-TARGETED-QB-CONTEXT-BETA-BINOMIAL-v1',active_protocol='reports/targeted-accuracy-w1w9-01/B/wave-v1/FROZEN_PROTOCOL_V2.json',
      final_manifest='reports/targeted-accuracy-w1w9-01/B/retention/final-v1/MANIFEST.json',final_readback='reports/targeted-accuracy-w1w9-01/B/retention/final-v1/READBACK.json',
      final_readback_receipt=receipt,readback_metadata_location='Read receipt paths from the same commit as EXPORT_INDEX; they are created after the evidence producer commit. The exact receipt is also embedded here.',
      scope='BBmean/exposurefixed vsP2/C1/C2BIN:0nativeLAWdirectionor19policy membershipchanges. Smalllinepropergains, broadcountNLLworse; DsameinputcontrolcountNLLbetterthanP2butdirectionlosesstrongB0. Useful75/80/90NOT_ESTABLISHED;1/1P90oneweekdisclosed.',
      actual_offer_weeks=[5,6,7,8,9],native_offers_each_category=142,numerical_current_weeks=list(range(1,10)),numerical_current_queries=315,
      robustness=dict(season=2025,weeks=list(range(11,19)),numeric_queries=303),new_M2_early_grade='A_OWNER_LOCAL_W1_4_JOIN_PENDING;SAVED_OUTPUTS_SUPPLIED_NO_REFIT_REQUIRED',
      original20policy_bridge='reports/targeted-accuracy-w1w9-01/B/independent/OWNER_LOCAL_NATIVE_ORDINAL_BRIDGE_V2.json',
      refreshed_A='3f10b641134658d3036933928cf2fa08dac4083c',refreshed_C='2b8bbc6da7bfb90106d7956cf86ccc160f2a343e',
      C_actual_receipt='NOT_OBSERVED_FOR_THIS_NEW_PACKAGE',new_primary_release=False,original_website_consumption='NOT_CLAIMED',old_exports_preserved=1849,new_exports=len(appended))
    x['next_action']='C intake exact targetedM2 evidence at supportedscope; A executeonlynewM2 early84saved-output join andapplyoriginal20policy ordinalbridge. No repeatedclosedFTN/timing/precisionsearch. Existing original-site/CountAowners continue independently.'
    index.write_text(json.dumps(x,indent=2,sort_keys=True,allow_nan=False)+'\n')
    assert read(index)['exports'][:1849]==json.loads(gzip.decompress(backup.read_bytes()))['exports']
    out=dict(state='APPENDED_VERIFIED_TARGETED_M2_EXPORTS_OLD_PREFIX_PRESERVED',producer_commit=commit,old_export_sha256=sha(old),new_export_sha256=sha(index.read_bytes()),old_entries=1849,new_entries=len(appended),all_entries=len(x['exports']),C_admission=False,production_activation=False)
    (BASE/'EXPORT_PUBLICATION_RECEIPT_V1.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
if __name__=='__main__':main()
