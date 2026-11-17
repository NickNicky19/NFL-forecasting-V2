"""Invented software fixtures only. No actual Week8 outcomes are read."""
import copy
import gzip
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from nfl_v2.result_index import evaluation, validate_index
from nfl_v2.shadow_grading import (CAPTURE_VERSION, CONTRACTS, LABEL_SCHEMA,
    canonical, grade_bytes, grade_files)


def digest(body):
    return hashlib.sha256(body).hexdigest()


def fixture(abstain=False):
    # Deliberately past, fictional dates/IDs allow clock checks without NFL outcomes.
    queries=[]
    for i,target in enumerate(("rush_yd","rec","anytime_td")):
        queries.append(dict(query_id="fixture-q"+str(i),sleeper_id="fixture-s"+str(i),
            player_id=None if abstain and i==1 else "fictional-player"+str(i),
            position="RB",target=target,game_id="fictional-game",espn_game_id="fictional-espn",
            kickoff_utc="2020-11-01T18:00:00Z",owner_input_cutoff_utc="2020-11-01T16:30:00Z",
            blocked_reason="UNKNOWN_IDENTITY" if abstain and i==1 else None))
    qhash=digest(canonical(queries))
    protocol=dict(version=CAPTURE_VERSION,query_membership_sha256=qhash,
        source_tier="fictional current-vintage fixture only",histories={"H-CURRENT":[2026],"H-RECENT":[2025,2026],"H-MULTI":[2022,2023,2024,2025,2026]},
        feature_memory="no football predictors; fixture only")
    protocol_bytes=canonical(protocol);phash=digest(protocol_bytes)
    rows=[]
    for q in queries:
        for arm in ("H-CURRENT","H-RECENT","H-MULTI"):
            for product in (("event_probability",) if q['target']=='anytime_td' else ("empirical_mean","lower_median")):
                blocked=q['blocked_reason'] is not None
                prediction={"rush_yd":-2.,"rec":2.25 if product=='empirical_mean' else 2.,"anytime_td":.25}[q['target']]
                rows.append(dict(q,run_id=CAPTURE_VERSION,history_regime=arm,product=product,
                    prediction=None if blocked else prediction,status="ABSTAIN" if blocked else "ISSUED_SHADOW",
                    abstention_reason=q['blocked_reason'],fallback=None if blocked else "none",
                    feature_cutoff_utc="2020-10-31T12:00:00Z",issued_at_utc="2020-10-31T12:00:01Z",
                    owner_cutoff_status="BEFORE_OWNER_INPUT_CUTOFF",actual_horizon_seconds=107999,
                    protocol_sha256=phash))
    body=canonical(dict(schema=CAPTURE_VERSION,rows=rows));blob=gzip.compress(body,mtime=0)
    receipt=dict(version=CAPTURE_VERSION,protocol_sha256=phash,
        private_forecast_sha256=digest(blob),private_uncompressed_sha256=digest(body),
        query_membership_sha256=qhash,query_cells=len(queries),forecast_output_rows=len(rows),
        actual_feature_cutoff_utc="2020-10-31T12:00:00Z",actual_inference_started_at="2020-10-31T12:00:00Z",
        actual_inference_completed_at="2020-10-31T12:00:02Z",actual_persistence_completed_at="2020-10-31T12:00:03Z",
        source_ids=[dict(name="fictional-only.csv",sha256="0"*64)])
    admission=dict(source_id="FICTIONAL-SOURCE",source_tier="current_vintage_final_snapshot",
        identity_contract_id="fixture-identity",statistic_contract_id="fixture-explicit",
        participation_contract_id="fixture-played",finality_contract_id="fixture-final",
        availability_basis_id="fixture-invented-clock")
    labels=[]
    for q,y in zip(queries,(0.,2.,1)):
        if q['blocked_reason']:continue
        labels.append(dict(query_id=q['query_id'],player_id=q['player_id'],game_id=q['game_id'],
            target=q['target'],contract_id=CONTRACTS[q['target']],actual=y,state="played",
            game_completed=True,finality="final",source_id="FICTIONAL-SOURCE",revision_id=None,
            available_utc="2020-11-01T23:00:00Z",observed_utc="2020-11-02T00:00:00Z"))
    packet=dict(schema=LABEL_SCHEMA,label_version_id="fixture-label-v1",source_admissions=[admission],labels=labels)
    return dict(blob=blob,receipt=receipt,protocol_bytes=protocol_bytes,packet=packet)


def grade(f,**changes):
    rb=canonical(f['receipt'])
    args=dict(expected_forecast_sha256=f['receipt']['private_forecast_sha256'],
        expected_capture_receipt_sha256=digest(rb),asof_utc="2020-11-02T12:00:00Z",run_id="fixture-grading-v1")
    args.update(changes)
    return grade_bytes(f['blob'],rb,f['protocol_bytes'],canonical(f['packet']),**args)


class ShadowGradingTests(unittest.TestCase):
    def test_empty_packet_keeps_every_forecast_pending(self):
        f=fixture();f['packet']['labels']=[]
        scores,errors,receipt=grade(f)
        self.assertEqual(len(errors),15);self.assertEqual(len(scores),15)
        self.assertEqual(receipt['scored_forecast_rows'],0)
        self.assertFalse(receipt['whole_week_complete'])
        self.assertEqual(receipt['query_states'],{'pending_no_label':3})
        self.assertTrue(all(r['n']==0 and r['mae'] is None for r in scores))

    def test_explicit_zero_signed_points_count_tolerances_and_brier(self):
        scores,errors,receipt=grade(fixture())
        rush=next(r for r in scores if r['target']=='rush_yd'and r['history_regime']=='H-CURRENT'and r['product_id']=='empirical_mean')
        self.assertEqual(rush['mae'],2);self.assertEqual(rush['bias'],-2)
        self.assertEqual(rush['abs_lt_1'],0);self.assertEqual(rush['abs_le_5'],1)
        td=next(r for r in scores if r['target']=='anytime_td')
        self.assertEqual(td['brier'],.5625)
        self.assertTrue(receipt['whole_week_complete'])
        validate_index([evaluation(r,'reports/fictional/SCORES.json')for r in scores])
        f=fixture();f['packet']['labels'][0]['actual']=-7.
        r=next(r for r in grade(f)[0] if r['target']=='rush_yd')
        self.assertEqual(r['abs_lt_5'],0);self.assertEqual(r['abs_le_5'],1)

    def test_hash_receipt_protocol_and_duplicate_capture_rejected(self):
        f=fixture()
        with self.assertRaises(ValueError):grade(f,expected_forecast_sha256='0'*64)
        with self.assertRaises(ValueError):grade(f,expected_capture_receipt_sha256='0'*64)
        f['protocol_bytes']+=b' '
        with self.assertRaises(ValueError):grade(f)
        f=fixture();body=json.loads(gzip.decompress(f['blob']));body['rows'].append(body['rows'][0]);b=canonical(body)
        f['blob']=gzip.compress(b,mtime=0);f['receipt'].update(private_forecast_sha256=digest(f['blob']),private_uncompressed_sha256=digest(b),forecast_output_rows=len(body['rows']))
        with self.assertRaises(ValueError):grade(f)

    def test_unfinalized_and_future_numeric_labels_rejected(self):
        for field,value in [('game_completed',False),('finality','pending'),('available_utc','2020-11-03T23:00:00Z'),('observed_utc','2020-11-03T00:00:00Z'),('available_utc','2020-11-01T18:00:00Z')]:
            f=fixture();f['packet']['labels'][0][field]=value
            with self.subTest(field=field,value=value),self.assertRaises(ValueError):grade(f)
        f=fixture();f['packet']['labels'][0]['actual']=None;f['packet']['labels'][0]['game_completed']=False;f['packet']['labels'][0]['finality']='pending'
        _,_,r=grade(f);self.assertFalse(r['whole_week_complete']);self.assertEqual(r['query_states']['pending_or_unverified_finality'],1)

    def test_duplicate_wrong_identity_or_contract_labels_rejected(self):
        for field,value in [('query_id','not-frozen'),('player_id','other'),('game_id','other'),('target','rec'),('contract_id','website-PPR'),('source_id','not-admitted')]:
            f=fixture();f['packet']['labels'][0][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):grade(f)
        f=fixture();f['packet']['labels'].append(copy.deepcopy(f['packet']['labels'][0]))
        with self.assertRaises(ValueError):grade(f)

    def test_invalid_counts_and_nonfinite_labels_rejected(self):
        for value in (-1,.5,float('nan')):
            f=fixture();f['packet']['labels'][1]['actual']=value
            with self.subTest(value=value),self.assertRaises(ValueError):grade(f)
        f=fixture();f['packet']['labels'][2]['actual']=2
        with self.assertRaises(ValueError):grade(f)
        f=fixture();del f['packet']['labels'][0]['actual']
        with self.assertRaises(ValueError):grade(f)

    def test_DNP_unknown_missing_never_zero_imputed(self):
        for state in ('DNP','unknown','played_missing','missing'):
            f=fixture();f['packet']['labels'][0].update(state=state,actual=None)
            scores,errors,receipt=grade(f)
            rush=[r for r in scores if r['target']=='rush_yd']
            self.assertTrue(all(r['n']==0 and r['mae'] is None for r in rush))
            self.assertTrue(all(r['signed_error'] is None for r in errors if r['target']=='rush_yd'))
            if state!='DNP':self.assertFalse(receipt['whole_week_complete'])
        f=fixture();f['packet']['labels'][0]['state']='DNP'
        with self.assertRaises(ValueError):grade(f)

    def test_abstention_and_partial_week_remain_coverage(self):
        scores,errors,receipt=grade(fixture(abstain=True))
        self.assertEqual(receipt['abstention_forecast_rows'],6)
        self.assertEqual(receipt['scored_forecast_rows'],9)
        self.assertFalse(receipt['whole_week_complete'])
        self.assertTrue(all(r['coverage']['abstention_rows']==1 for r in scores if r['target']=='rec'))

    def test_official_pre_kickoff_cancellation_is_terminal_without_numeric_score(self):
        f=fixture()
        f['packet']['labels'][0].update(state='canceled',actual=None,finality='canceled',game_completed=False,
            available_utc='2020-11-01T12:00:00Z',observed_utc='2020-11-01T12:05:00Z')
        scores,errors,receipt=grade(f)
        self.assertTrue(receipt['whole_week_complete'])
        self.assertEqual(receipt['query_states']['qualified_final_canceled'],1)
        self.assertTrue(all(r['n']==0 for r in scores if r['target']=='rush_yd'))
        self.assertTrue(all(r['absolute_error'] is None for r in errors if r['target']=='rush_yd'))
        # Unfinished is not cancellation, and cancellation never supplies zero.
        f['packet']['labels'][0]['actual']=0
        with self.assertRaises(ValueError):grade(f)
        f['packet']['labels'][0].update(actual=None,state='pending',finality='pending',
            available_utc='2020-11-01T23:00:00Z',observed_utc='2020-11-02T00:00:00Z')
        _,_,receipt=grade(f)
        self.assertFalse(receipt['whole_week_complete'])
        self.assertEqual(receipt['query_states']['pending_or_unverified_finality'],1)

    def test_history_cohort_hashes_equal_without_merging_views(self):
        scores,_,_=grade(fixture())
        for target in ('rush_yd','rec','anytime_td'):
            rows=[r for r in scores if r['target']==target]
            self.assertEqual(len({r['frozen_prediction_query_cohort_sha256']for r in rows}),1)
            self.assertEqual(len({r['scored_query_cohort_sha256']for r in rows}),1)
            self.assertEqual({r['history_regime']for r in rows},{'H-CURRENT','H-RECENT','H-MULTI'})
        self.assertEqual(len(scores),15)

    def test_issued_capture_cannot_override_an_identity_or_abstention_block(self):
        for field in ('blocked_reason','abstention_reason'):
            f=fixture();body=json.loads(gzip.decompress(f['blob']))
            for row in body['rows']:
                if row['query_id']=='fixture-q0':row[field]='UNKNOWN_IDENTITY'
            # Bind the altered cohort, protocol, row protocol IDs and hashes so
            # the negative case tests semantic integrity beyond byte integrity.
            queries={}
            from nfl_v2.shadow_grading import QUERY_FIELDS
            for row in body['rows']:
                queries.setdefault(row['query_id'],{k:row[k]for k in QUERY_FIELDS})
            protocol=json.loads(f['protocol_bytes']);protocol['query_membership_sha256']=digest(canonical(list(queries.values())))
            f['protocol_bytes']=canonical(protocol);phash=digest(f['protocol_bytes'])
            for row in body['rows']:row['protocol_sha256']=phash
            raw=canonical(body);f['blob']=gzip.compress(raw,mtime=0)
            f['receipt'].update(protocol_sha256=phash,query_membership_sha256=protocol['query_membership_sha256'],
                private_forecast_sha256=digest(f['blob']),private_uncompressed_sha256=digest(raw))
            with self.subTest(field=field),self.assertRaises(ValueError):grade(f)

    def test_aware_clocks_source_contracts_and_infinite_loss_preserved(self):
        f=fixture();f['packet']['labels'][0]['available_utc']='2020-11-01T23:00:00'
        with self.assertRaises(ValueError):grade(f)
        f=fixture();f['packet']['source_admissions'][0]['availability_basis_id']=''
        with self.assertRaises(ValueError):grade(f)
        f=fixture();body=json.loads(gzip.decompress(f['blob']))
        for r in body['rows']:
            if r['target']=='anytime_td':r['prediction']=0
        b=canonical(body);f['blob']=gzip.compress(b,mtime=0);f['receipt'].update(private_forecast_sha256=digest(f['blob']),private_uncompressed_sha256=digest(b))
        scores,_,_=grade(f)
        for r in scores:
            if r['target']=='anytime_td':self.assertEqual(r['log_loss'],'Infinity');self.assertEqual(r['infinite_NLL'],1)

    def test_fresh_files_only_private_errors_outside_public_repo(self):
        f=fixture()
        with tempfile.TemporaryDirectory()as temp:
            root=Path(temp)
            for name,body in [('forecast.gz',f['blob']),('receipt.json',canonical(f['receipt'])),('protocol.json',f['protocol_bytes']),('labels.json',canonical(f['packet']))]:(root/name).write_bytes(body)
            kwargs=dict(forecasts=root/'forecast.gz',capture_receipt=root/'receipt.json',capture_protocol=root/'protocol.json',labels=root/'labels.json',expected_forecast_sha256=f['receipt']['private_forecast_sha256'],expected_capture_receipt_sha256=digest(canonical(f['receipt'])),asof_utc='2020-11-02T12:00:00Z',run_id='fixture-grading-v1',public_output=root/'public',private_output=root/'private')
            before=digest((root/'forecast.gz').read_bytes());summary=grade_files(**kwargs)
            self.assertEqual(summary['new_forecasts'],0);self.assertEqual(digest((root/'forecast.gz').read_bytes()),before)
            self.assertTrue((root/'private/player-errors.json.gz').exists())
            self.assertFalse(any('player_id'in r for r in json.loads((root/'public/SCORES.json').read_bytes())))
            with self.assertRaises(ValueError):grade_files(**kwargs)


if __name__=='__main__':unittest.main()
