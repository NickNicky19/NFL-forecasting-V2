"""Public aggregate comparison; verifies independent paired-row reconciliation. No fits."""
from __future__ import annotations
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'reports/continuation-20261029'
TARGETS = ['pass_yd','pass_td','pass_cmp','pass_att','pass_int','rush_yd','rush_att','rec','rec_yd','rush_rec_yd','nick-chart-ppr-v1','anytime_td']
TIE = 1e-12

def read(path):
    with path.open(newline='') as f:
        return list(csv.DictReader(f))

def write(path, rows):
    with path.open('x', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)

def best(rows, metric):
    loss = min(float(r[metric]) for r in rows)
    ties = [r for r in rows if abs(float(r[metric]) - loss) <= TIE]
    return sorted(ties, key=lambda r:(r['history_regime'], r.get('product',r.get('objective',''))))[0], ties

def main():
    esrc = BASE/'history-diagnostic-v1/HISTORY_COMPARISON_2026_W1_W7.csv'
    hsrc = BASE/'hgb-history-v1/SCORES.csv'
    psrc = ROOT/'reports/verification/HGB_PAIRED_COMPARISONS.json'
    ep = [r for r in read(esrc) if r['population']=='primary' and r['season']=='2026' and r['week']=='ALL' and r['position']=='ALL' and r['fallback_view']=='ALL']
    hp = [r for r in read(hsrc) if r['population']=='primary' and r['week']=='ALL' and r['position']=='ALL']
    pairs = json.loads(psrc.read_text())
    assert pairs['same_source_same_2026_primary_query_identities'] is True
    lookup = {(r['target'],r['objective'],r['history_regime']):r for r in pairs['hgb_vs_empirical']}
    elookup = {(r['target'],r['product'],r['history_regime']):r for r in ep}
    mapping = {'absolute_error_point':'lower_median','squared_error_mean':'empirical_mean','log_loss_probability':'event_probability'}
    checks = 0
    for h in hp:
        k=(h['target'],h['objective'],h['history_regime']); p=lookup[k]
        e=elookup[(h['target'],mapping[h['objective']],h['history_regime'])]
        metric='brier' if h['target']=='anytime_td' else 'mae'
        assert int(h['scored_n'])==int(e['scored_n'])==p['n']
        assert abs(float(h[metric])-p['hgb_primary_error'])<1e-10
        assert abs(float(e[metric])-p['empirical_primary_error'])<1e-10
        checks+=1
    assert checks==63
    rows=[]; means=[]
    for target in TARGETS:
        metric='brier' if target=='anytime_td' else 'mae'
        es=[r for r in ep if r['target']==target]; hs=[r for r in hp if r['target']==target]
        row={'target':target,'evaluation_panel':'2026-REG-W1-W7-primary-ALL-week-ALL-position','ranking_metric':metric,'scored_rows':None,'empirical_product':None,'empirical_history':None,'empirical_loss':None,'empirical_tied_views':None,'hgb_objective':None,'hgb_history':None,'hgb_loss':None,'hgb_tied_views':None,'hgb_minus_empirical_minimum':None,'lowest_observed_family':None,'state':'SCORED_SOURCE_MATCHED','selection':'exposed_postfit_minimum_not_frozen_selection_policy'}
        if not es or not hs:
            assert target=='nick-chart-ppr-v1'; row.update(state='BLOCKED_EXACT_COMPONENT_CURRENT_SOURCE_CONTRACT',ranking_metric=None);rows.append(row);continue
        e,et=best(es,metric);h,ht=best(hs,metric)
        assert len({int(r['scored_n']) for r in es+hs})==1
        ev=float(e[metric]);hv=float(h[metric])
        row.update(scored_rows=int(e['scored_n']),empirical_product=e['product'],empirical_history=e['history_regime'],empirical_loss=ev,empirical_tied_views=';'.join(x['product']+':'+x['history_regime'] for x in et),hgb_objective=h['objective'],hgb_history=h['history_regime'],hgb_loss=hv,hgb_tied_views=';'.join(x['objective']+':'+x['history_regime'] for x in ht),hgb_minus_empirical_minimum=hv-ev,lowest_observed_family='tie' if abs(hv-ev)<=TIE else 'HGB' if hv<ev else 'empirical')
        rows.append(row)
        if target!='anytime_td':
            e,_=best([r for r in es if r['product']=='empirical_mean'],'mse');h,_=best([r for r in hs if r['objective']=='squared_error_mean'],'mse')
            means.append({'target':target,'metric':'MSE','scored_rows':int(e['scored_n']),'empirical_mean_history':e['history_regime'],'empirical_mse':float(e['mse']),'empirical_rmse':float(e['rmse']),'hgb_squared_error_mean_history':h['history_regime'],'hgb_mse':float(h['mse']),'hgb_rmse':float(h['rmse']),'hgb_minus_empirical_mse':float(h['mse'])-float(e['mse']),'selection':'exposed_best_observed_intended_mean_history_not_calibration_certificate'})
    write(BASE/'TWO_FAMILY_PRIMARY_COMPARISON_2026_W1_W7.csv',rows)
    write(BASE/'TWO_FAMILY_MEAN_MSE_2026_W1_W7.csv',means)
    lines=['# Two-family observed comparison: fixed 2026 Weeks 1–7','', 'HGB has the lower observed family-minimum MAE/Brier in seven of eleven supported targets. The empirical family is lower for passing TDs, interceptions, rushing yards and receiving yards. This is an exposed comparison of **two families**, not five independent learners or a frozen future selector. Exact chart PPR remains blocked. These minima choose among the registered products and three history regimes after observing their errors.','', 'Both families use the same source-matched primary player-game identities and labels. Every one of 63 family/objective/history contrasts was checked against the [independent saved-row reconciliation](../verification/HGB_PAIRED_COMPARISONS.json). Here `primary`, `week=ALL`, `position=ALL` includes full startup/fallback contribution, with no learned-only filtering. It covers all 107 games in 2026 Weeks 1–7, but supported rows remain target/position-specific; the underlying cohort is retrospective observed participation, with current-vintage sources and assumed seven-day availability. Their representations and refit/update rules differ, so this is a procedure comparison rather than a pure learner ablation.','', '[Point/Brier CSV](TWO_FAMILY_PRIMARY_COMPARISON_2026_W1_W7.csv) · [Separate intended-mean MSE/RMSE CSV](TWO_FAMILY_MEAN_MSE_2026_W1_W7.csv) · [HGB methods, losses and startup comparison](hgb-history-v1/README.md)','', '| Target | Rows | Empirical best observed product / history | MAE or Brier | HGB best observed objective / history | MAE or Brier | Lower observed family |','|---|---:|---|---:|---|---:|---|']
    for r in rows:
        if r['scored_rows'] is None:lines.append(f"| {r['target']} | — | blocked: exact component contract | — | blocked | — | unestablished |");continue
        lines.append(f"| {r['target']} | {r['scored_rows']} | {r['empirical_product']} / {r['empirical_history']} | {r['empirical_loss']:.6f} | {r['hgb_objective']} / {r['hgb_history']} | {r['hgb_loss']:.6f} | {r['lowest_observed_family']} |")
    lines+=['', 'Numeric targets use native-unit MAE, including fitted mean outputs when they win empirical MAE. The TD row uses Brier, never expected TD count. Different category units and populations cannot form a raw-error accuracy league. The CSV retains all ties within 1e-12; tied views are not additional learners.','', '## Intended means: separate MSE/RMSE product','', 'These minima compare only empirical means with squared-error HGB means. A fitted mean label does not establish calibration. RMSE is in native units; MSE is in squared units. Neither is mixed into the displayed-point MAE ranking.','', '| Target | Empirical history | MSE | RMSE | HGB mean history | MSE | RMSE |','|---|---|---:|---:|---|---:|---:|']
    for r in means:lines.append(f"| {r['target']} | {r['empirical_mean_history']} | {r['empirical_mse']:.6f} | {r['empirical_rmse']:.6f} | {r['hgb_squared_error_mean_history']} | {r['hgb_mse']:.6f} | {r['hgb_rmse']:.6f} |")
    lines+=['','No universal history regime is established. HGB arms share older feature memory; the empirical current arm uses only eligible current-season target outcomes, while its retrospective position/cohort definition prevents a full-system strict-current-information claim, H-CURRENT has startup fallback, and only seven current-season week clusters support uncertainty. These exposed minima need later selection-policy evaluation; legacy W1–6 CDF/provider scores are a different panel. Week 8 shadows are retained but unscored, and neither family is deployed. Chart rare components, richer role/defense/playcalling groups, authenticated offers and broad legacy adapters remain separate dependencies.','']
    assert sum(r['lowest_observed_family']=='HGB' for r in rows)==7
    (BASE/'TWO_FAMILY_PRIMARY_COMPARISON_2026_W1_W7.md').write_text('\n'.join(lines))
    receipt={'state':'PUBLIC_AGGREGATE_COMPARISON_VERIFIED_AGAINST_INDEPENDENT_ROW_PAIRS','independent_row_identity_match':True,'primary_history_product_contrasts_checked':checks,'target_rows':12,'scored_targets':11,'blocked_targets':['nick-chart-ppr-v1'],'families':2,'new_fits':0,'new_predictions':0,'tie_tolerance':TIE,'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [esrc,hsrc,psrc]},'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'selection':'exposed_postfit_family_minima_not_a_frozen_selection_policy'}
    (BASE/'TWO_FAMILY_COMPARISON_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(rows,indent=2))
if __name__=='__main__': main()
