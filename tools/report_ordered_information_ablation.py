"""Report fixed-control and prior-leader changes from immutable aggregate scores."""
import argparse,csv,hashlib,json,math
from pathlib import Path

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(path):return json.loads(Path(path).read_bytes())
def dump(path,value):
    with Path(path).open('x')as h:json.dump(value,h,indent=2,sort_keys=True,allow_nan=False);h.write('\n')
def full(r):return r.get('week')=='ALL'and r.get('position')=='ALL'and r.get('fallback_view','ALL')=='ALL'
def key(r):return(r['target'],r['policy_id'],r.get('population','primary'),r['product_id'])
def nll(r):return 'Infinity'if r.get('infinite_NLL',0)else r.get('NLL')

def run(public_root,control_public,chart_public,leader_csv):
    public_root,control_public,chart_public,leader_csv=map(Path,(public_root,control_public,chart_public,leader_csv));scores=load(public_root/'SCORES.json');old={};sourcebind=[]
    for path in(control_public/'SCORES.json',chart_public/'SCORES.json'):
        sourcebind.append(dict(artifact=path.as_posix(),sha256=sha(path)))
        for i,r in enumerate(load(path)):
            if full(r)and 'ordered_leaf_cdf'in r.get('procedure_id',''):old[key(r)]=(r,path.as_posix(),i)
    point=[];laws=[]
    for i,r in enumerate(scores):
        if not full(r):continue
        o,path,j=old[key(r)]
        if r['n']!=o['n']or r['unique_games']!=o['unique_games']:raise ValueError('fixedcontrolaggregatepopulationmismatch')
        metric='brier'if r['target']=='anytime_td'else'mae';comparison=r['comparison'];delta=r[metric]-o[metric]if r[metric]is not None else None
        point.append(dict(target=r['target'],policy_id=r['policy_id'],history_regime=r['history_regime'],population=r['population'],product_id=r['product_id'],n=r['n'],forecast_rows=r['forecast_rows'],fallback_rows=r['fallback_rows'],candidate_error=r[metric],ordered_control_error=o[metric],error_metric=metric,paired_error_delta=delta,relative_error_delta=delta/o[metric]if o[metric]else None,comparison_status=comparison['status'],membership_sha256=comparison.get('membership_sha256'),uncertainty=comparison.get('uncertainty'),source_row_index=i,control_artifact=path,control_source_row_index=j))
        if r['product_id']in('mean','event_probability'):
            laws.append(dict(target=r['target'],policy_id=r['policy_id'],history_regime=r['history_regime'],population=r['population'],n=r['n'],candidate_CRPS=r['CRPS'],ordered_control_CRPS=o['CRPS'],paired_CRPS_delta=r['CRPS']-o['CRPS']if r['CRPS']is not None else None,candidate_NLL=nll(r),ordered_control_NLL=nll(o),candidate_infinite_NLL=r['infinite_NLL'],ordered_control_infinite_NLL=o['infinite_NLL'],candidate_interval90_width=r['interval90_width'],ordered_control_interval90_width=o['interval90_width'],candidate_interval90_coverage=r['interval90_coverage'],ordered_control_interval90_coverage=o['interval90_coverage'],candidate_mean_zero_mass=r['mean_zero_mass'],ordered_control_mean_zero_mass=o['mean_zero_mass'],candidate_intended_mean_MSE=r['mse'],ordered_control_intended_mean_MSE=o['mse'],source_row_index=i,control_artifact=path,control_source_row_index=j))
    with leader_csv.open()as h:leaders=[r for r in csv.DictReader(h)if r['rank']=='1']
    best=[]
    for target in dict.fromkeys(r['target']for r in point):
        rows=[r for r in point if r['target']==target and r['population']=='primary'];r=min(rows,key=lambda x:x['candidate_error']);previous=[x for x in leaders if x['target']==target and x['ranking_product']=='display_point'];loss=float(previous[0]['ranking_loss']);
        if any(int(x['n'])!=r['n']or float(x['ranking_loss'])!=loss for x in previous):raise ValueError('priorleaderpanel/tiemismatch')
        best.append(dict(target=target,n=r['n'],candidate_policy=r['policy_id'],candidate_product=r['product_id'],candidate_error=r['candidate_error'],same_policy_ordered_control_error=r['ordered_control_error'],same_policy_error_delta=r['paired_error_delta'],prior_strongest_error=loss,prior_strongest_procedures=[dict(procedure_id=x['procedure_id'],history_regime=x['history_regime'],product=x['product'],source_artifact=x['source_artifact'])for x in previous],error_delta_vs_prior_strongest=r['candidate_error']-loss,relative_error_delta_vs_prior_strongest=(r['candidate_error']-loss)/loss if loss else None,evidence='samefixedquerypanel/labelidentitiesverifiedbyprior435156rowaudit+newC02controlqueryjoins;observedminimaafter2026exposure,notfrozenselection'))
    metadata=dict(version='v2-c02-fixed-ordered-control-and-prior-leader-report-v1',canonical_scores_sha256=sha(public_root/'SCORES.json'),control_score_bindings=sourcebind,prior_leader_artifact=leader_csv.as_posix(),prior_leader_sha256=sha(leader_csv),prior_identity_audit='reports/continuation-20261030/PREGAME_COHORT_INDEPENDENT_QA.json',point_views=point,proper_law_mean_views=laws,observed_primary_minima=best,new_fits=0,new_forecasts=0,week8_outcomes_read=0,limits='Removalofexplicitlagblockonly;recencymeansstillordered. Samefixedseedwithchangeddimensionalitydoesnotpairrandomthresholds;effectincludesfeaturecompetition/modelinteraction. Sevenexposedweeks,multiplicity/hindsightselection;no futurepolicyorproductionclaim.')
    dump(public_root/'CATEGORY_CONTROL_COMPARISON.json',metadata)
    for name,rs in [('POINT_CONTROL_COMPARISON.csv',point),('PROPER_LAW_CONTROL_COMPARISON.csv',laws),('OBSERVED_PRIMARY_MINIMA.csv',best)]:
        with(public_root/name).open('x',newline='')as h:
            w=csv.DictWriter(h,fieldnames=list(rs[0]));w.writeheader();w.writerows({k:json.dumps(v,sort_keys=True)if isinstance(v,(dict,list))else v for k,v in r.items()}for r in rs)
    lines=['# C02: explicit lag-block removal','',
'All336registered historical cells completed:278actual fits/retained models and58explicit no-fit fallbacks. No original control was refitted. All336candidate cells matched the original control’s training-membership digest, cutoff, feature floor, position-prior counts and exact prior parameters before fitting. The12targets retain17968fixed query identities across2026Weeks1–7; their107games are reused NFL evidence, not new outcomes.','',
'The candidate removes the four individual lag value/age/missing triplets and their imputation flags, keeping mean3/n3/mean8/n8 and position indicators. This changes20raw/40design features to8raw/16design features with the same forest, priors, fallback and scoring. **Recency summaries remain; this does not isolate all ordering.** Same random seed with fewer features does not hold every random split threshold fixed.','',
'The wave produced134168historical forecast views and1608aggregate views in103.530wall/109.001CPU seconds with1033506816bytes peak RSS/two threads. There are zero new future captures or Week8outcomes. Family count does not increase; this is a tested procedure variant of the existing leaf-CDF mechanism.','',
'## Native point minima and strong controls','',
'Each row selects the lowest observed candidate primary error across its predeclared products/policies after exposure to2026. Numeric primary error isMAE; TDusesBrier. The fixed-control column uses the exact same policy/product; the prior-leader column is the strongest previously observed family representative on the verified common population. These minima are descriptive, not an earlier-frozen selection rule.','',
'| Target | n | Candidate policy/product | Candidate | Same-policy ordered CDF | Previous strongest | Change vs previous strongest |','| --- | ---: | --- | ---: | ---: | ---: | ---: |']
    for r in best:lines.append(f"| {r['target']} | {r['n']} | {r['candidate_policy']} / {r['candidate_product']} | {r['candidate_error']:.6f} | {r['same_policy_ordered_control_error']:.6f} | {r['prior_strongest_error']:.6f} | {r['error_delta_vs_prior_strongest']:+.6f} |")
    lines+=['','Lag-block removal improves the observed primary point minimum over the prior leader for interceptions, receptions and qualified chart points; ties passingTD; and loses to prior leaders in the other eight targets. In particular, rushing-attempt MAE3.109005does not beat ordered-CDF3.059242. Preserve the unsuccessful comparisons. Tiny chart/reception differences and exposed minima require later evidence rather than an automatic switch.','',
'[POINT_CONTROL_COMPARISON.csv](POINT_CONTROL_COMPARISON.csv) retains every core-history/strict, product and primary/extended full-system comparison, fallback counts, absolute and relative candidate-minus-control deltas, masks and game-cluster sensitivity. [SCORES.json](SCORES.json) additionally retains weeks, positions, learned-only and exact paired-learned overlap. Seven exposed week clusters preclude the registered eight-week interval; game sensitivity does not correct selection/multiplicity.','',
'## Proper laws and intended means','',
'The same valid95%leaf-PMF+5%same-arm-role-prior law is used, with signed support preserved. [PROPER_LAW_CONTROL_COMPARISON.csv](PROPER_LAW_CONTROL_COMPARISON.csv) reports all48primary target/policy laws plus supported extended views: native CRPS, PMFnegative-logloss, explicit infinite-loss counts, interval width/coverage, zero mass and separate intended-meanMSE. Means and medians are views of each fitted law, not independent learners.','',
'Startup point-mass laws can assign zero mass to positive outcomes. The canonical inherited convention storesNLLnull with a positiveinfinite_NLLcount; this report explicitly renders those scores asInfinity, not missing success or zero loss. A finite-only subset is not substituted for the proper score. Chart NLLis PMFmass at score×50with no density Jacobian; chart CRPS/width/points use native units.','',
'Chart median strict/inclusive1/5/10point precision is computed on the exact0.02integer grid with explicit precision_counts_exact_grid. Mean forecasts remain unrounded. The35unqualified current chart labels remain in coverage. No generic provider fantasy target or component-median sum is substituted.','',
'## Reproduction and limits','',
'The protocol froze02:27:34.741204Z; seven fictional fixture functions passed before any fit. Source/helper/query/label/control hashes and every model/feature/prediction receipt are retained. The private output is stable and requires the root-managed approved companion receipt. Root registers/indexes the new canonical scores; the original scores, failed versions and future packets remain unchanged.','',
'This is a current-vintage retrospective observed-stat-row diagnostic with an assumed seven-day availability rule and previously exposed2026outcomes. Common-memoryH-CURRENTmeans current-season fitting; STRICTchanges the complete information policy with2026-only outcomes/features/priors and inherited historical architecture. No calibration, pricing, ROI, website deployment, future routing or permanent optimality claim follows.']
    (public_root/'README.md').write_text('\n'.join(lines)+'\n');return dict(point_views=len(point),proper_law_views=len(laws),observed_primary_minima=len(best),scores_sha256=metadata['canonical_scores_sha256'])

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for a in('public-root','control-public','chart-public','leader-csv'):p.add_argument('--'+a,type=Path,required=True)
    print(json.dumps(run(**vars(p.parse_args()))))
