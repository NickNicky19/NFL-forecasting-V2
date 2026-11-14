"""Readable W5 source projections and explicit leaf-origin metadata, no rescoring."""
import argparse
import gzip
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2 import full_provider_prop_replay as core
from nfl_v2.shared_subgroups import now,sha,write
from tools.numerical_championship import csvwrite


def main(a):
    a.output=a.output.resolve()
    parent=a.output/'method-comparison-v1';leaf=a.output/'complete-leaf-law-v1'
    parentrows=json.loads((parent/'SCORES.json').read_bytes());leafrows=json.loads((leaf/'SCORES.json').read_bytes())
    sig={(r['target'],r['procedure_id'],r['history_regime']) for r in leafrows if r['record_kind']=='prop_threshold_probability_evaluation'}
    default=[]
    for source,rows in ((parent/'SCORES.json',parentrows),(leaf/'SCORES.json',leafrows)):
        for i,r in enumerate(rows):
            if source.parent==parent and (r['target'],r['procedure_id'],r['history_regime']) in sig and (r['record_kind']=='prop_threshold_probability_evaluation' or (r['record_kind']=='prop_selection_evaluation' and r['decision_rule']=='P2')):continue
            default.append((source,i,r))
    grouped={};native=[]
    for source,i,r in default:
        binding=dict(source_artifact=source.relative_to(a.root).as_posix(),source_artifact_sha256=sha(source),source_row_index=i,record_id=r['record_id'])
        if r['record_kind']!='prop_selection_evaluation':native.append(dict(**r,source_binding=binding));continue
        key=(source.as_posix(),r['method_id'])
        grouped.setdefault(key,dict(target=r['target'],procedure_id=r['procedure_id'],history_regime=r['history_regime'],product_id=r['product_id'],decision_rule=r['decision_rule'],season=2026,weeks=[5],horizon='PER_GAME_SERVER_SOURCE_CLOCK_T90_QUALIFIED_KNOWN_TARGET_TIME',evidence='RETROSPECTIVE_RULE_REPLAY',source_bindings=[]))
        z=grouped[key];m=r['selection_metrics'];s=r['side'];z['source_bindings'].append(binding)
        for name,val in dict(selected=r['forecast_rows'],wins=m['WIN'],losses=m['LOSS'],decided=m['denominators']['decided'],hit_rate=m['hit_rate'],pushes=m['PUSH'],voids=m['status_counts']['VOID'],pending=m['status_counts']['PENDING'],missing_actual=m['status_counts']['MISSING_ACTUAL'],unknown_participation=m['status_counts']['UNKNOWN_PARTICIPATION'],statistical_unresolved=m['status_counts']['UNRESOLVED_CONTRACT'],book_contract_unresolved=r['forecast_rows'],unique_games=r['unique_games'],game_uncertainty=m['game_uncertainty']).items():z[s+'_'+name]=val
        z.update(eligible_opportunities=m['selection_pool_count'],admitted_forecasts=m.get('admitted_forecast_opportunities'),unavailable_forecasts=m.get('unavailable_forecast_opportunities'),admitted_rule_abstentions=m.get('admitted_rule_abstentions'),selection_coverage_combined=None)
    wide=list(grouped.values())
    for r in wide:
        for field in ('selected','wins','losses','decided','pushes','voids','pending','missing_actual','unknown_participation','statistical_unresolved'):
            if r['Combined_'+field]!=r['over_'+field]+r['under_'+field]:raise ValueError('W5 side partition failed')
        r['selection_coverage_combined']=r['Combined_selected']/r['eligible_opportunities'] if r['eligible_opportunities'] else None
    write(a.output/'ALL_PRIMARY_METHOD_SIDES.json',wide);csvwrite(a.output/'ALL_PRIMARY_METHOD_SIDES.csv',wide)
    write(a.output/'NATIVE_AND_PROPER_PRODUCTS.json',native);csvwrite(a.output/'NATIVE_AND_PROPER_PRODUCTS.csv',native)
    pg=json.loads(gzip.decompress((a.leaf_private/'GRADED_COMPLETE_LEAF_LAWS.json.gz').read_bytes()))
    pf=json.loads(gzip.decompress((a.leaf_private/'FROZEN_LAW_DIRECTIONS_K.json.gz').read_bytes()))
    losskeys={(r['method_id'],r['source_row_index']) for r in pg['proper_losses']}
    km={(r['method_id'],r['K'],r['scope']):set(r['source_indices']) for r in pf['Kplans']}
    annotations=[]
    sources=[leaf/'SCORES.json']+[a.root/r['path'] for r in json.loads((leaf/'SUPPLEMENTAL_SCORE_ARTIFACTS.json').read_bytes())]
    for source in sources:
        for i,r in enumerate(json.loads(source.read_bytes())):
            if r['record_kind']=='prop_threshold_probability_evaluation':
                tag=r['record_id'].removeprefix('LEAF-PROB-');chosen=[x for x in pg['graded'][tag] if x['admitted']]
            else:
                tag=r['method_id'];pool=pg['graded'][tag]
                chosen=[x for x in pool if x['source_row_index'] in km[tag,r['K'],r['rank_scope']]] if r.get('K') is not None else [x for x in pool if core.in_cohort(x,r['cohort_id']) and x['selected_side']]
                chosen=[x for x in chosen if r['side']=='Combined' or x['selected_side']==r['side']]
            eligible=[x for x in chosen if x['admitted']];fallback=[x for x in eligible if x['source']=='REUSED_ELIGIBLE_FALLBACK_LAW'];scored=[x for x in eligible if (tag,x['source_row_index']) in losskeys];sf=[x for x in fallback if (tag,x['source_row_index']) in losskeys]
            annotations.append(dict(source_artifact=source.relative_to(a.root).as_posix(),source_artifact_sha256=sha(source),source_row_index=i,record_id=r['record_id'],actual_source_fallback_count=len(fallback),actual_source_learned_count=len(eligible)-len(fallback),actual_source_eligible_count=len(eligible),actual_source_scored_fallback_count=len(sf),actual_source_scored_learned_count=len(scored)-len(sf),actual_source_scored_eligible_count=len(scored),actual_source_fallback_rate=len(fallback)/len(eligible) if eligible else None,fallback_rate_denominator='Eligible laws in exact selected side/cohort/K; proper rows include direction ties',inherited_private_fallback_metadata='Not authoritative; explicit saved-law origin only'))
    write(a.output/'COMPLETE_LEAF_LAW_ORIGIN_ANNOTATIONS.json',annotations)
    write(a.output/'CURRENT_ACTUAL_METHOD_SCORE_PROJECTION.json',dict(schema='v2-actual-method-score-default-coverage-view-v1',at=now(),source_rules=[dict(panel='W5',parent_sources=[dict(path=p.relative_to(a.root).as_posix(),sha256=sha(p)) for p in [parent/'SCORES.json']+[a.root/r['path'] for r in json.loads((parent/'SUPPLEMENTAL_SCORE_ARTIFACTS.json').read_bytes())]],complete_leaf_sources=[dict(path=p.relative_to(a.root).as_posix(),sha256=sha(p)) for p in sources],exclude_parent_only_when=dict(signature_fields=['target','procedure_id','history_regime'],matching_complete_leaf_signatures=[list(k) for k in sorted(sig)],predicate="record_kind=='prop_threshold_probability_evaluation' OR (record_kind=='prop_selection_evaluation' AND decision_rule=='P2')"))],all_originals_retained=True,scientific_procedure_count_unchanged=True))
    lines=['# Week 5 actual-method comparison','','The supported panel expands to **14 of 15 Week 5 games and 617 recorded provider-labelled thresholds**. The missing Thursday game is not backfilled. Two unresolved stable identities remain unavailable for method matching; all original source rows remain in the universe. These are new retrospective method comparisons using qualified pregame threshold/context clocks and current/revised football inputs, not recovered original model issuance or verified sportsbook settlement.','','The table shows one named, unchanged C02 H-MULTI lower-median P1 procedure for continuity across categories. It is not a hindsight-selected winner or a full-season championship. Every supported method/control/history/product, including losses and abstentions, is retained in the linked complete table.','','| Category | Predicted Over wins/decided | Over hit rate | Predicted Under wins/decided | Under hit rate | Combined wins/decided | Combined hit rate | Selected / eligible |','|---|---:|---:|---:|---:|---:|---:|---:|']
    show=sorted((r for r in wide if 'v2-c02-' in r['procedure_id'] and 'strict' not in r['procedure_id'] and r['history_regime']=='H-MULTI' and r['product_id']=='lower_median' and r['decision_rule']=='P1'),key=lambda r:r['target'])
    fmt=lambda v:'N/A' if v is None else f'{100*v:.2f}%'
    for r in show:lines.append(f"| {r['target']} | {r['over_wins']}/{r['over_decided']} | {fmt(r['over_hit_rate'])} | {r['under_wins']}/{r['under_decided']} | {fmt(r['under_hit_rate'])} | {r['Combined_wins']}/{r['Combined_decided']} | {fmt(r['Combined_hit_rate'])} | {r['Combined_selected']}/{r['eligible_opportunities']} |")
    lines += ['', 'Point errors, actual-line proper probability scores and selected-side hit rates remain separate products. The complete law view uses 80 source-bound Leaf/C02 category/history laws, with 4,846 recovered learned rows plus two legitimate prior rows. Parameters were recovered by exact lookup of saved leaf IDs into 80 retained models and matched against 9,692 original mean/median summary witnesses; estimator predict/apply/fit/transform calls were forbidden. Quantiles or points were never treated as CDFs.', '', 'All K6/10/20 lists use the already registered chronological rolling-greedy policy, separately per category/method/control and combined-side/Over-only/Under-only pool. Fixed weekly lists are not claimed. Cohort membership comes from the source worker’s pregame qualification; unavailable membership stays unknown. Parent metadata-only annotations add selected-pool proper losses, precision numerators/denominators and disjoint admitted/unavailable/abstention counts without changing grades.', '', '[All primary side tables](ALL_PRIMARY_METHOD_SIDES.csv) · [Numerical/proper products](NATIVE_AND_PROPER_PRODUCTS.csv) · [Parent canonical scores](method-comparison-v1/SCORES.json) · [Complete law canonical scores](complete-leaf-law-v1/SCORES.json) · [Current coverage projection](CURRENT_ACTUAL_METHOD_SCORE_PROJECTION.json) · [Exact law-origin annotations](COMPLETE_LEAF_LAW_ORIGIN_ANNOTATIONS.json).', '', 'Over/Under counts group by the side selected before outcomes. Combined counts and hit rates reproduce from underlying wins and losses; no unweighted average of side percentages is used. Every selected row has an unresolved bookmaker contract; statistical wins do not establish cash settlement, prices or profitability. No production changes, model fits, new inference, capture or Week 8 outcome read occurred.']
    (a.output/'README.md').write_text('\n'.join(lines)+'\n')
    write(a.output/'REPORT_RECEIPT.json',dict(code_sha256=sha(__file__),primary_method_strategy_rows=len(wide),native_and_proper_products=len(native),law_origin_annotations=len(annotations),new_scores=0,new_inference=0,new_fits=0,canonical_score_bytes_changed=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--output',type=Path,required=True);p.add_argument('--leaf-private',type=Path,required=True);main(p.parse_args())
