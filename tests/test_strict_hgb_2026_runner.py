import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from nfl_v2 import strict_hgb_2026_runner as r
class StrictRunnerFixtures(unittest.TestCase):
 def positive_gate(self,root):
  import hashlib
  (root/'reports').mkdir();proofs=[];archives=[]
  for ident,parts in zip(sorted(r.retention.EXPECTED_PENDING_IDS),(13,11,17,12)):
   digest=hashlib.sha256(ident.encode()).hexdigest();archives.append(dict(artifact_id=ident,missing_parts=parts,archive_sha256=digest,archive_bytes=100,inner_files=2));name='reports/'+ident+'.json';file=root/name;file.write_text(json.dumps(dict(artifact_id=ident,status='FRESH_PRIVATE_RESTORE_ALL_PARTS_AND_INNER_FILES_VERIFIED',archive_sha256=digest,archive_bytes=100,inner_file_checks=1,manifest_file_extra=1)));proofs.append(dict(artifact_id=ident,path=name,sha256=r.sha(file)))
  delta=next(x['archive_sha256']for x in archives if 'RECOVERY-DELTA'in x['artifact_id']);mapsha=r.retention.EXPECTED_PRIVATE_MAP_SHA256
  def bound(name,value):
   path='reports/'+name+'.json';(root/path).write_text(json.dumps(value));return dict(path=path,sha256=r.sha(root/path))
  plan=bound('plan',dict(archives=archives,cutoff_utc='2026-01-01T00:00:00+00:00',required_file_paths=29527,required_unique_content_hashes=20217,new_delta_unique_files=1787))
  prior=bound('prior',dict(entries=[dict(artifact_id='fictional'+str(i))for i in range(20)]))
  review=bound('review',dict(state='PASS_EXPANDED_CONTENT_RECOVERY_PLAN_WITH_POSITIVE_PROOF_SUPPLEMENT',status_artifact_sha256=plan['sha256'],positive_allowlist_sha256=prior['sha256'],positive_used_object_proofs=20,private_map_sha256=mapsha,required_path_aliases=29527,unique_content_hashes=20217,delta_unique_file_blobs=1787,delta_archive_sha256=delta))
  encoding=bound('encoding',dict(state='PASS_DISTINCT_EXTERNAL_AND_ARCHIVE_MAP_BYTE_BINDINGS',semantic_objects_identical=True,external_private_map_sha256=mapsha,delta_archive_sha256=delta))
  self.enterContext(patch.multiple(r.retention,EXPECTED_PLAN_SHA256=plan['sha256'],EXPECTED_CONTENT_REVIEW_SHA256=review['sha256'],EXPECTED_MAP_REVIEW_SHA256=encoding['sha256'],EXPECTED_PRIOR_ALLOWLIST_SHA256=prior['sha256']))
  gate=root/'gate.json';gate.write_text(json.dumps(dict(state=r.GATE_STATE,completed_at_utc=r.now(),all_required_archives_verified=True,all_required_members_verified=True,missing_required_parts=0,recovery_plan=plan,content_plan_review=review,map_encoding_review=encoding,accepted_prior_proof_allowlist=prior,covered_private_map_sha256=mapsha,covered_path_aliases=29527,covered_unique_content_hashes=20217,proof_receipts=proofs)));return gate
 def test_all147cells_accounted(self):
  grid=r.planned_grid();self.assertEqual(len(grid),147);self.assertEqual(len({c['slot']for c in grid}),147);self.assertTrue(all(c['state']=='NOT_RUN'and c['forecast_state']=='NOT_RUN'for c in grid))
 def test_capacity_confirmation_is_not_restoration(self):
  with tempfile.TemporaryDirectory()as temp:
   root=Path(temp);p=root/'capacity.json';p.write_text(json.dumps(dict(state='OWNER_CAPACITY_CONFIRMED',all_required_archives_verified=True,missing_required_parts=0)))
   with self.assertRaises(ValueError):r.require_retention(p,root)
 def test_all_four_hash_bound_positive_proofs(self):
  with tempfile.TemporaryDirectory()as temp:
   root=Path(temp);gate=self.positive_gate(root);self.assertEqual(r.require_retention(gate,root)['state'],r.GATE_STATE)
   one=json.loads(gate.read_text())['proof_receipts'][0];(root/one['path']).write_text('{}')
   with self.assertRaises(ValueError):r.require_retention(gate,root)
 def test_partial_or_missing_backlog_cannot_pass(self):
  with tempfile.TemporaryDirectory()as temp:
   root=Path(temp);gate=self.positive_gate(root);obj=json.loads(gate.read_text());obj['proof_receipts']=obj['proof_receipts'][:1];gate.write_text(json.dumps(obj))
   with self.assertRaises(ValueError):r.require_retention(gate,root)
 def test_unrelated_digest_and_future_clock_cannot_pass(self):
  from datetime import datetime,timezone,timedelta
  with tempfile.TemporaryDirectory()as temp:
   root=Path(temp);gate=self.positive_gate(root);obj=json.loads(gate.read_text());proofref=obj['proof_receipts'][0];file=root/proofref['path'];proof=json.loads(file.read_text());proof['source_prediction_sha256']=proof.pop('archive_sha256');file.write_text(json.dumps(proof));proofref['sha256']=r.sha(file);gate.write_text(json.dumps(obj))
   with self.assertRaises(ValueError):r.require_retention(gate,root)
   obj['completed_at_utc']=(datetime.now(timezone.utc)+timedelta(days=1)).isoformat();gate.write_text(json.dumps(obj))
   with self.assertRaises(ValueError):r.require_retention(gate,root)
 def test_initialization_failure_preserves_full_empty_grid(self):
  with tempfile.TemporaryDirectory()as temp:
   root=Path(temp);private=root/'private';private.mkdir();(root/'FROZEN_PROTOCOL.json').write_text(json.dumps(dict(run_id='fictional',query_cells=1)));(root/'EXECUTION_REGISTRATION.json').write_text('{}')
   with patch.object(r,'_execute',side_effect=r.ResourceBudget('fictional source stop')):out=r.execute(public=root,private=private)
   self.assertEqual(out['state'],'PARTIAL_STOPPED');self.assertEqual(out['actual_fit_calls'],0);self.assertEqual(out['score_views'],0);self.assertEqual(len(json.loads((root/'GRID_STATUS.json').read_text())),147)
 def test_private_bytes_checked_before_write(self):
  with tempfile.TemporaryDirectory()as temp:
   root=Path(temp);b=r.Budget(dict(wall_seconds=60,cpu_seconds=60,max_rss_bytes=2147483648,max_private_bytes=32,private_reserve_bytes=0),root);path=root/'wouldwrite.gz'
   with self.assertRaises(r.ResourceBudget):b.save(path,bytes(range(128)),raw=True)
   self.assertFalse(path.exists())
 def test_missing_label_is_preserved(self):
  q=dict(season='2026',week='1',game_id='g',player_id='00-0000001',target='pass_yd',population='primary',position='QB');row=dict(game_id='g',player_id='00-0000001',position='QB',week=1,kickoff=10,values={'pass_yd':None});p=dict(source_role_contract={'primary':{'pass_yd':['QB']}})
  out=r.join_labels([q],[row],p)[0];self.assertIsNone(out['actual']);self.assertEqual(out['actual_status'],'PARTICIPATION_OR_LABEL_UNKNOWN');self.assertEqual(q['season'],'2026')
 def test_proper_binary_endpoints_keep_infinite_loss(self):
  m=r.score.Meter();m.add(dict(target='anytime_td',prediction=0.,actual=1.,fallback='none',game_id='g',week=1));out=m.result();self.assertEqual(out['brier'],1);self.assertEqual(out['log_loss'],'Infinity');self.assertEqual(out['infinite_log_losses'],1)
  bins=r.reliability([dict(prediction=0.,actual=1.),dict(prediction=1.,actual=0.),dict(prediction=.5,actual=None)]);self.assertEqual((bins[0]['n'],bins[9]['n']),(1,1))
 def test_execution_cannot_touch_source_before_gate(self):
  with tempfile.TemporaryDirectory()as temp:
   root=Path(temp);(root/'FROZEN_PROTOCOL.json').write_text('{}');proof=root/'prefit.json';proof.write_text('{}')
   with patch.object(r,'load_current')as loader,patch.object(r.source,'make_estimator')as estimator:
    with self.assertRaises(ValueError):r.execute(source_root=root,public=root,private=root,retention_gate=None,repository=root,prefit_review=proof,sole_fit_worker=True)
    loader.assert_not_called();estimator.assert_not_called()
if __name__=='__main__':unittest.main()
