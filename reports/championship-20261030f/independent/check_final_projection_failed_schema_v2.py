"""Independent public-source QA of champions, annotations, coverage and index."""
import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
from fractions import Fraction
import gzip
import hashlib
import json
import math
from pathlib import Path
import resource
import time


def sha(p):
    h=hashlib.sha256()
    with p.open('rb')as f:
        for part in iter(lambda:f.read(1048576),b''):h.update(part)
    return h.hexdigest()
def read(p):return json.loads(p.read_bytes())
def close(a,b):
    if a is None or b is None:assert a is b
    elif isinstance(a,list):
        assert len(a)==len(b)
        for x,y in zip(a,b):close(x,y)
    else:assert math.isclose(a,b,abs_tol=1e-10,rel_tol=1e-10),(a,b)
def canon(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();start=time.monotonic();root=a.repo_root;base=root/'reports/championship-20261030f'
    nums=read(base/'numerical-v2/CATEGORY_CHAMPIONS_NUMERICAL.json');props=read(base/'offer-expansion/full-pool-v1/SCORES.json');champions=read(base/'CATEGORY_CHAMPIONS.json');assert len(champions)==12
    numeric_ids={(r['category'],r['procedure_id'],r['history_regime'],r['product_id'])for r in nums if r['metric']in('mae','brier')}
    declared=set()
    for c in champions:
        for n in c['numeric_leaders']:
            assert n in nums;declared.add((n['category'],n['procedure_id'],n['history_regime'],n['product_id']))
        assert c['offered_probability_leader']is None and c['price_aware_leader']is None
        assert c['release_state']=='RESEARCH_PACKAGE_NOT_ADMITTED'
        for side,maximum in c['partial_selection_maxima'].items():
            eligible=[r for r in props if r['target']==c['category']and r['cohort_id']=='ALL'and r['K']is None and r['rank_scope']is None and r['side']==side and r['n']]
            best=max((Fraction(r['selection_metrics']['WIN'],r['n'])for r in eligible),default=None)
            chosen=[r for r in eligible if Fraction(r['selection_metrics']['WIN'],r['n'])==best]
            assert {r['strategy']for r in maximum}=={r['strategy']for r in chosen}
            for r in maximum:
                source=next(v for v in chosen if v['strategy']==r['strategy']);m=source['selection_metrics']
                assert(r['selected'],r['wins'],r['losses'],r['decided'])==(source['forecast_rows'],m['WIN'],m['LOSS'],source['n']);close(r['hit_rate'],m['hit_rate']);assert r['game_uncertainty']==m['game_uncertainty']
    assert numeric_ids==declared
    annotations=0;empty=0;reverse=0
    for year in(2026,2025,2024,2023,2022):
        p=base/'numerical-v2'/str(year);scores=read(p/'SCORES.json');pairs={r['comparison_id']:r for r in read(p/'PAIRED_COMPARISONS.json')};ann=read(p/'COMPARISON_ANNOTATIONS.json')
        assert ann['source_score_sha256']==sha(p/'SCORES.json')and ann['paired_source_sha256']==sha(p/'PAIRED_COMPARISONS.json');assert len(ann['rows'])==len(scores)
        by={(r['comparison_id'],r['role']):r for r in scores}
        for i,(r,item)in enumerate(zip(scores,ann['rows'])):
            assert item['source_row_index']==i;c=item['comparison'];pair=pairs[r['comparison_id']];role=r['role'];forward=role=='candidate';other=by[r['comparison_id'],'comparator'if forward else'candidate']
            assert c['comparator_procedure_id']==other['procedure_id']and c['comparator_product_id']==other['product_id']and c['comparator_history_regime']==other['history_regime']
            assert c['paired_n']==pair['n']and c['membership_sha256']==pair['membership_sha256']
            av=pair.get('candidate_error'if forward else'comparator_error');bv=pair.get('comparator_error'if forward else'candidate_error');close(c['candidate_error'],av);close(c['comparator_error'],bv)
            delta=pair['delta'];delta=delta if forward or delta is None else-delta;close(c['absolute_error_change'],delta);close(c['relative_error_change'],delta/bv if delta is not None and bv and bv>0 else None)
            for field in('week_interval','game_normal95_sensitivity'):
                expected=pair[field]
                if not forward and expected is not None:expected=[-expected[1],-expected[0]]
                close(c['uncertainty'][field],expected)
            if not pair['n']:assert c['status']=='UNESTABLISHED'and av is None and bv is None and delta is None;empty+=1
            else:assert c['status']=='PAIRED_RETAINED_ROWS'
            reverse+=not forward;annotations+=1
    p=base/'category-selector-v2';scores=read(p/'SCORES.json');ann=read(p/'COMPARISON_ANNOTATIONS.json');masks=read(p/'EXACT_MASK_ADMISSION.json');baselines={r['target']:r for r in scores if r['procedure_id'].endswith(':FROZEN_2025_BEST')};assert ann['source_score_sha256']==sha(p/'SCORES.json')
    for i,(r,item)in enumerate(zip(scores,ann['rows'])):
        assert item['source_row_index']==i;c=item['comparison'];baseline=baselines[r['target']];metric='brier'if r['target']=='anytime_td'else'mae';av,bv=r[metric],baseline[metric]
        assert c['paired_n']==r['n'];close(c['candidate_error'],av);close(c['comparator_error'],bv);close(c['absolute_error_change'],av-bv)
        cells=sorted({(m['week'],m['support_sha256'],m['label_values_sha256'])for m in masks if m['season']==2026 and m['target']==r['target']})
        assert len(cells)==7 and c['membership_sha256']==hashlib.sha256(json.dumps(cells,separators=(',',':')).encode()).hexdigest();annotations+=1
    coverage=read(base/'coverage/COVERAGE_MANIFEST.json');file=base/'coverage/COVERAGE_GRID.json.gz';columnar=json.loads(gzip.decompress(file.read_bytes()));grid=[dict(zip(columnar['columns'],r))for r in columnar['rows']]
    assert len(grid)==coverage['rows']and len({r['coverage_id']for r in grid})==len(grid)
    observed=Counter((r['unit_kind'],r['status'])for r in grid);assert observed==Counter({(r['unit_kind'],r['status']):r['rows']for r in coverage['unit_status_counts']})
    fits=[r for r in grid if r['unit_kind']=='scientific_evaluation_cell'and r['status']=='FIT_REQUIRED'];assert len(fits)==13395
    assert sum(r['season']==2026 and str(r['procedure_id']).startswith('hgb-direct-history-controls-v1:')for r in fits)==147
    fixed=[r for r in grid if r['unit_kind']=='scientific_evaluation_cell'and r['status']=='NOT_APPLICABLE'];assert len(fixed)==60 and all('server-retained' in str(r['procedure_id'])for r in fixed)
    empirical=[r for r in grid if r['unit_kind']=='scientific_evaluation_cell'and r['procedure_id']=='empirical-player-history-control-v1'];assert empirical and all('PER_ARM' in r['feature_memory_policy']for r in empirical)
    assert len([r for r in grid if r['unit_kind']=='requested_pathway'])==60
    release=read(base/'CATEGORY_RELEASE_MATRIX.json');assert len(release)==12
    assert all(r['admission_ready']is False and r['newly_deployed']is False and r['served_verified']is False and r['point_release_requires_betting_profitability']is False for r in release)
    pointer=read(root/'registries/CURRENT_RESULTS_INDEX.json');manifest=read(root/pointer['manifest']);old=read(root/'reports/prop-grading-20261030e/compact-results-index/INDEX_MANIFEST.json')
    assert manifest['record_count']==159087 and len(manifest['shards'])==101 and len(manifest['csv_parts'])==17
    oldshards={r['path']:r['sha256']for r in old['shards']};oldcsv={r['path']:r['sha256']for r in old['csv_parts']}
    assert all(next(s['sha256']for s in manifest['shards']if s['path']==p)==h for p,h in oldshards.items())
    assert all(next(s['sha256']for s in manifest['csv_parts']if s['path']==p)==h for p,h in oldcsv.items())
    ids=set();kinds=Counter();newrecords=[]
    for binding in manifest['shards']:
        p=root/binding['path'];assert sha(p)==binding['sha256'];rows=read(p);assert len(rows)==binding['records']
        for r in rows:
            assert r['test_id']not in ids;ids.add(r['test_id']);kinds[r['record_kind']]+=1
        if binding['path']not in oldshards:newrecords+=rows
    assert len(ids)==159087 and dict(kinds)==manifest['by_kind']and len(newrecords)==6336
    headers=[]
    for binding in manifest['csv_parts']:
        p=root/binding['path'];assert sha(p)==binding['sha256']
        with p.open()as f:headers.append(next(csv.reader(f)))
    assert headers[-1]!=headers[0]and set(headers[0])<=set(headers[-1])
    assert all(h==headers[0]for h in headers[:-1])
    report=dict(state='PASS_FINAL_PUBLIC_CHAMPIONS_COMPARATORS_COVERAGE_AND_INDEX',checked_at_utc=datetime.now(timezone.utc).isoformat(),category_champions_sha256=sha(base/'CATEGORY_CHAMPIONS.json'),category_count=12,exact_numeric_point_event_leaders=len(declared),annotations_checked=annotations,comparator_reverse_views_checked=reverse,empty_paired_views_preserved_null=empty,coverage_manifest_sha256=sha(base/'coverage/COVERAGE_MANIFEST.json'),coverage_rows=len(grid),FIT_REQUIRED_scientific_cells=len(fits),fixed_reference_NOT_APPLICABLE_cells=len(fixed),index_manifest=pointer['manifest'],index_manifest_sha256=sha(root/pointer['manifest']),index_records=len(ids),reused_immutable_JSON_shards=len(oldshards),new_JSON_shards=5,reused_immutable_CSV_parts=len(oldcsv),new_CSV_parts=1,new_index_records=len(newrecords),CSV_header_policy='Prior headers reused; new columns extend header, combine by column name.',release_matrix_sha256=sha(base/'CATEGORY_RELEASE_MATRIX.json'),release_categories=12,admitted_or_deployed_categories=0,new_fits=0,new_forecasts=0,new_grades=0,new_NFL_observations=0,resources=dict(wall_seconds=time.monotonic()-start,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024))
    with a.output.open('x')as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps(report))


if __name__=='__main__':main()
