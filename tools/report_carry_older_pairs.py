"""Readable paired-analysis projection, no new univariate score artifact."""
import argparse,csv,json
from pathlib import Path

def display(v):return 'unknown'if v is None else f'{v:.4f}'

def main(root):
    root=Path(root);receipt=json.loads((root/'RUN_RECEIPT.json').read_bytes());protocol=json.loads((root/'FROZEN_PROTOCOL.json').read_bytes())
    pairs=[]
    for year in receipt['completed_seasons']:pairs.extend(json.loads((root/f'PAIR_ANALYSIS_{year}.json').read_bytes())['rows'])
    flat=[]
    for r in pairs:
        flat.append({k:r[k]for k in('pair_id','season','history_regime','policy_id','population','cohort_id','position','fallback_view','comparison','candidate_procedure_id','candidate_product_id','comparator_procedure_id','comparator_product_id','comparator_history_regime','query_rows','paired_n','unresolved_rows','native_error_delta','relative_error_delta','game_count','week_count','query_membership_sha256','paired_membership_sha256')}|dict(candidate_mae=r['candidate_metrics']['mae'],comparator_mae=r['comparator_metrics']['mae'],candidate_mse=r['candidate_metrics']['mse'],candidate_bias=r['candidate_metrics']['bias'],candidate_fallback_rows=r['candidate_metrics'].get('scored_fallback_rows',0),candidate_fallback_error_contribution=r['candidate_metrics'].get('fallback_full_error_contribution'),week95=json.dumps(r['uncertainty']['week_interval']),game_cluster_sensitivity_se=r['uncertainty']['game_cluster_sensitivity_se']))
    if flat:
        with(root/'PAIR_ANALYSIS.csv').open('x',newline='')as f:
            writer=csv.DictWriter(f,fieldnames=list(flat[0]));writer.writeheader();writer.writerows(flat)
    def find(year,pop='primary',cohort='all',position='ALL',view='full_system',policy='H-MULTI-COMMON',reference='strongest_observed_same_season_full_primary_control'):
        return next((r for r in pairs if(r['season'],r['population'],r['cohort_id'],r['position'],r['fallback_view'],r['policy_id'],r['comparison'])==(year,pop,cohort,position,view,policy,reference)),None)
    lines=['# Does the carry training-role repair hold up in older seasons?\n',
        'This is a new paired analysis of existing2022–2025 predictions. It tests the retained QB/RB-only L1 training-role repair against both original broad-training HGB L1 with the same history/information policy and the strongest observed same-season full-primary carry control. Strongest controls were fixed before paired subgroup losses were decoded; they were not reselected inside QB/RB/WR/TE or top-player bands. These are exposed descriptive benchmarks, not a recreated earlier model-selection policy.\n',
        'The main table fixes the repair to **H-MULTI/common feature memory**, matching the accepted2026 emphasis. Every current/recent/multi/strict contrast is retained in the linked JSON/CSV; no winning older-history variant is silently substituted. Negative deltas favor the repair. Native MAE is in carries, with candidate-minus-control signs.\n',
        '| Season | Primary paired n | Repair MAE | Delta vs original HGB L1 | Delta vs strongest control | Strong-control week95 interval |',
        '|---|---:|---:|---:|---:|---|']
    for y in receipt['completed_seasons']:
        a=find(y);b=find(y,reference='same_policy_original_broad_HGB_L1')
        ci=a['uncertainty']['week_interval'];ci='unknown'if ci is None else '['+', '.join(display(x)for x in ci)+']'
        lines.append(f"|{y}|{a['paired_n']}|{display(a['candidate_metrics']['mae'])}|{display(b['native_error_delta'])}|{display(a['native_error_delta'])}|{ci}|")
    lines+=['','The original L1 comparison isolates the registered training-role/fallback package at the same policy; the strongest-control comparison can use another history/product/update mechanism and is a practical benchmark. Both are necessary: improvement over a collapsed or weak original does not establish the strongest useful forecast.','',
        '| Season | Position/population | Repair MAE | Delta vs original | Delta vs strongest | n |', '|---|---|---:|---:|---:|---:|']
    for y in receipt['completed_seasons']:
        for pos in('QB','RB','WR','TE'):
            pop='primary'if pos in('QB','RB')else'extended';a=find(y,pop=pop,position=pos);b=find(y,pop=pop,position=pos,reference='same_policy_original_broad_HGB_L1')
            if a:lines.append(f"|{y}|{pos}/{pop}|{display(a['candidate_metrics']['mae'])}|{display(b['native_error_delta'])}|{display(a['native_error_delta'])}|{a['paired_n']}|")
    lines+=['','WR/TE remain in the extended population, including their structural low counts, nonzero carries and early exits. They are not removed to make the specialization look better. Their fallback/exposure composition differs from QB/RB and is reported separately.','',
        '| Season | Primary view | n | Repair MAE | Strong-control MAE | Delta | Repair fallback rows | Fallback contribution within this view |',
        '|---|---|---:|---:|---:|---:|---:|---:|']
    for y in receipt['completed_seasons']:
        for view in('full_system','own_learned_only','all_three_common_learned','candidate_fallback_only','any_model_fallback'):
            r=find(y,view=view)
            if r:lines.append(f"|{y}|{view}|{r['paired_n']}|{display(r['candidate_metrics']['mae'])}|{display(r['comparator_metrics']['mae'])}|{display(r['native_error_delta'])}|{r['candidate_metrics'].get('scored_fallback_rows',0)}|{display(r['candidate_metrics'].get('fallback_full_error_contribution'))}|")
    lines+=['','Common-learned rows require the repair, same-policy original and fixed strongest control all to have learned nonfallback forecasts. Own-learned and fallback views have different masks and are not credited as paired history comparisons. Each pair retains exact query/scored membership hashes and shared actual/position checks. Error summaries inside each pair use identical supported rows; unresolved query rows remain in the outer coverage counts.','',
        '| Season | Primary cohort | n | Repair MAE | Delta vs original | Delta vs strongest |', '|---|---|---:|---:|---:|---:|']
    for y in receipt['completed_seasons']:
        for cohort in('top10','top15','top20'):
            r=find(y,cohort=cohort);b=find(y,cohort=cohort,reference='same_policy_original_broad_HGB_L1')
            if r:lines.append(f"|{y}|{cohort}|{r['paired_n']}|{display(r['candidate_metrics']['mae'])}|{display(b['native_error_delta'])}|{display(r['native_error_delta'])}|")
    lines+=['','Top-player membership reuses the already frozen season-specific prior-carry rankings. It does not select stars by realized production, create authentic historical exante issuance or prove training only on stars helps. Strict-policy forecasts remain a complete information-policy comparison, while these common frozen selectors may use older opportunity history.','',
        'The2025 full specialization source is overlaid with the preserved correction packet: all base specialization rows are discarded, not numerically blended. The2023 source is the complete18-week recombination, not the stopped Week1–16 parent.2022 includes271 supported games; its H-RECENT arm lacks2021and is a source-limited2022proxy. The present test compares methods within that actual proxy and does not call it a completed requested older-history contrast.','',
        'MAE, signed bias, MSE/RMSE and tails remain native point diagnostics; these absolute-loss point outputs are not authenticated median distributions or genuine conditional-mean products. Paired week bootstrap uses500draws/seed1703 with18weekly blocks where supported; game-cluster intervals are sensitivity checks. Intervals do not adjust for previous research exposure, control selection or multiplicity.','',
        '[Accepted2026 strongest-control comparison](../../continuation-20261030b/carry-strong-control-comparison-v1/README.md) remains unchanged: the role repair beat the previous empirical mean on844matched QB/RB rows (3.091618versus3.128691), while orderedCDF was stronger at3.059242. Extended WR/TE repair error0.619436lost to mean0.291669and orderedCDF0.101583. No2026replay was executed here.','',
        f"Run state **{receipt['state']}**; completed seasons{receipt['completed_seasons']}, remaining{receipt['remaining_seasons']}. The saved-row run used{receipt['resource']['wall_seconds']:.2f}wall seconds,{receipt['resource']['cpu_seconds']:.2f}CPU seconds,{receipt['resource']['peak_rss_bytes']/1048576:.1f}MiB peak RSS and one thread, within the declared180second/1GiB limit if complete. It produced{receipt['pair_views']:,}paired aggregate views, zero new univariate score artifacts, zero fits/inferences/forecasts and zero current2026Week8label reads. Source retention/readiness limits remain those of the original archives; this replay grants no production admission.",
        '', 'Evidence: [frozen protocol](FROZEN_PROTOCOL.json), [run receipt](RUN_RECEIPT.json), [all paired comparisons CSV](PAIR_ANALYSIS.csv). Per-season `PAIR_ANALYSIS_YYYY.json` retains all paired native errors, support, fallback decomposition, exact row hashes and uncertainty. No player-level records or private locators are published.']
    (root/'README.md').write_text('\n'.join(lines)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--public-root',required=True,type=Path);main(p.parse_args().public_root)
