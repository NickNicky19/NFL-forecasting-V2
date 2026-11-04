"""Independent paired winner/next-distinct-score audit of verified retained rows."""
import argparse,collections,gzip,hashlib,json,math
from pathlib import Path


def read(p):return json.loads(gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def run(private,public,out):
    rows=collections.defaultdict(dict);scores=[];bindings=[]
    for folder,filename in [('continuation-20261103-v2','B_OWNER_LOCAL_C_MATCHED_ROWS_V2.json.gz'),('continuation-20261103-v3','B_OWNER_LOCAL_C_ADDITIONAL_ROWS_V3.json.gz'),('continuation-20261103-v4','B_OWNER_LOCAL_C_GLM_LAW_ROWS_V4.json.gz')]:
        file=private/filename;manifest=read(public/folder/'PRIVATE_DERIVATIVE_MANIFEST.json');assert sha(file)==manifest['sha256'];bindings.append(dict(safe_id=manifest['safe_id'],sha256=manifest['sha256']))
        for r in read(file)['rows']:
            k=r['method_key'],r['target'];assert r['offer_id'] not in rows[k];rows[k][r['offer_id']]=r
        for s in read(public/folder/'SCORES.json'):
            if s['record_kind']=='prop_selection_evaluation' and s['week']=='ALL' and s['side']=='Combined':scores.append(s)
    pairs=read(public/'continuation-20261103-v4/B_MATCHED_WINNER_NEXT_DISTINCT_SCORE_COMPARISONS.json');assert len(pairs)==4;findings=[]
    for p in pairs:
        target=p['target'];eligible=[s for s in scores if s['target']==target and s['n']]
        best=max(s['selection_metrics']['hit_rate'] for s in eligible);top=[s for s in eligible if s['selection_metrics']['hit_rate']==best]
        assert sorted(s['procedure_id'] for s in top)==sorted(p['all_top_ties']) and p['procedure_id'] in p['all_top_ties']
        next_score=max(s['selection_metrics']['hit_rate'] for s in eligible if s['selection_metrics']['hit_rate']<best)
        control_score=next(s for s in eligible if s['procedure_id']==p['control_id']);assert control_score['selection_metrics']['hit_rate']==next_score
        a,b=rows[p['procedure_id'],target],rows[p['control_id'],target];keys=sorted(set(a)&set(b));common=[(a[k],b[k]) for k in keys if a[k]['statistical_state'] in ('WIN','LOSS') and b[k]['statistical_state'] in ('WIN','LOSS')]
        n=len(common);aw=sum(a['statistical_state']=='WIN' for a,b in common);bw=sum(b['statistical_state']=='WIN' for a,b in common);disagreements=sum(a['selected_side']!=b['selected_side'] for a,b in common)
        assert (n,aw,bw,aw-bw,disagreements)==(p['common_decided'],p['candidate_wins'],p['control_wins'],p['win_difference'],p['disagreements'])
        games=collections.defaultdict(list);weeks=collections.defaultdict(list)
        for a,b in common:
            assert all(a[k]==b[k] for k in ('game_id','player_id','target','actual','line','decision_time','evidence_tier'))
            delta=int(a['statistical_state']=='LOSS')-int(b['statistical_state']=='LOSS');games[a['game_id']].append(delta);weeks[a['week']].append(delta)
        delta=sum(map(sum,games.values()))/n;g=len(games);se=math.sqrt(g/(g-1)*sum((sum(v)-len(v)*delta)**2 for v in games.values()))/n;interval=[delta-1.96*se,delta+1.96*se];u=p['uncertainty']
        assert u['delta']==delta and abs(u['game_cluster_sensitivity_se']-se)<1e-13 and all(abs(a-b)<1e-13 for a,b in zip(interval,u['game_normal95_sensitivity']))
        assert u['n']==n and u['game_clusters']==g and u['week_clusters']==len(weeks) and u['week_interval'] is None
        assert all(u['weekly_paired_sums_counts'][str(k)]==dict(loss_difference_sum=float(sum(v)),n=len(v)) for k,v in weeks.items())
        findings.append(dict(target=target,candidate=p['procedure_id'],control=p['control_id'],common_decided=n,candidate_wins=aw,control_wins=bw,extra_candidate_wins=aw-bw,candidate_win_rate_change=(aw-bw)/n,disagreements=disagreements,game_clusters=g,week_clusters=len(weeks),game_cluster_normal95_win_rate_sensitivity=[-interval[1],-interval[0]],week_interval=None,next_distinct_score_and_all_top_ties_verified=True))
    receipt=dict(state='PASS',source_bindings=bindings,comparison_source_sha256=sha(public/'continuation-20261103-v4/B_MATCHED_WINNER_NEXT_DISTINCT_SCORE_COMPARISONS.json'),pairs_verified=4,findings=findings,limitations=['Own-pool descriptive maxima and next distinct observed score; not a chronological selection policy.','Cluster sensitivity intervals are not selection/multiplicity-adjusted; two weeks do not support a week interval.','Receiving-yard gain is1win against next strongest distinct Bscore, not12;12is the separate Cdirect comparison.','No new fits, predictions, scorer invocation or production changes.'])
    out.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('private',type=Path);p.add_argument('public',type=Path);p.add_argument('out',type=Path);a=p.parse_args();run(a.private,a.public,a.out)
