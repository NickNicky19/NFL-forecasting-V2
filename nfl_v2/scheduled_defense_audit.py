"""Freeze and audit the scheduled-window alternative. There is no fit action.

Every root is an explicit CLI argument. Public receipts contain safe artifact
IDs, hashes and aggregates, never absolute private paths or player records.
"""
from __future__ import annotations

import collections
import csv
import gzip
import hashlib
import json
import platform
import resource
import time
from pathlib import Path

from . import chart_wave, chart_sources, week8_shadow, hgb_control as source, qualified_defense as old
from . import qualified_defense_inputs as inputs, scheduled_defense as candidate
from . import distribution_wave_v2 as learner, ordered_information_ablation as recipe

VERSION = 'v2-scheduled-defense-window-alternative-audit-v1'
CAPACITY_BLOCK = 'BLOCKED_DURABLE_RETENTION_CAPACITY; no NFL fit authorized'
TARGETS = recipe.TARGETS
POLICIES = learner.POLICIES
GROUPS = inputs.GROUPS
canonical, sha, now, write = source.canonical, source.sha, source.now, source.immutable_json


def load(path):
    return json.loads(Path(path).read_bytes())


def modules():
    return (candidate, old, inputs, source, source.empirical, chart_wave, chart_sources,
            week8_shadow, learner, recipe)


def require_fit_permission():
    raise RuntimeError(CAPACITY_BLOCK)


def prepare(*, original_public, original_private, source_root, public_root,
            leader_table, membership_root):
    original_public, original_private, source_root, public_root, leader_table, membership_root = map(
        Path, (original_public, original_private, source_root, public_root, leader_table, membership_root))
    if public_root.exists():
        raise ValueError('fresh immutable public output required')
    original = load(original_public / 'FROZEN_PROTOCOL.json')
    for m in modules():
        if Path(m.__file__).name in original['helpers'] and original['helpers'][Path(m.__file__).name] != sha(m.__file__):
            raise ValueError('retained original helper no longer matches source-bound version')
    for s in original['source_ids']:
        if sha(source_root / s['name']) != s['sha256']:
            raise ValueError('admitted source hash mismatch')
    if sha(original_private / 'frozen-queries.json') != original['frozen_queries_sha256']:
        raise ValueError('original query bytes changed')
    bindings = []
    for path in sorted(original_public.glob('*-FIT.json')):
        r = load(path)
        if 'training_membership_sha256' not in r:
            continue
        bindings.append(dict(artifact_id=path.name, sha256=sha(path),
            target=r['target'], policy_id=r['policy_id'], information_group=r['information_group'],
            training_n=r['training_n'], training_membership_sha256=r['training_membership_sha256']))
    if len(bindings) != 768:
        raise ValueError('all 672 historical plus 96 original future fit receipts required')
    members = []
    for sub in ('pregame-cohort-scorecards-v2', 'chart-cohort-scorecards-v1'):
        path = membership_root / sub / 'memberships.json.gz'
        members.append(dict(artifact_id='RETAINED-' + sha(path), member=sub + '/memberships.json.gz',
                            sha256=sha(path)))
    with leader_table.open() as handle:
        leaders = [r for r in csv.DictReader(handle) if r['rank'] == '1']
    point = [r for r in leaders if r['ranking_product'] == 'display_point']
    if {r['target'] for r in point} != set(TARGETS):
        raise ValueError('twelve strongest compatible full-primary point references required')
    public_root.mkdir(parents=True)
    write(public_root / 'ORIGINAL_FIT_BINDINGS.json', bindings)
    protocol = dict(version=VERSION, registered_at_utc=now(),
        state='FROZEN_BEFORE_SCHEDULED_FEATURE_AUDIT; NFL_FITS_BLOCKED',
        code_sha256=sha(__file__), helper_sha256={Path(m.__file__).name: sha(m.__file__) for m in modules()},
        original_protocol_sha256=sha(original_public / 'FROZEN_PROTOCOL.json'),
        original_fit_bindings_sha256=sha(public_root / 'ORIGINAL_FIT_BINDINGS.json'),
        frozen_queries_sha256=original['frozen_queries_sha256'], source_ids=original['source_ids'],
        source_role_contract=original['source_role_contract'], source_vintage='current_vintage_reconstruction',
        chart_label_packet_sha256=original['chart_label_packet_sha256'],
        original_future_query_asof_utc=original['fixed_future_query_asof_utc'],
        mechanism='Replace last four OBSERVED defense-position groups with last four SCHEDULED regular-season team games, availability kickoff+7days strictly before cutoff; absent groups occupy an unknown slot. Same D1 four/D2 nine columns, unchanged league compatible-rate prior, own features, learner, target labels, training members, priors and fallback.',
        absence='Absent position group: target_sum/rate numerator/exposure unknown; zero rows/known rows are coverage counts only. Existing observed group with missing target remains incomplete and consumes a slot. No padded zero outcome.',
        age='D2 latest_eligible_age_days uses latest eligible scheduled kickoff, including absent group. This is part of the declared window change, not separately hidden.',
        chronology='Weekly fit before earliest 2026 week kickoff; training features at their own kickoff; per-game historical query features at kickoff. All availability assumed kickoff+7days, strict left-limit. Common feature floor2022; STRICT floor2026 includes own/opponent/league/prior/transforms. No pre2022 data or current2026W8 outcomes.',
        learner=dict(family='ordered_leaf_cdf', forest=learner.FOREST,
            law='95% equal-tree empirical leaf PMF + 5% identical same-arm role/global prior',
            fallback='identical retained minimum60/allzero count/singleclass/own-history n8 routing'),
        targets=list(TARGETS), policies={k: dict(history_regime=a, fit_floor=b, feature_floor=c)
                                       for k, (a, b, c) in POLICIES.items()},
        historical_query_cells=17968, future_reference_query_cells=2229,
        future='Audit only at original16:59:45 cutoff. No new capture/issuance. Future fitting remains blocked; any later capture must freeze a new real cutoff, open deadlines and actual issue/persistence clocks before inference, and cannot inherit old capture times.',
        leader_table_sha256=sha(leader_table), strongest_reference_specs=leaders,
        comparisons='Each target/group/policy on same query IDs vs retained observed D1/D2, same-policy original own-player Leaf control and frozen strongest compatible full-primary control. Keep point MAE, genuine-mean MSE and legitimate-law CRPS/NLL/Brier separate. Do not select new winners within subgroups.',
        cohort_memberships=members,
        subgroup_views=['all', 'top10', 'top15', 'top20', 'rank_1_10', 'rank_11_15', 'rank_16_20',
                        'remainder', 'frozen opportunity bands', 'chart signed-score-history bands'],
        selectors='Reuse exact frozen memberships; last3 earlier available slots, missing consumes slots, cutoff earliest week kickoff-minus90 plus assumed7day availability. Chart bands are score history, not workload. Same competitor membership; full-system, own-learned, all-core-arm learned intersection, candidate/control learned intersection and fallback contributions. Retrospective participant universe remains.',
        uncertainty='Paired candidate-minus-control week losses; seven weeks insufficient for reliable bootstrap CI; retain week deltas/game-cluster sensitivity, selection/multiplicity exposure and ties. No future routing or ROI claims.',
        audit_budget=dict(max_fit_calls=0, max_inference_calls=0, wall_seconds=240,
            cpu_seconds=300, max_peak_memory_bytes=1073741824, max_threads=1,
            max_public_bytes=16777216, max_source_rows=200000),
        blocked_fit_budget=dict(historical_opportunities=672, possible_new_future_opportunities=96,
            max_fit_calls=768, max_threads=2, wall_seconds=1200, cpu_seconds=1800,
            max_peak_memory_bytes=2147483648, max_private_bytes=1073741824,
            max_forecast_rows=600000, hyperparameter_searches=0),
        admission=CAPACITY_BLOCK,
        prerequisites=['root verifies complete approved durable retention for original and new source/code/model/prediction bundles',
                       'independent prefit protocol/code review', 'root schedules one sole fit worker',
                       'fresh future-cutoff/deadline amendment before any future inference'],
        new_family_count=0, actual_fit_calls=0, new_forecasts=0, week8_outcomes_read=0,
        official_capture=False, deployed=False)
    write(public_root / 'FROZEN_PROTOCOL.json', protocol)
    grid = [dict(week=w, target=t, policy_id=p, information_group=g,
                 procedure_id=candidate.VERSION + ':' + g,
                 state='BLOCKED_DURABLE_RETENTION_CAPACITY', actual_fit_calls=0)
            for w in range(1, 9) for t in TARGETS for p in POLICIES for g in GROUPS]
    write(public_root / 'BLOCKED_FIT_GRID.json', grid)
    return protocol


def _change(old_features, new_features, old_audit, new_audit):
    changed = [c for c in old.RATE_COLUMNS if old_features[c] != new_features[c]]
    return dict(window_changed=old_audit['local_game_ids'] != new_audit['local_game_ids'],
                changed_columns=changed, absent_slots=new_audit['absent_group_slots'])


def _aggregate(contexts, columns):
    result = collections.Counter()
    for item in contexts:
        result['contexts'] += 1
        result['window_changed'] += int(item['window_changed'])
        cols = set(item['changed_columns']) & set(columns)
        result['any_raw_feature_changed'] += bool(cols)
        result['absent_slot_contexts'] += item['absent_slots'] > 0
        for c in cols:
            result['changed_' + c] += 1
    return dict(result)


def audit(*, original_public, original_private, source_root, public_root):
    original_public, original_private, source_root, public_root = map(
        Path, (original_public, original_private, source_root, public_root))
    p = load(public_root / 'FROZEN_PROTOCOL.json')
    if p['code_sha256'] != sha(__file__):
        raise ValueError('frozen audit code changed')
    for m in modules():
        if p['helper_sha256'][Path(m.__file__).name] != sha(m.__file__):
            raise ValueError('frozen feature/source/learner helper changed')
    for s in p['source_ids']:
        if sha(source_root / s['name']) != s['sha256']:
            raise ValueError('source bytes changed')
    if sha(original_private / 'frozen-queries.json') != p['frozen_queries_sha256']:
        raise ValueError('original query binding changed')
    if sha(original_public / 'FROZEN_PROTOCOL.json') != p['original_protocol_sha256']:
        raise ValueError('original protocol changed')
    bindings = load(public_root / 'ORIGINAL_FIT_BINDINGS.json')
    if sha(public_root / 'ORIGINAL_FIT_BINDINGS.json') != p['original_fit_bindings_sha256']:
        raise ValueError('fit receipt bindings changed')
    start, cpu = time.monotonic(), time.process_time()

    def guard():
        b = p['audit_budget']
        if time.monotonic()-start > b['wall_seconds'] or time.process_time()-cpu > b['cpu_seconds']:
            raise RuntimeError('AUDIT_TIME_BUDGET')
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024 > b['max_peak_memory_bytes']:
            raise RuntimeError('AUDIT_MEMORY_BUDGET')

    # The existing loader filters current Week8+ before outcome-field decoding.
    loader_protocol = dict(p, budget=dict(max_source_rows=p['audit_budget']['max_source_rows']))
    rows, games, counts, _, _ = chart_wave.load_chart_source(source_root, loader_protocol)
    inputs.attach_context(rows, games, source_root)
    observed = inputs.build_history(rows, TARGETS)
    scheduled = candidate.build_history(rows, games, TARGETS)
    lookup = {(r['game_id'], r['player_id']): r for r in rows}
    all_contexts, context_lookup, source_totals = {}, {}, []
    for target in TARGETS:
        roles = set(source.POSITIONS) if target == old.CHART else source.allowed_roles(p, target)
        for floor in (2022, 2026):
            eligible = [r for r in rows if r['season'] >= floor and r['position'] in roles
                        and r['values'][target] is not None]
            records = []
            for r in eligible:
                a, aa = observed.at(r['defense'], r['position'], target, r['kickoff'], feature_floor=floor)
                b, ba = scheduled.at(r['defense'], r['position'], target, r['kickoff'], feature_floor=floor)
                if (aa['league_rate'], aa['league_opportunities'], aa['league_rate_games']) != (
                        ba['league_rate'], ba['league_opportunities'], ba['league_rate_games']):
                    raise AssertionError('league prior changed')
                change = _change(a, b, aa, ba)
                item = dict(game_id=r['game_id'], player_id=r['player_id'], season=r['season'],
                            position=r['position'], available=r['available'], **change)
                records.append(item)
                context_lookup[target, floor, r['game_id'], r['player_id']] = change
            all_contexts[target, floor] = records
            for season in sorted({r['season'] for r in records}):
                for group, columns in GROUPS.items():
                    rr = [r for r in records if r['season'] == season]
                    source_totals.append(dict(target=target, feature_floor=floor, season=season,
                        information_group=group, **_aggregate(rr, columns)))
            guard()
    fit_changes = []
    for binding in bindings:
        path = original_public / binding['artifact_id']
        if sha(path) != binding['sha256']:
            raise ValueError('original fit receipt changed')
        r = load(path)
        arm, fit_floor, floor = POLICIES[r['policy_id']]
        origin = source.utc(r.get('fit_cutoff_utc') or r['training_label_fit_cutoff_utc']).timestamp()
        records = [x for x in all_contexts[r['target'], floor]
                   if x['season'] >= fit_floor and x['available'] < origin]
        membership = hashlib.sha256(canonical([(x['game_id'], x['player_id']) for x in records])).hexdigest()
        if len(records) != r['training_n'] or membership != r['training_membership_sha256']:
            raise ValueError('exact original training membership not reproduced')
        fit_changes.append(dict(artifact_id=binding['artifact_id'], target=r['target'],
            policy_id=r['policy_id'], history_regime=arm, feature_floor=floor,
            information_group=r['information_group'], training_membership_sha256=membership,
            future_reference=binding['artifact_id'].startswith('FUTURE-'),
            **_aggregate(records, GROUPS[r['information_group']])))
        guard()
    queries = load(original_private / 'frozen-queries.json')
    query_totals = []
    for period, qs in (('2026_W1_W7', queries['historical']), ('OLD_FUTURE_CONTEXT_ONLY', queries['week8'])):
        for floor in (2022, 2026):
            for target in TARGETS:
                changes, blocked = [], 0
                for q in qs:
                    if q['target'] != target:
                        continue
                    if q.get('blocked_reason') or q.get('position') not in source.POSITIONS:
                        blocked += 1
                        continue
                    if period == '2026_W1_W7':
                        row = lookup[q['game_id'], q['player_id']]
                        defense, cutoff = row['defense'], row['kickoff']
                    else:
                        if q.get('actual') is not None:
                            raise ValueError('future outcome forbidden')
                        defense, cutoff = q['defense'], source.utc(p['original_future_query_asof_utc']).timestamp()
                    a, aa = observed.at(defense, q['position'], target, cutoff, feature_floor=floor)
                    b, ba = scheduled.at(defense, q['position'], target, cutoff, feature_floor=floor)
                    changes.append(_change(a, b, aa, ba))
                for group, columns in GROUPS.items():
                    query_totals.append(dict(period=period, target=target, feature_floor=floor,
                        information_group=group, blocked_contexts=blocked,
                        **_aggregate(changes, columns)))
                guard()
    changed_source_ids = sorted((t, f, x['game_id'], x['player_id']) for (t, f), rr in all_contexts.items()
                                for x in rr if x['changed_columns'])
    writes = {
        'SOURCE_TRAINING_FEATURE_CHANGES.json': source_totals,
        'ORIGINAL_FIT_TRAINING_FEATURE_CHANGES.json': fit_changes,
        'QUERY_FEATURE_CHANGES.json': query_totals,
    }
    for name, value in writes.items():
        write(public_root / name, value)
    receipt = dict(version=VERSION, state='COMPLETE_NO_FIT_SOURCE_FEATURE_AUDIT',
        completed_at_utc=now(), protocol_sha256=sha(public_root / 'FROZEN_PROTOCOL.json'),
        code_sha256=sha(__file__), source_counts=counts,
        source_player_game_rows=len(rows), unique_scheduled_games=len(scheduled.games),
        audited_original_fit_receipts=len(fit_changes),
        original_fit_receipts_with_window_changes=sum(r.get('window_changed', 0) > 0 for r in fit_changes),
        original_fit_receipts_with_changed_raw_features=sum(r.get('any_raw_feature_changed', 0) > 0 for r in fit_changes),
        unique_target_floor_training_contexts=sum(len(rr) for rr in all_contexts.values()),
        changed_raw_feature_contexts=len(changed_source_ids),
        changed_context_membership_sha256=hashlib.sha256(canonical(changed_source_ids)).hexdigest(),
        raw_feature_change_counts_are_not_forecast_or_error_changes=True,
        output_bindings={name: dict(sha256=sha(public_root/name), bytes=(public_root/name).stat().st_size)
                         for name in writes},
        resource=dict(wall_seconds=time.monotonic()-start, cpu_seconds=time.process_time()-cpu,
            peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024, max_threads=1),
        environment=dict(python=platform.python_version()),
        actual_fit_calls=0, inference_calls=0, new_forecasts=0, score_views=0,
        week8_outcomes_read=0, fit_admission=CAPACITY_BLOCK)
    write(public_root / 'AUDIT_RECEIPT.json', receipt)
    return receipt
