"""Render retained results and product-week evidence; no scorer/model calls."""
import collections
import gzip
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools import abc_b_c_bound_replay as a
OUT=ROOT/'reports/post-wave-5w-v1'
RANK=OUT/'b-confidence-ordering-v1/context-ranker-v1'
CATS=['pass_yd','pass_td','pass_cmp','pass_att','pass_int','rush_yd','rush_att','rec','rec_yd','rush_rec_yd','anytime_td','nick-chart-ppr-v1']


def rate(w,l):
    return f'{w}–{l}/{w+l} ({100*w/(w+l):.2f}%)'if w+l else'N/A (0 decided)'


def main():
    original_path=ROOT/'reports/abc-championship/continuation-20261103-v1/original-selected-under-control-v1/SCORES.json'
    old=a.load(original_path)
    original={}
    outer=dict(zip(CATS[:10],[28,28,28,28,28,87,43,174,175,42]))
    for t in CATS[:10]:
        rr={r['side']:r for r in old if r['procedure_id']=='B_ORIGINAL_RECORDED'and r['target']==t}
        for key in ['WIN','LOSS','PUSH']:
            assert rr['Combined']['selection_metrics'][key]==sum(rr[s]['selection_metrics'][key]for s in ['over','under'])
        assert rr['Combined']['forecast_rows']==sum(rr[s]['forecast_rows']for s in ['over','under'])
        original[t]=dict(outer=outer[t],**{s:dict(selected=r['forecast_rows'],wins=r['selection_metrics']['WIN'],losses=r['selection_metrics']['LOSS'],decided=r['n'],unknown=r['selection_metrics']['status_counts']['UNKNOWN_PARTICIPATION'])for s,r in rr.items()})
    assert sum(v['Combined']['selected']for v in original.values())==427
    assert sum(v['Combined']['decided']for v in original.values())==415
    ta=['| Category | Over W–L/N/% | Under W–L/N/% | Combined W–L/N/% | Selected/eligible | Unknown O/U |','|---|---|---|---|---|---|']
    for t in CATS:
        if t not in original:
            reason='No matching rushing/receiving TD offer'if t=='anytime_td'else'No same-chart offer'
            ta.append(f'| {t} | N/A | N/A | N/A | {reason} | — |');continue
        r=original[t]
        vals=[rate(r[s]['wins'],r[s]['losses'])for s in ['over','under','Combined']]
        ta.append(f"| {t} | {' | '.join(vals)} | {r['Combined']['selected']}/{r['outer']} | {r['over']['unknown']}/{r['under']['unknown']} |")
    table_a='\n'.join(ta)
    scores=a.load(RANK/'SCORES.json');comparison=[]
    tb=['| Category / exact rule | Period | Over W–L/N/% | Under W–L/N/% | Combined W–L/N/% | Selected/eligible; unavailable |','|---|---|---|---|---|---|']
    for t,w in [('rec','ALL'),('pass_td',8)]:
        for arm in ['G0','G1']:
            rr={r['side']:r for r in scores if r['target']==t and r['procedure_id'].endswith('::'+arm)and r['strategy']=='MATCHED50'and r['cohort_id']=='ALL'and r['week']==w}
            x=rr['Combined'];sm=x['selection_metrics']
            vals=[rate(rr[s]['selection_metrics']['WIN'],rr[s]['selection_metrics']['LOSS'])for s in ['over','under','Combined']]
            tb.append(f"| {t} / {arm} MATCHED50 | 2026 W{'2–3'if t=='rec'else'8'} | {' | '.join(vals)} | {x['forecast_rows']}/{sm['selection_pool_count']}; {sm['technical_unavailable']} |")
            comparison.append(dict(target=t,arm=arm,procedure_id=x['procedure_id'],history=x['history_regime'],
                product=x['product_id'],policy=x['strategy'],actual_weeks=x['evaluation_weeks'],
                side_records={s:dict(wins=rr[s]['selection_metrics']['WIN'],losses=rr[s]['selection_metrics']['LOSS'],decided=rr[s]['n'],selected=rr[s]['forecast_rows'])for s in rr},
                eligible=sm['selection_pool_count'],selected=x['forecast_rows'],unavailable=sm['technical_unavailable'],
                games=x['unique_games'],MAE=None,MAE_null_reason='Selection reliability/event product has no own numeric point; original mean is ancillary, unchanged.',evidence=x['evidence_tier']))
    qualification_path=OUT/'B-product-week-qualification-v3/B_PRODUCT_WEEK_QUALIFICATION.json.gz'
    q=a.load(qualification_path);native=a.load(ROOT/'reports/baselines-coverage-20261031h/CATEGORY_DECISIONS.json')
    qs=[]
    for t in CATS:
        n=next(r for r in native if r['category']==t)
        results=[]
        for win in n['native_winners']:
            matches=[r for r in q if r['category']==t and r['procedure_id']==win['procedure_id']and r['product_id']==win['product_id']and r['history']==win['history_regime']]
            qualified=[r for r in matches if set(range(1,8)).issubset(set(r.get('per_season',{}).get('2026',{}).get('weeks',[])))]
            results.append(dict(procedure_id=win['procedure_id'],product=win['product_id'],history=win['history_regime'],
                current_n=win['n'],native_error=n['native_winner_loss'],metric=n['native_primary_metric'],
                matching_retained_contract_views=len(matches),current_seven_week_contract_views=len(qualified),
                witnesses=[dict(qualification_id=r['qualification_id'],horizon=r['horizon'],population=r['population'],position=r['position'],weeks=r['per_season']['2026']['weeks'],source_vintage=r['source_vintage'])for r in qualified[:3]],
                scope='Retained numerical/event-score week evidence only; not actual-line/TopPick or full target/operational admission.'))
        qs.append(dict(category=t,native_leaders=results,
            actual_line_status='NewG0/G1 <=2scoredweeks; prior exact procedure/policy/source/horizon continuity must be verified separately'if t in ['rec','pass_td']else'Existing source-specific two/three-week panels retained; no numerical-to-selection week borrowing',
            special_blocker='Partial chart labels cannot establish complete exact Nick chart contract'if t=='nick-chart-ppr-v1'else'No matching offered event'if t=='anytime_td'else None))
    a.save(OUT/'READABLE_TABLE_BINDINGS.json',dict(
        presentation_only=True,original_source=dict(path=str(original_path.relative_to(ROOT)),sha256=a.sha(original_path)),
        original_week8=original,new_policy_source=dict(path=str((RANK/'SCORES.json').relative_to(ROOT)),sha256=a.sha(RANK/'SCORES.json')),
        matched_policy_rows=comparison,new_grades=0,new_fits=0))
    a.save(OUT/'B_CATEGORY_PRODUCT_QUALIFICATION_SUMMARY.json',dict(
        B_only_contribution=True,source=dict(path=str(qualification_path.relative_to(ROOT)),sha256=a.sha(qualification_path)),
        source_scope='Accepted602201plusnew816ranker views;226diagnostics and468conditionalRBviews do not qualify newprimaryproducts.',
        categories=qs,qualification_is_not_release=True))
    with (OUT/'RETAINED_ORIGINAL_WEEK8_TABLE_V2.md').open('x') as f: f.write(table_a+'\n')
    # Copy only the existing category table. No numerical or selection rerun.
    oldmd=(ROOT/'reports/baselines-coverage-20261031h/DIRECT_CATEGORY_TABLES_PRESENTATION_V1.md').read_text()
    native_table=oldmd.split('| Category | Procedure/version')[1].split('\n\nBoth tied')[0]
    native_table='| Category | Procedure/version'+native_table
    md=f'''# B post-wave diagnosis, five-week qualification and delivery

Revision POST-WAVE-5W-v1. Session B local evidence contribution; C retains the common evaluator, intake and shared qualification table. The requested 2026 W1–8/historical championship remains incomplete. No additional NFL week was added by this wave.

The new earlier-only correctness ranker **lost one reception selection**: G0 86/163 (52.76%) versus G1 85/163 (52.15%). Passing TDs tied at 5/13 (38.46%). The fixed90% policy selected zero for either target: N/A accuracy, **TARGET_NOT_ESTABLISHED**. No threshold was lowered and no losing pick was inverted. Full-board base directions and event probabilities were unchanged.

C's specifically requested shared111-RB mask is now executed across all52 retained B point/history/output configurations. Four strict-current median recipes tie at **65/111**, versus always-Under/earlier-role **63/111**, the strongest other B score **63/111** (HGB-L1 RECENT/MULTI) and C direct **60/111**. Their own Over13–11/24 (54.17%), Under52–35/87 (59.77%) sum to65–46/111 (58.56%); MAE30.5225 yards and bias−23.3694 on these same111RB cases. The +2win paired gain has uncertainty crossingzero. The leaders retain55fallback rows (34/55correct, tied always-Under) and56learned rows (31/56correct versus always-Under29/56, Week3only). These are the same two exposed weeks, not new time coverage. All52 procedures, losses, full coverage and learned/fallback contributions remain in the [complete subset table](B-111-RB-common-mask-v3/SIDE_TABLE.csv); this new subset awaits C intake.

Count A's exact passing-TD mean/P1 has seven reported scored weeks and87/142 correct (61.27%). Its current derived-output producer route is still not present at the inspected immutable lab-state head; exact model/mean-corrector/current-adapter parity and consumer admission remain missing. This is a precise delivery dependency, not a new request for five future weeks or a blanket deployment approval.

## Table A — original recorded selections (retained)

Standalone 2026 Week8,14finalgames; prior W5–7 reports remain separate and immutable. W1–4 original-pregame evidence and W5Thursday are missing; this table is not full W1–8 performance. Statistical crossing only; bookmaker settlement/prices remain unverified. All selected outcomes are decided except12unknown appearances; zero pushes, pending or missing-actual states in this selected panel. Every category has only one scored week, so week-cluster uncertainty is insufficient.

{table_a}

Totals: Over109–128/237 (45.99%); Under96–82/178 (53.93%); Combined205–210/415 (49.40%). Selected427/661; unknown8Over+4Under=12. Each combined count is the sum of its selected-side buckets. Always-Under224/415 beats original205/415 by19wins on this same original-selected pool; this is not a future Under policy or profitability claim.

## Table B — actual forecasting procedures and products

**New controlled selection comparison.** G0/G1 use H-MULTI base forecasts and earlier eligible held-out evidence. G0 ranks unchanged base confidence; G1 estimates whether that frozen base side will be correct. MATCHED50 selects equal counts per chronological decision batch, from each arm's eligible rows. This is a reliability score, not a new Over probability or EV. Neither policy has an own numerical point: MAE is N/A; unchanged base mean references remain ancillary. These are timing-unverified retrospective actual-line diagnostics, not original issued G1 picks.

{chr(10).join(tb)}

Receptions has one selected unknown in each arm;22technical missing laws are unavailable, not confidence abstention. Passing TDs has2unavailable base laws. These whole-view unknown-fallback states are now explicit. The reception own-pool change is−0.61pp, game-cluster95% sensitivity−1.44to+0.22pp; insufficient week clusters (2). Both arms lose to always-Under88/163 on their own selected masks. Passing-TD arms lose to always-Over7/13 (always-Under6/13). Only1passing-TD test week. Own selected pools differ; the paired common-selection analyses are separate [records](b-confidence-ordering-v1/context-ranker-v1/PAIRED_COMPARISONS.json).

**All12category status and existing numerical leaders.** These rows are rendered unchanged from the existing [category evidence](../baselines-coverage-20261031h/DIRECT_CATEGORY_TABLES_PRESENTATION_V1.md). N=numerical2026W1–7 participant/stat-row panel, kickoff/current-revised reconstruction; O=actual threshold2026W5–7 known-target-time retrospective replay. Each row uses that SAME procedure's own sides; own pools differ. Error is MAE except the event Brier. M=H-MULTI; C=current fitting with older feature memory. No selected-side fallback count is silently assumed zero. Three offer weeks remain insufficient week-cluster evidence. The native numerical winners are not automatically selection winners.

{native_table}

Exact IDs: HGB-L1=`hgb-direct-history-controls-v1:absolute_error_point`; D1/D2=`v2-qualified-position-defense-information-wave-v1:D1/D2` four-**observed-position-group** window; C02=`v2-c02-explicit-lag-block-removal-leaf-cdf-v1`; Leaf-v2=`v2-distribution-controls-reconstruction-v2:ordered_leaf_cdf`; earlier-current selector=`v2-chronological-category-score-memory-selector-v2:EARLIER_AVAILABLE_2026_SCORE_MEMORY`; HGB-logloss=`hgb-direct-history-controls-v1:log_loss_probability`. Full bindings and all tied mean/median views remain in the existing registry. Partial chart labels do not certify the complete exact-chart contract. No same-contract anytime-TD/complete-chart offer panel is available.

The separate Over/Under/combined maxima, including1/1 and3/3 fallback-only cases, remain visible in [all-method maxima](../baselines-coverage-20261031h/DIRECT_CATEGORY_TABLES_PRESENTATION_V1.md). They are not hidden by the five-week floor or spliced into a fictional router. The floor is a primary-release requirement, not a retrospective ranking censor.

## What the diagnosis establishes

The earlier C reliability study already showed the reception baseline's weak confidence ordering. B reuses that result and extends the trace to B1, exact line, role, frozen support, fallback and opportunity-memory age groups; it is not a second C classifier/NGS study. On337reception outcomes, base Over AUC=.532884, confidence-versus-correctness AUC=.464152, Brier=.259868. The intercept repair lowers the latter AUC to.452185 and worsens Brier to.260203. A neutral50/50 reference has Brier.25 on these half-point/no-push cases.

The unchanged reception baseline's confidence bins show79/127correct at0.5–0.6confidence,73/133 at0.6–0.7,34/63 at0.7–0.8,8/14 at0.8–0.9. More displayed confidence did not reliably rank correctness. Role records are RB47/82,WR99/177,TE48/78; all losses are retained. Line6.5 is0/7 and7.5 is1/3: small exposed groups, not validated exclusion filters. Probability spread exists (.5004–.8569), so zero90% selections do not mean no variance.

Passing-TD Week8 has26supported outcomes: base14/26, Brier.266196; the original intercept repair retains14/26 and Brier.264826. Confidence-correctness AUC=.363095 base/.380952 repaired. Earlier Week6 development was18/27 with confidence AUC.617284. This deterioration is compatible with sampling and transfer changes; it does not isolate a causal source or prove a universal negative relationship. Development/reconstruction and Week8 captured-base products have different source/role/horizon limits.

Frozen opportunity memory age is **not actual consumed model-feature age**. The latter was not retained in these diagnostic rows, so cause remains unresolved. Missing laws' fallback state is unknown, not a known nonfallback. Target-game information used to describe correctness never enters the new selector's inputs.

## The single new mechanism and its controlled result

The [frozen protocol](b-confidence-ordering-v1/context-ranker-v1/FROZEN_PROTOCOL.json), SHA2568db55285efd2532155abf0a2a875052d0269909c50980a6aec651879f269da79, registers one L2correctness logistic ranker (C=.25), fixed confidence/side/line/role features, equal-game fitting weights, no search, strict earlier-label eligibility. Receptions uses rolling eligibleWeek2prefixes intoWeek3; passing-TD uses earlierWeek6held-out baseline decisions with coefficients frozen before the earliestWeek8decision. Week2/sparse prefixes preserve identity fallback. Five selection-ranker fits, **zero new football model fits/inference/original forecasts**. All periods were previously research-exposed; chronological construction is not untouched confirmation.

Learned-output overlap is separately filtered: rec65eligible/31selected, G0 18/31 versus G1 17/31 (Week3only); PT26eligible/13selected, both5/13 (Week8only). The earlier broader fitted-origin view is preserved and correctly renamed; it is not called a learned-output mask. [Metadata scope correction](b-confidence-ordering-v1/context-ranker-v1/METADATA_QUALIFICATION_V2.json) preserves every old804score/choice and adds12strict learned-output views.

Rolling Top-K is per category/week/side pool, chronological decision batches with remaining slots, stable ID ties, no forcedK. It is not a simultaneous fixed-weekly original list or ticket. Combined recG0/G1: Top6 3/11 (12selected,1unknown), Top10 11/19 (20selected,1unknown), Top20 25/39 (40selected,1unknown). PT: Top6 both3/6; Top10G0 4/10/G1 3/10; Top20both5/13. Separate Over-only and Under-only policies and all weekly side counts remain in canonicalSCORES. Fixed90% G0/G1 both0selected: **TARGET_NOT_ESTABLISHED**, not100%.

No probability repair, fitted selector or reliability threshold is promoted. A small exposed subset reaching a high rate would still require its exact coverage and week evidence; here none reaches90% under the fixed90% gate.

## Five-week qualification contribution to C

The [B-only exact-product inventory](B-product-week-qualification-v3/B_PRODUCT_WEEK_QUALIFICATION.json.gz), [CSV](B-product-week-qualification-v3/B_PRODUCT_WEEK_QUALIFICATION.csv.gz), [12category summary](B_CATEGORY_PRODUCT_QUALIFICATION_SUMMARY.json) and [independent witness](B-product-week-qualification-v3/INDEPENDENT_B_PRODUCT_WEEK_QUALIFICATION_V1.json) are a contribution to C's one shared table. They are not another consolidated benchmark.

Only explicit resolved per-week held-out score evidence counts, keyed by exact procedure/target/product/history/information/role/population/horizon/source/selection contract. Aggregate date spans, training weeks, aliases, repeated views and another output's scores do not count. Current2026 and each historical season remain separate. Five weeks is a floor; support, coverage, superiority, source rights and operational checks are separate.

G0/G1 reception full-system has2scoredweeks, PT1; their learned outputs have1each; zero90% selection policies have0. The older intercept repair likewise has2reception/1PTweeks, not the base model's full history. Existing seven-week numerical products and72-week historical base recipe views remain retained; they do not confer actual-line/TopPick qualification on another policy. Exact older D1/D2 cells cannot borrow ordinaryLeaf results.

The inventory identifies1596floor-met **product views**, not1596scientificmethods or admitted models;35552below-floor views and4256aggregate-only week-proof gaps remain. Source v1 case-sensitive `ALL` filtering incorrectly excluded existing full-system views; its exact raw/gzip/source/failure receipts are retained. V2/V3 correct scope/source binding only; no experiment was refit. The final inventory binds accepted602201plus816newranker records. New diagnostic/RBsubset views add no new qualifying primary product week.

## Count A delivery and actual owner operation

[Exact Count A witness](COUNT_A_FIVE_WEEK_AND_DELIVERY_WITNESS.json): f8607aa99a94c7c1c9ab5c89599e07eba9b15527749b092b225f368032881e83; seven2026scoredweeks, Over43–31/74, Under44–24/68, Combined87–55/142 (61.27%), MAE.864659499. Week1loss4/9 remains. Stronger matched learner Leafmedian85/142: only+2CountAwins with reported uncertainty crossingzero. These are timing-unverified retrospective diagnostics, not original issued picks, full-season proof or a probability law.

The [November4 owner receipt](https://github.com/NickNicky19/nicks-expert-nfl-picks/pull/1#issuecomment-6642441018) is verified, with no observed supersession at the read. Corrected mean is FORECASTS.parquet.point; legacy_point mixes fallback and mean isNaN. Barepredict is insufficient. B did not deserialize A's model or duplicate its producer. The complete776-entry pinned lab-state tree275aa84b27c4239d3b2dfea07755734d9db0ac7c contains publicW7/W8directories and noW9route: current publication missing at that head, **not proof the model is missing**.

Exact next action belongs to A/registered producer: restore exact existing model/features/environment/mean-corrector through approved storage, prove retained/current-adapter mean parity, then publish permitted fresh derived output with real issuance/persistence, role/side/ranking/fallback/expiry bindings. Original-site owner must acknowledge/admit its actual product. Learned mean, trained prior-MEAN and incumbent fallback remain distinct. Seven historical weeks do not qualify a new Top12selector; a restored exact procedure retains its existing weeks. No request for an unrelated blanket approval or extra waiting period is created.

The [owner capture witness](OWNER_CAPTURE_READBACK.json) and [nested clock qualification](OWNER_CAPTURE_QUALIFICATION_V2.json) verify actual productionaf8bc14abe4a4148a3f84e6c131775923b5300f4, policyv7SHA7933152e09d86e9e8a9482f46450b4765825d64f036e58f8f36d874c0cdd6382. Owner incumbent generatedNov4 21:03:37UTC, captured21:03:39, persisted21:03:44. The2573-row packet and24savedTopPicks (12O+12U across11games) match served bytes. Overlay DISABLED_USE_R0,0researchrows. B performed no browser rendering and no challenger publication. Existing updater41912247259completed/success; firstWeek9gameNov6 01:15UTC (Nov5 7:15p.m.CST). Next nominal configured captureNov5 14:06UTC (8:06a.m.CST) is not execution proof. B neither dispatched nor replaced it.

## Coverage, retention, delivery and next finite queue

No new NFL week/season, origin reconstruction, original pick or source-vintage authentication was created here. Reused native2026W1–7 and completed2022–25 rolling/base/source-specific startup tests remain unchanged. New52-way111RBcomparisons close a named matching gap, not W1–8 time coverage. C has admitted Bde34e962684C-board and219weekly source triads for owner-local diagnostics with public-mask verification; the older admission does not admit d835346c, the new ranker or new111RBsubset. Raw private row/model parity and source-time limits persist.

| Owner | Exact remaining action / dependency |
|---|---|
| B / C intake | C receives this immutable export, actual111RB/public mask mappings, newranker/qualification contribution and independent receipts; only C records received/validated/admitted. |
| B future probability | Need eligible next-origin B0 exact-line law/direct output and retained input/model contract; current point-only incumbent packet cannot supply probabilities. Freeze/capture a shadow through existing owner route, with real clocks; no backdated issuance or forced picks. |
| Source owners | Qualify actual annual/earlier-week thresholds and clocks plus exact-origin inputs; missing originals do not block supported reconstruction, missing prices do not block line-only scoring. C W2–3, B W5–7 and captured-baseW8 retain separate horizons/evidence; do not silently concatenate them. |
| B recovery / historical fits | Last verified38missing archive parts/796917760bytes; this is not a fresh quota check. Recover only missing required parts, fresh download/reassembly/full hashes. Original strictHGB147origins and exact olderD1/D2736cells remain recovery-dependent; no baseLeaf substitution. Scheduled-window and2021RECENT extensions retain their exact input/source/chart gaps. No unchanged upload retry or large fit launched. |
| A / Count A producer | Exact current mean-corrector/model/input restoration and parity, current public derived-output route and versioned side/eligibility/rank/fallback/expiry, then original-owner consumer acknowledgment. B's public witness is not delivery of A's model or new output. |
| C / common programme | Continue common intake, history/source coverage and own already-owned information studies; B does not duplicate NGS/target-share/direct-classifier work. |

Primary new work: five bounded correctness-ranker fits,0footballfits/inference,0newissuedforecasts,0newNFLobservations; ranker .728s wall/.852CPU/157417472peakRSS, threadpools2enforced,348170newprivatebytes before public scores. Derived rows/models are locally readback, not newly offhost-restored. Larger fit gate remains intact. RBmask adds zero private bytes; its2metadata-adapter failures are preserved before successful v3, no forecast changed. All old captures/losses, the unsuccessful intercept/gate and its resource caveat remain immutable.

Independent checks cover objective gradients/Hessians, earlier-prefix/target-mutation invariants, exact side counts, full/learned masks, actual owner clocks, CountAweekly arithmetic, five-week source witnesses and the newRBmask. Representative audits are not complete re-inference or source vintage authentication. Current permanent result/paired indexes append all versions; diagnostics/nonprimary products do not silently enter native rankings.

**Decision:** no new B primary replacement;90%target not established. Prepare/retain older independently eligible product exports under the existing policy and explicit five-week floor. CountApasses its reported point-direction week floor but still needs its producer/consumer delivery checks. Production remains with the incumbent owner; fullperiodchampionship remains partial at the exact source, recipe and retention cells above.
'''
    (OUT/'B_POST_WAVE_REPORT.md').write_text(md)
    print(json.dumps(dict(report='B_POST_WAVE_REPORT.md',original_categories=len(original),status_categories=len(qs),new_model_fits_by_render=0)))


if __name__=='__main__':main()
