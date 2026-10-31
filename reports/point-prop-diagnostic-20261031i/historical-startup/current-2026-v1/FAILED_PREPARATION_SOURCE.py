"""Current-year adapters reuse the sealed historical startup accumulator."""
import argparse,collections,csv,gzip,hashlib,json,math,resource,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2.shared_subgroups import canonical,sha,now,write,packet_rows
from tools.aggregate_historical_startup import Acc,numeric
from tools.numerical_championship import normalize,proc_id,product_id,csvwrite

VERSION='v2-fixed-2026-W1-W7-startup-retained-adapter-20261031i-v1'
GRID='reports/completion-20261031g/roster/finite-v2/CURRENT_METHOD_COMPARISONS.json'
DECISIONS='reports/championship-20261030f/category-selector-v2/DECISIONS.json'
def key(r):return(r['target'],proc_id(r['procedure_id']),r['history_regime'],product_id(r['product_id']))


def prepare(a):
    if a.output.exists():raise ValueError('fresh current startup identity required')
    a.output.mkdir(parents=True);grid=json.loads((a.root/GRID).read_bytes());valid=[r for r in grid if r['state']=='COMPLETED_VALID'];roster={key(r):r for r in valid};source=next(s for s in json.loads((a.root/'reports/championship-20261030f/numerical-v2/FROZEN_PROTOCOL.json').read_bytes())['sources'] if s['season']==2026)
    for r in source['members']:
        if sha(a.private_root/r['member'])!=r['sha256']:raise ValueError('existing source changed')
    decisions=json.loads((a.root/DECISIONS).read_bytes());routes=[]
    for r in decisions:
        chosen=(r['target'],proc_id(r['chosen_procedure_id']),'H-MULTI',product_id(r['chosen_product_id']));policy=(r['target'],'v2-chronological-category-score-memory-selector-v2:'+r['policy_id'],'H-MULTI','event_probability_policy' if r['target']=='anytime_td' else 'point_choice_policy')
        if chosen not in roster or policy not in roster:raise ValueError('registered policy does not map directly to a retained fixed recipe')
        routes.append(dict(week=r['evaluation_week'],chosen=list(chosen),policy=list(policy),earlier_score_weeks=r['current_score_weeks_available']))
    p=dict(version=VERSION,state='FROZEN_BEFORE_CURRENT_STARTUP_AGGREGATION',at=now(),code_sha256=sha(__file__),accumulator_code_sha256=sha(a.root/'tools/aggregate_historical_startup.py'),normalizer_code_sha256=sha(a.root/'tools/numerical_championship.py'),current_grid_path=GRID,current_grid_sha256=sha(a.root/GRID),selector_decisions_path=DECISIONS,selector_decisions_sha256=sha(a.root/DECISIONS),fixed_and_policy_roster=[dict(key=list(k),source_state=r['state'],kind=r['procedure_kind'],information_policy=r['information_policy'],source_record=r) for k,r in sorted(roster.items())],unrun_strict_HGB=[r for r in grid if r['state']!='COMPLETED_VALID'],raw_sources=source['members'],registered_routes=routes,windows=[dict(id='W1_W4_STARTUP',weeks=[1,2,3,4]),dict(id='W5_W7_LATER',weeks=[5,6,7])],partitions=['FULL_SYSTEM','LEARNED_ONLY','FALLBACK_ONLY'],scope='Only original retained2026W1–7forecasts; no W8numeric conversion/label acquisition, no later trained model use. Reuse sameAcc engine. Verify all656existingfullperiod n/MAE/MSE/bias before publication. New windows only, not duplicatefullperiod scores.',selector_scope='36alreadyregistered earlier-only category policies copied from252frozen weekly decisions and selected underlying retained points. No new decision/routing/hindsight choice. Learned/fallback describes underlying forecaster, not whether current score memory was empty.',metric_rules='Same frozen historical startup accumulator and exactchartmedian0.02precision. Fullsystem includes allregisteredcoldstart/fallbacks. Ownlearned masks differ; not common-historymask effect. P90/P95uncomputed, max exact.',population='Primary retrospective participant/statrow; pergame kickoff reconstruction, current/revised NFLsource/inherited7d availability. Current-season fit with oldmemory is not strictcurrentinformation. Chart remainsqualifiedpartiallabels.',budget=dict(wall_seconds=300,max_RSS_bytes=1073741824,max_native_threads=1,max_private_bytes=0),new_fits=0,new_model_inference=0,new_forecasts=0,new_NFL_observations=0)
    write(a.output/'FROZEN_PROTOCOL.json',p);(a.output/'SOURCE_SNAPSHOT.py').write_bytes(Path(__file__).read_bytes());print(json.dumps(dict(protocol_sha256=sha(a.output/'FROZEN_PROTOCOL.json'),valid_cells=len(roster),fixed_cells=sum(not k[1].startswith('v2-chronological') for k in roster),policy_cells=sum(k[1].startswith('v2-chronological') for k in roster),unrun_cells=len(p['unrun_strict_HGB']))))


def run(a):
    p=json.loads((a.output/'FROZEN_PROTOCOL.json').read_bytes());start=time.monotonic();cpu=time.process_time()
    if sha(__file__)!=p['code_sha256'] or sha(a.root/'tools/aggregate_historical_startup.py')!=p['accumulator_code_sha256']:raise ValueError('frozen adapter/accumulator changed')
    roster={tuple(r['key']):r for r in p['fixed_and_policy_roster']};routes=collections.defaultdict(list)
    for r in p['registered_routes']:routes[r['week'],tuple(r['chosen'])].append(tuple(r['policy']))
    acc=collections.defaultdict(Acc);outcomes={};qids={};games={};players={};policies=collections.defaultdict(set);scanned=used=skipped=0
    def guard():
        if time.monotonic()-start>300 or resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>1073741824:raise RuntimeError('current startup bounded wave')
    for b in p['raw_sources']:
        file=a.private_root/b['member']
        if sha(file)!=b['sha256']:raise ValueError('retained current source changed')
        iterator=packet_rows(file) if b['kind']=='packet' else csv.DictReader(gzip.open(file,'rt'))
        for r in iterator:
            scanned+=1
            if scanned%10000==0:guard()
            norm=normalize(r,b['source_id'],2026)
            if norm is None:skipped+=1;continue
            k,w=norm
            if k not in roster:continue
            point,actual=numeric(r.get('prediction')),numeric(r.get('actual'));fallback=r['fallback']
            if not isinstance(fallback,str) or not fallback:raise ValueError('unknown fallback origin')
            q=(r['game_id'],r['player_id'],r['target'],r['population'],r['position'])
            if q not in qids:qids[q]=len(qids);outcomes[q]=actual
            elif outcomes[q]!=actual:raise ValueError('current labels differ across source recipes')
            if r['game_id'] not in games:games[r['game_id']]=len(games)
            if r['player_id'] not in players:players[r['player_id']]=len(players)
            window='W1_W4_STARTUP' if w<=4 else 'W5_W7_LATER';origin='LEARNED_ONLY' if fallback=='none' else 'FALLBACK_ONLY'
            for dest in[k]+routes[w,k]:
                policies[dest].add(r.get('policy_id') or ('STRICT_CURRENT_INPUTS' if 'strict' in dest[1] else 'REGISTERED_SOURCE_SPECIFIC_POLICY'))
                for part in('FULL_SYSTEM',origin):acc[dest,window,part].add(point,actual,fallback,qids[q],games[r['game_id']],players[r['player_id']],w,k[0],dest[3])
            used+=1
    checked=0
    for k,s in roster.items():
        aa,bb=(acc[k,w,'FULL_SYSTEM'] for w in('W1_W4_STARTUP','W5_W7_LATER'));ref=s['source_record'];n=aa.n+bb.n
        if n!=ref['n'] or aa.issued+bb.issued!=ref['forecast_rows']:raise ValueError('current fullperiod n/issued mismatch:'+str(k))
        for got,metric in((aa.ae+bb.ae,'mae'),(aa.se+bb.se,'mse'),(aa.err+bb.err,'bias')):
            if ref.get(metric) is not None and not math.isclose(got,ref[metric]*n,rel_tol=1e-10,abs_tol=1e-7):raise ValueError('current native loss mismatch:'+metric+str(k))
        checked+=1
    universe=hashlib.sha256(canonical(sorted((code,q,outcomes[q]) for q,code in qids.items()))).hexdigest();scores=[]
    for k,source in sorted(roster.items()):
        target,proc,arm,product=k
        for window,weeks in(('W1_W4_STARTUP',[1,2,3,4]),('W5_W7_LATER',[5,6,7])):
            full,learned,prior=(acc[k,window,v] for v in('FULL_SYSTEM','LEARNED_ONLY','FALLBACK_ONLY'))
            if full.issued!=learned.issued+prior.issued or full.n!=learned.n+prior.n or full.issuedbits!=(learned.issuedbits|prior.issuedbits) or learned.issuedbits&prior.issuedbits:raise ValueError('current origin partitions differ')
            for v in('FULL_SYSTEM','LEARNED_ONLY','FALLBACK_ONLY'):
                z=acc[k,window,v];n=z.n;pre={name:dict(numerator=z.prec[name],denominator=n,rate=z.prec[name]/n if n else None) for name in ['exact_rate']+[f'abs_{op}_{t}' for t in(1,5,10) for op in('lt','le')]};mask=hashlib.sha256(bytes.fromhex(universe)+z.scoredbits.to_bytes((len(qids)+7)//8,'little')).hexdigest();row=dict(record_id='CURRENT-STARTUP-'+hashlib.sha256(canonical([k,window,v])).hexdigest()[:24],record_kind='forecast_evaluation_view',procedure_id=proc,procedure_kind=source['kind'],history_regime=arm,product_id=product,source_policy_ids=sorted(policies[k]),target=target,season=2026,week=window,evaluation_seasons=[2026],evaluation_weeks=weeks,window_id=window,evaluation_panel_id=VERSION,population='primary_retrospective_participant_stat_row',position='ALL',fallback_view=v,forecast_rows=z.issued,available_prediction_rows=z.predicted,missing_prediction_n=z.issued-z.predicted,missing_actual_n=z.missingactual,n=n,mae=z.ae/n if n else None,mse=z.se/n if n else None,rmse=math.sqrt(z.se/n) if n else None,bias=z.err/n if n else None,max_abs=z.maxabs,p90_abs=None,p95_abs=None,tail_quantile_status='NOT_COMPUTED_IN_STARTUP_SUFFICIENT_STAT_SPLIT; exactretainedrowsremainreplayable',precision_counts=pre,fallback_rows=z.fb,fallback_rate=z.fb/z.issued if z.issued else None,scored_fallback_rows=z.scoredfb,scored_fallback_rate=z.scoredfb/n if n else None,fallback_source_counts=dict(z.fallbacks),unique_games=z.gamebits.bit_count(),unique_players=z.playerbits.bit_count(),unique_target_player_game_rows=z.scoredbits.bit_count(),membership_sha256=mask,source_outcome_index_sha256=universe,source_vintage='CURRENT_REVISED_NFL_FOOTBALL;INHERITED_7DAY_AVAILABILITY_RECONSTRUCTION;NOT_ORIGINAL_ISSUANCE',horizon_id='ORIGINAL_REGISTERED_ROLLING_PER_GAME_KICKOFF_RECONSTRUCTION',information_policy=source['information_policy'],origin_partition_scope='Own underlying forecast model learned/fallback; no commonlearned claim. Selector score-memory startup is a separate registered policy state.',fullperiod_source_record=dict(path=GRID,source_test_id=source['source_record'].get('source_test_id'),source_artifact=source['source_record'].get('source_artifact')),evidence='NEW_CURRENT_STARTUP_AGGREGATION_OF_COMPLETED_SAVED_FORECASTS',new_fits=0,new_model_inference=0,new_forecasts=0,new_NFL_observations=0,null_reason=None if n else 'NO_SUPPORTED_ROWS_IN_REGISTERED_WINDOW_ORIGIN_PARTITION')
                if target=='anytime_td':row.update(brier=z.se/n if n else None,log_loss='Infinity' if z.inf else z.logsum/n if n else None,infinite_log_losses=z.inf,probability_target='AT_LEAST_ONE_RUSHING_OR_RECEIVING_TD_EXCLUDES_RETURNS')
                scores.append(row)
    write(a.output/'SCORES.json',scores);csvwrite(a.output/'STARTUP_NUMERICAL_RESULTS.csv',scores);write(a.output/'RUN_RECEIPT.json',dict(state='COMPLETE_FIXED_CURRENT_W1_W7_STARTUP_SAVED_ROW_AGGREGATION',at=now(),protocol_sha256=sha(a.output/'FROZEN_PROTOCOL.json'),score_sha256=sha(a.output/'SCORES.json'),fixed_and_policy_recipe_cells=len(roster),fullperiod_current_native_checks=checked,startup_window_partition_views=len(scores),original_frozen_policy_choices=len(p['registered_routes']),raw_rows_scanned=scanned,primary_fixed_prediction_rows_used=used,distinct_issued_target_player_game_ids=len(qids),unique_games=len(games),private_derivative_bytes=0,new_fits=0,new_model_inference=0,new_forecasts=0,new_NFL_observations=0,Week8_outcomes_read=0,resources=dict(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)))
    print(json.dumps(dict(score_views=len(scores),validated_current_cells=checked,raw_rows=scanned,wall_seconds=time.monotonic()-start)))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=('prepare','run'));p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--private-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();prepare(a) if a.action=='prepare' else run(a)
