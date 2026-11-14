"""Software handoff checks, not additional NFL accuracy observations."""
import copy
import gzip
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from nfl_v2.qb_aligned_freshness import ALTERNATIVE
from nfl_v2.qb_aligned_freshness_adapter import QBAlignedFreshnessAdapter

ROOT=Path(__file__).resolve().parents[1]
WAVE=ROOT/'reports/profile-increment-closure-next-02/B/aligned-wave-v1'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):
    body=path.read_bytes();return json.loads(gzip.decompress(body) if path.suffix=='.gz' else body)


class AlignedAdapterTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protocol=WAVE/'FROZEN_PROTOCOL.json';cls.order=WAVE/'FEATURE_ORDER_V1.json'
        cls.model=WAVE/'fits/2026-W08-F3.json.gz'
        cls.adapter=cls.restore()
        cls.qq=[dict(r) for r in cls.adapter.inputs if(r['season'],r['week'])==(2026,8)][:2]

    @classmethod
    def restore(cls,**kw):
        return QBAlignedFreshnessAdapter(ROOT,kw.get('protocol',cls.protocol),cls.order,kw.get('model',cls.model),
            arm=kw.get('arm','F3'),expected_protocol_sha256=sha(kw.get('protocol',cls.protocol)),
            expected_model_sha256=sha(kw.get('model',cls.model)))

    def future_fixture(self,*,week=10):
        # These explicit synthetic receipts test shape/guards and authenticate
        # no actual current event, role, source validity or model admission.
        at=self.adapter.model_created_at+3600;cutoff=at-1
        q=dict(game_id='SOFTWARE_FUTURE_EVENT',player_id='SOFTWARE_UNSEEN_QB',team='WAS',opponent='NYG',
            position='QB',season=2026,week=week,kickoff=at+3600,cutoff=cutoff,native_event_id='SYNTHETIC_NATIVE_EVENT')
        q['query_evidence']=dict(canonical_identity_verified=True,historical_team_verified=True,eligible_role_verified=True,
            source_id='SYNTHETIC_MEMBERSHIP_FIXTURE_NOT_AUTHENTICATED',source_sha256='a'*64,recorded_at=cutoff-1)
        r=dict(player_id=q['player_id'],game_id=q['game_id'],team=q['team'],opponent=q['opponent'],position='QB',
            season=2026,week=week,native_event_id=q['native_event_id'],admission='QUALIFIED_AS_OF_EVENT_DECISION',
            evidence_sha256='b'*64,source_sha256='a'*64,source_effective_at=cutoff-3,observed_at=cutoff-2,
            retained_at=cutoff-1,effective_scope='REVIEWED_CARRY_FORWARD_AS_OF_CUTOFF',carry_forward_evidence_sha256='c'*64,
            expected_starter='UNKNOWN',source_week=9)
        r['event_status_receipt']=dict(game_id=q['game_id'],native_event_id=q['native_event_id'],season=2026,week=week,
            kickoff=q['kickoff'],state='pre',status_name='STATUS_SCHEDULED',completed=False,source_sha256='f'*64,
            expiry_policy_evidence_sha256='f'*64,registered_at=cutoff-3,observed_at=cutoff-2,expires_at=at+1800)
        o=dict(refit_rule='WEEKLY_BEFORE_FIRST_ELIGIBLE_GAME_H_RECENT',season=2026,week=8,fit_cutoff=self.adapter.fit_cutoff,
            model_sha256=self.adapter.bindings['model_sha256'],protocol_sha256=self.adapter.bindings['protocol_sha256'],
            information_policy=ALTERNATIVE,evidence_sha256='d'*64,registered_at=self.adapter.fit_cutoff-1,
            first_game_kickoff=at+900)
        c=dict(registered_at=cutoff-4,source_received_at=cutoff-1,source_cutoff=cutoff,
            source_expires_at=at+1800,model_expires_at=at+1800,policy_id='SYNTHETIC_EXPIRY_FIXTURE',evidence_sha256='e'*64,
            inputs_sha256=self.adapter.bindings['inputs_sha256'],opportunity_source_sha256=self.adapter.bindings['opportunity_source_sha256'])
        return q,r,o,c,at

    def current(self,q,r,o,c,at):
        return self.adapter.predict_current(q,feature_names=self.adapter.expected_feature_order,
            roster_receipt=r,origin_contract=o,clock_contract=c,request_at=at)

    def test_F3_saved_historical_parity_and_typed_products(self):
        q=self.qq[0];result=self.adapter.predict_historical(q,feature_names=self.adapter.expected_feature_order,line=19.5)
        saved=next(r for r in read(WAVE/'predictions/2026-W08.json.gz')['rows'] if r['method']=='F3'
            and r['game_id']==q['game_id'] and r['player_id']==q['player_id'])
        self.assertAlmostEqual(result['mean'],saved['mean'],places=10)
        self.assertEqual(result['lower_median'],saved['lower_median'])
        self.assertEqual(result['law'],saved['law'])
        self.assertEqual(result['mean_type'],'EXPECTED_MEAN')
        self.assertEqual(result['median_type'],'LOWER_MEDIAN')
        self.assertEqual(result['exact_threshold']['P2']['policy_id'],'P2')
        self.assertEqual(result['exact_threshold']['push'],0)
        self.assertAlmostEqual(sum(result['exact_threshold'][k] for k in ('over','under','push')),1)
        self.assertIn('HISTORICAL_RECONSTRUCTED',result['status'])
        self.assertFalse(result['inference_is_issuance'])

    def test_same_width_wrong_feature_order_and_ambiguous_mode(self):
        names=self.adapter.expected_feature_order;names[0],names[1]=names[1],names[0]
        with self.assertRaisesRegex(ValueError,'Named feature order'):
            self.adapter.predict_historical(self.qq[0],feature_names=names)
        with self.assertRaisesRegex(ValueError,'explicit historical or current'):
            self.adapter.predict(self.qq[0])

    def test_historical_batch_single_shuffle_and_duplicate(self):
        names=self.adapter.expected_feature_order
        batch=self.adapter.predict_historical_batch(self.qq,feature_names=names)
        self.assertEqual(batch,[self.adapter.predict_historical(q,feature_names=names) for q in self.qq])
        self.assertEqual(list(reversed(batch)),self.adapter.predict_historical_batch(list(reversed(self.qq)),feature_names=names))
        with self.assertRaisesRegex(ValueError,'Duplicate query'):
            self.adapter.predict_historical_batch([self.qq[0]]*2,feature_names=names)

    def test_future_unknown_outcome_does_not_allow_old_week8_model_for_week10(self):
        q,r,o,c,at=self.future_fixture()
        result=self.current(q,r,o,c,at)
        self.assertEqual((result['status'],result['reason']),('UNAVAILABLE_CURRENT_MODEL','WEEKLY_REFIT_ORIGIN_MISMATCH'))
        q.update(official_attempts=None,official_completions=None,available=None,physical_participation=None)
        self.assertEqual(result,self.current(q,r,o,c,at))

    def test_basic_roster_unknown_starter_and_reviewed_week_label(self):
        q,r,_,_,_=self.future_fixture()
        self.assertIsNone(self.adapter._roster_reason(q,r))
        r['effective_scope']='PRIOR_WEEK_LABEL_ONLY'
        self.assertEqual(self.adapter._roster_reason(q,r),'ROSTER_EFFECTIVE_SCOPE_UNREVIEWED')
        r['effective_scope']='REVIEWED_CARRY_FORWARD_AS_OF_CUTOFF';r['source_effective_at']=None
        self.assertEqual(self.adapter._roster_reason(q,r),'UNKNOWN_ROSTER_EFFECTIVE_CLOCK')

    def test_registered_expiry_and_current_origin_guards(self):
        q,r,o,c,at=self.future_fixture(week=8)
        c['source_expires_at']=at
        result=self.current(q,r,o,c,at)
        self.assertEqual(result['reason'],'REGISTERED_SOURCE_EXPIRED')
        c['source_expires_at']=at+100;c['model_expires_at']=at
        self.assertEqual(self.current(q,r,o,c,at)['reason'],'REGISTERED_MODEL_EXPIRED')
        c['model_expires_at']=at+100;o['refit_rule']='OLD_MODEL_ANY_WEEK'
        self.assertEqual(self.current(q,r,o,c,at)['reason'],'UNQUALIFIED_REGISTERED_WEEKLY_REFIT_CONTRACT')

    def test_native_future_status_requires_actual_bound_receipt(self):
        q,r,o,c,at=self.future_fixture(week=8)
        del r['event_status_receipt']
        self.assertEqual(self.current(q,r,o,c,at)['reason'],'MISSING_CURRENT_EVENT_STATUS_RECEIPT')
        q,r,o,c,at=self.future_fixture(week=8);r['event_status_receipt']['expires_at']=at
        self.assertEqual(self.current(q,r,o,c,at)['reason'],'REGISTERED_EVENT_STATUS_EXPIRED')

    def test_source_validity_covers_query_inputs_not_just_training_labels(self):
        q,r,o,c,at=self.future_fixture(week=8)
        c['source_cutoff']=self.adapter.model_record['latest_training_label']
        self.assertEqual(self.current(q,r,o,c,at)['reason'],'SOURCE_VALIDITY_CLOCK_CONFLICT')

    def test_late_historical_model_is_not_pregame_weekly_fit(self):
        q,r,o,c,at=self.future_fixture(week=8)
        o['first_game_kickoff']=self.adapter.fit_cutoff
        self.assertEqual(self.current(q,r,o,c,at)['reason'],'UNQUALIFIED_REGISTERED_WEEKLY_REFIT_CONTRACT')

    def test_explicit_unknown_history_clock_is_not_filled_during_restore(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d);protocol=read(self.protocol)
            source_path=ROOT/protocol['opportunity_source']['path'];source=read(source_path)
            source['team_games'][0]['available']=None
            sf=d/'unknown.json.gz';sf.write_bytes(gzip.compress(json.dumps(source).encode(),mtime=0))
            protocol['opportunity_source']=dict(path=str(sf),sha256=sha(sf))
            pf=d/'protocol.json';pf.write_text(json.dumps(protocol))
            with self.assertRaisesRegex(ValueError,'Unresolved history availability'):
                self.restore(protocol=pf)

    def test_F2_restoration_and_integer_push(self):
        adapter=self.restore(model=WAVE/'fits/2026-W08-F2.json.gz',arm='F2');q=self.qq[0]
        result=adapter.predict_historical(q,feature_names=adapter.expected_feature_order,line=20)
        saved=next(r for r in read(WAVE/'predictions/2026-W08.json.gz')['rows'] if r['method']=='F2'
            and r['game_id']==q['game_id'] and r['player_id']==q['player_id'])
        self.assertAlmostEqual(result['mean'],saved['mean'],places=10)
        self.assertGreater(result['exact_threshold']['push'],0)
        restored=self.restore(model=WAVE/'fits/2026-W08-F2.json.gz',arm='F2')
        self.assertEqual(result,restored.predict_historical(q,feature_names=restored.expected_feature_order,line=20))


if __name__=='__main__':unittest.main()
