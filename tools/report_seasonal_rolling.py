#!/usr/bin/env python3
"""Saved-row seasonal reports and paired history contrasts; no fitting."""
import argparse,collections,csv,gzip,hashlib,json,math,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2 import seasonal_rolling as s

def normal_proc(p):
    for suffix in (':common-feature-memory',':strict-current-inputs',':strict-current-feature-memory'):p=p.replace(suffix,'')
    return p
def block_interval(blocks,replicates=500):
    if len(blocks)<8:return None
    values=np.asarray(list(blocks.values()),dtype=float);rng=np.random.default_rng(1703);ids=rng.integers(0,len(values),size=(replicates,len(values)));draw=values[ids].sum(axis=1);delta=draw[:,0]/draw[:,1]
    return [float(v) for v in np.quantile(delta,[.025,.975])]
def main():
    p=argparse.ArgumentParser();p.add_argument('--public',type=Path,required=True);p.add_argument('--private',type=Path,required=True);a=p.parse_args();pub,priv=a.public,a.private
    receipt=json.loads((pub/'RUN_RECEIPT.json').read_text());protocol=json.loads((pub/'FROZEN_PROTOCOL.json').read_text());report_protocol=pub.parent/'SEASONAL_REPORT_PROTOCOL.json'
    if not report_protocol.exists():raise ValueError('report protocol required before contrasts')
    if s.sha(priv/'predictions.csv.gz')!=receipt['private_flat']['sha256']:raise ValueError('retained prediction hash')
    scores=json.loads((pub/'SCORES.json').read_text());primary=[r for r in scores if r['population']=='primary' and r['week']=='ALL' and r['position']=='ALL' and r['fallback_view']=='ALL'];s.emp.write_csv(pub/'PRIMARY_PROCEDURE_HISTORY.csv',primary)
    paired={};rows_replayed=0
    for file in sorted((priv/'predictions').glob('W*.csv.gz')):
        cases=collections.defaultdict(dict)
        with gzip.open(file,'rt') as f:
            for r in csv.DictReader(f):
                if not r['actual']:continue
                key=(normal_proc(r['procedure_id']),r['family'],r['target'],r['population'],r['product_id'],r['query_id']);cases[key][r['policy_id']]=r;rows_replayed+=1
        for key,policies in cases.items():
            proc,family,target,pop,product,query=key
            for label,new,old in [('H-RECENT_MINUS_H-CURRENT','H-RECENT-COMMON','H-CURRENT-COMMON'),('H-MULTI_MINUS_H-CURRENT','H-MULTI-COMMON','H-CURRENT-COMMON'),('STRICT_MINUS_COMMON_CURRENT','H-CURRENT-STRICT','H-CURRENT-COMMON')]:
                if new not in policies or old not in policies:continue
                nr,orr=policies[new],policies[old]
                if nr['actual']!=orr['actual'] or nr['game_id']!=orr['game_id']:raise ValueError('history comparison mismatched labels/identity')
                actual=float(nr['actual']);npred,opred=float(nr['prediction']),float(orr['prediction']);loss=lambda p:(p-actual)**2 if target=='anytime_td' else abs(p-actual);nd,od=loss(npred),loss(opred)
                for view in ['FULL_SYSTEM']+(['PAIRED_LEARNED_ONLY'] if nr['fallback']=='none' and orr['fallback']=='none' else []):
                    k=(proc,family,target,pop,product,label,view)
                    if k not in paired:paired[k]=dict(n=0,new=0.,old=0.,weeks=collections.defaultdict(lambda:[0.,0]),games=collections.defaultdict(lambda:[0.,0]))
                    g=paired[k];g['n']+=1;g['new']+=nd;g['old']+=od
                    for dim,value in [('weeks',nr['week']),('games',nr['game_id'])]:g[dim][value][0]+=nd-od;g[dim][value][1]+=1
    contrasts=[]
    for k,g in sorted(paired.items()):
        proc,family,target,pop,product,label,view=k;n=g['n'];contrasts.append(dict(procedure_id=proc,procedure_family_id=family,target=target,population=pop,product_id=product,contrast=label,fallback_view=view,n=n,new_loss=g['new']/n,old_loss=g['old']/n,paired_loss_difference=(g['new']-g['old'])/n,negative_favors_new=True,week_clusters=len(g['weeks']),game_clusters=len(g['games']),week_block_interval_95=block_interval(g['weeks']),game_block_sensitivity_interval_95=block_interval(g['games']),uncertainty='descriptive paired500blockbootstraps; exposedmulti-comparison, noselection-adjustment; insufficient<8clusters; season-only not2026historyanswer'))
    s.write(pub/'HISTORY_COMPARISONS.json',contrasts);s.emp.write_csv(pub/'HISTORY_COMPARISONS.csv',contrasts)
    files=[dict(artifact_id='OLDER-SEASON-'+s.sha(f),bundle_name=f.relative_to(priv).as_posix(),sha256=s.sha(f),bytes=f.stat().st_size) for f in sorted(priv.rglob('*')) if f.is_file()]
    s.write(pub/'PUBLIC_ARTIFACT_MANIFEST.json',dict(state='LOCAL_RETAINED_PENDING_APPROVED_PRIVATE_RESTORATION',logical_member_contract='Portable archive member artifact IDs, not filesystem/storage locators',files=len(files),total_bytes=sum(f['bytes'] for f in files),artifacts=files))
    winners=[]
    for target in s.TARGETS:
        metric='brier' if target=='anytime_td' else 'mae';eligible=[r for r in primary if r['target']==target and r.get(metric) is not None]
        eligible.sort(key=lambda r:(r[metric],r['procedure_id'],r['history_regime'],r['product_id']))
        if eligible:
            best=eligible[0];winners.append(dict(target=target,metric=metric,procedure_id=best['procedure_id'],product_id=best['product_id'],history_regime=best['history_regime'],policy_id=best['policy_id'],native_error=best[metric],n=best['n'],games=best['unique_games']))
    s.emp.write_csv(pub/'CATEGORY_OBSERVED_MINIMA.csv',winners)
    # Attribute-only warnings preserve every fitted model; no refit or removal.
    optimizer=[]
    import pickle
    for path in sorted((priv/'models').glob('*.pickle.gz')):
        model=pickle.loads(gzip.decompress(path.read_bytes()));est=getattr(model,'estimator',model);niter=getattr(est,'n_iter_',None);limit=getattr(est,'max_iter',None)
        if niter is not None and limit is not None and np.max(np.atleast_1d(niter))>=limit and type(est).__name__ in ('PoissonRegressor','LogisticRegression'):optimizer.append(dict(model_artifact_id='OLDER-SEASON-'+s.sha(path),estimator=type(est).__name__,n_iter=np.atleast_1d(niter).tolist(),max_iter=limit,state='ITERATION_LIMIT_REACHED_RETAINED',warning_census='attribute-bound; completeoriginalstderrwarningcensusnotretained'))
    s.write(pub/'OPTIMIZER_LIMIT_DIAGNOSTICS.json',optimizer)
    s.write(pub/'REPORT_RECEIPT.json',dict(state='SAVED_ROW_REPORT_COMPLETE',actual_completed_at=s.now(),code_sha256=s.sha(__file__),source_scores_sha256=s.sha(pub/'SCORES.json'),source_flat_sha256=s.sha(priv/'predictions.csv.gz'),report_protocol_sha256=s.sha(report_protocol),primary_score_views=len(primary),paired_contrasts=len(contrasts),learned_prediction_rows_replayed=rows_replayed,retained_model_iteration_limit_flags=len(optimizer),new_fit_calls=0,new_future_forecasts=0,Week8_outcomes_read=0))
    text=['# '+str(receipt['evaluation_season'])+' rolling learned-method evaluation','',f"State: **{receipt['state']}**. This wave covers {receipt['query_games']} regular-season games and {receipt['query_cells']:,} frozen target opportunities, including missing labels. It creates {receipt['actual_fit_calls']:,} fits and retains {receipt['retained_models']:,} models; {receipt['failed_fits']} fits failed. Identical history policies reuse {receipt['identical_policy_alias_cells']:,} fit cells without adding fits.",'',f"It records {receipt['score_views']:,} aggregate score views and {receipt['forecast_output_views']:,} forecast views, including {receipt['retained_empirical_output_views']:,} retained empirical views replayed with zero fits. Views, models and NFL games are separate counts.",'','All training labels precede the weekly origin under the conservative seven-day rule. Features refresh before each game; transformations use only the selected earlier training rows. CURRENT fits the evaluation season, RECENT its preceding season plus current games, and MULTI expands from2022. Common-memory arms still use earlier feature history; strict-current additionally removes that older memory and fitted priors. There is no pre2022 warm start.','', '| Target | Lowest observed procedure/product/history | Native error | Supported rows |','|---|---|---:|---:|']
    text += [f"|{r['target']}|{r['procedure_id']} / {r['product_id']} / {r['policy_id']}|{r['native_error']:.6f}|{r['n']}|" for r in winners]
    text += ['','Numeric entries use MAE; anytime TD uses Brier. This table shows exposed observed minima, not a method-selection policy or a comparison across native units. Mean MSE and genuine-law CRPS/log scores remain separate in the complete score file. Every loss and fallback remains included.','', 'Paired history contrasts retain identical player/game/target rows and report full systems plus paired learned-only intersections. Week/block uncertainty is descriptive with multiplicity and prior research exposure; it does not establish a universal winner. An older-season result does not answer whether older training improves the same2026 games.','', 'The cohort is a current-vintage retrospective statistical-row/physical-participation diagnostic, not a reconstructed ex-ante roster or authenticated offers panel. Chart uses the qualified partial sixteen-component contract; positive or missing rare credits remain unknown. Chart medians use exact0.02-grid precision arithmetic; means are never rounded. No2026 model is refitted, and no Week8 outcome or future forecast is created.','',f"Resources: {receipt['resource']['wall_seconds']:.2f} active wall seconds, {receipt['resource']['cpu_seconds']:.2f} CPU seconds, peak RSS {receipt['resource']['peak_rss_bytes']:,} bytes, at most two threads. Private retained artifacts require the separately recorded offhost restoration before durability is claimed."]
    with (pub/'README.md').open('x') as f:f.write('\n'.join(text)+'\n')
    print(json.dumps(dict(year=receipt['evaluation_season'],score_views=receipt['score_views'],primary=len(primary),contrasts=len(contrasts),private_files=len(files),private_bytes=sum(r['bytes'] for r in files),winners=winners)))
if __name__=='__main__':main()
