"""Missing startup/late-period numerical views from unchanged seasonal forecasts."""
import argparse,collections,csv,gzip,hashlib,json,math,resource,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2.shared_subgroups import canonical,sha,now,write
from nfl_v2.precision_grid import coordinate
from tools.numerical_championship import proc_id,product_id,csvwrite

VERSION='v2-complete-season-startup-retained-predictions-20261031i-v1'
SEASONS=(2025,2022,2023,2024)
FOLDERS={2025:'season-2025-v1',2022:'season-2022-v2',2023:'season-2023-complete-replay-v1',2024:'season-2024-v2'}

def recipe(r):return(r['target'],proc_id(r['procedure_id']),r['history_regime'],product_id(r['product_id']),r['policy_id'])
def numeric(v):return None if v in(None,'') else float(v)
def summary_sources(a,y):
    paths=[a.root/'reports/continuation-20261030c'/FOLDERS[y]/'SCORES.json']
    if y==2025:paths.append(a.root/'reports/continuation-20261030c/season-2025-continuity-repair-v1/SCORES.json')
    return paths
def summaries(a,y):
    rows={};bindings=[]
    for path in summary_sources(a,y):
        digest=sha(path);bindings.append(dict(path=path.relative_to(a.root).as_posix(),sha256=digest))
        for index,r in enumerate(json.loads(path.read_bytes())):
            if r.get('population')!='primary' or r.get('position')!='ALL' or r.get('fallback_view')!='ALL' or not isinstance(r.get('week'),int):continue
            if y==2025 and path==summary_sources(a,y)[0] and 'qb-rb-specialization' in r['procedure_id']:continue
            key=(recipe(r),r['week'])
            if key in rows:raise ValueError('duplicate current-valid weekly summary')
            rows[key]=(r,dict(source_artifact=path.relative_to(a.root).as_posix(),source_artifact_sha256=digest,source_row_index=index))
    return rows,bindings

def prepare(a):
    if a.output.exists():raise ValueError('fresh startup protocol required')
    a.output.mkdir(parents=True);raw=json.loads((a.root/'reports/championship-20261030f/numerical-v2/FROZEN_PROTOCOL.json').read_bytes());seasons=[]
    for y in SEASONS:
        rows,binding=summaries(a,y);roster=sorted({k for k,w in rows})
        for k in roster:
            if {w for rk,w in rows if rk==k}!=set(range(1,19)):raise ValueError('complete-season weekly inputs required')
        source=next(s for s in raw['sources'] if s['season']==y)
        for b in source['members']:
            if sha(a.private_root/b['member'])!=b['sha256']:raise ValueError('retained seasonal prediction source changed')
        seasons.append(dict(season=y,recipe_roster=[list(k) for k in roster],weekly_summary_bindings=binding,raw_sources=source['members'],existing_primary_weekly_fullsystem_cells=len(rows),existing_learned_scope='Full-season learned-only saved; exact startup/late learned/fallback split not retained as an aggregate',planned_windows=[dict(id='W1_W4_STARTUP',weeks=list(range(1,5))),dict(id='W5_W18_LATER',weeks=list(range(5,19)))],planned_partitions=['FULL_SYSTEM','LEARNED_ONLY','FALLBACK_ONLY']))
    p=dict(version=VERSION,at=now(),state='FROZEN_BEFORE_MISSING_STARTUP_AGGREGATION',code_sha256=sha(__file__),precision_helper_sha256=sha(a.root/'nfl_v2/precision_grid.py'),source_summary_adapters='Current-valid2025continuity repair replaces original specialization;2024v2/2023complete/2022v2 only; originals not overwritten.',seasons=seasons,execution_order=list(SEASONS),identity='Exact target/procedure/history/product/policy/primary population; output views are not independent learners. Use retained historical-origin forecasts only, never later-trained models.',metrics='Stream sufficient loss/precision/fallback counts; compare new full-system sums to completed weekly n*MAE/MSE/bias on identical recipe/week cells. No duplicated full-season score emission. Exact outcome-ID masks, games and players derived from retained IDs. P90/P95 not recomputed and cannot be pooled from weekly quantiles; explicit null. Max absolute error is exact streaming max.',partitions='Fallback field exactly none=>learned; other nonempty registered source fallback=>fallback. FULL=disjoint LEARNED+FALLBACK for issued/scored rows/loss sums; own learned pools can differ by history, so not a common-learned comparison.',precision='Native strict/inclusive1,5,10units and exact equality counts. Genuine chart lower-median/actual pairs use exact0.02coordinate support; means are never rounded. Precision repair is not predictive improvement.',history='Season-relativeCURRENT/RECENT/MULTI with common2022-start versus strict-current information separately preserved by procedure/policy.2022RECENT remains original2022-only source-limited proxy, not exact2021comparison. Expanding2022has no pre2022history.',population='Retrospective verified participant/stat-row primary roles; no historical exante/offer population claimed. Missing outcomes/points retained as missing, never zero. Basic NFLcurrent/revised source plus inherited7day availability reconstruction, previously exposed research.',offers='Numerical experimentA is independent of missing historical linesB and original selectionsC; no offered threshold, Over/Under or return score is invented.',budget_per_season=dict(wall_seconds=300,max_RSS_bytes=1073741824,max_native_threads=1,max_new_private_bytes=0),new_fits=0,new_model_inference=0,new_forecasts=0,new_NFL_observations=0,Week8_outcomes_read=0)
    write(a.output/'FROZEN_PROTOCOL.json',p);(a.output/'SOURCE_SNAPSHOT.py').write_bytes(Path(__file__).read_bytes());print(json.dumps(dict(protocol_sha256=sha(a.output/'FROZEN_PROTOCOL.json'),recipes_per_season={s['season']:len(s['recipe_roster']) for s in seasons},planned_new_window_partition_views=sum(len(s['recipe_roster'])*6 for s in seasons))))

class Acc:
    def __init__(self):
        self.issued=self.predicted=self.n=self.missingactual=self.fb=self.scoredfb=self.inf=0;self.ae=self.se=self.err=self.logsum=0.;self.maxabs=None;self.prec=collections.Counter();self.fallbacks=collections.Counter();self.issuedbits=self.scoredbits=self.gamebits=self.playerbits=0;self.weeks=set()
    def add(self,point,actual,fallback,qcode,gcode,pcode,week,target,product):
        bit=1<<qcode
        if self.issuedbits&bit:raise ValueError('duplicate exact recipe/query in source')
        self.issuedbits|=bit;self.issued+=1;self.weeks.add(week);self.predicted+=point is not None;self.missingactual+=actual is None;self.fb+=fallback!='none';self.fallbacks[fallback]+=1
        if point is None or actual is None:return
        if not math.isfinite(point) or not math.isfinite(actual):raise ValueError('nonfinite forecast/label')
        if target=='anytime_td' and not(0<=point<=1 and actual in(0,1)):raise ValueError('invalid event probability/label')
        self.n+=1;self.scoredfb+=fallback!='none';self.scoredbits|=bit;self.gamebits|=1<<gcode;self.playerbits|=1<<pcode;e=point-actual;ab=abs(e);self.err+=e;self.ae+=ab;self.se+=e*e;self.maxabs=ab if self.maxabs is None else max(self.maxabs,ab)
        exacterror=abs(coordinate(point)-coordinate(actual)) if target=='nick-chart-ppr-v1' and product=='lower_median' else None
        for t in(1,5,10):
            self.prec[f'abs_lt_{t}']+=(exacterror<50*t if exacterror is not None else ab<t);self.prec[f'abs_le_{t}']+=(exacterror<=50*t if exacterror is not None else ab<=t)
        self.prec['exact_rate']+=point==actual
        if target=='anytime_td':
            mass=point if actual else 1-point
            if mass==0:self.inf+=1
            else:self.logsum-=math.log(mass)

def run(a):
    p=json.loads((a.output/'FROZEN_PROTOCOL.json').read_bytes());start=time.monotonic();cpu=time.process_time();y=a.season;out=a.output/str(y)
    if out.exists():raise ValueError('preserve completed/failed year; new identity required')
    out.mkdir()
    if sha(__file__)!=p['code_sha256']:raise ValueError('frozen executor changed')
    spec=next(s for s in p['seasons'] if s['season']==y);roster={tuple(k) for k in spec['recipe_roster']};weekly,bindings=summaries(a,y)
    if bindings!=spec['weekly_summary_bindings']:raise ValueError('current-valid weekly source changed')
    acc=collections.defaultdict(Acc);byweek=collections.defaultdict(lambda:[0,0.,0.,0.]);outcomes={};qid={};games={};players={};scanned=used=0
    def guard():
        if time.monotonic()-start>300 or resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>1073741824:raise RuntimeError('bounded startup wave')
    for source in spec['raw_sources']:
        path=a.private_root/source['member']
        if sha(path)!=source['sha256']:raise ValueError('historical saved forecasts changed')
        with gzip.open(path,'rt') as file:
            for r in csv.DictReader(file):
                scanned+=1
                if scanned%10000==0:guard()
                if r['population']!='primary':continue
                if y==2025 and source['source_id']=='season' and 'qb-rb-specialization' in r['procedure_id']:continue
                k=recipe(r)
                if k not in roster:continue
                w=int(r['week'])
                if int(r['season'])!=y or w not in range(1,19):raise ValueError('unregistered source season/week')
                point,actual=numeric(r['prediction']),numeric(r['actual']);fallback=r['fallback']
                if not isinstance(fallback,str) or not fallback:raise ValueError('unknown source fallback origin')
                q=(r['game_id'],r['player_id'],r['target'],r['population'],r['position'])
                if q not in qid:qid[q]=len(qid);outcomes[q]=actual
                elif outcomes[q]!=actual:raise ValueError('label values differ across retained procedure rows')
                if r['game_id'] not in games:games[r['game_id']]=len(games)
                if r['player_id'] not in players:players[r['player_id']]=len(players)
                window='W1_W4_STARTUP' if w<=4 else 'W5_W18_LATER';origin='LEARNED_ONLY' if fallback=='none' else 'FALLBACK_ONLY'
                for view in('FULL_SYSTEM',origin):acc[k,window,view].add(point,actual,fallback,qid[q],games[r['game_id']],players[r['player_id']],w,r['target'],k[3])
                if point is not None and actual is not None:
                    z=byweek[k,w];z[0]+=1;z[1]+=abs(point-actual);z[2]+=(point-actual)**2;z[3]+=point-actual
                used+=1
    # Verify completed source scores; this does not emit duplicated season/week evaluations.
    verified=0
    for (k,w),(r,b) in weekly.items():
        n,ae,se,err=byweek[k,w]
        if n!=r['n']:raise ValueError('weekly n mismatch')
        for got,metric in((ae,'mae'),(se,'mse'),(err,'bias')):
            expected=(r.get(metric) or 0)*n
            if not math.isclose(got,expected,rel_tol=1e-10,abs_tol=1e-7):raise ValueError('weekly loss sum mismatch:'+metric)
        verified+=1
    universe=hashlib.sha256(canonical(sorted((code,q,outcomes[q]) for q,code in qid.items()))).hexdigest();scores=[]
    for k in sorted(roster):
        target,proc,arm,product,policy=k
        for window,weeks in(('W1_W4_STARTUP',list(range(1,5))),('W5_W18_LATER',list(range(5,19)))):
            aa,bb,cc=(acc[k,window,v] for v in('FULL_SYSTEM','LEARNED_ONLY','FALLBACK_ONLY'))
            if aa.issued!=bb.issued+cc.issued or aa.n!=bb.n+cc.n or aa.issuedbits!=(bb.issuedbits|cc.issuedbits) or bb.issuedbits&cc.issuedbits:raise ValueError('origin partition mismatch')
            for attr in('ae','se','err'):
                if not math.isclose(getattr(aa,attr),getattr(bb,attr)+getattr(cc,attr),rel_tol=1e-10,abs_tol=1e-7):raise ValueError('loss partition mismatch')
            for view in('FULL_SYSTEM','LEARNED_ONLY','FALLBACK_ONLY'):
                z=acc[k,window,view];n=z.n;precision={name:dict(numerator=z.prec[name],denominator=n,rate=z.prec[name]/n if n else None) for name in ['exact_rate']+[f'abs_{op}_{t}' for t in(1,5,10) for op in('lt','le')]};bits=z.scoredbits.to_bytes((len(qid)+7)//8,'little');mask=hashlib.sha256(bytes.fromhex(universe)+bits).hexdigest();rid='STARTUP-'+hashlib.sha256(canonical([y,k,window,view])).hexdigest()[:24]
                row=dict(record_id=rid,record_kind='forecast_evaluation_view',procedure_id=proc,history_regime=arm,product_id=product,policy_id=policy,target=target,season=y,week=window,evaluation_seasons=[y],evaluation_weeks=weeks,window_id=window,evaluation_panel_id=VERSION,population='primary_retrospective_participant_stat_row',position='ALL',fallback_view=view,forecast_rows=z.issued,available_prediction_rows=z.predicted,missing_prediction_n=z.issued-z.predicted,missing_actual_n=z.missingactual,n=n,mae=z.ae/n if n else None,mse=z.se/n if n else None,rmse=math.sqrt(z.se/n) if n else None,bias=z.err/n if n else None,max_abs=z.maxabs,p90_abs=None,p95_abs=None,tail_quantile_status='NOT_COMPUTED_IN_SUFFICIENT_STAT_AGGREGATION; weekly quantiles cannot be pooled; retained rows remain replayable',precision_counts=precision,fallback_rows=z.fb,fallback_rate=z.fb/z.issued if z.issued else None,scored_fallback_rows=z.scoredfb,scored_fallback_rate=z.scoredfb/n if n else None,fallback_source_counts=dict(z.fallbacks),unique_games=z.gamebits.bit_count(),unique_players=z.playerbits.bit_count(),unique_target_player_game_rows=z.scoredbits.bit_count(),membership_sha256=mask,source_outcome_index_sha256=universe,source_vintage='CURRENT_REVISED_NFL_FOOTBALL;INHERITED_7DAY_AVAILABILITY_RECONSTRUCTION;NOT_ORIGINAL_ISSUANCE',horizon_id='ORIGINAL_REGISTERED_ROLLING_PER_GAME_KICKOFF_RECONSTRUCTION',history_status='SOURCE_LIMITED_2022_ONLY_RECENT_PROXY' if y==2022 and arm=='H-RECENT' else 'REGISTERED_SEASON_RELATIVE_HISTORY',feature_memory_policy='Strict evaluation-year inputs if strict policy/procedure; otherwise registered2022-start common memory; empirical arm has no separate football feature memory',origin_partition_scope='Own procedure learned/fallback partition, not a common-learned comparison across different procedures/arms',source_records=[b for (rk,w),(r,b) in weekly.items() if rk==k and w in weeks],evidence='NEW_STARTUP_PERIOD_AGGREGATION_OF_COMPLETED_HISTORICAL_FORECASTS',new_fits=0,new_model_inference=0,new_NFL_observations=0,null_reason=None if n else 'NO_SUPPORTED_ROWS_IN_REGISTERED_WINDOW_ORIGIN_PARTITION')
                if target=='anytime_td':row.update(brier=z.se/n if n else None,log_loss='Infinity' if z.inf else z.logsum/n if n else None,infinite_log_losses=z.inf,probability_target='AT_LEAST_ONE_RUSHING_OR_RECEIVING_TD_EXCLUDES_RETURNS')
                scores.append(row)
    write(out/'SCORES.json',scores);csvwrite(out/'STARTUP_NUMERICAL_RESULTS.csv',scores);guard();write(out/'RUN_RECEIPT.json',dict(state='COMPLETE_MISSING_STARTUP_SPLIT_FROM_RETAINED_ROWS',at=now(),season=y,protocol_sha256=sha(a.output/'FROZEN_PROTOCOL.json'),score_sha256=sha(out/'SCORES.json'),recipe_output_history_cells=len(roster),startup_window_partition_score_views=len(scores),weekly_fullsystem_reference_checks=verified,raw_rows_scanned=scanned,retained_primary_prediction_rows_used=used,distinct_target_player_game_ids=len(qid),unique_games=len(games),unique_players=len(players),origin_partition_checks='PASS',private_derivative_bytes=0,new_fits=0,new_model_inference=0,new_forecasts=0,new_NFL_observations=0,resources=dict(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)))
    print(json.dumps(dict(season=y,score_views=len(scores),recipes=len(roster),weekly_checks=verified,raw_rows=scanned,wall_seconds=time.monotonic()-start)))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=('prepare','run'));p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--private-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--season',type=int,choices=SEASONS);a=p.parse_args();prepare(a) if a.action=='prepare' else run(a)
