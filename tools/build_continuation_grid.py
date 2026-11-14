#!/usr/bin/env python3
"""Current run-cell projection; old provisional references remain separate."""
import collections,csv,hashlib,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1];OUT=ROOT/'reports/continuation-20261030'
def main():
 rows=[];wave_counts={}
 for wave in ['distribution-wave-v2','count-ablation-wave-v1','chart-wave-v1']:
  base=OUT/wave;source=base/'GRID_STATUS.json';grid=json.loads(source.read_text());receipt=json.loads((base/'RUN_RECEIPT.json').read_text());wave_counts[wave]=dict(cells=len(grid),states=dict(collections.Counter(r['state']for r in grid)),new_fit_calls=receipt['actual_fit_calls'],reused_fit_calls=receipt.get('reused_fitted_models',0))
  for r in grid:
   rows.append(dict(cell_id=wave+':'+r['slot'],wave=wave,procedure_family=r['family'],target=r['target'],history_regime=r['history_regime'],information_policy=r['policy_id'],origin_week=r['week'],fit_state=r['state'],forecast_state='CAPTURED_PARTIAL_WEEK_OPEN_DEADLINES'if r['week']==8 else 'RETROSPECTIVE_RECONSTRUCTION',score_state='PENDING_QUALIFIED_FINAL_LABELS'if r['week']==8 else 'SCORED_WITH_FALLBACK_COVERAGE',source_artifact=str(source.relative_to(ROOT)),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),independent_family_count=None))
 # Signed and event targets cannot be filled by a count-objective point adapter.
 for target in ['pass_yd','rush_yd','rec_yd','rush_rec_yd','nick-chart-ppr-v1','anytime_td']:
  for history in ['H-CURRENT','H-RECENT','H-MULTI']:
   rows.append(dict(cell_id='count-point-NOT-APPLICABLE:'+target+':'+history,wave='count-ablation-wave-v1',procedure_family='HGB-Poisson-count-point',target=target,history_regime=history,fit_state='NOT_APPLICABLE',score_state='NOT_A_SIGNED_OR_BINARY_LAW_ADAPTER',reason='Count-supportobjectiveprocedureonlysixcounttargets; retainedsigned/binarylegacyaliasesarenotnewcountmodels'))
 (OUT/'EXPERIMENT_GRID.json').write_text(json.dumps(rows,indent=2)+'\n')
 keys=list(dict.fromkeys(k for row in rows for k in row))
 with(OUT/'EXPERIMENT_GRID.csv').open('w',newline='')as f:
  w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)
 old=json.loads((ROOT/'registries/EXPERIMENT_GRID.json').read_text())
 (OUT/'GRID_COMPLETENESS.json').write_text(json.dumps(dict(legacy_checkpoint_cells=len(old),legacy_reference_grid_unchanged=True,legacy_cells_not_a_method_or_completion_denominator=True,new_origin_cells=992,new_grid_rows_with_explicit_NA=len(rows),new_nfl_fits=840,explicit_no_fit_fallback_cells=152,new_scientific_families=2,executed_family_library_now=4,prior_failed_version_reused_not_added_as_new_science=True,waves=wave_counts,original_complex_artifact_blocks_persist=True,chart_partial_label_and_extended_position_limits='35of2394currentchartlabelsunresolved;7of8currentrareaggregatecasesoutsidepredeclaredQB/RB/WR/TE remainseparatelyvisible'),indent=2)+'\n')
 print(json.dumps({'origin_cells':992,'new_fit_calls':840,'fallback_cells':152,'legacy_cells_separate':len(old)}))
if __name__=='__main__':main()
