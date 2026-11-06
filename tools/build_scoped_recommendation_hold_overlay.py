#!/usr/bin/env python3
"""Append a specific defect's admission metadata, never rewrite NFL scores."""
import argparse
import collections
import gzip
import hashlib
import json
import resource
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nfl_v2.recommendation_holds import recommendation_hold
from nfl_v2.result_index import RIGHT_WRONG_KIND


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def save(p, x):
    with p.open('x') as f:
        json.dump(x, f, indent=2, allow_nan=False)
        f.write('\n')


def old_generic_filter(r):
    return not any(x.get('diagnostic_only') is True or x.get('default_rank_eligible') is False
        or x.get('record_kind', x.get('kind')) == RIGHT_WRONG_KIND
        for x in (r, r.get('source_aggregate_fields') or {}))


def main():
    a = argparse.ArgumentParser()
    a.add_argument('--out', type=Path, required=True)
    args = a.parse_args()
    out = args.out.resolve()
    out.mkdir(exist_ok=False)
    start, cpu = time.monotonic(), time.process_time()
    pointer = ROOT / 'registries/CURRENT_RESULTS_INDEX.json'
    manifest = ROOT / json.loads(pointer.read_bytes())['manifest']
    idx = json.loads(manifest.read_bytes())
    bound = dict(source_index_manifest=str(manifest.relative_to(ROOT)), source_index_sha256=sha(manifest),
        source_records=idx['record_count'], hold_registry='registries/PROCEDURE_ADMISSION_HOLDS.json',
        hold_registry_sha256=sha(ROOT / 'registries/PROCEDURE_ADMISSION_HOLDS.json'),
        filter_code_sha256=sha(ROOT / 'nfl_v2/recommendation_holds.py'),
        code_sha256=sha(Path(__file__)), started_at_utc=datetime.now(timezone.utc).isoformat(),
        source_score_bytes_may_not_change=True, max_rows=650000,
        max_wall_seconds=240, max_cpu_seconds=240, max_RSS_bytes=1073741824,
        new_NFL_fits=0, new_NFL_scores=0)
    save(out / 'FROZEN_HOLD_OVERLAY_BINDINGS.json', bound)
    held, counts, seen = [], collections.Counter(), 0
    for shard in idx['shards']:
        p = ROOT / shard['path']
        b = p.read_bytes()
        if len(b) != shard['bytes'] or hashlib.sha256(b).hexdigest() != shard['sha256']:
            raise ValueError('immutable score shard mismatch')
        if shard.get('compression') == 'gzip':
            b = gzip.decompress(b)
            if len(b) != shard['uncompressed_bytes'] or hashlib.sha256(b).hexdigest() != shard['uncompressed_sha256']:
                raise ValueError('expanded score bytes mismatch')
        rows = json.loads(b)
        if len(rows) != shard['records']:
            raise ValueError('shard row count mismatch')
        for r in rows:
            seen += 1
            hold = recommendation_hold(r)
            if not hold:
                continue
            held.append(dict(test_id=r['test_id'], procedure_id=r.get('procedure_id'),
                category=r.get('category'), history_regime=r.get('history_regime'),
                product_id=r.get('product_id'), source_artifact=r.get('source_artifact'),
                source_artifact_sha256=r.get('source_artifact_sha256'), hold_id=hold,
                prior_generic_filter_passed=old_generic_filter(r),
                recommendation_eligible=False, retained_for_score_audit=True))
            counts['all_held_source_views'] += 1
            counts['previous_generic_passes'] += old_generic_filter(r)
            counts['already_diagnostic_excluded'] += not old_generic_filter(r)
        if seen > bound['max_rows'] or time.monotonic()-start > 240 or time.process_time()-cpu > 240:
            raise ValueError('bounded overlay limit')
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024 > bound['max_RSS_bytes']:
            raise ValueError('overlay memory limit')
    assert seen == idx['record_count']
    body = json.dumps(held, sort_keys=True, separators=(',', ':')).encode()
    blob = gzip.compress(body, mtime=0)
    if len(blob) > 4194304:
        raise ValueError('public overlay limit before write')
    target = out / 'HELD_RECORD_ANNOTATIONS.json.gz'
    with target.open('xb') as f:
        f.write(blob)
    assert target.read_bytes() == blob
    oldrank = ROOT / 'reports/continuation-20261030d/current-ranking-v2'
    rank = json.loads((oldrank / 'PROCEDURE_RANKINGS.json').read_bytes())
    top = json.loads((oldrank / 'TOP5_BY_CATEGORY_PRODUCT.json').read_bytes())
    rank_held = [r for r in rank if recommendation_hold(r)]
    top_held = [r for r in top if recommendation_hold(r)]
    save(out / 'LEGACY_RANKING_HOLD_STATUS.json', dict(
        raw_ranking_source_sha256=sha(oldrank / 'PROCEDURE_RANKINGS.json'),
        original_raw_ranking_rows=len(rank), held_raw_ranking_rows=rank_held,
        top5_source_sha256=sha(oldrank / 'TOP5_BY_CATEGORY_PRODUCT.json'),
        original_top5_rows=len(top), held_top5_rows=top_held,
        old_bytes_preserved=True, other_admission_requirements_unchanged=True))
    qual = ROOT / 'reports/post-wave-5w-v1/B-product-week-qualification-v3/B_PRODUCT_WEEK_QUALIFICATION.json.gz'
    qr = json.loads(gzip.decompress(qual.read_bytes()))
    qheld = [dict(qualification_id=r['qualification_id'], procedure_id=r['procedure_id'],
        category=r['category'], product_id=r['product_id'], history=r['history'],
        retained_duration_floor_status=r['minimum_week_floor_status'],
        primary_product_admission='HELD_CONFIRMED_PROCEDURE_DEFECT',
        hold_id=recommendation_hold(r), do_not_reset_or_borrow_test_weeks=True)
        for r in qr if recommendation_hold(r)]
    save(out / 'FIVE_WEEK_HOLD_ANNOTATIONS.json', dict(source=str(qual.relative_to(ROOT)),
        source_sha256=sha(qual), annotations=qheld, raw_week_evidence_unchanged=True))
    receipt = dict(state='PASS_SCOPED_HOLD_OVERLAY_NO_SCORE_OR_FORECAST_CHANGE',
        at_utc=datetime.now(timezone.utc).isoformat(), **counts, scanned_records=seen,
        held_record_annotations=dict(path=str(target.relative_to(ROOT)), sha256=sha(target),
            bytes=len(blob), uncompressed_sha256=hashlib.sha256(body).hexdigest(), records=len(held)),
        raw_legacy_ranking_rows_held=len(rank_held), existing_top5_rows_held=len(top_held),
        qualification_view_annotations=len(qheld), native_leader_changes_not_established_by_this_filter=True,
        frozen_bindings_sha256=sha(out / 'FROZEN_HOLD_OVERLAY_BINDINGS.json'),
        new_NFL_fits=0, new_forecasts=0, new_grade_changes=0,
        scope='Specific failedcarryprocedure only; not all zero predictions, allHGBs or allcount targets. Passingholdfilterisnotfullqualification.',
        resources=dict(wall_seconds=time.monotonic()-start, cpu_seconds=time.process_time()-cpu,
                       peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024))
    save(out / 'RUN_RECEIPT.json', receipt)
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
