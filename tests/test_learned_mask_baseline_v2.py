import csv,gzip,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from tools import learned_mask_baseline_portable as m
class DeferredEmpiricalFixture(unittest.TestCase):
 def test_empirical_current_before_recent_is_still_scored(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);base=root/'public';priv=root/'private';out=base/'run';pub=base/'fictional';folder=priv/'bundle'
   for d in (out,pub,folder):d.mkdir(parents=True)
   raw=[];scores=[]
   for proc,policy,arm,pred in [('empirical-player-history-control-v1','CURRENT','H-CURRENT',3.),('empirical-player-history-control-v1','RECENT','H-RECENT',4.),('model','CURRENT','H-CURRENT',1.)]:
    r=dict(procedure_id=proc,policy_id=policy,history_regime=arm,target='rec',population='primary',product_id='mean',query_id='q',prediction=pred,actual=2.,season=2025,week=1,game_id='g',fallback='none');raw.append(r);scores.append(dict(r,fallback_view='LEARNED_ONLY',n=1,mae=abs(pred-2)))
   flat=folder/'predictions.csv.gz'
   with gzip.open(flat,'wt',newline='') as f:w=csv.DictWriter(f,fieldnames=list(raw[0]));w.writeheader();w.writerows(raw)
   (pub/'SCORES.json').write_text(json.dumps(scores));(pub/'RUN_RECEIPT.json').write_text(json.dumps(dict(private_flat=dict(bundle_name=flat.name))))
   previous=dict(rows=[dict(source_row_index=i,comparison=dict(status='UNESTABLISHED'))for i in range(3)]);(pub/'BASELINE_COMPARISON_ANNOTATIONS.json').write_text(json.dumps(previous))
   spec=dict(source_scores_sha256=m.s.sha(pub/'SCORES.json'),source_flat_sha256=m.s.sha(flat),source_previous_annotations_sha256=m.s.sha(pub/'BASELINE_COMPARISON_ANNOTATIONS.json'))
   protocol=dict(code_sha256=m.s.sha(m.__file__),helper_sha256=m.s.sha('nfl_v2/paired_uncertainty.py'),sources=[spec],budget=dict(max_rows_read=10));(out/'FROZEN_PROTOCOL.json').write_text(json.dumps(protocol))
   with patch.multiple(m,BASE=base,PRIVATE=priv,OUT=out,SPECS=[('fictional','bundle')]):r=m.run()
   self.assertEqual(r['state'],'COMPLETE');self.assertEqual(r['learned_views_completed'],3)
   result=json.loads((pub/'BASELINE_COMPARISON_ANNOTATIONS_V2.json').read_text())['rows']
   self.assertEqual([x['comparison']['paired_n']for x in result],[1,1,1]);self.assertEqual(result[0]['comparison']['comparator_error'],2.)
if __name__=='__main__':unittest.main()
