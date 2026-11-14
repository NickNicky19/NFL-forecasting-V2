"""Two registered fresh-fit checks; verification is not new NFL evaluation."""
import os
os.environ.update(OPENBLAS_NUM_THREADS='2',MKL_NUM_THREADS='2',OMP_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1')
if hasattr(os,'sched_setaffinity'):
    os.sched_setaffinity(0,set(sorted(os.sched_getaffinity(0))[:2]))
import argparse,copy,gzip,hashlib,json,math,platform,resource,subprocess,sys,tempfile,time
from datetime import datetime,timezone
from pathlib import Path

PIN='2fa855fc4dd7e9e495126dea93ba90a33fee4be3'
def digest(b):return hashlib.sha256(b).hexdigest()
def read(p):
    p=Path(p);b=p.read_bytes();return json.loads(gzip.decompress(b)if p.suffix=='.gz'else b)
def save(p,x):
    p=Path(p)
    if p.exists():raise FileExistsError(p.name)
    b=(json.dumps(x,separators=(',',':'),allow_nan=False)+'\n').encode();p.write_bytes(gzip.compress(b,mtime=0)if p.suffix=='.gz'else b)
def now():return datetime.now(timezone.utc).isoformat()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repository',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();root=a.repository.resolve();out=a.out.resolve()
    reg=read(out/'REGISTRATION_V1.json');assert reg['producer_commit']==PIN
    start=time.monotonic();cpu=time.process_time();calls=dict(NFL=0,synthetic=0);checks=[]
    def budget():
        assert time.monotonic()-start<reg['budget']['wall_seconds']
        assert time.process_time()-cpu<reg['budget']['cpu_seconds']
        assert resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<reg['budget']['max_RSS_bytes']
    def fit_started(kind,tag):
        budget();calls[kind]+=1;assert calls[kind]<=reg[kind+'_verification_fit_limit']if kind=='NFL'else calls[kind]<=reg['synthetic_fit_limit']
        with(out/'VERIFICATION_FIT_ATTEMPTS.jsonl').open('a')as f:f.write(json.dumps(dict(kind=kind,tag=tag,at_utc=now()))+'\n')
    scratch=Path(tempfile.mkdtemp(prefix='b-context-acceptance-pinned-'))
    # The isolated module tree is a clean immutable Git restoration, not the
    # working tree. No import or deserialization of a model pickle occurs.
    names=subprocess.check_output(['git','ls-tree','-r','--name-only',PIN,'nfl_v2'],cwd=root,text=True).splitlines()
    pinned=[]
    for name in names:
        if not name.endswith('.py'):continue
        body=subprocess.check_output(['git','show',PIN+':'+name],cwd=root);p=scratch/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(body);pinned.append(dict(path=name,sha256=digest(body),bytes=len(body)))
    sys.path.insert(0,str(scratch));import numpy as np
    from scipy import special,stats
    from threadpoolctl import threadpool_limits,threadpool_info
    from nfl_v2 import player_context_matchup as ctx
    from nfl_v2.distribution_wave_v2 import FittedLawModel
    from nfl_v2.distribution_laws import prior
    from nfl_v2.player_context_typed_adapter_v2 import restore_completion
    base='reports/player-context-matchup-01/B/'
    def immutable(relative):
        b=subprocess.check_output(['git','show',PIN+':'+relative],cwd=root);p=scratch/relative;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b);return p
    ip=immutable(base+'source-fields-v3/DERIVED_QB_GAME_INPUTS.json.gz');rows=ctx.load_inputs(ip)
    chosen=read(immutable(base+'qb-wave-v1/SELECTED_EARLIER_CONFIG.json'));assert(chosen['window'],chosen['strength'])==(8,20)
    originals={arm:read(immutable(base+'qb-wave-v1/fits/2025-W01-'+arm+'.json.gz'))for arm in('E1','P1','P2')}
    packet=read(immutable(base+'qb-wave-v1/predictions/2025-W01.json.gz'));origin=packet['fit_cutoff'];queries=sorted([q for q in rows if(q['season'],q['week'])==(2025,1)],key=lambda q:(q['game_id'],q['player_id']))
    history=ctx.ContextHistory(rows,8,20)
    train=[r for r in rows if r.get('physical_participation')and r['target_parity']and r['season']>=2024 and r['available']<origin]
    assert len(train)==664
    membership=digest(json.dumps([(r['game_id'],r['player_id'])for r in train]).encode());assert membership==originals['P1']['training_membership_sha256']
    trainx=np.asarray([history.direct_features(q,'E1')for q in train]);qx=np.asarray([history.direct_features(q,'E1')for q in queries]);y=np.asarray([q['official_completions']for q in train],float);pr=prior(y,'pass_cmp')
    assert max(r['available']for r in train)==originals['E1']['latest_training_label']<origin
    # Simultaneously demonstrate future-invariance of all training inputs and
    # query features. Identical input arrays imply the same registered seeded
    # fit choice without paying for a redundant third fit.
    mutated=copy.deepcopy(rows)
    for r in mutated:
        if r['kickoff']>=origin:
            for field in('context_attempts','context_completions'):r[field]=[2*v for v in r[field]]
            for field in('attempts','completions','official_attempts','official_completions'):r[field]*=2
    extra=copy.deepcopy(mutated[-1]);extra.update(game_id='SYNTHETIC_FUTURE_INVARIANCE_RECORD',player_id='SYNTHETIC_FUTURE_ONLY',kickoff=4102444800.,available=4103049600.);mutated.append(extra)
    mh=ctx.ContextHistory(mutated,8,20);mtrain=[r for r in mutated if r.get('physical_participation')and r['target_parity']and r['season']>=2024 and r['available']<origin]
    assert[(r['game_id'],r['player_id'],r['official_completions'])for r in train]==[(r['game_id'],r['player_id'],r['official_completions'])for r in mtrain]
    assert np.array_equal(trainx,np.asarray([mh.direct_features(q,'E1')for q in mtrain]),equal_nan=True)
    assert np.array_equal(qx,np.asarray([mh.direct_features(q,'E1')for q in queries]),equal_nan=True)
    checks.append(dict(check='FUTURE_MUTATION_TRAINING_AND_QUERY_INPUT_INVARIANCE',training_rows=len(train),query_rows=len(queries),status='PASS'))
    with threadpool_limits(limits=2):
        fit_started('NFL','2025-W01-E1-representative');forest=FittedLawModel('ordered_leaf_cdf','pass_cmp').fit(trainx,y,['QB']*len(y));fp=ctx.export_forest(forest)
        if fp!=originals['E1']['model']:
            save(out/'MATERIAL_FRESH_FOREST_DISCREPANCY_V1.json',dict(state='FAIL_STOP_FURTHER_FITS',expected_hash=digest(json.dumps(originals['E1']['model'],sort_keys=True).encode()),actual_hash=digest(json.dumps(fp,sort_keys=True).encode())));raise RuntimeError('Material fresh forest mismatch; no further fits')
        save(out/'FRESH_2025_W01_E1_PARAMETERS.json.gz',dict(producer_commit=PIN,verification_not_new_forecast=True,model=fp))
        fit_started('NFL','2025-W01-P1-representative');glm=ctx.CompletionModel(False,20).fit(train,history);gp=glm.payload()
        oldglm=restore_completion(originals['P1']['model'],producer_version=ctx.VERSION)
        coefficient_error=float(np.max(np.abs(glm.beta-oldglm.beta)));probability_error=max(float(np.max(np.abs(glm.probabilities(q,history)-oldglm.probabilities(q,history))))for q in queries)
        if coefficient_error>1e-6 or probability_error>1e-7:
            save(out/'MATERIAL_FRESH_GLM_DISCREPANCY_V1.json',dict(state='FAIL_STOP_FURTHER_FITS',coefficient_max_error=coefficient_error,probability_max_error=probability_error));raise RuntimeError('Material fresh GLM mismatch; no further fits')
        save(out/'FRESH_2025_W01_P1_PARAMETERS.json.gz',dict(producer_commit=PIN,verification_not_new_forecast=True,model=gp))
        checks.append(dict(check='TWO_FRESH_NFL_FAMILIES',origin=[2025,1],training_rows=len(train),forest_payload_exact=True,GLM_max_coefficient_error=coefficient_error,GLM_max_probability_error=probability_error,GLM_optimization=gp['optimization'],status='PASS'))
        # Native estimator single/batch and shuffled-row checks; typed consumer
        # receives bounded arrays, with feature-order schema bound separately.
        batch=forest.predict(qx,['QB']*len(queries),{'QB':pr});perm=np.arange(len(queries))[::-1];shuffled=forest.predict(qx[perm],['QB']*len(queries),{'QB':pr});maxmean=0.;maxcdf=0.
        saved={(r['method'],r['game_id'],r['player_id']):r for r in packet['rows']}
        for i,q in enumerate(queries):
            single=forest.predict(qx[i:i+1],['QB'],{'QB':pr})[0][0];typed=ctx.restored_forest_law(json.loads(json.dumps(fp,sort_keys=True)),qx[i],pr)
            for other in(single,typed,shuffled[len(queries)-1-i][0]):
                maxmean=max(maxmean,abs(batch[i][0].mean-other.mean));maxcdf=max(maxcdf,max(abs(batch[i][0].cdf(k)-other.cdf(k))for k in(-1,0,10,19,40,80)))
            original=saved['E1',q['game_id'],q['player_id']];assert abs(typed.mean-original['mean'])<1e-10 and typed.quantile(.5)==original['lower_median']
            pvec=glm.probabilities(q,history);desc=history.describe(q);exposure=history.exposure(q);claw=ctx.CountLaw(exposure.mean*float(desc['mix']@pvec),exposure.shape)
            original=saved['P1',q['game_id'],q['player_id']];assert abs(claw.mean-original['mean'])<1e-6 and claw.quantile(.5)==original['lower_median']
            rebuilt=restore_completion(json.loads(json.dumps(gp,sort_keys=True)),producer_version=ctx.VERSION);assert np.max(np.abs(rebuilt.probabilities(q,history)-pvec))<1e-12
            assert all(claw.cdf(k)+1e-12>=exposure.cdf(k)for k in range(80))
            for l in(single,claw,exposure):
                probabilities=[ctx.exact_probabilities(l,k)for k in(0,1.5,19,19.5,30,40.5)]
                assert all(abs(sum(p.values())-1)<1e-10 and min(p.values())>=-1e-12 for p in probabilities)
                assert all(probabilities[j]['over']+1e-12>=probabilities[j+1]['over']for j in range(len(probabilities)-1))
            # Exact binomial thinning check against a finite joint summation;
            # omitted exposure tail is explicitly bounded, not discarded mass.
            nmax=int(stats.nbinom.ppf(1-1e-12,exposure.shape,exposure.p));ns=np.arange(nmax+1);pn=stats.nbinom.pmf(ns,exposure.shape,exposure.p);pbar=float(desc['mix']@pvec)
            for c in(0,5,19):
                joint=float(np.sum(pn*stats.binom.pmf(c,ns,pbar)));assert abs(joint-claw.pmf(c))<2e-12
        assert maxmean<1e-10 and maxcdf<1e-10
        bad_width_rejected=False
        try:ctx.restored_forest_law(fp,qx[0][:-1],pr)
        except ValueError:bad_width_rejected=True
        assert bad_width_rejected
        schema=read(immutable(base+'qb-wave-v1/FEATURE_ORDER_V1.json'));assert len(schema['orders']['E1'])==qx.shape[1]
        # Mean/count law typing versus the lower median; no rounding in a side.
        typing_examples=sum(abs(v[0].mean-v[0].quantile(.5))>1e-9 for v in batch)
        checks.append(dict(check='SINGLE_BATCH_SHUFFLE_AND_TYPED_ROUNDTRIP',query_rows=len(queries),maximum_mean_difference=maxmean,maximum_CDF_difference=maxcdf,mean_differs_from_median_examples=typing_examples,width_rejected=True,
                           semantic_feature_order='Boundschema/sourcecode required; positionalconsumer cannot detect a same-width semantic permutation intrinsically.',status='PASS_WITH_EXPLICIT_ARRAY_CONTRACT'))
        # Upcoming queries contain no final outcome/availability field.
        uq=dict(game_id='SYNTHETIC_UNSEEN_QUERY_NOT_NFL_CAPTURE',player_id='SYNTHETIC_UNSEEN_PLAYER',team='UNSEEN_TEAM',opponent='UNSEEN_DEFENSE',season=2025,week=1,kickoff=origin)
        ud=history.describe(uq);assert ud['fallback']=='no_player_history_role_prior'and ud['own_games']==0
        ux=history.direct_features(uq,'E1');ulaw=ctx.restored_forest_law(fp,ux,pr);uconv=glm.probabilities(uq,history);uexp=history.exposure(uq)
        assert math.isfinite(ulaw.mean)and np.isfinite(uconv).all()and np.all((uconv>0)&(uconv<1))and uexp is not None
        p3fallback=[r for r in packet['rows']if r['method']=='P3'and r['fallback']=='shared_no_pooling_support_fallback']
        assert p3fallback
        for r in p3fallback:
            match=saved['P1',r['game_id'],r['player_id']];assert r['mean']==match['mean']and r['law']==match['law']and r['lower_median']==match['lower_median']
        zero=ctx.CountLaw(0,2);assert zero.pmf(0)==1 and zero.pmf(1)==0 and zero.cdf(-1)==0
        checks.append(dict(check='STARTUP_UNSEEN_AND_FALLBACK',source_P3_shared_fallbacks=len(p3fallback),unseen_query_requires_final_outcome=False,zero_exposure_zero_completions=True,status='PASS'))
        # Frozen synthetic positive controls for both distinct family paths.
        signal=np.tile(np.r_[np.zeros(120),np.ones(120)],2);sx=signal[:,None];sy=20*signal
        fit_started('synthetic','strongeligible-direct-signal');positive=FittedLawModel('ordered_leaf_cdf','pass_cmp').fit(sx,sy,['QB']*len(sy));pv=positive.predict(np.array([[0.],[1.]]),['QB','QB'],{'QB':prior(sy,'pass_cmp')});gap=pv[1][0].mean-pv[0][0].mean;assert gap>15
        class SyntheticHistory:
            def describe(self,q):return dict(own_attempts=100.,own_completions=95. if q['signal'] else 5.,opponent_residual_main=0.,opponent_residual=np.zeros(25),team_residual=0.)
        fake=[]
        for i in range(40):
            n=[0]*25;c=[0]*25;n[0]=100;c[0]=95 if i%2 else 5
            fake.append(dict(team='T',opponent='D',signal=i%2,context_attempts=n,context_completions=c))
        fit_started('synthetic','strongeligible-conditional-signal');cg=ctx.CompletionModel(False,20).fit(fake,SyntheticHistory());low=cg.probabilities(dict(team='T',opponent='D',signal=0),SyntheticHistory())[0];high=cg.probabilities(dict(team='T',opponent='D',signal=1),SyntheticHistory())[0];assert high-low>.8
        checks.append(dict(check='SYNTHETIC_POSITIVE_CONTROLS_NOT_NFL_EVIDENCE',forest_mean_signal_gap=gap,conditional_probability_signal_gap=float(high-low),status='PASS'))
    budget();size=sum(p.stat().st_size for p in out.iterdir()if p.is_file());assert size<reg['budget']['artifact_bytes']
    receipt=dict(state='PASS_REPRESENTATIVE_FRESH_FIT_AND_INFERENCE',producer_commit=PIN,completed_utc=now(),registration_sha256=digest((out/'REGISTRATION_V1.json').read_bytes()),verifier_sha256=digest(Path(__file__).read_bytes()),
        isolated_code_files=pinned,source_input_sha256=digest(ip.read_bytes()),origin=dict(season=2025,week=1,fit_cutoff=origin,training_rows=len(train),training_membership_sha256=membership,latest_training_label=max(r['available']for r in train),first_query_kickoff=min(q['kickoff']for q in queries)),
        fresh_fit_calls=calls,new_NFL_observations=0,new_NFL_test_weeks=0,new_offered_line_weeks=0,new_original_forecasts=0,checks=checks,
        resources=dict(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,CPU_affinity=len(os.sched_getaffinity(0)),threadpools=[{k:d.get(k)for k in('internal_api','num_threads','version')}for d in threadpool_info()]),
        judgments=dict(A='PASS_FOR_EXACT_TWO_FAMILIES_AND_DECLARED_2025W1_ORIGIN',B='PASS_WITHIN_SEVEN_DAY_RECONSTRUCTION_NOT_AUTHENTICATED_VINTAGE',C='PASS_TWO_FRESH_FITS_PLUS34QUERY_COMPLETE_PATH_AND_EXISTING_SCOPE',D='UNKNOWN_BEST_ATTAINABLE_CONTEXT_CAPACITY;FIXED_LEARNER_ABLATION_ONLY',E='PARTIAL_TWO_TARGETS_NO_NEW_OLDER_OFFERS_OR_ROUTING',F='NO_PREDICTIVE_GAIN_OR_RELEASE_CLAIM_FROM_VERIFICATION'),
        limitations=['Fresh fits cover two representative model families at one origin, not all945originalfits or all25laterorigins.','P3 has own coefficients/sharedinputs/fallback, not entirely own-information system.','Same-width feature semantic reorder requires bound caller schema; rawarray checks width not feature names.','No capacity/window search, no calibration repair, no newscoring or originalcapture.','Models current/revised source +7day reconstructed availability; authenticated historicalvintages unestablished.'])
    save(out/'FRESH_FIT_INFERENCE_ACCEPTANCE_V1.json',receipt);print(json.dumps({k:receipt[k]for k in('state','fresh_fit_calls','resources','judgments')}))

if __name__=='__main__':
    try:main()
    except Exception as error:
        # Original output is retained; a failed checker never overwrites a
        # completed fit or licenses a repeated fit.
        print('VERIFICATION_FAILED',type(error).__name__,str(error),flush=True);raise
