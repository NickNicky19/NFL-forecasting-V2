#!/usr/bin/env python3
"""Versioned metadata correction; reads retained week evidence, never scores.

The presentation's short D1/D2/C02 names are not their qualified full IDs.
Unknown selector aliases remain unresolved rather than falsely untested.
"""
import copy
import gzip
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / 'reports/post-wave-5w-v1/B_CATEGORY_PRODUCT_QUALIFICATION_SUMMARY.json'
OUT = ROOT / 'reports/execution-closure-02/B/B_CATEGORY_PRODUCT_QUALIFICATION_CORRECTION_V2.json'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    old = json.loads(OLD.read_bytes())
    qpath = ROOT / old['source']['path']
    assert sha(qpath) == old['source']['sha256']
    rows = json.loads(gzip.decompress(qpath.read_bytes()))
    result = copy.deepcopy(old)
    changes = []
    for c in result['categories']:
        for w in c['native_leaders']:
            short = w['procedure_id']
            if short.startswith('v2-qualified-position-defense-information-wave-v1:') or short == 'v2-c02-explicit-lag-block-removal-leaf-cdf-v1':
                full = short + ':common-feature-memory'
            else:
                full = short
            matches = [r for r in rows if r['category'] == c['category'] and r['procedure_id'] == full
                       and r['product_id'] == w['product'] and r['history'] == w['history']]
            qualified = [r for r in matches if set(range(1, 8)).issubset(r.get('per_season', {}).get('2026', {}).get('weeks', []))]
            w['presentation_procedure_alias'] = short
            w['procedure_id'] = full
            w['matching_retained_contract_views'] = len(matches)
            w['current_seven_week_contract_views'] = len(qualified)
            w['witnesses'] = [dict(qualification_id=r['qualification_id'],
                product_id=r['product_id'], population=r['population'], position=r['position'],
                fallback_view=r['fallback_view'], selection_rule=r['selection_rule'],
                horizon=r['horizon'], weeks=r['per_season']['2026']['weeks'],
                source_artifacts=r['source_artifacts'], source_vintage=r['source_vintage']) for r in qualified]
            w['zero_match_meaning'] = ('UNRESOLVED_PRESENTATION_ALIAS_NOT_PROOF_OF_MISSING_TESTS' if not matches else None)
            if full != short:
                changes.append(dict(category=c['category'], old_alias=short, exact_procedure_id=full,
                                    old_seven_week_views=0, corrected_seven_week_views=len(qualified)))
    result.update(schema='B-category-product-qualification-summary-v2',
        created_at_utc=datetime.now(timezone.utc).isoformat(),
        correction_disposition='VERIFIED_REPORT_METADATA_IDENTITY_DEFECT;NO_FORECAST_OR_SCORE_CHANGE',
        supersedes=dict(path=str(OLD.relative_to(ROOT)), sha256=sha(OLD), old_bytes_preserved=True),
        changes=changes, new_fits=0, new_scores=0, new_NFL_observations=0,
        default_for_B_native_duration_presentation=True,
        canonical_shared_qualification_owner='C;this is a B contribution only',
        actual_line_qualification='Unchanged separate policy/horizon evidence; no numerical or shorter-panel borrowing',
        current_query_and_Top_Picks_admission='NOT_ESTABLISHED_BY_THIS_METADATA_CORRECTION')
    with OUT.open('x') as f:
        f.write(json.dumps(result, indent=2, sort_keys=True)+'\n')
    print(json.dumps(dict(path=str(OUT.relative_to(ROOT)), sha256=sha(OUT), corrected_aliases=len(changes))))


if __name__ == '__main__':
    main()
