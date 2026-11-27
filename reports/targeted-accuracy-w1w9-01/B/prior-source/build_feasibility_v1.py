"""Bounded source/prior-use receipt; no fitting, inference or grading."""
import collections
import datetime
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
BASE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, value):
    (BASE / name).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def main(cache):
    at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    a = '3f10b641134658d3036933928cf2fa08dac4083c'
    c = '2b8bbc6da7bfb90106d7956cf86ccc160f2a343e'
    table = []
    inside = False
    for line in (cache / 'A_FINAL_REPORT_DECODED.txt').read_text().splitlines():
        if line.startswith('| Category |'):
            inside = True
            continue
        if inside and line.startswith('|---'):
            continue
        if inside and not line.startswith('|'):
            break
        if inside:
            columns = [value.strip() for value in line.strip().strip('|').split('|')]
            assert len(columns) == 7
            table.append(dict(zip(['category', 'reported_procedure_or_ties', 'actual_2026_weeks', 'own_Over_W_L_N', 'own_Under_W_L_N', 'own_combined_W_L_N_pct', 'status_recommendation'], columns)))
    assert len(table) == 12
    write('LATEST_A_TWELVE_REPORTED_ROWS_V1.json', {
        'id': 'B_NORMALIZED_A_SUPERSEDING_W1W9_CHECKPOINT_v1', 'at_UTC': at,
        'source_repository': 'NickNicky19/NFL-forecasting', 'source_commit': a,
        'source_path': 'reports/abc-championship/w1w9-comparison-closure-01/FINAL_A_CHECKPOINT_V1.md',
        'normalized_decoded_source_sha256': sha(cache / 'A_FINAL_REPORT_DECODED.txt'),
        'byte_qualification': 'Normalized connector-decoded text, not original wire/file byte identity.',
        'state': 'REPORTED_OWNER_RESULTS_NOT_PRIVATE_ROW_REGRADE', 'rows': table,
        'source_policy': 'A annual W1-4 plus native W5-9 for CMP; native W5-7 for other completed categories. Annual W5 remains separate overlap sensitivity. Annual W6-7 references excluded. Quote clocks/main-alt/settlement unknown, current-vintage seven-day reconstruction, exposed development.',
        'new_control_receipts': 'C E0_ENV mean102/226 and median107/226 now owner-locally joined. A Cat/HGB early51/84 still lack later142 exact outputs. B2 median/law122 vs B0 median/law117, B0 mean119, AlwaysOver115 on226.',
        'coverage_limits': [
            'All12 cross-session W1-9 remains PARTIAL; nine other categories now W1-7 after1852 native offer joins.',
            'Rec full-board median595-450/1045 with1127/1128 forecasts and82 unknowns differs from common modeled594-449/1043.',
            'C receiving-yard common1057 advantage is not complete-system win:77 full-board unavailable.',
            'Original Backfield Top6 is29-13/42,11.08%coverage, no gain over same-case mean controls.',
            'Markdown row extraction does not authenticate raw membership, role masks, source clocks or model fits.'
        ]})
    depth_path = ROOT / 'reports/player-context-completion-decision-01/B/source-depth-v1/FTN_DEPTH_QB_GAME_INPUTS.json.gz'
    context_path = ROOT / 'reports/information-first-20261112-01/B/completion-wave-v1/QB_CONTEXT_W1_W9_INPUTS_V1.json.gz'
    depth = json.loads(gzip.decompress(depth_path.read_bytes()))
    contexts = json.loads(gzip.decompress(context_path.read_bytes()))
    if isinstance(contexts, dict):
        contexts = contexts['rows']
    cutoff = min(row['kickoff'] for row in contexts if row['season'] == 2026 and row['week'] == 9)
    eligible = [row for row in contexts if row['available'] < cutoff]
    keys = {(row['game_id'], row['player_id']) for row in depth}
    missing = [row for row in eligible if (row['game_id'], row['player_id']) not in keys]
    assert not missing
    write('CHART_DEPTH_W9_ELIGIBILITY_V1.json', {
        'id': 'B_M2_EXISTING_CHART_DEPTH_W9_SUPPORT_v1', 'state': 'ELIGIBLE_DEPTH_KEYS_COMPLETE_NO_NEW_SOURCE_REQUIRED',
        'depth': {'path': str(depth_path.relative_to(ROOT)), 'sha256': sha(depth_path), 'rows': len(depth), '2026weeks': sorted({row['week'] for row in depth if row['season'] == 2026})},
        'contexts': {'path': str(context_path.relative_to(ROOT)), 'sha256': sha(context_path), 'rows': len(contexts)},
        'W9weekly_fit_cutoff_UTC': datetime.datetime.fromtimestamp(cutoff, datetime.timezone.utc).isoformat(),
        'eligible_historical_rows': len(eligible), 'missing_depth_keys': len(missing),
        'eligible_W8_rows': sum(row['season'] == 2026 and row['week'] == 8 for row in eligible),
        'target_W9_charting_consumed': False,
        'qualification': 'Existing W8 depth rows suffice for W9 earlier-only features. Current-vintage7day strict< proxy remains a reconstruction; date_pulled is retrieval, not authenticated original publication.'})
    classifications = [
        ('P1/P2/P3 conditional GLM', 'ALREADY_TESTED', '25 down-by-depth contexts; own earlier conversion logit, opponent overall/context residuals, team residual; team/opponent effects and P2 QB intercepts. Fixed gamma-Poisson attempts plus binomial thinning. P2 law53/112 vs P1/P3 54, E3 58 and prevalence59.'),
        ('Depth catchability C1/C2 and D1/D2', 'EQUIVALENT_TEST_COMPLETE', 'Five FTN depth-specific catchability logits/support were already tested. C2 ties C1 54/112; D2 loses D1 49vs52. Catchability, completion, drop and unknown annotations remain distinct.'),
        ('R0-R3 opportunity/defense; FTN B0/B2', 'ALREADY_TESTED', 'Retain failed/inconclusive profile and two aggregate throwaway/IWP additions. Full226 B2mean112 vs B0mean119, B2median/law122 vs B0median117; poorer probability scores and stronger-control gaps persist.'),
        ('QB learned conversion dispersion', 'GENUINELY_NEW_QUALIFIED_COMBINATION_IN_INSPECTED_B_SCOPE', 'A separate learned beta-binomial conversion precision integrated against the unchanged predicted attempt law differs from retained fixed-conversion binomial thinning. It is not globally new math: A2/A3 use NB-beta-binomial rushing allocation. Mean/context/history controls and C<=A must stay explicit.'),
        ('Complete receiver/destination/distance feature scope', 'PARTIAL', 'Current P2 consumes down-by-depth, not destination/alignment. ContextHistory computes lagged distance/field/time/score summaries but retained _conditional_x omits them. Qualified receiver-group/all-route inputs absent from inspected input. Do not claim the full original feature mechanism complete.'),
        ('Historical personnel/alignment/route block', 'SOURCE_BLOCKED', 'No authenticated event-effective teammate universe/all-route alignment in inspected B input. Later injury tables, stat appearance, pass destination and snaps cannot fill it. Blocks that block, not PBP M2.'),
        ('Independent market reference/hybrid', 'EXISTING_A_STUDIES;NEW_B_M4_ROW_ACCESS_SOURCE_BLOCKED', 'A has retained offering-book-excluded M/F/FC/FS/H v3 on2024 and2026W1-5, not a never-tested mechanism. B native284CMP/ATT records have no price fields. Exact other-book two-sided same-line prices and OOT football residual features are not bound for a new B M4.'),
        ('Separate Astra v10/v12', 'ARTIFACTS_NOT_OBTAINED', 'User-reported studies remain preserved. No exact separate Astra artifact contents obtained; no global first-use or equivalence conclusion claimed.')
    ]
    local_paths = [
        'nfl_v2/player_context_matchup.py', 'nfl_v2/qb_depth_catchability.py', 'nfl_v2/qb_depth_catchability_v2.py',
        'nfl_v2/qb_opportunity_increment.py', 'nfl_v2/qb_ftn_information.py',
        'reports/player-context-matchup-01/B/qb-wave-v1/FROZEN_PROTOCOL.json',
        'reports/player-context-completion-decision-01/B/depth-wave-v2/FROZEN_PROTOCOL.json',
        'reports/information-first-20261112-01/B/completion-wave-v1/FROZEN_PROTOCOL.json'
    ]
    write('NEW_INFORMATION_FEASIBILITY_V1.json', {
        'id': 'NFL-TARGETED-ACCURACY-W1W9-01-B-NEW-INFORMATION-FEASIBILITY-v1', 'at_UTC': at,
        'state': 'M2_SUPPORTED_WITH_DECLARED_PARTIAL_FEATURE_SCOPE;NEW_M4_NOT_EXECUTED',
        'owner': 'B; C coordinator and A/original-site ownership preserved', 'latest_A_research': a, 'latest_C_main': c,
        'classifications': [{'block': block, 'status': status, 'reason': reason} for block, status, reason in classifications],
        'local_code_protocol_bindings': [{'path': p, 'sha256': sha(ROOT / p)} for p in local_paths],
        'source_terms': 'Ordinary nflverse/nflfastR derivatives CC-BY-4.0. FTN Data via nflverse CC-BY-SA-4.0 for charting-derived arrays/models/forecasts/scores; previous source qualification retained. No protected raw offers/rosters/private locators/models exported.',
        'MATCHUP_PERSONALIZATION_mapping': 'Map new M2 to existing B player-context/conditional-completion and distribution contracts. No exact separately named MATCHUP-PERSONALIZATION-01 B artifact located in inspected registered relevant paths. Material new arm requires versioned registration, not old-roster mutation.',
        'market_existing_results': {'2026CMPevents': 58, 'CMP_Brier_F': .255434, 'CMP_Brier_M': .247206, 'CMP_Brier_H': .250552, '2026ATTevents': 46, 'ATT_Brier_F': .243263, 'ATT_Brier_M': .248612, 'ATT_Brier_H': .249421, 'limits': 'A public reported aggregates only; quote timing unverified, aged frozen football reference, no exact incumbent. Do not relabel point MAE gains as probability/direction superiority.'},
        'source_and_novelty_limits': 'Current-vintage7day reconstruction, exposed history. No source publication authentication or global all-method/Astra novelty claim. Existing closed information/offset/confidence experiments remain closed.',
        'new_NFL_fits': 0, 'new_grades': 0, 'new_original_forecasts': 0, 'new_primary_switches': 0})
    sources = [
        ('C_MAIN', 'https://api.github.com/repos/NickNicky19/NFL-forecasting-NGS-C/branches/main'),
        ('A_BAD_BRANCH', 'https://api.github.com/repos/NickNicky19/NFL-forecasting/branches/research%2Faccuracy-wave-20261026'),
        ('A_BRANCHES', 'https://api.github.com/repos/NickNicky19/NFL-forecasting/branches?per_page=100'),
        ('C_PROTOCOL', f'https://github.com/NickNicky19/NFL-forecasting-NGS-C/blob/{c}/reports/abc-championship/CURRENT_PROTOCOL.json'),
        ('C_EXPORT', f'https://github.com/NickNicky19/NFL-forecasting-NGS-C/blob/{c}/reports/abc-championship/EXPORT_INDEX.json'),
        ('A_EXPORT', f'https://github.com/NickNicky19/NFL-forecasting/blob/{a}/reports/abc-championship/EXPORT_INDEX.json'),
        ('C_W1W9_REPORT', f'https://github.com/NickNicky19/NFL-forecasting-NGS-C/blob/{c}/reports/w1w9-comparison-closure-01/README.md'),
        ('C_B_INTAKE', f'https://github.com/NickNicky19/NFL-forecasting-NGS-C/blob/{c}/reports/w1w9-comparison-closure-01/B-intake/COMPATIBILITY_AND_ADMISSION.json'),
        ('A_LATEST_COMMIT', f'https://api.github.com/repos/NickNicky19/NFL-forecasting/commits/{a}'),
        ('A_METHOD_REGISTRY', f'https://github.com/NickNicky19/NFL-forecasting/blob/{a}/reports/opportunity-four/METHOD_REGISTRY.json'),
        ('A_FINAL_REPORT', f'https://github.com/NickNicky19/NFL-forecasting/blob/{a}/reports/abc-championship/w1w9-comparison-closure-01/FINAL_A_CHECKPOINT_V1.md'),
        ('A_MARKET_REPORT', f'https://github.com/NickNicky19/NFL-forecasting/blob/{a}/reports/historical-market-comparison-no2025-v3/PUBLIC_RESULTS.md')
    ]
    observed = []
    for i, (key, url) in enumerate(sources):
        path = cache / (key + '_DECODED.txt')
        observed.append({'attempt': i + 1, 'key': key, 'url': url, 'state': 'OBTAINED' if path.exists() else 'TOOL_URL_VALIDATION_REJECTED_NO_SOURCE', 'normalized_decoded_bytes': path.stat().st_size if path.exists() else 0, 'normalized_decoded_sha256': sha(path) if path.exists() else None})
    write('SOURCE_AND_RESOURCE_RECEIPT_V1.json', {
        'id': 'B_M2_PRIOR_SOURCE_READS_v1', 'at_UTC': at, 'attempts': observed,
        'source_read_attempts': len(observed), 'allocated_source_read_attempts': 12,
        'normalized_decoded_bytes': sum(row['normalized_decoded_bytes'] for row in observed),
        'allocated_source_bytes': 8388608, 'wire_byte_qualification': 'Connector normalized UTF8 sizes, not original wire byte totals; no original file-byte hash parity inferred from parsed JSON.',
        'fits': 0, 'grades': 0, 'peer_writes': 0,
        'development_notes': 'One local dictionary-key counting probe initially used Counter.update(dict) and failed on None; corrected to update(dict.keys()). Two source-receipt scratch script constructions failed Python syntax before artifact creation. No source/model/forecast/grade changed.'})
    print(json.dumps({'source_attempts': len(observed), 'decoded_bytes': sum(row['normalized_decoded_bytes'] for row in observed), 'all12_rows': len(table), 'eligible_missing_chart_keys': len(missing)}))


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--cache', type=Path, required=True)
    main(parser.parse_args().cache)
