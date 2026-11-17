"""Independent saved-row supplementary arithmetic; no producer/scorer/fit imports."""
import argparse, collections, gzip, hashlib, json, math
from datetime import datetime, timezone
from pathlib import Path

def read(p):
    b=p.read_bytes();return json.loads(gzip.decompress(b) if p.suffix=='.gz' else b)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def close(a,b):
    if b=='Infinity':b=math.inf
    return a==b or (a is not None and b is not None and abs(a-b)<1e-10)
def view(rows,w):return [r for r in rows if str(w)=='ALL' or r['week']==int(w)]
def state(r):
    if r['probabilities'] is None:return 'UNAVAILABLE_FORECAST'
    if r['selected_side'] is None:return 'ABSTAIN'
    if r['participation']!='VERIFIED_PLAYED_POSITIVE_PHYSICAL':return 'UNKNOWN_PARTICIPATION'
    if r['actual'] is None:return 'MISSING_ACTUAL'
    return 'PUSH' if r['actual']==r['line'] else 'WIN' if ((r['actual']>r['line'])==(r['selected_side']=='over')) else 'LOSS'
def loss(r):
    event='over' if r['actual']>r['line'] else 'under' if r['actual']<r['line'] else 'push'
    return .5*math.fsum((r['probabilities'][k]-int(k==event))**2 for k in ('over','under','push'))
def proper(rows):
    rr=[r for r in rows if r['probabilities'] is not None and r['actual'] is not None and r['participation']=='VERIFIED_PLAYED_POSITIVE_PHYSICAL']
    ll=[]
    for r in rr:
        e='over' if r['actual']>r['line'] else 'under' if r['actual']<r['line'] else 'push';p=r['probabilities'][e];ll.append(-math.log(p) if p else math.inf)
    return dict(n=len(rr),brier=math.fsum(map(loss,rr))/len(rr) if rr else None,log_loss=math.fsum(ll)/len(rr) if rr else None,infinite_log_losses=sum(math.isinf(x) for x in ll))
def check_proper(expect,actual):
    for k in ('n','brier','log_loss','infinite_log_losses'):assert close(expect[k],actual[k]),(k,expect[k],actual[k])
def check_selection(pool,s):
    selected=[r for r in pool if r['selected_side'] and (s['side']=='Combined' or r['selected_side']==s['side'])]
    c=collections.Counter(state(r) for r in selected);m=s['selection_metrics'];n=c['WIN']+c['LOSS']
    assert (s['forecast_rows'],s['n'],m['WIN'],m['LOSS'],m['PUSH'])==(len(selected),n,c['WIN'],c['LOSS'],c['PUSH'])
    assert m['selection_pool_count']==len(pool) and close(m['selection_coverage'],len(selected)/len(pool) if pool else None)
    assert close(m['hit_rate'],c['WIN']/n if n else None)
    assert m['technical_unavailable']==sum(state(r)=='UNAVAILABLE_FORECAST' for r in pool)
    assert m['admitted_rule_abstentions']==sum(state(r)=='ABSTAIN' for r in pool)
    for k,v in m['status_counts'].items():assert v==c[k],(k,v,c[k])
    check_proper(proper(selected),m['probability_scores'])
    assert s['unique_games']==len({r['game_id'] for r in selected}) and s['unique_player_games']==len({(r['game_id'],r['player_id']) for r in selected})
    return selected
def run(repo,private,evidence,out):
    binding=read(out/'CURRENT_EXECUTION_BINDING.json');data=read(private/binding['inputs']);payload=read(private/'CALIBRATOR_MODELS_AND_ROWS.json.gz');rows=payload['rows'];source=read(out/'SCORES.json')
    names=['MATCHED_SELECTED_CONTROL_SCORES','REFERENCE_PROBABILITY_SCORES','COMMON_COHORT_SCORES','COHORT_MEMBERSHIP_MANIFEST','PAIRED_PROBABILITY_ANALYSIS','OWN_POOL_CHANGE_SENSITIVITY','ANCILLARY_POINT_SCORES','TARGET_90_STATUS','INDEX_REPORTING_ANNOTATIONS']
    docs={n:read(out/(n+'.json')) for n in names};allrows={(t,a,p):[r for r in rows if r['target']==t and r['method_key'].endswith('::B'+str(a)) and r['selection_policy']==p] for t in ('rec','pass_td') for a in (0,1) for p in ('ALL','B2_MATCHED_EARLIER_CONFIDENCE','CONF_0.90')}
    priors={t:{r['offer_id']:r for r in data[t]['prior']} for t in ('rec','pass_td')};matched={};summaries=[]
    for s in docs['MATCHED_SELECTED_CONTROL_SCORES']:
        t=s['target'];a=int(s['parent_arm'][-1]);p=s['parent_policy'];parent=view(allrows[t,a,p],s['week']);selected=[r for r in parent if r['selected_side']];ids=sorted(r['offer_id'] for r in selected)
        assert s['parent_selected']==len(selected) and s['parent_source_eligible']==len(parent) and digest(ids)==s['parent_selected_membership_sha256']
        rr=[]
        for r in selected:
            if s['strategy']=='EARLIER_SOURCE_PRIOR':
                pp=priors[t][r['offer_id']]['probabilities'];side=None if pp is None or pp['over']==pp['under'] else 'over' if pp['over']>pp['under'] else 'under'
            else:pp=dict(over=.5,under=.5,push=0.);side='over' if s['strategy']=='ALWAYS_OVER' else 'under'
            rr.append(dict(r,probabilities=pp,selected_side=side,prediction=None))
        check_selection(rr,s);assert s['mae'] is None and s['bias'] is None
        key=t,a,p,str(s['week']),s['strategy'];matched[key]=rr
        if s['side']=='Combined' and str(s['week']) in ('ALL','8') and p=='B2_MATCHED_EARLIER_CONFIDENCE':summaries.append(dict(target=t,arm=a,control=s['strategy'],parent_policy=p,selected=s['forecast_rows'],wins=s['selection_metrics']['WIN'],losses=s['selection_metrics']['LOSS'],decided=s['n']))
    for s in docs['REFERENCE_PROBABILITY_SCORES']:
        a=int(s['procedure_id'].split('PARENT_B')[1][0]);p=s['procedure_id'].split('::')[-1];c=s['procedure_id'].split('MATCHED_')[1].split('::')[0];rr=matched[s['target'],a,p,str(s['week']),c]
        check_proper(proper(rr),s);assert s['forecast_rows']==len(rr)
        if c.startswith('ALWAYS_') and s['n']:assert s['brier']==.25 and close(s['log_loss'],math.log(2)) and all(r['line']%1==.5 for r in rr)
    # Membership is frozen before the respective decisions and independent of B0/B1 choice/outcome.
    hp=evidence/'pregame-cohort-scorecards-v2/memberships.json.gz';fp=evidence/'pregame-cohort-scorecards-v2/future-memberships.json.gz';profiles={}
    for f in (hp,fp):
        for m in read(f):
            g,p,t,pop=m['key']
            if t in ('rec','pass_td') and pop in ('primary','frozen_exante_feed'):
                assert (g,p,t) not in profiles;profiles[g,p,t]=m
    tags={};census={};timing=collections.Counter()
    for t in ('rec','pass_td'):
        tags[t]={};census[t]=collections.Counter()
        for r in allrows[t,1,'ALL']:
            tt={'role_'+r['position']};m=profiles.get((r['game_id'],r['player_id'],t))
            if r['probabilities'] is not None and r['repair_state']=='FITTED_GAME_WEIGHTED_INTERCEPT_MAP':tt.add('ACTIVE_REPAIR_COMMON')
            if r['probabilities'] is not None and r['fallback'] in ('none',False):tt.add('BASE_LEARNED_COMMON')
            if m is None or m['ranking_cutoff']>r['decision_epoch']:
                tt.add('membership_unavailable');census[t]['missing' if m is None else 'cutoff_later_than_decision']+=1
            else:
                assert m['latest_available'] is None or m['latest_available']<m['ranking_cutoff']<=r['decision_epoch'];census[t]['matched']+=1;timing[t]+=1
                rank=m['rank'];expected={'all'}
                if rank is None:expected.add('unranked')
                else:
                    expected.update('top'+str(k) for k in (10,15,20) if rank<=k);expected.add('rank1_10' if rank<=10 else 'rank11_15' if rank<=15 else 'rank16_20' if rank<=20 else 'rank21plus')
                v=m['mean'];low,high=(20,35) if t=='pass_td' else (3,7);band='unknown' if v is None else 'zero' if v==0 else 'low' if v<=low else 'middle' if v<=high else 'high';expected.add('workload_'+band);assert set(m['cohorts'])==expected
                assert m['history_slots']<=3 and m['supported_slots']<=m['history_slots'];tt.update(expected)
            tags[t][r['offer_id']]=tt
    memberships={}
    for m in docs['COHORT_MEMBERSHIP_MANIFEST']:
        t=m['target'];c=m['cohort_id']
        if c=='SOURCE_MEMBERSHIP_CENSUS':assert {k:v for k,v in m.items() if k not in ('target','cohort_id')}==dict(census[t]);continue
        ids=sorted(k for k,tt in tags[t].items() if c in tt);assert len(ids)==m['n'] and digest(ids)==m['membership_sha256'];assert m['historical_membership_sha256']==sha(hp) and m['future_membership_sha256']==sha(fp);memberships[t,c]=ids
    cohort_pair_masks={}
    for s in docs['COMMON_COHORT_SCORES']:
        t=s['target'];c=s['cohort_id'];a=int(s['procedure_id'][-1]);lookup={r['offer_id']:r for r in allrows[t,a,'ALL']};rr=view([lookup[i] for i in memberships[t,c]],s['week']);check_selection(rr,s);assert digest([r['offer_id'] for r in rr])==s['cohort_membership_sha256']
        cohort_pair_masks[t,c,str(s['week']),a]=sorted(r['offer_id'] for r in rr)
    for (t,c,w,a),ids in cohort_pair_masks.items():assert ids==cohort_pair_masks[t,c,w,1-a]
    for s in docs['PAIRED_PROBABILITY_ANALYSIS']:
        t=s['target'];aa={r['offer_id']:r for r in view(allrows[t,1,'ALL'],s['week'])};bb={r['offer_id']:r for r in view(allrows[t,0,'ALL'],s['week'])};ids=sorted(k for k in aa.keys()&bb.keys() if all(r['probabilities'] is not None and r['actual'] is not None and r['participation']=='VERIFIED_PLAYED_POSITIVE_PHYSICAL' for r in (aa[k],bb[k])))
        assert len(ids)==s['n'] and digest(ids)==s['membership_sha256'];diff={k:loss(aa[k])-loss(bb[k]) for k in ids};delta=math.fsum(diff.values())/len(ids);u=s['uncertainty'];assert close(delta,u['delta']) and close(math.fsum(loss(aa[k]) for k in ids)/len(ids),u['candidate_error']) and close(math.fsum(loss(bb[k]) for k in ids)/len(ids),u['comparator_error'])
        games=collections.defaultdict(list)
        for k in ids:games[aa[k]['game_id']].append(diff[k])
        se=math.sqrt(len(games)/(len(games)-1)*math.fsum((math.fsum(v)-len(v)*delta)**2 for v in games.values()))/len(ids);assert close(se,u['game_cluster_sensitivity_se']) and u['week_interval'] is None and u['week_interval_status']=='INSUFFICIENT_WEEK_CLUSTERS'
    for s in docs['OWN_POOL_CHANGE_SENSITIVITY']:
        t=s['target'];p=s['policy'];pools={a:[r for r in view(allrows[t,a,p],s['week']) if state(r) in ('WIN','LOSS')] for a in (0,1)};nn={a:len(rr) for a,rr in pools.items()};ww={a:sum(state(r)=='WIN' for r in rr) for a,rr in pools.items()};rates={a:ww[a]/nn[a] if nn[a] else None for a in (0,1)};delta=rates[1]-rates[0] if all(nn.values()) else None
        assert (nn[0],ww[0],nn[1],ww[1])==(s['raw_n'],s['raw_wins'],s['repaired_n'],s['repaired_wins']) and close(delta,s['hit_rate_change'])
        games=sorted({r['game_id'] for r in view(data[t]['evaluation'],s['week'])});assert len(games)==s['game_clusters']
        se=None
        if delta is not None:
            influence=[math.fsum(int(state(r)=='WIN')-rates[1] for r in pools[1] if r['game_id']==g)/nn[1]-math.fsum(int(state(r)=='WIN')-rates[0] for r in pools[0] if r['game_id']==g)/nn[0] for g in games];se=math.sqrt(len(games)/(len(games)-1)*math.fsum(x*x for x in influence))
        assert close(se,s['game_sensitivity_se'])
    r=docs['ANCILLARY_POINT_SCORES'][0];rr=[q for q in allrows['pass_td',0,'ALL'] if q['prediction'] is not None and q['actual'] is not None and q['participation']=='VERIFIED_PLAYED_POSITIVE_PHYSICAL'];err=[q['prediction']-q['actual'] for q in rr];ae=sorted(map(abs,err));assert len(rr)==r['n']==26 and r['unavailable_forecasts']==2
    assert close(math.fsum(ae)/len(ae),r['mae']) and close(math.fsum(e*e for e in err)/len(err),r['mse']) and close(math.fsum(err)/len(err),r['bias']) and close(math.sqrt(r['mse']),r['rmse'])
    for p in (.9,.95):
        ix=(len(ae)-1)*p;lo=math.floor(ix);q=ae[lo]+(ae[min(lo+1,len(ae)-1)]-ae[lo])*(ix-lo);assert close(q,r['p'+str(int(p*100))+'_abs'])
    assert r['max_abs']==ae[-1] and 'original_mean' in r['product_id'] and r['unchanged_in_B1']
    for name,c in r['precision_counts'].items():
        n=sum(e==0 for e in ae) if name=='exact_rate' else sum((e<=float(name[7:]) if name.startswith('abs_le_') else e<float(name[7:])) for e in ae);assert c==dict(numerator=n,denominator=len(ae))
    for s in docs['TARGET_90_STATUS']:
        rr=view(allrows[s['target'],s['arm'],'CONF_0.90'],s['week']);assert not any(r['selected_side'] for r in rr);assert (s['selected'],s['wins'],s['losses'],s['decided'],s['hit_rate'])==(0,0,0,0,None)
    annotation=docs['INDEX_REPORTING_ANNOTATIONS'];assert annotation['source_score_sha256']==sha(out/'SCORES.json') and annotation['predictions_and_selection_scores_unchanged'];byindex={r['source_row_index']:r for r in annotation['rows']};rolling=0
    for i,s in enumerate(source):
        if s['record_kind']!='prop_selection_evaluation':continue
        need=(s.get('mae') is not None or s.get('bias') is not None or s['strategy'].startswith('ROLLING_K') or bool(s['selection_metrics'].get('probability_scores',{}).get('conditioning')=='MODELED_APPEARANCE'))
        if need:assert i in byindex
        if i not in byindex:continue
        note=byindex[i];assert note['record_id']==s['record_id']
        if s.get('mae') is not None or s.get('bias') is not None:
            assert note['ancillary_point_attribution']['kind']=='ORIGINAL_B0_MEAN_REFERENCE_NOT_THIS_EVENT_PRODUCT'
            assert note['ancillary_point_attribution']['original_metrics']=={k:s.get(k) for k in ('mae','mse','rmse','bias','p90_abs','p95_abs','max_abs')}
        if s['strategy'].startswith('ROLLING_K'):
            k,side=s['strategy'].split('_')[1:];assert note['registered_rolling_rank']==dict(K=int(k[1:]),side_pool=side,rank_scope='PER_CATEGORY_PER_WEEK_ROLLING_DECISION_BATCHES');rolling+=1
    result=dict(state='PASS_WITH_EXPLICIT_SCOPE_AND_RESOURCE_LIMITATIONS',at_utc=datetime.now(timezone.utc).isoformat(),verification_code_sha256=sha(Path(__file__)),source_scores_sha256=sha(out/'SCORES.json'),source_rows_sha256=sha(private/'CALIBRATOR_MODELS_AND_ROWS.json.gz'),supplement_code_sha256=sha(repo/'tools/supplement_b_predictive_improvement_01.py'),artifact_sha256={n:sha(out/(n+'.json')) for n in names},selected_control_views_verified=len(docs[names[0]]),reference_probability_views_verified=len(docs[names[1]]),cohort_side_views_verified=len(docs[names[2]]),cohort_manifest_rows_verified=len(docs[names[3]]),paired_probability_contrasts_verified=4,own_pool_contrasts_verified=12,ancillary_numeric_views_verified=1,target90_views_verified=8,typed_rolling_K_annotations_verified=rolling,temporal_cohort_matches=dict(timing),same_B0_B1_cohort_memberships=True,matched_B2_control_summary=summaries,new_fits=0,new_inference=0,new_NFL_observations=0,limits=['Declared two-thread fitting limit was not explicitly enforced in the executed six scalar fits; BLAS pool configuration five, active fitting threads unrecorded. Approximately equal CPU/wall time does not authenticate the cap. This is disclosed resource nonconformance and future hardening, not a reason to silently rerun or alter results.','Frozen earlier-opportunity cohort membership does not authenticate an ex-ante full population; historical participant and original future-query universes remain distinct. Top-player cohorts are not top-ranked picks.','Rec law inputs are single actual-line events; complete direct CDF and nontrivial cross-line coherence are unestablished. PT historical-to-original-capture transfer and current-revised source limits remain.','PT ancillary mean belongs to unchanged original B0 C02, not repaired-law or constant/prior controls.','All confidence90 pools are empty; hit rate N/A and target unestablished. All probability/selection differences are exposed, descriptive, few-week comparisons without fresh validation or profitability evidence.'])
    (out/'INDEPENDENT_SUPPLEMENT_CONTROLS_COHORTS_AND_TYPING_V1.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('repo',type=Path);p.add_argument('private',type=Path);p.add_argument('evidence',type=Path);p.add_argument('out',type=Path);a=p.parse_args();run(a.repo,a.private,a.evidence,a.out)
