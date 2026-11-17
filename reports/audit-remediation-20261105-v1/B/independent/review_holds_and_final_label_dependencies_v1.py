"""Read-only guard/retention dependency audit. Never fit or regrade forecasts."""
import argparse,collections,csv,hashlib,json,sys
from pathlib import Path
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser()
 for name in ('repo','old-private','final-private','public-cache','output'):ap.add_argument('--'+name,type=Path,required=True)
 a=ap.parse_args();sys.path.insert(0,str(a.repo))
 from nfl_v2.recommendation_holds import recommendation_hold,HGB_CARRY_HOLD
 from nfl_v2.result_index import is_championship_eligible
 original='hgb-direct-history-controls-v1:absolute_error_point'
 cases=[]
 for name in (original,'v2-'+original,'B::'+original+':known-target-time-v1','B:'+original+':retained_view'):
  r=dict(target='rush_att',procedure_id=name);h=recommendation_hold(r)
  cases.append(dict(case='original_candidate_alias',procedure_id=name,expected_hold=HGB_CARRY_HOLD,actual_hold=h,pass_check=h==HGB_CARRY_HOLD,rank_eligible=is_championship_eligible(r)))
 for name,target in [(original,'pass_yd'),('v2-hgb-rush-att-qb-rb-specialization-v1:absolute_error_point','rush_att'),('hgb-direct-history-controls-v1:squared_error_mean','rush_att'),('empirical-player-history-control-v1','rush_att')]:
  r=dict(target=target,procedure_id=name,control_procedure_id=original);h=recommendation_hold(r)
  assert h is None and is_championship_eligible(r)
  cases.append(dict(case='unaffected_other_target_repair_or_comparator',procedure_id=name,target=target,pass_check=True))
 raw=dict(target='rush_att',objective='absolute_error_point',source_artifact='reports/continuation-20261029/hgb-history-v1/SCORES.json')
 assert recommendation_hold(raw)==HGB_CARRY_HOLD and recommendation_hold(dict(raw,source_artifact='reports/unknown.json'))is None
 sp=a.repo/'reports/abc-championship/local-week8-final-v1/SCORES.json';scores=json.loads(sp.read_bytes())
 actual=[r for r in scores if r.get('target')=='rush_att'and original in r.get('procedure_id','')]
 assert len(actual)==12 and all(recommendation_hold(r)==HGB_CARRY_HOLD for r in actual)
 oldcsv=a.old_private/'source-labels/fresh-player-stats-2026.csv';newcsv=a.final_private/'source-labels/stats.csv'
 def readcsv(p):return {(r['game_id'],r['player_id']):r for r in csv.DictReader(p.open())if(r['season'],r['week'],r['season_type'])==('2026','8','REG')}
 old,new=readcsv(oldcsv),readcsv(newcsv);common=old.keys()&new.keys();changed=collections.Counter()
 for key in common:
  for f in set(old[key])|set(new[key]):
   if old[key].get(f)!=new[key].get(f):changed[f]+=1
 assert dict(changed)=={'penalties':1,'penalty_yards':1} and len(common)==916 and len(new)==981
 bindingpaths={'original_parent_local_contract':a.old_private/'LOCAL_INPUT_BINDINGS_V1.json',
   'old_CSV':oldcsv,'final_CSV':newcsv,'final_games':a.final_private/'source-labels/games.csv',
   'final_ESPN':a.final_private/'source-labels/espn.json',
   'frozen_original_numeric_rows':a.old_private/'CAPTURED_LIBRARY_NUMERIC_ROWS_V1.json.gz'}
 source_bindings={k:dict(bytes=p.stat().st_size,sha256=sha(p))for k,p in bindingpaths.items()}
 oldcontrast=a.repo/'reports/week8-grading-20261102l/frozen-ablation-grading-v1/PAIRED_FROZEN_CONTRASTS.json'
 contrasts=json.loads(oldcontrast.read_bytes());assert all(r['whole_week_complete']is False for r in contrasts)
 final_contrast_candidates=[str(p.relative_to(a.repo))for p in(a.repo/'reports').rglob('*CONTRASTS.json')if 'week8'in str(p).lower()and p!=oldcontrast]
 cachefiles=[p for p in a.public_cache.rglob('*')if p.is_file()]
 r=dict(state='READ_ONLY_GUARD_AND_FINAL_LABEL_DEPENDENCY_REVIEW',
  recommendation_hold_code_sha256=sha(a.repo/'nfl_v2/recommendation_holds.py'),result_index_code_sha256=sha(a.repo/'nfl_v2/result_index.py'),
  guard_cases=cases,guard_failures=sum(not c['pass_check']for c in cases),
  existing_final_W8_original_L1_carry_views=12,existing_final_W8_views_all_protected_via_bound_base_procedure=True,
  narrow_limit='A single B: prefix without base procedure metadata needs explicit normalization; B:: is already recognized. Do not broaden the hold to specialization repairs, L2, other targets or comparator-only references.',
  actual_saved_score_file_sha256=sha(sp),source_bindings=source_bindings,
  final_Labels_construction='Reuse original parent Labels identity/frozen schedule contracts, then explicitly override games/finality/stats from final snapshot exactly as tools/abc_b_local_saved_replay.py; never assume old parent Labels is final.',
  complete_source_presence=dict(old_week8_rows=len(old),final_week8_rows=len(new),target_component_identical_existing_rows=len(common),changed_shared_non_target_cells=dict(changed),
    new_rows=len(new.keys()-old.keys()),new_game_ids=sorted({k[0]for k in new.keys()-old.keys()})),
  no_op_scope='All target component columns for916shared raw W8 rows are unchanged. Two penalty-related cells revised outside these targets; preserve source revision. Previously qualified/final target labels can be retained without alteration. Remaining label changes require finality/new-row qualification, not prediction regeneration.',
  chart_limit='Existing chart admission binds only old CSV6f04648e and old RDS. Its exact shared rows can retain old source qualification;65new CHI_SEA rows require a separately bound final-source/rare-component extension or stay unavailable. A final ordinary-source override does not silently authenticate new chart labels.',
  existing_frozen_contrasts=dict(path=str(oldcontrast.relative_to(a.repo)),sha256=sha(oldcontrast),views=len(contrasts),whole_week_complete=False,
     later_named_week8_contrast_candidates=final_contrast_candidates),
  search_scope='Current B reports tree names containing CONTRASTS.json and week8; existing local-final-v1 only ordinary offered-mask scoring. Not a census of unshared owner artifacts.',
  permitted_next_B_work='Freeze bounded saved-row finalization of existing H-MULTI empirical/Leaf A/B/C original captures; same retained forecasts/masks and final qualified labels only, original partial grades immutable. New chart source qualification explicit. No fits/inference/offer regeneration.',
  audit_resource_snapshot=dict(fetched_public_code_and_observation_cache_files=len(cachefiles),fetched_public_cache_bytes=sum(p.stat().st_size for p in cachefiles),
    restricted_player_row_copies_created_by_this_verifier=0,new_private_model_bytes=0,
    qualification='Public code cache includes preserved transport-extra-newline copies and Python bytecode; not restricted source/model uploads or restored archives.'),
  fixture_fit_calls=0,model_calls=0,new_NFL_grades=0,source_mutations=0)
 if a.output.exists():raise FileExistsError(a.output)
 a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(state=r['state'],guard_failures=r['guard_failures'],source_presence_identical_rows=len(common),sha256=sha(a.output))))
if __name__=='__main__':main()
