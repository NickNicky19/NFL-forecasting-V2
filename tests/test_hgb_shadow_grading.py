"""Fictional software fixtures only: no actual Week8 outcomes or model calls."""
import copy
import gzip
import tempfile
import unittest
from pathlib import Path

from nfl_v2.hgb_shadow_grading import (BINDING_SCHEMA, CAPTURE_VERSION,
    collect_bindings, grade_bytes, grade_files, objectives)
from nfl_v2.result_index import evaluation, validate_index
from nfl_v2.shadow_grading import ARMS, CONTRACTS, LABEL_SCHEMA, canonical, digest


def descriptor(name, body, artifacts):
    blob=gzip.compress(body,mtime=0);artifacts[name]=blob
    return dict(name=name,bytes=len(blob),sha256=digest(blob),uncompressed_sha256=digest(body))


def fixture(blocked=False):
    queries=[]
    for i,t in enumerate(("rush_yd","rec","anytime_td")):
        queries.append(dict(query_id="fictional-q"+str(i),player_id="fictional-player"+str(i),
            sleeper_id="fictional-s"+str(i),position="RB",target=t,game_id="fictional-game",
            espn_game_id="fictional-event",kickoff_utc="2020-11-01T18:00:00Z",
            owner_input_cutoff_utc="2020-10-31T11:00:00Z",
            blocked_reason="UNKNOWN_IDENTITY" if blocked and i==1 else None))
    protocol=dict(version=CAPTURE_VERSION,registered_at_utc="2020-10-31T11:59:00Z",code_sha256="1"*64,
        week8_query_cells=3,history_regimes={"H-CURRENT":[2026],"H-RECENT":[2025,2026],"H-MULTI":[2022,2023,2024,2025,2026]},
        feature_memory="fictional common feature memory",availability="fictional current-vintage fixture",
        output_contract="absolute-loss point, squared-loss intendedmean; no numeric distribution")
    bindings=dict(schema=BINDING_SCHEMA,execution=dict(version=CAPTURE_VERSION,
        actual_started_at="2020-10-31T12:00:00Z",actual_week8_feature_origin_utc="2020-10-31T12:00:00Z"),
        run=dict(version=CAPTURE_VERSION,code_sha256="1"*64),fits=[],forecasts=[])
    cutoff=1604145600.;kickoff=1604253600.
    rows=[];artifacts={}
    for q in queries:
        for arm in sorted(ARMS):
            for objective in objectives(q['target']):
                slot=f"W08-{q['target']}-{arm}-{objective}"
                model=descriptor("models/"+slot+".pickle.gz",b"fictional opaque bytes never unpickled",artifacts)
                features=descriptor("query-features/"+slot+".json.gz",b"[]",artifacts)
                fit=dict(slot=slot,state="FITTED_RETAINED",origin=8,target=q['target'],history_regime=arm,
                    objective=objective,fit_cutoff_utc="2020-10-31T12:00:00Z",training_n=50,training_seasons=[2026],
                    latest_training_feature_available=cutoff-100,latest_training_label_available=cutoff-100,
                    actual_fit_started_at="2020-10-31T12:00:00Z",actual_fit_completed_at="2020-10-31T12:00:01Z",
                    model=model,query_features=features)
                bindings['fits'].append(fit)
                p={"rush_yd":-2.,"rec":2.25,"anytime_td":.25}[q['target']]
                row=dict(q,objective=objective,history_regime=arm,prediction=None if q['blocked_reason'] else p,
                    actual=None,status="ABSTAIN" if q['blocked_reason'] else "FORECASTED",abstention_reason=q['blocked_reason'],
                    fallback=None if q['blocked_reason'] else "none",cutoff=cutoff,kickoff=kickoff,season=2026,week=8,
                    population="original_pregame_feed",run_id=CAPTURE_VERSION,fit_slot=slot,fit_state="FITTED_RETAINED",
                    evidence_tier="genuine_new_research_pregame_shadow",issued_at_utc="2020-10-31T12:00:02Z",
                    actual_generated_at="2020-10-31T12:00:02Z",actual_horizon_seconds=107998.,
                    owner_cutoff_status="LATER_THAN_OWNER_INPUT_CUTOFF",latest_feature_available=cutoff-50,
                    latest_fallback_available=None)
                rows.append(row)
                bindings['forecasts'].append(dict(slot=slot,rows=1,forecasted=int(not q['blocked_reason']),
                    abstained=int(bool(q['blocked_reason'])),actual_persistence_completed_at="2020-10-31T12:00:03Z"))
    source=dict(source_id="FICTIONAL",source_tier="current_vintage_final_snapshot",identity_contract_id="fixture-identity",
        statistic_contract_id="fixture-explicit",participation_contract_id="fixture-played",finality_contract_id="fixture-final",availability_basis_id="fixture-clock")
    labels=[]
    for q,y in zip(queries,(0.,2.,1)):
        labels.append(dict(query_id=q['query_id'],player_id=q['player_id'],game_id=q['game_id'],target=q['target'],
            contract_id=CONTRACTS[q['target']],source_id='FICTIONAL',actual=y,state='played',game_completed=True,
            finality='final',available_utc='2020-11-01T23:00:00Z',observed_utc='2020-11-02T00:00:00Z'))
    receipt=dict(version=CAPTURE_VERSION,output_views=len(rows),queries=3,unique_games=1,
        cutoff_utc="2020-10-31T12:00:00Z",actual_completed_at="2020-10-31T12:00:04Z",
        official_capture=False,website_published=False)
    f=dict(queries=dict(historical=[],week8=queries),protocol=protocol,bindings=bindings,artifacts=artifacts,
        rows=rows,receipt=receipt,labels=dict(schema=LABEL_SCHEMA,label_version_id="fixture-label-v1",source_admissions=[source],labels=labels))
    return rebind(f)


def rebind(f):
    qbytes=canonical(f['queries']);p=f['protocol']
    p.update(frozen_queries_sha256=digest(qbytes),week8_membership_sha256=digest(canonical(f['queries']['week8'])))
    phash=digest(canonical(p))
    for key in ('execution','run'):f['bindings'][key]['protocol_sha256']=phash
    for r in f['bindings']['forecasts']:
        rows=[x for x in f['rows'] if x['fit_slot']==r['slot']]
        r['packet']=descriptor('prediction-chunks/'+r['slot']+'.json.gz',canonical(dict(schema=CAPTURE_VERSION,rows=rows)),f['artifacts'])
        r['rows']=len(rows)
    body=canonical(dict(schema=CAPTURE_VERSION,rows=f['rows']))
    f['blob']=gzip.compress(body,mtime=0)
    f['receipt'].update(packet=dict(name='WEEK8_SHADOWS.json.gz',bytes=len(f['blob']),sha256=digest(f['blob']),uncompressed_sha256=digest(body)),
        forecasted=sum(r['status']=='FORECASTED'for r in f['rows']),abstained=sum(r['status']=='ABSTAIN'for r in f['rows']))
    return f


def grade(f, **changes):
    rb,pb,bb=map(canonical,(f['receipt'],f['protocol'],f['bindings']))
    kwargs=dict(artifacts=f['artifacts'],expected_forecast_sha256=digest(f['blob']),expected_capture_receipt_sha256=digest(rb),
        expected_protocol_sha256=digest(pb),expected_bindings_sha256=digest(bb),asof_utc='2020-11-02T12:00:00Z',run_id='fixture-hgb-grading-v1')
    kwargs.update(changes)
    return grade_bytes(f['blob'],rb,pb,canonical(f['queries']),bb,canonical(f['labels']),**kwargs)


class HGBShadowGradingTests(unittest.TestCase):
    def test_empty_labels_preserve_frozen_matrix_pending_no_score(self):
        f=fixture();f['labels']['labels']=[]
        scores,errors,r=grade(f)
        self.assertEqual((len(scores),len(errors),r['scored_forecast_rows']),(15,15,0))
        self.assertFalse(r['whole_week_complete']);self.assertEqual(r['query_states'],{'pending_no_label':3})
        self.assertTrue(all(s['n']==0 and s['mae'] is None for s in scores))

    def test_signed_zero_count_brier_and_objective_identity(self):
        scores,errors,r=grade(fixture())
        self.assertTrue(r['whole_week_complete']);self.assertEqual(r['new_fits'],0)
        rush=next(s for s in scores if s['target']=='rush_yd')
        self.assertEqual(rush['mae'],2);self.assertEqual(rush['bias'],-2)
        self.assertEqual(next(s for s in scores if s['target']=='anytime_td')['brier'],.5625)
        self.assertEqual({s['product_id']for s in scores},{'absolute_error_point','squared_error_intended_mean','event_probability'})
        self.assertTrue(all(s['procedure_family_id']=='hgb-direct-history-controls' for s in scores))
        validate_index([evaluation(s,'reports/fictional/SCORES.json') for s in scores])
        for target in ('rush_yd','rec','anytime_td'):
            subset=[s for s in scores if s['target']==target]
            self.assertEqual(len({s['frozen_prediction_query_cohort_sha256']for s in subset}),1)
        self.assertTrue(all(e['owner_cutoff_status']=='LATER_THAN_OWNER_INPUT_CUTOFF'for e in errors))

    def test_trusted_hashes_model_and_original_chunk_bindings(self):
        for field in ('expected_forecast_sha256','expected_capture_receipt_sha256','expected_protocol_sha256','expected_bindings_sha256'):
            with self.subTest(field=field),self.assertRaises(ValueError):grade(fixture(),**{field:'0'*64})
        f=fixture();f['artifacts'][f['bindings']['fits'][0]['model']['name']]=b'wrong'
        with self.assertRaises(ValueError):grade(f)
        f=fixture();f['bindings']['fits'][0]['state']='NO_FIT_INSUFFICIENT_TRAINING'
        with self.assertRaises(ValueError):grade(f)
        f=fixture();f['rows'][0]['prediction']=123
        # Fresh trusted packet hash alone cannot override the original chunk.
        body=canonical(dict(schema=CAPTURE_VERSION,rows=f['rows']));f['blob']=gzip.compress(body,mtime=0)
        f['receipt']['packet'].update(bytes=len(f['blob']),sha256=digest(f['blob']),uncompressed_sha256=digest(body))
        with self.assertRaises(ValueError):grade(f)

    def test_duplicate_missing_history_and_wrong_identity_rejected(self):
        for mutation in ('duplicate','missing','identity','outcome','objective'):
            f=fixture()
            if mutation=='duplicate':f['rows'].append(copy.deepcopy(f['rows'][0]));f['receipt']['output_views']+=1
            elif mutation=='missing':f['rows'].pop();f['receipt']['output_views']-=1
            elif mutation=='identity':f['rows'][0]['player_id']='wrong'
            elif mutation=='outcome':f['rows'][0]['actual']=0
            else:f['rows'][0]['objective']='empirical_mean'
            rebind(f)
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):grade(f)

    def test_issue_cannot_override_block_or_abstention(self):
        for field in ('blocked_reason','abstention_reason'):
            f=fixture()
            for row in f['rows']:
                if row['query_id']=='fictional-q0':row[field]='UNKNOWN_IDENTITY'
            if field=='blocked_reason':f['queries']['week8'][0][field]='UNKNOWN_IDENTITY'
            rebind(f)
            with self.subTest(field=field),self.assertRaises(ValueError):grade(f)
        scores,_,r=grade(fixture(blocked=True))
        self.assertEqual(r['abstention_forecast_rows'],6)
        self.assertTrue(all(s['n']==0 for s in scores if s['target']=='rec'))

    def test_unfinal_future_wrong_identity_invalid_count_labels(self):
        for index,field,value in ((0,'game_completed',False),(0,'finality','pending'),
                (0,'available_utc','2020-11-03T23:00:00Z'),(0,'player_id','wrong'),
                (0,'contract_id','wrong'),(0,'source_id','wrong'),(1,'actual',-.1),(1,'actual',.5),(2,'actual',2)):
            f=fixture();f['labels']['labels'][index][field]=value
            with self.subTest(field=field,value=value),self.assertRaises(ValueError):grade(f)
        f=fixture();f['labels']['labels'].append(copy.deepcopy(f['labels']['labels'][0]))
        with self.assertRaises(ValueError):grade(f)

    def test_DNP_missing_pending_and_canceled_do_not_get_scores(self):
        for state in ('DNP','unknown','played_missing','pending','canceled'):
            f=fixture();label=f['labels']['labels'][0];label.update(actual=None,state=state)
            if state=='pending':label.update(game_completed=False,finality='pending')
            if state=='canceled':label.update(game_completed=False,finality='canceled',available_utc='2020-11-01T12:00:00Z',observed_utc='2020-11-01T12:05:00Z')
            scores,errors,r=grade(f)
            self.assertTrue(all(s['n']==0 and s['mae']is None for s in scores if s['target']=='rush_yd'))
            self.assertEqual(r['whole_week_complete'],state in ('DNP','canceled'))
            self.assertTrue(all(e['absolute_error']is None for e in errors if e['target']=='rush_yd'))

    def test_feature_fit_capture_clocks_and_support(self):
        for field,value in (('latest_feature_available',1604145600.),('cutoff',1604145601.),
                ('issued_at_utc','2020-11-01T18:00:00Z'),('owner_cutoff_status','BEFORE_OWNER_INPUT_CUTOFF'),('actual_horizon_seconds',1)):
            f=fixture();f['rows'][0][field]=value;rebind(f)
            with self.subTest(field=field),self.assertRaises(ValueError):grade(f)
        f=fixture();f['bindings']['fits'][0]['training_seasons']=[2027]
        with self.assertRaises(ValueError):grade(f)
        f=fixture();f['rows'][-1]['prediction']=1.5;rebind(f)
        with self.assertRaises(ValueError):grade(f)

    def test_file_grading_immutable_private_rows_and_no_model_execution(self):
        f=fixture()
        with tempfile.TemporaryDirectory()as temp:
            root=Path(temp)
            bodies={'forecast.gz':f['blob'],'receipt.json':canonical(f['receipt']),'protocol.json':canonical(f['protocol']),
                'queries.json':canonical(f['queries']),'bindings.json':canonical(f['bindings']),'labels.json':canonical(f['labels'])}
            for n,b in bodies.items():(root/n).write_bytes(b)
            for n,b in f['artifacts'].items():
                p=root/'artifacts'/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
            kw=dict(forecasts=root/'forecast.gz',capture_receipt=root/'receipt.json',capture_protocol=root/'protocol.json',
                frozen_queries=root/'queries.json',capture_bindings=root/'bindings.json',labels=root/'labels.json',artifact_root=root/'artifacts',
                public_output=root/'public',private_output=root/'private',expected_forecast_sha256=digest(f['blob']),
                expected_capture_receipt_sha256=digest(bodies['receipt.json']),expected_protocol_sha256=digest(bodies['protocol.json']),
                expected_bindings_sha256=digest(bodies['bindings.json']),run_id='fictional-files-v1',asof_utc='2020-11-02T12:00:00Z')
            result=grade_files(**kw)
            self.assertEqual(result['new_forecasts'],0);self.assertEqual((root/'forecast.gz').read_bytes(),f['blob'])
            self.assertTrue((root/'private/player-errors.json.gz').exists())
            self.assertNotIn(b'player_id',(root/'public/SCORES.json').read_bytes())
            with self.assertRaises(ValueError):grade_files(**kw)


if __name__=='__main__':unittest.main()
