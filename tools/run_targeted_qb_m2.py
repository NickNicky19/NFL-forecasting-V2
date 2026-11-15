"""One bounded M2 rolling-origin package; no source acquisition or search."""
import argparse,copy,gzip,hashlib,json,math,platform,resource,sys,time
from pathlib import Path
import numpy as np
import scipy,sklearn
from threadpoolctl import threadpool_limits

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from nfl_v2 import targeted_qb_m2 as m2,player_context_matchup as ctx
from nfl_v2.qb_depth_catchability import DepthHistory
from nfl_v2.qb_depth_catchability_v2 import ConvergedDepthCompletionModel
from nfl_v2.distribution_laws import prior
from nfl_v2.distribution_wave_v2 import FittedLawModel
from tools.run_player_context_wave import read,write,sha,now,clean

BASE=ROOT/'reports/targeted-accuracy-w1w9-01/B'
OUT=BASE/'wave-v1'
INPUTS=ROOT/'reports/information-first-20261112-01/B/completion-wave-v1/QB_CONTEXT_W1_W9_INPUTS_V1.json.gz'
CHART=ROOT/'reports/player-context-completion-decision-01/B/source-depth-v1/FTN_DEPTH_QB_GAME_INPUTS.json.gz'
PARENTS={'P2':ROOT/'reports/player-context-matchup-01/B/qb-wave-v1',
         'C1':ROOT/'reports/player-context-completion-decision-01/B/depth-wave-v2',
         'C2':ROOT/'reports/player-context-completion-decision-01/B/depth-wave-v2'}
PLAN=[(2025,w)for w in range(11,19)]+[(2026,w)for w in range(1,10)]

class Budget:
    def __init__(self):
        self.path=OUT/'OPTIMIZER_ATTEMPTS.jsonl';self.start=time.monotonic();self.cpu=time.process_time()
    def charge(self,slot,nfl=True):
        n=len(self.path.read_text().splitlines())if self.path.exists()else 0
        if n>=64:raise RuntimeError('REGISTERED_OPTIMIZER_CAP')
        if time.process_time()-self.cpu>1800 or time.monotonic()-self.start>1200:raise RuntimeError('REGISTERED_COMPUTE_CAP')
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>2147483648:raise RuntimeError('REGISTERED_RSS_CAP')
        with self.path.open('a')as f:f.write(json.dumps({'slot':slot,'started_UTC':now(),'NFL_fit':nfl,'attempt':n+1})+'\n')
    def resource(self):
        return dict(cpu_seconds=time.process_time()-self.cpu,wall_seconds=time.monotonic()-self.start,
          peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
          cumulative_optimizer_calls=len(self.path.read_text().splitlines())if self.path.exists()else 0)

def context():
    rows=ctx.load_inputs(INPUTS);history=ctx.ContextHistory(rows,8,20.)
    chart=DepthHistory(rows,read(CHART),8,20.)
    return rows,history,chart

def old_parents():
    out={};bindings={}
    for method,base in PARENTS.items():
        out[method]={}
        for path in sorted((base/'predictions').glob('*.json.gz')):
            bindings[str(path.relative_to(ROOT))]=sha(path)
            for r in read(path)['rows']:
                if r['method']==method:out[method][r['game_id'],r['player_id']]=r
    missing=OUT/'parents/PREDICTIONS_2026_W09.json.gz'
    if missing.exists():
        for r in read(missing)['rows']:out[r['method']][r['game_id'],r['player_id']]=r
    return out,bindings

def prepare():
    OUT.mkdir(exist_ok=False);rows,h,ch=context();parents,bindings=old_parents()
    keys={(r['game_id'],r['player_id'])for r in rows};chartkeys=set(ch.chart)
    lastq=[q for q in rows if q['season']==2026 and q['week']==9]
    latest=max(q['kickoff']for q in lastq)
    eligible_keys={(r['game_id'],r['player_id'])for r in h.rows if r['available']<latest}
    assert eligible_keys<=chartkeys
    oldcounts={p:len(v)for p,v in parents.items()};assert all(n==941 for n in oldcounts.values())
    code=[Path(__file__),ROOT/'nfl_v2/targeted_qb_m2.py',ROOT/'nfl_v2/player_context_matchup.py',
          ROOT/'nfl_v2/qb_depth_catchability.py',ROOT/'nfl_v2/qb_depth_catchability_v2.py',
          ROOT/'nfl_v2/distribution_wave_v2.py',ROOT/'nfl_v2/distribution_laws.py']
    p=dict(id=m2.VERSION,state='FROZEN_BEFORE_NEW_OPTIMIZER_CALLS_AND_COMPARATIVE_SCORES',at_UTC=now(),owner='B_ROOT',coordinator='C',
      source_inputs={str(x.relative_to(ROOT)):sha(x)for x in [INPUTS,CHART]},code={str(x.relative_to(ROOT)):sha(x)for x in code},
      old_prediction_bindings=bindings,old_rows_per_parent=oldcounts,plan=PLAN,
      new_mechanism='Learn context-dependent game-conversion BB dispersion on earlier-origin OOT predicted means; fixed parent conversion mean and analytic common attempt law.',
      mean_parents={'P2':'Retained penalized QB/team/defense conditional25down-depthlogistic',
                    'C1':'Retained shared conditionalcontextGLM plus depthchart support',
                    'C2':'C1plus qualifiedearlier depthcatchability values'},
      arms={p:{'BIN':'exact unchanged mean/exposure/binomial thinning','BB':'same mean/exposure plus new learned conditional precision'}for p in PARENTS},
      direct='D_M2:unchanged32treeLeafCDF learner, same P2+dispersion input information, predicted attemptμ/shape, fit-onlyidentitylevels; standaloneCMPmarginal, no jointclaim.',
      feature_schema=list(m2.FEATURES),kappa_link='0.05+9999.95*expit(zbeta); fixedridge intercept1 towardk20 andslopes10toward0',
      optimizer='L-BFGS-Bmaxiter200ftol1e-10gtol1e-6; no search; nonconvergenceusesregisteredk20fallback',
      history='H-RECENT previousseason+earliercurrentlabels; sourcefeaturesown8strength20/expanding2022memory; inherited7daystrictavailability<cutoff.',
      fitting='Weekly beforeearliestgame. Dispersiontrainingusesearlier-origin OOTparentpmean andactualhistoricalattempt/completionlabels available<origin; no in-sample residual fitting.',
      source_tier='CURRENT_VINTAGE_SEVEN_DAY_CHRONOLOGICAL_RECONSTRUCTION;NOT_AUTHENTICATED_HISTORICAL_PUBLICATION',
      scope_limits='No receiverpersonnel universe or actualalignment/routes. Destinationentropy anddistancehistory arepregame summary dispersioncovariates, not jointper-attemptdistancecells. Predicted25mix fixed, not full posteriorcontextuncertainty.',
      forecast_population='RetainedofficialQBstat-rowqueries, not authenticatedexante roster; no targetgameoutcomes orrealizedcontextsinpredictors.',
      exact_integration={'attempt_tail_tolerance':m2.TAIL_TOL,'no_renormalization':True,'support':'InfiniteNBattempts; C<=A; numericalgridtailbounded, notdata-dependentclipping'},
      chart_contrasts='C2-C1 samebinary/BBfamily isolates chartvaluesbeyondsupport. P2versusC1 differssharing/features andiscomplete-systemonly.',
      budget={'optimizer_calls_max':64,'NFL_calls_max':63,'synthetic_calls_max':1,'dispersion':51,'missing_parent_W9':3,'direct_current_origins':9,'CPU_seconds':1800,'wall_seconds':1200,'max_threads':2,'RSS_bytes':2147483648,'public_bytes':33554432},
      evaluated_old_outcomes_exposed=True,lookback_and_settings='Inheritedfixed8/20and32tree; newdispersionlink/ridge frozen scientificallybeforecomparativegains; no tuning menu.',
      pilot='Beforebroad:3missingW9meanfits,1syntheticpositivecontrol,firstchronological2025W11P2dispersion; saveinputs/code/models and exactGitHubreadback.',
      selection_protocol='../evaluation/FROZEN_EVALUATION_PROTOCOL_V1.json',
      source_coverage={'chart_rows':len(ch.chart),'W9_chart_not_required':True,'eligible_chart_keys_all_matched':len(eligible_keys)},
      original_issuance=False,new_primary_release=False)
    write(OUT/'FROZEN_PROTOCOL_V1.json',p)
    write(OUT/'ENVIRONMENT_V1.json',dict(python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__,sklearn=sklearn.__version__))
    print(json.dumps({'state':p['state'],'parent_rows':oldcounts,'plan':PLAN}))

def missing_means(rows,h,ch,budget):
    destination=OUT/'parents/PREDICTIONS_2026_W09.json.gz'
    if destination.exists():return
    query=[q for q in rows if(q['season'],q['week'])==(2026,9)];cutoff=min(q['kickoff']for q in query)
    train=h.eligible(cutoff,2025);forecasts=[]
    for parent in PARENTS:
        budget.charge('MISSING_MEAN_2026W09_'+parent)
        if parent=='P2':model=ctx.CompletionModel(True,20).fit(train,h)
        else:model=ConvergedDepthCompletionModel(values=parent=='C2',penalty=20.).fit(train,h,ch)
        path=OUT/'parents'/('2026-W09-'+parent+'.json.gz')
        write(path,dict(model=model.payload(),fit_cutoff=cutoff,latest_label=max(r['available']for r in train),
          training_membership_sha256=hashlib.sha256(json.dumps([(r['game_id'],r['player_id'])for r in train]).encode()).hexdigest(),
          rows=len(train),source_policy='UNMODIFIED_RETAINED_PARENT_FAMILY',actual_execution_UTC=now()))
        for q in query:
            d=h.describe(q);a=h.exposure(q);pc=model.probabilities(q,h)if parent=='P2'else model.probabilities(q,h,ch)
            prob=float(d['mix']@pc);law=ctx.CountLaw(a.mean*prob,a.shape)
            forecasts.append(dict(procedure_id=(ctx.VERSION+':P2')if parent=='P2'else'B-QB-DEPTH-CATCHABILITY-v2:'+parent,
              method=parent,game_id=q['game_id'],player_id=q['player_id'],season=2026,week=9,team=q['team'],opponent=q['opponent'],target='pass_cmp',
              kickoff=q['kickoff'],fit_cutoff=cutoff,feature_cutoff=q['kickoff'],mean=law.mean,lower_median=law.quantile(.5),law=law.parameters(),
              components=dict(attempt_law=a.parameters(),predicted_context_mix=d['mix'].tolist(),conditional_completion_probability=pc.tolist(),integrated_completion_probability=prob),
              actual=q['official_completions']if q['physical_participation']else None,actual_status=q['label_status'],fallback=d['fallback'],original_issuance=False))
    write(destination,dict(rows=forecasts,fit_cutoff=cutoff,actual_persisted_UTC=now(),original_issuance=False))

def dispersion_training(parent,parents,rows,h,cutoff,season):
    data=[]
    for q in h.eligible(cutoff,season-1):
        r=parents[parent].get((q['game_id'],q['player_id']))
        if r is None:continue
        if r['fit_cutoff']>q['kickoff']or r['feature_cutoff']!=q['kickoff']:raise ValueError('OOFparentclock')
        m=r['components']['integrated_completion_probability']
        if not 0<m<1:raise ValueError('UnsupportedOOFconversionendpoint')
        z,trace=m2.dispersion_features(q,h)
        if trace['latest_own_source']is not None and trace['latest_own_source']>=q['kickoff']:raise ValueError('Historical dispersionfeature chronology')
        data.append(dict(game_id=q['game_id'],player_id=q['player_id'],available=q['available'],kickoff=q['kickoff'],parent_fit_cutoff=r['fit_cutoff'],
          parent_probability=m,attempts=q['official_attempts'],completions=q['official_completions'],z=z.tolist()))
    return data

def fit_dispersion(parent,season,week,cutoff,parents,rows,h,budget):
    path=OUT/'fits'/f'{season}-W{week:02}-{parent}-BB.json.gz'
    if path.exists():return m2.DispersionModel.restore(read(path)['model'])
    data=dispersion_training(parent,parents,rows,h,cutoff,season)
    budget.charge(f'{season}-W{week:02}-{parent}-BB')
    model=m2.DispersionModel().fit([r['z']for r in data],[r['attempts']for r in data],[r['completions']for r in data],[r['parent_probability']for r in data])
    write(path,dict(model=model.payload(),fit_cutoff=cutoff,training_rows=len(data),latest_training_label=max((r['available']for r in data),default=None),
      training_objective_inputs=data,training_membership_sha256=hashlib.sha256(json.dumps([(r['game_id'],r['player_id'])for r in data]).encode()).hexdigest(),actual_execution_UTC=now()))
    return model

def direct_x(q,h,levels):
    d=h.describe(q);a=h.exposure(q);z,_=m2.dispersion_features(q,h)
    aa,cc=d['own_attempts'],d['own_completions']
    x=list(d['mix'])+list(d['opponent_residual'])+[math.log((cc+1)/(aa-cc+1)),d['opponent_residual_main'],d['team_residual']]+list(z)+[a.mean,a.shape]
    for field in ('player_id','team','opponent'):x += [float(q[field]==v)for v in levels[field]]
    return np.asarray(x,float)

def direct_fit_and_predict(qs,rows,h,season,week,cutoff,budget):
    train=h.eligible(cutoff,season-1);levels={f:sorted({q[f]for q in train})for f in ('player_id','team','opponent')}
    xx=np.asarray([direct_x(q,h,levels)for q in train]);y=np.asarray([q['official_completions']for q in train]);pr=prior(y,'pass_cmp')
    budget.charge(f'{season}-W{week:02}-D_M2');model=FittedLawModel('ordered_leaf_cdf','pass_cmp').fit(xx,y,['QB']*len(y));payload=ctx.export_forest(model)
    write(OUT/'fits'/f'{season}-W{week:02}-D_M2.json.gz',dict(model=payload,identity_levels=levels,prior=pr.parameters(),fit_cutoff=cutoff,
      training_rows=len(train),training_membership_sha256=hashlib.sha256(json.dumps([(r['game_id'],r['player_id'])for r in train]).encode()).hexdigest(),
      feature_information='P2meansameinput+BBdispersionz+predictedATTmean/shape;onlyeligiblefitidentitylevels',feature_width=xx.shape[1]))
    result=[]
    for q in qs:
        x=direct_x(q,h,levels);law=ctx.restored_forest_law(payload,x,pr);fresh=model.predict(x[None,:],['QB'],{'QB':pr})[0][0]
        assert abs(fresh.mean-law.mean)<1e-10
        result.append(dict(method='D_M2',procedure_id=m2.VERSION+':D_M2',game_id=q['game_id'],player_id=q['player_id'],team=q['team'],opponent=q['opponent'],
          season=season,week=week,target='pass_cmp',kickoff=q['kickoff'],fit_cutoff=cutoff,feature_cutoff=q['kickoff'],
          mean=law.mean,lower_median=law.quantile(.5),law=dict(kind='leaf_mixture',support=law.support.tolist(),weights=law.weights.tolist(),prior=pr.parameters(),mixture=.05),
          actual=q['official_completions']if q['physical_participation']else None,actual_status=q['label_status'],fallback='none',
          distribution_scope='STANDALONE_COMPLETION_MARGINAL_CONTROL_NOT_ATTEMPT_JOINT',features=x.tolist(),original_issuance=False))
    return result

def positive_control(budget):
    path=OUT/'SYNTHETIC_POSITIVE_CONTROL_V1.json'
    if path.exists():return
    rng=np.random.default_rng(1703);n=np.full(600,35);m=np.full(600,.65);z=np.zeros((600,7));z[:,0]=1;z[300:,1]=1
    precision=np.r_[np.full(300,1.),np.full(300,120.)]
    theta=rng.beta(m*precision,(1-m)*precision);c=rng.binomial(n,theta)
    budget.charge('SYNTHETIC_POSITIVE_CONTROL',nfl=False);model=m2.DispersionModel().fit(z,n,c,m)
    initial=m2.DispersionModel.objective(m2.prior_beta(),z,n,c,m)[0];final=m2.DispersionModel.objective(model.beta,z,n,c,m)[0]
    assert final<initial and model.precision(z)[300:].mean()>model.precision(z)[:300].mean()
    write(path,dict(seed=1703,NFL_evaluation=False,rows=600,initial_penalized_objective=initial,fitted_penalized_objective=final,model=model.payload(),
      learned_precision_by_group=[float(model.precision(z)[:300].mean()),float(model.precision(z)[300:].mean())],state='PASS_CAN_LEARN_STRONG_ELIGIBLE_DISPERSION_SIGNAL'))

def run(pilot):
    p=read(OUT/'FROZEN_PROTOCOL_V1.json')
    for path,digest in {**p['source_inputs'],**p['code'],**p['old_prediction_bindings']}.items():assert sha(ROOT/path)==digest,path
    rows,h,ch=context();budget=Budget();start=now()
    with threadpool_limits(limits=2):
        missing_means(rows,h,ch,budget);positive_control(budget);parents,_=old_parents()
        plan=PLAN[:1]if pilot else PLAN
        for season,week in plan:
            qs=[q for q in rows if(q['season'],q['week'])==(season,week)];cutoff=min(q['kickoff']for q in qs)
            methods=('P2',)if pilot else tuple(PARENTS)
            for parent in methods:fit_dispersion(parent,season,week,cutoff,parents,rows,h,budget)
            if pilot:continue
            path=OUT/'predictions'/f'{season}-W{week:02}.json.gz'
            if path.exists():continue
            forecasts=[]
            for parent in PARENTS:
                dispersion=m2.DispersionModel.restore(read(OUT/'fits'/f'{season}-W{week:02}-{parent}-BB.json.gz')['model'])
                for q in qs:
                    r=parents[parent][q['game_id'],q['player_id']];components=r['components'];a=components['attempt_law'];m=components['integrated_completion_probability'];z,trace=m2.dispersion_features(q,h)
                    k=float(dispersion.precision(z));bb=m2.IntegratedBetaBinomial(a['mean'],a['shape'],m,k)
                    for suffix in ('BIN','BB'):
                        law=ctx.CountLaw(a['mean']*m,a['shape'])if suffix=='BIN'else bb
                        v=copy.deepcopy(r);v.update(method=f'M2_{parent}_{suffix}',procedure_id=m2.VERSION+f':{parent}_{suffix}',target='pass_cmp',season=season,week=week,
                          kickoff=q['kickoff'],fit_cutoff=cutoff,feature_cutoff=q['kickoff'],mean=law.mean,lower_median=law.quantile(.5),law=law.parameters(),
                          original_parent_procedure=r['procedure_id'],original_parent_fit_cutoff=r['fit_cutoff'],dispersion_features=z.tolist(),dispersion_trace=trace,
                          new_execution_UTC=now(),source_tier=p['source_tier'],original_issuance=False,
                          conversion_components={'mean':m,'precision':k if suffix=='BB'else None,'rho':1/(k+1)if suffix=='BB'else 0.,'same_attempt_mean':a['mean'],'same_attempt_shape':a['shape'],
                            'new_dispersion_model_fallback':dispersion.optimization.get('fallback')if suffix=='BB'else None})
                        if suffix=='BB':v['numerical_integration']={'max_attempt_grid':bb.grid_max,'omitted_attempt_tail':bb.omitted_attempt_tail,'tail_tolerance':m2.TAIL_TOL,'renormalized':False,'variance':bb.variance}
                        forecasts.append(v)
            if season==2026:forecasts+=direct_fit_and_predict(qs,rows,h,season,week,cutoff,budget)
            for q in qs:
                law=h.exposure(q);d=h.describe(q)
                forecasts.append(dict(method='COMMON_EXPOSURE',procedure_id=ctx.VERSION+':COMMON_EXPOSURE',game_id=q['game_id'],player_id=q['player_id'],team=q['team'],opponent=q['opponent'],
                  season=season,week=week,target='pass_att',kickoff=q['kickoff'],fit_cutoff=cutoff,feature_cutoff=q['kickoff'],mean=law.mean,lower_median=law.quantile(.5),law=law.parameters(),
                  actual=q['official_attempts']if q['physical_participation']else None,actual_status=q['label_status'],fallback=d['fallback'],original_issuance=False))
            write(path,dict(rows=forecasts,season=season,week=week,fit_cutoff=cutoff,actual_persisted_UTC=now(),resources=budget.resource(),original_issuance=False))
            print(json.dumps({'origin':[season,week],'rows':len(forecasts),'optimizer_calls':budget.resource()['cumulative_optimizer_calls']}),flush=True)
    state='PILOT_RETAINED_BEFORE_BROAD'if pilot else'COMPLETE_FIXED_M2_ROLLING_PACKAGE'
    write(OUT/('PILOT_RECEIPT_V1.json'if pilot else'RUN_RECEIPT_V1.json'),dict(state=state,started_UTC=start,completed_UTC=now(),resources=budget.resource(),
      new_model_families=1,changing_mean_in_BB=False,original_issuance=False,production_change=False))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('action',choices=['prepare','pilot','run']);a=ap.parse_args()
    if a.action=='prepare':prepare()
    else:run(a.action=='pilot')
