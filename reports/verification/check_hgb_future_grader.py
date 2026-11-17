"""Independent invented-fixture and EMPTY-label checks; no Week8 labels opened."""
import copy
from datetime import datetime, timezone
import gzip
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from nfl_v2.hgb_shadow_grading import (BINDING_SCHEMA, CAPTURE_VERSION,
    collect_bindings, grade_bytes, load_artifacts)
from nfl_v2.shadow_grading import CONTRACTS, LABEL_SCHEMA, QUERY_FIELDS


def body(x):
    return json.dumps(x, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def sha(x):
    return hashlib.sha256(x).hexdigest()


def packet(name, value, artifacts):
    compressed = gzip.compress(value, mtime=0)
    artifacts[name] = compressed
    return dict(name=name, bytes=len(compressed), sha256=sha(compressed), uncompressed_sha256=sha(value))


def bind(f):
    qb = body(dict(historical=[], week8=f['queries']))
    f['queries_bytes'] = qb
    f['protocol'].update(frozen_queries_sha256=sha(qb), week8_membership_sha256=sha(body(f['queries'])))
    for key in ('execution', 'run'):
        f['bindings'][key]['protocol_sha256'] = sha(body(f['protocol']))
    for receipt in f['bindings']['forecasts']:
        rs = [r for r in f['rows'] if r['fit_slot'] == receipt['slot']]
        receipt['packet'] = packet('prediction-chunks/'+receipt['slot']+'.gz', body(dict(schema=CAPTURE_VERSION, rows=rs)), f['artifacts'])
        receipt['rows'] = len(rs)
        receipt['forecasted'] = sum(r['status']=='FORECASTED' for r in rs)
        receipt['abstained'] = sum(r['status']=='ABSTAIN' for r in rs)
    uncompressed = body(dict(schema=CAPTURE_VERSION, rows=f['rows']))
    f['forecast'] = gzip.compress(uncompressed, mtime=0)
    f['receipt'].update(packet=dict(name='WEEK8_SHADOWS.json.gz', bytes=len(f['forecast']), sha256=sha(f['forecast']), uncompressed_sha256=sha(uncompressed)),
        output_views=len(f['rows']), forecasted=sum(r['status']=='FORECASTED' for r in f['rows']), abstained=sum(r['status']=='ABSTAIN' for r in f['rows']))
    return f


def fixture():
    origin = datetime.fromisoformat('2020-08-31T18:00:00+00:00').timestamp()
    kickoff = datetime.fromisoformat('2020-09-01T20:00:00+00:00').timestamp()
    qs = [dict(query_id='independent-invented-'+t, sleeper_id='fictional-sleeper-'+t, player_id='fictional-player-'+t,
        position='QB', target=t, game_id='fictional-game', espn_game_id='fictional-event', blocked_reason=None,
        kickoff_utc='2020-09-01T20:00:00Z', owner_input_cutoff_utc='2020-09-01T18:30:00Z') for t in ('pass_att', 'anytime_td')]
    protocol = dict(version=CAPTURE_VERSION, registered_at_utc='2020-08-31T17:59:00Z', code_sha256='2'*64, week8_query_cells=2,
        history_regimes={'H-CURRENT':[2026], 'H-RECENT':[2025,2026], 'H-MULTI':[2022,2023,2024,2025,2026]})
    bindings = dict(schema=BINDING_SCHEMA, execution=dict(version=CAPTURE_VERSION, actual_started_at='2020-08-31T18:00:00Z', actual_week8_feature_origin_utc='2020-08-31T18:00:00Z'),
        run=dict(version=CAPTURE_VERSION, code_sha256='2'*64), fits=[], forecasts=[])
    rows, artifacts = [], {}
    for q in qs:
        for arm in ('H-CURRENT','H-RECENT','H-MULTI'):
            for objective in (('log_loss_probability',) if q['target']=='anytime_td' else ('absolute_error_point','squared_error_mean')):
                slot=f"W08-{q['target']}-{arm}-{objective}"
                p=({'H-CURRENT':0.,'H-RECENT':.25,'H-MULTI':.75}[arm] if q['target']=='anytime_td' else 12. if objective=='absolute_error_point' else 12.5)
                bindings['fits'].append(dict(slot=slot, origin=8, target=q['target'], history_regime=arm, objective=objective,
                    state='FITTED_RETAINED', fit_cutoff_utc='2020-08-31T18:00:00Z', training_seasons=[2026],
                    actual_fit_started_at='2020-08-31T18:00:00Z', actual_fit_completed_at='2020-08-31T18:00:01Z',
                    latest_training_feature_available=origin-1, latest_training_label_available=origin-1,
                    model=packet('models/'+slot+'.gz', b'invented opaque bytes; NEVER unpickled', artifacts),
                    query_features=packet('query-features/'+slot+'.gz', body([]), artifacts)))
                bindings['forecasts'].append(dict(slot=slot, actual_persistence_completed_at='2020-08-31T18:00:03Z'))
                rows.append(dict(q, history_regime=arm, objective=objective, run_id=CAPTURE_VERSION, fit_slot=slot, fit_state='FITTED_RETAINED',
                    cutoff=origin, kickoff=kickoff, season=2026, week=8, population='original_pregame_feed',
                    evidence_tier='genuine_new_research_pregame_shadow', issued_at_utc='2020-08-31T18:00:02Z', actual_generated_at='2020-08-31T18:00:02Z',
                    actual_horizon_seconds=kickoff-origin-2, owner_cutoff_status='BEFORE_OWNER_INPUT_CUTOFF', latest_feature_available=origin-1,
                    latest_fallback_available=None, actual=None, prediction=p, status='FORECASTED', abstention_reason=None, fallback='none'))
    source=dict(source_id='INVENTED', source_tier='current_vintage_final_snapshot', identity_contract_id='fictional-identity',
        statistic_contract_id='fictional-explicit', participation_contract_id='fictional-played', finality_contract_id='fictional-final', availability_basis_id='fictional-clock')
    labels=[dict(query_id=q['query_id'], player_id=q['player_id'], game_id=q['game_id'], target=q['target'], contract_id=CONTRACTS[q['target']],
        actual=11 if q['target']=='pass_att' else 1, state='played', game_completed=True, finality='final', source_id='INVENTED',
        available_utc='2020-09-01T23:30:00Z', observed_utc='2020-09-02T00:00:00Z') for q in qs]
    return bind(dict(queries=qs, protocol=protocol, bindings=bindings, artifacts=artifacts, rows=rows,
        receipt=dict(version=CAPTURE_VERSION, queries=2, unique_games=1, cutoff_utc='2020-08-31T18:00:00Z', actual_completed_at='2020-08-31T18:00:04Z', official_capture=False, website_published=False),
        labels=dict(schema=LABEL_SCHEMA, label_version_id='fictional-labels-only', source_admissions=[source], labels=labels)))


def grade(f):
    rb,pb,bb = map(body,(f['receipt'],f['protocol'],f['bindings']))
    return grade_bytes(f['forecast'],rb,pb,f['queries_bytes'],bb,body(f['labels']),artifacts=f['artifacts'],
        expected_forecast_sha256=sha(f['forecast']),expected_capture_receipt_sha256=sha(rb),expected_protocol_sha256=sha(pb),
        expected_bindings_sha256=sha(bb),asof_utc='2020-09-02T00:01:00Z',run_id='independent-fictional-QA')


def review(private, public):
    checks=0
    def ok(x):
        nonlocal checks
        assert x
        checks+=1
    def rejects(f):
        try: grade(f)
        except ValueError: return True
        return False
    scores,errors,receipt=grade(fixture())
    ok(receipt['scored_forecast_rows']==9 and receipt['whole_week_complete'])
    for r in scores:
        if r['target']=='pass_att':
            e=1. if r['objective']=='absolute_error_point' else 1.5
            ok(r['mae']==e and r['mse']==e*e and r['bias']==e)
            ok(r['abs_lt_1']==0 and r['abs_le_1']==(e==1))
        else:
            p={'H-CURRENT':0.,'H-RECENT':.25,'H-MULTI':.75}[r['history_regime']]
            ok(r['brier']==(p-1)**2)
            ok(r['log_loss']=='Infinity' if p==0 else math.isclose(r['log_loss'],-math.log(p)))
    for target in ('pass_att','anytime_td'):
        ok(len({r['scored_query_cohort_sha256'] for r in scores if r['target']==target})==1)
    for state in ('DNP','unknown','played_missing','pending','canceled'):
        f=fixture();label=f['labels']['labels'][0];label.update(actual=None,state=state)
        if state=='pending':label.update(game_completed=False,finality='pending')
        if state=='canceled':label.update(game_completed=False,finality='canceled',available_utc='2020-09-01T12:00:00Z',observed_utc='2020-09-01T12:01:00Z')
        ss,ee,rr=grade(f)
        ok(all(s['n']==0 and s['mae'] is None for s in ss if s['target']=='pass_att'))
        ok(all(e['signed_error'] is None for e in ee if e['target']=='pass_att'))
    for field,val in [('actual',.5),('finality','pending'),('game_completed',False),('available_utc','2020-09-03T00:00:00Z'),('source_id','UNKNOWN'),('contract_id','wrong')]:
        f=fixture();f['labels']['labels'][0][field]=val;ok(rejects(f))
    for field in ('blocked_reason','abstention_reason'):
        f=fixture()
        for r in f['rows']:
            if r['target']=='pass_att':r[field]='UNKNOWN_IDENTITY'
        if field=='blocked_reason':f['queries'][0][field]='UNKNOWN_IDENTITY'
        bind(f);ok(rejects(f))
    f=fixture();f['artifacts'][next(iter(f['artifacts']))]=b'mutated';ok(rejects(f))
    f=fixture();f['rows'][0]['actual']=0;bind(f);ok(rejects(f))
    f=fixture();f['bindings']['fits'][0]['training_seasons']=[2027];ok(rejects(f))

    cb=(private/'WEEK8_SHADOWS.json.gz').read_bytes();rb=(public/'WEEK8_CAPTURE_RECEIPT.json').read_bytes();pb=(public/'FROZEN_PROTOCOL.json').read_bytes()
    qb=(private/'frozen-queries.json').read_bytes();bindings=collect_bindings(public);bb=body(bindings);artifacts=load_artifacts(bindings,private)
    before=sha(cb);now=datetime.now(timezone.utc)
    rows=json.loads(gzip.decompress(cb))['rows']
    assert now<min(datetime.fromisoformat(r['kickoff_utc'].replace('Z','+00:00')) for r in rows)
    empty=body(dict(schema=LABEL_SCHEMA,label_version_id='QA-EMPTY-LABELS-NO-OUTCOMES',source_admissions=[],labels=[]))
    ss,ee,rr=grade_bytes(cb,rb,pb,qb,bb,empty,artifacts=artifacts,expected_forecast_sha256=before,
        expected_capture_receipt_sha256=sha(rb),expected_protocol_sha256=sha(pb),expected_bindings_sha256=sha(bb),asof_utc=now.isoformat(),run_id='QA-HGB-EMPTY-LABELS-ONLY')
    assert rr['scored_forecast_rows']==rr['scored_unique_games']==0
    assert rr['forecast_rows']==10416 and rr['unique_queries']==1951 and rr['abstention_forecast_rows']==30
    assert rr['query_states']=={'pending_no_label':1951} and not rr['whole_week_complete'] and len(ss)==63
    assert all(r['n']==0 and all(r[k] is None for k in ['mae','mse','rmse','bias']) for r in ss)
    assert all(r['actual'] is None and r['signed_error'] is None and r['absolute_error'] is None for r in ee)
    assert sha((private/'WEEK8_SHADOWS.json.gz').read_bytes())==before
    return dict(status='PASS_INDEPENDENT_FIXTURES_AND_EMPTY_REAL_CAPTURE',independent_fictional_checks=checks,
        reviewed_code_sha256=sha((ROOT/'nfl_v2/hgb_shadow_grading.py').read_bytes()),actual_empty_label_check_asof_utc=now.isoformat(),
        trusted_capture_sha256=before,trusted_receipt_sha256=sha(rb),trusted_protocol_sha256=sha(pb),trusted_bindings_sha256=sha(bb),
        retained_models_hash_verified=rr['capture_model_artifacts_verified'],real_capture_views_checked=10416,real_capture_query_cells=1951,
        real_capture_abstention_views=30,pending_aggregate_views=len(ss),actual_week8_labels_opened=0,actual_week8_scores_produced=0,
        original_forecasts_unchanged=True,models_unpickled_or_executed=0,new_fits=0,new_forecasts=0)


if __name__=='__main__':
    result=review(Path(sys.argv[1]),Path(sys.argv[2]))
    (ROOT/'reports/verification/HGB_FUTURE_GRADER_REVIEW.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
