import gzip,hashlib,json,unittest
from pathlib import Path
from nfl_v2.player_context_named_adapter_v3 import NamedLeafAdapter
from nfl_v2.distribution_laws import prior
from nfl_v2.player_context_matchup import load_inputs,VERSION

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'reports/player-context-matchup-01/B'

class NamedContextAdapterTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema=(BASE/'qb-wave-v1/FEATURE_ORDER_V1.json').read_bytes()
        cls.receipt=(BASE/'qb-wave-v1/fits/2025-W01-E1.json.gz').read_bytes()
        inputs=load_inputs(BASE/'source-fields-v3/DERIVED_QB_GAME_INPUTS.json.gz')
        packet=json.loads(gzip.decompress((BASE/'qb-wave-v1/predictions/2025-W01.json.gz').read_bytes()))
        train=[r for r in inputs if r['physical_participation']and r['target_parity']and r['season']>=2024 and r['available']<packet['fit_cutoff']]
        cls.prior=prior([r['official_completions']for r in train],'pass_cmp')
        cls.rows=[r for r in packet['rows']if r['method']=='E1']
        cls.names=json.loads(cls.schema)['orders']['E1']

    def adapter(self):
        return NamedLeafAdapter(schema_bytes=self.schema,expected_schema_sha256=hashlib.sha256(self.schema).hexdigest(),receipt_bytes=self.receipt,
            expected_receipt_sha256=hashlib.sha256(self.receipt).hexdigest(),arm='E1',fallback_prior=self.prior,
            expected_prior_sha256=hashlib.sha256(json.dumps(self.prior.parameters(),sort_keys=True,separators=(',',':')).encode()).hexdigest(),producer_version=VERSION)

    def test_preserved_predictions_and_shuffled_batch_identity(self):
        records=[dict(query_id=r['game_id']+':'+r['player_id'],feature_names=self.names,feature_values=r['features'])for r in self.rows]
        got=self.adapter().predict_batch(list(reversed(records)));expected={r['game_id']+':'+r['player_id']:r for r in self.rows}
        for r in got:
            self.assertAlmostEqual(r['law'].mean,expected[r['query_id']]['mean'],places=11)
            self.assertEqual(r['law'].quantile(.5),expected[r['query_id']]['lower_median'])

    def test_wrong_columns_hashes_and_duplicate_ids_rejected(self):
        r=self.rows[0];names=list(self.names);names[0],names[1]=names[1],names[0]
        with self.assertRaises(ValueError):self.adapter().predict_one(feature_names=names,feature_values=r['features'])
        rec=dict(query_id='duplicate',feature_names=self.names,feature_values=r['features'])
        with self.assertRaises(ValueError):self.adapter().predict_batch([rec,rec])
        with self.assertRaises(ValueError):NamedLeafAdapter(schema_bytes=self.schema,expected_schema_sha256='0'*64,receipt_bytes=self.receipt,
            expected_receipt_sha256=hashlib.sha256(self.receipt).hexdigest(),arm='E1',fallback_prior=self.prior,expected_prior_sha256='0'*64,producer_version=VERSION)
        with self.assertRaises(ValueError):NamedLeafAdapter(schema_bytes=self.schema,expected_schema_sha256=hashlib.sha256(self.schema).hexdigest(),receipt_bytes=self.receipt,
            expected_receipt_sha256=hashlib.sha256(self.receipt).hexdigest(),arm='E1',fallback_prior=self.prior,expected_prior_sha256='0'*64,producer_version=VERSION)

if __name__=='__main__':unittest.main()
