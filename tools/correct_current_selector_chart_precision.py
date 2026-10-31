"""Only the 18 current chart-policy window/origin precision scoring revisions."""
import argparse,collections,csv,gzip,hashlib,json,math,resource,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2.shared_subgroups import canonical,sha,now,write
from nfl_v2.precision_grid import coordinate
from tools.numerical_championship import normalize,csvwrite

KIND='PRECISION_ONLY_NO_FORECAST_OR_NATIVE_LOSS_CHANGE'

def prepare(a):
    if a.output.exists():raise ValueError('fresh precision correction identity required')
    a.output.mkdir(parents=True);parent=json.loads((a.parent/'FROZEN_PROTOCOL.json').read_bytes());scores=json.loads((a.parent/'SCORES.json').read_bytes());affected=[dict(source_row_index=i,record_id=r['record_id']) for i,r in enumerate(scores) if r['target']=='nick-chart-ppr-v1' and r['procedure_id'].startswith('v2-chronological-category-score-memory-selector')]
    if len(affected)!=18:raise ValueError('exactly18affectedscoringviews expected')
    sources=[r for r in parent['raw_sources'] if r['source_id']=='chart']
    if len(sources)!=1:raise ValueError('one original qualified chart source required')
    for r in sources:
        if sha(a.private_root/r['member'])!=r['sha256']:raise ValueError('retained chart source changed')
    p=dict(version='v2-current-startup-chart-selector-precision-v3',state='FROZEN_BEFORE_NARROW_PRECISION_REPLAY',at=now(),code_sha256=sha(__file__),precision_helper_sha256=sha(a.root/'nfl_v2/precision_grid.py'),parent_source=(a.parent/'SCORES.json').relative_to(a.root).as_posix(),parent_score_sha256=sha(a.parent/'SCORES.json'),parent_protocol_sha256=sha(a.parent/'FROZEN_PROTOCOL.json'),affected_rows=affected,chart_sources=sources,registered_chart_routes=[r for r in parent['registered_routes'] if r['chosen'][0]=='nick-chart-ppr-v1'],reference_grid_path=parent['current_grid_path'],reference_grid_sha256=parent['current_grid_sha256'],correction_kind=KIND,rule='Use underlying selected fixed recipe product: lower_median uses exact0.02coordinate errors; mean/continuous points retain original unrounded float semantics. Destinationpolicy product remains unchanged. Recompute precision counts only; copy every existing point/loss/history/choice/sample field unchanged.',unchanged='No forecasts,labels,selections,model fits,inference,MAE,MSE,bias,n or other startupscores changed.18newscoringversions are not18newmethods/backtests.',budget=dict(wall_seconds=300,max_RSS_bytes=1073741824,max_native_threads=1,max_private_bytes=0))
    write(a.output/'FROZEN_PROTOCOL.json',p);(a.output/'SOURCE_SNAPSHOT.py').write_bytes(Path(__file__).read_bytes());print(json.dumps(dict(protocol_sha256=sha(a.output/'FROZEN_PROTOCOL.json'),affected_views=18)))

def run(a):
    p=json.loads((a.output/'FROZEN_PROTOCOL.json').read_bytes());start=time.monotonic();cpu=time.process_time()
    if sha(__file__)!=p['code_sha256'] or sha(a.parent/'SCORES.json')!=p['parent_score_sha256']:raise ValueError('frozen correction source changed')
    old=json.loads((a.parent/'SCORES.json').read_bytes());routes=collections.defaultdict(list)
    for r in p['registered_chart_routes']:routes[r['week'],tuple(r['chosen'])].append(tuple(r['policy']))
    counters=collections.defaultdict(collections.Counter);counts=collections.Counter();seen=set();scanned=matched=0;types=collections.Counter()
    for source in p['chart_sources']:
        file=a.private_root/source['member']
        if sha(file)!=source['sha256']:raise ValueError('chart source changed')
        with gzip.open(file,'rt') as f:
            for r in csv.DictReader(f):
                scanned+=1;norm=normalize(r,'chart',2026)
                if norm is None:continue
                key,week=norm;policies=routes.get((week,key),[])
                if not policies or r.get('prediction') in(None,'') or r.get('actual') in(None,''):continue
                pred,actual=float(r['prediction']),float(r['actual']);window='W1_W4_STARTUP' if week<=4 else 'W5_W7_LATER';origin='LEARNED_ONLY' if r['fallback']=='none' else 'FALLBACK_ONLY';grid=key[3]=='lower_median';error=abs(coordinate(pred)-coordinate(actual)) if grid else abs(pred-actual);scale=50 if grid else 1
                for policy in policies:
                    identity=(policy,r['game_id'],r['player_id'])
                    if identity in seen:raise ValueError('duplicate selected policy/query')
                    seen.add(identity);matched+=1;types['GRID_MEDIAN' if grid else 'UNROUNDED_OTHER_PRODUCT']+=1
                    for view in('FULL_SYSTEM',origin):
                        g=(policy,window,view);counts[g]+=1;counters[g]['exact_rate']+=pred==actual
                        for t in(1,5,10):counters[g][f'abs_lt_{t}']+=error<scale*t;counters[g][f'abs_le_{t}']+=error<=scale*t
                if time.monotonic()-start>300 or resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>1073741824:raise RuntimeError('precision-only bounded replay')
    corrected=[];replacement=[];changed=[]
    for binding in p['affected_rows']:
        original=old[binding['source_row_index']]
        if original['record_id']!=binding['record_id']:raise ValueError('bound record identity changed')
        policy=(original['target'],original['procedure_id'],original['history_regime'],original['product_id']);g=(policy,original['window_id'],original['fallback_view']);n=counts[g]
        if n!=original['n']:raise ValueError('precision supported mask differs from original source')
        precise={name:dict(numerator=counters[g][name],denominator=n,rate=counters[g][name]/n if n else None) for name in ['exact_rate']+[f'abs_{op}_{t}' for t in(1,5,10) for op in('lt','le')]};r=dict(original);r.update(record_id='CURRENT-STARTUP-PRECISION-V3-'+hashlib.sha256(canonical([original['record_id'],p['version']])).hexdigest()[:24],scoring_version=p['version'],correction_kind=KIND,replaces_source_record_id=original['record_id'],replaces_source_artifact=p['parent_source'],replaces_source_sha256=p['parent_score_sha256'],precision_counts=precise,precision_functional_rule='Actual underlying selected lower_median uses exact chartgrid; chosen mean/continuous points unrounded')
        for name,values in precise.items():r[name]=values['rate']
        for field in('mae','mse','bias','n','prediction','history_regime','product_id','forecast_rows','fallback_rows'):
            if r.get(field)!=original.get(field):raise ValueError('precision correction changed native loss or forecast metadata')
        if precise!=original['precision_counts']:changed.append(original['record_id'])
        replacement.append(dict(old_source_row_index=binding['source_row_index'],old_record_id=original['record_id'],new_source_row_index=len(corrected),new_record_id=r['record_id']));corrected.append(r)
    # Whole-period precision must reproduce the retained corrected selector reference.
    grid=json.loads((a.root/p['reference_grid_path']).read_bytes());checks=[]
    for proc in sorted({r['procedure_id'] for r in corrected}):
        refs=next(r for r in grid if r['target']=='nick-chart-ppr-v1' and r['procedure_id']==proc and r['state']=='COMPLETED_VALID');full=[r for r in corrected if r['procedure_id']==proc and r['fallback_view']=='FULL_SYSTEM']
        for name,values in refs['precision_counts'].items():
            total=sum(r['precision_counts'][name]['numerator'] for r in full)
            if total!=values['numerator']:raise ValueError('corrected wholeperiod precision differs from original exact selector:'+name)
            checks.append(dict(procedure_id=proc,precision_metric=name,numerator=total,reference_numerator=values['numerator']))
    write(a.output/'SCORES.json',corrected);csvwrite(a.output/'CORRECTED_POLICY_PRECISION.csv',corrected)
    write(a.output/'SOURCE_BOUND_SCORING_REPLACEMENTS.json',dict(schema='v2-source-bound-scoring-version-replacement-v1',old_source_artifact=p['parent_source'],old_source_sha256=p['parent_score_sha256'],new_source_artifact=(a.output/'SCORES.json').relative_to(a.root).as_posix(),new_source_sha256=sha(a.output/'SCORES.json'),replacements=replacement,default_action='REPLACE_ONLY18MATCHED_OLD_SCORING_RECORDS; retain alloldrowsinaudit',correction_kind=KIND,predictions_and_native_losses_unchanged=True))
    write(a.output/'RUN_RECEIPT.json',dict(state='COMPLETE_NARROW_CURRENT_CHART_POLICY_PRECISION_CORRECTION',at=now(),protocol_sha256=sha(a.output/'FROZEN_PROTOCOL.json'),score_sha256=sha(a.output/'SCORES.json'),new_scoring_versions=len(corrected),rows_with_actual_precision_count_change=len(changed),changed_original_record_ids=changed,fullperiod_reference_checks=checks,raw_chart_rows_scanned=scanned,selected_policy_query_rows=matched,underlying_products=dict(types),new_fits=0,new_model_inference=0,new_forecasts=0,new_native_loss_evaluations=0,new_private_bytes=0,resources=dict(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)))
    print(json.dumps(dict(scoring_versions=len(corrected),changed_precision_rows=len(changed),fullperiod_checks=len(checks),wall_seconds=time.monotonic()-start)))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=('prepare','run'));p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--parent',type=Path,required=True);p.add_argument('--private-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.parent=a.parent.resolve();a.output=a.output.resolve();prepare(a) if a.action=='prepare' else run(a)
