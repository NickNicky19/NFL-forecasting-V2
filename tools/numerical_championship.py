"""Bounded retained-row numerical championship; never fits or infers forecasts."""
from __future__ import annotations
import argparse,collections,csv,gzip,hashlib,json,math,resource,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2.shared_subgroups import packet_rows,canonical,sha,now,write
from nfl_v2.scoring import point_metrics
from nfl_v2.precision_grid import chart_median_precision
from nfl_v2.paired_uncertainty import paired_losses
from tools.build_current_valid_view_v2 import recipe as mechanism

VERSION='v2-numerical-championship-retained-row-20261030f-v2'
SEASONS=(2026,2025,2024,2023,2022)
CURRENT='reports/continuation-20261030d/current-ranking-v2/PROCEDURE_RANKINGS.json'
SOURCES={2025:'season-2025-v1',2024:'season-2024-v2',2023:'season-2023-complete-replay-v1',2022:'season-2022-v2'}
CURRENT_RAW=[('empirical','empirical-history-diagnostic-v1/predictions.csv.gz','csv'),
 ('laws','distribution-wave-v2/all-predictions.csv.gz','csv'),('chart','chart-wave-v1/all-chart-predictions.csv.gz','csv'),
 ('count','count-ablation-wave-v1/PREDICTIONS_FLAT.csv.gz','csv'),('c02','ordered-information-ablation-v1/ALL_PREDICTIONS.json.gz','packet'),
 ('defense','qualified-defense-information-v1/ALL_HISTORICAL_PREDICTIONS.json.gz','packet')]
MEANS={'mean','empirical_mean','squared_error_mean','poisson_intended_mean_point'}
VIEWS=('FULL_SYSTEM','COMMON_LEARNED','ANY_FALLBACK')


def dump(path,obj):
    Path(path).write_bytes(canonical(obj))


def csvwrite(path,rows):
    rows=list(rows)
    if not rows:return
    fields=list(dict.fromkeys(k for r in rows for k in r))
    with Path(path).open('x',newline='')as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for r in rows:w.writerow({k:json.dumps(v,separators=(',',':'))if isinstance(v,(list,dict))else v for k,v in r.items()})


def proc_id(value):
    if value=='v2-qualified-partial-chart-direct-wave-v1:empirical':return'empirical-player-history-control-v1'
    return value.removesuffix(':common-feature-memory')


def product_id(value):return'mean'if value=='empirical_mean'else value


def key(spec):return(spec['target'],proc_id(spec['procedure_id']),spec['history_regime'],product_id(spec['product_id']))


def choices_older(root,year):
    paths=[root/'reports/continuation-20261030c'/SOURCES[year]/'SCORES.json']
    if year==2025:paths.append(root/'reports/continuation-20261030c/season-2025-continuity-repair-v1/SCORES.json')
    rows=[]
    for p in paths:
        for i,r in enumerate(json.loads(p.read_bytes())):
            if r.get('population')!='primary'or r.get('week')!='ALL'or r.get('position')!='ALL'or r.get('fallback_view')!='ALL':continue
            if year==2025 and p==paths[0]and'qb-rb-specialization'in r['procedure_id']:continue
            m=mechanism(r)
            if not m:continue
            target=r['target'];point='brier'if target=='anytime_td'else'mae'
            products=[('event_probability',point)]if target=='anytime_td'else[('display_point','mae')]
            if target!='anytime_td'and r['product_id']in MEANS:products.append(('genuine_mean','mse'))
            if target!='anytime_td'and r['product_id']=='lower_median'and r.get('CRPS')is not None:products.append(('forecast_distribution','crps'))
            for purpose,metric in products:
                value=r.get('CRPS'if metric=='crps'else metric)
                if value is None:continue
                rows.append(dict(r,category=target,ranking_product=purpose,ranking_metric=metric,ranking_loss=value,
                    mechanism_id=m[1],family_id=m[0],source_artifact=p.relative_to(root).as_posix(),source_row_index=i))
    return rows


def choose_representatives(rows):
    by=collections.defaultdict(list)
    for r in rows:by[r['target'],r['ranking_product'],r['mechanism_id']].append(r)
    return[min(rr,key=lambda r:(r['ranking_loss'],r['procedure_id'],r['history_regime'],r['product_id']))for rr in by.values()]


def compact(r,year):
    out={k:r.get(k)for k in('procedure_id','history_regime','product_id','mechanism_id','family_id','ranking_product','ranking_metric','ranking_loss','n','forecast_rows','fallback_rows','bias','mae','mse','rmse','p90_abs','p95_abs','max_abs','brier','CRPS','crps','precision_counts','source_artifact')}
    out.update(season=year,target=r.get('target',r.get('category')),population='primary',position='ALL')
    out['forecast_rows']=r.get('forecast_rows',r.get('forecast_or_offered_rows'))
    out['spec_id']='SPEC-'+hashlib.sha256(canonical([year,key(out),out['ranking_product']])).hexdigest()[:20]
    return out


def raw_sources(private,year):
    if year!=2026:
        members=[('season',f'seasonal-rolling-{year}-'+({2025:'v1',2024:'v2',2023:'complete-replay-v1',2022:'v2'}[year])+'/predictions.csv.gz','csv')]
        if year==2025:members.append(('repair','seasonal-rolling-2025-continuity-repair-v1/CORRECTED_PREDICTIONS.csv.gz','csv'))
        return members
    out=list(CURRENT_RAW)
    for f in sorted((private/'hgb-history-v1/prediction-chunks').glob('W0[1-7]-*.json.gz')):
        out.append(('hgb',f.relative_to(private).as_posix(),'packet'))
    return out


def prepare(a):
    if a.output.exists():raise ValueError('fresh immutable output required')
    a.output.mkdir(parents=True)
    current=json.loads((a.root/CURRENT).read_bytes());allrank=[];selected={};pairs=[];bindings=[]
    peryear={2026:[dict(r,target=r['category'])for r in current]}
    for year in SEASONS[1:]:peryear[year]=choose_representatives(choices_older(a.root,year))
    for year,rows in peryear.items():
        groups=collections.defaultdict(list)
        for r in rows:
            c=compact(r,year);allrank.append(c);selected[c['spec_id']]=c;groups[c['target'],c['ranking_product']].append(c)
        for group,rr in groups.items():
            rr.sort(key=lambda r:(r['ranking_loss'],r['mechanism_id']))
            leaders=[r for r in rr if math.isclose(r['ranking_loss'],rr[0]['ranking_loss'],abs_tol=1e-12,rel_tol=0)]
            runner=next((r for r in rr if r not in leaders),None)
            for c in leaders:
                if runner:pairs.append(dict(season=year,target=group[0],ranking_product=group[1],metric=c['ranking_metric'],candidate=c['spec_id'],comparator=runner['spec_id'],purpose='SAME_SEASON_OBSERVED_LEADER_VS_RUNNER',tie_leader_ids=[r['spec_id']for r in leaders]))
            for c in leaders[1:]:pairs.append(dict(season=year,target=group[0],ranking_product=group[1],metric=c['ranking_metric'],candidate=leaders[0]['spec_id'],comparator=c['spec_id'],purpose='TIED_CURRENT_LEADERS',tie_leader_ids=[r['spec_id']for r in leaders]))
    # Fixed current contenders on older seasons, without substituting a missing recipe.
    current_pairs=[r for r in pairs if r['season']==2026 and r['purpose']=='SAME_SEASON_OBSERVED_LEADER_VS_RUNNER']
    gaps=[]
    for year in SEASONS[1:]:
        older=choices_older(a.root,year);lookup={(key(r),r['ranking_product']):r for r in older}
        for pair in current_pairs:
            refs=[]
            for role in('candidate','comparator'):
                src=selected[pair[role]];found=lookup.get((key(src),src['ranking_product']))
                if found:
                    c=compact(found,year);selected[c['spec_id']]=c;refs.append(c['spec_id'])
                else:gaps.append(dict(season=year,target=src['target'],ranking_product=src['ranking_product'],procedure_id=src['procedure_id'],history_regime=src['history_regime'],product_id=src['product_id'],state='FIT_REQUIRED'if'observed-defense'in src['mechanism_id']else'SOURCE_OR_PROCEDURE_NOT_EVALUATED',reason='Exactcurrentrecipehasnoretainedfullprior-seasonforecastcell; no replacement by another mechanism.'))
            if len(refs)==2:pairs.append(dict(pair,season=year,candidate=refs[0],comparator=refs[1],purpose='FIXED_2026_CONTENDERS_ON_PRIOR_SEASON'))
    for i,pair in enumerate(pairs):pair['pair_id']='PAIR-'+hashlib.sha256(canonical([pair])).hexdigest()[:20]
    for year in SEASONS:
        members=[]
        for source_id,member,kind in raw_sources(a.private_root,year):
            f=a.private_root/member
            if not f.exists():raise ValueError('retained member absent '+member)
            members.append(dict(source_id=source_id,member=member,kind=kind,bytes=f.stat().st_size,sha256=sha(f)))
        bindings.append(dict(season=year,members=members))
    p=dict(protocol_id=VERSION,registered_at_utc=now(),code_sha256=sha(__file__),paired_helper_sha256=sha(a.root/'nfl_v2/paired_uncertainty.py'),
        selection='Exposed observed full-primary procedure minima; histories/pointviews collapse per distinctmechanism, raw ranksretained. All tied leaders retained and compared with nextdistinct score. Not earlier selectionpolicy or untouchedvalidation.',
        current_ranking_artifact=CURRENT,current_ranking_sha256=sha(a.root/CURRENT),seasons=list(SEASONS),pairs=pairs,specs=list(selected.values()),sources=bindings,
        periods='2026REGW1-7 fixed; each2022-25fullREGW1-18. 2022RECENT remains available2022proxy; strictcurrentinformation is different fromcurrentfit witholdermemory.',
        comparisons='Samecanonicalgame/player/target/population/position; requireequalactuals; fullsystem/commonbothlearned/anyfallback. Missingactuals neverzero; retainoutercoverage.',
        proper_scores='CRPS is replay ofretained per-row distribution_summary,notnewPMF/lawinference. Properlawqualification/retention remainsoriginalsourcecontract. Offeredthresholdprobabilityskill is separate and NOTestablished here.',
        budget_per_season=dict(max_wall_seconds=180,max_CPU_seconds=240,max_RSS_bytes=1073741824,max_threads=2,max_rows=4000000),new_NFL_fits=0,new_forecasts=0,current2026_Week8_outcomes_read=0)
    write(a.output/'FROZEN_PROTOCOL.json',p);write(a.output/'ALL_VALID_REPRESENTATIVES.json',allrank);csvwrite(a.output/'ALL_VALID_REPRESENTATIVES.csv',allrank);write(a.output/'EXACT_RECIPE_GAPS.json',gaps);csvwrite(a.output/'EXACT_RECIPE_GAPS.csv',gaps)
    return dict(state='SEALED_BEFORE_COMPARATIVE_ROW_REPLAY',pairs=len(pairs),representatives=len(allrank),sources=len(bindings),new_fits=0)


def normalize(raw,source_id,year):
    if int(raw.get('season',year))!=year or raw.get('population')!='primary':return None
    week=int(raw['week'])
    if not 1<=week<=(7 if year==2026 else 18):return None
    p=raw.get('procedure_id')
    if source_id=='empirical':p='empirical-player-history-control-v1'
    if source_id=='hgb':p='hgb-direct-history-controls-v1:'+raw['objective']
    product=raw.get('product_id')or raw.get('product')or raw.get('objective')
    return(raw['target'],proc_id(p),raw['history_regime'],product_id(product)),week


def run(a):
    p=json.loads((a.output/'FROZEN_PROTOCOL.json').read_bytes());start,cpu=time.monotonic(),time.process_time();year=a.season
    if p['code_sha256']!=sha(__file__)or p['paired_helper_sha256']!=sha(a.root/'nfl_v2/paired_uncertainty.py'):raise ValueError('sealed code changed')
    out=a.output/str(year)
    if out.exists():raise ValueError('preserve completed/partial wave; use newversion')
    out.mkdir();pairs=[r for r in p['pairs']if r['season']==year];specs={r['spec_id']:r for r in p['specs']};needed={key(specs[r[role]])for r in pairs for role in('candidate','comparator')}
    points={k:{}for k in needed};rows_read=0;unknown=0
    def guard():
        if time.monotonic()-start>180 or time.process_time()-cpu>240 or resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>1073741824:raise RuntimeError('BOUNDED_NUMERIC_REPLAY_LIMIT')
    source=next(s for s in p['sources']if s['season']==year)
    for binding in source['members']:
        file=a.private_root/binding['member']
        if sha(file)!=binding['sha256']:raise ValueError('retained source changed')
        iterator=packet_rows(file)if binding['kind']=='packet'else csv.DictReader(gzip.open(file,'rt'))
        for raw in iterator:
            rows_read+=1
            if rows_read%10000==0:guard()
            if rows_read>p['budget_per_season']['max_rows']:raise RuntimeError('ROW_BUDGET')
            norm=normalize(raw,binding['source_id'],year)
            if norm is None:continue
            k,week=norm
            if k not in needed:continue
            if year==2025 and binding['source_id']=='season'and'qb-rb-specialization'in k[1]:continue
            q=tuple(raw[x]for x in('game_id','player_id','target','population','position'))
            if q in points[k]:raise ValueError('duplicate exact procedure/query')
            pred=raw.get('prediction');actual=raw.get('actual');pred=None if pred in('',None)else float(pred);actual=None if actual in('',None)else float(actual)
            d=raw.get('distribution_summary')
            if isinstance(d,str):d=json.loads(d)if d else{}
            d=d or{};crps=d.get('crps',raw.get('crps'));crps=None if crps in('',None)else float(crps)
            points[k][q]=(pred,actual,raw['fallback'],week,raw['game_id'],crps)
    scores=[];comparisons=[]
    for pair in pairs:
        ca,cb=specs[pair['candidate']],specs[pair['comparator']];aa,bb=points[key(ca)],points[key(cb)]
        if set(aa)!=set(bb):raise ValueError('leader and runner-up outerquerysets differ')
        supported=[];missing=0
        for q in sorted(aa):
            x,y=aa[q],bb[q]
            if x[1]!=y[1]or x[3]!=y[3]:raise ValueError('leader and comparator label/week mismatch')
            if x[0]is None or y[0]is None or x[1]is None:missing+=1;continue
            if pair['metric']=='crps'and(x[5]is None or y[5]is None):raise ValueError('requested proper loss notretained')
            supported.append((q,x,y))
        for view in VIEWS:
            rr=[v for v in supported if view=='FULL_SYSTEM'or((v[1][2]=='none'and v[2][2]=='none')==(view=='COMMON_LEARNED'))]
            def losses(side):
                return[v[side][5]if pair['metric']=='crps'else(v[side][0]-v[side][1])**2 if pair['metric']in('mse','brier')else abs(v[side][0]-v[side][1])for v in rr]
            la,lb=losses(1),losses(2);u=paired_losses(la,lb,[v[1][3]for v in rr],[v[1][4]for v in rr]);membership=hashlib.sha256(canonical([v[0]for v in rr])).hexdigest()
            comparison=dict(pair,comparison_id=pair['pair_id']+':'+view,fallback_view=view,population='primary',membership_sha256=membership,outer_rows=len(aa),missing_rows=missing,fullsystem_n=len(supported),metric_provenance='retained_per_row_CRPS_replay'if pair['metric']=='crps'else'recomputed_from_retained_point_and_actual',**u)
            comparisons.append(comparison)
            for role,sp,side in [('candidate',ca,1),('comparator',cb,2)]:
                preds=[v[side][0]for v in rr];actuals=[v[side][1]for v in rr];metrics=point_metrics(preds,actuals,sp['target']);n=len(rr)
                if metrics.get('log_loss')==math.inf:metrics['log_loss']='Infinity'
                precision={name:dict(numerator=sum((abs(x-y)==0)if name=='exact_rate'else(abs(x-y)<int(name.rsplit('_',1)[1]))if'_lt_'in name else abs(x-y)<=int(name.rsplit('_',1)[1])for x,y in zip(preds,actuals)),denominator=n,rate=metrics.get(name))for name in('exact_rate','abs_lt_1','abs_le_1','abs_lt_5','abs_le_5','abs_lt_10','abs_le_10')}
                if sp['target']=='nick-chart-ppr-v1'and sp['product_id']=='lower_median':
                    exact=chart_median_precision(preds,actuals,product_id='lower_median');precision.update(exact)
                    for name,value in exact.items():metrics[name]=value['rate']
                rid='NUM-CHAMP-'+hashlib.sha256(canonical([pair['pair_id'],view,role])).hexdigest()[:24]
                row=dict(record_id=rid,record_kind='forecast_evaluation_view',procedure_id=sp['procedure_id'],history_regime=sp['history_regime'],product_id=sp['product_id'],target=sp['target'],population='primary',position='ALL',season=year,week='ALL',period='REG',evaluation_panel_id=VERSION+':'+str(year),evaluation_seasons=[year],evaluation_weeks=sorted({v[1][3]for v in rr}),fallback_view=view,forecast_rows=len(aa)if view=='FULL_SYSTEM'else n,unique_games=len({v[1][4]for v in rr}),fallback_rows=sum(v[side][2]!='none'for v in rr),precision_counts=precision,ranking_product=sp['ranking_product'],comparison_id=comparison['comparison_id'],role=role,membership_sha256=membership,cohort_limit='retrospective current-vintage participant/stat-row panel; not complete exante offer universe',source_vintage='frozen current-vintage reconstruction; assumed seven-day availability; original exposure retained',evidence='REPRODUCED_FROM_DATA',**metrics)
                if pair['metric']=='crps':row['CRPS']=math.fsum(v[side][5]for v in rr)/n if n else None
                scores.append(row)
            if view=='FULL_SYSTEM':
                if len(supported)!=ca['n']or len(supported)!=cb['n']:raise ValueError('retained full row support differs from frozen source ranking')
                if not math.isclose(u['candidate_error'],ca['ranking_loss'],abs_tol=1e-8,rel_tol=1e-10)or not math.isclose(u['comparator_error'],cb['ranking_loss'],abs_tol=1e-8,rel_tol=1e-10):raise ValueError('source numerical ranking not reproduced')
        guard()
    write(out/'SCORES.json',scores);write(out/'PAIRED_COMPARISONS.json',comparisons);csvwrite(out/'PAIRED_COMPARISONS.csv',comparisons)
    receipt=dict(state='COMPLETE_BOUNDED_RETAINED_NUMERIC_COMPARISON',season=year,actual_completed_at=now(),protocol_sha256=sha(a.output/'FROZEN_PROTOCOL.json'),code_sha256=sha(__file__),score_sha256=sha(out/'SCORES.json'),pair_sha256=sha(out/'PAIRED_COMPARISONS.json'),rows_scanned=rows_read,selected_recipe_query_rows=sum(len(v)for v in points.values()),comparison_views=len(comparisons),score_views=len(scores),new_NFL_fits=0,new_forecasts=0,new_NFL_observations=0,current2026_Week8_outcomes_read=0,resources=dict(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,max_threads=2))
    write(out/'RUN_RECEIPT.json',receipt);return receipt


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=('prepare','run'));parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);parser.add_argument('--private-root',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--season',type=int,choices=SEASONS);a=parser.parse_args();print(json.dumps(prepare(a)if a.action=='prepare'else run(a)))
