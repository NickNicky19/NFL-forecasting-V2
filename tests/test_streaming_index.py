import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import build_test_index_v2 as old
from tools import build_test_index_v3 as streaming
from tests import test_index_v2 as old_tests


class StreamingIndexTests(unittest.TestCase):
    def test_shared_csv_delivery_reuses_prior_parts_and_keeps_policy_identity(self):
        with tempfile.TemporaryDirectory()as folder:
            root=Path(folder);self.setup_tree(root)
            rows=json.loads((root/'added.json').read_text())
            rows[0]['record_kind']='retrospective_chronological_category_selector_aggregate_replay'
            (root/'added.json').write_text(json.dumps(rows))
            prior=json.loads((root/'prior/INDEX_MANIFEST.json').read_text())
            streaming.write(root,'prior/INDEX_MANIFEST.json','current',reuse_prior_csv=True)
            manifest=json.loads((root/'current/INDEX_MANIFEST.json').read_text())
            self.assertEqual(manifest['csv_parts'][:-1],prior['csv_parts'])
            self.assertEqual(manifest['csv_parts'][-1]['rows'],1)
            self.assertEqual(sum(p['rows']for p in manifest['csv_parts']),7)
            record=json.loads((root/manifest['shards'][-1]['path']).read_text())[0]
            self.assertEqual(record['kind'],rows[0]['record_kind'])
            self.assertEqual(record['source_aggregate_fields'],rows[0])

    def setup_tree(self,root):
        old_tests.ShardedIndexTests().setup_tree(root)
        with patch.object(old,'BASE','old.json'),patch.object(old,'OUTPUT','prior'),patch.object(old,'PREVIOUS_SHARDED','absent.json'):
            old.write(root)
        row=json.loads((root/'new.json').read_text())[0]
        row.update(week=6,record_id='fixture-6')
        (root/'added.json').write_text(json.dumps([row]))
        r=json.loads((root/'registries/RESULT_ARTIFACTS.json').read_text())
        r.append(dict(artifact='added.json',state='SCORED'))
        (root/'registries/RESULT_ARTIFACTS.json').write_text(json.dumps(r))

    def test_appends_without_changing_any_prior_record_or_shard(self):
        with tempfile.TemporaryDirectory()as folder:
            root=Path(folder);self.setup_tree(root)
            prior=json.loads((root/'prior/INDEX_MANIFEST.json').read_text())
            result=streaming.write(root,'prior/INDEX_MANIFEST.json','current')
            self.assertEqual(result['new_records'],1)
            self.assertEqual(result['records'],7)
            manifest=json.loads((root/'current/INDEX_MANIFEST.json').read_text())
            self.assertEqual(manifest['shards'][:len(prior['shards'])],prior['shards'])
            for shard in prior['shards']:
                self.assertEqual(hashlib.sha256((root/shard['path']).read_bytes()).hexdigest(),shard['sha256'])
            self.assertEqual(sum(x['rows']for x in manifest['csv_parts']),7)

    def test_changed_frozen_source_is_rejected(self):
        with tempfile.TemporaryDirectory()as folder:
            root=Path(folder);self.setup_tree(root);(root/'oldsource.json').write_text('[]')
            with self.assertRaisesRegex(ValueError,'frozen input changed'):
                streaming.write(root,'prior/INDEX_MANIFEST.json','current')

    def test_duplicate_new_identity_rejected_without_erasing_failure(self):
        with tempfile.TemporaryDirectory()as folder:
            root=Path(folder);self.setup_tree(root)
            rows=json.loads((root/'added.json').read_text());rows.append(rows[0])
            (root/'added.json').write_text(json.dumps(rows))
            with self.assertRaisesRegex(ValueError,'duplicate'):
                streaming.write(root,'prior/INDEX_MANIFEST.json','current')
            with self.assertRaisesRegex(ValueError,'incomplete index'):
                streaming.write(root,'prior/INDEX_MANIFEST.json','current')

    def test_empty_source_bound_dates_remain_unknown(self):
        with tempfile.TemporaryDirectory()as folder:
            root=Path(folder);self.setup_tree(root)
            row=json.loads((root/'added.json').read_text())[0];row.update(n=0,mae=None,week='ALL')
            body=json.dumps([row]).encode();(root/'added.json').write_bytes(body)
            dates=dict(source_score_sha256=hashlib.sha256(body).hexdigest(),rows=[dict(source_row_index=0,evaluation_seasons=[],evaluation_weeks=[])])
            (root/'dates.json').write_text(json.dumps(dates));reg=json.loads((root/'registries/RESULT_ARTIFACTS.json').read_text())
            reg[-1].update(dates_projection='dates.json',empty_dates_policy='explicit_empty_supported_scoring_dates')
            (root/'registries/RESULT_ARTIFACTS.json').write_text(json.dumps(reg))
            streaming.write(root,'prior/INDEX_MANIFEST.json','current')
            manifest=json.loads((root/'current/INDEX_MANIFEST.json').read_text())
            records=json.loads((root/manifest['shards'][-1]['path']).read_text())
            self.assertEqual(records[0]['weeks'],[])
            self.assertEqual(records[0]['source_aggregate_fields']['week'],'ALL')

    def test_infinite_count_log_score_preserved_as_explicit_failure(self):
        with tempfile.TemporaryDirectory()as folder:
            root=Path(folder);self.setup_tree(root)
            rows=json.loads((root/'added.json').read_text());rows[0].update(infinite_NLL=1,NLL=None)
            (root/'added.json').write_text(json.dumps(rows));streaming.write(root,'prior/INDEX_MANIFEST.json','current')
            manifest=json.loads((root/'current/INDEX_MANIFEST.json').read_text())
            record=json.loads((root/manifest['shards'][-1]['path']).read_text())[0]
            self.assertEqual(record['metric_status']['nll'],'positive_infinite_loss')
            self.assertIsNone(record['metrics']['nll'])

    def test_source_exact_precision_counts_replace_rate_derived_provenance(self):
        with tempfile.TemporaryDirectory()as folder:
            root=Path(folder);self.setup_tree(root)
            rows=json.loads((root/'added.json').read_text());rows[0].update(n=4,abs_lt_1=.75,precision_counts={'abs_lt_1':{'numerator':3,'denominator':4}})
            (root/'added.json').write_text(json.dumps(rows));streaming.write(root,'prior/INDEX_MANIFEST.json','current')
            manifest=json.loads((root/'current/INDEX_MANIFEST.json').read_text());record=json.loads((root/manifest['shards'][-1]['path']).read_text())[0]
            self.assertEqual(record['precision_metrics']['abs_lt_1']['numerator'],3)
            self.assertEqual(record['precision_metrics']['abs_lt_1']['numerator_provenance'],'retained_prediction_row_exact_counts_in_source_aggregate')

    def test_prediction_supersession_is_bound_without_altering_original_source(self):
        with tempfile.TemporaryDirectory()as folder:
            root=Path(folder);self.setup_tree(root);body=(root/'added.json').read_bytes();row=json.loads(body)[0]
            identity=streaming.evaluation(row,'added.json')['test_id']
            mapping={'rows':[{'source_artifact':'added.json','source_sha256':hashlib.sha256(body).hexdigest(),'source_row_index':0,'source_test_id':identity,'replacement_test_id':'TEST-new-version','state':'SUPERSEDED_ORIGINAL_RECIPE_CONTINUITY'}]}
            (root/'mapping.json').write_text(json.dumps(mapping));registry=json.loads((root/'registries/RESULT_ARTIFACTS.json').read_text());registry[-1]['supersession_mapping']='mapping.json';(root/'registries/RESULT_ARTIFACTS.json').write_text(json.dumps(registry))
            streaming.write(root,'prior/INDEX_MANIFEST.json','current');manifest=json.loads((root/'current/INDEX_MANIFEST.json').read_text());record=json.loads((root/manifest['shards'][-1]['path']).read_text())[0]
            self.assertEqual(record['test_id'],identity);self.assertEqual(record['source_aggregate_fields'],row)
            self.assertEqual(record['score_version_state'],'SUPERSEDED_ORIGINAL_RECIPE_CONTINUITY')
            self.assertEqual(record['replacement_test_id'],'TEST-new-version')
