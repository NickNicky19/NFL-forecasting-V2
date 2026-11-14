"""Output-preserving adapter checks; these add no NFL evaluation rows."""
import copy
import gzip
import hashlib
import json
import unittest
from pathlib import Path

from nfl_v2.qb_opportunity_adapter import QBOpportunityAdapter

ROOT=Path(__file__).resolve().parents[1]
WAVE=ROOT/'reports/profile-increment-to-release-01/B/opportunity-wave-v1'


def read(path):
    body=path.read_bytes()
    return json.loads(gzip.decompress(body) if path.suffix=='.gz' else body)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class AdapterTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protocol=WAVE/'FROZEN_PROTOCOL.json'
        cls.order=WAVE/'FEATURE_ORDER_V1.json'
        cls.model=WAVE/'fits/2025-W01-R2.json.gz'
        cls.adapter=QBOpportunityAdapter(ROOT,cls.protocol,cls.order,cls.model,arm='R2',
            expected_protocol_sha256=sha(cls.protocol),expected_model_sha256=sha(cls.model))
        inputs=cls.adapter.inputs
        cls.queries=[dict(r) for r in inputs if(r['season'],r['week'])==(2025,1)][:2]
        # Explicitly synthetic membership proof tests the software contract;
        # it does not authenticate historical roster membership.
        for q in cls.queries:
            q['query_evidence']=dict(canonical_identity_verified=True,historical_team_verified=True,eligible_role_verified=True,
                source_id='SYNTHETIC_SOFTWARE_MEMBERSHIP_FIXTURE',source_sha256='a'*64,recorded_at=q['kickoff']-1)

    def contract(self,q):
        return dict(policy_id='SYNTHETIC_SOFTWARE_EXPIRY_FIXTURE',evidence_sha256='b'*64,
                    registered_at=q['kickoff']-2,source_received_at=q['kickoff']-1,
                    source_expires_at=q['kickoff']+100000,model_expires_at=q['kickoff']+100000)

    def predict(self,q,**kw):
        return self.adapter.predict(q,feature_names=self.adapter.expected_feature_order,
            clock_contract=self.contract(q),request_at=q['kickoff'],**kw)

    def test_saved_case_parity_and_exact_line(self):
        q=self.queries[0];r=self.predict(q,line=19.5)
        saved=next(r for r in read(WAVE/'predictions/2025-W01.json.gz')['rows']
                   if r['method']=='R2' and r['game_id']==q['game_id'] and r['player_id']==q['player_id'])
        self.assertEqual(r['status'],'READY_ADAPTER_INFERENCE')
        self.assertAlmostEqual(r['mean'],saved['mean'],places=10)
        self.assertEqual(r['lower_median'],saved['lower_median'])
        self.assertAlmostEqual(sum(r['exact_threshold'][x] for x in ('over','under','push')),1.,places=12)
        self.assertEqual(r['exact_threshold']['push'],0.)
        self.assertFalse(r['inference_is_issuance'])

    def test_named_same_width_wrong_order_is_rejected(self):
        names=self.adapter.expected_feature_order;names[0],names[1]=names[1],names[0]
        with self.assertRaisesRegex(ValueError,'Named feature order'):
            self.adapter.predict(self.queries[0],feature_names=names,clock_contract={},request_at=0)

    def test_batch_single_shuffled_identity(self):
        qq=self.queries;request_at=max(q['kickoff'] for q in qq);contract=self.contract(qq[0])
        contract['source_expires_at']=contract['model_expires_at']=request_at+100000
        batch=self.adapter.predict_batch(qq,feature_names=self.adapter.expected_feature_order,clock_contract=contract,request_at=request_at)
        singles=[self.adapter.predict(q,feature_names=self.adapter.expected_feature_order,clock_contract=contract,request_at=request_at) for q in qq]
        self.assertEqual(batch,singles)
        shuffled=self.adapter.predict_batch(list(reversed(qq)),feature_names=self.adapter.expected_feature_order,clock_contract=contract,request_at=request_at)
        self.assertEqual(shuffled,list(reversed(batch)))

    def test_unqualified_and_expired_are_distinct(self):
        q=copy.deepcopy(self.queries[0]);del q['query_evidence']
        self.assertEqual(self.predict(q)['status'],'UNAVAILABLE_QUERY')
        q=self.queries[0];contract=self.contract(q);contract['source_expires_at']=q['kickoff']
        r=self.adapter.predict(q,feature_names=self.adapter.expected_feature_order,clock_contract=contract,request_at=q['kickoff'])
        self.assertEqual((r['status'],r['reason']),('UNAVAILABLE_SOURCE','REGISTERED_SOURCE_EXPIRED'))
        contract=self.contract(q);contract['model_expires_at']=q['kickoff']
        r=self.adapter.predict(q,feature_names=self.adapter.expected_feature_order,clock_contract=contract,request_at=q['kickoff'])
        self.assertEqual(r['status'],'UNAVAILABLE_MODEL')

    def test_future_unknown_outcome_and_unseen_player(self):
        q=copy.deepcopy(self.queries[0]);q.update(player_id='CANONICAL_UNSEEN_FIXTURE',game_id='FUTURE_FIXTURE')
        for key in ('official_completions','official_attempts','attempts','completions','physical_participation','target_parity','available','label_status'):
            q.pop(key,None)
        r=self.predict(q)
        self.assertEqual(r['status'],'READY_ADAPTER_INFERENCE')
        self.assertEqual(r['own_prior_games'],0)
        self.assertIn('UNSEEN',r['own_history_state'])
        # Invented target labels cannot change inference.
        q.update(official_completions=1000,official_attempts=1000,available=None)
        self.assertEqual(r,self.predict(q))

    def test_hash_and_duplicate_identity_checks(self):
        with self.assertRaisesRegex(ValueError,'hash mismatch'):
            QBOpportunityAdapter(ROOT,self.protocol,self.order,self.model,arm='R2',expected_protocol_sha256='0'*64,
                                 expected_model_sha256=sha(self.model))
        with self.assertRaisesRegex(ValueError,'Duplicate query'):
            self.adapter.predict_batch([self.queries[0]]*2,feature_names=self.adapter.expected_feature_order,
                                       clock_contract={},request_at=0)

    def test_integer_push_and_deterministic_restoration(self):
        q=self.queries[0];r=self.predict(q,line=20)
        self.assertGreater(r['exact_threshold']['push'],0)
        restored=QBOpportunityAdapter(ROOT,self.protocol,self.order,self.model,arm='R2',
            expected_protocol_sha256=sha(self.protocol),expected_model_sha256=sha(self.model))
        rr=restored.predict(q,feature_names=restored.expected_feature_order,clock_contract=self.contract(q),request_at=q['kickoff'],line=20)
        self.assertEqual(r,rr)

    def test_reused_control_preserves_missing_original_membership_limit(self):
        model=ROOT/'reports/player-context-matchup-01/B/qb-wave-v1/fits/2025-W01-E3.json.gz'
        adapter=QBOpportunityAdapter(ROOT,self.protocol,self.order,model,arm='R0',
            expected_protocol_sha256=sha(self.protocol),expected_model_sha256=sha(model))
        q=self.queries[0]
        r=adapter.predict(q,feature_names=adapter.expected_feature_order,clock_contract=self.contract(q),request_at=q['kickoff'])
        saved=next(r for r in read(WAVE/'predictions/2025-W01.json.gz')['rows']
                   if r['method']=='R0' and r['game_id']==q['game_id'] and r['player_id']==q['player_id'])
        self.assertAlmostEqual(r['mean'],saved['mean'],places=10)
        self.assertIn('RECONSTRUCTED_R0_MEMBERSHIP',r['bindings']['prior_membership_evidence'])


if __name__=='__main__':unittest.main()
