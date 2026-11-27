"""Check bounded VM evidence/bindings without rerunning VM or grading outcomes."""
import argparse,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;BASE=HERE.parent;SUP=BASE/'supplemental';ROOT=HERE.parents[2]
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--cache',type=Path,required=True);ap.add_argument('--projection',type=Path,required=True);a=ap.parse_args();manifest=read(SUP/'PUBLIC_ARTIFACT_MANIFEST.json')
    for x in manifest['artifacts']:
        p=SUP/x['path'];assert p.stat().st_size==x['bytes']and sha(p)==x['sha256']
    p=read(SUP/'FROZEN_PROTOCOL.json');receipt=read(SUP/'SOFTWARE_VERIFICATION_RECEIPT.json');assert receipt['protocol_sha256']==sha(SUP/'FROZEN_PROTOCOL.json')
    for x in receipt['code_bindings']:
        f=(ROOT if x['path'].startswith('tools/')else SUP)/x['path'];assert sha(f)==x['sha256']
    for x in receipt['output_bindings']:assert sha(SUP/x['path'])==x['sha256']
    main=read(SUP/'CONSUMER_EXECUTION_RESULT.json');selected=read(SUP/'SELECTED_CONSUMER_EXECUTION_RESULT.json');acq=read(SUP/'FRESH_SERVED_ACQUISITION.json');assert acq['source_acquisition_sha256']==sha(BASE/'FRESH_BYTE_READBACK.json')
    for x in acq['receipts']:assert sha(a.cache/x['kind'])==x['sha256']
    board=read(SUP/'BOARD_METADATA_PROJECTION_RECEIPT.json');assert sha(a.projection)==board['projection_sha256']==selected['projection_sha256'];assert a.projection.stat().st_size==board['private_projected_bytes']==239221;assert not{'actual','actuals','outcomes','stats','results','st','labels'}&set(board['allowlist']);assert board['NFL_outcomes_used']==board['NFL_statistic_scalars_decoded']==0
    assert main['rows']==main['all_exact_valid_window_values_checked']==main['all_exact_valid_window_cards_checked']==main['currently_renderable_values_checked']==1945;assert sum(x['future_renderable']for x in main['categories'].values())==1789 and sum(x['frozen']for x in main['categories'].values())==156;assert main['stat_point_mae_v2_rows']==0
    assert len(main['checks'])==11 and len(selected['checks'])==6 and all(x['status']=='PASS'for x in main['checks']+selected['checks']);assert len({x['name']for x in main['checks']+selected['checks']})==17;assert selected['selected_records']==24 and selected['by_side']['over']['visible']==selected['by_side']['under']['visible']==12;assert sum(x['adaptive']for x in selected['by_side'].values())==21 and sum(x['classic_reference']for x in selected['by_side'].values())==3
    assert main['audit_clock']==selected['audit_clock']==receipt['audit_clock']=='2026-10-31T18:46:30.977Z';assert receipt['forecast_numeric_fields_parsed']is True and receipt['target_game_outcome_scalars_decoded']==0 and receipt['full_browser_DOM_execution']is False;assert receipt['tests_passed']==receipt['tests_run']==17
    app=(a.cache/'app.js').read_text();boundaries=[('function selectedRankingPolicy(','\nfunction rankingCanonical('),('function rankingCanonical(','\nfunction effectivePropForecast('),('function compareSelectedRankingItems(','\nasync function validateSelectedRankings('),('async function validateSelectedRankings(','\nasync function startSelectedRankings('),('function selectedPropForecast(','\nfunction propChip('),('function visibleTopPicks(','\nfunction topPicksSourceCaption(')];slices=[]
    for start,end in boundaries:
        i=app.index(start);j=app.index(end,i);slices.append(hashlib.sha256(app[i:j].encode()).hexdigest())
    assert slices==selected['function_slices_sha256'];assert sha(a.cache/'app.js')==selected['app_sha256']and sha(a.cache/'consumer.js')==selected['consumer_sha256'];assert sha(a.cache/'payload.json')==selected['overlay_payload_sha256']and sha(a.cache/'selected-payload.json')==selected['selected_payload_sha256'];helper=(SUP/'check_selected_consumer.js').read_text();assert'class AuditDate extends Date'in helper and'vm.createContext'in helper and'fetch:'not in helper;consumer=(a.cache/'consumer.js').read_text();assert'row.first_prepared_at'in consumer and'doc.packaged_at'in consumer
    out=dict(state='PASS_INDEPENDENT_CONSUMER_SUPPLEMENT_SOURCE_AND_OUTPUT_BINDINGS',checker_sha256=sha(Path(__file__)),protocol_sha256=sha(SUP/'FROZEN_PROTOCOL.json'),software_receipt_sha256=sha(SUP/'SOFTWARE_VERIFICATION_RECEIPT.json'),manifest_sha256=sha(SUP/'PUBLIC_ARTIFACT_MANIFEST.json'),actual_source_function_slices_reproduced=6,public_artifacts_checked=len(manifest['artifacts']),named_software_checks_verified=17,actual_admitted_value_function_witnesses=1945,future_function_witnesses=1789,frozen_function_witnesses=156,selected_visibility_witnesses=24,selected_Over=12,selected_Under=12,forecast_numeric_parsing_explicit=True,target_game_outcome_scalars_used=0,duplicate_VM_runs_by_verifier=0,new_NFL_grades=0,new_models=0,scope='Separately audited exact function slices, wire/source/projection hashes, clock injection, output arithmetic and labelled failure probes. Existing actual VM execution was not repeated. This is software admission/returnedstring evidence at the recorded readback epoch, not full browser DOM, new inference/issuance, forecast accuracy, authenticated source availability or retained-owner admission.')
    with(HERE/'INDEPENDENT_CONSUMER_SUPPLEMENT_REVIEW.json').open('x')as f:json.dump(out,f,indent=2);f.write('\n')
    print(json.dumps(dict(state=out['state'],named_checks=17,value_function_witnesses=1945,selected_visible=24)))
if __name__=='__main__':main()
