"""Internal arithmetic/contract review of supplied text, not external truth.

No acquisitions, model execution, fits, forecast grading or registry mutations.
"""
import csv
import hashlib
import io
import json
import platform
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP, getcontext
from pathlib import Path

getcontext().prec = 40
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    path = HERE / name
    if path.exists():
        raise ValueError('Frozen review exists; preserve it and append a version')
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def rows(text, header):
    data = text.split(header, 1)[1].split('\n\n', 1)[0]
    return list(csv.DictReader(io.StringIO(header + data)))


def main():
    reference = HERE / 'SUPPLIED_APPENDIX_A3_A4_REFERENCE.txt'
    text = reference.read_text()
    attempts = rows(text, 'Rank,Defense,Games,Pass attempts faced,Attempts per game\n')
    completions = rows(text, 'Rank,Defense,Completions allowed,Completions per game,Completion percent\n')
    if len(attempts) != 32 or len(completions) != 32:
        raise ValueError('Supplied row count')
    a = {r['Defense']: r for r in attempts}
    c = {r['Defense']: r for r in completions}
    if len(a) != 32 or set(a) != set(c):
        raise ValueError('Supplied identity mismatch')
    checks, mismatches = [], []

    def compare(kind, team, expected, supplied):
        ok = expected == supplied
        checks.append(dict(kind=kind, team=team, expected=str(expected), supplied=str(supplied), match=ok))
        if not ok:
            mismatches.append(checks[-1])

    for group, field in ((attempts, 'Pass attempts faced'), (completions, 'Completions allowed')):
        frequencies = Counter(int(r[field]) for r in group)
        values = [int(r[field]) for r in group]
        for row in group:
            value = int(row[field])
            rank = 1 + sum(other > value for other in values)
            expected = ('T' if frequencies[value] > 1 else '') + str(rank)
            compare(field + '_competition_rank', row['Defense'], expected, row['Rank'])
    for team, ar in a.items():
        cr = c[team]
        games = Decimal(ar['Games'])
        at, co = Decimal(ar['Pass attempts faced']), Decimal(cr['Completions allowed'])
        compare('attempts_per_game', team, (at/games).quantize(Decimal('.01'), rounding=ROUND_HALF_UP), Decimal(ar['Attempts per game']))
        compare('completions_per_game', team, (co/games).quantize(Decimal('.01'), rounding=ROUND_HALF_UP), Decimal(cr['Completions per game']))
        compare('completion_percent', team, (100*co/at).quantize(Decimal('.1'), rounding=ROUND_HALF_UP), Decimal(cr['Completion percent'].removesuffix('%')))
        compare('completions_do_not_exceed_attempts', team, True, co <= at)
    totals = dict(attempts=sum(int(r['Pass attempts faced']) for r in attempts),
        completions=sum(int(r['Completions allowed']) for r in completions),
        team_games=sum(int(r['Games']) for r in attempts))
    weighted = Decimal(100) * totals['completions'] / totals['attempts']
    rounded_team_average = sum(Decimal(r['Completion percent'].removesuffix('%')) for r in completions) / 32
    save('INTERNAL_ARITHMETIC_REVIEW_V1.json', dict(
        id='B-SUPPLIED-DEFENSIVE-PASSING-ARITHMETIC-v1', reviewed_UTC=datetime.now(timezone.utc).isoformat(),
        supplied_reference=dict(path=reference.name, bytes=reference.stat().st_size, sha256=digest(reference),
            serialization='Exact extracted A3/A4 supplied headings/notes and numeric rows; UTF-8/LF. Not workbook bytes or a full assignment identity claim.'),
        environment=dict(python=platform.python_version(), arithmetic='Decimal precision40, ROUND_HALF_UP at2dp per-game and1dp percent'),
        workbook_access='NOT_OBTAINED', external_source_verification=False,
        supplied_teams=32, checks=len(checks), mismatches=mismatches,
        internal_verdict='PASS' if not mismatches else 'DISCREPANCIES_RETAINED',
        detail=checks, supplied_totals=totals,
        supplied_weighted_completion_percent=str(weighted),
        mean_of_supplied_rounded_team_percentages=str(rounded_team_average),
        weighted_vs_unweighted_note='Different quantities. Totals-derived weighting is internally available here; neither is an externally authenticated league fact.',
        half_tie_examples=[dict(team='Lions', metric='attempts_per_game', exact='313/8=39.125', supplied='39.13'),
            dict(team='Jaguars', metric='attempts_per_game', exact='261/8=32.625', supplied='32.63'),
            dict(team='Saints', metric='completions_per_game', exact='171/8=21.375', supplied='21.38')],
        definition_limits=['A3 sack exclusion/non-QB inclusion are supplied claims, not source-verified.',
            'A4 games are joined from A3 by supplied defense name; common provider/cutoff is unverified.',
            'A4 completion denominator is supplied A3 total attempts; unknown-stat completeness cannot be inferred.',
            'Passing totals are not dropback totals, completion rates are not catchability or pressure.',
            'No target counts, RB/TE/alignment labels or rights can be recovered from this arithmetic.'],
        new_fits=0, new_forecasts=0, new_grades=0, new_NFL_observations=0, new_tested_weeks=0))
    print(json.dumps(dict(checks=len(checks), mismatches=len(mismatches), supplied_totals=totals,
        weighted_completion_percent=str(weighted))))


if __name__ == '__main__':
    main()
