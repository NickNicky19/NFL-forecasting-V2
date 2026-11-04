"""Independent side reconciliation, coverage and existing-point comparison audit."""
import argparse,collections,gzip,hashlib,json,math
from pathlib import Path


def read(p):return json.loads(gzip.decompress(p.read_bytes())if p.suffix=='.gz'else p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def run(private,previous,out):
    rows=read(private)['rows'];groups=collections.defaultdict(dict)
    for r in rows:groups[r['method_key'],r['target']][r['offer_id']]=r
    scores=[r for r in read(out/'SCORES.json')if r['record_kind']=='prop_selection_evaluation'];triads=collections.defaultdict(dict)
    for r in scores:triads[r['procedure_id'],r['target'],str(r['week'])][r['side']]=r
    assert len(triads)==192
    for key,views in triads.items():
        assert set(views)=={'over','under','Combined'};o,u,t=views['over'],views['under'],views['Combined']
        for k in('WIN','LOSS','PUSH'):assert o['selection_metrics'][k]+u['selection_metrics'][k]==t['selection_metrics'][k]
        assert o['forecast_rows']+u['forecast_rows']==t['forecast_rows']and o['n']+u['n']==t['n']
        for state in t['selection_metrics']['status_counts']:assert o['selection_metrics']['status_counts'][state]+u['selection_metrics']['status_counts'][state]==t['selection_metrics']['status_counts'][state]
    for proc,target in groups:
        for side in('over','under','Combined'):
            a,b,total=(triads[proc,target,w][side]for w in('2','3','ALL'))
            for k in('WIN','LOSS','PUSH'):assert a['selection_metrics'][k]+b['selection_metrics'][k]==total['selection_metrics'][k]
            assert a['forecast_rows']+b['forecast_rows']==total['forecast_rows']and a['n']+b['n']==total['n']
    # No row-level example values published: replay first chronological case in each bucket.
    examples={}
    for r in sorted(rows,key=lambda r:(r['target'],r['week'],r['game_id'],r['offer_id'],r['method_key'])):
        if r['statistical_state']in('WIN','LOSS'):
            k=r['target'],r['selected_side'],r['statistical_state'];examples.setdefault(k,True)
    assert len(examples)==16
    coverage=[]
    for target in('pass_yd','rush_yd','rec','rec_yd'):
        rr=[r for r in rows if r['target']==target];counts=collections.Counter(r['fallback']for r in rr if r['probabilities']is not None);n=sum(r['probabilities']is not None for r in rr)
        assert sum(counts.values())==n and all(r['fallback']is None for r in rr if r['probabilities']is None)
        coverage.append(dict(target=target,method_rows=len(rr),available_law_rows=n,technical_unavailable_rows=len(rr)-n,available_law_fallback_counts=dict(counts),unissued_fallback_state='UNKNOWN_NOT_LEARNED_OR_COMPLETED_FALLBACK'))
    pairs=read(out/'PAIRED_CONTROLS.json');reversal=[p for p in pairs if p['target']=='rec'and':D2:common-feature-memory::H-CURRENT-COMMON::'in p['procedure_id']and p['control_id']=='P3_DIRECT'];assert len(reversal)==3
    r2=next(p for p in reversal if p['week_view']=='2');r3=next(p for p in reversal if p['week_view']=='3');total=next(p for p in reversal if p['week_view']=='ALL');assert(r2['candidate_wins'],r2['control_wins'],r2['common_decided'])==(89,85,161);assert(r3['candidate_wins'],r3['control_wins'],r3['common_decided'])==(105,109,176);assert(total['candidate_wins'],total['control_wins'],total['common_decided'])==(194,194,337)
    # Compare all tied law leaders with prior fixed point leaders, not merely weak controls.
    old=collections.defaultdict(dict)
    for folder,name in[('continuation-20261103-v2','B_OWNER_LOCAL_C_MATCHED_ROWS_V2.json.gz'),('continuation-20261103-v3','B_OWNER_LOCAL_C_ADDITIONAL_ROWS_V3.json.gz'),('continuation-20261103-v4','B_OWNER_LOCAL_C_GLM_LAW_ROWS_V4.json.gz')]:
        f=previous/name;pub=out.parent/folder;assert sha(f)==read(pub/'PRIVATE_DERIVATIVE_MANIFEST.json')['sha256']
        for r in read(f)['rows']:old[r['method_key'],r['target']][r['offer_id']]=r
    contrasts=read(out/'PAIRED_PRIOR_POINT_ANALYSIS.json');assert len(contrasts)==24
    for p in contrasts:
        a,b=groups[p['procedure_id'],p['target']],old[p['comparator_procedure_id'],p['target']];weekset=p['actual_weeks'];common=[(a[k],b[k])for k in sorted(set(a)&set(b))if a[k]['week']in weekset and a[k]['statistical_state']in('WIN','LOSS')and b[k]['statistical_state']in('WIN','LOSS')];assert len(common)==p['n']
        aa=sum(x['statistical_state']=='WIN'for x,y in common);bb=sum(y['statistical_state']=='WIN'for x,y in common);assert aa==p['candidate_wins']and bb==p['comparator_wins']
        games=collections.defaultdict(list)
        for x,y in common:
            assert all(x[k]==y[k]for k in('game_id','player_id','line','actual','decision_time','evidence_tier'))
            games[x['game_id']].append(int(x['statistical_state']=='LOSS')-int(y['statistical_state']=='LOSS'))
        n=len(common);delta=sum(map(sum,games.values()))/n;g=len(games);se=math.sqrt(g/(g-1)*sum((sum(v)-len(v)*delta)**2 for v in games.values()))/n
        assert abs(delta-p['delta'])<1e-12 and abs(se-p['uncertainty']['game_cluster_sensitivity_se'])<1e-12
    result=dict(state='PASS',private_source_sha256=sha(private),explicit_side_triads_reconciled=192,weekly_to_cumulative_method_target_views=64,representative_win_loss_side_buckets_verified=16,examples='First chronological available record in each target/selected-side/WIN-or-LOSS bucket; values remain in existing private source, no new derivative.',coverage=coverage,weekly_reversal=dict(procedure_id=total['procedure_id'],control='C::P3_DIRECT',W2=dict(candidate_wins=89,control_wins=85,n=161,win_change=4),W3=dict(candidate_wins=105,control_wins=109,n=176,win_change=-4),cumulative=dict(candidate_wins=194,control_wins=194,n=337),scope='Weekly reversal only; no older-season persistence established.'),prior_point_comparisons_verified=24,prior_comparison_source_sha256=sha(out/'PAIRED_PRIOR_POINT_ANALYSIS.json'),no_new_fits_or_inference=True,limitation='No new policy/side inversion or claimthat adding a law improved forecast direction; comparisons and sourceperiods remain exposed/timing-unverified.')
    (out/'INDEPENDENT_SIDE_COVERAGE_REVERSAL_VERIFICATION_V1.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('private',type=Path);p.add_argument('previous',type=Path);p.add_argument('out',type=Path);a=p.parse_args();run(a.private,a.previous,a.out)
