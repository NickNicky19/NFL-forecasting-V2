import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from nfl_v2.result_index import evaluation
from tools import build_test_index_v2 as index


class ShardedIndexTests(unittest.TestCase):
    def setup_tree(self,root):
        row=dict(procedure_id='fictional-old',target='rush_att',product_id='point',
                 evaluation_panel_id='fixture',population='fixture',n=1,mae=2.,season=2026,week=1)
        body=json.dumps([row]).encode();(root/'oldsource.json').write_bytes(body)
        record=evaluation(row,'oldsource.json')
        old=dict(records=[record],input_manifests=[dict(source_artifact='oldsource.json',sha256=hashlib.sha256(body).hexdigest())],
                 definitions={},precision_definition='fixture',forbidden_accuracy_conversion='none')
        (root/'old.json').write_text(json.dumps(old))
        (root/'registries').mkdir()
        new=[dict(row,procedure_id='fictional-new',week=w,record_id='fixture-'+str(w)) for w in range(1,6)]
        (root/'new.json').write_text(json.dumps(new))
        (root/'registries/RESULT_ARTIFACTS.json').write_text(json.dumps([dict(artifact='new.json',state='SCORED')]))
        return old

    def test_shards_retain_prior_ids_and_bound_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);old=self.setup_tree(root)
            with patch.object(index,'BASE','old.json'),patch.object(index,'OUTPUT','out'),patch.object(index,'MAX_SHARD',12000):
                result=index.write(root)
            self.assertEqual(result['records'],6)
            manifest=json.loads((root/'out/INDEX_MANIFEST.json').read_text())
            self.assertGreater(len(manifest['shards']),1)
            rows=[]
            for s in manifest['shards']:
                b=(root/s['path']).read_bytes();self.assertLessEqual(len(b),12000)
                self.assertEqual(hashlib.sha256(b).hexdigest(),s['sha256']);rows.extend(json.loads(b))
            self.assertIn(old['records'][0]['test_id'],{r['test_id'] for r in rows})

    def test_changed_frozen_input_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);self.setup_tree(root);(root/'oldsource.json').write_text('[]')
            with patch.object(index,'BASE','old.json'),self.assertRaisesRegex(ValueError,'source changed'):
                index.build(root)

    def test_duplicate_evaluation_not_counted_twice(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);self.setup_tree(root)
            rows=json.loads((root/'new.json').read_text());rows.append(rows[0]);(root/'new.json').write_text(json.dumps(rows))
            with patch.object(index,'BASE','old.json'),self.assertRaisesRegex(ValueError,'duplicate'):
                index.build(root)

    def test_full_source_hash_is_not_repeated_for_each_output_view(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);self.setup_tree(root);body=(root/'new.json').read_bytes();calls=[];original=index.sha
            def observed(value):
                if value==body:calls.append(1)
                return original(value)
            with patch.object(index,'BASE','old.json'),patch.object(index,'sha',side_effect=observed):
                index.build(root)
            self.assertLessEqual(len(calls),2)

    def test_next_checkpoint_reuses_prior_shards_and_preserves_their_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);self.setup_tree(root)
            with patch.object(index,'BASE','old.json'),patch.object(index,'OUTPUT','first'),patch.object(index,'PREVIOUS_SHARDED','absent.json'):
                index.write(root)
            prior=json.loads((root/'first/INDEX_MANIFEST.json').read_text())
            prior_bytes={s['path']:(root/s['path']).read_bytes() for s in prior['shards']}
            row=json.loads((root/'new.json').read_text())[0];row.update(week=6,record_id='fixture-6')
            (root/'additional.json').write_text(json.dumps([row]))
            (root/'registries/RESULT_ARTIFACTS.json').write_text(json.dumps([
                dict(artifact='new.json',state='SCORED'),dict(artifact='additional.json',state='SCORED')]))
            with patch.object(index,'BASE','old.json'),patch.object(index,'OUTPUT','second'),patch.object(index,'PREVIOUS_SHARDED','first/INDEX_MANIFEST.json'):
                result=index.write(root)
            self.assertEqual(result['records'],7)
            manifest=json.loads((root/'second/INDEX_MANIFEST.json').read_text())
            self.assertTrue(set(prior_bytes)<={s['path'] for s in manifest['shards']})
            for path,body in prior_bytes.items():self.assertEqual((root/path).read_bytes(),body)

    def test_explicit_empty_scored_dates_remain_empty_without_changing_source_period(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);self.setup_tree(root)
            row=json.loads((root/'new.json').read_text())[0];row.update(n=0,mae=None,week='ALL')
            body=json.dumps([row]).encode();(root/'new.json').write_bytes(body)
            projection=dict(source_score_sha256=hashlib.sha256(body).hexdigest(),
                            rows=[dict(source_row_index=0,evaluation_seasons=[],evaluation_weeks=[])])
            (root/'dates.json').write_text(json.dumps(projection))
            (root/'registries/RESULT_ARTIFACTS.json').write_text(json.dumps([dict(artifact='new.json',state='SCORED',
                dates_projection='dates.json',empty_dates_policy='explicit_empty_supported_scoring_dates')]))
            with patch.object(index,'BASE','old.json'):_,records,_,_=index.build(root)
            result=next(r for r in records if r['source_artifact']=='new.json')
            self.assertEqual(result['weeks'],[])
            self.assertEqual(result['dates_missing_reason'],'zero_supported_rows_no_scored_weeks')
            self.assertEqual(result['source_aggregate_fields']['week'],'ALL')
