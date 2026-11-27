"""Read immutable public peer aggregates and emit hashes/scoped observations.

No score function, fit, private record, model restoration, production write or
provider acquisition. Full source bodies stay in memory and are not republished.
"""
import concurrent.futures
import hashlib
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

C_REF = '2e604d8801d74788a61b3fa9e5206e7c4a452e81'
A_REF = '3a3d48791d5c7e6cf789af480bfb99c062005a97'
JOBS = [
    ('C_pointer', 'NFL-forecasting-NGS-C', C_REF, 'reports/abc-championship/CURRENT_PROTOCOL.json'),
    ('C_export', 'NFL-forecasting-NGS-C', C_REF, 'reports/abc-championship/EXPORT_INDEX.json'),
    ('C_decisions', 'NFL-forecasting-NGS-C', C_REF, 'reports/category-decision-release-01/CATEGORY_PRODUCT_DECISIONS.json'),
    ('C_admission', 'NFL-forecasting-NGS-C', C_REF, 'reports/category-decision-release-01/intake/ADMISSION.json'),
    ('C_operational', 'NFL-forecasting-NGS-C', C_REF, 'reports/category-decision-release-01/operational-intake/ADMISSION.json'),
    ('C_report', 'NFL-forecasting-NGS-C', C_REF, 'reports/category-decision-release-01/README.md'),
    ('C_current', 'NFL-forecasting-NGS-C', C_REF, 'reports/category-decision-release-01/CURRENT_QUERY_HANDOFF.json'),
    ('C_stages', 'NFL-forecasting-NGS-C', C_REF, 'reports/category-decision-release-01/RELEASE_AND_CAPTURE_STAGES.json'),
    ('A_export', 'NFL-forecasting', A_REF, 'reports/abc-championship/EXPORT_INDEX.json'),
    ('A_report', 'NFL-forecasting', A_REF, 'reports/abc-championship/category-decision-release-01/EXECUTED_CATEGORY_DECISIONS_V1.md'),
    ('A_contribution', 'NFL-forecasting', A_REF, 'reports/abc-championship/category-decision-release-01/A_CATEGORY_PRODUCT_CONTRIBUTION_V1.json'),
    ('A_queue', 'NFL-forecasting', A_REF, 'reports/abc-championship/category-decision-release-01/A_FINITE_REMAINING_QUEUE_V1.json'),
    ('A_stages', 'NFL-forecasting', A_REF, 'reports/abc-championship/category-decision-release-01/RELEASE_AND_CAPTURE_STAGES_V1.json'),
    ('A_book_policy', 'NFL-forecasting', A_REF, 'reports/abc-championship/category-decision-release-01/A_ANNUAL_BOOK_POLICY_METADATA_V1.json'),
    ('A_ATT_manifest', 'NFL-forecasting', A_REF, 'reports/abc-championship/category-decision-release-01/B_ATT_ALIAS_PUBLIC_MANIFEST_V2.json'),
]


def fetch(job):
    key, repo, ref, path = job
    url = 'https://raw.githubusercontent.com/NickNicky19/' + repo + '/' + ref + '/' + path
    with urllib.request.urlopen(url, timeout=30) as response:
        body = response.read(1024 * 1024 + 1)
    if len(body) > 1024 * 1024:
        raise ValueError('Bounded metadata response too large')
    text = body.decode('utf-8')
    data = json.loads(text) if path.endswith('.json') else text
    record = dict(key=key, repository='NickNicky19/' + repo, ref=ref, path=path,
                  bytes=len(body), sha256=hashlib.sha256(body).hexdigest(), url=url,
                  observed_UTC=datetime.now(timezone.utc).isoformat())
    return key, data, record


def main():
    out = Path(__file__).resolve().parent
    if (out / 'IMMUTABLE_PEER_BINDINGS_V1.json').exists():
        raise ValueError('Frozen receipt exists; append a version if justified')
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(fetch, JOBS))
    data = {key: body for key, body, _ in rows}
    records = {key: record for key, _, record in rows}
    for field, key in [('category_product_decisions', 'C_decisions'), ('intake', 'C_admission'),
                       ('operational_intake', 'C_operational'), ('current_handoff', 'C_current'),
                       ('operational_stages', 'C_stages'), ('report', 'C_report')]:
        wanted = data['C_pointer']['category_decision_release_01'][field]
        assert wanted['path'] == records[key]['path']
        assert wanted['SHA256'] == records[key]['sha256']
    cats = data['C_decisions']['categories']
    if isinstance(cats, dict):
        cats = list(cats.values())
    assert len(cats) == 12
    compact = []
    for row in cats:
        compact.append({key: row[key] for key in (
            'category', 'origin', 'exact_procedure', 'decision_policy', 'output', 'role_scope',
            'decision', 'preferred_eligible_candidate', 'actual_weeks_by_season', 'OVER', 'UNDER',
            'COMBINED', 'coverage', 'controls', 'uncertainty', 'evidence_tier', 'five_week_status',
            'current_query', 'actual_live_method', 'remaining_owner_action', 'other_products')})
    needles = ['14a47eec', '3a3d4879', '48c615bc', '520dd17a', 'B_ATT_ALIAS_RESULTS_V2',
               'A_POINT_PAIR_RESULTS_V1', '96136a8e', '3e7c174e', '40364b7c']
    intake_search = {}
    for key in ('C_pointer', 'C_export', 'C_decisions', 'C_admission', 'C_report'):
        text = data[key] if isinstance(data[key], str) else json.dumps(data[key])
        intake_search[key] = [needle for needle in needles if needle in text]
    result = dict(id='B-FOLLOWTHROUGH-IMMUTABLE-PEER-BINDINGS-v1',
        completed_UTC=datetime.now(timezone.utc).isoformat(), sources=list(records.values()),
        total_bytes=sum(r['bytes'] for r in records.values()),
        C_pointer_declared_hashes_checked=6, C_scope='One existing C canonical table, not a B master ranking',
        C_latest_exact_identifier_search=intake_search,
        source_bodies='Read transiently in memory; not copied into B archive',
        score_or_fit_calls=0, new_NFL_games_or_weeks=0, peer_writes=0, dispatches=0)
    (out / 'IMMUTABLE_PEER_BINDINGS_V1.json').write_text(json.dumps(result, indent=2) + '\n')
    (out / 'C_DECISION_RECEIPT_EXTRACT_V1.json').write_text(json.dumps(dict(
        id='B-READONLY-C-DECISION-EXTRACT-v1', source=records['C_decisions'],
        role='Quoted existing C decisions and scope; no B recommendation substitution',
        categories=compact, new_common_table=False), indent=2) + '\n')
    (out / 'A_NEW_PACKAGE_AND_SOURCE_SCOPE_V1.json').write_text(json.dumps(dict(
        id='B-RECEIVED-A-POINT-ATT-SOURCE-SCOPE-v1', sources=[records[k] for k in
            ('A_export', 'A_report', 'A_contribution', 'A_queue', 'A_stages', 'A_book_policy', 'A_ATT_manifest')],
        current_execution=data['A_export']['current_execution'],
        book_policy=data['A_book_policy'], ATT_public_manifest=data['A_ATT_manifest'],
        completed_not_requeued=data['A_queue']['completed_not_requeued'],
        finite_owner_tasks=data['A_queue']['queue'],
        actual_stages=data['A_stages'],
        scope='Source metadata/public aggregate receipt only; private row membership/model/source-clock parity not established',
        new_fits=0, new_inference=0, new_grades=0), indent=2) + '\n')
    print(json.dumps(dict(state='PASS', sources=len(rows), bytes=result['total_bytes'],
        C_hashes=6, C_categories=len(compact), new_fit_or_score_calls=0)))


if __name__ == '__main__':
    main()
