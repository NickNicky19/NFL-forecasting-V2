"""Project existing Week8 candidate and strong-control rankings; never rescore."""
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'reports/week8-grading-20261102l'
SUMMARY = BASE / 'checkpoint-summary-v1'


def load(path):
    return json.loads(path.read_bytes())


def save(path, value):
    with path.open('x') as handle:
        json.dump(value, handle, indent=2)
        handle.write('\n')


def run():
    candidate_path = BASE / 'comparable-products-v3/SELECTION_SIDE_TABLE.json'
    control_path = SUMMARY / 'CONTROL_SIDE_TABLE.json'
    candidates = load(candidate_path)
    controls = [r for r in load(control_path) if r['strategy'] != 'original']
    metadata = {r['method_key']: r for r in load(BASE / 'comparable-products-v3/SCORES.json')}
    output = []
    for target in ('pass_yd', 'pass_td', 'pass_cmp', 'pass_att', 'pass_int',
                   'rush_yd', 'rush_att', 'rec', 'rec_yd', 'rush_rec_yd'):
        for side in ('over', 'under', 'combined'):
            pool = [r for r in candidates + controls if r['target'] == target and r[side + '_decided']]
            maximum = max(r[side + '_hit_rate'] for r in pool)
            winners = [r for r in pool if abs(r[side + '_hit_rate'] - maximum) < 1e-12]
            for row in winners:
                mid = row['procedure_id'].rsplit(':', 1)[-1]
                meta = metadata.get(mid)
                value = dict(row)
                value.update(selected_side_product=side, tie_count=len(winners),
                    history_regime=meta['history_regime'] if meta else 'FIXED_SAVED_CONTROL_NO_RETRAINING',
                    product_id=meta['product_id'] if meta else row['strategy'],
                    capture_version=meta['capture_version'] if meta else 'WEBSITE_SAVED_PROVIDER_T90_SOURCE',
                    availability_arm=meta['availability_arm'] if meta else None,
                    method_key=mid if meta else None,
                    source_kind='SAVED_CANDIDATE_P1' if meta else 'SAVED_POINT_OR_CONSTANT_DIRECTION_CONTROL')
                output.append(value)
    path = SUMMARY / 'COMMON_P1_WITH_STRONG_CONTROLS_MAXIMA_V2.json'
    save(path, output)
    fields = list(dict.fromkeys(k for row in output for k in row))
    with (SUMMARY / 'COMMON_P1_WITH_STRONG_CONTROLS_MAXIMA_V2.csv').open('x', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in output:
            writer.writerow({k: json.dumps(v, separators=(',', ':')) if isinstance(v, (dict, list)) else v
                             for k, v in row.items()})
    save(SUMMARY / 'COMMON_P1_CONTROL_SCOPE_QUALIFICATION_V2.json', dict(
        state='RANKING_SCOPE_PROJECTION_INCLUDES_STRONG_SAVED_AND_CONSTANT_CONTROLS',
        at_utc=datetime.now(timezone.utc).isoformat(), score_values_changed=False,
        new_NFL_fits=0, new_inference=0, new_forecasts=0, new_score_views=0, rows=len(output),
        inputs=[dict(path=p.relative_to(ROOT).as_posix(), sha256=hashlib.sha256(p.read_bytes()).hexdigest())
                for p in (candidate_path, control_path)],
        code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        qualification='Earlier executive maxima cover captured candidates. This projection includes saved-point and constant controls. Original recorded selections remain TrackA. Different selected-pool coverage and ties remain; no new score or earlier-executable method selector.'))
    note = '''# Common-offer P1 maxima including strong controls

This supplements the candidate-only maxima in the original Week8 executive table. No score, forecast or selected side changes. Actual original leans remain a separate evidence track.

- Completions: saved raw Over4/10(40.00%) exceeds candidate7/18(38.89%); selected Under maximum remains strict baseCDF5/6(83.33%). Combined **alwaysUnder16/24(66.67%)** exceeds best candidate15/24(62.50%).
- Receptions: raw saved-point Under **50/81(61.73%)** exceeds candidate49/80(61.25%); combined raw **83/137(60.58%)** exceeds candidate83/138(60.14%). The same83wins and one equality abstention explain the denominator difference; no pure learner improvement or release switch is established.
- Rushing attempts: alwaysUnder20/37 ties the candidate maximum20/37(54.05%). All15tied views/controls stay visible; these are not15independent learners.
- Other measured maxima retain their values. All ties, exact procedures and each same procedure's own Over/Under/Combined counts are in the [JSON](COMMON_P1_WITH_STRONG_CONTROLS_MAXIMA_V2.json) and [CSV](COMMON_P1_WITH_STRONG_CONTROLS_MAXIMA_V2.csv). Interception1/1maxima remain tiny descriptive cases.

These use existing common rows and fixed rule choices. Native numerical minima, probability scores and price-aware rankings remain separate. No native MAE is invented for a constant direction rule. One exposed week and dependent player/game props do not establish durable champions, profitability or owner admission.
'''
    (SUMMARY / 'COMMON_P1_WITH_CONTROLS_README_V2.md').write_text(note)
    report = BASE / 'FULL_CATEGORY_CHAMPIONSHIP_REPORT.md'
    text = report.read_text()
    anchor = 'This is an additive Week8 checkpoint, not replacement of the fixed2026W1–7 or completed older-season evidence.'
    addition = '\n\n**Read the [matched P1 maxima including strong controls](checkpoint-summary-v1/COMMON_P1_WITH_CONTROLS_README_V2.md) alongside the candidate-only executive maxima:** alwaysUnder wins completions16/24; raw saved-point wins reception hitrate83/137 versus83/138 with different abstention coverage. No scores or predictions changed.'
    assert anchor in text
    report.write_text(text.replace(anchor, anchor + addition, 1))
    print(json.dumps(dict(scope_projection_rows=len(output), new_scores=0)))


if __name__ == '__main__':
    run()
