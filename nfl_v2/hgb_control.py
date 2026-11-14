"""New fixed HGB history reconstruction and genuine current research shadows.

Prior HGB studies remain separate. No acquisition, search, production publication
or modification of the frozen empirical engine is performed by this module.
"""
from __future__ import annotations

import bisect
import collections
import csv
import gzip
import hashlib
import json
import math
import pickle
import platform
import resource
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import sklearn
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from threadpoolctl import threadpool_limits

from . import empirical_benchmark as empirical
from .week8_shadow import schedules, utc

VERSION = "v2-hgb-direct-history-controls-v1"
TARGETS = tuple(empirical.MAP) + ("rush_rec_yd", "anytime_td")
POSITIONS = ("QB", "RB", "WR", "TE")
ARMS = ("H-CURRENT", "H-RECENT", "H-MULTI")
FEATURES = ("mean3", "n3", "mean8", "n8") + tuple(f"lag{i}_{field}" for i in range(1,5) for field in ("value", "age_days", "missing")) + tuple("position_"+p for p in POSITIONS)
PARAMS = dict(max_iter=64, max_depth=3, max_leaf_nodes=31, min_samples_leaf=10,
              learning_rate=.05, l2_regularization=10, random_state=1701,
              early_stopping=False, categorical_features=None, max_bins=255)


def now():
    return datetime.now(timezone.utc).isoformat()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def immutable_json(path, value):
    with Path(path).open("xb") as handle:
        handle.write(canonical(value))
        handle.flush()
        import os
        os.fsync(handle.fileno())


def objectives(target):
    return ("log_loss_probability",) if target == "anytime_td" else ("absolute_error_point", "squared_error_mean")


def fit_floor(arm):
    return 2026 if arm == "H-CURRENT" else 2025 if arm == "H-RECENT" else 2022


def train_indices(rows, origin, floor):
    return np.asarray([i for i,r in enumerate(rows) if floor <= r["season"] <= 2026 and r["available"] < origin], dtype=int)


class FeatureHistory:
    """Target slots from strictly earlier available games; missing slots remain."""
    def __init__(self, rows):
        self.rows = collections.defaultdict(list)
        for r in rows:
            self.rows[r["player_id"]].append(r)
        self.times = {}
        for pid, values in self.rows.items():
            values.sort(key=lambda r:(r["available"],r["kickoff"],r["game_id"]))
            self.times[pid] = [r["available"] for r in values]

    def get(self, player_id, position, target, cutoff):
        rows = self.rows.get(player_id, [])
        right = bisect.bisect_left(self.times.get(player_id, []), cutoff)
        selected = rows[max(0,right-8):right]
        result = []
        for window in (3,8):
            values = [r["values"][target] for r in selected[-window:] if r["values"][target] is not None]
            result.extend((sum(values)/len(values) if values else math.nan, float(len(values))))
        for lag in range(1,5):
            row = selected[-lag] if len(selected) >= lag else None
            value = row["values"][target] if row else None
            result.extend((value if value is not None else math.nan,
                           (cutoff-row["kickoff"])/86400 if row else math.nan,
                           float(value is None)))
        result.extend(float(position == p) for p in POSITIONS)
        maximum = selected[-1]["available"] if selected else None
        if maximum is not None and maximum >= cutoff:
            raise AssertionError("feature chronology")
        return result, maximum


def make_estimator(target, objective):
    if target == "anytime_td":
        return HistGradientBoostingClassifier(loss="log_loss", **PARAMS)
    return HistGradientBoostingRegressor(loss="absolute_error" if objective == "absolute_error_point" else "squared_error", **PARAMS)


def project_point(target, value):
    if not math.isfinite(float(value)):
        raise ValueError("nonfinite model prediction")
    return max(0.,float(value)) if target in empirical.COUNTS else float(value)


def prepare(source_root, empirical_private, week8_private, empirical_protocol, public_root, private_root):
    """Freeze source bytes and memberships before new numeric features/fits."""
    source_root, public_root, private_root = map(Path,(source_root,public_root,private_root))
    public_root.mkdir(parents=True,exist_ok=True);private_root.mkdir(parents=True,exist_ok=True)
    old_protocol = json.loads(Path(empirical_protocol).read_text())
    historic = []
    with gzip.open(empirical_private,"rt",newline="") as handle:
        for r in csv.DictReader(handle):
            if r["season"] == "2026" and r["history_regime"] == "H-CURRENT" and r["product"] in ("empirical_mean","event_probability"):
                historic.append({k:r[k] for k in ("season","week","game_id","player_id","position","target","population")})
    identities = [(r["game_id"],r["player_id"],r["target"],r["population"]) for r in historic]
    if len(identities)!=len(set(identities)):
        raise ValueError("duplicate historical membership")
    future = json.loads(Path(week8_private).read_text())
    query_document = dict(historical=historic,week8=future)
    immutable_json(private_root/"frozen-queries.json",query_document)
    matrix = [dict(origin=origin,target=target,history_regime=arm,objective=objective,state="REGISTERED")
              for origin in (8,1,2,3,4,5,6,7) for target in TARGETS for arm in ARMS for objective in objectives(target)]
    protocol = dict(version=VERSION,state="FROZEN_BEFORE_NEW_FEATURES_AND_HGB_FITS",
        registered_at_utc=now(),previous_research_exposure="Empirical diagnostic and legacy HGB results already exposed; no untouched historical claim",
        code_sha256=sha(__file__),helper_code_sha256=sha(empirical.__file__),
        schedule_adapter_sha256=sha(Path(__file__).with_name('week8_shadow.py')),
        source_ids=[dict(name=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in [source_root/f"stats_player_week_{y}.csv" for y in range(2022,2027)]+[source_root/'games.csv']],
        empirical_predictions_sha256=sha(empirical_private),empirical_protocol_sha256=sha(empirical_protocol),
        source_role_contract=dict(primary=old_protocol['primary_roles'],extended=old_protocol['extended_roles']),
        frozen_queries_sha256=sha(private_root/'frozen-queries.json'),
        historical_membership_sha256=hashlib.sha256(canonical(historic)).hexdigest(),
        week8_membership_sha256=sha(week8_private),historical_query_cells=len(historic),week8_query_cells=len(future),
        targets=list(TARGETS),chart="BLOCKED_EXACT_RARE_COMPONENT_LABEL_CONTRACT",
        feature_columns=list(FEATURES),feature_memory="common2022-start earlier available own target slots across all fit arms; H-CURRENT is current-season FITTING, not pure current-season information",
        feature_contract="last3/8 roster/stat slots, finite mean/count; ordered4value/age/missing; unknown slots consume slots; positiononehot; no learned transforms or other inputs",
        history_regimes={"H-CURRENT":[2026],"H-RECENT":[2025,2026],"H-MULTI":[2022,2023,2024,2025,2026]},
        weekly_refit="oncebeforeearliestkickoffeach2026week, eligiblelabelavailabilitystrictlyearlier; Week8realcurrentorigin",
        query_refresh="historical per-game kickoff leftlimit; Week8actualcommoncurrentfeatureorigin; no targetgame outcomes",
        availability="kickoff+7days reconstruction assumption; sourcecurrentvintage, publicationunknown; same acrossarms",
        params=PARAMS,minimum_training_rows=40,binary_requirement="bothclasses;otherwiseexplicitfallback",
        fallback="samearm own/sameposition empirical then samearmposition empirical then literal0; per-query cutoff; blockedqueryABSTAIN",
        output_contract="absolute-loss point and squared-loss intendedmean separateobjectiveprocedures; countsmax0projection,norounding;signedyardsunclipped;noauthenticatednumericdistribution",
        anytimeTD="HGBClassifier logloss binary probability, uncalibrated; no extra median/count product",
        source_policy="sameobservedstatrow/positivephysicalproof/explicitzeros as empiricaldiagnostic; no PFRsnaps/EPA/NGS/markets/injuries",
        origin_order=[8,1,2,3,4,5,6,7],category_order=list(TARGETS),grid=matrix,
        budget=dict(max_fit_calls=504,wall_seconds=1200,cpu_seconds=1800,max_peak_memory_bytes=2147483648,
                    max_private_bytes=536870912,max_source_rows=200000,max_forecast_rows=2000000,max_threads=2,hyperparameter_searches=0),
        software_checks_required="hgb_control_tests_v1PASSbeforefirstNFLfit",
        cohort="samefrozen2026W1-W7observedstatrowprimary/extendeddiagnostic; Week8original1951exantefeedqueries and retainedabstentions",
        new_method_status="newsource-matchedHGBprocedure/version, notdiscoveryofHGB; priorexperiments/failurespreserved")
    immutable_json(public_root/"FROZEN_PROTOCOL.json",protocol)
    return protocol


def load_source(source_root, protocol):
    source_root=Path(source_root);games=schedules(source_root/'games.csv')
    needed=set(empirical.MAP.values())|set(empirical.PHYSICAL_COUNTS)|set(empirical.PHYSICAL_YARDS)|{'rushing_tds','receiving_tds'}
    rows=[];seen=set();counts=collections.Counter()
    for year in range(2022,2027):
        with (source_root/f'stats_player_week_{year}.csv').open() as handle:
            reader=csv.DictReader(handle)
            if not needed<=set(reader.fieldnames):raise ValueError('source schema')
            for r in reader:
                counts['source_rows']+=1
                if counts['source_rows']>protocol['budget']['max_source_rows']:raise ValueError('source row budget')
                if r['season_type']!='REG' or int(r['season'])!=year or (year==2026 and int(r['week'])>7):continue
                if r['position'] not in POSITIONS or not __import__('re').fullmatch(r'00-\d{7}',r['player_id']):continue
                game=games.get(r['game_id'])
                if not game or game['season']!=year or game['week']!=int(r['week']):raise ValueError('history game binding')
                if (r['team'],r['opponent_team']) not in ((game['home'],game['away']),(game['away'],game['home'])):raise ValueError('history team binding')
                key=(r['game_id'],r['player_id'])
                if key in seen:raise ValueError('duplicate history identity')
                seen.add(key)
                v={k:empirical.numeric(r[k]) for k in needed}
                played=any(empirical.valid_count(v[k]) and v[k]>0 for k in empirical.PHYSICAL_COUNTS) or any(v[k] is not None and v[k]!=0 for k in empirical.PHYSICAL_YARDS)
                rows.append(dict(season=year,week=int(r['week']),game_id=r['game_id'],player_id=r['player_id'],position=r['position'],kickoff=game['kickoff'],available=game['kickoff']+7*86400,values={t:empirical.target_value(t,v) if played else None for t in TARGETS},played=played))
                counts['played' if played else 'unknown_participation']+=1
    return rows,games,dict(counts)


def allowed_roles(protocol,target):
    roles=protocol['source_role_contract']
    return set(roles['primary'][target])|set(roles['extended'].get(target,[]))


def json_features(values):
    return [float(x) if math.isfinite(float(x)) else None for x in values]


def run(source_root, public_root, private_root):
    start,cpu=time.monotonic(),time.process_time()
    source_root,public_root,private_root=map(Path,(source_root,public_root,private_root))
    protocol_path=public_root/'FROZEN_PROTOCOL.json';protocol=json.loads(protocol_path.read_text())
    if protocol['version']!=VERSION or protocol['code_sha256']!=sha(__file__) or protocol['helper_code_sha256']!=sha(empirical.__file__):raise ValueError('changed code/protocol')
    checks=json.loads((public_root/'SOFTWARE_CHECKS.json').read_text())
    if checks['state']!='PASS' or checks['hgb_code_sha256']!=sha(__file__):raise ValueError('software checks required')
    for source in protocol['source_ids']:
        if sha(source_root/source['name'])!=source['sha256']:raise ValueError('changed source')
    if sha(private_root/'frozen-queries.json')!=protocol['frozen_queries_sha256']:raise ValueError('changed queries')
    future_origin=datetime.now(timezone.utc).timestamp()
    immutable_json(public_root/'EXECUTION_REGISTRATION.json',dict(version=VERSION,protocol_sha256=sha(protocol_path),actual_week8_feature_origin_utc=datetime.fromtimestamp(future_origin,timezone.utc).isoformat(),actual_started_at=now(),environment=dict(python=platform.python_version(),numpy=np.__version__,sklearn=sklearn.__version__),params=PARAMS))
    queries=json.loads((private_root/'frozen-queries.json').read_text())
    source_rows,games,source_counts=load_source(source_root,protocol);lookup={(r['game_id'],r['player_id']):r for r in source_rows}
    feature_history=FeatureHistory(source_rows);datasets={};fallbacks={}
    for target in TARGETS:
        eligible=[r for r in source_rows if r['position'] in allowed_roles(protocol,target) and r['values'][target] is not None]
        x,maximum=[],[]
        for r in eligible:
            f,m=feature_history.get(r['player_id'],r['position'],target,r['kickoff']);x.append(f);maximum.append(m)
        datasets[target]=(eligible,np.asarray(x,dtype=float),np.asarray([r['values'][target] for r in eligible]),maximum)
        for arm in ARMS:
            group=collections.defaultdict(list)
            for r in eligible:
                if r['season']>=fit_floor(arm):
                    item=(r['available'],(r['game_id'],r['player_id']),r['values'][target]);group[(r['position'],r['player_id'])].append(item);group[(r['position'],None)].append(item)
            fallbacks[(target,arm)]={k:empirical.Series(v) for k,v in group.items()}
    historical=collections.defaultdict(list)
    for q in queries['historical']:
        r=lookup.get((q['game_id'],q['player_id']))
        if not r or r['position']!=q['position']:raise ValueError('frozen historical cohort no longer binds')
        historical[int(q['week'])].append(dict(q,kickoff=r['kickoff'],cutoff=r['kickoff'],actual=r['values'][q['target']],blocked_reason=None))
    future=[dict(q,season=2026,week=8,population='original_pregame_feed',kickoff=utc(q['kickoff_utc']).timestamp(),cutoff=future_origin,actual=None) for q in queries['week8']]
    origins={w:min(g['kickoff'] for g in games.values() if g['season']==2026 and g['week']==w) for w in range(1,8)};origins[8]=future_origin
    fits=[];model_count=fit_calls=private_bytes=0;forecast_count=0;all_records=[];week8_records=[];failures=[];grid=[]
    metric_groups=collections.defaultdict(empirical.Metrics)
    (private_root/'models').mkdir(exist_ok=True);(private_root/'query-features').mkdir(exist_ok=True);(private_root/'prediction-chunks').mkdir(exist_ok=True)
    def check_budget():
        if time.monotonic()-start>protocol['budget']['wall_seconds']:raise RuntimeError('WALL_BUDGET')
        if time.process_time()-cpu>protocol['budget']['cpu_seconds']:raise RuntimeError('CPU_BUDGET')
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>protocol['budget']['max_peak_memory_bytes']:raise RuntimeError('RSS_BUDGET')
        if private_bytes>protocol['budget']['max_private_bytes']-4194304:raise RuntimeError('PRIVATE_BYTE_BUDGET')
    def save_gzip(path,value,raw=False):
        nonlocal private_bytes
        body=value if raw else canonical(value);compressed=gzip.compress(body,mtime=0)
        if private_bytes+len(compressed)>protocol['budget']['max_private_bytes']-4194304:raise RuntimeError('PRIVATE_BYTE_BUDGET')
        with path.open('xb') as handle:
            handle.write(compressed);handle.flush();__import__('os').fsync(handle.fileno())
        private_bytes+=len(compressed)
        return dict(name=path.relative_to(private_root).as_posix(),bytes=len(compressed),sha256=sha(path),uncompressed_sha256=hashlib.sha256(body).hexdigest())
    terminal='COMPLETE'
    with threadpool_limits(limits=2):
        try:
            for week in protocol['origin_order']:
                origin=origins[week];population=future if week==8 else historical[week]
                for target in TARGETS:
                    check_budget();qrows=[q for q in population if q['target']==target];qfeatures=[];qmax=[]
                    for q in qrows:
                        if q['blocked_reason']:f,m=[math.nan]*len(FEATURES),None
                        else:f,m=feature_history.get(q['player_id'],q['position'],target,q['cutoff'])
                        qfeatures.append(f);qmax.append(m)
                    qx=np.asarray(qfeatures,dtype=float)
                    feature_packet=save_gzip(private_root/'query-features'/f'W{week:02}-{target}.json.gz',[dict(query=q,features=json_features(f),latest_feature_available=m) for q,f,m in zip(qrows,qfeatures,qmax)])
                    trainrows,trainx,trainy,trainmax=datasets[target]
                    for arm in ARMS:
                        indices=train_indices(trainrows,origin,fit_floor(arm))
                        for objective in objectives(target):
                            check_budget();slot=f'W{week:02}-{target}-{arm}-{objective}';model=None;fitstate='NO_FIT_INSUFFICIENT_TRAINING';model_packet=None
                            audit=dict(slot=slot,origin=week,target=target,history_regime=arm,objective=objective,training_n=len(indices),fit_cutoff_utc=datetime.fromtimestamp(origin,timezone.utc).isoformat(),latest_training_label_available=max((trainrows[i]['available'] for i in indices),default=None),latest_training_feature_available=max((trainmax[i] for i in indices if trainmax[i] is not None),default=None),training_seasons=sorted({trainrows[i]['season'] for i in indices}),training_membership_sha256=hashlib.sha256(canonical([(trainrows[i]['game_id'],trainrows[i]['player_id']) for i in indices])).hexdigest(),actual_fit_started_at=None,actual_fit_completed_at=None)
                            if len(indices)>=40 and (target!='anytime_td' or len(np.unique(trainy[indices]))==2):
                                if fit_calls>=protocol['budget']['max_fit_calls']:raise RuntimeError('FIT_CALL_BUDGET')
                                fit_calls+=1;audit['actual_fit_started_at']=now()
                                try:
                                    model=make_estimator(target,objective);model.fit(trainx[indices],trainy[indices]);audit['actual_fit_completed_at']=now()
                                    model_packet=save_gzip(private_root/'models'/(slot+'.pickle.gz'),pickle.dumps(model,protocol=5),raw=True);model_count+=1;fitstate='FITTED_RETAINED'
                                except Exception as exc:
                                    fitstate='FIT_FAILED_FALLBACK';model=None;audit['actual_fit_completed_at']=now();failures.append(dict(slot=slot,exception=type(exc).__name__,reason=str(exc)[:300]))
                            elif target=='anytime_td' and len(indices)>=40:fitstate='NO_FIT_SINGLE_CLASS'
                            audit.update(state=fitstate,model=model_packet,query_features=feature_packet,iteration_count=int(model.n_iter_) if model is not None else None);fits.append(audit)
                            immutable_json(public_root/(slot+'-FIT.json'),audit)
                            if model is not None:
                                predicted=model.predict_proba(qx)[:,list(model.classes_).index(1.)] if target=='anytime_td' else model.predict(qx)
                            else:predicted=[None]*len(qrows)
                            generated=now();records=[]
                            for q,value,featuremax in zip(qrows,predicted,qmax):
                                blocked=q['blocked_reason'];fb='none';n=None;latest_fb=None
                                if week==8 and datetime.now(timezone.utc).timestamp()>=q['kickoff']:blocked=blocked or 'GAME_ALREADY_STARTED'
                                if blocked:prediction=None;fb=None
                                elif model is not None:prediction=project_point(target,value)
                                else:
                                    own=fallbacks[(target,arm)].get((q['position'],q['player_id']));summary=own.at(q['cutoff']) if own else (0,None,None,None)
                                    if summary[0]:fb='own_empirical'
                                    else:
                                        prior=fallbacks[(target,arm)].get((q['position'],None));summary=prior.at(q['cutoff']) if prior else (0,None,None,None);fb='position_empirical' if summary[0] else 'constant_zero'
                                    n,latest_fb=summary[0],summary[3];prediction=(summary[2] if objective=='absolute_error_point' else summary[1]) if n else 0.
                                record=dict(q,run_id=VERSION,history_regime=arm,objective=objective,prediction=prediction,fallback=fb,fallback_n=n,latest_fallback_available=latest_fb,latest_feature_available=featuremax,fit_slot=slot,fit_state=fitstate,actual_generated_at=generated,status='ABSTAIN' if blocked else 'FORECASTED',abstention_reason=blocked,evidence_tier='genuine_new_research_pregame_shadow' if week==8 else 'current_vintage_historical_reconstruction')
                                if week==8:record.update(issued_at_utc=generated,actual_horizon_seconds=q['kickoff']-utc(generated).timestamp(),owner_cutoff_status='LATER_THAN_OWNER_INPUT_CUTOFF' if utc(generated)>utc(q['owner_input_cutoff_utc']) else 'BEFORE_OWNER_INPUT_CUTOFF')
                                if featuremax is not None and featuremax>=q['cutoff']:raise AssertionError('queryfeatureleak')
                                if prediction is not None and week!=8:
                                    for suffix in (('ALL','ALL'),(str(week),'ALL'),('ALL',q['position'])):metric_groups[(target,q['population'],arm,objective)+suffix].add(prediction,q['actual'],fb,target)
                                records.append(record);forecast_count+=1
                            packet=save_gzip(private_root/'prediction-chunks'/(slot+'.json.gz'),dict(schema=VERSION,rows=records));persisted=now()
                            receipt=dict(slot=slot,packet=packet,actual_persistence_completed_at=persisted,rows=len(records),forecasted=sum(r['prediction'] is not None for r in records),abstained=sum(r['prediction'] is None for r in records),all_week8_forecasts_persisted_before_kickoff=all(utc(persisted).timestamp()<r['kickoff'] for r in records if r['prediction'] is not None) if week==8 else None)
                            immutable_json(public_root/(slot+'-FORECAST.json'),receipt);grid.append(dict(slot=slot,state=fitstate,forecast_receipt=receipt))
                            all_records.extend(records)
                            if week==8:week8_records.extend(records)
                if week==8:
                    summary=save_gzip(private_root/'WEEK8_SHADOWS.json.gz',dict(schema=VERSION,rows=week8_records))
                    immutable_json(public_root/'WEEK8_CAPTURE_RECEIPT.json',dict(state='CAPTURED_LOCAL_READBACK_PENDING_PRIVATE_UPLOAD',version=VERSION,packet=summary,output_views=len(week8_records),forecasted=sum(r['prediction'] is not None for r in week8_records),abstained=sum(r['prediction'] is None for r in week8_records),actual_completed_at=now(),cutoff_utc=datetime.fromtimestamp(future_origin,timezone.utc).isoformat(),unique_games=len({r['game_id'] for r in week8_records}),queries=protocol['week8_query_cells'],new_fit_calls=fit_calls,official_capture=False,website_published=False))
        except Exception as exc:
            terminal='PARTIAL_STOPPED';failures.append(dict(exception=type(exc).__name__,reason=str(exc)[:300]))
    scores=[dict(target=k[0],population=k[1],history_regime=k[2],objective=k[3],week=k[4],position=k[5],**value.result()) for k,value in sorted(metric_groups.items())]
    with (public_root/'SCORES.csv').open('x',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(dict.fromkeys(k for r in scores for k in r)));writer.writeheader();writer.writerows(scores)
    immutable_json(public_root/'SCORES.json',scores)
    completed={r['slot'] for r in grid};full_grid=[]
    for r in protocol['grid']:
        slot=f"W{r['origin']:02}-{r['target']}-{r['history_regime']}-{r['objective']}";full_grid.append(dict(r,slot=slot,state=next((x['state'] for x in grid if x['slot']==slot),'NOT_RUN_AFTER_BOUNDED_STOP')))
    immutable_json(public_root/'GRID_STATUS.json',full_grid);immutable_json(public_root/'FAILURES.json',failures)
    receipt=dict(version=VERSION,state=terminal,actual_completed_at=now(),protocol_sha256=sha(protocol_path),code_sha256=sha(__file__),source_counts=source_counts,fit_opportunities=504,actual_fit_calls=fit_calls,fitted_retained_models=model_count,failed_fits=sum(x.get('state')=='FIT_FAILED_FALLBACK' for x in fits),completed_cells=len(completed),remaining_cells=504-len(completed),forecast_output_views=forecast_count,score_views=len(scores),historical_query_cells=protocol['historical_query_cells'],week8_query_cells=protocol['week8_query_cells'],new_week8_shadows=len(week8_records),private_output_bytes=private_bytes,resource=dict(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,max_threads=2),private_durability='LOCAL_IMMUTABLE_PACKETS;OFFHOST_RESTORATION_SEPARATELY_ATTESTED',scientific_limit='Exposedsame2026games;fitwindowcomparisonwithcommonolderfeaturememory;observedparticipantdiagnosticnotexantehistoricalpopulation',chart='BLOCKED',official_capture=False,website_published=False)
    immutable_json(public_root/'RUN_RECEIPT.json',receipt)
    return receipt
