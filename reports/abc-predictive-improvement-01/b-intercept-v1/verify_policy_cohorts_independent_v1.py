"""Independent original-policy/subgroup partition; no producer/scorer imports."""
import argparse,collections,gzip,hashlib,json,math
from datetime import datetime,timezone
from pathlib import Path
def load(p):
    b=p.read_bytes();return json.loads(gzip.decompress(b)if p.suffix=='.gz'else b)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def state(r):
    if r['probabilities']is None:return'UNAVAILABLE_FORECAST'
    if r['selected_side']is None:return'ABSTAIN'
    if r['participation']!='VERIFIED_PLAYED_POSITIVE_PHYSICAL':return'UNKNOWN_PARTICIPATION'
    if r['actual']is None:return'MISSING_ACTUAL'
    return'PUSH'if r['actual']==r['line']else'WIN'if((r['actual']>r['line'])==(r['selected_side']=='over'))else'LOSS'
def run(repo,private,evidence,out):
    rows=load(private/'CALIBRATOR_MODELS_AND_ROWS.json.gz')['rows'];sourcehash=sha(private/'CALIBRATOR_MODELS_AND_ROWS.json.gz');scores=load(out/'POLICY_COHORT_SCORES.json');manifest=load(out/'COHORT_MEMBERSHIP_MANIFEST.json');registration=load(out/'POLICY_COHORT_REGISTRATION.json');receipt=load(out/'POLICY_COHORT_RECEIPT.json')
    assert sourcehash==receipt['source_rows_sha256']and sha(out/'POLICY_COHORT_SCORES.json')==receipt['score_sha256'];assert registration['source_sha256']==sha(repo/'tools/extend_b_improvement_policy_cohorts.py')
    profiles={}
    for file in('memberships.json.gz','future-memberships.json.gz'):
        for m in load(evidence/'pregame-cohort-scorecards-v2'/file):
            game,player,target,pop=m['key']
            if target in('rec','pass_td')and pop in('primary','frozen_exante_feed'):
                assert(game,player,target)not in profiles;profiles[game,player,target]=m
    tags={};expected_masks={};bygroup=collections.defaultdict(list)
    for r in rows:bygroup[r['target'],int(r['method_key'][-1]),r['selection_policy']].append(r)
    for t in('rec','pass_td'):
        tags[t]={}
        for r in bygroup[t,1,'ALL']:
            label={'role_'+r['position']}
            if r['probabilities']is not None and r['repair_state']=='FITTED_GAME_WEIGHTED_INTERCEPT_MAP':label.add('ACTIVE_REPAIR_COMMON')
            if r['probabilities']is not None and r['fallback']in('none',False):label.add('BASE_LEARNED_COMMON')
            m=profiles.get((r['game_id'],r['player_id'],t))
            if m is None or m['ranking_cutoff']>r['decision_epoch']:label.add('membership_unavailable')
            else:
                assert m['latest_available']is None or m['latest_available']<m['ranking_cutoff']<=r['decision_epoch'];label.update(m['cohorts'])
            tags[t][r['offer_id']]=label
    for m in manifest:
        if m['cohort_id']=='SOURCE_MEMBERSHIP_CENSUS':continue
        t=m['target'];c=m['cohort_id'];ids=sorted(k for k,labels in tags[t].items()if c in labels);assert len(ids)==m['n']and digest(ids)==m['membership_sha256'];expected_masks[t,c]=set(ids)
    triads=collections.defaultdict(dict);policies=collections.defaultdict(set);cohorts=collections.defaultdict(set);periods=collections.defaultdict(set);kviews=0;unknown_examples=[]
    for s in scores:
        t=s['target'];arm=int(s['procedure_id'][-1]);p=s['strategy'];c=s['cohort_id'];w=str(s['week']);assert p!='ALL';policies[t,arm].add(p);cohorts[t].add(c);periods[t].add(w)
        pool=[r for r in bygroup[t,arm,p]if r['offer_id']in expected_masks[t,c]and(w=='ALL'or r['week']==int(w))]
        assert s['cohort_membership_sha256']==digest(sorted(r['offer_id']for r in pool));assert s['source_prediction_and_selection_rows_unchanged']
        assert len({r['offer_id']for r in pool})==len(pool);assert 'NEVER_RERANK_OR_REPLACE_MEMBERS'in s['cohort_scope']
        selected=[r for r in pool if r['selected_side']and(s['side']=='Combined'or r['selected_side']==s['side'])];counts=collections.Counter(state(r)for r in selected);m=s['selection_metrics'];n=counts['WIN']+counts['LOSS']
        assert(s['forecast_rows'],s['n'],m['WIN'],m['LOSS'],m['PUSH'])==(len(selected),n,counts['WIN'],counts['LOSS'],counts['PUSH']);assert m['hit_rate']==(counts['WIN']/n if n else None)
        for key,value in m['status_counts'].items():assert value==counts[key]
        assert m['selection_pool_count']==len(pool)and m['selection_coverage']==(len(selected)/len(pool)if pool else None)
        assert s['unique_games']==len({r['game_id']for r in selected})and s['unique_player_games']==len({(r['game_id'],r['player_id'])for r in selected})
        assert s['evaluation_weeks']==sorted({r['week']for r in pool})
        full=[r for r in bygroup[t,arm,'ALL']if w=='ALL'or r['week']==int(w)];assert s['full_source_offer_universe']==len(full)
        assert m['technical_unavailable']==sum(state(r)=='UNAVAILABLE_FORECAST'for r in pool)and m['admitted_rule_abstentions']==sum(state(r)=='ABSTAIN'for r in pool)
        assert m['fallback_issued']==sum(r.get('fallback')not in('none',False,None,'NOT_RETAINED')for r in pool)and m['fallback_status_unknown']==sum(r.get('fallback')=='NOT_RETAINED'for r in pool)
        assert all(s.get(k)is None for k in('mae','mse','rmse','bias','p90_abs','p95_abs','max_abs'))and s['native_metric_null_reason']=='EVENT_POLICY_HAS_NO_OWN_POINT_OUTPUT'
        assert s['probability_scope']=='NO_ADDITIONAL_COHORT_PROPER_SCORE;FULL_BOARD_AND_SELECTED_PRIMARY_SCORES_RETAINED'
        if p.startswith('ROLLING_K'):
            k,side=p.split('_')[1:];assert s['K']==int(k[1:])and s['rank_side_pool']==side and s['rank_scope']=='PER_CATEGORY_PER_WEEK_ROLLING_DECISION_BATCHES';kviews+=1
            # Subgroups condition on original picks; no replacement or filling to K.
            for week in {r['week']for r in pool}:assert sum(r['selected_side']is not None for r in pool if r['week']==week)<=int(k[1:])
        else:assert s['K']is None
        key=t,arm,p,c,w;assert s['side']not in triads[key];triads[key][s['side']]=s
        if s['side']=='Combined'and m['technical_unavailable']and c=='membership_unavailable'and p=='CONF_0.90':unknown_examples.append(dict(target=t,arm=arm,week=w,technical_unavailable=m['technical_unavailable'],fallback_unknown=m['fallback_status_unknown'],rule_abstentions=m['admitted_rule_abstentions'],selected=s['forecast_rows']))
    assert len(scores)==6720 and len(triads)==2240 and all(len(v)==14 for v in policies.values())and all(len(v)==20 for v in cohorts.values());assert periods=={'rec':{'2','3','ALL'},'pass_td':{'8'}}
    for key,v in triads.items():
        assert set(v)=={'over','under','Combined'}
        for field in('WIN','LOSS','PUSH'):
            assert v['Combined']['selection_metrics'][field]==sum(v[s]['selection_metrics'][field]for s in('over','under'))
        for field in('n','forecast_rows'):assert v['Combined'][field]==v['over'][field]+v['under'][field]
        for status,value in v['Combined']['selection_metrics']['status_counts'].items():assert value==sum(v[s]['selection_metrics']['status_counts'][status]for s in('over','under'))
        t,arm,p,c,w=key;other=triads[t,1-arm,p,c,w];assert v['Combined']['cohort_membership_sha256']==other['Combined']['cohort_membership_sha256']
    for k in('new_fits','new_forecast_inference','new_grades','new_private_bytes','new_NFL_observations','policy_or_membership_changes'):assert receipt[k]==0
    result=dict(state='PASS_INDEPENDENT_SAVED_POLICY_SUBGROUP_PARTITION',at_utc=datetime.now(timezone.utc).isoformat(),verification_code_sha256=sha(Path(__file__)),producer_code_sha256=sha(repo/'tools/extend_b_improvement_policy_cohorts.py'),source_prediction_policy_rows_sha256=sourcehash,score_sha256=receipt['score_sha256'],registration_sha256=sha(out/'POLICY_COHORT_REGISTRATION.json'),source_membership_manifest_sha256=sha(out/'COHORT_MEMBERSHIP_MANIFEST.json'),side_views_verified=len(scores),complete_side_triads_verified=len(triads),non_ALL_policies_per_arm=14,common_cohorts_per_target=20,typed_rolling_K_views_verified=kviews,actual_periods={k:sorted(v)for k,v in periods.items()},unavailable_scope_examples=unknown_examples,base_fits=0,forecast_inference=0,new_NFL_observations=0,limits=['Subgroup tables condition on unchanged original policy decisions and frozen common memberships; they do not rerank or refill top-K within cohorts.','Technical unavailability remains distinct from deliberate rule abstention; fallback unknown includes missing original forecast metadata. Empty selected and decided pools retain null rates.','Historical participant and future-query memberships do not authenticate complete original ex-ante player boards. These remain exposed descriptive subgroup views, not new independent observations.','Native error is intentionally null for event policies. Original unchanged PT mean remains only in the separate ancillary point product.','The earlier declared fitting thread cap was not demonstrably enforced; this saved-row-only supplement introduces no additional fits.'])
    (out/'INDEPENDENT_POLICY_COHORT_PARTITIONS_V1.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('repo',type=Path);p.add_argument('private',type=Path);p.add_argument('evidence',type=Path);p.add_argument('out',type=Path);a=p.parse_args();run(a.repo,a.private,a.evidence,a.out)
