"""Check vintage corrections and each deduplicated context's coverage denominator."""
import argparse,hashlib,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent;PUB=HERE.parent/'point-offer/v1'
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--receipt',type=Path,default=HERE/'REPORTING_METADATA_INDEPENDENT_REVIEW_V2.json');args=ap.parse_args()
    scores=read(PUB/'SCORES.json');byid={s['record_id']:s for s in scores};anno=read(PUB/'CURRENT_REPORTING_ANNOTATIONS_I_V1.json');default=read(PUB/'DEFAULT_DIAGNOSTIC_VIEW.json');assert anno['source_score_sha256']==default['canonical_score_sha256']==sha(PUB/'SCORES.json');assert default['reporting_annotations_sha256']==sha(ROOT/default['reporting_annotations']);assert len(anno['rows'])==len(scores)==258
    seen=set();kinds={};tiers={}
    for a in anno['rows']:
        i=a['source_row_index'];assert i not in seen;seen.add(i);r=scores[i];assert r['record_id']==a['record_id']and r['record_kind']==a['record_kind'];assert r.get('source_vintage')==a['original_source_vintage'];assert a['correction_kind']=='SOURCE_VINTAGE_METADATA_ONLY';kinds[r['record_kind']]=kinds.get(r['record_kind'],0)+1
        if r['history_regime']=='ARCHIVED':tier='SERVER_RETAINED_SAVED_PRECISION_POINT_AND_THRESHOLD;CURRENT_VINTAGE_QUALIFIED_LABELS;INTERNAL_MODEL_VINTAGE_UNVERIFIED;RETROSPECTIVE_P1_REPLAY'
        elif r['horizon_id']=='SAME_SAVED_KICKOFF_POPULATION_DIAGNOSTIC':tier='CURRENT_VINTAGE_FOOTBALL_RECONSTRUCTION;SAVED_KICKOFF_VECTOR_POPULATION_DIAGNOSTIC;NOT_ORIGINAL_ISSUANCE'
        else:tier='QUALIFIED_SERVER_RETAINED_THRESHOLD_CONTEXT;CURRENT_VINTAGE_7DAY_FOOTBALL_KNOWN_TARGET_TIME_RECONSTRUCTION;NOT_ORIGINAL_ISSUANCE'
        assert a['source_vintage']==tier;tiers[tier]=tiers.get(tier,0)+1
    assert kinds=={'forecast_evaluation_view':69,'prop_selection_evaluation':189}
    contexts=read(PUB/'CONTEXT_TO_DEDUPLICATED_SCORE.json');coverage=read(ROOT/default['context_coverage_extension']);assert len(contexts)==len(coverage)==178;own=common=broad=0;focal_own=[]
    for c,v in zip(contexts,coverage):
        assert all(c[k]==v[k]for k in ['context','record_id','same_mask_alias']);s=byid[c['record_id']];assert s['record_kind']=='forecast_evaluation_view';assert s['forecast_rows']==v['available_point_forecasts'];assert s['outer_opportunities']==v['canonical_record_outer_opportunities'];assert(s['target'],s['procedure_id'],s['history_regime'],s['product_id'])==tuple(v[k]for k in ['target','procedure_id','history_regime','product_id'])
        if c['context'].startswith('OWN_'):expected=84;own+=1
        elif c['context'].startswith('FOCAL_'):expected=s['forecast_rows'];common+=1
        else:expected=s['outer_opportunities'];broad+=1
        assert v['context_outer_opportunities']==expected;assert math.isclose(v['context_coverage'],s['forecast_rows']/expected if expected else 0,abs_tol=1e-12)if expected else v['context_coverage']is None
        if c['context']=='OWN_DECISION_ELIGIBLE_FULL_SYSTEM'and(s['target'],s['procedure_id'],s['product_id'])in [('pass_yd','hgb-direct-history-controls-v1:absolute_error_point','absolute_error_point'),('pass_cmp','v2-qualified-position-defense-information-wave-v1:D1','lower_median')]:focal_own.append(dict(target=s['target'],available=s['forecast_rows'],outer=expected,canonical_context_outer=s['outer_opportunities'],context_coverage=v['context_coverage']))
    receipt=dict(state='PASS_SOURCE_VINTAGE_CORRECTION_AND_CONTEXT_COVERAGE',canonical_score_sha256=sha(PUB/'SCORES.json'),annotation_sha256=sha(PUB/'CURRENT_REPORTING_ANNOTATIONS_I_V1.json'),default_view_sha256=sha(PUB/'DEFAULT_DIAGNOSTIC_VIEW.json'),context_extension_sha256=sha(ROOT/default['context_coverage_extension']),corrected_side_labels=189,added_point_labels=69,metadata_tiers=tiers,context_bindings=178,own_contexts=own,paired_contexts=common,broad_contexts=broad,focal_own_coverage=focal_own,canonical_scores_changed=False,new_fits=0,new_inference=0,new_scores=0)
    with args.receipt.open('x')as f:json.dump(receipt,f,indent=2);f.write('\n')
    print(json.dumps(receipt))
if __name__=='__main__':main()
