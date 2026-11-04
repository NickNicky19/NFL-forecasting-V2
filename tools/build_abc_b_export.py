"""Public-safe B export discovery; verify exact committed bytes, not working copies."""
import hashlib,json,subprocess,urllib.request,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def committed_export(ref,path,kind):
 expected=subprocess.check_output(['git','show',ref+':'+path],cwd=ROOT)
 url=f'https://raw.githubusercontent.com/NickNicky19/NFL-forecasting-V2/{ref}/{path}'
 with urllib.request.urlopen(url,timeout=60)as response:body=response.read()
 if body!=expected:raise ValueError('Committed byte readback mismatch:'+path)
 return dict(artifact_id='B-EXPORT-'+hashlib.sha256(path.encode()).hexdigest()[:16],producer_commit=ref,path=path,retrieval_url=url,sha256=hashlib.sha256(body).hexdigest(),bytes=len(body),kind=kind,readback_verified=True,rights='PUBLIC_AGGREGATES_CODE_OR_SAFE_C_SOURCE_IDS_ONLY;NO_B_RESTRICTED_ROWS_OR_MODELS',retention='IMMUTABLE_GITHUB_EXACT_BYTES_VERIFIED',admission='NOT_C_ADMITTED')

def continuation(ref):
 """Versioned amendment to the existing index; retain immutable old exports."""
 base='reports/abc-championship/';wave=base+'continuation-20261103-v4/'
 prior=json.loads(subprocess.check_output(['git','show',ref+':'+base+'EXPORT_INDEX_7c0690bf_V2.json'],cwd=ROOT))
 paths=[(wave+'PINNED_C_PROTOCOL_AND_B_ACKNOWLEDGEMENT.json','C_protocol_pin_and_B_acknowledgement'),
  (base+'continuation-20261103-v2/SCORES.json','B_D1_D2_ordered_actual_line_saved_points'),
  (base+'continuation-20261103-v3/SCORES.json','B_additional_actual_line_saved_points'),
  (wave+'SCORES.json','B_restored_GLM_law_P2_and_proper_probability_scores'),
  (wave+'numerical-offer-panel-v1/SCORES.json','same_offer_native_errors_and_precision'),
  (wave+'OWNER_LOCAL_MASK_MEMBERSHIP.json.gz','public_safe_C_opportunity_mask_members'),
  (wave+'OWNER_LOCAL_VERIFICATION_LIMITS.json','owner_local_reproducibility_limits'),
  (wave+'PROBABILITY_BASELINES.json','matched_probability_control_scores'),
  (wave+'B_PERIOD_COMPARISON_REPORT.md','local_readable_period_comparison'),
  (wave+'B_EXACT_WEEK_GAP_OVERLAY.csv','overlay_on_established_exact_B_roster'),
  (wave+'SESSION_SOURCE_WEEK_COVERAGE.csv','A_B_C_source_scope_with_ownership'),
  (wave+'TASK_LEDGER.json','single_owner_missing_work_and_dependencies'),
  (wave+'REC_YD_C02_OWNER_REVIEW_PACKAGE.json','prepared_not_admitted_category_package'),
  (wave+'results-index-v1/INDEX_MANIFEST.json','current_permanent_accuracy_error_index'),
  (base+'continuation-20261103-v1/original-selected-under-control-v1/SCORES.json','original_W8_selected_pool_constant_control'),
  (base+'continuation-20261103-v1/independent/INDEPENDENT_RETAINED_RECORD_VERIFICATION_V1.json','independent_C_and_B_original_arithmetic'),
  (base+'continuation-20261103-v1/independent/INDEPENDENT_NEW_V2_POSTQUALIFICATION_VERIFICATION.json','independent_B_D1_D2_joins_and_counts'),
  (base+'continuation-20261103-v1/independent/INDEPENDENT_NEW_V3_VERIFICATION.json','independent_other_B_saved_points'),
  (base+'continuation-20261103-v1/independent/INDEPENDENT_EXACT_LINE_LAWS_V4.json','independent_analytic_law_and_baseline_math'),
  (base+'continuation-20261103-v1/independent/INDEPENDENT_FINAL_NUMERIC_AND_MASKS_V1.json','independent_precision_and_public_masks'),
  (base+'continuation-20261103-v1/independent/INDEPENDENT_OWNER_OPERATION_FINAL_QUALIFICATION_V3.json','independent_owner_W9_payload_readback')]
 exports=prior['exports']+[committed_export(ref,path,kind)for path,kind in paths]
 value=dict(prior,schema_version='B-ABC-EXPORT-INDEX-v3.0',at_utc=datetime.now(timezone.utc).isoformat(),
  canonical_state='C_PROTOCOL_PINNED_B_OWNER_LOCAL_OUTPUTS_NOT_C_ADMITTED',
  pinned_C=dict(repository='NickNicky19/NFL-forecasting-NGS-C',ref='ac9cb1000bcb8f1197505b68ccfe246ea61bbafe',protocol_id='ABC-ACTUAL-PROP-CHAMPIONSHIP-v2-C-1',protocol_sha256='fa19581487519a854948269bc1ce328cbbcdc734afee2464f1ff778d1ff241a1',scorer_sha256='2ba450f91bb5fac869ce3adde031099390ec70408a91204653869032b49b2bce',schema_sha256='0ba0755f94889a33fb7c02efbf4cc9e414b9a733fc3bc7f1357faba1c294f2f4'),
  exports=exports,previous_index=dict(ref='7c0690bfb564db5481cc27a00a45e7f4311b1f70',path=base+'EXPORT_INDEX.json',preserved_copy=base+'EXPORT_INDEX_7c0690bf_V2.json'),
  adoption_qualification='B normalized chatadoption860a... and C executablefa1958... are different documents. Semantic agreement verified; no byte-for-byte transcript adoption claim. Prior404records historical only.',
  actual_new_scope=dict(period_id='E1',requested_weeks=list(range(1,9)),actual_weeks=[2,3],source='C_PINNACLE_CORRECTED_v7.1_AT_ac9cb100',source_offers=968,source_games=32,source_player_games=469,point_recipe_category_history_product_cells=212,law_category_history_cells=16,scope='B_OWNER_LOCAL_NOT_C_ADMITTED;4categoriesonly; source/participantpopulation differences explicit',origin_forecasts='B',offers_outcomes_controls='C',A_predictions_received_or_scored=False),
  owner_local_contract=dict(producer_repository='NickNicky19/NFL-forecasting-V2',producer_commit=ref,procedure_id='EXACT_NAMESPACED_IDS_PER_SCORE_ROW',period_id='E1_PARTIAL_W2_W3',rights_analysis='QUALIFIED_PINNED_C_REVIEW_AND_EXISTING_B_SOURCE_CONTRACTS',rights_export='PUBLIC_AGGREGATES_CODE_SAFE_C_SOURCE_IDS_ONLY;B_ROWS_REMAIN_RESTRICTED_OWNER_LOCAL',rights_GitHub_retention='PUBLIC_SAFE_OUTPUTS_ONLY',rights_publication='PERMITTED_AGGREGATES_NOT_PRIVATE_PREDICTION_ROWS',contracts='OfficialfullgameOT;signedyards;exactCofferID/GSIS/game/role/labelversion; BprimaryQBpassing,QB/RBrushing,RB/WR/TEreceiving',history='ExactperrowCURRENT/strictCURRENT/RECENT/MULTI; no merged arm',feature_memory='Exactperrowcommon2022memoryorstrictCURRENT;empiricalarmtargethistoryseparate',priors='Originalsamearmrole/global/fixedstartup; no newlyfittedprior',calibration_history='No newcalibration; existingprocedureunchanged',update_rule='Originalhistoricalweeklyfit/per-gamequery; no currentmodel substituting pastorigin',output_type='Typedretainedpoints and separatelyrestoredcompleteparametricGLMlaws',selection_rule='P1unroundedpoint versusline;P2exactlineconditionalappearance; noEVorprobabilityfrompoint',horizon='Kickoffreconstructionversuslast-recordedpre-kickclose; timingunverifieddiagnostic',availability_tier='CURRENT_REVISED_SOURCE_7DAY_RECONSTRUCTION_NOT_AUTHENTIC_ASOF',fallback='Ownsourcebehavior; technicalunavailable not confidenceabstention; unknownparticipation notzero',actual_rows_games_weeks='968Csourceoffers,32games,469player-games,W2-W3; eachprocedureowncoverage/decidedmaskpublished; viewsnotNFLobservations',missing_dependencies='Cintake/ownerlocaladmission; otherweeks/categories/historicaloffers; exactlaw/member and candidate-specificretentionrequirements'),
  restricted_evidence=dict(public_row_transfer_allowed=False,private_locator=None,retention='ExistingBapprovedstoreprotected;newboundedderivativeslocalreadbackonly; nooffhostclaim',owner_local_option='Executed againstpinnedCoffer/outcomeIDs; safemaskmembers and deterministicoutputsavailable; code/chunkhashbindings and independentlocalarithmeticretained',verification_limit='Ccanverifyitscontrolcountsfrompublicmasks. Publicaggregatesalone do not letC independentlyrecomputeBprivatecandidateforecasts; admissionmustretainthislimit or identify specificpermittedlocalchallenge/export.',dependencies='SpecificBsource/model/rowpermission and recovery; notblanketgradingstop; no newsharedprivatearchive'),
  delivery=dict(discovery_file_published=True,C_received='UNVERIFIED',C_acknowledged='UNVERIFIED',C_validated='UNVERIFIED',C_admitted='UNVERIFIED',external_messages=0),
  next_action='C consume this exact immutableexportindex and boundnewBfiles/masks; record perartifact received/validated/admitted/rejected or exactdependency. Bdoesnotassumeacceptance. Aannualownerlocal replay/402byteallocation belongsA; no duplicatefits.',
  budgets=dict(new_fits=0,new_model_coefficient_inference=0,new_issued_forecasts=0,restored_threshold_CDF_queries=3668),production_changes=False)
 for p in value['periods']:
  p['common_status']='C_PROTOCOL_PINNED;B_OWNER_LOCAL_PARTIAL_NOT_ADMITTED'
  if p['period_id']=='E1':p['local_status']='New B/C W2-W3fourcategoryactual-line diagnostics; priorB W5-W8source-specificpanels retainedseparately; W1/W4/missingW5game gaps. NotfullW1-W8or original8weekrecord.'
  elif p['period_id']in ['E2','E3','E4']:p['local_status']+='; reusedno newseasonalfits or actual-lineyears inthiswave.'
 target=ROOT/base/'EXPORT_INDEX.json';target.write_text(json.dumps(value,indent=2)+'\n')
 print(json.dumps(dict(schema=value['schema_version'],new_readbacks=len(paths),all_exports=len(exports),producer_commit=ref,C_admission='UNVERIFIED_NOT_CLAIMED')))
def run():
 current=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();prior='08fa2ea888620f5587ed5618dfc0e239be82a664'
 paths=[(current,'reports/abc-championship/ADOPTED_ASSIGNMENT_V2.json','adoption'),(current,'reports/abc-championship/local-week8-final-v1/SCORES.json','local_direction_results'),(current,'reports/abc-championship/local-week8-final-v1/independent/INDEPENDENT_LOCAL_FINAL_REVIEW_V1.json','independent_local_review'),(prior,'reports/completion-20261031g/roster/finite-v2/FINITE_IMPLEMENTED_PROCEDURE_ROSTER.json','existing_method_roster'),(prior,'reports/completion-20261031g/roster/finite-v2/FINITE_RECIPE_CATEGORY_PERIOD_PRODUCT_GRID.json','existing_exact_cell_grid'),(prior,'registries/CURRENT_RESULTS_INDEX.json','prior_index_pointer')]
 exports=[]
 for ref,path,kind in paths:
  expected=subprocess.check_output(['git','show',ref+':'+path],cwd=ROOT);url=f'https://raw.githubusercontent.com/NickNicky19/NFL-forecasting-V2/{ref}/{path}'
  with urllib.request.urlopen(url,timeout=60)as r:body=r.read()
  if body!=expected:raise ValueError('Committed byte readback mismatch:'+path)
  exports.append(dict(artifact_id='B-EXPORT-'+hashlib.sha256(path.encode()).hexdigest()[:16],producer_commit=ref,path=path,retrieval_url=url,sha256=hashlib.sha256(body).hexdigest(),bytes=len(body),kind=kind,readback_verified=True,rights='PUBLIC_AGGREGATES_OR_CODE_ONLY_NOT_RAW_RESTRICTED_ROWS_OR_MODELS',retention='IMMUTABLE_GITHUB_EXACT_BYTES_VERIFIED',admission='NOT_C_ADMITTED'))
 value=dict(schema_version='B-ABC-EXPORT-INDEX-v2.0',at_utc=datetime.now(timezone.utc).isoformat(),session='B',repository='NickNicky19/NFL-forecasting-V2',canonical_owner='C:NickNicky19/NFL-forecasting-NGS-C',canonical_discovery='reports/abc-championship/CURRENT_PROTOCOL.json in C',canonical_state='NOT_LOCATED_NOT_PINNED_NO_PARITY',adopted_document=exports[0],exports=exports,
  source_identity='Website/reference origin stays originalrepository/producer; B auditing it is not a new independentlearner. FullIDs/config/history/featurememory/fallback/update contracts via existing18mechanismroster, aliases,3205cellgrid andlocalleaderbindings; not onlyMAEfinalists.',
  periods=[dict(period_id=p,common_status='AWAIT_C_BOUND_MASK_AND_CONTRACT',local_status=s)for p,s in [('E1','PARTIAL_W1-8: localW8all14gamesfinal,13gameT90commoncore; earlieroriginalW5-7covers42/43games,W1-4andoneW5missing. Notoriginaleightweekrecord.'),('E2','2025W1-8oldnumericalevidenceexists; actualoffers/exactrecipes source-specific'),('E3','2022-24W1-8numericalevidenceexists;2021RECENT andexactD1D2gaps'),('E4','Supported2022-25oldrollingnumericalresults, notproofactual-lineperformance'),('E5','NOT_POOLED_NO_MATCHED_COMMON_SEASON_SET'),('E6','NOT_POOLED_NO_DOUBLE_COUNTING'),('E7','NOT_COMPUTED_SAME_SEASON_SET_WEIGHTS_REQUIRED'),('E8','GENUINE_FUTURE_CAPTURE_VERSIONS_SEPARATE_NO_NEW_CAPTURE')]],
  restricted_evidence=dict(public_row_transfer_allowed=False,private_locator=None,retention='EXISTING_APPROVED_B_ROUTE_ONLY; NEW_BOUNDED_ROWS_LOCAL_READBACK_OFFHOST_PENDING',owner_local_option='After C publishes boundopportunity/scorer/schema and permittedanalysis contract, B assesses ownerlocal scoring. No newsharedprivatearchive or publicrawmigration.',verification_limit='Publicaggregates alone cannot establish pairedcross-session superiority.',dependencies='Ccommoncontract; specificrowpermission or ownerlocaladmission; existingBsource/model/recovery requirements; no waiverofCGitHub-onlyrule'),
  delivery=dict(discovery_file_published=True,C_received=False,C_acknowledged=False,C_validated=False,C_admitted=False,external_messages=0),next_action='C read this existing EXPORT_INDEX and publish its canonical pointer/equivalent mapping with bound scorer/schema/roster/opportunity/outcomes and compliant admission route. B verifies actual bytes before commonclaims.',budgets=dict(new_fits=0,new_inference=0,new_forecasts=0),production_changes=False,
  readback_attempt_note='An initial verification compared an old committed pointer to its newer working copy and stopped before index creation. Corrected verifier compares git-show bytes of each exact producer commit; no data/score change.')
 target=ROOT/'reports/abc-championship/EXPORT_INDEX.json'
 with target.open('x')as f:json.dump(value,f,indent=2);f.write('\n')
 print(json.dumps(dict(exports=len(exports),adoption_sha256=exports[0]['sha256'],producer=current)))
def period_amendment(ref):
 """Append published period artifacts and qualify newer C admissions."""
 ref=subprocess.check_output(['git','rev-parse',ref],cwd=ROOT,text=True).strip()
 base='reports/abc-championship/';wave=base+'continuation-20261103-v4/';weekly=base+'weekly-point-partition-20261104-v1/'
 target=ROOT/base/'EXPORT_INDEX.json';prior=json.loads(target.read_bytes())
 if prior['schema_version']!='B-ABC-EXPORT-INDEX-v3.0':raise ValueError('Expected retained v3 index')
 oldcopy=ROOT/base/'EXPORT_INDEX_61b2424a_V3.json'
 if oldcopy.exists():assert oldcopy.read_bytes()==target.read_bytes()
 else:oldcopy.write_bytes(target.read_bytes())
 paths=[(wave+'B_PERIOD_COMPARISON_REPORT.md','updated_B_period_report'),(wave+'TASK_LEDGER.json','current_ownership_and_dependencies'),(wave+'LATEST_HANDOFF_ADMISSION_QUALIFICATION_V2.json','current_C_A_readback_and_admission_limits'),(wave+'NEW_A_OWNER_LOCAL_REPORTED_PERIOD_LEADERS.json','A_reported_period_leaders_aggregate_only'),(wave+'C_CORRECTED_OUTCOME_POPULATION_SCOPE_QUALIFICATION.json','corrected_C_outcome_population_scope'),(wave+'B_MATCHED_WINNER_NEXT_DISTINCT_SCORE_COMPARISONS.json','strongest_other_B_comparisons'),(wave+'STRONGEST_B_PAIRED_ANALYSIS.json','derived_paired_analysis'),(wave+'REC_YD_C02_OWNER_REVIEW_PACKAGE.json','prepared_not_admitted_category_package_with_strongest_B_control'),(wave+'paired-analysis-index-v1/ANALYSIS_MANIFEST.json','paired_analysis_index'),(weekly+'README.md','weekly_readable_results'),(weekly+'SCORES.json','weekly_retained_method_scores'),(weekly+'CONSTANT_CONTROL_SCORES.json','weekly_full_board_and_matched_controls'),(weekly+'FULL_SYSTEM_FOCAL_SCORES.json','weekly_focal_full_system_views'),(weekly+'NATIVE_FALLBACK_SCOPE_QUALIFICATION.json','issued_vs_unavailable_fallback_scope'),(weekly+'FOCAL_COVERAGE_ALIAS_QUALIFICATION_V3.json','mask_alias_qualification'),(weekly+'WEEK_TO_PARENT_RECONCILIATION.json','weekly_to_cumulative_reconciliation'),(weekly+'RUN_RECEIPT.json','weekly_execution_receipt'),(weekly+'SUPPLEMENTAL_DERIVATION_BINDINGS.json','supplemental_code_and_source_bindings'),(weekly+'INDEPENDENT_WEEKLY_PARTITION_VERIFICATION_V1.json','independent_weekly_counts_masks_and_metrics'),(weekly+'INDEPENDENT_FALLBACK_QUALIFICATION_READBACK_V1.json','independent_fallback_scope_check'),(weekly+'results-index-v1/INDEX_MANIFEST.json','permanent_result_index'),('registries/CURRENT_RESULTS_INDEX.json','current_result_discovery_pointer'),(base+'continuation-20261103-v1/independent/INDEPENDENT_FRESH_UPSTREAM_AGGREGATES_V1.json','independent_A_period_aggregate_checks_and_limits'),(base+'continuation-20261103-v1/independent/INDEPENDENT_FRESH_C_CODE_READBACK_V1.json','independent_current_C_scorer_hash_check')]
 from concurrent.futures import ThreadPoolExecutor
 with ThreadPoolExecutor(max_workers=4)as pool:new=list(pool.map(lambda x:committed_export(ref,*x),paths))
 for r in new:r['artifact_id']='B-EXPORT-'+hashlib.sha256((ref+':'+r['path']).encode()).hexdigest()[:16]
 value=dict(prior,schema_version='B-ABC-EXPORT-INDEX-v4.0',at_utc=datetime.now(timezone.utc).isoformat(),exports=prior['exports']+new,
  previous_index=dict(ref='61b2424a8e76ea6d79c345727f4477fad02cc145',path=base+'EXPORT_INDEX.json',preserved_copy=base+'EXPORT_INDEX_61b2424a_V3.json'),
  canonical_state='C_CORE_PINNED_OLDER_B7C_AGGREGATES_LIMITED_ADMITTED_NEW_B_EXPORTS_AWAIT_C_INTAKE',
  latest_C_publication=dict(ref='39b98567cc11835363e91c6a2b504bf9cae1f17a',continuation_id='ABC-C-PERIOD-CONTINUATION-v2-1',continuation_sha256='e6a5b8488a7810231100098d1de53f19f902fa378dc1d4efa975ed62431b6f20',core_protocol_unchanged=True,admission_ledger_sha256='3b40290841143c0bfcb0c21a8cbf69af0c10ac27d2620eed957c6fb8df5e6909'),
  delivery=dict(discovery_file_published=True,older_B7c='LIMITED_PUBLIC_AGGREGATE_ADMISSION_AT_C39b;NOT_RAW_TIMING_OR_MASK_PARITY',new_B_exports='RECEIVED_VALIDATED_ADMITTED_NOT_OBSERVED',external_messages=0),
  next_action='C intake immutable newBexports at producer '+ref+' and refreshedA21ca outputs; record perartifact states. A402issue resolved. Preserve separate source/horizon/population and rawverification limits; no duplicate fits.',
  new_weekly_scope=dict(actual_weeks=[5,6,7],targets=['pass_yd','pass_cmp'],source_games=42,parent_cumulative_triads=63,new_score_views=852,new_fits=0,new_inference=0,new_forecasts=0,new_NFL_observations=0,partial_scope='Provider-labelled retained point-rule replay, missing oneW5game; separate from C Pinnacle W2-W3 and original picks.'),
  current_qualification=dict(path=wave+'LATEST_HANDOFF_ADMISSION_QUALIFICATION_V2.json',producer_commit=ref,scope='Current handoff/task status supersedes stale 402byte and not-published blockers in earlier exports. Existing numeric/grade evidence unchanged.'))
 target.write_text(json.dumps(value,indent=2)+'\n')
 print(json.dumps(dict(schema=value['schema_version'],new_readbacks=len(new),all_exports=len(value['exports']),producer_commit=ref)))

if __name__=='__main__':
 if len(sys.argv)>2 and sys.argv[1]=='period-amendment':period_amendment(sys.argv[2])
 elif len(sys.argv)>1:continuation(sys.argv[1])
 else:run()
