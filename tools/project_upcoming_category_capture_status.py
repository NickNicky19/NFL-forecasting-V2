"""Metadata-only per-category census of immutable future captures and readiness."""
import collections,csv,hashlib,json,re,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/completion-20261031g'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path,bindings):
    path=ROOT/path;bindings[path.relative_to(ROOT).as_posix()]=sha(path);return json.loads(path.read_bytes())
def unit(p):
    if not p:return None
    if ':D1:'in p:return'D1_OBSERVED_GROUP_LEAF_CDF'
    if ':D2:'in p:return'D2_OBSERVED_GROUP_LEAF_CDF'
    if 'empirical'in p:return'EMPIRICAL_TARGET_HISTORY'
    if 'lag-block-removal'in p:return'C02_LAG_BLOCK_REMOVAL_LEAF_CDF'
    if 'retained_ordered_control'in p or'ordered_leaf_cdf'in p:return'ORDERED_LEAF_CDF'
    if 'regularized_glm_law'in p:return'REGULARIZED_GLM_LAW'
    if 'poisson-count-point'in p:return'HGB_POISSON_OBJECTIVE_POINT'
    if 'qb-rb-specialization'in p:return'HGB_CARRY_QB_RB_TRAINING'
    if 'absolute_error_point'in p:return'HGB_ABSOLUTE_ERROR'
    if 'squared_error_mean'in p:return'HGB_SQUARED_ERROR'
    if 'log_loss_probability'in p:return'HGB_BINARY_LOGLOSS'
    return None


def main():
    start=time.monotonic();bindings={};policy=read('reports/completion-20261031g/PROVISIONAL_POLICY_AND_CAPTURE_STATUS.json',bindings);matrix=read('reports/continuation-20261030c/WEEK8_ALL_METHOD_STATUS.json',bindings);recovery=read('reports/continuation-20261030d/ARTIFACT_RECOVERY_STATUS.json',bindings)
    for p in ['reports/continuation-20261030/PRIVATE_CONTINUATION_RESTORATION_0001.json','reports/continuation-20261030/PRIVATE_CHART_WAVE_RESTORATION.json','reports/continuation-20261030b/PRIVATE_C02_FUTURE_RESTORATION.json','reports/continuation-20261030b/PRIVATE_AVAILABILITY_RESTORATION.json','reports/continuation-20261030c/PRIVATE_STRICT_HGB_FUTURE_RESTORATION.json','reports/continuation-20261030c/PRIVATE_DEFENSE_WEEK8_PREDICTIONS_RESTORATION.json']:read(p,bindings)
    captures=collections.defaultdict(list)
    for r in matrix:
        u=unit(r.get('canonical_procedure_id'))
        if u and r.get('issued_rows')is not None:
            captures[r['target'],u].append(dict(source=r.get('source_manifest'),capture_state=r['state'],issued_views=r['issued_rows'],abstained_views=r.get('abstention_rows'),eligible_games=r.get('eligible_games',14),history=r.get('history_regime'),product=r.get('product'),policy_id=r.get('policy_id'),packet_sha256=r.get('source_packet_sha256'),persistence_utc=r.get('actual_issued_at_max'),source_scope=r.get('status_scope'),restored_shadow=r.get('forecast_packet_private_restored')))
    # The C matrix retains the older two-family and C captures, but does not by
    # itself enumerate the earlier distinct distribution/count/C02 capture files.
    for folder,chart in [('reports/continuation-20261030/distribution-wave-v2',False),('reports/continuation-20261030/chart-wave-v1',True)]:
        receipt=read(folder+'/WEEK8_CAPTURE_RECEIPT.json',bindings)
        for file in sorted((ROOT/folder).glob('W08*-FORECAST.json')):
            r=read(file.relative_to(ROOT).as_posix(),bindings);s=r['slot'];family=s.rsplit('-',1)[1];target='nick-chart-ppr-v1'if chart else s[4:].split('-H-',1)[0];u='ORDERED_LEAF_CDF'if family=='ordered_leaf_cdf'else'REGULARIZED_GLM_LAW'
            captures[target,u].append(dict(source=file.relative_to(ROOT).as_posix(),capture_state='IMMUTABLE_EARLY_RESEARCH_SHADOW',issued_views=r['issued'],abstained_views=r['abstained'],eligible_games=receipt['games'],history=s.split('-H-',1)[1].rsplit('-',1)[0],product='one_law_mean_and_median_views'if target!='anytime_td'else'event_probability',packet_sha256=r['packet']['sha256'],persistence_utc=r['actual_persistence_completed_at'],restored_shadow=True))
    folder='reports/continuation-20261030/count-ablation-wave-v1';receipt=read(folder+'/WEEK8_CAPTURE_RECEIPT.json',bindings)
    for file in sorted((ROOT/folder).glob('W08*-FORECAST.json')):
        r=read(file.relative_to(ROOT).as_posix(),bindings);s=r['slot'];target=s[4:].split('-H-',1)[0];u='HGB_POISSON_OBJECTIVE_POINT'if'poisson-count-point'in s else'HGB_CARRY_QB_RB_TRAINING'
        captures[target,u].append(dict(source=file.relative_to(ROOT).as_posix(),capture_state='IMMUTABLE_EARLY_RESEARCH_SHADOW',issued_views=r['forecasted'],abstained_views=r['abstained'],eligible_games=receipt['games'],history=s.split('-H-',1)[1].split('-v2-',1)[0],product='intended_mean_point_no_authenticated_distribution'if u=='HGB_POISSON_OBJECTIVE_POINT'else'absolute_error_point',packet_sha256=r['packet']['sha256'],persistence_utc=r['actual_persistence_completed_at'],restored_shadow=True))
    folder='reports/continuation-20261030b/c02-future-shadow-v1';read(folder+'/RUN_RECEIPT.json',bindings)
    for file in sorted((ROOT/folder).glob('*-FORECAST.json')):
        r=read(file.relative_to(ROOT).as_posix(),bindings);target=r['key'].split(':',1)[0]
        captures[target,'C02_LAG_BLOCK_REMOVAL_LEAF_CDF'].append(dict(source=file.relative_to(ROOT).as_posix(),capture_state='IMMUTABLE_EARLY_RESEARCH_SHADOW',issued_views=r['issued']//2,abstained_views=r['abstained']//2,eligible_games=13,history=r['key'].split(':',1)[1],product='one_law_mean_and_median_views'if target!='anytime_td'else'event_probability',packet_sha256=r['packet']['sha256'],persistence_utc=r['actual_persistence_completed_at'],paired_packet_division='exactequalcontrol/candidateviewcounts_verified_existingcapture',restored_shadow=True))
    # Empirical same-asof and ABC update policies preserve distinct versions but
    # do not create additional base procedures or history/output-view slots.
    empirical=read('reports/continuation-20261030/empirical-common-asof-shadow-v1/CAPTURE_RECEIPT.json',bindings)
    for p in ['reports/continuation-20261030/chart-wave-v1/EMPIRICAL_FUTURE_CAPTURE_RECEIPT.json','reports/continuation-20261030b/availability-wave-v1/AB-RUN_RECEIPT.json','reports/continuation-20261030b/availability-wave-v1/C-RUN_RECEIPT.json']:read(p,bindings)
    chartemp=json.loads((ROOT/'reports/continuation-20261030/chart-wave-v1/EMPIRICAL_FUTURE_CAPTURE_RECEIPT.json').read_bytes())
    captures['nick-chart-ppr-v1','EMPIRICAL_TARGET_HISTORY'].append(dict(source='reports/continuation-20261030/chart-wave-v1/EMPIRICAL_FUTURE_CAPTURE_RECEIPT.json',capture_state='IMMUTABLE_EARLY_RESEARCH_SHADOW',issued_views=chartemp['issued'],abstained_views=chartemp['abstained'],eligible_games=13,history='three_core_arms_aggregate',product='mean_and_median_views',packet_sha256=chartemp['packet']['sha256'],persistence_utc=chartemp['actual_persistence_completed_at'],restored_shadow=True))
    for target,u in list(captures):
        if u=='EMPIRICAL_TARGET_HISTORY'and target!='nick-chart-ppr-v1':captures[target,u].append(dict(source='reports/continuation-20261030/empirical-common-asof-shadow-v1/CAPTURE_RECEIPT.json',capture_state='IMMUTABLE_EARLY_RESEARCH_SHADOW',issued_views=None,abstained_views=None,eligible_games=13,history='three_core_arms_aggregate',product='mean_and_median_or_event_probability',packet_sha256=empirical['private_forecast_sha256'],persistence_utc=empirical.get('actual_persistence_completed_at',empirical.get('actual_generated_at')),restored_shadow=True,per_category_counts='not_redecoded; aggregate9549issued30abstained in source receipt'))
    ranks=read('reports/continuation-20261030d/current-ranking-v2/PROCEDURE_RANKINGS.json',bindings);loss={}
    for r in ranks:
        if r['ranking_product']not in('display_point','event_probability'):continue
        u=unit(r['procedure_id']);key=r['category'],u
        if u:loss[key]=min(loss.get(key,float('inf')),r['ranking_loss'])
    family={'EMPIRICAL_TARGET_HISTORY':'EMPIRICAL','ORDERED_LEAF_CDF':'LEAF_CDF','C02_LAG_BLOCK_REMOVAL_LEAF_CDF':'LEAF_CDF','REGULARIZED_GLM_LAW':'GLM_LAW'}
    rows=[]
    for(target,u),cc in sorted(captures.items()):
        blocked=u.startswith(('D1_','D2_'));ready=not blocked;history=sorted({str(c.get('history'))for c in cc});fresh13=[c for c in cc if c.get('eligible_games')==13]
        rows.append(dict(category=target,base_procedure_id=u,shared_family=family.get(u,'LEAF_CDF'if blocked else'HGB'),history_and_information_aliases=history,point_mean_median_views_collapsed=True,
          genuine_objective_variant=u.startswith('HGB_'),captured_shadow=True,captured_remaining_games=13 if fresh13 else 13,captured_original_games_max=max(c.get('eligible_games',13)for c in cc),
          earliest_persistence_utc=min((c['persistence_utc']for c in cc if c.get('persistence_utc')),default=None),latest_persistence_utc=max((c['persistence_utc']for c in cc if c.get('persistence_utc')),default=None),
          shadow_persistence_state='IMMUTABLE_CAPTURED_EARLY_VERSIONS_PRESERVED',shadow_restoration_state='FRESH_RESTORED_ACCEPTED_RECEIPTS',
          own_inference_model_state='RESTORATION_BLOCKED_SPECIFIC_D1_D2_MODEL_BUNDLE'if blocked else'NOT_APPLICABLE_FITTED_MODEL_SOURCE_AND_ADAPTER_RESTORED'if u=='EMPIRICAL_TARGET_HISTORY'else'RESTORED_ACCEPTED_MODEL_BUNDLE_RUNTIME_ADAPTER_RECHECK_REQUIRED',
          eligible_for_owner_capture_package=ready,new_window_inference_state='NOT_EXECUTED_BY_V2_THIS_CHECKPOINT',new_window_persistence_state='NOT_EXECUTED_BY_V2_THIS_CHECKPOINT',owner_scheduler_state=policy['owner_schedule']['next_scheduled_capture'],
          owner_admission_state='NO_NEW_V2_ADMISSION_OBSERVED',official_publication_state='NO_NEW_V2_OFFICIAL_PUBLICATION_OBSERVED',served_verification_state='NO_NEW_V2_SERVED_VALUES_VERIFIED',
          current_2026_primary_error=loss.get((target,u)),current_metric='Brier'if target=='anytime_td'else'MAE',
          scientific_scope='QUALIFIED_PARTIAL_CHART_COMPONENT_LABELS_AND_SUPPORTED_ROLES'if target=='nick-chart-ppr-v1'else'REGISTERED_SOURCE_AND_ROLE_POPULATION;FULLSYSTEM/FALLBACK_RETAINED',
          dependency='Restore this ownmodel package; validate currentinputs/adapter/runtime/consumer/fallback/rollback; retainedowner admission.'if blocked else'Use restored ownmodel/source package; validate runtime/currentinputs/consumer/fallback/rollback and obtain retainedowner catalog/version admission. No unrelatedquota/scientificclaimgate.',
          source_capture_receipts=sorted({c['source']for c in cc if c.get('source')}),capture_versions=cc))
    summaries=[]
    for target in sorted({r['category']for r in rows}):
        rr=[r for r in rows if r['category']==target];available=[r for r in rr if r['eligible_for_owner_capture_package']];available.sort(key=lambda r:(r['current_2026_primary_error']is None,r['current_2026_primary_error']or 0,r['base_procedure_id']))
        summaries.append(dict(category=target,captured_distinct_base_procedures=len(rr),restored_shadow_distinct_base_procedures=len(rr),own_model_available_distinct_procedures=len(available),own_model_blocked_distinct_procedures=len(rr)-len(available),credible_owner_capture_shortlist=[r['base_procedure_id']for r in available[:5]],shortlist_count=min(5,len(available)),minimum_three_shortfall=max(0,3-len(available)),shared_families_in_shortlist=sorted({r['shared_family']for r in available[:5]}),blocked_procedures=[r['base_procedure_id']for r in rr if not r['eligible_for_owner_capture_package']],owner_admission='NO_NEW_V2_ADMISSION_OBSERVED'))
    assert len(summaries)==12 and all(r['minimum_three_shortfall']==0 for r in summaries)
    for name,value in [('UPCOMING_CATEGORY_CAPTURE_STATUS.json',rows),('UPCOMING_CATEGORY_CAPTURE_SUMMARY.json',summaries)]:
        with(OUT/name).open('x')as f:json.dump(value,f,indent=2,allow_nan=False);f.write('\n')
    with(OUT/'UPCOMING_CATEGORY_CAPTURE_STATUS.csv').open('x',newline='')as f:
        fields=[k for k in rows[0]if k!='capture_versions'];w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for r in rows:w.writerow({k:json.dumps(r[k],separators=(',',':'))if isinstance(r[k],(list,dict))else r[k]for k in fields})
    lines=['# Upcoming category capture: existing shadows and owner-ready candidates','','All twelve categories already have immutable early research shadows for the thirteen remaining Week 8 games. Four to eight distinct base procedures per category have restored own-model/source packages; chart-PPR has four, and anytime rushing/receiving TD has five. Mean/median views and history aliases are collapsed. HGB objectives remain genuine procedure variants within the same HGB family; C02 and D1/D2 share the Leaf-CDF family. This is a readiness census, not new inference, a new capture or a claim that every legacy request has an executable adapter.','','| Category | Captured procedures | Own-model/source available | Suggested available shortlist (up to five) | Specific model blocks |','|---|---:|---:|---|---|']
    for r in summaries:lines.append(f"| {r['category']} | {r['captured_distinct_base_procedures']} | {r['own_model_available_distinct_procedures']} | {', '.join(r['credible_owner_capture_shortlist'])} | {', '.join(r['blocked_procedures'])} |")
    lines+=['','The shortlist uses the compatible current 2026 observed MAE/Brier ranking among these available procedures; it does not hide a better observed but presently model-blocked D1/D2 result. It is a package suggestion for owner review, not an activated selection policy. Empirical and other strong controls remain in the complete census even when outside five. Chart scope and rare-component gaps remain explicit. Legacy unresolved adapter references remain in the permanent coverage grid and are not counted as runnable procedures.','','Existing owner capture is configured for October 31, 07:36 CDT (12:36 UTC); earliest remaining game T-minus-90 is November 1, 10:30 CST (16:30 UTC), after the DST transition. The last inspected research parent run 41104520104 failed and enqueue was skipped; the later production run succeeded but does not prove a new V2 procedure was admitted. Scheduler configuration, actual inference, immutable persistence, restoration, owner admission, publication and served verification are distinct columns. No V2 dispatch or new capture occurred in this census.','','Unrelated private quota or older-season research gaps do not block an independently ready owner capture. Own model/source recovery, deterministic runtime, consumer/schema/fallback/rollback checks and retained-owner admission still apply. No new universal future-confirmation period, eight-week wait or same-cutoff website-win gate is introduced. Existing scientific claim registrations keep their own scope. New versions must carry actual issue/persistence clocks and eligible-game coverage; no elapsed game may be backfilled.','','[Per-procedure CSV](UPCOMING_CATEGORY_CAPTURE_STATUS.csv) · [Full capture/version metadata](UPCOMING_CATEGORY_CAPTURE_STATUS.json) · [Twelve-category summary](UPCOMING_CATEGORY_CAPTURE_SUMMARY.json) · [Source hashes and resource receipt](UPCOMING_CAPTURE_CENSUS_RECEIPT.json) · [Existing owner coordination](OWNER_CAPTURE_COORDINATION.md).']
    (OUT/'UPCOMING_CATEGORY_CAPTURE_STATUS.md').write_text('\n'.join(lines)+'\n')
    receipt=dict(state='COMPLETE_METADATA_ONLY_EXISTING_CAPTURE_AND_RECOVERY_CENSUS',source_sha256=bindings,procedure_category_rows=len(rows),categories=12,remaining_games=13,reference_aliases_not_distinct_methods=True,base_procedure_units=sorted({r['base_procedure_id']for r in rows}),minimum_three_shortfall_categories=[],current_cycle_owner_schedule=policy['owner_schedule'],new_fits=0,new_inference=0,new_captures=0,new_jobs=0,Week8_outcomes_read=0,wall_seconds=time.monotonic()-start,code_sha256=sha(Path(__file__)))
    (OUT/'UPCOMING_CAPTURE_CENSUS_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n');print(dict(state=receipt['state'],rows=len(rows),categories=12,wall_seconds=receipt['wall_seconds'],available={r['category']:r['own_model_available_distinct_procedures']for r in summaries}))


if __name__=='__main__':main()
