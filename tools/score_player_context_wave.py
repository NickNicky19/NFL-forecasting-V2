"""Owner-local projections of frozen QB outputs through the existing V2 scorer.

Offers stay owner-local. Public outputs contain aggregates and source commitments;
this adapter does not implement another settlement engine or produce live picks.
"""
import argparse, collections, csv, gzip, hashlib, json, math, resource, sys, time
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from scipy.stats import rankdata

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from nfl_v2 import scoring, player_context_matchup as ctx
from nfl_v2.distribution_laws import Law
from nfl_v2.full_provider_prop_replay import score_row, check_triplet
from nfl_v2.paired_uncertainty import paired_losses

VERSION='B-QB-CONTEXT-SCORES-v1'
BASE=ROOT/'reports/player-context-matchup-01/B'
TIER='CURRENT_REVISED_SOURCE_SEVEN_DAY_RECONSTRUCTION_TIMING_UNVERIFIED_ACTUAL_LINE_DIAGNOSTIC'

def read(p):
    p=Path(p);b=p.read_bytes();return json.loads(gzip.decompress(b)if p.suffix=='.gz'else b)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def now():return datetime.now(timezone.utc).isoformat()
def write(p,x):
    p=Path(p)
    if p.exists():raise FileExistsError(p.name)
    p.parent.mkdir(parents=True,exist_ok=True)
    body=(json.dumps(x,separators=(',',':'),allow_nan=False)+'\n').encode()
    p.write_bytes(gzip.compress(body,mtime=0)if p.suffix=='.gz'else body)
def law(r):
    p=r['law']
    if p['kind']=='gamma_poisson_count':return ctx.CountLaw(p['mean'],p['shape'])
    if p['kind']=='leaf_mixture':
        return Law('mixture',support=p['support'],weights=p['weights'],prior=Law(**p['prior']),mixture=p['mixture'])
    raise ValueError('Unregistered law')
def isfallback(r):return r.get('fallback') not in(None,'none','NONE','learned','NOT_APPLICABLE')
def key(r):return r['game_id'],r['player_id'],r['target']
def ident(r):return [r['game_id'],r['player_id'],r['target']]
def sidepoint(point,line):
    if point is None:return None
    a,b=scoring.exact_decimal(point),scoring.exact_decimal(line)
    return 'over'if a>b else'under'if a<b else None

def prepare(a):
    p=read(a.wave/'FROZEN_PROTOCOL.json')
    offers=[]
    for w in range(5,9):
        source=getattr(a,'week'+str(w));offers.append(dict(week=w,sha256=sha(source),bytes=source.stat().st_size))
    out=dict(id=VERSION,state='FROZEN_BEFORE_NEW_SCORES',registered_utc=now(),owner='B',coordinator='C',
        producer_protocol_sha256=sha(a.wave/'FROZEN_PROTOCOL.json'),scoring_adapter_sha256=sha(__file__),
        grader_sha256=sha(ROOT/'nfl_v2/scoring.py'),aggregate_sha256=sha(ROOT/'nfl_v2/full_provider_prop_replay.py'),
        offers=offers,method_scope='All7frozencompletionprocedures and1commonattemptlaw; unchanged savedLeaf mean/median where compatible; saved raw/adjusted and constant-side controls.',
        periods='2025W1-18 and2026W1-8 numerical; actual-line2026W5-8 only, each week and cumulative. Separate W1-4/W5+ numeric views; no aliases counted as NFL observations.',
        selection='P1_MEAN and P1_LOWER_MEDIAN exact unrounded point/line; P2_STATISTICAL_LAW compares Over/Under mass, ties abstain. All condition on physical participation, not book nonvoid.',
        selective='P90 requires selected-side unconditional physical-panel probability >=0.90, unchanged; zero picks=N/A. No evaluated-outcome calibration/gate training.',
        topK='Per category/week/side-pool K6,10,20; chronological game-kickoff batches, fill remaining slots from that batch by selected-side probability; stable game/player/target/line ties, duplicates rejected. Kickoff features with earlier retained lines: timing-unverified diagnostics, not executable original lists.',
        role_groups='NO_PRIOR,LOW_<10,MID_10_25,HIGH_25_PLUS from earlier predicted exposure; own fit/fallback separately. P3 uses own coefficient-training rows plus shared external inputs and P1 fallback.',
        strong_controls='Exact savedLeaf H-RECENT points on common rows, saved source adjusted/raw points, alwaysOver/Under; earlier-only same-line prevalence and neutral0.5 on halfpoints. No market probabilities without prices/paired quote evidence.',
        scope='Retrospective officialQBstat membership; no pregame-roster claim. Current/revised inputs +7day availability, earlier-only weekly fit/query. Football/quote clocks distinct; earlier quote execution not authenticated.',
        multiplicity='Exposed development; no untouched confirmation. Own-pool maxima are not a frozen routing policy. Paired game/week uncertainty via existing helper; four offered weeks insufficient week clusters.',
        budgets=dict(new_fits=0,new_inference=0,new_private_derivative_bytes=0,wall_seconds=360,max_RSS_bytes=2147483648,public_bytes=16777216),
        product_qualification='Numerical tested weeks do not qualify actual-line direction, probability or Top Picks. Four offered weeks<five-week primary floor; no primary admission or release.')
    a.out.mkdir(parents=True,exist_ok=False);write(a.out/'FROZEN_SCORING_PROTOCOL.json',out)
    print(json.dumps(dict(state=out['state'],protocol_sha256=sha(a.out/'FROZEN_SCORING_PROTOCOL.json'))))

def panelmeta(rows,season,window):
    return dict(evaluation_seasons=[season],evaluation_weeks=sorted({r['week']for r in rows}),season=season,week=window,
        period='full_game',season_type='REG',statistic_period='full_game',overtime=True,history_regime='H-RECENT',
        population='RETROSPECTIVE_OFFICIAL_QB_STAT_ROWS_NOT_EXANTE_ROSTER',position='QB',horizon_id='KICKOFF_LEFT_LIMIT_SEVEN_DAY_RECONSTRUCTION',
        source_vintage=TIER,evidence='RETROSPECTIVE_RULE_REPLAY',evaluation_panel_id=VERSION+':'+str(season)+':'+str(window))

def pointview(rr,outer,season,window,method,product,scope='FULL_SYSTEM'):
    good=[r for r in rr if r['actual']is not None and r.get(product)is not None]
    m=scoring.point_metrics([r[product]for r in good],[r['actual']for r in good],rr[0]['target']if rr else outer[0]['target'])
    precision={}
    for name in ('exact_rate','abs_lt_1','abs_le_1','abs_lt_5','abs_le_5','abs_lt_10','abs_le_10'):
        if name=='exact_rate':hits=sum(r[product]==r['actual']for r in good)
        else:
            _,op,k=name.split('_');hits=sum(abs(r[product]-r['actual'])<int(k)if op=='lt'else abs(r[product]-r['actual'])<=int(k)for r in good)
        precision[name]=dict(numerator=hits,denominator=len(good),rate=hits/len(good)if good else None)
    record=dict(panelmeta(outer,season,window),**m,record_kind='forecast_evaluation_view',procedure_id=method,
        target=outer[0]['target'],product_id=product,record_id='QB-NATIVE-'+digest([method,product,season,window,scope])[:24],
        fallback_view=scope,forecast_rows=len(rr),outer_query_rows=len(outer),technical_unavailable=len(outer)-len(rr),
        fallback_rows=sum(isfallback(r)for r in rr),scored_fallback_rows=sum(isfallback(r)for r in good),
        unique_games=len({r['game_id']for r in good}),unique_players=len({r['player_id']for r in good}),
        unique_player_games=len({(r['game_id'],r['player_id'])for r in good}),precision_counts=precision,
        query_membership_sha256=digest(sorted(ident(r)for r in good)),null_reason=None if good else'NO_SUPPORTED_ROWS')
    if good and all('law'in r for r in good):
        losses=[-law(r).logpmf(r['actual'])for r in good];inf=sum(not math.isfinite(x)for x in losses)
        record.update(NLL=float(np.mean(losses))if not inf else None,infinite_NLL=inf,
                      NLL_scope='Same complete count law; not a point-derived probability')
    return record

def old_predictions(paths,wanted):
    out=[]
    for path in paths:
        source_digest=sha(path)
        with gzip.open(path,'rt')as f:
            for r in csv.DictReader(f):
                if r['target']not in('pass_cmp','pass_att')or r['position']!='QB'or r['history_regime']!='H-RECENT'or r['family']!='ordered_leaf_cdf':continue
                if r['product_id']not in('mean','lower_median'):continue
                if(r['game_id'],r['player_id'],r['target'])not in wanted:continue
                if r.get('information_policy')not in(None,'','COMMON_FEATURE_MEMORY','COMMON','common-feature-memory') and 'strict-current'in r.get('procedure_id',''):continue
                try:prediction=float(r['prediction']);actual=float(r['actual'])
                except(ValueError,TypeError):continue
                out.append(dict(game_id=r['game_id'],player_id=r['player_id'],target=r['target'],season=int(r['season']),week=int(r['week']),
                    procedure_id=r['procedure_id'],product_id=r['product_id'],prediction=prediction,actual=actual,
                    fit_cutoff=r.get('fit_cutoff'),feature_cutoff=r.get('feature_cutoff',r.get('cutoff')),fallback=r.get('fallback'),
                    source_sha256=source_digest))
    grouped=collections.defaultdict(dict)
    for r in out:
        k=key(r),r['product_id']
        if k in grouped[r['procedure_id']]and grouped[r['procedure_id']][k]!=r:raise ValueError('Ambiguous retained old point version')
        grouped[r['procedure_id']][k]=r
    return grouped

def probability_stats(rr):
    good=[r for r in rr if r['actual']is not None and r.get('probs')is not None]
    if not good:return dict(n=0,brier=None,log_loss=None,infinite_log_losses=0)
    losses=[];ll=[];confidence=[];hit=[];over=[];observed=[]
    for r in good:
        event='over'if r['actual']>r['line']else'under'if r['actual']<r['line']else'push';p=r['probs']
        losses.append(.5*sum((p[s]-int(s==event))**2 for s in ('over','under','push')))
        ll.append(-math.log(p[event])if p[event]>0 else math.inf)
        confidence.append(max(p['over'],p['under']));hit.append(None if p['over']==p['under']else float(('over'if p['over']>p['under']else'under')==event))
        over.append(p['over']);observed.append(event=='over')
    inf=sum(not math.isfinite(x)for x in ll)
    y=np.asarray(observed);ranks=rankdata(over);n1=int(y.sum());n0=len(y)-n1
    auc=(float(ranks[y].sum())-n1*(n1+1)/2)/(n1*n0)if n1 and n0 and all(r['probs']['push']==0 for r in good)else None
    reliability=[]
    for lo,hi in [(0,.5),(.5,.6),(.6,.7),(.7,.8),(.8,.9),(.9,1.0000001)]:
        ii=[i for i,v in enumerate(confidence)if lo<=v<hi and hit[i]is not None]
        reliability.append(dict(lower=lo,upper=min(hi,1),n=len(ii),mean_predicted=float(np.mean([confidence[i]for i in ii]))if ii else None,
                                correct_direction_rate=float(np.mean([hit[i]for i in ii]))if ii else None))
    return dict(n=len(good),brier=float(np.mean(losses)),log_loss=float(np.mean(ll))if not inf else None,infinite_log_losses=inf,
                over_event_AUC=auc,reliability=reliability,probability_direction_ties=sum(x is None for x in hit),conditioning='MODELED_APPEARANCE',score_contract='HALF_MULTICLASS_BRIER_OVER_UNDER_PUSH_V1')

def summary(grades,season,window,method,policy,target,cohort='ALL',rank_scope=None,K=None):
    selected=[r for r in grades if r['selected_side']];views=[]
    for side in('over','under','Combined'):
        rr=[r for r in selected if side=='Combined'or r['selected_side']==side]
        v=score_row(rr,grades,strategy=policy,target=target,cohort=cohort,side=side,K=K,rank_scope=rank_scope,
                    rank_eligible=len(grades)if K is not None else None)
        v.update(panelmeta(grades,season,window),record_id='QB-OFFER-'+digest([method,policy,target,season,window,cohort,side,rank_scope,K])[:24],
                 procedure_id=method,product_id=policy,target=target,selection_evidence='RETROSPECTIVE_RULE_REPLAY',
                 evaluation_panel_id=VERSION+':OFFER:'+str(season)+':'+str(window),unique_weeks=len({r['week']for r in rr}),
                 registered_weeks=sorted({r['week']for r in grades}),source_vintage=TIER,
                 quote_timing='Earlier retained source clocks do not establish executable quotes at kickoff; timing-unverified actual-line diagnostic.',
                 technical_unavailable=sum(r['technical_unavailable']for r in grades),fallback_rows=sum(isfallback(r)for r in rr))
        v['selection_metrics'].update(technical_unavailable=v['technical_unavailable'],admitted_rule_abstentions=sum(r['selected_side']is None and not r['technical_unavailable']for r in grades),
            abstentions_outside_selected_partition=sum(r['selected_side']is None and not r['technical_unavailable']for r in grades),
            fallback_issued=sum(isfallback(r)for r in rr),selected_week_count=len({r['week']for r in rr}),
            learned_issued=sum(not isfallback(r)for r in rr),probability_scores=probability_stats(rr),selection_pool_count=len(grades))
        views.append(v)
    check_triplet(views);return views

def score(a):
    start=time.monotonic();p=read(a.out/'FROZEN_SCORING_PROTOCOL.json')
    assert p['scoring_adapter_sha256']==sha(__file__)and p['grader_sha256']==sha(ROOT/'nfl_v2/scoring.py')
    assert read(a.wave/'RUN_RECEIPT.json')['state']=='COMPLETE'
    for rec in p['offers']:assert sha(getattr(a,'week'+str(rec['week'])))==rec['sha256']
    allrows=[r for path in sorted((a.wave/'predictions').glob('*.json.gz'))for r in read(path)['rows']]
    queries=ctx.load_inputs(a.inputs);qmap={(r['game_id'],r['player_id']):r for r in queries};history=ctx.ContextHistory(queries,8,20)
    by=collections.defaultdict(list)
    for r in allrows:by[(r['season'],r['target'],r['procedure_id'])].append(r)
    numeric=[];player=[];pairs=[];coverage=[]
    for(season,target,method),rr in sorted(by.items()):
        for window,subset in [('ALL',rr),('W1_4',[r for r in rr if r['week']<=4]),('W5_PLUS',[r for r in rr if r['week']>=5])]+[(w,[r for r in rr if r['week']==w])for w in sorted({r['week']for r in rr})]:
            for product in('mean','lower_median'):
                for scope,rows in [('FULL_SYSTEM',subset),('LEARNED',[r for r in subset if not isfallback(r)]),('FALLBACK',[r for r in subset if isfallback(r)])]:
                    numeric.append(pointview(rows,subset,season,window,method,product,scope))
        for pid in sorted({r['player_id']for r in rr}):
            own=[r for r in rr if r['player_id']==pid and r['actual']is not None]
            for product in('mean','lower_median'):
                m=scoring.point_metrics([r[product]for r in own],[r['actual']for r in own],target)
                player.append(dict(season=season,procedure_id=method,target=target,player_id=pid,product=product,**m,
                    games=len(own),fallback=sum(isfallback(r)for r in own),weeks=sorted({r['week']for r in own}),sample_limit='One/few appearances do not establish a player-specific winner.'))
    # Paired controlled numerical changes; no hindsight routing.
    for season in(2025,2026):
        for am,bm,label in [('E1','E0','OWN_CONTEXT'),('E2','E1','OPPONENT_MAIN'),('E3','E2','REGISTERED_INTERACTIONS'),('P2','P1','PARTIAL_POOLING'),('P3','P1','OWN_ONLY_COEFFICIENTS_WITH_SHARED_FALLBACK'),('P1','E2','SAME_CONTEXT_STRUCTURED_VS_DIRECT')]:
            aa=by[season,'pass_cmp',ctx.VERSION+':'+am];bb={key(r):r for r in by[season,'pass_cmp',ctx.VERSION+':'+bm]}
            for product in('mean','lower_median'):
                for scope in('FULL_SYSTEM','COMMON_LEARNED'):
                    same=[(r,bb[key(r)])for r in aa if r['actual']is not None and key(r)in bb and(scope=='FULL_SYSTEM'or not isfallback(r)and not isfallback(bb[key(r)]))]
                    z=paired_losses([abs(r[product]-r['actual'])for r,s in same],[abs(s[product]-s['actual'])for r,s in same],[(r['season'],r['week'])for r,s in same],[r['game_id']for r,s in same])
                    pairs.append(dict(kind='NUMERICAL_PAIRED_MAE',season=season,target='pass_cmp',candidate=am,control=bm,contrast=label,product=product,scope=scope,**z))
    import importlib.util
    spec=importlib.util.spec_from_file_location('retained_qb_offer_inventory',BASE/'independent/inventory_retained_qb_offers_v1.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    offers=[dict(r)for w in range(5,9)for r in mod.iter_offers(getattr(a,'week'+str(w)),w)]
    if len(offers)!=224 or len({(key(r),str(r['line']))for r in offers})!=224:raise ValueError('Offer universe/duplicate changed')
    indexed={(r['procedure_id'],key(r)):r for r in allrows}
    old=old_predictions(a.old_predictions,{key(r)for r in allrows})if a.old_predictions else{}
    methods=sorted({r['procedure_id']for r in allrows})+['SAVED_ADJUSTED','SAVED_RAW','ALWAYS_OVER','ALWAYS_UNDER','EARLIER_LINE_PREVALENCE','NEUTRAL_HALFPOINT']
    oldids=[]
    for proc,entries in old.items():
        for product in('mean','lower_median'):
            if any(k[1]==product for k in entries):oldids.append((proc+'::SAVED_'+product,proc,product));methods.append(oldids[-1][0])
    oldlookup={name:(proc,product)for name,proc,product in oldids}
    policyrows={};probviews=[];offer_scores=[];commitments=[]
    for target in('pass_cmp','pass_att'):
        board=[r for r in offers if r['target']==target]
        for method in methods:
            if method.startswith(ctx.VERSION)and not any((method,key(r))in indexed for r in board):continue
            policies=['P1_MEAN','P1_LOWER_MEDIAN','P2_STATISTICAL_LAW','P90']if method.startswith(ctx.VERSION)else['REGISTERED_DIRECTION']
            for policy in policies:
                gg=[]
                for ix,r in enumerate(board):
                    q=qmap[r['game_id'],r['player_id']];pred=indexed.get((method,key(r)));point=None;probs=None;fallback='none';sd=None
                    if pred:
                        if pred['actual']!=r['actual']:raise ValueError('New forecast/offer label mismatch')
                        point=pred['mean'if policy=='P1_MEAN'else'lower_median'];probs=ctx.exact_probabilities(law(pred),r['line']);fallback=pred['fallback']
                        sd=sidepoint(point,r['line'])if policy.startswith('P1_')else'over'if probs['over']>probs['under']else'under'if probs['under']>probs['over']else None
                        if policy=='P90'and(sd is None or probs[sd]<.90):sd=None
                    elif method in oldlookup:
                        proc,product=oldlookup[method];saved=old[proc].get((key(r),product))
                        if saved:
                            if saved['actual']!=r['actual']:raise ValueError('Retained control label mismatch')
                            point=saved['prediction'];sd=sidepoint(point,r['line']);fallback=saved['fallback']
                    elif method in('SAVED_ADJUSTED','SAVED_RAW'):
                        point=r.get('prediction'if method=='SAVED_ADJUSTED'else'raw_prediction');sd=sidepoint(point,r['line'])
                    elif method in('ALWAYS_OVER','ALWAYS_UNDER'):sd='over'if method=='ALWAYS_OVER'else'under'
                    elif method=='NEUTRAL_HALFPOINT':
                        if float(r['line'])%1==.5:probs=dict(over=.5,under=.5,push=0.)
                    elif method=='EARLIER_LINE_PREVALENCE':
                        earlier=history.eligible(q['kickoff'],q['season']-1);yy=[x['official_completions'if target=='pass_cmp'else'official_attempts']for x in earlier]
                        whole=float(r['line']).is_integer();den=len(yy)+(3 if whole else 2)
                        probs=dict(over=(sum(y>r['line']for y in yy)+1)/den,under=(sum(y<r['line']for y in yy)+1)/den,push=(sum(y==r['line']for y in yy)+1)/den if whole else 0.)
                        sd='over'if probs['over']>probs['under']else'under'if probs['under']>probs['over']else None
                    available=pred is not None or point is not None or sd is not None or probs is not None
                    if probs and not math.isclose(sum(probs.values()),1,abs_tol=1e-10):raise ValueError('Probability complement')
                    state='ABSTAIN'if sd is None else scoring.threshold_crossing(r['actual'],r['line'],sd,target=target)
                    # All224 qualified physical labels are verified independently; no zero filling here.
                    g=dict(r,source_row_index=ix,selected_side=sd,statistical_state=state,settlement_state='UNRESOLVED_CONTRACT',net_return=None,
                        strategy=policy,ranking_point=point,technical_unavailable=not available,probs=probs,fallback=fallback,
                        pregame_role_band=pred['pregame_role_band']if pred else'CONTROL_SCOPE',source_cohorts=[],forecast_method=method)
                    gg.append(g)
                policyrows[target,method,policy]=gg
                for window,subset in [('ALL',gg)]+[(w,[r for r in gg if r['week']==w])for w in range(5,9)]:
                    scopes=[('ALL',subset),('LEARNED',[r for r in subset if not isfallback(r)]),('FALLBACK',[r for r in subset if isfallback(r)])]
                    if window=='ALL':scopes += [('ROLE:'+band,[r for r in subset if r['pregame_role_band']==band])for band in('NO_PRIOR','LOW_<10','MID_10_25','HIGH_25_PLUS')]
                    for cohort,sub in scopes:
                        if not sub:continue
                        offer_scores+=summary(sub,2026,window,method,policy,target,cohort)
                    if policy in('P2_STATISTICAL_LAW','REGISTERED_DIRECTION')and any(r['probs']for r in subset):
                        z=probability_stats(subset);z.update(panelmeta(subset,2026,window),record_kind='prop_threshold_probability_evaluation',target=target,procedure_id=method,
                            product_id='EXACT_LINE_OVER_UNDER_PUSH',record_id='QB-PROB-'+digest([method,target,window])[:24],forecast_rows=z['n'],
                            outer_offer_rows=len(subset),unique_games=len({r['game_id']for r in subset if r['probs']}),
                            probability_conditioning='MODELED_APPEARANCE',probability_score_contract='HALF_MULTICLASS_BRIER_OVER_UNDER_PUSH_V1',
                            mae=None,mse=None,evidence=TIER)
                        probviews.append(z)
                if policy=='P2_STATISTICAL_LAW':
                    for w in range(5,9):
                        weekly=[r for r in gg if r['week']==w]
                        for poolside in('Combined','over','under'):
                            for K in(6,10,20):
                                selected=[];slots=K
                                batches=sorted({r['kickoff']for r in weekly})
                                for batch in batches:
                                    eligible=[r for r in weekly if r['kickoff']==batch and r['selected_side']and(poolside=='Combined'or r['selected_side']==poolside)]
                                    eligible.sort(key=lambda r:(-r['probs'][r['selected_side']],r['game_id'],r['player_id'],str(r['line'])))
                                    add=eligible[:slots];selected+=add;slots-=len(add)
                                selectedids={r['source_row_index']for r in selected};ranked=[dict(r,selected_side=r['selected_side']if r['source_row_index']in selectedids else None,statistical_state=r['statistical_state']if r['source_row_index']in selectedids else'ABSTAIN')for r in weekly]
                                offer_scores+=summary(ranked,2026,w,method,'ROLLING_TOP_K_DIAGNOSTIC',target,rank_scope=poolside,K=K)
                commitments.append(dict(target=target,procedure_id=method,policy=policy,rows=len(gg),row_calculations_sha256=digest([{k:r.get(k)for k in('game_id','player_id','target','line','selected_side','actual','statistical_state','probs','fallback')}for r in gg]),restricted_rows_published=False))
    # Same eligible masks: every model versus saved/simple controls and E-stage pair.
    for(target,method,policy),gg in policyrows.items():
        if not method.startswith(ctx.VERSION):continue
        controls=[(m,p)for t,m,p in policyrows if t==target and not m.startswith(ctx.VERSION)]
        arm=method.rsplit(':',1)[-1];prev={'E1':'E0','E2':'E1','E3':'E2','P2':'P1','P3':'P1','P1':'E2'}.get(arm)
        if prev:controls.append((ctx.VERSION+':'+prev,policy))
        for cm,cp in controls:
            controlsby={key(r):r for r in policyrows[target,cm,cp]}
            for window in ['ALL',5,6,7,8]:
                same=[(r,controlsby[key(r)])for r in gg if(window=='ALL'or r['week']==window)and r['statistical_state']in('WIN','LOSS')and controlsby[key(r)]['statistical_state']in('WIN','LOSS')]
                if not same:continue
                z=paired_losses([float(r['statistical_state']=='LOSS')for r,s in same],[float(s['statistical_state']=='LOSS')for r,s in same],[(2026,r['week'])for r,s in same],[r['game_id']for r,s in same])
                pairs.append(dict(kind='OFFER_DIRECTION_PAIRED_LOSS',season=2026,window=window,target=target,candidate=method,policy=policy,control=cm,control_policy=cp,
                    candidate_wins=sum(r['statistical_state']=='WIN'for r,s in same),control_wins=sum(s['statistical_state']=='WIN'for r,s in same),
                    membership_sha256=digest(sorted(ident(r)for r,s in same)),scope='COMMON_DECIDED_SELECTED_POOL_NOT_FULLBOARD',**z))
    equal=[]
    for(season,target,method),rr in sorted(by.items()):
        for product in('mean','lower_median'):
            pp=[r for r in player if r['season']==season and r['target']==target and r['procedure_id']==method and r['product']==product and r['n']]
            equal.append(dict(season=season,target=target,procedure_id=method,product=product,players=len(pp),equal_player_MAE=float(np.mean([r['mae']for r in pp]))if pp else None,
                opportunity_weighted_MAE=sum(r['mae']*r['n']for r in pp)/sum(r['n']for r in pp)if pp else None,definition='Each supported player receives equal weight versus each supported player-game. Same declared year; not pooled years.'))
    write(a.out/'SCORES.json',numeric+offer_scores+probviews);write(a.out/'PAIRED_COMPARISONS.json',pairs)
    write(a.out/'PER_PLAYER_NUMERICAL.json',player);write(a.out/'EQUAL_PLAYER_SUMMARIES.json',equal)
    write(a.out/'OWNER_LOCAL_CALCULATION_COMMITMENTS.json',commitments)
    write(a.out/'RUN_RECEIPT.json',dict(state='COMPLETE_NAMED_QB_WAVE_LOCAL_NOT_C_ADMITTED',completed_utc=now(),forecast_records=len(allrows),numerical_views=len(numeric),
        actual_offer_rows=len(offers),actual_offer_weeks=[5,6,7,8],offer_views=len(offer_scores),probability_views=len(probviews),paired_views=len(pairs),
        no_private_row_export=True,new_fits=0,new_original_issuance=0,wall_seconds=time.monotonic()-start,RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
        numerical_years=[2025,2026],missing_current_actual_line_weeks=[1,2,3,4],missing_older_actual_line_years=[2022,2023,2024,2025],
        qualification='Four actual-offer weeks; new direction/probability/ranking primary products NOT_FIVE_WEEK_QUALIFIED; numerical products assessed separately.',
        price_ev_roi_clv='UNAVAILABLE_NO_QUALIFIED_PRICES_OR_VENUE_SETTLEMENT',TARGET_90_STATUS='TARGET_NOT_ESTABLISHED_UNTIL_SCOPED_COUNTS_AND_DEPENDENCE_ARE_REVIEWED'))
    print(json.dumps(read(a.out/'RUN_RECEIPT.json')))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('action',choices=['prepare','score']);ap.add_argument('--wave',type=Path,required=True);ap.add_argument('--inputs',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    for w in range(5,9):ap.add_argument('--week'+str(w),type=Path,required=True)
    ap.add_argument('--old-predictions',type=Path,action='append',default=[]);a=ap.parse_args()
    if a.action=='prepare':prepare(a)
    else:score(a)
if __name__=='__main__':main()
