"""Independent source/frame/feature/replay/score QA; NEVER calls estimator.fit."""
from collections import Counter,defaultdict
import bisect,csv,gzip,hashlib,json,math,pickle,re
from pathlib import Path
from datetime import datetime
from decimal import Decimal,localcontext
import sys
from zoneinfo import ZoneInfo
import numpy as np
from threadpoolctl import threadpool_limits

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).resolve().parent))
from check_empirical_diagnostic import ACTION_COUNTS,ACTION_YARDS,count,num,value
from check_label_extension import metrics

def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def clock(x):return datetime.fromisoformat(x.replace('Z','+00:00'))

def audit(source,private,public):
    protocol=json.loads((public/'FROZEN_PROTOCOL.json').read_text());receipt=json.loads((public/'RUN_RECEIPT.json').read_text())
    assert sha(ROOT/'nfl_v2/hgb_control.py')==protocol['code_sha256']==receipt['code_sha256']
    assert sha(private/'frozen-queries.json')==protocol['frozen_queries_sha256']
    frozen=json.loads((private/'frozen-queries.json').read_text())
    assert hashlib.sha256(canonical(frozen['historical'])).hexdigest()==protocol['historical_membership_sha256']
    for item in protocol['source_ids']:
        p=source/item['name'];assert p.stat().st_size==item['bytes'] and sha(p)==item['sha256']
    schedule={}
    with (source/'games.csv').open() as f:
        for r in csv.DictReader(f):
            if r['game_type']!='REG' or int(r['season']) not in range(2022,2027) or (int(r['season'])==2026 and int(r['week'])>8):continue
            dt=datetime.fromisoformat(r['gameday']+'T'+r['gametime']).replace(tzinfo=ZoneInfo('America/New_York'))
            schedule[r['game_id']]=dict(kickoff=dt.timestamp(),season=int(r['season']),week=int(r['week']),home=r['home_team'],away=r['away_team'])
    raw=[];lookup={};hist=defaultdict(list);eligible=defaultdict(list)
    for year in range(2022,2027):
        with (source/f'stats_player_week_{year}.csv').open() as f:
            for r in csv.DictReader(f):
                if r['season_type']!='REG' or int(r['season'])!=year or(year==2026 and int(r['week'])>7):continue
                if r['position'] not in ['QB','RB','WR','TE'] or not re.fullmatch(r'00-\d{7}',r['player_id']):continue
                game=schedule[r['game_id']]
                assert (game['season'],game['week'])==(year,int(r['week']))
                assert (r['team'],r['opponent_team']) in [(game['home'],game['away']),(game['away'],game['home'])]
                played=any(count(num(r[k])) and num(r[k])>0 for k in ACTION_COUNTS) or any(num(r[k]) not in [None,0] for k in ACTION_YARDS)
                row=dict(player_id=r['player_id'],game_id=r['game_id'],position=r['position'],season=year,week=int(r['week']),kickoff=game['kickoff'],available=game['kickoff']+7*86400,
                    values={t:value(t,r) if played else None for t in protocol['targets']})
                raw.append(row);lookup[(row['game_id'],row['player_id'])]=row;hist[row['player_id']].append(row)
                for target,y in row['values'].items():
                    roles=protocol['source_role_contract']['primary'][target]+protocol['source_role_contract']['extended'].get(target,[])
                    if y is not None and row['position'] in roles:eligible[target].append(row)
    for rows in hist.values():rows.sort(key=lambda r:(r['available'],r['kickoff'],r['game_id']))
    times={p:[r['available'] for r in rs] for p,rs in hist.items()}
    def feature(q):
        if q['blocked_reason']:return [None]*20,None
        cutoff=float(q['cutoff']);end=bisect.bisect_left(times.get(q['player_id'],[]),cutoff)
        chosen=hist.get(q['player_id'],[])[max(0,end-8):end];result=[]
        for window in [3,8]:
            ys=[r['values'][q['target']] for r in chosen[-window:] if r['values'][q['target']] is not None]
            result.extend([float(sum(ys)/Decimal(len(ys))) if ys else None,float(len(ys))])
        for i in range(1,5):
            prior=chosen[-i] if len(chosen)>=i else None;y=prior['values'][q['target']] if prior else None
            result.extend([float(y) if y is not None else None,(cutoff-prior['kickoff'])/86400 if prior else None,float(y is None)])
        result.extend(float(q['position']==p) for p in ['QB','RB','WR','TE'])
        return result,chosen[-1]['available'] if chosen else None
    feature_checks=0;feature_packets={};all_query_keys=set();historical_keys=set()
    for p in sorted((private/'query-features').glob('*.json.gz')):
        rows=json.loads(gzip.decompress(p.read_bytes()));feature_packets[p.name]=rows
        for entry in rows:
            q=entry['query'];expected,latest=feature(q)
            assert len(expected)==20 and len(entry['features'])==20
            for a,b in zip(expected,entry['features']):
                assert (a is None and b is None) or(a is not None and b is not None and math.isclose(a,b,rel_tol=3e-14,abs_tol=3e-12))
                feature_checks+=1
            assert entry['latest_feature_available']==latest;feature_checks+=1
            if int(q['week'])<=7:
                s=lookup[(q['game_id'],q['player_id'])]
                assert num(str(q['actual']))==s['values'][q['target']]
                assert q['cutoff']==q['kickoff']==schedule[q['game_id']]['kickoff']
                historical_keys.add((q['game_id'],q['player_id'],q['target'],q['population']))
            else:assert q['actual'] is None
            all_query_keys.add((int(q['week']),q['game_id'],q['player_id'],q['target'],q['population']))
    assert historical_keys=={(r['game_id'],r['player_id'],r['target'],r['population']) for r in frozen['historical']}
    origins={w:min(g['kickoff'] for g in schedule.values() if g['season']==2026 and g['week']==w) for w in range(1,8)}
    execution=json.loads((public/'EXECUTION_REGISTRATION.json').read_text());origins[8]=clock(execution['actual_week8_feature_origin_utc']).timestamp()
    audits=[json.loads(p.read_text()) for p in sorted(public.glob('*-FIT.json'))]
    assert len(audits)==504;training_checks=0;models=0;model_replays=0;forecast_checks=0
    all_records=[];cohorts=defaultdict(lambda:defaultdict(set));groups=defaultdict(list);week8=[]
    with threadpool_limits(limits=2):
        for audit in audits:
            week,target,arm=audit['origin'],audit['target'],audit['history_regime'];origin=origins[week]
            floor=2026 if arm=='H-CURRENT' else 2025 if arm=='H-RECENT' else 2022
            selected=[r for r in eligible[target] if floor<=r['season']<=2026 and r['available']<origin]
            assert len(selected)==audit['training_n'];assert clock(audit['fit_cutoff_utc']).timestamp()==origin
            assert sorted({r['season'] for r in selected})==audit['training_seasons']
            assert max((r['available'] for r in selected),default=None)==audit['latest_training_label_available']
            assert hashlib.sha256(canonical([(r['game_id'],r['player_id']) for r in selected])).hexdigest()==audit['training_membership_sha256']
            assert all(r['available']<origin for r in selected);training_checks+=6
            packet=audit['query_features'];qp=private/packet['name'];assert sha(qp)==packet['sha256']
            entries=feature_packets[qp.name]
            qx=np.asarray([[math.nan if v is None else v for v in e['features']] for e in entries],dtype=float)
            slot=audit['slot'];pr=json.loads((public/(slot+'-FORECAST.json')).read_text());pred_packet=pr['packet']
            pp=private/pred_packet['name'];assert sha(pp)==pred_packet['sha256']
            records=json.loads(gzip.decompress(pp.read_bytes()))['rows'];assert len(records)==len(entries)
            if audit['model'] is not None:
                models+=1;mp=private/audit['model']['name'];assert sha(mp)==audit['model']['sha256']
                uncompressed=gzip.decompress(mp.read_bytes());assert hashlib.sha256(uncompressed).hexdigest()==audit['model']['uncompressed_sha256']
                # Trusted self-produced, digest-verified pickle; inference only, never fit.
                model=pickle.loads(uncompressed)
                assert model.n_iter_==64
                for k,v in protocol['params'].items():assert model.get_params()[k]==v
                expected=model.predict_proba(qx)[:,list(model.classes_).index(1.)] if target=='anytime_td' else model.predict(qx)
                for r,pred,e in zip(records,expected,entries):
                    if r['prediction'] is None:continue
                    projected=max(0.,float(pred)) if target in ['pass_td','pass_cmp','pass_att','pass_int','rush_att','rec'] else float(pred)
                    assert math.isclose(r['prediction'],projected,rel_tol=3e-14,abs_tol=3e-12);model_replays+=1
            for r,e in zip(records,entries):
                q=e['query']
                assert all(r[k]==v for k,v in q.items());assert r['latest_feature_available']==e['latest_feature_available']
                if q['blocked_reason']:
                    assert r['prediction'] is None and r['status']=='ABSTAIN'
                elif audit['model'] is None:
                    candidates=[s for s in eligible[target] if floor<=s['season']<=2026 and s['position']==q['position'] and s['available']<q['cutoff']]
                    own=[s for s in candidates if s['player_id']==q['player_id']];chosen=own or candidates
                    fb='own_empirical' if own else 'position_empirical' if candidates else 'constant_zero'
                    ys=sorted(s['values'][target] for s in chosen)
                    pred=(ys[(len(ys)-1)//2] if audit['objective']=='absolute_error_point' else sum(ys)/Decimal(len(ys))) if ys else Decimal(0)
                    assert r['fallback']==fb and r['fallback_n']==len(chosen)
                    assert math.isclose(float(pred),r['prediction'],rel_tol=3e-14,abs_tol=3e-12)
                    assert max((s['available'] for s in chosen),default=None)==r['latest_fallback_available']
                if week==8:
                    assert r['actual'] is None
                    issued=clock(r['issued_at_utc']).timestamp();persisted=clock(pr['actual_persistence_completed_at']).timestamp()
                    if r['prediction'] is not None:
                        assert origin<=issued<=persisted<r['kickoff']
                        late='LATER_THAN_OWNER_INPUT_CUTOFF' if issued>clock(r['owner_input_cutoff_utc']).timestamp() else 'BEFORE_OWNER_INPUT_CUTOFF'
                        assert r['owner_cutoff_status']==late
                    week8.append(r)
                else:
                    pk=(target,r['population'],audit['objective']);cohorts[pk][arm].add((r['game_id'],r['player_id']))
                    for ending in [('ALL','ALL'),(str(week),'ALL'),('ALL',r['position'])]:groups[(target,r['population'],arm,audit['objective'])+ending].append(r)
                forecast_checks+=3;all_records.append(r)
    assert models==receipt['actual_fit_calls']==receipt['fitted_retained_models']==452
    assert sum(a['model'] is None for a in audits)==52
    for arms in cohorts.values():assert set(arms)=={'H-CURRENT','H-RECENT','H-MULTI'} and len({frozenset(v) for v in arms.values()})==1
    published=json.loads((public/'SCORES.json').read_text());metric_checks=0;max_delta=0.
    for row in published:
        k=tuple(row[f] for f in ['target','population','history_regime','objective','week','position']);rs=groups[k]
        scored=[(float(r['prediction']),float(r['actual'])) for r in rs if r['prediction'] is not None and r['actual'] is not None]
        assert len(rs)==row['forecast_queries'] and len(scored)==row['scored_n'];metric_checks+=2
        if not scored:continue
        ms=metrics(scored,row['target'])
        for name,val in ms.items():
            if name=='n':continue
            if val.is_infinite():assert row[name] is None and row['infinite_log_losses']>0
            else:
                delta=abs(float(val)-row[name]);max_delta=max(max_delta,delta)
                assert math.isclose(float(val),row[name],rel_tol=3e-14,abs_tol=4e-12)
            metric_checks+=1
    return dict(status='PASS_NEW_HGB_REPLAY_WITH_STATED_HISTORY_FEATURE_MEMORY',
        reviewed_code_sha256=protocol['code_sha256'],source_hashes_checked=len(protocol['source_ids']),
        historical_query_cells=len(historical_keys),all_query_cells=len(all_query_keys),raw_feature_value_and_clock_checks=feature_checks,
        training_frame_checks=training_checks,fit_opportunities=len(audits),retained_models=models,insufficient_training_fallback_cells=52,
        inference_only_replayed_prediction_views=model_replays,forecast_binding_checks=forecast_checks,
        total_retained_prediction_views=len(all_records),week8_views=len(week8),week8_issued=sum(r['prediction'] is not None for r in week8),
        week8_abstained=sum(r['prediction'] is None for r in week8),week8_owner_cutoff_status=dict(Counter(r['owner_cutoff_status'] for r in week8 if r['prediction'] is not None)),
        summary_views_checked=len(published),metric_checks=metric_checks,max_absolute_metric_difference=max_delta,
        independent_refits=0,actual_week8_labels_read_or_scored=0,
        methodological_limits=['H-CURRENT means current-season fitting with common older2022-start feature memory; not pure-current information.',
            'Historical source-row population/positions are retrospective; current-vintage reconstruction with assumed7dayavailability.',
            'Absolute/squared-loss points are separate objectives, not authenticated numeric probability laws; binary HGB uncalibrated.',
            'Protocol max_forecast_rows is declared but not actively checked in run; actual96678 is below2000000. Preserve frozen code; version a guard repair.',
            'No live website release, official capture, chart labels, broad tuning or untouched confirmation.'])

if __name__=='__main__':
    with localcontext() as ctx:
        ctx.prec=50
        result=audit(Path(sys.argv[1]),Path(sys.argv[2]),Path(sys.argv[3]))
    (ROOT/'reports/verification/HGB_HISTORY_INDEPENDENT_QA.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['status','retained_models','raw_feature_value_and_clock_checks','training_frame_checks','inference_only_replayed_prediction_views','summary_views_checked','metric_checks','week8_issued']},indent=2))
