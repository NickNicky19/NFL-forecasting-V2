import hashlib
import gzip
import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import build_test_index_v2 as old
from tools import build_test_index_v3 as streaming
from tests import test_index_v2 as old_tests


class StreamingIndexTests(unittest.TestCase):
    def test_lossless_compressed_append_keeps_old_parts_and_can_be_extended(self):
        with tempfile.TemporaryDirectory()as folder:
            root=Path(folder);self.setup_tree(root)
            prior=json.loads((root/'prior/INDEX_MANIFEST.json').read_text())
            streaming.write(root,'prior/INDEX_MANIFEST.json','compressed',reuse_prior_csv=True,compressed_delivery=True)
            m=json.loads((root/'compressed/INDEX_MANIFEST.json').read_text())
            self.assertEqual(m['shards'][:len(prior['shards'])],prior['shards'])
            self.assertEqual(m['csv_parts'][:len(prior['csv_parts'])],prior['csv_parts'])
            last=m['shards'][-1];self.assertEqual(last['compression'],'gzip')
            records=streaming.decode_shard(root,last);self.assertEqual(len(records),1)
            with gzip.open(root/m['csv_parts'][-1]['path'],'rt')as f:
                rows=list(csv.DictReader(f))
            self.assertEqual(rows[0]['test_id'],records[0]['test_id'])
            # A later checkpoint reads the mixed raw/gzip ancestor without replacement.
            result=streaming.write(root,'compressed/INDEX_MANIFEST.json','later',reuse_prior_csv=True,compressed_delivery=True)
            self.assertEqual(result['records'],7);self.assertEqual(result['new_records'],0)
            broken=dict(last,uncompressed_sha256='0'*64)
            with self.assertRaisesRegex(ValueError,'uncompressed shard'):
                streaming.decode_shard(root,broken)

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

class ProbabilityMaskCoverageTests(unittest.TestCase):
    def test_mask_coverage_is_not_whole_offer_coverage(self):
        r=dict(kind='prop_threshold_probability_evaluation',n=20)
        c=dict(outer_offer_universe=25,matched_candidate_admitted_law_rows=22,candidate_full_qualified_mask_n=20,qualified_mask_n=20,mask_over_outer_offer_fraction=.8)
        self.assertEqual(streaming.validate_probability_outer_coverage(r,c)['mask_over_outer_offer_fraction'],.8)
        with self.assertRaisesRegex(ValueError,'outer fraction'):
            streaming.validate_probability_outer_coverage(r,dict(c,mask_over_outer_offer_fraction=1.))
        with self.assertRaisesRegex(ValueError,'exceeds'):
            streaming.validate_probability_outer_coverage(r,dict(c,matched_candidate_admitted_law_rows=26))
        with self.assertRaisesRegex(ValueError,'other product'):
            streaming.validate_probability_outer_coverage(dict(r,kind='forecast_evaluation_view'),c)


class SelectionVintageCorrectionTests(unittest.TestCase):
    def test_bound_vintage_correction_preserves_original_score_and_side(self):
        original = dict(record_kind='prop_selection_evaluation',
                        source_vintage='SERVER_BOUND_ORIGINAL_THRESHOLDS_AND_POINTS',
                        side='under', n=48, selection_metrics={'WIN': 14, 'LOSS': 34})
        annotation = dict(correction_kind='SOURCE_VINTAGE_METADATA_ONLY',
                          original_source_vintage=original['source_vintage'],
                          source_vintage='RECONSTRUCTED_POINTS_SERVER_RETAINED_THRESHOLDS_REVISED_LABELS')
        corrected = streaming.apply_source_vintage_annotation(original, annotation)
        self.assertEqual(original['source_vintage'], annotation['original_source_vintage'])
        self.assertEqual(corrected['source_vintage'], annotation['source_vintage'])
        self.assertEqual(corrected['selection_metrics'], {'WIN': 14, 'LOSS': 34})
        self.assertEqual(corrected['side'], 'under')
        self.assertEqual(corrected['n'], 48)

    def test_vintage_correction_rejects_stale_or_unqualified_override(self):
        original = dict(record_kind='prop_selection_evaluation', source_vintage='old')
        good = dict(correction_kind='SOURCE_VINTAGE_METADATA_ONLY',
                    original_source_vintage='old', source_vintage='reconstructed')
        for bad in (dict(good, original_source_vintage='different'),
                    dict(good, correction_kind='prediction_change'),
                    dict(good, source_vintage='')):
            with self.assertRaises(ValueError):
                streaming.apply_source_vintage_annotation(original, bad)
        with self.assertRaisesRegex(ValueError, 'point/selection record'):
            streaming.apply_source_vintage_annotation(dict(original, record_kind='prop_threshold_probability_evaluation'), good)
        point = dict(record_kind='forecast_evaluation_view', mae=60.08, n=80)
        fixed = streaming.apply_source_vintage_annotation(point, dict(good, original_source_vintage=None))
        self.assertEqual(fixed['mae'], point['mae'])
        self.assertEqual(fixed['source_vintage'], 'reconstructed')
        self.assertNotIn('source_vintage', point)

    def test_conditional_mask_does_not_hide_full_source_unavailability(self):
        record = dict(kind='forecast_evaluation_view', n=80)
        context = dict(context='OWN_DECISION_ELIGIBLE_FULL_SYSTEM', source_offer_universe=84,
                       source_available_points=80, mask_points=80, context_outer_opportunities=84,
                       scored_or_selected_n=80, fraction_of_source=80/84, fraction_of_context=80/84)
        result = streaming.validate_diagnostic_context_coverage(record, [context])
        self.assertEqual(result[0]['source_offer_universe']-result[0]['source_available_points'], 4)
        with self.assertRaisesRegex(ValueError, 'fraction mismatch'):
            streaming.validate_diagnostic_context_coverage(record, [dict(context, fraction_of_source=1.0)])
        with self.assertRaisesRegex(ValueError, 'scope'):
            streaming.validate_diagnostic_context_coverage(record, [dict(context, source_available_points=76)])
