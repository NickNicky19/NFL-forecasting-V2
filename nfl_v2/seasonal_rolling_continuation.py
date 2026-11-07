"""Finite season-relative rolling evaluation of existing V2 procedures.

No acquisition, future capture, 2026 refit, or target seasons after evaluation
are decoded. Streaming private CSVs retain forecasts, labels and law summaries.
"""
from __future__ import annotations
from array import array
import collections,csv,gzip,hashlib,io,json,math,os,pickle,platform,re,resource,time,warnings
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import sklearn
from threadpoolctl import threadpool_limits
from . import hgb_control as source, empirical_benchmark as emp,chart_sources,chart_wave as chart
from . import distribution_wave_v2 as laws, ordered_information_ablation as c02,count_ablations as count
from .distribution_laws import prior

VERSION='v2-existing-learners-season-2023-w17-w18-continuation-v1'
TARGETS=source.TARGETS+(chart.TARGET,)
METHODS=('leaf','glm_law','c02','hgb_L1','hgb_L2','hgb_TD','hgb_poisson','hgb_carry_primary')
canonical=source.canonical;sha=source.sha;now=source.now;write=source.immutable_json
FIELDS=('run_id','query_id','game_id','player_id','target','population','position','season','week','history_regime','policy_id','information_policy','family','procedure_id','product_id','prediction','actual','actual_grid','actual_status','fallback','fallback_source','fallback_source_n','status','fit_slot','fit_state','model_artifact_id','latest_training_label_available','latest_training_feature_available','latest_feature_available','feature_cutoff','fit_cutoff','actual_generated_at','distribution_summary','law_reference')

def policies(year):
    return {'H-CURRENT-COMMON':('H-CURRENT',year,2022),'H-RECENT-COMMON':('H-RECENT',max(2022,year-1),2022),'H-MULTI-COMMON':('H-MULTI',2022,2022),'H-CURRENT-STRICT':('H-CURRENT',year,year)}
def methods(target):
    out=['leaf','glm_law','c02']
    if target!=chart.TARGET:out+=['hgb_TD'] if target=='anytime_td' else ['hgb_L1','hgb_L2']
    if target in count.COUNT_TARGETS:out.append('hgb_poisson')
    if target=='rush_att':out.append('hgb_carry_primary')
    return out
def products(method,target):
    if method in ('leaf','glm_law','c02'):return ('event_probability',) if target=='anytime_td' else ('mean','lower_median')
    return ('log_loss_probability',) if method=='hgb_TD' else ('absolute_error_point',) if method=='hgb_L1' else ('squared_error_mean',) if method=='hgb_L2' else ('poisson_intended_mean_point',) if method=='hgb_poisson' else ('absolute_loss_point',)
def procedure(method,target,strict):
    suffix=':strict-current-inputs' if strict else ':common-feature-memory'
    if method in ('leaf','glm_law'):
        stem=chart.VERSION if target==chart.TARGET else laws.VERSION;family='ordered_leaf_cdf' if method=='leaf' else 'regularized_glm_law';return stem+':'+family+suffix,family
    if method=='c02':return c02.VERSION+suffix,'ordered_leaf_cdf'
    if method in ('hgb_L1','hgb_L2','hgb_TD'):return 'hgb-direct-history-controls-v1:'+products(method,target)[0]+suffix,'HGB_DIRECT_HISTORY_CONTROL'
    if method=='hgb_poisson':return count.POISSON+(':strict-current-feature-memory' if strict else ':common-feature-memory'),'hgb-poisson-objective-count-point'
    return count.RA+(':strict-current-feature-memory' if strict else ':common-feature-memory'),'hgb-rush-att-role-specialization'
def logical_policy_key(year,policy):return policies(year)[policy][1:]
def alias_policy(year,policy):
    k=logical_policy_key(year,policy)
    return next(p for p in policies(year) if logical_policy_key(year,p)==k)
def lower_median(values):
    s=sorted(values);return s[(len(s)-1)//2] if s else None
def fallback_sample_rows(rows,target,floor,method):
    return [r for r in rows if r['season']>=floor and r['values'][target] is not None and (method!='hgb_carry_primary' or r['position'] in ('QB','RB'))]
def all_zero_count_skip(method,target,y):
    return method in ('leaf','glm_law','c02','hgb_poisson') and target in emp.COUNTS and bool(np.all(np.asarray(y)==0))

class CheckedStream:
    """Reject compressed bytes before writing beyond the cumulative private cap."""
    def __init__(self,raw,remaining):self.raw=raw;self.remaining=remaining
    def write(self,data):
        if self.raw.tell()+len(data)>self.remaining():raise RuntimeError('STREAM_PRIVATE_BUDGET_BEFORE_WRITE')
        return self.raw.write(data)
    def __getattr__(self,name):return getattr(self.raw,name)

class Meter:
    def __init__(self):
        self.errors=array('d');self.actuals=array('d');self.forecasts=0;self.fallbacks=collections.Counter();self.games=set();self.querygames=set();self.weeks=set();self.precision=collections.Counter();self.crps=0.;self.nll=0.;self.infinite=0;self.width=0.;self.covered=0;self.zero=0.;self.law_n=0;self.logloss=0.;self.log_infinite=0
    def add(self,r):
        self.forecasts+=1;self.fallbacks[r['fallback']]+=1;self.querygames.add(r['game_id'])
        y=r['actual'];p=r['prediction']
        if y is None:return
        self.errors.append(p-y);self.games.add(r['game_id']);self.weeks.add(r['week']);a=abs(p-y)
        if r['target']==chart.TARGET and r['product_id']=='lower_median':
            # Predictions/labels are retained integer law coordinates, not rounded means.
            pg=p*50
            if not math.isclose(pg,round(pg),abs_tol=1e-7):raise ValueError('nongrid chart median')
            a=abs(int(round(pg))-int(r['actual_grid']));unit=50
        else:unit=1
        for t in (1,5,10):
            self.precision['abs_lt_'+str(t)]+=a<t*unit;self.precision['abs_le_'+str(t)]+=a<=t*unit
        self.precision['exact_rate']+=a==0
        if r['target']=='anytime_td':
            self.actuals.append(y);mass=p if y else 1-p
            if mass<=0:self.log_infinite+=1
            else:self.logloss-=math.log(mass)
        d=r.get('distribution_summary')
        if d:
            self.law_n+=1;self.crps+=d['crps'];self.width+=d['interval90_width'];self.covered+=d['interval90_covered'];self.zero+=d['zero_mass'];self.infinite+=d['infinite_nll']
            if not d['infinite_nll']:self.nll+=d['nll']
    def result(self):
        n=len(self.errors);out=dict(n=n,scored_n=n,forecast_rows=self.forecasts,missing_actual_n=self.forecasts-n,fallback_rows=self.forecasts-self.fallbacks['none'],fallback_source_counts=dict(self.fallbacks),unique_games=len(self.games),forecast_games=len(self.querygames),evaluation_weeks=sorted(self.weeks),mae=None,mse=None,rmse=None,bias=None)
        if n:
            absolute=sorted(map(abs,self.errors));q=lambda p:float(np.quantile(absolute,p,method='linear'));mse=math.fsum(e*e for e in self.errors)/n
            out.update(mae=math.fsum(absolute)/n,mse=mse,rmse=math.sqrt(mse),bias=math.fsum(self.errors)/n,p90_abs=q(.9),p95_abs=q(.95),max_abs=absolute[-1],precision_counts={k:dict(numerator=v,denominator=n,rate=v/n) for k,v in self.precision.items()},**{k:v/n for k,v in self.precision.items()})
            if self.actuals:out.update(brier=mse,prevalence=math.fsum(self.actuals)/n,log_loss='Infinity' if self.log_infinite else self.logloss/n,infinite_log_losses=self.log_infinite)
        if self.law_n:out.update(CRPS=self.crps/self.law_n,NLL='Infinity' if self.infinite else self.nll/self.law_n,infinite_NLL=self.infinite,interval90_width=self.width/self.law_n,interval90_coverage=self.covered/self.law_n,mean_zero_mass=self.zero/self.law_n)
        return out

def load_source(root,protocol):
    root=Path(root);year=protocol['evaluation_season'];games=source.schedules(root/'games.csv');needed=set(emp.MAP.values())|set(emp.PHYSICAL_COUNTS)|set(emp.PHYSICAL_YARDS)|{'rushing_tds','receiving_tds'};finality={}
    with (root/'games.csv').open() as f:
        for r in csv.DictReader(f):
            if r['game_type']!='REG' or not 2022<=int(r['season'])<=year:continue
            hs,aws,result,total=(emp.numeric(r[k]) for k in ('home_score','away_score','result','total'))
            finality[r['game_id']]=bool(emp.valid_count(hs) and emp.valid_count(aws) and result==hs-aws and total==hs+aws)
    rows=[];seen=set();counts=collections.Counter()
    for season in range(2022,year+1):
        with (root/f'stats_player_week_{season}.csv').open() as f:
            for raw in csv.DictReader(f):
                counts['source_rows']+=1
                if counts['source_rows']>protocol['budget']['max_source_rows']:raise ValueError('source row budget')
                if raw['season_type']!='REG' or raw['season']!=str(season) or raw['position'] not in source.POSITIONS or not re.fullmatch(r'00-\d{7}',raw['player_id']):continue
                game=games.get(raw['game_id']);key=(raw['game_id'],raw['player_id'])
                if not game or game['season']!=season or game['week']!=int(raw['week']) or key in seen:raise ValueError('history identity/calendar binding')
                if (raw['team'],raw['opponent_team']) not in ((game['home'],game['away']),(game['away'],game['home'])):raise ValueError('history team binding')
                seen.add(key);v={k:emp.numeric(raw[k]) for k in needed};played=any(emp.valid_count(v[k]) and v[k]>0 for k in emp.PHYSICAL_COUNTS) or any(v[k] is not None and v[k]!=0 for k in emp.PHYSICAL_YARDS)
                label=chart_sources.chart_label(raw,source_sha256=chart_sources.CSV_SHA256_BY_SEASON[season],appearance_verified=bool(played),game_completed_verified=finality.get(raw['game_id'],False));values={t:emp.target_value(t,v) if played else None for t in source.TARGETS};values[chart.TARGET]=label['points_times_50'];counts[label['status']]+=1
                rows.append(dict(season=season,week=int(raw['week']),game_id=raw['game_id'],player_id=raw['player_id'],position=raw['position'],kickoff=game['kickoff'],available=game['kickoff']+7*86400,played=played,values=values,chart_status=label['status']))
    return rows,games,dict(counts)

def prepare(*,year,source_root,base_protocol,empirical_predictions,empirical_chart_predictions,chart_queries,public,private):
    if year not in (2022,2023,2024,2025):raise ValueError('older season only')
    public,private=Path(public),Path(private)
    if public.exists() or private.exists():raise ValueError('fresh immutable wave required')
    old=json.loads(Path(base_protocol).read_text())
    for item in old['source_ids']:
        if sha(Path(source_root)/item['name'])!=item['sha256']:raise ValueError('source hash')
    public.mkdir(parents=True);private.mkdir(parents=True);queries=[]
    with gzip.open(empirical_predictions,'rt') as f:
        for r in csv.DictReader(f):
            if r['season']==str(year) and r['history_regime']=='H-CURRENT' and r['product'] in ('empirical_mean','event_probability'):
                q={k:r[k] for k in ('game_id','player_id','target','population','position')};q.update(season=year,week=int(r['week']));queries.append(q)
    for q in json.loads(Path(chart_queries).read_text())['historical']:
        if q['season']==year:queries.append(dict(q))
    keys=[tuple(q[k] for k in ('game_id','player_id','target','population')) for q in queries]
    if len(keys)!=len(set(keys)):raise ValueError('duplicate query membership')
    for q in queries:q['query_id']=hashlib.sha256(canonical(q)).hexdigest()
    write(private/'frozen-queries.json',queries);weeks=sorted({q['week'] for q in queries});unique_policies=sorted(set(alias_policy(year,p) for p in policies(year)));opps=len(weeks)*len(unique_policies)*sum(len(methods(t)) for t in TARGETS);views=sum(sum(len(products(m,q['target'])) for m in methods(q['target'])) for q in queries)*len(policies(year));empviews=sum((1 if q['target']=='anytime_td' else 2) for q in queries)*3
    p=dict(version=VERSION,run_id=VERSION+':'+str(year),state='FROZEN_BEFORE_SEASON_NUMERIC_FEATURES_OR_FITS',registered_at_utc=now(),evaluation_season=year,evaluation_weeks=weeks,code_sha256=sha(__file__),helpers={Path(m.__file__).name:sha(m.__file__) for m in (source,emp,chart_sources,chart,laws,c02,count)},law_code_sha256=sha(Path(__file__).with_name('distribution_laws.py')),source_ids=old['source_ids'],source_role_contract=old['source_role_contract'],query_sources=dict(empirical_prediction_sha256=sha(empirical_predictions),empirical_chart_prediction_sha256=sha(empirical_chart_predictions),chart_query_sha256=sha(chart_queries)),frozen_queries_sha256=sha(private/'frozen-queries.json'),query_cells=len(queries),query_games=len({q['game_id'] for q in queries}),targets=list(TARGETS),policies={k:dict(history_regime=v[0],fit_floor=v[1],feature_floor=v[2],model_alias_of=alias_policy(year,k)) for k,v in policies(year).items()},nominal_fit_opportunities=len(weeks)*len(policies(year))*sum(len(methods(t)) for t in TARGETS),unique_fit_opportunities=opps,method_cells=[dict(target=t,method=m,products=list(products(m,t))) for t in TARGETS for m in methods(t)],not_applicable=[dict(target=chart.TARGET,method=m,reason='NoexistingchartHGBrecipe/futureadapter; not silentlyinvented forolder-seasonreplay') for m in ('hgb_L1','hgb_L2','hgb_poisson','hgb_carry_primary','hgb_TD')],feature_contract='own mean3/n3/mean8/n8,last4targetvalue/age/missing,positiononehot; C02drop12explicitlagcolumns+imputerflags; no team/defense/injury/market/NGS/weather/currentroster',chronology='onefitbeforeearliestREGgameeachweek; labels kickoff+7days STRICTLYearlierthanweeklyorigin; trainfeatures ownkickoff; queryfeatures ownkickoff; no sourceyears afterevaluationyear decoded; no pre2022training',history='CURRENT=evalyear; RECENT=max2022,evalyear-1; MULTI=2022 expanding; sharedfeaturememory2022; strictfit/features/priors/transformsstart evalyear; architecturepreviouslyselected/exposed',cold_start='fullsystem includes declaredsamearmempirical own/position then0 forpointmodels; exactsamearmrole/globallawprior forlawmodels; zeroownfeaturehistory triggerslawroleprior; noNFLlabels=>numericpointmass0/TDfixed.5law; allzero-count/singleclass flags retained',forest=laws.FOREST,glm=laws.GLM,hgb=source.PARAMS,minimum_training_rows=dict(leaf=60,glm_law=40,c02=60,hgb=40),law_contract='inheritedexactdiscretePMF/CDF/quantiles/CRPS;95/5leaf/roleprior; GLMPoisson/binary/signed-discreteLaplace explicituncalibratedassumptions; trueinfinityretained, neverPoissonobjectiveaslaw',chart='samequalified16components andprovidercompletezero rules; integerpoints*50; signedlaw; points/CRPS/widthdivide50; PMFmassunchanged; exactmedianprecisionintegercoordinate; missingrarelabels retained',empirical='replay previoussamequeryrolling empiricalmean/lowermedian/TDprobability where retained,0optimizerfits; exactsource/labelbindings checked; STRICT aliasCURRENT notnewlearner',scoring='numericMAEallcompatiblepoints, intendedmeansMSE/RMSEseparate;TDprimaryBrier/logloss; lawCRPS/PMFNLL/interval90/zero; nativeprecisionstrict/inclusive1/5/10; primary/extended+week+positions+learnedonly',cohort='retrospective observedstatisticalrow/physicalproof, historicalrowpositions, missingactualsretained; not fullhistoricalexanteofferedpopulation; nofutureselection',previous_exposure='Currentvintagepreviouslyexposedresearch; olderseasonrobustness, not untouchedconfirmation or answeralone to2026historyquestion',budget=dict(max_fit_calls=opps,wall_seconds=2400,cpu_seconds=3600,max_threads=2,max_peak_memory_bytes=2147483648,max_private_bytes=1073741824,max_source_rows=200000,max_forecast_rows=views+empviews,max_model_bytes_preflight=734003200,hyperparameter_searches=0),expected_learned_output_views=views,expected_empirical_output_views=empviews,unique_policy_fits=len(unique_policies),new_family_count=0,future_forecasts=0,Week8_outcomes_read=0,actual2026_refits=0)
    write(public/'FROZEN_PROTOCOL.json',p);return p

def run(*,source_root,public,private,empirical_predictions,empirical_chart_predictions,verifier_receipt):
    public,private=Path(public),Path(private);p=json.loads((public/'FROZEN_PROTOCOL.json').read_text());year=p['evaluation_season'];start,cpu=time.monotonic(),time.process_time();verify=json.loads(Path(verifier_receipt).read_text())
    if verify.get('state')!='PASS_SEASONAL_CONTINUATION_PREFIT_REVIEW' or verify.get('code_sha256')!=sha(__file__) or verify.get('protocol_sha256_by_season',{}).get(str(year))!=sha(public/'FROZEN_PROTOCOL.json') or year not in (2022,2023,2024,2025):raise ValueError('independent season-bound prefit review required')
    if sha(__file__)!=p['code_sha256'] or sha(private/'frozen-queries.json')!=p['frozen_queries_sha256']:raise ValueError('frozen binding')
    for name,h in p['helpers'].items():
        if sha(Path(__file__).with_name(name))!=h:raise ValueError('helper changed')
    if sha(Path(__file__).with_name('distribution_laws.py'))!=p['law_code_sha256']:raise ValueError('law helper changed')
    for item in p['source_ids']:
        if sha(Path(source_root)/item['name'])!=item['sha256']:raise ValueError('source changed')
    if sha(empirical_predictions)!=p['query_sources']['empirical_prediction_sha256'] or sha(empirical_chart_predictions)!=p['query_sources']['empirical_chart_prediction_sha256']:raise ValueError('retained empirical bytes changed')
    if json.loads((public/'SOFTWARE_CHECKS.json').read_text())['code_sha256']!=sha(__file__):raise ValueError('software tests binding')
    write(public/'EXECUTION_REGISTRATION.json',dict(actual_started_at=now(),protocol_sha256=sha(public/'FROZEN_PROTOCOL.json'),independent_prefit_review_sha256=sha(verifier_receipt),new_fit_calls=0,sole_fit_worker=True,environment=dict(python=platform.python_version(),numpy=np.__version__,sklearn=sklearn.__version__)))
    rows,games,sourcecounts=load_source(source_root,p);lookup={(r['game_id'],r['player_id']):r for r in rows};queries=json.loads((private/'frozen-queries.json').read_text());byweek=collections.defaultdict(list)
    for q in queries:
        r=lookup[q['game_id'],q['player_id']];v=r['values'][q['target']];byweek[q['week']].append(dict(q,cutoff=r['kickoff'],actual_grid=v if q['target']==chart.TARGET else None,actual=v/50 if q['target']==chart.TARGET and v is not None else v,actual_status=r['chart_status'] if q['target']==chart.TARGET else 'SUPPORTED_OFFICIAL_PHYSICAL_STAT' if v is not None else 'PARTICIPATION_OR_LABEL_UNKNOWN'))
    histories={floor:source.FeatureHistory([r for r in rows if r['season']>=floor]) for floor in (2022,year)};datasets={}
    for t in TARGETS:
        roles=set(source.POSITIONS) if t==chart.TARGET else source.allowed_roles(p,t)
        for memory in histories:
            rs=[r for r in rows if r['season']>=memory and r['position'] in roles and r['values'][t] is not None];x=[];mx=[]
            for r in rs:
                f,m=histories[memory].get(r['player_id'],r['position'],t,r['kickoff']);x.append(f);mx.append(m)
                if m is not None and m>=r['kickoff']:raise ValueError('train feature leakage')
            datasets[t,memory]=(rs,np.asarray(x),np.asarray([r['values'][t] for r in rs]),mx)
    for d in ('models','query-features','predictions','training-memberships'):(private/d).mkdir(exist_ok=True)
    private_bytes=sum(f.stat().st_size for f in private.rglob('*') if f.is_file());model_bytes=0;fitcalls=retained=failcount=aliases=output_count=0;grids=[];failures=[];meters=collections.defaultdict(Meter);terminal='COMPLETE';fit_cache={};priors_cache={};fallback_cache={};completed_weeks=[];active_raw=None;active_text=None
    def guard():
        if time.monotonic()-start>p['budget']['wall_seconds'] or time.process_time()-cpu>p['budget']['cpu_seconds']:raise RuntimeError('TIME_BUDGET')
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>p['budget']['max_peak_memory_bytes']:raise RuntimeError('RSS_BUDGET')
        if private_bytes+(active_raw.tell() if active_raw is not None and not active_raw.closed else 0)>p['budget']['max_private_bytes']-8388608:raise RuntimeError('PRIVATE_BUDGET')
    def save(path,obj,raw=False):
        nonlocal private_bytes,model_bytes
        blob=gzip.compress(obj if raw else canonical(obj),mtime=0)
        active_bytes=active_raw.tell() if active_raw is not None and not active_raw.closed else 0
        if private_bytes+active_bytes+len(blob)>p['budget']['max_private_bytes']-8388608:raise RuntimeError('PRIVATE_BUDGET_BEFORE_WRITE')
        if raw and model_bytes+len(blob)>p['budget']['max_model_bytes_preflight']:raise RuntimeError('MODEL_BYTE_BUDGET_BEFORE_WRITE')
        with path.open('xb') as f:f.write(blob);f.flush();os.fsync(f.fileno())
        private_bytes+=len(blob)
        if raw:model_bytes+=len(blob)
        return dict(artifact_id='OLDER-SEASON-'+sha(path),bundle_name=path.relative_to(private).as_posix(),sha256=sha(path),bytes=len(blob))
    def add(r,writer):
        nonlocal output_count
        if output_count>=p['budget']['max_forecast_rows']:raise RuntimeError('FORECAST_BUDGET')
        serialized=dict(r,distribution_summary='' if not r.get('distribution_summary') else json.dumps(r['distribution_summary'],sort_keys=True,separators=(',',':')),law_reference='' if not r.get('law_reference') else json.dumps(r['law_reference'],sort_keys=True,separators=(',',':')));writer.writerow(serialized);output_count+=1
        if output_count%1000==0:
            if active_text is not None:active_text.flush()
            guard()
        dims=(r['procedure_id'],r['family'],r['target'],r['policy_id'],r['history_regime'],r['product_id'],r['population'])
        for week,pos,view in [('ALL','ALL','ALL'),(str(r['week']),'ALL','ALL'),('ALL',r['position'],'ALL')]+([('ALL','ALL','LEARNED_ONLY')] if r['fallback']=='none' else []):meters[dims+(week,pos,view)].add(r)
    def fallback_summary(t,policy,q,method):
        _,floor,_=policies(year)[policy];key=(t,floor,'QB_RB_ONLY' if method=='hgb_carry_primary' else 'ALL_APPLICABLE_ROLES')
        if key not in fallback_cache:
            groups=collections.defaultdict(list)
            for r in fallback_sample_rows(rows,t,floor,method):
                item=(r['available'],(r['game_id'],r['player_id']),r['values'][t]);groups[r['position'],r['player_id']].append(item);groups[r['position'],None].append(item)
            fallback_cache[key]={k:emp.Series(v) for k,v in groups.items()}
        groups=fallback_cache[key];own=groups.get((q['position'],q['player_id']));s=own.at(q['cutoff']) if own else (0,None,None,None);fb='own_empirical'
        if not s[0]:pool=groups.get((q['position'],None));s=pool.at(q['cutoff']) if pool else (0,None,None,None);fb='position_empirical' if s[0] else 'constant_zero'
        return s,fb
    labels=save(private/'QUALIFIED_QUERY_LABELS.json.gz',[dict(q) for w in sorted(byweek) for q in byweek[w]])
    with threadpool_limits(limits=2):
      try:
        for week in p['evaluation_weeks']:
          guard();fit_cache.clear();priors_cache.clear();origin=min(g['kickoff'] for g in games.values() if g['season']==year and g['week']==week);path=private/'predictions'/f'W{week:02}.csv.gz';before=output_count
          with path.open('xb') as raw:
           with gzip.GzipFile(fileobj=CheckedStream(raw,lambda:p['budget']['max_private_bytes']-private_bytes),mode='wb',mtime=0) as handle:
            text=io.TextIOWrapper(handle,encoding='utf-8',newline='');active_text=text;active_raw=raw;writer=csv.DictWriter(text,fieldnames=FIELDS,extrasaction='ignore');writer.writeheader()
            for target in TARGETS:
             qr=[q for q in byweek[week] if q['target']==target]
             for policy,(arm,floor,memory) in policies(year).items():
              guard();rs,tx,ty,tm=datasets[target,memory];fullq=[];qm=[]
              for q in qr:
                  f,m=histories[memory].get(q['player_id'],q['position'],target,q['cutoff']);fullq.append(f);qm.append(m)
                  if m is not None and m>=q['cutoff']:raise ValueError('query feature leakage')
              qx=np.asarray(fullq);featurepacket=save(private/'query-features'/f'W{week:02}-{target}-{policy}.json.gz',[dict(query_id=q['query_id'],features=source.json_features(f),latest_feature_available=m) for q,f,m in zip(qr,fullq,qm)])
              for method in methods(target):
               guard();slot=f'W{week:02}-{target}-{policy}-{method}';cachekey=(target,floor,memory,method);isalias=cachekey in fit_cache;idx=np.asarray([i for i,r in enumerate(rs) if r['season']>=floor and r['available']<origin and (method!='hgb_carry_primary' or r['position'] in ('QB','RB'))],dtype=int);y=ty[idx];positions=[rs[i]['position'] for i in idx];globalprior=(chart.chart_prior if target==chart.TARGET else lambda v:prior(v,target))(y);counts={pos:positions.count(pos) for pos in source.POSITIONS};priors={pos:(chart.chart_prior if target==chart.TARGET else lambda v:prior(v,target))([ty[i] for i in idx if rs[i]['position']==pos]) if counts[pos] else globalprior for pos in source.POSITIONS};model=None;modelpacket=None;state='NO_FIT_INSUFFICIENT_TRAINING';began=ended=None;minimum=60 if method in ('leaf','c02') else 40
               if isalias:model,modelpacket,state,originalslot=fit_cache[cachekey];aliases+=1;state='REUSED_IDENTICAL_POLICY:'+state
               elif len(idx)>=minimum:
                if all_zero_count_skip(method,target,y):state='NO_FIT_ALL_ZERO_COUNT'
                elif target=='anytime_td' and len(np.unique(y))<2:state='NO_FIT_SINGLE_CLASS_BINARY'
                else:
                 if fitcalls>=p['budget']['max_fit_calls']:raise RuntimeError('FIT_BUDGET')
                 fitcalls+=1;began=now()
                 try:
                    if method in ('leaf','c02','glm_law'):
                        model=(chart.ChartModel('ordered_leaf_cdf' if method!='glm_law' else 'regularized_glm_law',target) if target==chart.TARGET else laws.FittedLawModel('ordered_leaf_cdf' if method!='glm_law' else 'regularized_glm_law',target));model.fit(c02.project(tx[idx]) if method=='c02' else tx[idx],y,positions)
                    else:model=count.make_estimator(count.POISSON if method=='hgb_poisson' else count.RA) if method in ('hgb_poisson','hgb_carry_primary') else source.make_estimator(target,'absolute_error_point' if method=='hgb_L1' else 'squared_error_mean' if method=='hgb_L2' else 'log_loss_probability');model.fit(tx[idx],y)
                    ended=now();guard();modelpacket=save(private/'models'/(slot+'.pickle.gz'),pickle.dumps(model,protocol=5),True);retained+=1;state='FITTED_RETAINED'
                 except Exception as exc:model=None;ended=now();state='FIT_FAILED_FALLBACK';failcount+=1;failures.append(dict(slot=slot,type=type(exc).__name__,reason=str(exc)[:240]))
               if not isalias:fit_cache[cachekey]=(model,modelpacket,state,slot)
               membership=hashlib.sha256(canonical([(rs[i]['game_id'],rs[i]['player_id']) for i in idx])).hexdigest();trainmax=max((tm[i] for i in idx if tm[i] is not None),default=None);labelmax=max((rs[i]['available'] for i in idx),default=None)
               if labelmax is not None and labelmax>=origin:raise ValueError('training label chronology')
               audit=dict(slot=slot,target=target,method=method,policy_id=policy,history_regime=arm,state=state,alias_of=originalslot if isalias else None,training_n=len(idx),training_seasons=sorted({rs[i]['season'] for i in idx}),training_membership_sha256=membership,fit_cutoff=origin,feature_floor=memory,latest_training_label_available=labelmax,latest_training_feature_available=trainmax,prior_parameters={pos:law.parameters() for pos,law in priors.items()},prior_position_sample_counts=counts,actual_fit_started_at=began,actual_fit_completed_at=ended,model=modelpacket,query_features=featurepacket)
               write(public/(slot+'-FIT.json'),audit);grids.append(dict(slot=slot,state=state,alias_of=audit['alias_of'],training_n=len(idx)))
               inputq=c02.project(qx) if method=='c02' else qx;lawmodel=method in ('leaf','glm_law','c02')
               if lawmodel:predicted=laws.predict_admitted(model,inputq,qr,priors)
               elif model is not None:predicted=model.predict_proba(inputq)[:,list(model.classes_).index(1.)] if method=='hgb_TD' else model.predict(inputq)
               else:predicted=[None]*len(qr)
               strict=policy.endswith('STRICT');proc,family=procedure(method,target,strict);generated=now()
               for j,q in enumerate(qr):
                fb='none';fbsource=None;fbn=None;d=None;detail=None;scale=50 if target==chart.TARGET else 1
                if lawmodel:
                    law,detail=predicted[j]
                    if model is None or fullq[j][3]<=0:law=priors[q['position']];fb='fixed_no_NFL_startup' if not len(idx) else 'cold_start_role_prior' if fullq[j][3]<=0 else 'no_model_role_prior';fbsource='fixed_no_NFL_startup' if not len(idx) else 'same_arm_position_prior' if counts[q['position']] else 'same_arm_global_prior';fbn=counts[q['position']] or len(idx);detail=dict(fallback_prior=law.parameters())
                    d=chart.chart_summary(law,q['actual_grid']) if target==chart.TARGET else law.summary(q['actual'])
                elif model is None:s,fb=fallback_summary(target,policy,q,method);fbn=s[0];fbsource=fb
                for product in products(method,target):
                    if lawmodel:value=d['mean' if product=='event_probability' else product]
                    elif model is not None:value=source.project_point(target,predicted[j])
                    else:value=(s[2] if product in ('absolute_error_point','absolute_loss_point') else s[1])/scale if s[0] else 0.
                    r=dict(q,run_id=p['run_id'],procedure_id=proc,family=family,history_regime=arm,policy_id=policy,information_policy='STRICT-CURRENT' if strict else 'COMMON-2022-MEMORY',product_id=product,prediction=value,fallback=fb,fallback_source=fbsource,fallback_source_n=fbn,status='RECONSTRUCTED_RESEARCH_FORECAST',fit_slot=slot,fit_state=state,model_artifact_id=None if modelpacket is None else modelpacket['artifact_id'],latest_training_label_available=labelmax,latest_training_feature_available=trainmax,latest_feature_available=qm[j],feature_cutoff=q['cutoff'],fit_cutoff=origin,actual_generated_at=generated,distribution_summary=d,law_reference=detail)
                    add(r,writer)
               guard()
            text.flush();text.detach()
          private_bytes+=path.stat().st_size;completed_weeks.append(week);write(public/f'WEEK-{week:02}-RECEIPT.json',dict(week=week,actual_completed_at=now(),fit_calls_cumulative=fitcalls,retained_models_cumulative=retained,output_views=output_count-before,packet=dict(bundle_name=path.relative_to(private).as_posix(),sha256=sha(path),bytes=path.stat().st_size),resource_so_far=dict(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)))
          try:
            print(json.dumps(dict(season=year,week=week,actual_fit_calls=fitcalls,retained_models=retained,output_views=output_count,active_wall_seconds=time.monotonic()-start)),flush=True)
          except BrokenPipeError:
            pass # Progress transport cannot invalidate an already persisted week.
      except Exception as exc:terminal='PARTIAL_STOPPED';failures.append(dict(type=type(exc).__name__,reason=str(exc)[:240]))
    # Reuse authenticated saved empirical rows, not another fit or refreshed model.
    baseline=private/'predictions'/'EMPIRICAL_REPLAY.csv.gz';empirical_rows=0;querykeys={tuple(q[k] for k in ('game_id','player_id','target','population')):q for w in byweek.values() for q in w}
    with baseline.open('xb') as raw:
     with gzip.GzipFile(fileobj=CheckedStream(raw,lambda:p['budget']['max_private_bytes']-private_bytes),mode='wb',mtime=0) as handle:
      text=io.TextIOWrapper(handle,encoding='utf-8',newline='');active_text=text;active_raw=raw;writer=csv.DictWriter(text,fieldnames=FIELDS,extrasaction='ignore');writer.writeheader()
      for inputfile,ischart in [(empirical_predictions,False),(empirical_chart_predictions,True)]:
       with gzip.open(inputfile,'rt') as f:
        for r in csv.DictReader(f):
         if r.get('season')!=str(year):continue
         if ischart and r.get('family')!='empirical_chart_history_control':continue
         target=r['target'];key=tuple(r[k] for k in ('game_id','player_id','target','population'));q=querykeys.get(key)
         if not q:continue
         product=r.get('product_id') if ischart else r['product'];product='mean' if product=='empirical_mean' else product
         actual=emp.numeric(r['actual']);prediction=emp.numeric(r['prediction'])
         if actual!=q['actual']:raise ValueError('empirical baseline actual mismatch')
         row=dict(q,run_id=p['run_id']+':retained-empirical-replay',procedure_id='empirical-player-history-control-v1',family='empirical_history_control',history_regime=r['history_regime'],policy_id=r['history_regime']+'-EMPIRICAL',information_policy='ARM_LIMITED_TARGET_HISTORY',product_id=product,prediction=prediction,fallback=r['fallback'],fallback_source=r.get('fallback_source'),fallback_source_n=r.get('used_n'),status='RETAINED_EMPIRICAL_REPLAY',distribution_summary=None,law_reference=None);add(row,writer);empirical_rows+=1
      text.flush();text.detach()
    private_bytes+=baseline.stat().st_size
    scores=[]
    for dims,meter in sorted(meters.items()):
        proc,family,target,policy,arm,product,pop,week,pos,view=dims;result=meter.result();scores.append(dict(procedure_id=proc,procedure_family_id=family,target=target,history_regime=arm,policy_id=policy,product_id=product,population=pop,season=year,evaluation_seasons=[year],week=int(week) if week.isdigit() else week,position=pos,fallback_view=view,evaluation_panel_id=p['run_id'],period='REG',record_kind='NEW_EXPERIMENT_CURRENT_VINTAGE_PARTICIPANT_DIAGNOSTIC',evidence='NEW_EXPERIMENT',source_vintage='current-vintage; seven-day availability assumption',feature_memory_policy='2022common or evaluationyearstrict; seepolicy_id',cohort_limit=p['cohort'],**result))
    write(public/'SCORES.json',scores);emp.write_csv(public/'SCORES.csv',scores);write(public/'FAILURES.json',failures);done={g['slot']:g for g in grids};fullgrid=[]
    for week in p['evaluation_weeks']:
     for target in TARGETS:
      for policy in policies(year):
       for method in methods(target):
        slot=f'W{week:02}-{target}-{policy}-{method}';fullgrid.append(done.get(slot,dict(slot=slot,state='NOT_RUN_AFTER_BOUNDED_STOP',alias_of=None)))
    write(public/'GRID_STATUS.json',fullgrid)
    flat=private/'predictions.csv.gz'
    with flat.open('xb') as raw:
     with gzip.GzipFile(fileobj=CheckedStream(raw,lambda:p['budget']['max_private_bytes']-private_bytes),mode='wb',mtime=0) as handle:
      text=io.TextIOWrapper(handle,encoding='utf-8',newline='');writer=csv.DictWriter(text,fieldnames=FIELDS,extrasaction='ignore');writer.writeheader()
      for file in sorted((private/'predictions').glob('*.csv.gz')):
       with gzip.open(file,'rt') as f:
        for i,r in enumerate(csv.DictReader(f)):
         writer.writerow(r)
         if i%1000==0:
          text.flush()
          if private_bytes+raw.tell()>p['budget']['max_private_bytes']:raise RuntimeError('FLAT_PRIVATE_BUDGET')
      text.flush();text.detach()
    private_bytes+=flat.stat().st_size;receipt=dict(version=VERSION,run_id=p['run_id'],state=terminal,actual_completed_at=now(),protocol_sha256=sha(public/'FROZEN_PROTOCOL.json'),evaluation_season=year,query_cells=len(queries),query_games=p['query_games'],unique_player_games=len({(q['game_id'],q['player_id']) for q in queries}),completed_weeks=completed_weeks,nominal_fit_opportunities=p['nominal_fit_opportunities'],unique_fit_opportunities=p['unique_fit_opportunities'],actual_fit_calls=fitcalls,retained_models=retained,failed_fits=failcount,identical_policy_alias_cells=aliases,completed_cells=len(grids),score_views=len(scores),forecast_output_views=output_count,retained_empirical_output_views=empirical_rows,labels=labels,private_flat=dict(bundle_name=flat.name,sha256=sha(flat),bytes=flat.stat().st_size),source_counts=sourcecounts,private_output_bytes=private_bytes,resource=dict(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,max_threads=2),new_family_count=0,new_future_forecasts=0,actual2026_refits=0,Week8_outcomes_read=0)
    write(public/'RUN_RECEIPT.json',receipt);return receipt
