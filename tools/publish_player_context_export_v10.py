"""Extend B's existing export index with exact immutable context bindings."""
import hashlib,json,subprocess
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE='reports/player-context-matchup-01/B/'
DATA='3ad682cf86912f025e5a1699c8a396f3d9065222'
META='f3849b405d5f2cfb9a8fcb24d6302aa3a5bce9dc'

def sha(b):return hashlib.sha256(b).hexdigest()
def main():
    path=ROOT/'reports/abc-championship/EXPORT_INDEX.json';old=path.read_bytes();index=json.loads(old)
    if index['schema_version']!='B-ABC-EXPORT-INDEX-v9.1':raise ValueError('Unexpected existing export version; inspect newer legitimate work')
    data=[
        'qb-wave-v1/FROZEN_PROTOCOL.json','qb-wave-v1/FROZEN_SCOPE_AMENDMENT_V2.json','qb-wave-v1/QB_OPPORTUNITY_SCOPE_AMENDMENT_V3.json','qb-wave-v1/SELECTED_EARLIER_CONFIG.json','qb-wave-v1/RUN_RECEIPT.json',
        'qb-charting-wave-v1/FROZEN_PROTOCOL.json','qb-charting-wave-v1/RUN_RECEIPT.json','qb-charting-wave-v1/SOURCE_DENOMINATOR_AND_CLOCK_SCOPE_V2.json',
        'source-fields-v3/DERIVED_QB_GAME_INPUTS.json.gz','source-fields-v3/FTN_DERIVED_QB_GAME_INPUTS.json.gz','source-fields-v3/SOURCE_FIELD_WEEK_COVERAGE.json','source-fields-v3/TARGET_RECONCILIATION.json',
        'qb-scores-v1/SCORES.json','qb-scores-v1/SOURCE_PERIOD_HISTORY_METADATA_ANNOTATIONS_V2.json','qb-scores-v1/RETAINED_CONTROL_EXECUTION_BINDING_V1.json',
        'qb-charting-scores-v1/SCORES.json','component-and-controls-v1/SCORES.json','INDEX_BOUND_PAIRED_ANALYSIS_V2.json','PAIRED_PROJECTION_CORRECTION_V2.json',
        'results-index-v1/INDEX_MANIFEST.json','paired-analysis-index-v2/ANALYSIS_MANIFEST.json','ALL_METHOD_SIDE_TABLE.json','ALL_METHOD_SIDE_TABLE.csv','TOPK_CUMULATIVE_COUNT_PROJECTION.json',
        'PRODUCT_QUALIFICATION.json','POLICY_QUALIFICATION_COUNTS.json','SEASON_SUMMARIES_V1.json','TASKS_V2.json','OWNER_CAPTURE_AND_SERVED_STATUS_V1.json','FULL_ARTIFACT_MANIFEST_V1.json']
    metadata=['B_PLAYER_CONTEXT_MATCHUP_REPORT.md','DIRECT_CATEGORY_TABLES.md','CURRENT_COVERAGE_SCOPE_V3.json','CURRENT_EXPORT_READER_REQUIREMENTS_V1.json',
        'DATA_LICENSES_AND_ATTRIBUTION_V2.md','FULL_ARTIFACT_MANIFEST_V2.json','FULL_GITHUB_RESTORATION_RECEIPT_V2.json','FULL_READBACK_MANIFEST_FAILURE_V1.json',
        'CURRENT_METADATA_ADDENDUM_MANIFEST_V1.json','METADATA_CLOSURE_CHECKS_V2.json','independent/FINAL_SCOPED_COVERAGE_AND_RESTORATION_REVIEW_V2.json']
    jobs=[(DATA,BASE+p,'B_CONTEXT_FROZEN_SOURCE_RECIPE_FORECAST_OR_AGGREGATE')for p in data]+[(META,BASE+p,'B_CONTEXT_CURRENT_QUALIFIED_METADATA_AND_RECOVERY')for p in metadata]
    jobs += [(DATA,p,'B_CONTEXT_CODE_AND_CONFIG')for p in ['nfl_v2/player_context_matchup.py','nfl_v2/player_context_typed_adapter_v2.py','tools/run_player_context_wave.py','tools/run_qb_charting_context_wave.py','tools/score_player_context_wave.py','tools/score_qb_charting_context_wave.py','tools/supplement_qb_context_wave.py']]
    jobs += [(META,p,'B_CONTEXT_CURRENT_READER_OR_DISCOVERY')for p in ['nfl_v2/context_scope_metadata.py','registries/CURRENT_RESULTS_INDEX.json','registries/RESULT_ARTIFACTS.json','registries/ANALYSIS_ARTIFACTS.json']]
    new=[]
    for ref,p,kind in jobs:
        body=subprocess.check_output(['git','show',ref+':'+p],cwd=ROOT)
        new.append(dict(artifact_id='B-CONTEXT-EXPORT-'+sha((ref+':'+p).encode())[:16],producer_commit=ref,path=p,
            retrieval_url='https://raw.githubusercontent.com/NickNicky19/NFL-forecasting-V2/'+ref+'/'+p,sha256=sha(body),bytes=len(body),kind=kind,
            readback_verified=True,rights='Source-specificCC-BY4/CC-BY-SA4newpublicderivatives; projectcode/aggregatepermissions. See bothboundlicense pages; no restrictedoffers/legacyweights.',
            retention='IMMUTABLE_GITHUB_BYTES_COMPLETE_FRESH_RESTORATION_PLUS_CURRENT_METADATA_READBACK',admission='B_VALIDATED_NEW_C_RECEIPT_AND_ADMISSION_NOT_OBSERVED'))
    assert len({r['artifact_id']for r in new})==len(new)
    index['schema_version']='B-ABC-EXPORT-INDEX-v10';index['at_utc']=datetime.now(timezone.utc).isoformat();index['exports']+=new
    index['previous_index']=dict(producer_commit=DATA,path=BASE+'PREVIOUS_EXPORT_INDEX_V9_1.json',sha256=sha(old),bytes=len(old),preserved_unchanged=True)
    index['canonical_state']='C_REMAINS_COORDINATOR;NEW_B_CONTEXT_OWNER_LOCAL_VALIDATED_NOT_C_ADMITTED'
    index['pinned_C']['current_verified_pointer_ref']='1bdba21442d7c48b93e0779e7d52346efdf7308d'
    index['next_action']='C intake exact new Bcontext manifests/qualifiedviews; preserve source-specificmask/horizon/permissions. Sourceowner qualify missing earlier and annualQBactualthresholds or permittedowner-localscoring. A/Ccontinueownedcontexttasks. Retainedoriginalowneraloneadmit/capture/release; noBdispatch.'
    index['player_context_matchup']=dict(assignment='PLAYER-CONTEXT-MATCHUP-01 v1',data_commit=DATA,current_metadata_commit=META,new_export_artifacts=len(new),
        completed_numerical_origins=dict(season2025=list(range(1,19)),season2026=list(range(1,9))),numerical_QB_player_games=dict(season2025=664,season2026=277),
        new_method_target_week_cells=260,forecast_products='Mean/lower-median/count-law views, not additional independent learner families.',
        actual_offers=dict(season=2026,weeks=[5,6,7,8],pass_cmp=112,pass_att=112,games=56,original_picks_recovered=0,new_authentic_offer_weeks=0,missing_current_weeks=[1,2,3,4],missing_Week5_games=1,historical_offer_years_not_added=[2022,2023,2024,2025]),
        best_new_completion_direction=dict(procedure='B-player-context-matchup-01-v1:E3',policy='P2_STATISTICAL_LAW',Over=[17,13],Under=[41,41],Combined=[58,54],
            E0_correct=49,saved_adjusted_correct=58,always_Over_correct=58,earlier_prevalence_correct=59,n=112),
        adverse=dict(all_new_threshold_Briers_worse_than_neutral_025=True,FTN_F2_direction_ties_E1_54_of112=True,
            E3_rolling_combined_top6=[8,16,24],P90_selected=0,P90_accuracy=None),
        five_week='Exactnewpointproducts have26scoredseasonweeks; newactual-linepoliciesatmost4weeks, P90zero decidedweeks. No primaryselection/probability/TopKqualification ornewfuturewaitingperiod.',
        current_reader_requirements=BASE+'CURRENT_EXPORT_READER_REQUIREMENTS_V1.json',source_period_history_overlay=BASE+'qb-scores-v1/SOURCE_PERIOD_HISTORY_METADATA_ANNOTATIONS_V2.json',
        current_scope_overlay=BASE+'CURRENT_COVERAGE_SCOPE_V3.json',current_coverage_reader='nfl_v2/context_scope_metadata.py:qualified_rows',
        metadata_effect='W7template/historyhorizon and outside-scopeversusfailure fields qualified; sourcepredictions/grades/errors/countsunchanged. MandatoryoverlayscarryexactSHA/recordIDbindings.',
        recovery=dict(required_public_files=1139,required_public_bytes=50046384,complete_restoration_receipt=BASE+'FULL_GITHUB_RESTORATION_RECEIPT_V2.json',
            previous1141manifest_failure='Two ignoredPythoncaches were notscientific dependencies; originalmanifest/failure preserved; everyrequiredtrackedfile independently rehashed.',
            original_private_recovery='UNCHANGED38MISSINGPARTS796917760BYTES;147strictHGB/736olderexactD1D2cells remaingoverned.'),
        new_fit_counts=dict(total945=945,earlier2024tuning=48,base_including_tuning=893,FTN_extension=52),new_original_forecasts=0,new_original_selections=0,
        public_lane='Newlicensedderivedinputs/typedJSONmodels/forecasts genuinely publicandrecoverable; nooldrestrictedarchives or protectedofferrows moved.',
        independently_verified='All4852newcanonicalviews,1130currentnewscientificpairs,9410frozenpredictionrecords/sourcedcontexts andrepresentativetypedmodels; checksare notnewNFLobservations.',
        paired_counts=dict(prior_preserved=19576,new_scientific=1130,total=20706,raw_identical_method_diagonal_retained_outside_current_scientific_projection=1),
        live='Ownerreference1561rows/14games,6Git/servedpairs; overlaydisabled0researchrows,24TopPicks12O12U with1priorfrozenproof. No Bmodel admitted/published/served.',
        remaining='AllothercategorycontextworkunderA/B/Cowners; earlierCMP/ATTquote/sourcegaps;2022-24newcontextneeds earlier-onlyconfiguration/startup. Existingchampionshipnotcomplete.')
    for p in index['periods']:
        p['previous_local_status']=p['local_status'];pid=p['period_id']
        if pid=='E1':p['local_status']='NewexactQBrecipes2026W1-8numericalcomplete;actual-lineW5-8only. PriorC2-3othercategoryandoriginalpanelsremainseparate;notfulleightweekactualpropchampionship.'
        elif pid=='E2':p['local_status']='NewexactQB2025W1-8originscompletedwithinfull2025run;allweeklyerrorsretained. No new2025actualoffers.'
        elif pid=='E3':p['local_status']='Oldvalid2022-24testsreused;newQBcontextnotrunbeforeits2024configurationselection. Earlier-onlytuning/startupneeded; legacyD1D2/HGBrecoveryseparate.'
        elif pid=='E4':p['local_status']='NewexactQB2025fullREGW1-18completed; othernewcontextyears/categoriesincomplete. Oldrolling2022-25testsunchanged; noactual-lineclaimfromnumeric.'
        elif pid in('E5','E6','E7'):p['local_status']='Fullrequestedcommonseasonsetnotcomplete. Newexplicit2025full+2026W1-8numericmicro/equal-yearprojections arepartial andnotpooledactualprops; sourceweeklyresultspermitCcommonperiodaggregation.'
        elif pid=='E8':p['local_status']='No newBoriginalforecast/pick; ownerreferencecapture/servedreadbackverifiedseparately. Newmethodgenuinefutureconfirmationnotbackfilled.'
    # Receipt is envelope metadata; C resolves it at the same immutable commit
    # from which it retrieves this index, with an exact content hash.
    companion=ROOT/BASE/'CURRENT_METADATA_GITHUB_READBACK_RECEIPT_V1.json'
    index['player_context_matchup']['envelope_readback_receipt']=dict(path=str(companion.relative_to(ROOT)),sha256=sha(companion.read_bytes()),ref_resolution='Same immutablecommit as thisexportindex; not a newforecastartifact.')
    path.write_text(json.dumps(index,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(new_artifacts=len(new),total_exports=len(index['exports']),data_commit=DATA,metadata_commit=META)))
if __name__=='__main__':main()
