"""Original V2 projection of pinned upstream aggregates; never reads NFL raw feeds.

Run from repository root with the decoded public aggregate input. Extra source
inputs are optional public aggregate snapshots. Imports are reported evidence,
not independently reproduced NFL scores or authenticated original runs.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path

PIN = 'b246e44b5fa85ea46a0b6294d1347709933a5fb2'
BASE = f'https://github.com/NickNicky19/NFL-forecasting/blob/{PIN}/'


def write(rows, path):
    path.with_suffix('.json').write_text(json.dumps(rows, indent=2, allow_nan=False) + '\n')
    keys = list(dict.fromkeys(k for row in rows for k in row))
    with path.with_suffix('.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(v, separators=(',', ':')) if isinstance(v, (dict, list)) else v for k, v in row.items()})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, default=Path('reports/inventory/UPSTREAM_AGGREGATES_DECODED.json'))
    parser.add_argument('--categories', type=Path)
    parser.add_argument('--events', type=Path)
    parser.add_argument('--out', type=Path, default=Path('reports/inventory'))
    args = parser.parse_args()
    args.out.mkdir(exist_ok=True, parents=True)
    data = json.loads(args.input.read_text())
    scores = []
    years = []
    for row in data['records']:
        record = {k: v for k, v in row.items() if k not in {'metrics', 'coverage'}}
        record.update(row['metrics'])
        record['coverage'] = row['coverage']
        record['new_fits_in_V2'] = 0
        record['new_NFL_scores_in_V2'] = 0
        scores.append(record)
        period = row['period']
        match = re.fullmatch(r'20\d{2}', period)
        seasons = [int(period)] if match else [2022, 2023, 2024] if '2022' in period and ('2024' in period or '24' in period) else []
        # Years not explicitly supplied by this aggregate stay unverified.
        years.append({'record_id': row['record_id'], 'procedure_id': row['procedure_label'],
                      'target': row['target'], 'product_id': row['product_id'],
                      'evaluation_panel_id': row['evaluation_panel_id'],
                      'evaluation_period_literal': period, 'evaluation_seasons': seasons,
                      'evaluation_weeks': None, 'train_seasons': None, 'tune_seasons': None,
                      'calibrate_seasons': None, 'feature_memory_seasons': None,
                      'dates_reason': 'Compact aggregate omits exact dates; inspect pinned source/config before reuse.',
                      'status': 'REPORTED_NOT_REPRODUCED', 'source_id': row['source_id']})
    write(scores, args.out / 'ALL_METHOD_SCORES')
    write(years, args.out / 'METHOD_YEAR_INVENTORY')
    write(data['method_families'], args.out / 'METHOD_FAMILY_CATALOG')
    write(data['sources'], args.out / 'REPORTED_SOURCE_MANIFEST')

    if args.categories:
        cats = json.loads(args.categories.read_text())
        top = []
        views = []
        status = []
        for cat in cats['categories']:
            target = cat['target']
            for entry in cat['top_up_to5']:
                best = entry['best_observed_display_view']
                m = best['metrics']
                top.append({'target': target, 'rank': entry['rank'], 'family_id': entry['family'],
                            'procedure_id': best['method'], 'product_id': best['product'],
                            'evaluation_panel_id': 'upstream_1956_primary_2026_W1_W6',
                            'requested_W1_W7_ranking': False, 'history_regime': 'SOURCE_SPECIFIC_NOT_V2_CORE_H_MULTI',
                            'information_tier': 'football_history_current_vintage_reconstruction',
                            'metric': cat['ranking_score'], 'loss': m.get(cat['ranking_score']),
                            'scored': m.get('scored', m.get('n')), 'planned': m.get('planned'),
                            'games': m.get('games'), 'weeks': m.get('weeks'),
                            'bias': m.get('bias'), 'p90': m.get('p90_AE'), 'p95': m.get('p95_AE'),
                            'fallback_planned': m.get('fallback_planned'), 'fallback_scored': m.get('fallback_scored'),
                            'evidence': 'REPORTED_NOT_REPRODUCED', 'operational_admission': 'UNVERIFIED_BY_V2',
                            'source_url': BASE + 'reports/category-topfive-20261029/PUBLIC_RESULTS.json'})
                for view in entry.get('retained_views', []):
                    views.append({'target': target, 'family_id': entry['family'], 'procedure_id': view['method'],
                                  'product_id': view['product'], 'metrics': view['metrics'],
                                  'source_panel': view.get('source_panel'), 'status': 'REPORTED_NOT_REPRODUCED'})
            status.append({'target': target, 'comparable_families': cat['comparable_families_available'],
                           'research_shortfall_from_five': cat['shortfall_from5'],
                           'upstream_live_family_at_dated_read': cat['actual_website_family_from_previous_catalog'],
                           'live_identity': cat['actual_website_current_public_payload_identity'],
                           'V2_independent_live_verification': False,
                           'week7_summary': cat.get('genuine_week7_dated_summary'),
                           'horizon': cat['horizon'], 'evaluation_period': cat['period'],
                           'source_url': BASE + 'reports/category-topfive-20261029/PUBLIC_RESULTS.json'})
        write(top, args.out / 'REPORTED_TOP5_2026_W1_W6')
        write(views, args.out / 'CURRENT_RETAINED_OUTPUT_VIEWS')
        write(status, args.out / 'TWELVE_CATEGORY_EVIDENCE_STATUS')

    if args.events:
        events = [json.loads(line) for line in args.events.read_text().splitlines() if line.strip()]
        event_index = []
        for i, event in enumerate(events, 1):
            # Preserve event evidence without treating prose as canonical run IDs.
            label = event['event']
            hint = 'failed_event' if any(s in label.lower() for s in ['failed', 'failure', 'timeout', 'rejected']) else 'registration_event' if any(s in label.lower() for s in ['predeclared', 'registered', 'preregistered']) else 'other_event'
            event_index.append({'event_id': f'UEV-{i:04}', 'event_literal': label,
                                'at_literal': event.get('at'), 'classification_hint': hint,
                                'is_independent_fit_or_run': None,
                                'reason': 'An event is not necessarily a run. Originals/IDs need owner evidence.',
                                'source_url': BASE + 'execution/ledger.jsonl',
                                'source_line': i, 'evidence': 'VERIFIED_FROM_CODE'})
        write(event_index, args.out / 'EXECUTION_EVENT_INDEX')

    summary = {'upstream_commit': PIN, 'aggregate_cells': len(scores),
               'distinct_procedure_labels_NOT_canonical_procedures': len({r['procedure_label'] for r in data['records']}),
               'distinct_output_contract_labels': len({r['product_id'] for r in data['records']}),
               'distinct_evaluation_panel_labels': len({r['evaluation_panel_id'] for r in data['records']}),
               'dated_family_catalog_entries': len(data['method_families']),
               'source_manifest_entries': len(data['sources']),
               'input_projection_sha256': hashlib.sha256(args.input.read_bytes()).hexdigest(),
               'new_V2_fits': 0, 'new_V2_forecasts': 0, 'new_V2_NFL_scores': 0,
               'private_attempt_census_complete': False,
               'canonical_request_count': None, 'canonical_fit_count': None,
               'canonical_failure_count': None, 'completion_percentage': None}
    (args.out / 'INVENTORY_COUNTS.json').write_text(json.dumps(summary, indent=2) + '\n')


if __name__ == '__main__':
    main()
