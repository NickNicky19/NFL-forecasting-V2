"""Saved-row chart-point-history cohorts. No fitting, inference or acquisition.

This is a new selector/version; the eleven-target workload scorer is untouched.
Missing qualified-chart slots consume the last-three window. Signed scores are
not opportunities and are never named workload in this contract.
"""
from __future__ import annotations
import bisect,collections,csv,gzip,hashlib,importlib.util,json,math,time
from datetime import datetime,timezone
from pathlib import Path
from statistics import fmean
from zoneinfo import ZoneInfo

VERSION='v2-chart-score-history-cohort-extension-v1'
TARGET='nick-chart-ppr-v1'
SNAPSHOT_SHA256='1a72e393f8c27c60348c9ceef38c042e515816255923fcdf2e37297ac1ab2c25'
CORE=('H-CURRENT','H-RECENT','H-MULTI')
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def digest(value):return hashlib.sha256(canonical(value)).hexdigest()
def load(path):return json.loads(Path(path).read_bytes())
def aware(value):
    t=datetime.fromisoformat(value.replace('Z','+00:00'))
    if t.tzinfo is None:raise ValueError('aware clock required')
    return t.timestamp()
def write(path,value):
    with Path(path).open('xb')as h:h.write(canonical(value))
def player(q):
    if q.get('player_id'):return q['player_id']
    if q.get('sleeper_id')is None:raise ValueError('exact blocked source identity required')
    return 'sleeper:'+str(q['sleeper_id'])
def identity(q):return(q['game_id'],player(q),q['target'],q['population'])


def band(value):
    if value is None:return 'unknown'
    if not math.isfinite(value):raise ValueError('nonfinite prior chart points')
    if value==0:return 'zero'
    return 'low'if value<=5 else'middle'if value<=15 else'high'


class ScoreHistory:
    def __init__(self,slots):
        self.rows=collections.defaultdict(list)
        for row in slots:self.rows[row['player_id']].append(row)
        self.times={}
        for pid,rows in self.rows.items():
            rows.sort(key=lambda r:(r['available'],r['game_id']));self.times[pid]=[r['available']for r in rows]
    def at(self,pid,cutoff):
        end=bisect.bisect_left(self.times.get(pid,[]),cutoff);rows=self.rows.get(pid,[])[max(0,end-3):end]
        points=[r['points']for r in rows if r['points']is not None]
        return dict(mean=fmean(points)if points else None,supported_slots=len(points),history_slots=len(rows),latest_available=max((r['available']for r in rows),default=None))


def memberships(queries,history,origins):
    groups=collections.defaultdict(list)
    for q in queries:groups[int(q['week']),q['population']].append(q)
    result={};summary=[]
    for(week,pop),rows in sorted(groups.items()):
        cutoff=origins[week];profiles={}
        for q in rows:
            pid=player(q)
            if pid in profiles:raise ValueError('duplicate chart player/week/population')
            # Unknown/blocked source contexts remain unranked even if another
            # source happens to supply a historical value for that raw ID.
            profiles[pid]=history.at(pid,cutoff)if not q.get('blocked_reason')else dict(mean=None,supported_slots=0,history_slots=0,latest_available=None)
        ranked=sorted((pid for pid,p in profiles.items()if p['mean']is not None),key=lambda pid:(-profiles[pid]['mean'],pid));ranks={pid:i+1 for i,pid in enumerate(ranked)}
        for q in rows:
            pid=player(q);rank=ranks.get(pid);views=['all']
            if rank is None:views.append('unranked')
            else:
                views.extend('top'+str(n)for n in(10,15,20)if rank<=n)
                views.append('rank1_10'if rank<=10 else'rank11_15'if rank<=15 else'rank16_20'if rank<=20 else'rank21plus')
            views.append('score_history_'+band(profiles[pid]['mean']))
            key=identity(q)
            if key in result:raise ValueError('duplicate frozen chart query')
            result[key]=dict(rank=rank,cohorts=views,ranking_cutoff=cutoff,selector_quantity='prior_chart_point_mean_last3_slots',**profiles[pid])
        summary.append(dict(week=week,target=TARGET,population=pop,query_rows=len(rows),ranked=len(ranked),unranked=len(rows)-len(ranked),blocked_source_contexts=sum(bool(q.get('blocked_reason'))for q in rows),selector_quantity='prior_chart_points_not_workload'))
    return result,summary


def schedules(path):
    games={}
    with Path(path).open()as h:
        for r in csv.DictReader(h):
            if r['game_type']!='REG'or int(r['season'])not in range(2022,2027):continue
            if int(r['season'])==2026 and int(r['week'])>8:continue
            dt=datetime.fromisoformat(r['gameday']+'T'+r['gametime']).replace(tzinfo=ZoneInfo('America/New_York'))
            games[r['game_id']]=dict(season=int(r['season']),week=int(r['week']),kickoff=dt.timestamp())
    return games


def evaluator(snapshot):
    if sha(snapshot)!=SNAPSHOT_SHA256:raise ValueError('original frozen scalar scorer snapshot mismatch')
    spec=importlib.util.spec_from_file_location('nfl_v2._frozen_pregame_scalar_snapshot',snapshot);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.evaluate


def prepare(*,chart_public,chart_private,source_root,scorer_snapshot,scope,public_output,private_output):
    chart_public,chart_private,source_root,public_output,private_output=map(Path,(chart_public,chart_private,source_root,public_output,private_output))
    if public_output.exists()or private_output.exists():raise ValueError('fresh immutable output directories required')
    if private_output.resolve().is_relative_to(Path(__file__).resolve().parents[1]):raise ValueError('private membership must remain outside public Git')
    base=load(chart_public/'FROZEN_PROTOCOL.json');run=load(chart_public/'RUN_RECEIPT.json');export=load(chart_public/'POSTRUN_REPLAY_RECEIPT.json')
    if sha(scorer_snapshot)!=SNAPSHOT_SHA256:raise ValueError('scalar snapshot changed')
    if sha(chart_private/'frozen-queries.json')!=base['frozen_queries_sha256']:raise ValueError('chart frozen query hash mismatch')
    if sha(chart_private/'qualified-chart-labels.json.gz')!=run['chart_label_packet']['sha256']:raise ValueError('qualified chart label hash mismatch')
    if sha(chart_private/'all-chart-predictions.csv.gz')!=export['flat_prediction_sha256']:raise ValueError('chart forecast export hash mismatch')
    for s in base['source_ids']:
        if sha(source_root/s['name'])!=s['sha256']:raise ValueError('original chart source hash mismatch')
    public_output.mkdir(parents=True);private_output.mkdir(parents=True)
    p=dict(version=VERSION,state='FROZEN_BEFORE_CHART_LOSS_DECODE',registered_at_utc=datetime.now(timezone.utc).isoformat(),code_sha256=sha(__file__),scope_sha256=sha(scope),scalar_scorer_snapshot_sha256=SNAPSHOT_SHA256,chart_protocol_sha256=sha(chart_public/'FROZEN_PROTOCOL.json'),chart_run_receipt_sha256=sha(chart_public/'RUN_RECEIPT.json'),chart_export_receipt_sha256=sha(chart_public/'POSTRUN_REPLAY_RECEIPT.json'),qualified_label_packet_sha256=run['chart_label_packet']['sha256'],chart_prediction_sha256=export['flat_prediction_sha256'],chart_query_sha256=base['frozen_queries_sha256'],chart_source_policy=base['chart_policy_id'],source_ids=base['source_ids'],selector='meanfinite signed chartpoints from last3earlieravailable playergameSLOTS; missing/rareunknown consumes slot; no reachback to completepoints',availability='kickoff+7days strictlyless than weeklyearliestkickoffminus90minutes; assumedpublication',ranking='descendingpriorchartmean then exactplayerID; common acrossfamilies/products/fitwindows/strictpolicy; unknownunranked',bands='score_history_unknown/zero/low<=5includingnegative/middle<=15/high>15; scorehistoryNOTworkload',historical_panel='2026W1-W7 fixed2394retrospectivestatrowqueries;35unknownlabelsretained',future_asof_utc=base['fixed_feature_origin_utc'],future_panel='same434originalfrozenplayergamechartunion/13openT90games;2blockedcontextsremainunranked; no futurelabels',strict_note='Commonselectorolderchartmemory is diagnostic, not a predictor or purecurrentselectedsystem; strictmodelandempiricalCURRENTaliasretained',views=['full_system','own_learned_only','three_history_learned_overlap','all_competitor_learned_overlap'],products='originalempiricalmean/lower_median and2directlawmean/lower_median points; no refit/aliasinflation; no new CRPS/PMF scores from point-onlycohortscorer',budget=dict(max_prediction_rows=300000,max_score_views=5000,wall_seconds=180,max_private_bytes=8388608),new_fits=0,new_forecasts=0,week8_outcomes_read=0)
    write(public_output/'FROZEN_PROTOCOL.json',p);return p


def run(*,chart_public,chart_private,source_root,scorer_snapshot,public_output,private_output):
    started=time.monotonic();chart_public,chart_private,source_root,public_output,private_output=map(Path,(chart_public,chart_private,source_root,public_output,private_output));p=load(public_output/'FROZEN_PROTOCOL.json')
    if p['code_sha256']!=sha(__file__)or p['scalar_scorer_snapshot_sha256']!=sha(scorer_snapshot):raise ValueError('frozen code changed')
    for file,key in [('qualified-chart-labels.json.gz','qualified_label_packet_sha256'),('all-chart-predictions.csv.gz','chart_prediction_sha256'),('frozen-queries.json','chart_query_sha256')]:
        if sha(chart_private/file)!=p[key]:raise ValueError('frozen chart artifact changed')
    for s in p['source_ids']:
        if sha(source_root/s['name'])!=s['sha256']:raise ValueError('source changed')
    checks=load(public_output/'SOFTWARE_CHECKS.json')
    if checks['status']!='PASS'or checks['code_sha256']!=sha(__file__):raise ValueError('exact-code software checks required')
    write(public_output/'EXECUTION_REGISTRATION.json',dict(version=VERSION,actual_started_at_utc=datetime.now(timezone.utc).isoformat(),protocol_sha256=sha(public_output/'FROZEN_PROTOCOL.json'),new_fits=0,new_forecasts=0,week8_outcomes_read=0))
    games=schedules(source_root/'games.csv');packet=json.loads(gzip.decompress((chart_private/'qualified-chart-labels.json.gz').read_bytes()));slots=[];labels={};status_counts=collections.Counter()
    for r in packet['rows']:
        year,week=int(r['season']),int(r['week'])
        if year not in range(2022,2027)or(year==2026 and week>7):continue
        label=r['label'];grid=label.get('points_times_50');value=label.get('points')
        if grid is not None:
            if(type(grid)not in(int,float)or not math.isfinite(grid)or int(grid)!=grid or value!=grid/50 or not label['appearance_verified']or not label['game_completed_verified']or label['target_id']!=TARGET):raise ValueError('unqualified chart numeric label')
        elif value is not None:raise ValueError('chart grid and point null must agree')
        game=games[r['game_id']]
        if(game['season'],game['week'])!=(year,week):raise ValueError('chart game binding')
        key=r['game_id'],r['player_id']
        if key in labels:raise ValueError('duplicate qualified chart identity')
        labels[key]=value;slots.append(dict(player_id=r['player_id'],game_id=r['game_id'],available=game['kickoff']+604800,points=value));status_counts[label['status']]+=1
    query=load(chart_private/'frozen-queries.json');historical=[q for q in query['historical']if int(q['season'])==2026 and int(q['week'])<=7];history=ScoreHistory(slots)
    origins={w:min(g['kickoff']for g in games.values()if g['season']==2026 and g['week']==w)-5400 for w in range(1,8)}
    member,coverage=memberships(historical,history,origins)
    future=[dict(q,season=2026,week=8,population='frozen_exante_chart_union')for q in query['week8']]
    if any(datetime.now(timezone.utc).timestamp()>=aware(q['owner_input_cutoff_utc'])for q in future):raise ValueError('future cohort frozen after T90')
    fm,fc=memberships(future,history,{8:aware(p['future_asof_utc'])})
    for filename,values in [('memberships.json.gz',member),('future-memberships.json.gz',fm)]:
        body=gzip.compress(canonical([dict(key=k,**v)for k,v in values.items()]),mtime=0)
        if len(body)>p['budget']['max_private_bytes']:raise RuntimeError('PRIVATE_BYTES')
        with(private_output/filename).open('xb')as h:h.write(body)
    records=[];families=collections.Counter()
    with gzip.open(chart_private/'all-chart-predictions.csv.gz','rt',newline='')as h:
        for r in csv.DictReader(h):
            # Filter FUTURE and older-season records BEFORE decoding actuals.
            if int(r['season'])!=2026 or int(r['week'])>7:continue
            if len(records)>=p['budget']['max_prediction_rows']or time.monotonic()-started>p['budget']['wall_seconds']:raise RuntimeError('REPLAY_BUDGET')
            r['week']=int(r['week']);r['season']=2026
            if r['target']!=TARGET or identity(r)not in member:raise ValueError('forecast outside fixed chart query')
            for field in('prediction','actual'):
                r[field]=None if r[field]==''else float(r[field])
                if r[field]is not None and not math.isfinite(r[field]):raise ValueError('nonfinite chart point')
            if r['actual']!=labels[r['game_id'],r['player_id']]:raise ValueError('forecast actual differs from qualified chart source')
            if r['fallback']=='':raise ValueError('explicit fallback required')
            records.append(r);families[r['procedure_id']]+=1
    scores=evaluator(scorer_snapshot)(records,member,sha(public_output/'FROZEN_PROTOCOL.json'))
    if len(scores)>p['budget']['max_score_views']or time.monotonic()-started>p['budget']['wall_seconds']:raise RuntimeError('OUTPUT_BUDGET')
    for s in scores:
        s.update(record_id='CHART-'+s['record_id'],evaluation_panel_id=VERSION,cohort_limit=p['historical_panel']+';qualifiedpartialchartlabelpolicy;commonpriorSCOREmembershipNOTworkload',selector_quantity='prior_chart_point_mean_last3_slots',chart_source_policy=p['chart_source_policy'],point_grid_denominator=50)
    write(public_output/'SCORES.json',scores)
    with(public_output/'SCORES.csv').open('x',newline='')as h:
        fields=list(dict.fromkeys(k for s in scores for k in s));w=csv.DictWriter(h,fieldnames=fields);w.writeheader();w.writerows({k:json.dumps(v,sort_keys=True)if isinstance(v,(list,dict))else v for k,v in s.items()}for s in scores)
    write(public_output/'MEMBERSHIP_COVERAGE.json',coverage);write(public_output/'FUTURE_EXANTE_COHORT_COVERAGE.json',dict(state='FROZEN_UNSCORED_PREGAME_CHART_SCORE_COHORT',coverage=fc,query_cells=len(future),unique_games=len({q['game_id']for q in future}),blocked_contexts=sum(bool(q.get('blocked_reason'))for q in future),feature_cutoff_utc=p['future_asof_utc'],actual_frozen_at_utc=datetime.now(timezone.utc).isoformat(),membership_sha256=sha(private_output/'future-memberships.json.gz'),actuals_read=0,not_actual_T90_snapshot=True))
    receipt=dict(version=VERSION,state='SCORED_NEW_CHART_COHORT_VIEWS',actual_completed_at_utc=datetime.now(timezone.utc).isoformat(),protocol_sha256=sha(public_output/'FROZEN_PROTOCOL.json'),code_sha256=sha(__file__),scalar_scorer_snapshot_sha256=SNAPSHOT_SHA256,query_cells=len(member),supported_current_labels=sum(labels[q['game_id'],q['player_id']]is not None for q in historical),unknown_current_labels=sum(labels[q['game_id'],q['player_id']]is None for q in historical),retained_prediction_views=len(records),supported_scored_prediction_views=sum(r['actual']is not None and r['prediction']is not None for r in records),score_views=len(scores),unique_games=len({q['game_id']for q in historical}),unique_player_games=len({(q['game_id'],q['player_id'])for q in historical}),source_label_slots=len(slots),source_label_status_counts=dict(status_counts),procedures=dict(families),future_query_cells=len(future),future_games=len({q['game_id']for q in future}),membership_sha256=sha(private_output/'memberships.json.gz'),future_membership_sha256=sha(private_output/'future-memberships.json.gz'),score_sha256=sha(public_output/'SCORES.json'),new_fits=0,new_forecasts=0,week8_outcomes_read=0,wall_seconds=time.monotonic()-started,private_durability='LOCAL_READBACK_PENDING_COMPANION_RECEIPT')
    write(public_output/'RUN_RECEIPT.json',receipt);return receipt
