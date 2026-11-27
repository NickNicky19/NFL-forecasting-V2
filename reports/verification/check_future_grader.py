"""Read-only grader QA: invented labels and real captured bytes with EMPTY labels.

This never opens a Week8 outcome source and never writes a Week8 scorecard.
"""
from collections import Counter
from datetime import datetime,timezone
import gzip,hashlib,json,math
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from nfl_v2.shadow_grading import CAPTURE_VERSION,CONTRACTS,LABEL_SCHEMA,grade_bytes

def body(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def sha(x):return hashlib.sha256(x).hexdigest()

def fixture():
    qs=[dict(query_id='qa-invented-'+t,sleeper_id='invented-sid-'+t,player_id='invented-player-'+t,
        position='QB',target=t,game_id='invented-game',espn_game_id='invented-espn',
        kickoff_utc='2020-09-01T20:00:00Z',owner_input_cutoff_utc='2020-09-01T18:30:00Z',
        blocked_reason=None) for t in ['pass_att','anytime_td']]
    protocol=dict(version=CAPTURE_VERSION,query_membership_sha256=sha(body(qs)))
    pb=body(protocol);rows=[]
    for q in qs:
        for arm in ['H-CURRENT','H-RECENT','H-MULTI']:
            for product in ['event_probability'] if q['target']=='anytime_td' else ['empirical_mean','lower_median']:
                pred=({'H-CURRENT':0.,'H-RECENT':.25,'H-MULTI':.75}[arm] if product=='event_probability'
                      else 12.5 if product=='empirical_mean' else 12.)
                rows.append(dict(q,history_regime=arm,product=product,prediction=pred,
                    status='ISSUED_SHADOW',abstention_reason=None,fallback='none',
                    issued_at_utc='2020-08-31T18:00:00Z',feature_cutoff_utc='2020-08-31T17:59:00Z',
                    protocol_sha256=sha(pb),owner_cutoff_status='BEFORE_OWNER_INPUT_CUTOFF',
                    actual_horizon_seconds=93600,run_id=CAPTURE_VERSION))
    packet=dict(schema=CAPTURE_VERSION,rows=rows);decoded=body(packet);blob=gzip.compress(decoded,mtime=0)
    receipt=dict(version=CAPTURE_VERSION,private_forecast_sha256=sha(blob),private_uncompressed_sha256=sha(decoded),
        protocol_sha256=sha(pb),query_membership_sha256=sha(body(qs)),forecast_output_rows=len(rows),query_cells=len(qs),
        actual_persistence_completed_at='2020-08-31T18:00:01Z')
    source=dict(source_id='INVENTED',source_tier='current_vintage_final_snapshot',
        identity_contract_id='invented-identity',statistic_contract_id='invented-explicit',
        participation_contract_id='invented-played',finality_contract_id='invented-final',
        availability_basis_id='invented-clocks')
    labels=[dict(query_id=q['query_id'],player_id=q['player_id'],game_id=q['game_id'],target=q['target'],
        contract_id=CONTRACTS[q['target']],actual=11 if q['target']=='pass_att' else 1,state='played',
        game_completed=True,finality='final',source_id='INVENTED',revision_id=None,
        available_utc='2020-09-01T23:30:00Z',observed_utc='2020-09-02T00:00:00Z') for q in qs]
    lp=dict(schema=LABEL_SCHEMA,label_version_id='invented-label-v1',source_admissions=[source],labels=labels)
    return blob,receipt,pb,lp

def fictional_grade(blob,receipt,pb,lp):
    rb=body(receipt)
    return grade_bytes(blob,rb,pb,body(lp),expected_forecast_sha256=sha(blob),
        expected_capture_receipt_sha256=sha(rb),asof_utc='2020-09-02T00:01:00Z',run_id='invented-QA-only')

def check(private,public):
    before={p.name:sha(p.read_bytes()) for p in [private/'shadow-forecasts.json.gz',public/'CAPTURE_RECEIPT.json',public/'FROZEN_PROTOCOL.json']}
    cb=(private/'shadow-forecasts.json.gz').read_bytes();rb=(public/'CAPTURE_RECEIPT.json').read_bytes();pb=(public/'FROZEN_PROTOCOL.json').read_bytes()
    now=datetime.now(timezone.utc);capture=json.loads(gzip.decompress(cb))
    assert now<min(datetime.fromisoformat(r['kickoff_utc'].replace('Z','+00:00')) for r in capture['rows'])
    empty=body(dict(schema=LABEL_SCHEMA,label_version_id='QA-EMPTY-LABELS-NO-OUTCOMES',source_admissions=[],labels=[]))
    scores,errors,summary=grade_bytes(cb,rb,pb,empty,expected_forecast_sha256=sha(cb),
        expected_capture_receipt_sha256=sha(rb),asof_utc=now.isoformat(),run_id='QA-REAL-CAPTURE-EMPTY-LABELS-ONLY')
    assert summary['scored_forecast_rows']==0 and summary['scored_unique_player_games']==0 and summary['scored_unique_games']==0
    assert summary['query_states']=={'pending_no_label':1951} and not summary['whole_week_complete']
    assert summary['forecast_rows']==10416 and summary['abstention_forecast_rows']==30 and len(errors)==10416
    assert len(scores)==63
    assert all(r['n']==0 and all(r[k] is None for k in ['mae','mse','rmse','bias']) for r in scores)
    assert all(r['signed_error'] is None and r['absolute_error'] is None and r['actual'] is None for r in errors)
    after={p.name:sha(p.read_bytes()) for p in [private/'shadow-forecasts.json.gz',public/'CAPTURE_RECEIPT.json',public/'FROZEN_PROTOCOL.json']}
    assert before==after
    checks=0
    def ok(condition):
        nonlocal checks
        assert condition;checks+=1
    def rejects(f):
        try:fictional_grade(*f)
        except ValueError:return True
        return False
    f=fixture();fs,fe,fr=fictional_grade(*f)
    ok(fr['whole_week_complete']);ok(fr['scored_forecast_rows']==9)
    for r in fs:
        if r['target']=='pass_att':
            e=1.5 if r['product_id']=='empirical_mean' else 1.
            ok(r['mae']==e and r['mse']==e*e and r['bias']==e)
            ok(r['abs_lt_1']==0 and r['abs_le_1']==(r['product_id']=='lower_median'))
        else:
            pred={'H-CURRENT':0.,'H-RECENT':.25,'H-MULTI':.75}[r['history_regime']]
            ok(r['brier']==(pred-1)**2)
            ok(r['log_loss']=='Infinity' if pred==0 else math.isclose(r['log_loss'],-math.log(pred)))
    for target in ['pass_att','anytime_td']:
        rs=[r for r in fs if r['target']==target]
        ok(len({r['scored_query_cohort_sha256'] for r in rs})==1)
    for state in ['DNP','unknown','missing','played_missing','pending']:
        a=fixture();a[3]['labels'][0].update(actual=None,state=state)
        so,er,su=fictional_grade(*a)
        ok(all(r['n']==0 and r['mae'] is None for r in so if r['target']=='pass_att'))
        ok(all(r['signed_error'] is None for r in er if r['target']=='pass_att'))
    a=fixture();a[3]['labels'][0].update(actual=None,state='canceled',finality='canceled',game_completed=False,
        available_utc='2020-09-01T12:00:00Z',observed_utc='2020-09-01T12:01:00Z')
    so,er,su=fictional_grade(*a);ok(su['whole_week_complete']);ok(su['query_states']['qualified_final_canceled']==1)
    for field,val in [('actual',.5),('finality','pending'),('game_completed',False),
                      ('available_utc','2020-09-03T00:00:00Z'),('source_id','UNKNOWN'),('contract_id','wrong')]:
        a=fixture();a[3]['labels'][0][field]=val;ok(rejects(a))
    # Malformed fictional capture must never turn a blocked query into issued numeric scoring.
    a=fixture();packet=json.loads(gzip.decompress(a[0]));protocol=json.loads(a[2])
    for r in packet['rows']:
        if r['target']=='pass_att':r['blocked_reason']='UNKNOWN_IDENTITY'
    qs=[];seen=set()
    keys=('query_id','sleeper_id','player_id','position','target','game_id','espn_game_id','kickoff_utc','owner_input_cutoff_utc','blocked_reason')
    for r in packet['rows']:
        if r['query_id'] not in seen:qs.append({k:r[k] for k in keys});seen.add(r['query_id'])
    protocol['query_membership_sha256']=sha(body(qs));new_pb=body(protocol)
    for r in packet['rows']:r['protocol_sha256']=sha(new_pb)
    decoded=body(packet);new_blob=gzip.compress(decoded,mtime=0);new_receipt=dict(a[1],query_membership_sha256=sha(body(qs)),
        protocol_sha256=sha(new_pb),private_forecast_sha256=sha(new_blob),private_uncompressed_sha256=sha(decoded))
    blocked_capture_rejected=rejects((new_blob,new_receipt,new_pb,a[3]))
    return dict(status='PASS_PENDING_CAPTURE_AND_FIXTURE_MATH' if blocked_capture_rejected else 'CONCRETE_INPUT_VALIDATION_GAP_FOUND',
        actual_empty_label_check_asof_utc=now.isoformat(),trusted_capture_sha256=sha(cb),trusted_receipt_sha256=sha(rb),
        real_capture_views_checked=10416,real_capture_query_cells=1951,real_capture_abstention_views=30,
        real_capture_zero_scored_views=0,real_capture_pending_aggregate_views=len(scores),
        actual_week8_label_sources_opened=0,actual_week8_scores_published=0,original_inputs_unchanged=before==after,
        independent_fictional_checks=checks,blocked_query_issued_capture_rejected=blocked_capture_rejected,
        reviewed_grader_sha256=sha((ROOT/'nfl_v2/shadow_grading.py').read_bytes()),
        note='Real capture tested in memory against an empty label packet only; fictional labels do not refer to NFL outcomes.')

if __name__=='__main__':
    result=check(Path(sys.argv[1]),Path(sys.argv[2]))
    (ROOT/'reports/verification/FUTURE_GRADER_REVIEW.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
