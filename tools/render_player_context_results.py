"""Render retained aggregate calculations; never fit, infer or regrade."""
import collections,csv,io,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools.score_player_context_wave import read,write,sha,VERSION,ctx
BASE=ROOT/'reports/player-context-matchup-01/B'

def fmt(w,l):
    n=w+l;return f'{w}–{l}/{n}/'+(f'{w/n:.2%}'if n else'N/A')
def main():
    raw={d:read(BASE/d/'SCORES.json')for d in('qb-scores-v1','qb-charting-scores-v1','component-and-controls-v1')}
    corrected=[dict(r)for r in raw['qb-scores-v1']]
    for ann in read(BASE/'qb-scores-v1/SOURCE_PERIOD_HISTORY_METADATA_ANNOTATIONS_V2.json')['rows']:
        corrected[ann['source_row_index']].update({k:v['current']for k,v in ann['contract_metadata']['fields'].items()})
    rows=corrected+raw['qb-charting-scores-v1'];offers=[r for r in rows if r['record_kind']=='prop_selection_evaluation'];native=[r for r in rows if r['record_kind']=='forecast_evaluation_view']
    methods=[]
    for r in offers:
        if r['side']!='Combined'or r.get('K')is not None or r['cohort_id']!='ALL':continue
        sides={x['side']:x for x in offers if x['procedure_id']==r['procedure_id']and x['target']==r['target']and x['week']==r['week']and x['strategy']==r['strategy']and x['cohort_id']=='ALL'and x.get('K')is None}
        assert set(sides)=={'over','under','Combined'}
        sm={k:dict(wins=x['selection_metrics']['WIN'],losses=x['selection_metrics']['LOSS'],decided=x['n'],selected=x['forecast_rows'],hit_rate=x['selection_metrics']['hit_rate'])for k,x in sides.items()}
        assert sm['Combined']['wins']==sm['over']['wins']+sm['under']['wins']and sm['Combined']['losses']==sm['over']['losses']+sm['under']['losses']
        n=next((x for x in native if x['procedure_id']==r['procedure_id']and x['season']==2026 and x['week']=='ALL'and x['product_id']=='mean'and x.get('fallback_view','FULL_SYSTEM')=='FULL_SYSTEM'),None)
        methods.append(dict(procedure_id=r['procedure_id'],category=r['target'],period='2026W5-8'if r['week']=='ALL'else'2026W'+str(r['week']),week_view=r['week'],history=r['history_regime'],output_rule=r['strategy'],
            sides=sm,eligible=r['selection_metrics']['selection_pool_count'],technical_unavailable=r['technical_unavailable'],fallback=r['selection_metrics']['fallback_issued'],games=r['unique_games'],
            coverage=r['selection_metrics']['selection_coverage'],numerical_mean_MAE=n['mae']if n else None,numerical_n=n['n']if n else None,numerical_panel='2026W1-8retrospectiveQBparticipants'if n else'No compatible own native point in this wave',evidence=r['source_vintage']))
    write(BASE/'ALL_METHOD_SIDE_TABLE.json',methods)
    flat=[]
    for r in methods:
        x={k:v for k,v in r.items()if k!='sides'}
        for side,v in r['sides'].items():x.update({side+'_'+k:value for k,value in v.items()})
        flat.append(x)
    with(BASE/'ALL_METHOD_SIDE_TABLE.csv').open('x',newline='')as f:
        w=csv.DictWriter(f,fieldnames=list(flat[0]));w.writeheader();w.writerows(flat)
    # Cumulative Top-K is an arithmetic projection of four disjoint weekly
    # canonical views, not a new run or additional NFL observations.
    cumulative=[]
    group=collections.defaultdict(list)
    for r in offers:
        if r.get('K')is not None:group[r['procedure_id'],r['target'],r['K'],r['rank_scope'],r['side']].append(r)
    for k,rr in sorted(group.items()):
        assert {r['week']for r in rr}=={5,6,7,8}and len(rr)==4
        wins=sum(r['selection_metrics']['WIN']for r in rr);losses=sum(r['selection_metrics']['LOSS']for r in rr)
        cumulative.append(dict(procedure_id=k[0],target=k[1],K=k[2],rank_scope=k[3],side=k[4],actual_weeks=[5,6,7,8],wins=wins,losses=losses,decided=wins+losses,
            selected=sum(r['forecast_rows']for r in rr),eligible=sum(r['selection_metrics']['selection_pool_count']for r in rr),hit_rate=wins/(wins+losses)if wins+losses else None,
            source_score_record_ids=[r['record_id']for r in rr],projection='SUM_OF_DISJOINT_WEEKLY_CANONICAL_COUNTS_NOT_ADDITIONAL_SCORED_RUN',
            timing='Perweek percategory perpool K, chronological kickoff batches; timing-unverified line diagnostics, not original executable weekly tickets.'))
    write(BASE/'TOPK_CUMULATIVE_COUNT_PROJECTION.json',cumulative)
    # Exact numerical duration; original/vintage and product readiness distinct.
    qualification=[]
    for proc in sorted({r['procedure_id']for r in native}):
        rr=[r for r in native if r['procedure_id']==proc and isinstance(r['week'],int)and r['n']and r.get('fallback_view','FULL_SYSTEM')=='FULL_SYSTEM']
        for product in('mean','lower_median'):
            pp=[r for r in rr if r['product_id']==product];weeks=sorted({(r['season'],r['week'])for r in pp})
            qualification.append(dict(procedure_id=proc,product=product,category=pp[0]['target'],scored_season_weeks=weeks,numerical_week_count=len(weeks),numerical_duration_floor='PASS'if len(weeks)>=5 else'FAIL',
                source_tier='Current/revised chronological reconstruction; retrospective participant membership, not original issuance.',actual_line_scored_weeks=[[2026,w]for w in(5,6,7,8)],
                direction_probability_topK_floor='FAIL_FOUR_ACTUAL_OFFER_WEEKS',operational_status='NOT_CURRENT_QUERY_ADMITTED_NOT_SERVED',recommendation='No new primary selection/probability switch; point product requires its own supported comparison/runtime/admission, no added future waiting period.'))
    write(BASE/'PRODUCT_QUALIFICATION.json',qualification)
    original=read(ROOT/'reports/audit-remediation-20261105-v1/B/TABLE_A_PRESERVED_ORIGINAL_WEEK8.json')
    legacy=read(ROOT/'reports/audit-remediation-20261105-v1/B/TABLE_B_MATCHED_AVAILABILITY_LEADERS_WITH_TIES.json')
    write(BASE/'PRESERVED_CATEGORY_TABLE_BINDINGS.json',dict(original_source='reports/audit-remediation-20261105-v1/B/TABLE_A_PRESERVED_ORIGINAL_WEEK8.json',original_sha256=sha(ROOT/'reports/audit-remediation-20261105-v1/B/TABLE_A_PRESERVED_ORIGINAL_WEEK8.json'),
        legacy_method_source='reports/audit-remediation-20261105-v1/B/TABLE_B_MATCHED_AVAILABILITY_LEADERS_WITH_TIES.json',legacy_method_sha256=sha(ROOT/'reports/audit-remediation-20261105-v1/B/TABLE_B_MATCHED_AVAILABILITY_LEADERS_WITH_TIES.json'),rerun=False))
    lines=['# Session B — player context and matchup: executed results', '',
        '**The strongest new completion direction scored 58/112 (51.79%), versus E0 49/112. It tied saved adjusted and always-Over, and lost to earlier-only prevalence 59/112. All new exact-line probability products lost to neutral Brier 0.25. No 90%-gate selections occurred.**', '',
        'New numerical evaluation covers every regular-season week in 2025 (664 QB-player-games) and 2026 Weeks 1–8 (277). Actual-line evaluation reuses the qualified retained 2026 Weeks 5–8 board: 112 completions plus 112 attempts over 56 games. No earlier offered week or historical offered season was added. Week 5 still lacks one game; Weeks 1–4 and older CMP/ATT thresholds/clocks remain source-owner dependencies. This is new procedure-and-period evidence, not completion of the all-category championship.', '',
        'C retains the canonical shared evaluator/intake. These B results are LOCAL_NOT_C_ADMITTED. All already inspected history remains exposed development. Inputs are current/revised versions under strict seven-day reconstructed availability, not authenticated historical publication. Numerical membership is retrospective official QB stat membership, not an ex-ante roster.', '',
        '## Controlled exact-line decisions', '',
        'All rows below have 112 eligible offers, zero technical unavailability, zero pushes/pending/unknowns, and 56 games. Every own side belongs to the same displayed procedure. P2 compares exact-law Over/Under mass; it conditions on physical participation, not verified bookmaker nonvoid settlement.', '',
        '| Category | Exact procedure suffix / H-RECENT | Over W–L/n/% | Under W–L/n/% | Combined W–L/n/% | Brier |',
        '|---|---|---:|---:|---:|---:|']
    for r in methods:
        if r['week_view']!='ALL'or r['output_rule']not in('P2_STATISTICAL_LAW','REGISTERED_DIRECTION'):continue
        if not r['procedure_id'].startswith(('B-player-context','B-QB-CHARTED'))and r['procedure_id']not in('SAVED_ADJUSTED','SAVED_RAW','ALWAYS_OVER','ALWAYS_UNDER','EARLIER_LINE_PREVALENCE'):continue
        prob=next((x for x in rows if x['record_kind']=='prop_threshold_probability_evaluation'and x['procedure_id']==r['procedure_id']and x['target']==r['category']and x['week']=='ALL'),None)
        ss=r['sides'];br=f"{prob['brier']:.6f}"if prob else'N/A'
        lines.append('| '+r['category']+' | '+r['procedure_id']+' | '+' | '.join(fmt(ss[k]['wins'],ss[k]['losses'])for k in('over','under','Combined'))+' | '+br+' |')
    lines += ['', 'E3 gains 9/112 decisions (+8.04 percentage points) over E0; game-cluster sensitivity is +1.53 to +14.54 points. There are only four week clusters, so the whole-week interval is unavailable. Against saved adjusted, E3 gains zero; its game sensitivity is −11.44 to +11.44 points. These exposed multiple comparisons do not establish a durable winner.', '',
        'Adding opponent main effects reduced P2 direction from E1 54/112 to E2 50/112. Explicit interactions increased it to E3 58/112. Shared P1, partially pooled P2 and own-only-coefficient P3 scored 54, 53 and 54/112. No useful personalization gain is established. P3 has shared-input and shared-model fallback; it is not an entirely player-only information system.', '',
        'The shared attempt-exposure law scored 55/112; saved adjusted scored 69/112. It is one common QB exposure control, not three separate attempt models. The strongest all-board baseline need not be a newly learned model.', '',
        'The .90 selected-side probability gate produced zero selections in every offered week for every new procedure: accuracy N/A, TARGET_NOT_ESTABLISHED. No threshold was lowered. Neutral probabilities have no directional choice at exactly 50/50; their Brier remains 0.25.', '',
        '## Native error and historical reversal', '',
        'Mean and lower median are separate products. Mean MSE/RMSE, signed bias, tails, exact-count and strict/inclusive tolerances remain in canonical scores; none is converted to percentage pick accuracy.', '',
        '| Exact procedure suffix | 2025 mean MAE (664) | 2025 median MAE (664) | 2026 W1–8 mean MAE (277) | 2026 W1–8 median MAE (277) |',
        '|---|---:|---:|---:|---:|']
    for proc in sorted({r['procedure_id']for r in native}):
        vals=[]
        for year in(2025,2026):
            for product in('mean','lower_median'):
                x=next(r for r in native if r['procedure_id']==proc and r['season']==year and r['week']=='ALL'and r['product_id']==product and r.get('fallback_view','FULL_SYSTEM')=='FULL_SYSTEM');vals.append(f"{x['mae']:.6f}")
        lines.append('| '+proc+' | '+' | '.join(vals)+' |')
    lines += ['', 'On the full matched 2025 panel, FTN F2 median loses to the retained exact base Leaf-v2 median: 5.992470 versus 5.945783 on 664 identical QB-player-games. In 2026 the old Leaf common comparison has only 242 of the new 277 rows: F2 median 5.417355 versus old Leaf 5.561983 on those 242. Do not splice the 242-row comparator with F2’s full 277-row MAE 5.606498.', '',
        'F2 improves on support-only F1’s median in both years, but its mean improvement reverses against the unchanged E1 in 2025. F2’s actual-line direction merely ties E1 (54/112). Its Brier is 0.272159, worse than 0.25. Improved numerical error does not establish improved selected-side accuracy.', '',
        'Startup Weeks 1–4, Week 5 onward, every individual week, each season, learned/fallback scopes and per-player/equal-player summaries are retained. Numerical duration meets five distinct weeks for these exact point products. Four actual-line weeks do not qualify direction, threshold probability, or Top Picks as primary replacements. No requirement for five NEW future weeks is added.', '',
        '## Source and component contract', '',
        '| Information group | Actual accessible support | Definition / limitation |',
        '|---|---|---|',
        '| PBP QB down/depth | 2022–2025 full REG; 2026 W1–8; 2,901 QB-game rows | Down 1–4/unknown × signed air-depth <0,0–9,10–19,20+/unknown. Official attempts exclude sacks/two-point attempts; stat-credited no-play retained. |',
        '| Field context | Same earlier QB histories | Lagged distance, field position, time and score summaries. No target-game future context supplied. |',
        '| Opponent context | Earlier qualified QB-passing team-games | Shrunken residual versus earlier offense-quality reference. QB-only passing scope; not all team dropbacks or causal defense talent. |',
        '| FTN charted catchability/drop/contested | Retained 2022–2026 charting joined by game/play | Rates positive/known; support known/all official throws, matches separate. CC BY-SA 4.0, FTN Data via nflverse. Missing is not false. |',
        '| CP/CPOE | Columns located; withheld from this model | Auxiliary-model/version/availability provenance not qualified; not catchability. |',
        '| WR/TE starting alignment, untargeted routes, QB-receiver route exposure | Not present in inspected PBP/FTN charting subset; C owns source/export | Actual alignment/targets-per-route SOURCE_BLOCKED pending full route denominators. Thrown-ball destination is not alignment; snap is not route. |',
        '| Rushing direction/gap and allocation | A owns actual experiment/export | No duplicate B rushing model; consume owner result when actually delivered. |', '',
        'One source-staging filter initially excluded a stat-credited no-play attempt. It was fixed before all model fits, and 2,901 official attempt/completion rows now reconcile; original staging bytes remain. One physical-participation state remains unknown in source history, outside the new 2025–2026 evaluation. No historical win count was changed.', '',
        'Explicit component laws integrate predicted QB attempts and predicted down/depth mixture. Conditional completion coefficients and context weights are point estimates; exposure follows a declared gamma-Poisson moment law. This is not a full Bayesian posterior. Direct forests have no invented component forecasts. Actual-exposure/context substitution is a postgame diagnostic and never enters the saved full-game prediction.', '',
        'The portable JSON consumer had an order-sensitive coefficient restoration path. The current writer’s order preserved the pilot; v2 explicitly binds coefficient order and reproduces sorted-JSON consumption. No NFL score contamination was demonstrated. Independent tests reproduce all pilot outputs and representative later typed models. The outcome/forecast records remain unchanged.', '',
        'Source age and latest prior game are retained. Global source-clock fields are upper bounds where a model uses only own history; the scope amendments distinguish E0 and FTN F1 own inputs. The seven-day policy is not an authenticated observation-clock experiment or a claimed freshness improvement.', '',
        '## Original records and other category status', '',
        'The original Week 8 table and prior full category leaders are linked by immutable hashes in PRESERVED_CATEGORY_TABLE_BINDINGS.json; neither was regraded for this presentation. The 205/415 original record and 224/415 always-Under diagnostic remain unchanged, with 12 unknowns. Old fixed-Friday Week 7 and rolling Week 7 records remain separate.', '',
        '| Category | This new B wave | Existing evidence / exact next owner action |','|---|---|---|']
    for target in s_targets():
        status='Completed 2025full/2026W1-8 numerical, W5-8 actual-line only'if target in('pass_cmp','pass_att')else'Not newly fitted in this bounded QB wave'
        action='B/offer owner: fifth qualified actual-line week and missing W1-4/annual clocks; no fabricated thresholds'if target in('pass_cmp','pass_att')else'A context/export owner'if target in('rush_yd','rush_att')else'C alignment/targeting exporter; B exact-line evaluator'if target in('rec','rec_yd')else'No matching rushing-or-receiving event offer in inspected boards'if target=='anytime_td'else'No matching exact chart-PPR offer; scoring contract unchanged'if target=='nick-chart-ppr-v1'else'B existing next QB component targets / retained championship; new input qualification and finite registration required'if target.startswith('pass_')else'Joint components queued; no component-sum median assumption'
        lines.append('| '+target+' | '+status+' | '+action+' |')
    lines += ['', 'All earlier losses, tiny/fallback-only maxima, per-side leaders and tied procedures remain in the earlier complete all-method tables. They are not replaced by this new two-category wave. Complete W1–8/historical actual-line championship remains PARTIAL.', '',
        '## Selection timing, uncertainty and release decision', '',
        'Top-6/10/20 applies separately per category, week and combined/Over-only/Under-only pool. Game-kickoff batches consume remaining slots; ranks use legitimate selected-side probabilities with canonical ties. Fewer qualifying picks remain fewer. The original earlier quotes are not authenticated executable kickoff quotes, so these are timing-unverified rolling diagnostics, never a fixed Thursday weekly list. Cumulative counts sum four disjoint canonical weekly views and add no NFL observations. No changed website Top Picks replay or six-leg ticket is implied.', '',
        'Keep incumbent selection/probability products for this package. F2 median is a current-year numerical research candidate, with a historical loss and incomplete incumbent/cross-session current-panel comparison. Its numerical duration floor is met; deterministic historical adapter parity is checked, but authentic live-input/current-query inference, consumer admission and served candidate values are not established. These specific operational requirements, not a new waiting period or universal profitability gate, prevent claiming a released improvement.', '',
        'The production owner’s November 6 20:21:52 UTC (2:21:52 p.m. CST) reference generation and 20:21:54 capture are retained at 11278d99. Six current Git/served payload pairs match; 1,561 captured rows/14 games, overlay DISABLED_USE_R0 and zero research rows. Top Picks are 12 Overs plus 12 Unders: 23 match the current capture; one carries an older frozen proof and is not silently replaced by this refresh. This is data-consumer byte verification, not a rerun browser test or B release. Registered producer still binds dad58d45; A’s history repair/current Count A handoff remains its producer/owner task.', '',
        'The old missing-only archive dependency remains 38 parts/796,917,760 bytes for 147 strict-HGB origins and 736 older exact D1/D2 output cells. No unchanged upload was retried. The new licensed small public-derived inputs, JSON models and forecast chunks use their own GitHub retention/readback lane; no restricted archive was moved publicly.', '',
        'Exact next work: C intake the immutable B contribution; source owner qualifies earlier CMP/ATT thresholds/time and annual owner-local boards; A/C deliver their owned context outputs; B executes next QB gain/event components only under a distinct finite source/fit registration. New 2022–2024 context evaluations need an earlier-only configuration/startup rule, because this recipe selected settings using 2024 validation; those years cannot be retroactively called untuned held-out tests.', '',
        '## Permanent evidence', '',
        '[All method/side rows](ALL_METHOD_SIDE_TABLE.csv) · [Canonical base scores](qb-scores-v1/SCORES.json) · [FTN scores](qb-charting-scores-v1/SCORES.json) · [Matched controls/right-and-wrong/components](component-and-controls-v1/SCORES.json) · [Source/clock metadata correction](qb-scores-v1/SOURCE_PERIOD_HISTORY_METADATA_ANNOTATIONS_V2.json) · [Cumulative Top-K projection](TOPK_CUMULATIVE_COUNT_PROJECTION.json) · [Product qualification](PRODUCT_QUALIFICATION.json) · [Permanent index](results-index-v1/INDEX_MANIFEST.json) · [Paired index](paired-analysis-index-v1/ANALYSIS_MANIFEST.json) · [Independent calculations](independent/) · [Owner capture witness](OWNER_CAPTURE_AND_SERVED_STATUS_V1.json).', '']
    (BASE/'B_PLAYER_CONTEXT_MATCHUP_REPORT.md').write_text('\n'.join(lines))
    print('Rendered',len(methods),'method-period rows;',len(cumulative),'derived TopKcount rows;',len(qualification),'exact point-duration rows')

def s_targets():return ('pass_yd','pass_td','pass_cmp','pass_att','pass_int','rush_yd','rush_att','rec','rec_yd','rush_rec_yd','anytime_td','nick-chart-ppr-v1')
if __name__=='__main__':main()
