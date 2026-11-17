"""Metadata-only checks; do not decode future predictions/outcomes or run models."""
import argparse,collections,hashlib,json
from datetime import datetime
from pathlib import Path

def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();p=a.root/'reports/completion-20261031g';rec=read(p/'UPCOMING_CAPTURE_CENSUS_RECEIPT.json');rows=read(p/'UPCOMING_CATEGORY_CAPTURE_STATUS.json');summary=read(p/'UPCOMING_CATEGORY_CAPTURE_SUMMARY.json');assert len(rows)==100 and len(summary)==12 and len({(r['category'],r['base_procedure_id'])for r in rows})==100
 for path,h in rec['source_sha256'].items():assert sha(a.root/path)==h
 assert all(rec[k]==0 for k in('new_fits','new_inference','new_captures','new_jobs','Week8_outcomes_read'));blocked=collections.Counter();available=collections.Counter();versions=0
 for r in rows:
  assert r['captured_shadow']and r['captured_remaining_games']==13 and r['capture_versions'];assert any(c['eligible_games']>=13 for c in r['capture_versions']);blocked_own=r['base_procedure_id'].startswith(('D1_','D2_'));assert r['eligible_for_owner_capture_package']==(not blocked_own);blocked[r['category']]+=blocked_own;available[r['category']]+=not blocked_own
  for c in r['capture_versions']:
   assert(a.root/c['source']).exists()if c.get('source')else True
   if c.get('persistence_utc'):assert datetime.fromisoformat(c['persistence_utc'].replace('Z','+00:00'))<datetime.fromisoformat('2026-11-01T16:30:00+00:00')
   assert c.get('restored_shadow')is not False;versions+=1
  assert r['owner_admission_state']=='NO_NEW_V2_ADMISSION_OBSERVED'and r['official_publication_state']=='NO_NEW_V2_OFFICIAL_PUBLICATION_OBSERVED'and r['served_verification_state']=='NO_NEW_V2_SERVED_VALUES_VERIFIED';assert r['new_window_inference_state']==r['new_window_persistence_state']=='NOT_EXECUTED_BY_V2_THIS_CHECKPOINT'
 for r in summary:
  cat=r['category'];assert r['captured_distinct_base_procedures']==available[cat]+blocked[cat]and r['own_model_available_distinct_procedures']==available[cat]and r['own_model_blocked_distinct_procedures']==blocked[cat];assert r['shortlist_count']==len(r['credible_owner_capture_shortlist'])==min(5,available[cat]);assert all(next(x for x in rows if x['category']==cat and x['base_procedure_id']==u)['eligible_for_owner_capture_package']for u in r['credible_owner_capture_shortlist'])
 note=(p/'UPCOMING_POLICY_IDENTITY_NOTE.md').read_text();assert'UNCAPTURED_PROSPECTIVELY'in note and'known-target-time'in note
 report=dict(state='PASS_INDEPENDENT_EXISTING_CAPTURE_CENSUS_METADATA',base_procedure_category_units=len(rows),categories=len(summary),capture_version_views=versions,available_own_model_source_units=dict(available),blocked_own_model_units=dict(blocked),all_base_units_have_thirteen_remaining_game_capture_source=True,new_G_known_target_time_policies='UNCAPTURED_PROSPECTIVELY',source_hashes_checked=len(rec['source_sha256']),new_inference=0,new_captures=0,future_prediction_payloads_read=0,future_outcomes_read=0,limitations=['Sourcebound accepted recovery receipts reviewed; no fresh complete restoration of every model/input packet performed by this metadata-only census.','Base-procedure capture versions and restored sources do not authenticate owner admission, currentruntime parity or new reconstructionpolicy captures.','Configured nextscheduler time is not an executedcapture or a V2scheduler authorization.'])
 with a.output.open('x')as f:json.dump(report,f,indent=2);f.write('\n')
 print(json.dumps(report))
if __name__=='__main__':main()
