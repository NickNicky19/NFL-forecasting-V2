"""Register the completed post-wave saved-row products; no re-evaluation."""
import collections
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools import abc_b_c_bound_replay as a
from tools import register_b_predictive_improvement_01 as inherited

OUT=ROOT/'reports/post-wave-5w-v1'
RANK=OUT/'b-confidence-ordering-v1/context-ranker-v1'


def main():
    p=ROOT/'registries/RESULT_ARTIFACTS.json';reg=a.load(p)
    sources=[]
    for f,kind in [
        (OUT/'b-confidence-ordering-v1/SCORES.json','saved_row_confidence_diagnostic_not_primary_rank'),
        (RANK/'SCORES.json','earlier_heldout_correctness_ranker_selection_not_event_probability_repair')]:
        rel=str(f.relative_to(ROOT));rows=a.load(f)
        assert rel not in {r['artifact'] for r in reg}, 'Do not re-register a completed wave'
        assert len({r['record_id'] for r in rows})==len(rows)
        reg.append(dict(artifact=rel,state='SCORED',kind=kind,
            version_note='POST-WAVE-5W-v1 B-owned saved-row diagnosis and one registered '
            'earlier-only L2 correctness-ranking mechanism. Original choices/event '
            'probabilities unchanged, losses/metadata versions retained. Primary '
            'product requires five exact scored weeks. Diagnostic/nonprimary research '
            'views, no original issuance or new C admission.'))
        sources.append(dict(path=rel,sha256=a.sha(f),rows=len(rows),kind=kind))
    p.write_text(json.dumps(reg,indent=2)+'\n')
    a.save(OUT/'NEW_CANONICAL_SCORE_MANIFEST.json',dict(
        state='REGISTERED_APPEND_ONLY',sources=sources,views=sum(r['rows'] for r in sources),
        raw_804_archive='AUDIT_ONLY;NOT_DUPLICATE_CURRENT_FEED',new_forecasts=0,new_NFL_observations=0))
    pairs=[]
    for r in a.load(RANK/'PAIRED_COMPARISONS.json'):
        pairs.append(dict(
            target=r['target'],procedure_id=r['procedure_id'],
            comparator_procedure_id=r['procedure_id'].removesuffix('::G1')+'::G0',
            product_id='base_event_direction_with_selection_reliability_ranker',
            comparator_product_id='base_event_direction_with_selection_reliability_ranker',
            population='COMMON_SELECTED_DECIDED_ROWS;OWN_POOL_COMPARISONS_SEPARATE',
            season=2026,history_regime='H-MULTI_BASE_EARLIER_OOF_CORRECTNESS',
            comparator_history_regime='H-MULTI_BASE_EARLIER_OOF_CONFIDENCE_THRESHOLD',
            policy_id=r['scope']+':W'+r['week_view'],
            contrast='EARLIER_CORRECTNESS_RANK_MINUS_RAW_CONFIDENCE',
            fallback_view='full_system',metric='STATISTICAL_SELECTED_SIDE_LOSS_RATE',
            n=r['common_decided'],candidate_error=r['uncertainty'].get('candidate_error'),
            comparator_error=r['uncertainty'].get('comparator_error'),
            delta=r['uncertainty']['delta'],relative_error_change=r['uncertainty']['relative_error_change'],
            uncertainty=r['uncertainty'],candidate_wins=r['candidate_wins'],comparator_wins=r['control_wins'],
            actual_weeks=([2,3] if r['target']=='rec' else [8]) if r['week_view']=='ALL' else [int(r['week_view'])],
            history_limit='No base forecast/side/event-probability change. G1 ranks '
            'baseline correctness learned from earlier heldout cases. Common selected '
            'mask is not complete selected-pool coverage or full-board accuracy. '
            'Exposed research; fewer than five scored weeks; insufficient week '
            'clusters. Own-pool matched-count sensitivity retained separately.'))
    inherited.OUT=OUT
    a.save(OUT/'INDEX_BOUND_PAIRED_ANALYSIS.json',pairs)
    inherited.append_pairs(pairs)
    print(json.dumps(dict(new_score_views=sum(r['rows'] for r in sources),new_paired_views=len(pairs))))


def append_mask():
    out=OUT/'B-111-RB-common-mask-v3'
    p=ROOT/'registries/RESULT_ARTIFACTS.json';reg=a.load(p)
    score=out/'SCORES.json';rel=str(score.relative_to(ROOT))
    assert rel not in {r['artifact']for r in reg}
    reg.append(dict(artifact=rel,state='SCORED',kind='owner_local_C_requested_111_RB_mask_saved_point_replay',
        version_note='All52retained rushing point/history/output configurations on C exact111RBmask, '
        'W2/W3/cumulative. No fit/inference/private-row-copy/newweek. Own learned/fallback '
        'contributions and all losses preserved; conditional subset is not broad-board '
        'coverage, C admission or five-week primary qualification.'))
    p.write_text(json.dumps(reg,indent=2)+'\n')
    metadata={r['procedure_id']:r for r in a.load(score)if r['side']=='Combined'and r['week']=='ALL'}
    crows,_=a.c_rows(Path('/workspace/evidence-private/abc-b-continuation-20261103/c-snapshot'))
    cp={r['method_id']:a.pid(r)for r in crows if r['category']=='rush_yd'}
    pairs=[]
    for r in a.load(out/'PAIRED_CONTROLS.json'):
        m=metadata[r['procedure_id']];u=r['uncertainty']
        pairs.append(dict(target='rush_yd',procedure_id=r['procedure_id'],
            comparator_procedure_id=cp[r['control_id']],product_id=m['product_id'],
            comparator_product_id='C_BOUND_ORIGINAL_DIRECTION',population='COMMON_DECIDED_ROWS_INSIDE_C_111_RB_MASK',
            season=2026,history_regime=m.get('history_regime'),comparator_history_regime='C_BOUND_EARLIER_POLICY',
            policy_id='C_111_RB_P1:W'+r['week_view'],contrast='COMPLETE_B_POINT_MINUS_BOUND_C_CONTROL',
            fallback_view='full_system',metric='STATISTICAL_SELECTED_SIDE_LOSS_RATE',n=r['common_decided'],
            candidate_error=u.get('candidate_error'),comparator_error=u.get('comparator_error'),
            delta=u['delta'],relative_error_change=u['relative_error_change'],uncertainty=u,
            candidate_wins=r['candidate_wins'],comparator_wins=r['control_wins'],
            actual_weeks=[2,3]if r['week_view']=='ALL'else[int(r['week_view'])],
            history_limit='C frozen111RBsubset; no new algorithm, time coverage or information '
            'effect claimed. Compare complete own procedures on common rows. '
            'Different/partial available populations remain in univariate source. '
            'Source/quote vintages unverified; exposed two-week sample, no C admission or release.'))
    inherited.OUT=out
    a.save(out/'INDEX_BOUND_PAIRED_ANALYSIS.json',pairs)
    inherited.append_pairs(pairs)
    a.save(out/'REGISTRATION_RECEIPT.json',dict(score_source=dict(path=rel,sha256=a.sha(score),rows=len(a.load(score))),
        new_paired_views=len(pairs),new_fits=0,new_inference=0,new_NFL_observations=0))


if __name__=='__main__':
    append_mask() if sys.argv[1:]==['--append-111-rb'] else main()
