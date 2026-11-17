"""Separate Decimal arithmetic over public aggregates; not an NFL grader."""
import argparse
import collections
import csv
import hashlib
import json
from decimal import Decimal
from pathlib import Path

STEM = 'reports/abc-championship/profile-timing-closure-and-confirm-01'
REF = 'd7c8bc619eb7aed93df8259822eb08488d837005'
CHECKS = 0
MAX_DIFFERENCE = Decimal(0)


def number(x):
    return None if x in (None, '') else Decimal(str(x))


def equal(a, b, tolerance='1e-10'):
    global CHECKS, MAX_DIFFERENCE
    CHECKS += 1
    a, b = number(a), number(b)
    if a is None or b is None:
        assert a is b, (a, b)
        return
    delta = abs(a-b)
    MAX_DIFFERENCE = max(MAX_DIFFERENCE, delta)
    assert delta <= Decimal(tolerance), (a, b, delta)


def count(row, name):
    value = row.get(name)
    if value in ('', None) and name.endswith(('_wins', '_losses')):
        assert row[name.rsplit('_', 1)[0]+'_decided'] == '0'
        return 0
    return int(value)


def obj(row, name):
    value = row.get(name)
    return json.loads(value) if value and value.startswith(('{', '[')) else None


def rate(wins, decided, value):
    equal(Decimal(wins)/Decimal(decided) if decided else None, value)


def csv_rows(folder, prefix):
    result = []
    for path in sorted(folder.glob(prefix+'*.csv')):
        result.extend(csv.DictReader(path.open(newline='')))
    return result


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def summary_checks(rows, category):
    for row in rows:
        for side in ('over', 'under', 'combined'):
            equal(count(row, side+'_wins')+count(row, side+'_losses'), count(row, side+'_decided'))
            rate(count(row, side+'_wins'), count(row, side+'_decided'), row[side+'_rate'])
        for field in ('selected', 'wins', 'losses', 'decided'):
            equal(count(row, 'over_'+field)+count(row, 'under_'+field), count(row, 'combined_'+field))
        equal(count(row, 'combined_selected')+count(row, 'unavailable')+count(row, 'abstentions'), count(row, 'eligible'))
        equal(Decimal(count(row, 'combined_selected'))/Decimal(count(row, 'eligible')) if count(row, 'eligible') else None,
              row['coverage'])
        states = obj(row, 'states')
        equal(sum(states.values()), count(row, 'eligible'))
        equal(states.get('WIN', 0), count(row, 'combined_wins'))
        equal(states.get('LOSS', 0), count(row, 'combined_losses'))
        if 'UNAVAILABLE_FORECAST' in states:
            equal(states['UNAVAILABLE_FORECAST'], count(row, 'unavailable'))
        numerical = obj(row, 'numerical')
        if numerical['scored']:
            assert number(numerical['MAE']) >= 0
            assert number(numerical['MSE']) + Decimal('1e-9') >= number(numerical['MAE'])**2
            assert abs(number(numerical['bias'])) <= number(numerical['MAE']) + Decimal('1e-9')
            if numerical.get('RMSE') is not None:
                equal(number(numerical['MSE']).sqrt(), numerical['RMSE'])
        else:
            assert all(numerical.get(k) is None for k in ('MAE', 'MSE', 'bias'))
        if row['candidate_id'].endswith('::P2') and category == 'pass_cmp':
            equal(numerical['scored'], 0)
        probability = obj(row, 'probability')
        if probability and probability.get('events'):
            equal(probability['events'], count(row, 'combined_decided'))
            assert 0 <= number(probability['Brier']) <= 1
            equal(probability['neutral_binary_half_Brier'], '.25')
            bins = probability['reliability_fixed_bins']
            equal(sum(x['count'] for x in bins), probability['events'])
            for item in bins:
                n = number(item['count'])*number(item['observed_Over'])
                equal(n, round(n))
        if category == 'rec':
            assert row['probability'] == 'N/A_TYPED_POINTS_ONLY;NO_PROBABILITY_LAW_OR_CONFIDENCE_INFERRED'
            if '::F2::' in row['candidate_id'] or '::F3::' in row['candidate_id']:
                equal(row['unknown_fallback_flags'], count(row, 'combined_selected'))
                assert all(row[k] == '' for k in ('fallback_outputs', 'profile_covered_outputs', 'any_imputed_outputs'))


def combine(total, parts):
    for field in ('eligible', 'unavailable', 'abstentions'):
        equal(sum(count(x, field) for x in parts), count(total, field))
    for side in ('over', 'under', 'combined'):
        for field in ('selected', 'wins', 'losses', 'decided'):
            equal(sum(count(x, side+'_'+field) for x in parts), count(total, side+'_'+field))
    tn = obj(total, 'numerical')
    pn = [obj(x, 'numerical') for x in parts]
    equal(sum(x['scored'] for x in pn), tn['scored'])
    if tn['scored']:
        for metric in ('MAE', 'MSE', 'bias'):
            equal(sum(Decimal(x['scored'])*number(x[metric]) for x in pn if x['scored'])/Decimal(tn['scored']), tn[metric])
    tp = obj(total, 'probability')
    pp = [obj(x, 'probability') for x in parts]
    if tp and tp.get('events'):
        equal(sum((x or {}).get('events', 0) for x in pp), tp['events'])
        for metric in ('Brier', 'three_state_log_loss'):
            equal(sum(Decimal(x['events'])*number(x[metric]) for x in pp if x and x.get('events'))/Decimal(tp['events']), tp[metric])


def reconcile(rows, category):
    lookup = {(r['view'], r['source_panel'], r['candidate_id'], r['week_view']): r for r in rows}
    assert len(lookup) == len(rows)
    new_prefix = 'B-QB-ALIGNED-FRESHNESS-v1:' if category == 'pass_cmp' else 'C-RECEIVING-ALIGNED-TIMING-v1::'
    for key, total in lookup.items():
        view, panel, candidate, week = key
        if week != 'ALL' or not candidate.startswith(new_prefix):
            continue
        weekly = [r for (v,p,c,w),r in lookup.items() if (v,p,c)==(view,panel,candidate) and w!='ALL']
        assert len(weekly) == (8 if category == 'pass_cmp' else 7)
        combine(total, weekly)
        if panel == 'ALL':
            combine(total, [lookup[view,p,candidate,'ALL'] for p in ('ANNUAL_NAMED_NJ','SITE_RECORDED_DK_JURISDICTION_UNKNOWN')])
    for (view,panel,candidate,week), row in lookup.items():
        if week != 'ALL':
            continue
        if category == 'pass_cmp' and candidate.startswith(new_prefix):
            arm, product = candidate[len(new_prefix):].split('::')
            if product == 'P2':
                other = lookup[view,panel,new_prefix+arm+'::lower_median','ALL']
                for side in ('over','under','combined'):
                    for field in ('selected','wins','losses','decided'):
                        equal(row[side+'_'+field],other[side+'_'+field])
            alias = {'F0':'R0','F1':'R2'}.get(arm)
            alias_id = 'B-QB-OPPORTUNITY-PROFILE-INCREMENT-v1:'+alias+'::'+product if alias else None
        elif category == 'rec' and candidate.startswith(new_prefix):
            arm,product = candidate[len(new_prefix):].split('::')
            alias = {'F0':'R1','F1':'R2'}.get(arm)
            alias_id = 'C-RECEIVING-PROFILE-INCREMENT-v2::'+alias+'::'+product if alias else None
        else:
            continue
        if alias_id:
            other = lookup[view,panel,alias_id,'ALL']
            for field in ('eligible','unavailable','abstentions'):
                equal(row[field],other[field])
            for side in ('over','under','combined'):
                for field in ('selected','wins','losses','decided'):
                    equal(row[side+'_'+field],other[side+'_'+field])
            for metric in ('MAE','MSE','bias','scored'):
                equal(obj(row,'numerical').get(metric),obj(other,'numerical').get(metric))
    return lookup


def pair_checks(rows, lookup, category):
    for row in rows:
        a = lookup[row['view'],row['source_panel'],row['left'],'ALL']
        b = lookup[row['view'],row['source_panel'],row['right'],'ALL']
        den = count(row,'common_decided')
        equal(row['left_wins'],a['combined_wins'])
        equal(row['right_wins'],b['combined_wins'])
        delta = count(row,'left_wins')-count(row,'right_wins')
        if category == 'pass_cmp':
            equal(Decimal(delta)/Decimal(den) if den else None,row['accuracy_change'])
        else:
            equal(delta,row['win_change'])
        disagreements = count(row,'side_disagreements')
        assert abs(delta)<=disagreements<=den and (disagreements-delta)%2==0
        if category == 'pass_cmp':
            if count(row,'common_numerical'):
                equal(number(obj(a,'numerical')['MAE'])-number(obj(b,'numerical')['MAE']),row['MAE_change'])
            if count(row,'common_law_events'):
                equal(number(obj(a,'probability')['Brier'])-number(obj(b,'probability')['Brier']),row['Brier_change'])
        else:
            numerical = obj(row,'numerical_paired')
            if numerical['common_cases']:
                equal(number(obj(a,'numerical')['MAE'])-number(obj(b,'numerical')['MAE']),numerical['MAE_change'])


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--cache',type=Path,required=True);args=ap.parse_args()
    dest=Path(__file__).resolve().parent;source=args.cache/STEM
    downloads=json.loads((args.cache/'DOWNLOAD_MANIFEST.json').read_text())
    for r in downloads:
        path=args.cache/r['path'];assert path.stat().st_size==r['bytes'] and sha(path)==r['sha256']
    result={};all_files=[]
    for category,folder in [('pass_cmp','b-timing-public-v1'),('rec','c04-public-v1')]:
        directory=source/folder;manifest=json.loads((directory/'MANIFEST_V1.json').read_text())
        for r in manifest['files']:
            path=directory/r['path'];assert sha(path)==r['sha256'] and path.stat().st_size==r['bytes']
            equal(len(list(csv.DictReader(path.open(newline='')))),r['rows']);all_files.append(dict(path=STEM+'/'+folder+'/'+r['path'],sha256=r['sha256'],bytes=r['bytes'],rows=r['rows']))
        summaries=csv_rows(directory,'ALL_NEW_TIMING_WEEKLY')+csv_rows(directory,'RETAINED_CONTROLS')
        pairs=csv_rows(directory,'ALL_NEW_TIMING_MATCHED')
        summary_checks(summaries,category);lookup=reconcile(summaries,category);pair_checks(pairs,lookup,category)
        result[category]=dict(summary_rows=len(summaries),paired_rows=len(pairs),candidate_products=len({r['candidate_id']for r in summaries}),data_files=manifest['data_files'],state='PASS_PUBLIC_AGGREGATE_ARITHMETIC')
    receipt=dict(id='B-INDEPENDENT-A-EXACT-TIMING-JOINS-v1',status='PASS_PUBLIC_AGGREGATE_SCOPE',A_ref=REF,A_research_branch='research/accuracy-wave-20261026',downloaded_files=len(downloads),downloaded_bytes=sum(r['bytes']for r in downloads),manifest_data_files=len(all_files),decimal_checks=CHECKS,largest_decimal_difference=str(MAX_DIFFERENCE),panels=result,source_bindings=downloads,manifest_data_bindings=all_files,new_fits=0,new_inference=0,new_owner_local_joins=0,new_NFL_observations=0,limits=['No restricted player/offer rows, source clocks, private masks, full native score restoration or fitted models inspected.','No bootstrap replication: intervals are owner-reported and only their score changes/counts checked.','Aggregate pairwise masks are opaque hashes; private identity/membership/duplicate/threshold grading remains UNKNOWN.','W1-5 annual real-line timing-unverified diagnostics; W6-7 internal/unqualified source diagnostics, no A W8 rows.','Exact law/P2 and mean/median products remain separate; C04 typed points supply no law/confidence/EV.','Five-week duration does not grant superiority or automatic production admission.'])
    (dest/'INDEPENDENT_PUBLIC_ARITHMETIC_V1.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({k:v for k,v in receipt.items()if k not in ('source_bindings','manifest_data_bindings')},indent=2))


if __name__=='__main__':main()
