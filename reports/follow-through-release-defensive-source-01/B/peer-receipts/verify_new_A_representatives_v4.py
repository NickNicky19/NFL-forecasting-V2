"""Independent arithmetic of selected public A aggregates, no grader reuse."""
import concurrent.futures
import csv
import hashlib
import io
import json
import urllib.request
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

REF = '3a3d48791d5c7e6cf789af480bfb99c062005a97'
BASE = 'reports/abc-championship/category-decision-release-01/'
URL = 'https://raw.githubusercontent.com/NickNicky19/NFL-forecasting/' + REF + '/'
OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]


def get(path, binding=None):
    body = urllib.request.urlopen(URL + path, timeout=30).read()
    record = dict(ref=REF, path=path, bytes=len(body), sha256=hashlib.sha256(body).hexdigest())
    if binding:
        assert record['bytes'] == binding['bytes']
        assert record['sha256'] == binding['sha256']
    return body, record


def csv_rows(path, binding):
    body, record = get(path, binding)
    rows = list(csv.DictReader(io.StringIO(body.decode())))
    assert len(rows) == binding['rows']
    return rows, record


def math_check(row, upper):
    prefixes = ('OVER', 'UNDER', 'COMBINED') if upper else ('over', 'under', 'combined')
    checks = 0
    for prefix in prefixes:
        raw_w, raw_l, raw_n = [row[prefix + '_' + k] for k in ('wins', 'losses', 'decided')]
        n = int(raw_n)
        rate = row[prefix + '_rate']
        if n == 0 and raw_w == raw_l == rate == '':
            checks += 1  # Explicit absent-period nulls, not manufactured observed zeros.
            continue
        w, l = int(raw_w), int(raw_l)
        assert w + l == n
        if n:
            assert abs(Decimal(rate) - Decimal(w) / Decimal(n)) <= Decimal('1e-12')
        else:
            assert rate == ''
        checks += 2
    for field in ('wins', 'losses', 'decided'):
        values = [row[prefix + '_' + field] for prefix in prefixes]
        if values == ['', '', '']:
            assert int(row[prefixes[2] + '_decided']) == 0
        else:
            terms = []
            for prefix, value in zip(prefixes, values):
                if value == '':
                    assert int(row[prefix + '_decided']) == 0
                    terms.append(0)  # Empty-sum identity; does not rewrite a source null.
                else:
                    terms.append(int(value))
            assert terms[0] + terms[1] == terms[2]
        checks += 1
    return checks


def empty_sum_term(row, prefix, field):
    value = row[prefix + "_" + field]
    if value == "":
        assert field in ("wins", "losses") and int(row[prefix + "_decided"]) == 0
        return 0  # Empty selected-side contribution to an identity, raw null retained.
    return int(value)


def main():
    if (OUT / 'A_REPRESENTATIVE_CALCULATION_RECEIPT_V1.json').exists():
        raise ValueError('Frozen receipt exists')
    sources, checks = [], 0
    manifest_body, record = get(BASE + 'B_ATT_ALIAS_PUBLIC_MANIFEST_V2.json')
    sources.append(record)
    manifest = json.loads(manifest_body)
    att_rows, pairs = [], []
    for binding in manifest['files']:
        if binding['path'].endswith('.csv'):
            rows, record = csv_rows(binding['path'], binding)
            sources.append(record)
            (pairs if 'PAIRS' in binding['path'] else att_rows).extend(rows)
    assert len(att_rows) == 324 and len(pairs) == 50
    for row in att_rows:
        checks += math_check(row, True)
    full = [r for r in att_rows if r['view'] == 'FULL_A_BOARD_ALIAS_QUALIFIED87'
            and r['source_panel'] == 'ALL' and r['week_view'] == 'ALL']
    candidate = next(r for r in full if r['candidate_id'] == 'B-player-context-matchup-01-v1:COMMON_EXPOSURE::lower_median')
    a = next(r for r in full if r['candidate_id'] == 'A::COUNT_A_MEAN::mean_objective_point')
    over = next(r for r in full if 'ALWAYS_OVER' in r['candidate_id'])
    assert [int(r['COMBINED_wins']) for r in (candidate, a, over)] == [44, 43, 46]
    assert all(int(r['COMBINED_decided']) == 87 for r in (candidate, a, over))
    weekly_att = [r for r in att_rows if r['view'] == candidate['view'] and r['source_panel'] == 'ALL'
                  and r['candidate_id'] == candidate['candidate_id'] and r['week_view'] in ('1', '2', '3', '4', '5')]
    assert len(weekly_att) == 5
    for prefix in ('OVER', 'UNDER', 'COMBINED'):
        for field in ('wins', 'losses', 'decided', 'selected'):
            assert sum(empty_sum_term(r, prefix, field) for r in weekly_att) == int(candidate[prefix + '_' + field])
            checks += 1
    chosen_pair = []
    for p in pairs:
        assert int(p['left_wins']) - int(p['right_wins']) == int(p['win_change'])
        assert abs(int(p['win_change'])) <= int(p['side_disagreements']) <= int(p['common_decided'])
        checks += 2
        if candidate['candidate_id'] in (p['left'], p['right']) and p['view'] == candidate['view']:
            chosen_pair.append(p)

    point_body, record = get(BASE + 'point-pairs-public-v1/MANIFEST_V1.json')
    sources.append(record)
    point_manifest = json.loads(point_body)
    td_rows = []
    checked_parts = 0
    # The declared public order starts passing yards then passing TDs. Stop
    # once all fixed week views for the one target product have been obtained.
    for binding in point_manifest['files']:
        if not binding['path'].startswith('OWN_RECORDS_'):
            continue
        rows, record = csv_rows(BASE + 'point-pairs-public-v1/' + binding['path'], binding)
        sources.append(record)
        checked_parts += 1
        for row in rows:
            if row['category'] == 'pass_td' and row['candidate_id'].endswith('::COUNT_A_MEAN::mean_objective_point') and row['view'] == 'FULL_ELIGIBLE_ANNUAL_BOARD':
                td_rows.append(row)
                checks += math_check(row, False)
        if {r['week_view'] for r in td_rows} >= {'ALL', '1', '2', '3', '4', '5', '6', '7', '8'}:
            break
        if checked_parts >= 12:
            raise ValueError('Bounded representative part search exhausted')
    td = next(r for r in td_rows if r['week_view'] == 'ALL')
    assert int(td['combined_wins']) == 49 and int(td['combined_decided']) == 86
    assert (int(td['over_wins']), int(td['under_wins'])) == (25, 24)
    weekly_td = [r for r in td_rows if r['week_view'] in ('1', '2', '3', '4', '5')]
    assert len(weekly_td) == 5
    for prefix in ('over', 'under', 'combined'):
        for field in ('wins', 'losses', 'decided', 'selected'):
            assert sum(empty_sum_term(r, prefix, field) for r in weekly_td) == int(td[prefix + '_' + field])
            checks += 1
    assert all(int(r['eligible']) == 0 for r in td_rows if r['week_view'] in ('6', '7', '8'))

    reused_body, record = get(BASE + 'REUSED_CROSS_SESSION_COMPARISONS_V2.json')
    sources.append(record)
    reused = json.loads(reused_body)['reception_existing_non_timing']['annual_records']
    selected = [r for r in reused if r['candidate_id'] in (
        'A::LEAF_CDF::mean', 'C::PLAYER-CONTEXT-MATCHUP-01::v1.1::P1::mean')]
    assert len(selected) == 2
    prior_path = ROOT / 'reports/category-decision-release-01/B/A-join-review/ACKNOWLEDGED_EXACT_JOIN_RECORDS_V1.json'
    prior_bytes = prior_path.read_bytes()
    prior = json.loads(prior_bytes)['annual_records']
    for row in selected:
        p = next(r for r in prior if r['candidate_id'] == row['candidate_id'] and r['combined_decided'] == 412)
        for side in ('OVER', 'UNDER', 'COMBINED'):
            for field in ('wins', 'losses', 'decided'):
                assert row[side][field] == p[side.lower() + '_' + field]
                checks += 1
            assert row[side]['wins'] + row[side]['losses'] == row[side]['decided']
            checks += 1
        for field in ('MAE', 'MSE', 'bias'):
            assert abs(Decimal(str(row['numerical'][field])) - Decimal(str(p['numerical'][field]))) <= Decimal('1e-12')
            checks += 1
    assert {r['candidate_id']: r['COMBINED']['wins'] for r in selected} == {
        'A::LEAF_CDF::mean': 238, 'C::PLAYER-CONTEXT-MATCHUP-01::v1.1::P1::mean': 239}
    report = dict(id='B-A-NEW-PUBLIC-REPRESENTATIVE-CALCULATIONS-v1',
        completed_UTC=datetime.now(timezone.utc).isoformat(), state='PASS_IN_PUBLIC_AGGREGATE_SCOPE',
        sources=sources, source_bytes=sum(r['bytes'] for r in sources),
        independent_integer_Decimal_checks=checks, ATT_public_summary_rows=len(att_rows), ATT_public_pair_rows=len(pairs),
        ATT_full87=dict(B_lower_median=candidate, A_corrected_mean=a, Always_Over=over,
                        B_weekly=weekly_att, B_named_pairs=chosen_pair),
        CountA_TD=dict(own=td, weekly=weekly_td, declared_empty_weeks=[6, 7, 8], public_parts_checked=checked_parts),
        reception=dict(records=selected, earlier_verified_B_receipt=str(prior_path.relative_to(ROOT)),
            earlier_verified_B_receipt_sha256=hashlib.sha256(prior_bytes).hexdigest(),
            reuse='New A reused records match previously independently checked exact A/d7 public rows for all18 side counts and numerical MAE/MSE/bias; no duplicate private join or complete scorer replay'),
        limits=['Aggregate arithmetic and exact source byte/hash checks only; not private row/quote/model-fit parity.',
                'No bootstrap replication; supplied dependence-aware intervals remain owner-reported.',
                'New A79 point/ATT package is published, but no exact C intake observed in inspected current pointers.',
                'Six alias memberships restore coverage, not new NFL games or demonstrated learned-model gain.',
                'The native A88/B112 completion W5 intersection remains unresolved and is a different task.'],
        new_fits=0, new_inference=0, new_grades=0, new_test_games_or_weeks=0)
    (OUT / 'A_REPRESENTATIVE_CALCULATION_RECEIPT_V1.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(state=report['state'], checks=checks, ATT_rows=len(att_rows), pairs=len(pairs),
        TD_parts=checked_parts, reception='239vs238/412 previous exact receipt reused', source_bytes=report['source_bytes'])))


if __name__ == '__main__':
    main()
