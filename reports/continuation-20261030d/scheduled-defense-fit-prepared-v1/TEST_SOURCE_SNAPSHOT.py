import json,tempfile,unittest
from pathlib import Path
import numpy as np
from nfl_v2 import scheduled_defense_wave as w


class ScheduledDefenseWaveTests(unittest.TestCase):
    def files(self,tmp,restore=True):
        root=Path(tmp)
        values={'restoration':dict(full_restore_pass=restore,archives_verified=True,source_file_map_checked=True,completed_at_utc='2026-10-30T00:00:00+00:00',archive_bindings=[dict(sha256='a'*64)]),
                'review':dict(state='PASS_PREFIT_PROTOCOL_REVIEW',protocol_sha256='p'),
                'software':dict(status='PASS',code_sha256=w.sha(w.__file__))}
        for k,v in values.items():(root/k).write_text(json.dumps(v))
        release=dict(worker_release=True,protocol_sha256='p',restoration_gate_sha256=w.sha(root/'restoration'),max_new_fits=308,phases=['historical','future'],released_at_utc='2026-10-30T00:00:01+00:00')
        (root/'worker').write_text(json.dumps(release))
        return dict(restoration_gate=root/'restoration',worker_release=root/'worker',review=root/'review',software=root/'software',phase='historical')

    def test_unchanged_training_reuses_instead_of_fitting(self):
        self.assertEqual(w.action('FITTED_RETAINED',False),'REUSE_UNCHANGED_TRAINING_MODEL')
    def test_affected_training_requires_new_fit(self):
        self.assertEqual(w.action('FITTED_RETAINED',True),'REFIT_AFFECTED_TRAINING')
    def test_no_model_prior_can_ignore_defense_change(self):
        self.assertEqual(w.action('NO_FIT_INSUFFICIENT_TRAINING',True),'REUSE_DECLARED_NO_MODEL_PRIOR')
    def test_failed_original_cannot_be_silently_reused(self):
        with self.assertRaises(ValueError):w.action('FIT_FAILED_FALLBACK',False)
    def test_matrix_hash_tracks_shape_values_age_and_missing(self):
        a=np.asarray([[1.,np.nan]])
        self.assertEqual(w.array_digest(a),w.array_digest(a.copy()))
        self.assertNotEqual(w.array_digest(a),w.array_digest([[1.,0.]]))
        self.assertNotEqual(w.array_digest(a),w.array_digest([[2.,np.nan]]))
        self.assertNotEqual(w.array_digest(a),w.array_digest([1.,np.nan]))
    def test_provider_capacity_claim_without_verified_restore_rejected(self):
        with tempfile.TemporaryDirectory()as tmp:
            kw=self.files(tmp,False)
            with self.assertRaisesRegex(ValueError,'restoration'):w.gates(dict(protocol_sha256='p'),**kw)
    def test_verified_restore_without_source_file_map_rejected(self):
        with tempfile.TemporaryDirectory()as tmp:
            kw=self.files(tmp);p=Path(kw['restoration_gate']);r=json.loads(p.read_text());r['source_file_map_checked']=False;p.write_text(json.dumps(r))
            with self.assertRaises(ValueError):w.gates(dict(protocol_sha256='p'),**kw)
    def test_worker_release_separately_bound_to_exact_restore(self):
        with tempfile.TemporaryDirectory()as tmp:
            kw=self.files(tmp);p=Path(kw['worker_release']);r=json.loads(p.read_text());r['restoration_gate_sha256']='wrong';p.write_text(json.dumps(r))
            with self.assertRaisesRegex(ValueError,'worker'):w.gates(dict(protocol_sha256='p'),**kw)
    def test_no_768_fit_permission(self):
        with tempfile.TemporaryDirectory()as tmp:
            kw=self.files(tmp);p=Path(kw['worker_release']);r=json.loads(p.read_text());r['max_new_fits']=768;p.write_text(json.dumps(r))
            with self.assertRaises(ValueError):w.gates(dict(protocol_sha256='p'),**kw)
    def test_only_fictional_complete_gate_fixture_passes(self):
        with tempfile.TemporaryDirectory()as tmp:
            kw=self.files(tmp);proof=w.gates(dict(protocol_sha256='p'),**kw);self.assertIn('restoration_gate_sha256',proof)
    def test_bundle_escape_and_modified_bytes_rejected(self):
        with tempfile.TemporaryDirectory()as tmp:
            with self.assertRaises(ValueError):w.member(tmp,dict(bundle_name='../private',sha256='a'*64))
            p=Path(tmp)/'fiction';p.write_bytes(b'one')
            with self.assertRaises(ValueError):w.member(tmp,dict(bundle_name='fiction',sha256='a'*64))
            self.assertEqual(w.member(tmp,dict(bundle_name='fiction',sha256=w.sha(p))),p)
    def test_separate_identity_fixed_family_and_672_plus96_cells(self):
        self.assertEqual(w.FAMILY,'ordered_leaf_cdf');self.assertEqual(len(w.TARGETS)*len(w.POLICIES)*len(w.GROUPS)*7,672)
        self.assertEqual(len(w.TARGETS)*len(w.POLICIES)*len(w.GROUPS),96)
        self.assertNotEqual(w.proc('D1','H-MULTI-COMMON'),w.old_wave.proc('D1','H-MULTI-COMMON'))

if __name__=='__main__':unittest.main()
