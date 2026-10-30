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
