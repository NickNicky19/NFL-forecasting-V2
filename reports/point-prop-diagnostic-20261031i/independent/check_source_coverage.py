"""Verify claim-specific source limits from retained pinned public code/documents."""
import argparse,hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent;PUB=HERE.parent/'source-coverage'
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--private-root',type=Path,required=True);ap.add_argument('--receipt',type=Path,default=HERE/'SOURCE_COVERAGE_INDEPENDENT_REVIEW.json');a=ap.parse_args();folder=a.private_root/'point-prop-diagnostic-20261031i-source';protocol=read(PUB/'READ_ONLY_DISCOVERY_PROTOCOL.json');bindings=read(PUB/'PUBLIC_SOURCE_BINDINGS.json')['sources'];wrappers={}
    for f in folder.glob('*.json'):
        z=read(f)
        if isinstance(z,dict)and z.get('path')and isinstance(z.get('content'),str)and z.get('source_commit'):wrappers[z['path']]=z
    checked=[]
    for b in bindings:
        z=wrappers[b['path']];body=z['content'].encode();assert len(body)==b['bytes'];assert hashlib.sha256(body).hexdigest()==b['sha256'];assert hashlib.sha1(b'blob '+str(len(body)).encode()+b'\0'+body).hexdigest()==z['git_blob']==b['git_blob_sha1'];assert z['source_commit']==b['commit'];checked.append(dict(path=b['path'],git_blob_sha1=b['git_blob_sha1'],sha256=b['sha256']))
    deps=read(PUB/'EXACT_EXPORT_AND_TIME_DEPENDENCIES.json');offer=read(folder/'PRODUCER_CODE_2.json')['content'];archive=read(folder/'PRODUCER_CODE_3.json')['content'];driver=read(folder/'OFFER_EXTRA_1.json')['content'];exporter=read(folder/'AUDIT_FILE_0.json')['content'];owner=read(folder/'OWNER_FILE_1.json');owner_receipt=json.loads(owner['content'])
    assert re.search(r'source_quote_time\s*=\s*None',offer)and re.search(r'cutoff_qualified\s*=\s*False',offer)
    assert '"last_updated": "source_collection_naive"'in archive
    assert re.search(r"\[['\"]cutoff_utc['\"]\]\s*=\s*f\.kickoff_utc",driver)and'cutoff_utc=g.kickoff_utc'in driver
    assert'Reconstructed 2026 REG Weeks1-7; not original website recommendations'in exporter
    assert deps['producer_contract']['source_quote_time']is None and deps['producer_contract']['cutoff_qualified']is False
    readable=deps['readable_scorecard'];assert readable['bytes']==11137356 and readable['sha256']=='80ba907a24b4f9cc10b66f48e4408736ae9bc6d182a4be8bdf49fd9bf4113036';assert readable['sha256']in owner['content']and str(readable['bytes'])in owner['content']
    assert owner_receipt['rows']=={z['name']:z['reported_rows']for z in readable['members']if'reported_rows'in z};assert readable['CSV_headers'].startswith('NOT_INDEPENDENTLY_READ')and readable['inner_member_hashes'].startswith('NOT_PUBLISHED')
    plan=read(folder/'MARKET_SEALED_PLAN.json')['content'];caps=deps['normalized_capsules'];containers={}
    for b in caps:
        for field in ('container_sha256','member_sha256'):assert b[field]in plan
        assert b['member']in plan and b['quote_time_state'].startswith('UNQUALIFIED')and b['original_selection_state']=='NO_ORIGINAL_MODEL_PICK_AUTHENTICATED';containers[b['container_sha256']]=b['container_bytes']
    assert {z['season']for z in caps}=={2022,2023,2024,2026}and sum(containers.values())==deps['distinct_container_bytes']==9401788
    rows=read(PUB/'CLAIM_SPECIFIC_COVERAGE_A_TO_E.json');assert len(rows)==9;assert {str(r['period'])for r in rows}=={'2026W1','2026W2','2026W3','2026W4','2026W5_THURSDAY','2022','2023','2024','2025'}
    for r in rows:
        assert r['A_original_state']=='NO_AUTHENTIC_ORIGINAL_PICK_CLOCK_LOCATED_IN_INSPECTED_SCOPE';assert r['newly_executable_original_panel']is False and r['newly_executable_timing_qualified_offer_panel']is False;assert r['newly_identified_bounded_replay_dependency']is True;assert 'NOT_ALL_METHODS'in r['C_football_input_state']or'PARTIAL'in r['C_football_input_state']or'RETAINED'in r['C_football_input_state'];assert ('D1/D2'in r['C_football_input_reason'])if str(r['period'])in {'2022','2023','2024','2025'}else ('147'in r['C_football_input_reason']);assert ('2021'in r['C_football_input_reason'])if str(r['period'])=='2022'else True
        if str(r['period'])=='2025':assert 'not proof'in r['B_threshold_reason']and r['D_reconstruction_state']=='POINT_REPLAY_ALREADY_SUPPORTED_THRESHOLD_REPLAY_NEEDS2025SOURCE'
        else:assert r['B_threshold_state']=='REPORTED_RECORDED_THRESHOLDS_TIMING_UNVERIFIED_NOT_QUALIFIED_HISTORICAL_OFFERS'
    r2022=next(r for r in rows if str(r['period'])=='2022');assert 'single-sided'in r2022['B_threshold_reason']and'no qualifying named-book pairs'in r2022['B_threshold_reason']
    assert deps['Drive_root_refresh']['evidence_level']=='REPORTED_BY_ROOT_READONLY_METADATA_CHECK'
    receipt=dict(state='PASS_INDEPENDENT_CLAIM_SPECIFIC_SOURCE_CODE_AND_SCOPE_REVIEW',protocol_sha256=sha(PUB/'READ_ONLY_DISCOVERY_PROTOCOL.json'),coverage_sha256=sha(PUB/'CLAIM_SPECIFIC_COVERAGE_A_TO_E.json'),dependency_sha256=sha(PUB/'EXACT_EXPORT_AND_TIME_DEPENDENCIES.json'),pinned_public_documents_verified=len(checked),period_cells=len(rows),readable_archive_reported_bytes=readable['bytes'],readable_archive_hash_reported=readable['sha256'],normalized_seasons=[2022,2023,2024,2026],distinct_normalized_container_bytes=9401788,independently_decoded_offer_player_rows=0,new_timing_qualified_offer_panels=0,new_authenticated_original_panels=0,source_code_findings=['Normalized quote time NULL and cutoff qualification false.','Raw last_updated is a naive collection clock, not authenticated quote/decision time.','Driver kickoff cutoff is a reconstructed query horizon, not original issuance.','Readable export expressly reconstructed2026W1-W7; CSV headers/inner bytes/route remain unrecovered.','2022 no-pair report does not establish no single-sided lines;2025 exclusion is scoped, not global absence.','Existing football replay and exact D1/D2/strict/2021 limitations remain separate from missing offer evidence.'],Drive_search_independently_repeated=False,Drive_search_limit='Root-reported metadata search only; no global private-source absence or quota proof.',new_fits=0,new_inference=0,new_scores=0,Week8_outcomes_read=0)
    with a.receipt.open('x')as f:json.dump(receipt,f,indent=2);f.write('\n')
    print(json.dumps(receipt))
if __name__=='__main__':main()
