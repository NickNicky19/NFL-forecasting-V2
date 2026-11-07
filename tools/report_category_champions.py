"""Project retained aggregate champions; no forecast, grading or selection changes."""
import csv, hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'reports/championship-20261030f'
TARGETS=['pass_yd','pass_td','pass_cmp','pass_att','pass_int','rush_yd','rush_att','rec','rec_yd','rush_rec_yd','nick-chart-ppr-v1','anytime_td']
LABEL={'original':'Original recorded lean','SAVED_ADJUSTED_POINT_DIRECTION_RETAINED_PRECISION':'Saved adjusted point','SAVED_RAW_PROJECTION_DIRECTION_RETAINED_PRECISION':'Saved raw projection','alwaysOver':'Always Over','alwaysUnder':'Always Under'}
def read(p):return json.loads((BASE/p).read_text())
def pct(v):return 'N/A' if v is None else f'{100*v:.2f}%'
def cell(r):
    if r is None:return 'N/A'
    m=r['selection_metrics'];return f"{r['forecast_rows']} / {m['WIN']} / {m['LOSS']} / {r['n']} / {pct(m['hit_rate'])}"
def maxrows(rows):
    valid=[r for r in rows if r['n']>0]
    if not valid:return []
    best=max(r['selection_metrics']['hit_rate'] for r in valid)
    return [dict(strategy=r['strategy'],selected=r['forecast_rows'],wins=r['selection_metrics']['WIN'],losses=r['selection_metrics']['LOSS'],decided=r['n'],hit_rate=best,selection_coverage=r['selection_metrics']['selection_coverage'],game_uncertainty=r['selection_metrics']['game_uncertainty']) for r in valid if r['selection_metrics']['hit_rate']==best]
def main():
    numerical=read('numerical-v2/CATEGORY_CHAMPIONS_NUMERICAL.json')
    props=read('offer-expansion/full-pool-v1/SCORES.json')
    policies=read('category-selector-v2/SCORES.json')
    bases=[r for r in props if r['cohort_id']=='ALL' and r['K'] is None and r['rank_scope'] is None]
    sources=['numerical-v2/CATEGORY_CHAMPIONS_NUMERICAL.json','offer-expansion/full-pool-v1/SCORES.json','category-selector-v2/SCORES.json']
    provenance={p:hashlib.sha256((BASE/p).read_bytes()).hexdigest()for p in sources}
    out=[];lines=['# Category champions: verified comparable tested procedures','',
      '**New result:** expanded Week 7 saved adjusted-point decisions score **272/446 (60.99%)** versus saved raw projection **261/446 (58.52%)** on the full provider-labelled pool. Original selected leans remain **183/279 (65.59%)**. Those are different selected populations. The added167 qualified previously unselected rows give adjusted89/167 (53.29%) versus always-Under97/167 (58.08%). No new weeks or seasons of authentic V2 offer evidence have been added.', '',
      'Numerical comparisons now independently replay220 contrasts on current 2026 Weeks1–7 and complete2022–2025 seasons. No completed fit was rerun: **zero new fits, inference calls or forecasts**. The 2026 static-procedure leader list is unchanged as these comparisons use the same retained predictions; the new earlier-only carry selector scores3.049763 versus staticD1 3.058057 and is shown separately. Expanded selection coverage changes observed selection leaders. The chronological category selector wins4/12 and loses8/12 against frozen2025 selection. Neither static hindsight winners nor this exposed replay establish a live policy.', '',
      'This is a partial all-method tournament. Current numeric panels cover107games/7weeks; old panels cover18weeks (2022:271completed games, other years272). Primary passing isQB, rushingQB+RB, receiving/combined/TD RB+WR+TE; extended positions remain separate source views. Chart labels2359/2394,35unknown. These are reconstructed participant panels with per-game kickoff query features, weekly fitting and assumed seven-day source availability, not authenticated T-minus90 forecasts or full ex-ante populations. Current fitting with older feature memory is distinct from strict-current information.', '',
      '[Full numerical tables, mean-MSE/law leaders and older reversals](numerical-v2/CATEGORY_CHAMPIONS_NUMERICAL.md) · [All913 mechanism/product/season representatives](numerical-v2/ALL_VALID_REPRESENTATIVES.csv) · [Every full-pool method and side](offer-expansion/full-pool-v1/README.md) · [Top-player/workload tables](offer-expansion/full-pool-v1/COHORT_READABLE.md) · [Top-6/10/20 pick tables](offer-expansion/full-pool-v1/TOPK_READABLE.md) · [Earlier-only category selection](category-selector-v2/README.md) · [Release packages](RELEASE_CANDIDATES.md)', '',
      'Selection cells below show **selected / wins / losses / decided / hit rate**. Every combined count is the sum of its actual selected-Over and selected-Under buckets. Full462threshold pool,13-games,2026W7; original retains177abstentions. Missing appearances16 overall (6original) stay unknown. Statistical pushes/voids/pending/missing-actuals are0 in this bounded source; every bookmaker settlement remains unresolved. Provider labels are not authenticated price, quote freshness, jurisdiction or refund evidence. All probability-at-offer, EV, ROI and CLV leaders remain unestablished. Nick chart and rushing-or-receiving anytime-TD have no matching offered contract here.', '',
      'Raw side maxima below have no new posthoc minimum-support gate. They are descriptive maxima across these five strategies, including original filtered picks and one-side controls; their selected-side pools differ. An original4/4 result remains visible but is not a full-pool or full-season champion. All forecast procedures not temporally matched to these earlier retained lines remain unavailable for this offer comparison; numerical learners are not silently treated as evaluated selection strategies.', '']
    for target in TARGETS:
        nums=[r for r in numerical if r['category']==target]
        primary=[r for r in nums if r['ranking_product'] in ('display_point_mae','event_probability')]
        # Sources use display_point MAE under a declared product name.
        if not primary:primary=[r for r in nums if r['metric'] in ('mae','brier')]
        byside={s:[r for r in bases if r['target']==target and r['side']==s]for s in ('over','under','Combined')}
        maxima={s:maxrows(a)for s,a in byside.items()}
        metric='brier' if target=='anytime_td' else'mae'
        selected_policies=[r for r in policies if r['target']==target]
        policy_best=min(selected_policies,key=lambda r:r[metric])
        overall=dict(procedure_id=primary[0]['procedure_id'],loss=primary[0]['ranking_loss'],kind='static_procedure')
        if policy_best[metric]<overall['loss']-1e-12:overall=dict(procedure_id=policy_best['procedure_id'],loss=policy_best[metric],kind='chronological_category_selection_policy')
        out.append(dict(category=target,numeric_leaders=primary,best_numeric_including_registered_category_policies=overall,chronological_policy_scores=selected_policies,partial_selection_maxima=maxima,full_period_selection_state='UNESTABLISHED_MISSING_OTHER_WEEKS_AND_TEMPORALLY_MATCHED_PROCEDURES',offered_probability_leader=None,price_aware_leader=None,release_state='RESEARCH_PACKAGE_NOT_ADMITTED',source_sha256=provenance))
        lines += [f'## {target}','','| Numerical product | Exact procedure / output / history | Native loss | n / games / weeks | Fallback |','|---|---|---:|---|---|']
        for r in nums:
            lines.append(f"| {r['ranking_product']} ({r['metric']}) | `{r['procedure_id']}` / {r['product_id']} / {r['history_regime']} | {r['ranking_loss']:.6f} | {r['n']} / {r['unique_games']} / {r['unique_weeks']} | {r['scored_fallback_rows']}/{r['n']} |")
        lines += ['','| Strategy | Predicted Over | Predicted Under | Combined |','|---|---|---|---|']
        for method in LABEL:
            rows={r['side']:r for r in bases if r['target']==target and r['strategy']==method}
            lines.append(f"| {LABEL[method]} | {cell(rows.get('over'))} | {cell(rows.get('under'))} | {cell(rows.get('Combined'))} |")
        if overall['kind']=='chronological_category_selection_policy':
            lines += ['',f"**Lowest observed MAE including tested routing policies:** `{overall['procedure_id']}` at **{overall['loss']:.6f}**, below the best static procedure {primary[0]['ranking_loss']:.6f}. It selects from earlier eligible score weeks, with named startup fallback. It is a separate exposed reconstruction, not an issued prospective policy; missing fresh confirmation/readiness does not conceal this numerical result."]
        for side in ('over','under','Combined'):
            found=maxima[side]
            desc='; '.join(f"{LABEL[r['strategy']]} {r['wins']}/{r['decided']} ({pct(r['hit_rate'])}), selected{r['selected']}"for r in found) or 'unavailable: no matching offered target/threshold contract'
            lines += ['',f'**Best observed partial {side}:** {desc}.']
        if primary:
            r=primary[0]
            lines += ['',f"Current numerical leader{'s (tie)' if len(primary)>1 else ''} {'; '.join('`'+v['procedure_id']+'` '+v['history_regime'] for v in primary)}; next distinct score {r['runner_up_loss']:.6f}, paired difference {r['paired_delta']:+.6f}. Game-cluster95% sensitivity interval {r['game_normal95_sensitivity']}; seven current weeks are insufficient for the registered week-bootstrap interval. Prior exact-recipe seasons: {r['full_prior_seasons_for_exact_recipe'] or 'FIT_REQUIRED; no older D1/D2 substitution'}. See linked older-season tables for reversals and exact recipes."]
        lines += ['', 'The current served website has not been beaten on a matched full-period/horizon panel. Archived R0 beats the artifact’s fixed V2 comparator in8/10 numeric categories on its narrower thirteen-game reference; it is not a comparison against every new champion. Owner review can consider this named research package, but a production switch needs matched incumbent evidence, appropriate later confirmation, recovery/runtime/fallback parity and retained-owner admission. Point releases do not require betting-profit claims.','']
    lines += ['## Coverage, uncertainty and next executable work','',
      'Original, retrospective and prospective tracks stay separate. Source seasons are exposed research. The full-pool adjusted-minus-raw hit-rate difference is11/446=2.47percentage points; game-bootstrap95% sensitivity[-1.68,+6.74]points includes zero. Adjusted overall95% sensitivity[57.01,65.35]%; raw[54.99,61.99]%. One week cannot establish a season-stable side advantage. The numerical passing-yard HGB-MULTI versus Leaf-MULTI comparison improves2025 by1.376yards but reverses2023 by0.977yards. Older rows are not pooled to hide the current comparison.', '',
      'Top-K here is a newly frozen retrospective within-category weekly list, separately combined-side, Over-only and Under-only; it is not an originally issued list. K6/10/20 does not force extra selections. Player top10/15/20 and disjoint bands are shared prior-feature diagnostics frozen after games, not original ex-ante cohorts. Their full tables retain adverse low-workload results. Source snapshots share a server pregame bound; missing original internal precision is never invented. Existing kickoff-feature V2 reconstructions are not paired as earlier forecasts to these earlier quotes.', '',
      'The coverage projection distinguishes scientific evaluation cells, fit-origin/output cells, unresolved legacy references and60 requested pathways. Missing cells have exact actions; no whole-project completion percentage is claimed. Large fits remain gated by missing-only recovery:53 parts/1,093,747,658bytes, plus separate2,536,759-byte qualified2021 source; no upload retry or capacity proof this turn.147 strict-HGB origins, scheduled-window768 logicalcells and1,098 ordinary2021RECENT cells(+54 chart source blocked) remain queued. D1/D2older-season fits remain required. Safe replay/source qualification continues while actual recovery is blocked.', '',
      'At00:00UTC Oct31 (19:00CDT Oct30), the first Week 8game has elapsed; thirteen games remain future. Existing immutable packets retain their actual clocks, differing first-game horizons and13/14game coverage. No new capture, replacement or V2Week 8player-outcome grading occurred here. A fresh upstream aggregate report includes one completedWeek 8game; that separate reported source is not untouched evidence. Existing forecasts require qualified retained outcomes and frozen rules before later grading.', '',
      '[Independent calculations and join checks](independent/INDEPENDENT_REVIEW.md) · [Permanent result index](results-index-v5/README.md) · [Coverage grid](coverage/README.md) · [Upstream refresh](UPSTREAM_REFRESH.md) · [Recovery status](RECOVERY_AND_QUEUE.md) · [Owner defect notification](OWNER_NOTIFICATION_RECEIPT.json). Production remains unchanged by V2.']
    (BASE/'CATEGORY_CHAMPIONS.md').write_text('\n'.join(lines)+'\n')
    (BASE/'CATEGORY_CHAMPIONS.json').write_text(json.dumps(out,indent=2)+'\n')
    flat=[]
    for r in out:
        p=r['numeric_leaders'][0]
        row=dict(category=r['category'],overall_numeric_procedure=r['best_numeric_including_registered_category_policies']['procedure_id'],overall_numeric_loss=r['best_numeric_including_registered_category_policies']['loss'],overall_numeric_kind=r['best_numeric_including_registered_category_policies']['kind'],numeric_procedure='; '.join(v['procedure_id'] for v in r['numeric_leaders']),numeric_tie=len(r['numeric_leaders'])>1,history=p['history_regime'],product=p['product_id'],metric=p['metric'],loss=p['ranking_loss'],n=p['n'],games=p['unique_games'],weeks=p['unique_weeks'],full_period_selection_state=r['full_period_selection_state'],offered_probability_leader=None,price_aware_leader=None,release_state=r['release_state'])
        for side in ('over','under','Combined'):row[side+'_partial_maxima']=json.dumps(r['partial_selection_maxima'][side],separators=(',',':'))
        flat.append(row)
    with (BASE/'CATEGORY_CHAMPIONS.csv').open('w',newline='')as f:
        w=csv.DictWriter(f,fieldnames=list(flat[0]));w.writeheader();w.writerows(flat)
    print(json.dumps(dict(categories=len(out),new_grades=0,new_fits=0,source_sha256=provenance)))
if __name__=='__main__':main()
