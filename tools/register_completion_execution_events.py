"""Root-only append of real saved-row work and separately retained attempts."""
import csv,hashlib,json
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];G=ROOT/'reports/completion-20261031g'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def append_csv(p,rows):
 with p.open(newline='')as f:fields=csv.DictReader(f).fieldnames
 with p.open('a',newline='')as f:
  w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writerows({k:json.dumps(v)if isinstance(v,(dict,list))else v for k,v in r.items()}for r in rows)
def main():
 now=datetime.now(timezone.utc).isoformat();p=ROOT/'registries/EXECUTIONS.jsonl';old=[json.loads(s)for s in p.read_text().splitlines()if s.strip()];known={r['run_id']for r in old};events=[];artifacts=[]
 receipts=sorted({q for q in G.rglob('*.json')if q.name.endswith('RECEIPT.json')and'results-index-v1'not in q.parts}|{G/'RECOVERY_STATUS.json',G/'COMPLETION_PROTOCOL.json',G/'PROVISIONAL_AUTHORITY_ADDENDUM_RECEIPT.json',G/'PROVISIONAL_POLICY_AND_CAPTURE_STATUS.json',G/'SOFTWARE_VERIFICATION_MANIFEST.json',G/'law-recovery/v1/ENVIRONMENT_AND_THREAD_LIMIT_FINDING.json'})
 for q in receipts:
  rel=q.relative_to(ROOT).as_posix();rid='V2-20261031G-'+hashlib.sha256(rel.encode()).hexdigest()[:16]
  if rid in known:continue
  obj=json.loads(q.read_text());state=obj.get('state',obj.get('status','RECEIPT_METADATA_SNAPSHOT'))
  ev=dict(run_id=rid,state=state,recorded_at_utc=now,accepted_parent='d8249404747059d91637190dda36cef7a89c7279',receipt=rel,receipt_sha256=sha(q),actual_new_fit_calls=0,new_inference_calls=0,new_issued_forecasts=0,new_current2026_Week8_player_outcomes_read=0,production_changed_by_V2=False,scope='Saved-source/loss/retained-law lookup, timing qualification, metadata, software, independent verification or preserved failed attempt; receipt gives exact execution state. Evaluation views are not unique NFLobservations.')
  events.append(ev);artifacts.append(dict(artifact_id=rid+'-ARTIFACT',run_id=rid,file=rel,sha256=sha(q),bytes=q.stat().st_size,kind='bounded_execution_or_independent_or_notification_receipt',status=state,original=False,evidence_availability='PUBLIC_SAFE_SOURCE_BOUND_RECEIPT',private_locator=None))
 with p.open('a')as f:
  for r in events:f.write(json.dumps(r)+'\n')
 p=ROOT/'registries/RUN_RESULT_ARTIFACT_MANIFEST.json';rows=json.loads(p.read_text());rows.extend(artifacts);dump(p,rows);append_csv(ROOT/'registries/RUN_RESULT_ARTIFACT_MANIFEST.csv',artifacts)
 reqs=[]
 for rid,mechanism,state,answer in [
 ('CATEGORY-COMPLETION-20261031','Finite all-method current/full-prior-season category decisions; actual procedures at offered thresholds and exact-recipe gaps','SUPPORTED_COMPLETION_WITH_EXPLICIT_EXTERNAL_GAPS','FULL_CATEGORY_CHAMPIONSHIP_REPORT.md'),
 ('PROVISIONAL-CAPTURE-ADDENDUM-20261031','Existing provisional owner policy; parallel upcoming capture; distinct source vintages and mandatory operational gates','APPLIED_OWNER_NOTIFIED_ACK_UNOBSERVED','PROVISIONAL_AUTHORITY_ADDENDUM_RECEIPT.json')]:
  reqs.append(dict(request_id=rid,delivery='DIRECT_USER_INSTRUCTION_THIS_SESSION',amendment_group='FULL_CATEGORY_CHAMPIONSHIP_COMPLETION',target='ALL12',requested_mechanism=mechanism,procedure_id=None,equivalence_status='ADDITIVE_CONTINUATION_PRESERVES_PRIOR_EVIDENCE',completion_condition='All admitted executable comparisons; exact remaining source/storage/owner dependencies visible, no production authority transfer',status=state,seasons=[2022,2023,2024,2025,2026],source_id='OWNER-COMPLETION-20261031',answer_or_status_artifact=(G/answer).relative_to(ROOT).as_posix(),related_legacy_labels=[],source_prerequisites='Existing source/retention/horizon/settlement/owner rules persist'))
 for filename in('REQUESTS.json','REQUEST_METHOD_CROSSWALK.json'):
  p=ROOT/'registries'/filename;rows=json.loads(p.read_text());ids={r['request_id']for r in rows};rows.extend(r for r in reqs if r['request_id']not in ids);dump(p,rows)
 p=ROOT/'registries/REQUEST_METHOD_CROSSWALK.csv';existing={r['request_id']for r in csv.DictReader(p.open())};append_csv(p,[r for r in reqs if r['request_id']not in existing])
 dump(G/'EXECUTION_REGISTRATION_RECEIPT.json',dict(state='ROOT_APPENDED_SOURCE_BOUND_EVENTS',new_events=len(events),new_fits=0,new_inference_calls=0,new_issued_forecasts=0,restricted_records_published=False,source_thresholds=1319,qualified_threshold_actuals=1275,unknown_threshold_appearances=44,distinct_source_games=28,distinct_source_weeks=2,evaluation_views=json.loads((G/'NEW_CANONICAL_SCORE_MANIFEST.json').read_text())['views'],unit_note='1319offer rows contain correlated props; the28games are already in the fixed107-game numerical panel. Repeated methods/outputviews/books/cohorts are not new NFLobservations.',resource_caveat='Per-run receipts report measured wall/RSS/CPU where available. No fabricated total for unmetered failed compiler/native peak. Law lookupv1 configured5nativepool ceiling violated2threadregistration; preserved with finding, no modelpredict/apply/fit; future enforcement patched.'))
 print(json.dumps(dict(new_events=len(events),new_manifest_rows=len(artifacts))))
if __name__=='__main__':main()
