"""Seal final public pointer/source metadata after independent calculations."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];H=Path(__file__).resolve().parent.parent
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    file=ROOT/'registries/CURRENT_RESULTS_INDEX.json';p=read(file);bindings=[]
    for key,v in p.items():
        if isinstance(v,dict)and'path'in v and'sha256'in v:
            assert sha(ROOT/v['path'])==v['sha256'];bindings.append(dict(role=key,**v))
    assert p['manifest']=='reports/baselines-coverage-20261031h/results-index-v1/INDEX_MANIFEST.json';index=read(ROOT/p['manifest']);ind=read(H/'independent/FINAL_H_INDEX_INDEPENDENT_REVIEW.json');assert index['record_count']==542633 and sha(ROOT/p['manifest'])==ind['manifest_sha256']
    report=read(H/'independent/FINAL_CATEGORY_REPORT_INDEPENDENT_REVIEW.json');assert sha(ROOT/p['readable_checkpoint'])==report['report_sha256']and p['category_champions']['sha256']==report['category_JSON_sha256']
    prop=read(ROOT/p['prop_scoreboard']['path']);assert len(prop['source_scores'])==103
    for b in prop['source_scores']:assert sha(ROOT/b['path'])==b['sha256']
    coverage=read(H/'PROP_COVERAGE_WORDING_CORRECTION_V2.json');assert coverage['current_projection']['sha256']==sha(ROOT/p['prop_scoreboard']['path']);assert sha(ROOT/coverage['prior_draft']['path'])==coverage['prior_draft']['sha256'];assert coverage['score_or_membership_changes']is False
    assert'W1–4'in prop['historical_offer_coverage']and'14of15'in prop['historical_offer_coverage'];assert prop['price_state']=='UNESTABLISHED'and prop['publication']=='NO_V2_PRODUCTION_CHANGE'
    b=prop['complete_law_projection'];assert sha(ROOT/b['path'])==b['sha256'];law=read(ROOT/b['path']);assert law['parent_projection_timestamp_scope'].startswith('Inherited G');assert law['at']>law['parent_projection_at'];assert law['scientific_procedure_count_unchanged']and law['all_originals_retained'];assert len(law['source_rules'])==4
    prior=read(ROOT/'reports/completion-20261031g/roster/actual-method-period-summary-v2/CURRENT_ACTUAL_METHOD_SCORE_PROJECTION.json');assert law['source_rules'][:3]==prior['source_rules']
    assert law['source_rules'][3]['panel']=='W5'
    for rule in law['source_rules']:
        predicate=rule['exclude_parent_only_when']['predicate'];assert "decision_rule=='P2'"in predicate and"'P1'"not in predicate
        for name in ('parent_sources','complete_leaf_sources'):
            for b in rule[name]:assert sha(ROOT/b['path'])==b['sha256']
    receipt=dict(state='PASS_FINAL_H_POINTER_SOURCE_REPLACEMENT_AND_RELEASE_SCOPE',pointer_sha256=sha(file),pointer_hash_bindings=bindings,pointer_hash_binding_count=len(bindings),index_manifest_sha256=ind['manifest_sha256'],index_records=542633,report_sha256=report['report_sha256'],category_JSON_sha256=report['category_JSON_sha256'],prop_source_arrays=103,law_replacement_panels=4,all_G_parent_law_rules_unchanged=True,H_projection_timestamp_explicit=True,stale_W5_gap_wording_corrected=True,score_bytes_or_memberships_changed=False,production_release_authorized=False,independent_scope='Source calculations, side partitions, masks, metadata/index/report bindings; no merger, publication or owner admission attestation.')
    with (H/'independent/FINAL_H_POINTER_AND_ADMISSION_REVIEW.json').open('x')as f:json.dump(receipt,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in receipt.items()if k!='pointer_hash_bindings'}))
if __name__=='__main__':main()
