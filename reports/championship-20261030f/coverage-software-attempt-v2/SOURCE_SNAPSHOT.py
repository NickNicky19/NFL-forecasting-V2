"""Source-bound scientific coverage and unresolved-reference projection; no fits or grades."""
from __future__ import annotations
import collections,csv,hashlib,json,re,resource,time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/championship-20261030f/coverage'
CURRENT='reports/continuation-20261030d/current-ranking-v2/current-valid-results/CURRENT_MANIFEST.json'
AUDIT='reports/prop-grading-20261030e/compact-results-index/INDEX_MANIFEST.json'
EXCLUSIONS='reports/continuation-20261030d/CURRENT_SCORE_VERSION_EXCLUSIONS_RECOMMENDATION.json'
OLD='registries/EXPERIMENT_GRID.json'
CGRID='reports/continuation-20261030c/EXPERIMENT_GRID.json'
STRICT='reports/continuation-20261030d/strict-hgb-2026-prepared-v2/PREPARED_PROTOCOL_NO_FITS.json'
SCHEDULED='reports/continuation-20261030d/scheduled-defense-window-v1/BLOCKED_FIT_GRID.json'
REUSE='reports/continuation-20261030d/scheduled-defense-fit-prepared-v3/REUSE_PLAN.json'
E2021='reports/continuation-20261030d/source2021-qualification-v1/EXTENSION_DESIGN_NO_FITS.json'
PATHWAYS='reports/continuation-20261030d/pathway-reconciliation-v2/PATHWAY_STATUS_60.json'
R0='reports/continuation-20261030c/server-retained-R0-v1/SCORES.json'
NEWSEL='reports/championship-20261030f/offer-expansion/full-pool-v1/SCORES.json'
MECHANISMS=('empirical-player-history-control-v1','v2-qualified-partial-chart-direct-wave-v1:',
 'v2-distribution-controls-reconstruction-v2:','v2-hgb-poisson-count-point-reconstruction-v1:',
 'v2-hgb-rush-att-qb-rb-specialization-v1:','v2-c02-explicit-lag-block-removal-leaf-cdf-v1:',
 'hgb-direct-history-controls-v1:','v2-qualified-position-defense-information-wave-v1:')
CORE=('H-CURRENT','H-RECENT','H-MULTI')


def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(path):return json.loads((ROOT/path).read_bytes())
def scientific(p):return any(p.startswith(s)for s in MECHANISMS)
def product(value):return'mean'if value=='empirical_mean'else value
def proc(p):
    if p=='v2-qualified-partial-chart-direct-wave-v1:empirical':return'empirical-player-history-control-v1'
    for suffix in(':common-feature-memory',':strict-current-inputs',':strict-current-feature-memory'):
        p=p.removesuffix(suffix)
    return p
def memory(p,raw):
    policy=str(raw.get('policy_id',''))+' '+str(raw.get('information_policy',''))
    if 'empirical'in p:return'PER_ARM_OUTCOME_HISTORY_NO_PREDICTOR_FEATURE_MEMORY_RETROSPECTIVE_POSITION'
    if'strict-current'in p or'STRICT'in policy:return'EVALUATION_SEASON_ONLY_NFL_INFORMATION'
    if 'common-feature-memory'in p or'COMMON'in policy or'2022common'in str(raw.get('feature_memory_policy')):return'COMMON_NFL_MEMORY_FROM_2022'
    # The original HGB construction consumes the common historical slot vector;
    # the separately named strict-input procedure is the unrun147-cell queue.
    if p.startswith('hgb-direct-history-controls-v1:'):return'COMMON_NFL_MEMORY_FROM_2022'
    return'SOURCE_POLICY_UNRESOLVED_INSPECT_LINKED_CONTRACT'
def hist(policy):return next((v for v in CORE if str(policy).startswith(v)),None)
def base(unit,status,reason,**kw):
    return dict(unit_kind=unit,status=status,reason=reason,procedure_id=None,procedure_aliases=[],category=None,season=None,week=None,
      history_regime=None,product_id=None,feature_memory_policy=None,information_tier=None,horizon_id=None,population=None,
      evaluation_policy=None,source_records=[],source_artifacts=[],source_states=[],dependencies=[],**kw)
def emit(rows,row):
    row['coverage_id']='COV-'+hashlib.sha256(canonical(row)).hexdigest()[:24];rows.append(row)


def main():
    begin=time.monotonic()
    def guard():
        if time.monotonic()-begin>120 or resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>1073741824:raise RuntimeError('coverage resource bound')
    if OUT.exists():raise ValueError('immutable projection destination exists')
    current,audit=load(CURRENT),load(AUDIT);assert current['selected_evaluation_views']==124630 and audit['record_count']==152751
    manifests=[CURRENT,AUDIT,EXCLUSIONS,OLD,CGRID,STRICT,SCHEDULED,REUSE,E2021,PATHWAYS,R0,NEWSEL]
    sources={p:sha(ROOT/p)for p in manifests}
    ids=set(load(current['selected_ids']['path']));assert len(ids)==124630
    candidates={}
    for part in current['csv_parts']:
        assert sha(ROOT/part['path'])==part['sha256']
        for r in csv.DictReader((ROOT/part['path']).open()):
            if r['population']=='primary'and r['position']=='ALL'and r['fallback_view']=='ALL'and not r['cohort_id']and scientific(r['procedure_id']):candidates[r['test_id']]=r
    groups={};seen=set();audit_count=0
    for shard in audit['shards']:
        assert sha(ROOT/shard['path'])==shard['sha256']
        for r in load(shard['path']):
            audit_count+=1
            if r['test_id']not in candidates:continue
            assert r['test_id']in ids
            seen.add(r['test_id']);a=r.get('source_aggregate_fields')or{};p=r['procedure_id'];years=r.get('seasons')or[];weeks=r.get('weeks')or[]
            if len(years)!=1 or years[0]not in range(2022,2027):continue
            year=int(years[0]);wk=weeks[0]if len(weeks)==1 else'ALL';mem=memory(p,a)
            contract=dict(policy_id=a.get('policy_id'),information_policy=a.get('information_policy'),feature_memory_policy=r.get('feature_memory_policy'),cutoff=r.get('cutoff'),cutoff_status=r.get('cutoff_status'))
            key=(proc(p),r['category'],year,str(wk),r['history_regime'],product(r['product_id']),mem,r.get('evaluation_panel_id'))
            if key not in groups:
                partial=year==2022 and r['history_regime']=='H-RECENT'
                groups[key]=base('scientific_evaluation_cell','COMPLETED_PARTIAL'if partial else'COMPLETED_VALID',
                  '2022 RECENT uses source-limited 2022-floor proxy; authentic preceding-2021 fitting is separately staged.'if partial else'Scored current-valid full-system primary/ALL cell; not a fit or an independent new observation.')
                groups[key].update(procedure_id=proc(p),category=r['category'],season=year,week=wk,history_regime=r['history_regime'],product_id=product(r['product_id']),product_aliases=[],feature_memory_policy=mem,
                  information_tier='FOOTBALL_HISTORY_ONLY_CURRENT_VINTAGE_RECONSTRUCTION',horizon_id='KICKOFF_LEFT_LIMIT_RECONSTRUCTION_ORIGINAL_SOURCE_CONTRACT',population='primary',
                  evaluation_policy='FULL_SYSTEM_PRIMARY_ALL_POSITION_NO_SUBGROUP',evaluation_panel_id=r.get('evaluation_panel_id'),evaluation_weeks=weeks,source_contracts=[],supported_n_values=[],forecast_rows_values=[])
            g=groups[key];g['procedure_aliases'].append(p);g['product_aliases'].append(r['product_id']);g['source_records'].append(r['test_id']);g['source_artifacts'].append(r['source_artifact']);g['source_states'].append(r.get('evidence'));g['source_contracts'].append(contract)
            if r.get('n')is not None:g['supported_n_values'].append(r['n'])
            if r.get('forecast_or_offered_rows')is not None:g['forecast_rows_values'].append(r['forecast_or_offered_rows'])
        guard()
    assert audit_count==152751 and seen==set(candidates)
    rows=[]
    for r in groups.values():
        for k in('procedure_aliases','product_aliases','source_records','source_artifacts','source_states','supported_n_values','forecast_rows_values'):r[k]=sorted(set(r[k]),key=str)
        r['source_contracts']=list({canonical(x):x for x in r['source_contracts']}.values())
        if r['supported_n_values']and all(float(n)==0 for n in r['supported_n_values']):r.update(status='COMPLETED_PARTIAL',reason='Forecast/score cell retained but no supported outcomes; error and accuracy remain unavailable, not zero.')
        emit(rows,r)
    # Existing observed recipes define finite weekly coverage. Unknown legacy labels
    # never generate thousands of invented scientific procedures or missing fits.
    signatures={};aggregates=set()
    covered=set()
    for r in rows:
        sig=(r['procedure_id'],r['category'],r['product_id'],r['feature_memory_policy'])
        signatures.setdefault(sig,r)
        if isinstance(r['week'],int):covered.add((*sig,r['history_regime'],r['season'],r['week']))
        elif r['week']=='ALL':
            for w in r['evaluation_weeks']:aggregates.add((*sig,r['history_regime'],r['season'],w))
    for sig,seed in signatures.items():
        p,target,product,mem=sig
        arms=('H-CURRENT',)if mem=='EVALUATION_SEASON_ONLY_NFL_INFORMATION'else CORE
        for year in range(2022,2027):
            for week in range(1,8 if year==2026 else 19):
                for arm in arms:
                    if(*sig,arm,year,week)in covered:continue
                    status='FIT_REQUIRED';dependencies=['Verified durable retention capacity and execution admission before any fitting.']
                    if(*sig,arm,year,week)in aggregates:
                        status='REPLAYABLE_NOT_RUN';reason='Retained exact-recipe full-period aggregate covers this week; replay retained forecasts for a separate weekly score before considering any refit.'
                    elif 'position-defense'in p:
                        reason='Exact D1/D2 four-observed-position-group recipe lacks this older/current weekly score; learner/information rows must be held fixed, then fitted under retained source contract.'
                    elif year==2026 and p.startswith('hgb-direct-history-controls-v1:')and mem=='EVALUATION_SEASON_ONLY_NFL_INFORMATION':
                        reason='Specifically unrun original-HGB strict-current historical cell; prepared147-origin protocol is authoritative, not completed future adapter.';dependencies.append(STRICT)
                    elif year==2022 and arm=='H-RECENT':
                        reason='Exact preceding-year2021 RECENT is unrun; qualified ordinary2021 extension needs offhost source restoration/admission; chart components remain source-blocked.';dependencies.append(E2021)
                    else:reason='No current-valid exact-recipe weekly full-system score found; inspect retained predictions and replay if present before authorizing any new fit.'
                    r=base('scientific_evaluation_cell',status,reason);r.update(procedure_id=p,category=target,season=year,week=week,history_regime=arm,product_id=product,feature_memory_policy=mem,
                        information_tier=seed['information_tier'],horizon_id=seed['horizon_id'],population='primary',evaluation_policy=seed['evaluation_policy'],dependencies=dependencies,
                        source_artifacts=seed['source_artifacts'],coverage_scope='SCIENTIFICALLY_IDENTIFIED_RECIPE_FINITE_WEEKLY_GRID',score=None)
                    emit(rows,r)
    # Fixed archives cannot supply retraining arms. Their narrow panels remain narrow.
    for i,r in enumerate(load(R0)):
        if r.get('population')!='primary':continue
        fixed=r['procedure_id'].startswith('server-retained-')
        row=base('scientific_evaluation_cell','COMPLETED_PARTIAL','Retained fixed reference or exact modern-model comparator on a qualified thirteen-game W7 subset; preserve source-specific clocks, not full W7/current season.')
        row.update(procedure_id=proc(r['procedure_id']),procedure_aliases=[r['procedure_id']],category=r['target'],season=2026,week=7,history_regime=r['history_regime'],product_id=r['product_id'],
            feature_memory_policy='ARCHIVED_COMPONENT_TRAINING_AND_FEATURE_MEMORY_UNQUALIFIED'if fixed else memory(r['procedure_id'],r),information_tier='ARCHIVED_REFERENCE_SOURCE_VINTAGE_QUALIFIED_ONLY_AS_RETAINED'if fixed else'FOOTBALL_HISTORY_ONLY_CURRENT_VINTAGE_RECONSTRUCTION',horizon_id=r.get('cutoff','INSPECT_EXACT_RETAINED_COMPARATOR_SOURCE_CONTRACT'),population='primary',
            evaluation_policy='QUALIFIED_APPEARANCE_WITHIN_ARCHIVED_REFERENCE',evaluation_panel_id=r['evaluation_panel_id'],source_records=[f'{R0}#/{i}'],source_artifacts=[R0],supported_n_values=[r['n']],forecast_rows_values=[r['forecast_rows']])
        emit(rows,row)
        for arm in CORE if fixed else():
            missing=dict(row);missing.update(history_regime=arm,status='NOT_APPLICABLE',reason='Fixed archived forecast cannot be retrained; do not invent history regime.',source_records=[f'{R0}#/{i}']);emit(rows,missing)
    for i,r in enumerate(load(NEWSEL)):
        if r['target']=='ALL'or r['cohort_id']!='ALL'or r['K']is not None:continue
        row=base('scientific_evaluation_cell','COMPLETED_PARTIAL','Statistical threshold direction on the frozen462 provider-labelled source panel; thirteen W7 games only; no authenticated price, PMF or sportsbook settlement.')
        row.update(procedure_id=r['procedure_id'],category=r['target'],season=2026,week=7,history_regime='FIXED_RETAINED_POINT_SELECTION_NOT_RETRAINABLE',product_id=r['product_id'],
            feature_memory_policy='SAVED_POINT_COMPONENT_MEMORY_UNQUALIFIED',information_tier=r['selection_evidence'],horizon_id=r['horizon_id'],population='FULL_RETAINED_PROVIDER_LABELLED_THRESHOLD_PANEL',
            evaluation_policy=r['strategy']+':SELECTED_'+r['side'],source_records=[r['record_id']],source_artifacts=[NEWSEL],supported_n_values=[r['n']],forecast_rows_values=[r['forecast_rows']]);emit(rows,row)
    for r in load(OLD):
        fixed=r['status']=='NOT_RETRAINABLE_IF_FIXED_ARCHIVE';row=base('unresolved_legacy_request_reference','NOT_APPLICABLE_FIXED_ARCHIVE_RETRAINING'if fixed else'CANONICALIZATION_AND_CONTRACT_RECONCILIATION_REQUIRED',
          'Original planning reference preserved; current2026 sources and many executable V2 results now exist. Exact original recipe/version/artifact and source/output alias reconciliation remains required; this is not a distinct scientific method or a blanket current-data access block.')
        row.update(category=r.get('target'),history_regime=r.get('history_regime'),product_id=r.get('product_id'),feature_memory_policy=r.get('feature_memory'),information_tier=r.get('information_tier'),
          source_records=[r['cell_id']],source_artifacts=[OLD],source_states=[r['status']],legacy_procedure_reference_id=r.get('procedure_reference_id'),legacy_label=r.get('procedure_label'),
          dependencies=['Resolve exact procedure identity and contract against current-valid records and original source receipts; original private artifacts may remain unavailable.']);emit(rows,row)
    for r in load(CGRID):
        row=base('fit_origin_reference',r['state'],'Retained original C origin/output opportunity state; no new fit performed and aliases/output views do not count as independent fit calls.')
        row.update(category=r.get('target'),week=r.get('week'),history_regime=r.get('history_regime'),product_id=r.get('product_id',r.get('objective')),source_records=[r['cell_id']],source_artifacts=[CGRID],source_states=[r['state']],
            source_unit=r.get('cell_unit'),source_slot=r.get('slot'),source_grid_artifact=r.get('source_artifact'),policy_id=r.get('policy_id'),alias_of=r.get('alias_of'),wave=r.get('wave'),
            reference_subtype='OUTPUT_NOT_FIT'if'not a fit'in r.get('cell_unit','')else'ORIGIN_OR_FIT_OPPORTUNITY_NOT_A_NEW_FIT');emit(rows,row)
    for i,r in enumerate(load(STRICT)['grid']):
        row=base('fit_origin_reference','PREPARED_NOT_FITTED_RETENTION_BLOCKED','Specific original-HGB strict-current historical runner prepared; no147-fit execution, not a rerun of completed rolling equivalents.')
        row.update(procedure_id=r['procedure_id'],category=r['target'],season=2026,week=r['week'],history_regime=r['history_regime'],product_id=r['objective'],feature_memory_policy='EVALUATION_SEASON_ONLY_NFL_INFORMATION',
            source_records=[f'{STRICT}#/grid/{i}'],source_artifacts=[STRICT],dependencies=['Verified whole-archive restoration and capacity; sole-worker execution registration and independent prefit admission.']);emit(rows,row)
    reuse=load(REUSE);counts=collections.Counter((r['phase'],r['action'])for r in reuse)
    for i,r in enumerate(load(SCHEDULED)):
        row=base('fit_origin_reference','PREPARED_SELECTIVE_REUSE_OR_REFIT_RETENTION_BLOCKED','Scheduled-four-team-game alternative; absent-group missingness retained; original four-observed-group procedure unchanged. Selective plan, not768 new fits.')
        row.update(procedure_id=r['procedure_id'],category=r['target'],season=2026,week=r['week'],history_regime=hist(r['policy_id']),feature_memory_policy=r['policy_id'],source_records=[f'{SCHEDULED}#/{i}'],source_artifacts=[SCHEDULED,REUSE],
            dependencies=['Retain/reuse unchanged models; refit only affected training cells after restoration/admission.','New future capture requires actual open game deadlines and owner coordination.']);emit(rows,row)
    recent=load('reports/continuation-20261030c/season-2022-v2/GRID_STATUS.json')
    extension_count=collections.Counter()
    for r in recent:
        match=re.fullmatch(r'W(\d+)-(.+)-H-RECENT-COMMON-(.+)',r['slot'])
        if not match:continue
        week,target,method=int(match[1]),match[2],match[3];chart=target=='nick-chart-ppr-v1';extension_count['chart'if chart else'ordinary']+=1
        row=base('fit_origin_reference','SOURCE_BLOCKED'if chart else'STAGED_EXACT_2021_RECENT_RETENTION_AND_ADMISSION_REQUIRED',
            '2021 chart rare-component/zero/parity source not qualified.'if chart else'Qualified ordinary2021 source extension staged; full source offhost restoration and finite execution admission required; old2022floor proxy preserved.')
        row.update(category=target,season=2022,week=week,history_regime='H-RECENT',product_id='SOURCE_RECIPE_OUTPUTS_REQUIRE_DECLARED_MAPPING',feature_memory_policy='E1_RECENT2021_COMMON_2021_MEMORY',
            source_records=[r['slot']],source_artifacts=[E2021,'reports/continuation-20261030c/season-2022-v2/GRID_STATUS.json'],source_recipe_slot=method,dependencies=[E2021]);emit(rows,row)
    assert extension_count==dict(ordinary=1098,chart=54)
    for r in load(PATHWAYS):
        row=base('requested_pathway',r['status'],'Original requested pathway accounting; completed related work does not authenticate an unrun remaining mechanism or a new scientific method.')
        row.update(category=r['target'],source_records=[r['pathway_id']],source_artifacts=[PATHWAYS],source_states=[r['new_fit_state']],requested_mechanism=r['requested_mechanism'],remaining_mechanism=r['exact_remaining_mechanism'],
          dependencies=[r['additional_prerequisites'],r['new_fit_state']],reference_artifacts=r['reference_artifacts']);emit(rows,row)
    guard();OUT.mkdir(parents=True)
    fields=list(dict.fromkeys(k for r in rows for k in r))
    # Column encoding preserves all values and exact CSV identities while avoiding
    # repeated long keys crossing GitHub's100MiB single-file limit.
    (OUT/'COVERAGE_GRID.json').write_bytes(canonical(dict(schema='v2-source-bound-coverage-column-rows-v1',columns=fields,rows=[[r.get(k)for k in fields]for r in rows]))+b'\n')
    with(OUT/'COVERAGE_GRID.csv').open('x',newline='')as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for r in rows:w.writerow({k:json.dumps(v,separators=(',',':'))if isinstance(v,(list,dict))else v for k,v in r.items()})
    counts=collections.Counter((r['unit_kind'],r['status'])for r in rows)
    summary=dict(state='SOURCE_BOUND_COVERAGE_PROJECTION_NO_FITS_OR_GRADES',source_manifests_sha256=sources,current_valid_evaluation_views=124630,all_audit_evaluation_and_software_views=152751,
      matched_fullsystem_baseline_record_ids=len(candidates),grouped_observed_scientific_cells=len(groups),rows=len(rows),unit_status_counts=[dict(unit_kind=k[0],status=k[1],rows=v)for k,v in sorted(counts.items())],
      original_grid_reference_rows=5408,retained_C_origin_or_output_rows=25277,original_HGB_strict_prepared=147,scheduled_logical_opportunities=768,scheduled_selective_reuse_action_counts=[dict(phase=k[0],action=k[1],n=v)for k,v in sorted(collections.Counter((r['phase'],r['action'])for r in reuse).items())],
      exact_2021_RECENT_extension=dict(extension_count),requested_pathways=60,new_fits=0,new_forecasts=0,new_grades=0,
      wall_seconds=time.monotonic()-begin,max_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,code_sha256=sha(Path(__file__)),grid_json_sha256=sha(OUT/'COVERAGE_GRID.json'),grid_csv_sha256=sha(OUT/'COVERAGE_GRID.csv'),
      canonicalization_boundary='Known valid scientific recipes only generate finite missing weekly cells. Legacy5408 references include5007LREF cells plus earlier plans/pathway references and do not identify1669 distinct scientific methods. No completion percentage or lifetime-method count.',
      proper_score_boundary='Retained football-law CRPS/Brier is not actual-offered-threshold probability performance. Statistical selection crossing remains separate from priced/book-settled return.')
    (OUT/'COVERAGE_MANIFEST.json').write_text(json.dumps(summary,indent=2)+'\n')
    lines=['# Current coverage, finite cells and unresolved references','','This is a source-bound projection of valid numerical coverage, the bounded462-threshold selection panel and retained execution/request references. It changes no scientific result, grid source, fit, forecast, capture or production state. Missing scores are null, not zero. The old grids remain immutable.','','| Unit | Status | Rows |','|---|---|---:|']
    lines +=[f'| {u} | {s} | {n:,} |'for(u,s),n in sorted(counts.items())]
    lines+=['','The124,630 current-valid record IDs select canonical score versions from the145,219-record numerical ancestor; the152,751-view all-audit index also retains later prop score views, supersessions and software receipts. Only primary/ALL/full-system/no-cohort known numerical recipes establish scientific weekly coverage. Products, histories, populations, information and source panels remain separate; grouped source IDs are references, not additional samples. All missing weekly cells are restricted to scientifically identified recipes. Finite grids cover2022–2025 REG Weeks1–18 and fixed2026 REG Weeks1–7. Source-limited2022 RECENT proxy scores remain partial, with separately staged2021 ordinary and chart requirements.','','Empirical controls use per-arm target-outcome history with no predictor-feature memory. Their observed/position cohort is retrospective: do not call their H-CURRENT product a full ex-ante strict-current-information system. Rolling empirical policy_id ends EMPIRICAL and retained input information_policy is ARM_LIMITED_TARGET_HISTORY; shared_subgroups calls it PER-ARM-OUTCOME-HISTORY. This differs from the common2022-memory learner feature vector. Original settings and startup/fallback qualifications remain in linked source protocols.','','D1/D2 older-season exact four-observed-position-group cells require new fits after durable recovery, rather than substitution by another defense/window procedure. The scheduled-four-team-game alternative retains its separate768 logical opportunities and selective reuse/refit plan. Original strict-HGB147 retrospective cells remain prepared, not fitted. Fixed archived R0/provider forecasts have not-applicable retraining arms; modern-model comparators in the same reference score source retain their original trainable histories. Source cuts, feature memory and exact contracts must be checked through each linked source record before comparison.','','The25,277 C records include aliases, startup no-fit cells and648 A/B/C output cells explicitly described as not fits. Their original states are preserved under fit-origin-reference units; they are not25,277 actual fits. New candidate fits and these old origin references must never be summed. The5,408 old planning references are not5,408 executable methods: exact-label canonicalization and original contract/artifact reconciliation remain incomplete. Existing2026 data and executed reconstructions mean their stale blanket data-inaccessible wording is no longer the current status. Unknown private originals remain a narrower claim-specific limitation.','','The60 requested pathways each retain completed-related-work and exact remaining dependencies. No aliases, seeds, output views or references become distinct learners. No denominator supports a global completion percentage. Football-law distribution scores do not establish actual-offered-line probability accuracy, and provider-labelled statistical direction does not establish sportsbook settlement, price-aware returns or full-season selection winners.','','JSON is column-encoded: reconstruct a row as dict(zip(columns, values)) for each entry in rows. CSV contains identical cell identities and values. The invalidated first generated projection is retained losslessly in coverage-draft-v1 with its findings and source snapshot.','','[Machine-readable CSV](COVERAGE_GRID.csv) · [JSON](COVERAGE_GRID.json) · [source hashes, resource receipt and counts](COVERAGE_MANIFEST.json).']
    (OUT/'README.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({k:summary[k]for k in('rows','grouped_observed_scientific_cells','matched_fullsystem_baseline_record_ids','wall_seconds','max_RSS_bytes','new_fits','new_grades')}))


if __name__=='__main__':main()
