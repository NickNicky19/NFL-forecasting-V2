"""Render existing source/availability support; never score or rank forecasts."""
import argparse
import ast
import collections
import csv
import hashlib
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load(p):
    return json.loads(p.read_bytes())


def side(v):
    return f"{v['wins']}–{v['losses']}/{v['decided']}/{100*v['rate']:.2f}%" if v and v.get('decided') else 'N/A'


def main():
    ap = argparse.ArgumentParser()
    for name in ['C-category-source', 'schedule', 'schedule-readback', 'native-source-bindings']:
        ap.add_argument('--' + name, type=Path, required=True)
    a = ap.parse_args()
    out = Path(__file__).resolve().parent
    base, repo = out.parent, out.parents[3]
    now = datetime.now(timezone.utc).isoformat()
    def write(name, value):
        (out/name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
    rp = base/'roster/FROZEN_B_CONTRIBUTION_ROSTER_V1.json'
    roster = load(rp)
    pp = base/'source-policy/FROZEN_NAMED_COMPLETION_PANEL_V1.json'
    panel = load(pp)
    contract = load(out/'CURRENT_C_CONTRACT_AND_INTAKE_V1.json')
    Cstatus = {r['category']: r for r in load(out/'C_TWELVE_SOURCE_STATUS_V1.json')['rows']}
    Cbinding = next(r for r in contract['sources'] if r['label'] == 'C_CATEGORY_DECISIONS')
    assert sha(a.C_category_source) == Cbinding['sha256']
    Ccats = load(a.C_category_source)['categories']
    assert len(roster['candidates']) == roster['candidate_count'] == 59
    assert sha(rp) == panel['roster_sha256']
    schedule_hash = '14d32c7b5ea24be56441d3fca6ab0d6683bea52b42f4a4e541fd1403a6bf29b2'
    assert sha(a.schedule) == schedule_hash
    schedule = list(csv.DictReader(a.schedule.open()))
    assert len(schedule) == 272
    assert all(r['season'] == '2026' and r['game_type'] == 'REG' for r in schedule)
    bygame = {r['game_id']: r for r in schedule}
    byespn = {r['espn']: r for r in schedule}
    assert len(bygame) == len(byespn) == 272
    scheduled = collections.Counter(int(r['week']) for r in schedule)
    assert [scheduled[w] for w in range(1, 10)] == [16,16,16,16,15,14,14,14,15]
    readback = load(a.schedule_readback)
    spec = importlib.util.spec_from_file_location('retained_offer_iterator', repo/'reports/player-context-matchup-01/B/independent/inventory_retained_qb_offers_v1.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sources = {int(w): Path(p) for w,p in load(a.native_source_bindings).items()}
    offers = [r for w,p in sorted(sources.items()) for r in module.iter_offers(p,w) if r['target'] == 'pass_cmp']
    assert len(offers) == 142
    alias_path = repo/'nfl_v2/week8_shadow.py'
    aliases = next(ast.literal_eval(n.value) for n in ast.parse(alias_path.read_bytes()).body
                   if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='TEAM_ALIASES' for t in n.targets))
    assert aliases == {'LAR':'LA'}
    direct_team_matches = 0
    alias_team_matches = 0
    for r in offers:
        g = bygame[r['game_id']]
        assert g == byespn[str(r['source_game_id'])]
        assert int(g['season']) == r['season'] == 2026
        assert int(g['week']) == r['week']
        direct_team_matches += r['team'] in (g['home_team'],g['away_team'])
        alias_team_matches += r['team'] not in (g['home_team'],g['away_team'])
        assert aliases.get(r['team'],r['team']) in (g['home_team'],g['away_team'])
    counts = {1:10,2:25,3:26,4:23}
    counts.update(collections.Counter(r['week'] for r in offers))
    games = {int(w): n for w,n in panel['eligible']['source_games_by_week'].items()}
    for w in range(5,10):
        assert games[w] == len({r['game_id'] for r in offers if r['week'] == w})
    sourceweeks = [dict(season=2026,week=w,scheduled_games=scheduled[w],covered_games=games[w],eligible_offers=counts[w],game_coverage=games[w]/scheduled[w],
                        source='A_ANNUAL_NJ_OWNER_LOCAL' if w<5 else 'B_NATIVE_DK_SLEEPER',quote_clock='UNKNOWN',main_alternate='UNCLASSIFIED',
                        tier='TIER_B_RETAINED_REAL_LINE_DIAGNOSTIC',
                        raw_membership_check='OWNER_LOCAL_ONLY_PRIVATE_PARITY_UNKNOWN' if w<5 else 'CANONICAL_GAME_ESPN_SEASON_WEEK_TEAM_MATCH') for w in range(1,10)]
    write('SCHEDULE_AND_PANEL_COVERAGE_V1.json',dict(id='B_W1W9_SCHEDULE_AND_COMPLETION_COVERAGE_v1',at_UTC=now,
        source=dict(filename='schedule.csv',SHA256=schedule_hash,bytes=a.schedule.stat().st_size,rows=272,season=2026,game_type='REG',
                    readback_commit=readback.get('commit'),readback_UTC=readback.get('observed_UTC'),readback_receipt_SHA256=sha(a.schedule_readback),
                    representation='Previously retained C schedule projection; no original remote path or earlier source vintage invented'),
        weeks=sourceweeks,scheduled_games=136,covered_games=119,eligible_offers=226,player_games=226,game_coverage=119/136,
        native_identity_checks=dict(canonical_game=142,ESPN_event=142,same_canonical_source_event=142,season_week=142,
            exact_team=direct_team_matches,existing_alias_team=alias_team_matches,team_after_existing_alias=142,
            team_alias_contract=dict(path='nfl_v2/week8_shadow.py',SHA256=sha(alias_path),aliases=aliases)),
        limits=['119/136 games is not complete offered-player or league-wide offer coverage. Unretained offers are not abstentions.',
                'Combined QB statistical appearances and this projection are not an authenticated ex-ante roster universe.',
                'Quote clocks remain unknown; Tier B diagnostic is not original pregame issuance. Main/alternate stays unclassified.',
                'Annual A W5 and older A W6-W7 reference thresholds excluded; independent native later real-line records retained.',
                'A early private membership/source-clock parity remains unknown outside owner-local execution.'],new_source_reads=0,new_fits=0,new_scores=0,new_NFL_games=0))
    legacy = load(base/'legacy-completion-extension/RUN_RECEIPT_V1.json')
    modern = load(base/'modern-completion-extension/RUN_RECEIPT_V1.json')
    assert legacy['state'] == 'COMPLETE_FOUR_MISSING_STRICT_CURRENT_ORIGIN_FITS'
    assert modern['state'] == 'COMPLETE_THREE_EXISTING_ORIGIN_FITS'
    matrix = []
    for x in roster['candidates']:
        cid = x['candidate_id']
        e = x.get('existing_scoped_evidence') or {}
        reported = e.get('weeks',e.get('actual_weeks',[]))
        cells = []
        for w in range(1,10):
            fixed = 'NOT_RECONCILED_TO_FROZEN_NINE_WEEK_SOURCE_PANEL'
            if cid.startswith('B-NUMERIC-'):
                s = 'NUMERICAL_EVENT_ONLY_NOT_ACTUAL_LINE_WEEK_EVIDENCE'
            elif cid in ('B-CMP-B0','B-CMP-B1','B-CMP-B2'):
                s = 'COMPLETED_A_OWNER_LOCAL_84_JOIN' if w<5 else 'COMPLETED_NATIVE_OFFER_VIEW'
                fixed = 'FIXED_SOURCE_POLICY_BOUND;ROOT_CANONICAL_UNION_SCORE_PENDING'
            elif cid in ('B-CMP-E3','B-CMP-F2','B-CMP-P1'):
                s = 'SAVED_OUTPUT;REUSE_MATCHING_OWNER_JOIN_WHERE_BOUND' if w<5 else 'SAVED_NATIVE_OUTPUT'
                if w == 9:
                    s = 'MISSING_ORIGIN_FIT_AND_INFERENCE_NOW_COMPLETE'
                fixed = 'EXACT_OUTPUT_JOIN_AND_ROOT_CANONICAL_SCORE_PENDING'
            elif cid.startswith('B-CMP-LEGACY-'):
                s = 'EXISTING_ORIGIN_OUTPUT;EARLY_EXACT_PANEL_JOIN_NOT_BOUND_HERE' if w<8 else 'REQUIRED_ORIGIN_FIT_AND_INFERENCE_NOW_COMPLETE'
                fixed = 'EXACT_OUTPUT_JOIN_AND_ROOT_CANONICAL_SCORE_PENDING'
            elif cid == 'B-ATT-COMMON-EXPOSURE':
                s = 'EXISTING_ANALYTIC_OUTPUT_OR_POLICY;EXACT_PANEL_JOIN_NOT_BOUND_HERE' if w<9 else 'ANALYTIC_W9_INFERENCE_NOT_ESTABLISHED_IN_THIS_RECEIPT'
            else:
                s = 'PUBLISHED_PRIOR_SCOPED_OFFER_VIEW;DIFFERENT_SOURCE_MASK' if w in reported else 'EXACT_WEEK_SOURCE_OUTPUT_JOIN_NOT_ESTABLISHED_BY_FROZEN_ENTRY'
            cells.append(dict(week=w,state=s,fixed_panel_score_state=fixed,prior_scoped_reported_week=w in reported,
                              selected=None,decided=None,unknown=None,unavailable=None,count_scope='Availability metadata; actual counts belong to canonical scores or bound prior record.'))
        matrix.append(dict(candidate_id=cid,category=x['category'],procedure_id=x['procedure_id'],origin=x.get('origin'),
            output=x.get('output',x.get('outputs')),decision_policy=x.get('decision_policy',x.get('decision_policies')),
            original_roster_status=x['status'],prior_scoped_panel=e.get('panel'),prior_scoped_offer_weeks=reported,
            alias_of=x.get('alias_of'),weeks=cells,next_executor='B original method/output owner',
            next_action='Reuse saved outputs and completed exact-identity joins; bind only missing compatible source/output cells under C common policy. No repeated completed fit.'))
    category_weeks = []
    for category_entry in roster['categories']:
        cat = category_entry['category']
        prior_offers = [r for r in roster['candidates'] if r['category']==cat and r['candidate_id'].startswith('B-EXISTING-')]
        Bweeks = sorted({w for r in prior_offers for w in (r['existing_scoped_evidence'].get('weeks',r['existing_scoped_evidence'].get('actual_weeks',[])))})
        ownC = Cstatus[cat]['C_scored_procedure_source_coverage']['actual_source_weeks']
        cells = []
        for w in range(1,10):
            source_states = []
            if cat not in ('anytime_td','nick-chart-ppr-v1') and w<=5:
                source_states.append('A_ANNUAL_REAL_LINE_DIAGNOSTIC_PRIOR_SCOPED;NOT_ALL_CONTENDERS')
            if w in Bweeks:
                source_states.append('B_PRIOR_SCOPED_ACTUAL_SOURCE_VIEW;EXACT_CONTRACT_AND_MASK_RETAINED')
            if w in ownC:
                source_states.append('C_PROPLINE_REAL_LINE_DIAGNOSTIC_PRIMARY_AND_SENSITIVITIES')
            if cat=='pass_cmp':
                source_states.append('FIXED226_NINE_WEEK_SOURCE_ROW_BOUND')
            cells.append(dict(week=w,actual_source_status=source_states or ['NO_MATCHING_REAL_LINE_PANEL_BOUND_IN_INSPECTED_RECORDS;RETAINED_INVENTORY_RECONCILIATION_REQUIRED'],
                reference_only_package_present=w in (6,7) and cat not in ('anytime_td','nick-chart-ppr-v1'),
                complete_all_contender_comparison='ROOT_COMPLETION_SCORES_PENDING' if cat=='pass_cmp' else 'NOT_ESTABLISHED',
                selected=None,decided=None,unknown=None,unavailable=None,
                next_executor='C common evaluation/intake coordinator',
                next_action='Reuse bound prior scopes and resolve exact candidate/source cells; do not count reference thresholds, duplicate sources or numeric forecasts as actual offers.'))
        category_weeks.append(dict(category=cat,weeks=cells))
    write('WEEK_COMPLETION_MATRIX_V1.json',dict(id='B_FROZEN59_NINE_WEEK_EXECUTION_SUPPORT_v1',at_UTC=now,roster_id=roster['id'],roster_SHA256=sha(rp),candidate_count=59,
        scope='B contribution to existing C comparison, not a new master roster or ranker',source_weeks=sourceweeks,candidates=matrix,categories=category_weeks,
        superseding_fit_receipts=[dict(path='../legacy-completion-extension/RUN_RECEIPT_V1.json',SHA256=sha(base/'legacy-completion-extension/RUN_RECEIPT_V1.json'),state=legacy['state']),
                                 dict(path='../modern-completion-extension/RUN_RECEIPT_V1.json',SHA256=sha(base/'modern-completion-extension/RUN_RECEIPT_V1.json'),state=modern['state'])],
        rules=['Saved forecasts are not scored offers or quote-time authentication. Null counts here mean not rendered, not zero.',
               'Source coverage, scored weeks, decision weeks and complete league coverage remain separate.',
               'Frozen roster old fit-required states are superseded only by named completed execution receipts; no roster rewrite.',
               'Reuse R0/F0/F1/R2/R3 receipts only with exact code/output/history identity; matching totals do not prove aliases.',
               'Root canonical SCORES and C admission may supersede pending score statuses. No new score was calculated here.']))
    rows = []
    fields = ['origin','exact_procedure','output','decision_policy','role_scope','actual_weeks_by_season','OVER','UNDER','COMBINED','coverage','controls','uncertainty','evidence_tier','five_week_status','decision']
    for x in Ccats:
        cat = x['category']
        entries = [y for y in roster['candidates'] if y['category'] == cat]
        p = {k:x.get(k) for k in fields}
        annual = next((v for v in x.get('highest_observed_panels',[]) if v.get('panel_id') == 'A14A_SOURCE_BOUND_ANNUAL_NJ_W1_W5'),{})
        p['tied_candidate_set'] = annual.get('tied_candidate_set')
        p['source_panel'] = 'A14A_SOURCE_BOUND_ANNUAL_NJ_W1_W5' if p['COMBINED'] else None
        p['scope'] = 'PREVIOUS_SCOPED_C_ADMISSION_NOT_NEW_NINE_WEEK_LEADER;OWNER_LOCAL_PRIVATE_PARITY_UNKNOWN'
        if cat == 'pass_cmp':
            state = 'NINE_SOURCE_WEEKS_FIXED226;EXACT_CONTENDER_COMPARATIVE_SCORING_IN_PROGRESS'
            action = 'Admit fixed226 Tier B panel; bind completed missing-origin outputs and strongest A/C controls to SAME rows, then intake root canonical scores and remaining candidate gaps.'
            missing = 'All nine source weeks represented, partial within-week coverage. Later A strong-control outputs and any existing C completion nominations still need exact bindings.'
        elif cat in ('anytime_td','nick-chart-ppr-v1'):
            state = 'SOURCE_BLOCKED_EXACT_OFFER_DIRECTION;EVENT_NUMERICAL_EVIDENCE_SEPARATE'
            action = 'Check approved retained exact-contract offer inventory once; bind qualified rows or preserve missing W1-W9 offers. Do not invent Anytime NO or replace exact chart.'
            missing = 'No compatible exact actual-offer direction panel in inspected admitted source record; all nine direction-source cells unfilled.'
        else:
            state = 'PARTIAL_SCOPED_PANELS;NO_COMMON_NINE_WEEK_CATEGORY_WINNER_ESTABLISHED'
            action = Cstatus[cat]['next_action']
            missing = 'A named annual W1-W5 and separate B/C scoped panels do not establish common nine-week all-contender comparison. Older A W6-W7 mixed-package references cannot fill actual offers; independent later native rows need their own exact bindings.'
        live = x.get('actual_live_method') or {}
        rows.append(dict(category=cat,status=state,prior_scoped_C_record=p,B_frozen_contender_count=len(entries),
            B_frozen_contender_ids=[y['candidate_id'] for y in entries],
            B_prior_scoped_offered_records=[dict(candidate_id=y['candidate_id'],procedure_id=y['procedure_id'],output=y.get('output'),decision_policy=y.get('decision_policy'),evidence=y['existing_scoped_evidence']) for y in entries if y['candidate_id'].startswith('B-EXISTING-')],
            C_own_source_coverage=Cstatus[cat]['C_scored_procedure_source_coverage'],missing_or_incomplete=missing,
            next_executor='C common evaluation/intake coordinator',next_action=action,
            website_retained_snapshot=dict(commit=contract['C_current_main_commit'],actual_primary=live.get('website_actual_primary'),
                direction=live.get('category_direction'),operational_disposition=live.get('website_operational_candidate_disposition'),research_primary_rows=live.get('research_primary_rows'),
                scope='Prior owner receipt only; no new served-byte verification or activation'),
            new_release_decision='NONE_FROM_THIS_METADATA_RENDER;EXISTING_C_AND_WEBSITE_ADMISSION_AUTHORITY_RETAINED'))
    write('HEADLINE_SUPPORT_V1.json',dict(id='B_ALL_TWELVE_W1_W9_HEADLINE_SUPPORT_v1',at_UTC=now,C_source_commit=contract['C_current_main_commit'],C_category_source_binding=Cbinding,
        B_roster_id=roster['id'],B_roster_SHA256=sha(rp),current_intake_delta=contract['current_C_intake'],categories=rows,
        limits=['Not a new category ranking or new score artifact. Disconnected scoped panels cannot establish a global winner.',
                'All displayed Over/Under/combined records belong to the SAME exact procedure and own decided pool.',
                'Pinned C explicitly reports corrected COUNT_A_MEAN and COUNT_A_LEGACY_POINT as annual49/86 tied products; private parity not independently checked.',
                'Missing fallback attribution remains unknown. Five retrospective duration weeks do not authenticate quote clocks or authorize activation.',
                'Root immutable canonical SCORES supplies new226 numerical/probability/direction comparisons; this render adds no grades.']))
    md = ['# All-twelve support for the fixed W1–9 comparison','',
        'The completion source contract is fixed at **226 retained offers across all nine weeks and 119 games**. The schedule contains 136 games in those weeks. This adds procedure coverage using existing games, not new NFL observations. New comparison metrics belong to root canonical SCORES.','',
        'The following are **previously published scoped W1–5 actual-line diagnostic records**, not new W1–9 category leaders. B and C partial panels keep their own masks and linked records. Quote timing remains unverified.','',
        '| Category | Prior scoped procedure / origin | Actual 2026 weeks | Own Over W–L/N/% | Own Under W–L/N/% | Own combined W–L/N/% | Eligible / available / selected / unknown / fallback | Current support / C action |',
        '|---|---|---|---|---|---|---|---|']
    for x in rows:
        p=x['prior_scoped_C_record'];proc=p['exact_procedure'] or 'N/A: exact offer direction absent'
        if x['category']=='pass_td':proc='COUNT_A_MEAN / LEGACY_POINT reported tie (A)'
        elif '::' in proc:proc=' / '.join(proc.split('::')[-2:])+f" ({p['origin']})"
        cov=p['coverage']or{};cs='/'.join(str(cov.get(k))if cov.get(k)is not None else'N/A'for k in ['eligible','available','selected','unknown','fallback'])
        ws=','.join(map(str,(p.get('actual_weeks_by_season')or{}).get('2026',[])))or'none'
        action='Fixed 226; root scores/control bindings pending'if x['category']=='pass_cmp'else('Exact offers absent; inspect retained inventory'if x['category']in('anytime_td','nick-chart-ppr-v1')else'Partial; bind missing exact weeks/masks')
        md.append('| '+' | '.join(str(v).replace('|',' / ')for v in [x['category'],proc,ws,side(p['OVER']),side(p['UNDER']),side(p['COMBINED']),cs,action])+' |')
    md += ['', 'Exact IDs, ties, roles, controls, uncertainty, prior operational snapshots and one coordinator action per category are in [HEADLINE_SUPPORT_V1.json](HEADLINE_SUPPORT_V1.json). The [frozen 59-entry B roster](../roster/FROZEN_B_CONTRIBUTION_ROSTER_V1.json) links each contender’s own records, including tiny/fallback-only maxima. Percentages on disconnected masks cannot select a global winner.','',
        'C already admitted B FTN public arithmetic and website V7 five-block policy at its stated partial conditional retrospective tier. Its inspected pin predates A’s completed 84-offer join at 5a41 and B’s acd32c8e closure: intake those exact receipts rather than repeat either calculation.','',
        'Older A W6–7 values in the mixed annual package are reference thresholds. Independent native later offers retain their own qualification. Fixed completion precedence excludes annual A W5 to avoid duplicate source opportunities. Main/alternate remains unclassified and unknown clocks remain unknown.','',
        'Research SHADOW and operational KEEP_INCUMBENT differ in purpose; neither means a listed research product is active or that the incumbent is proved best. This local render adds no source reads, fits, scoring, releases or future captures.','']
    (out/'HEADLINE_SUPPORT_V1.md').write_text('\n'.join(md))
    md=['# Completion week and execution support','',
        'Fixed source panel: 226 offers/player-games, 119/136 scheduled games (87.5%), all nine weeks represented. Game coverage is not complete offered-player coverage. Counts below describe source opportunities, not decisions by every candidate.','',
        '| Week | Scheduled games | Offer games | Retained offers | Source | Quote clock | Evidence |','|---|---|---|---|---|---|---|']
    for x in sourceweeks:md.append(f"| {x['week']} | {x['scheduled_games']} | {x['covered_games']} | {x['eligible_offers']} | {x['source']} | UNKNOWN | Tier B real-line diagnostic |")
    md += ['', 'All 142 native rows match canonical game and ESPN event IDs and season/week. Team checks match 137 directly and 5 through the existing LAR→LA alias. Early A membership remains owner-local; public arithmetic is not private-row/source-clock verification. Schedule commitments are in [SCHEDULE_AND_PANEL_COVERAGE_V1.json](SCHEDULE_AND_PANEL_COVERAGE_V1.json).','',
        'The [machine matrix](WEEK_COMPLETION_MATRIX_V1.json) explicitly covers 59 frozen entries × 9 weeks, plus all twelve category/source-week statuses. Null decision counts here mean not rendered in availability metadata; use immutable canonical scores or bound prior records.','',
        '| Candidate group | W1–4 | W5–7 | W8 | W9 | Existing executor / next action |','|---|---|---|---|---|---|',
        '| B0/B1/B2 FTN completion | Completed A84 joins | Existing native views | Existing native view | Existing native view | B/root maps fixed-panel scores; C admits actual scope. B1 remains alias. |',
        '| E3/F2/P1 completion | Saved outputs; reuse exact matching owner joins | Existing saved outputs | Existing saved outputs | Missing-origin inference COMPLETE | B/root finishes exact output/score bindings, no repeat fits. |',
        '| Ordered-leaf / GLM completion | Existing origins; exact early join not bound here | Existing origins | Required origin inference COMPLETE | Required origin inference COMPLETE | B/root reuses legacy extension; resolves only missing exact-panel cells. |',
        '| Common-exposure attempts | Existing analytic policy; separate annual receipt | Existing policy/output | Existing output | Analytic inference not established here | B supplies unchanged-policy append if still needed; C reconciles offers. |',
        '| Other B offered endpoints | Exact new-panel cells remain unfilled | Prior W5–7 native / W2–3 C-board views | No union claim | No union claim | B supplies existing output bindings; C resolves common source masks. |',
        '| Numerical/event-only entries | Not actual-offer evidence | Not actual-offer evidence | Not actual-offer evidence | Not actual-offer evidence | C retains offer gaps until qualified exact-contract lines exist. |','',
        'The four legacy and three modern missing-origin fits are complete under their existing executors. This receipt updates status only: additional forecasts/fits are not NFL games. Root canonical scores may supersede pending states without rewriting frozen source/roster records.','']
    (out/'WEEK_COMPLETION_MATRIX_V1.md').write_text('\n'.join(md))
    print(json.dumps(dict(state='COMPLETE_METADATA_RENDER_NO_NEW_SCORING',categories=len(rows),candidates=len(matrix),weeks=9,scheduled_games=136,covered_games=119,eligible=226,native_identity_checks=142,new_reads=0,new_fits=0,new_scores=0)))


if __name__ == '__main__':
    main()
