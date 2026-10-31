"""Synthetic chronology/model spies only; no NFL rows, fit or inference."""
import copy
import contextlib
import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

from nfl_v2 import defense_season_executor as runner
from nfl_v2 import qualified_defense as defense
from nfl_v2 import qualified_defense_inputs as inputs
from nfl_v2.distribution_laws import Law
from tools.run_defense_seasons import main


TARGET = 'pass_att'
ROLES = {'source_role_contract': {'primary': {TARGET: ['QB']}, 'extended': {}}}


def fixture(year=2024):
    rows, games, queries = [], {}, []
    for season in range(2022, year + 1):
        for week in range(1, 19):
            kickoff = 1_650_000_000 + (season-2022)*365*86400 + week*7*86400
            game = f'{season}-{week:02}-A-B'
            games[game] = dict(season=season, week=week, kickoff=kickoff, home='A', away='B')
            for j in range(4):
                rows.append(dict(season=season, week=week, game_id=game, player_id=f'p{j}',
                    position='QB', kickoff=kickoff, available=kickoff+7*86400, played=True,
                    values={TARGET: float(20+week+j)}, team='A', defense='B',
                    workload=dict(attempts=20+week+j, carries=0, targets=0)))
            if season == year:
                queries.append(dict(season=year, week=week, game_id=game, player_id='p0',
                    position='QB', target=TARGET, population='primary', query_id='q'+str(week)))
    return rows, games, queries


def bindings(rows, games, queries, year=2024):
    features = runner.Features(rows, year, (TARGET,), ROLES)
    out = {}
    for week in runner.WEEKS:
        origin = min(g['kickoff'] for g in games.values() if g['season'] == year and g['week'] == week)
        qr = [q for q in queries if q['week'] == week]
        for policy in runner.plan.policies(year):
            packet = features.origin(year, week, TARGET, policy, origin, qr)
            out[runner.slot(week, TARGET, policy)] = packet['binding']
    return out


class SpyModel:
    def __init__(self, calls):
        self.calls = calls

    def fit(self, x, y, positions):
        self.calls.append(('fit', x.copy(), y.copy(), list(positions)))
        return self

    def predict(self, x, positions, priors):
        self.calls.append(('predict', x.copy(), list(positions)))
        return [(Law('zero'), {'synthetic_spy': True}) for _ in positions]


class DefenseSeasonExecutorTests(unittest.TestCase):
    def test_default_cli_does_not_decode_source_or_construct_model(self):
        with patch.object(runner.seasonal, 'load_source', side_effect=AssertionError('NFL read')), \
             patch.object(runner.laws, 'FittedLawModel', side_effect=AssertionError('real model')), \
             patch('builtins.print') as output:
            main([])
        result = json.loads(output.call_args.args[0])
        self.assertEqual(result['state'], 'PREFLIGHT_ONLY_NO_NFL_ROWS_OR_MODELS')
        self.assertEqual(result['logical_origins'], 1728)
        self.assertEqual(result['actual_fits'], 0)

    def test_season_policy_aliases_and_true2022_recent_remains_unimplemented(self):
        p = runner.metadata_plan(2022)
        self.assertEqual(p['unique_origin_ceiling'], 432)
        self.assertTrue(p['policies']['H-RECENT-COMMON']['recent2022_proxy'])
        self.assertEqual(p['policies']['H-RECENT-COMMON']['fit_floor'], 2022)
        self.assertIn('2021', p['exact_2022_recent'])
        self.assertEqual(runner.metadata_plan(2023)['unique_origin_ceiling'], 1296)
        for year in (2021, 2026, True):
            with self.assertRaises(ValueError):
                runner.metadata_plan(year)

    def test_spy_full18weeks_exact_dimensions_and_week1_startup(self):
        rows, games, queries = fixture()
        calls, before = [], []
        expected = bindings(rows, games, queries)
        with patch.object(runner.laws, 'FittedLawModel', side_effect=AssertionError('real model')):
            events = list(runner.observed_loop(rows=rows, games=games, queries=queries,
                year=2024, baseline=expected, role_contract=ROLES,
                model_factory=lambda _: SpyModel(calls), before_fit=lambda: before.append(1),
                guard=lambda: None, targets=(TARGET,)))
        self.assertEqual([e['week'] for e in events if e['kind'] == 'WEEK_COMPLETE'], list(range(1,19)))
        fits = [e for e in events if e['kind'] == 'FIT']
        self.assertEqual(len(fits), 18*4*2)
        self.assertEqual(len(before), sum(c[0] == 'fit' for c in calls))
        for event in fits:
            audit = event['audit']
            width = 24 if audit['information_group'] == 'D1' else 29
            self.assertEqual(event['train_features'].shape[1], width)
            self.assertEqual(event['query_features'].shape[1], width)
            self.assertEqual(audit['feature_columns'][:20], list(runner.source.FEATURES))
            for row in event['training']:
                self.assertLess(row['available'], audit['fit_cutoff'])
                self.assertGreaterEqual(row['season'], audit['fit_floor'])
            latest = audit['latest_training_consumed_feature_available']
            self.assertTrue(latest is None or latest < audit['fit_cutoff'])
        forecasts = [r for e in events if e['kind'] == 'FORECAST' for r in e['records']]
        self.assertEqual(len(forecasts), 18*4*2*2)
        startup = [r for r in forecasts if r['week'] == 1 and r['history_regime'] == 'H-CURRENT']
        self.assertTrue(startup)
        self.assertTrue(all(r['fallback'] == 'fixed_no_NFL_startup' for r in startup))
        self.assertTrue(all(r['prediction'] == 0 for r in startup))
        self.assertTrue(all(r['status'] == 'NEW_RECONSTRUCTED_RESEARCH_FORECAST' for r in forecasts))

    def test_target_and_future_outcomes_do_not_enter_origin(self):
        rows, games, queries = fixture()
        week = 8
        origin = games[queries[week-1]['game_id']]['kickoff']
        qr = [queries[week-1]]
        before = runner.Features(rows, 2024, (TARGET,), ROLES).origin(
            2024, week, TARGET, 'H-MULTI-COMMON', origin, qr)
        changed = copy.deepcopy(rows)
        for r in changed:
            if r['season'] == 2024 and r['week'] >= week-1:
                r['values'][TARGET] = 1_000_000.
        after = runner.Features(changed, 2024, (TARGET,), ROLES).origin(
            2024, week, TARGET, 'H-MULTI-COMMON', origin, qr)
        self.assertEqual(before['binding'], after['binding'])
        for a, b in zip(before['query_packets'], after['query_packets']):
            np.testing.assert_equal(a[1], b[1])
        # Week7 is exactly at label availability==origin and must be excluded.
        self.assertFalse(any(r['season'] == 2024 and r['week'] >= 7 for r in before['train']))

    def test_per_row_training_features_are_not_built_at_fit_origin(self):
        rows, games, queries = fixture()
        feature = runner.Features(rows, 2024, (TARGET,), ROLES)
        q = queries[10]
        packet = feature.origin(2024, 11, TARGET, 'H-MULTI-COMMON',
            games[q['game_id']]['kickoff'], [q])
        for r, p in zip(packet['train'], packet['packets']):
            expected, latest = feature.histories[2022].get(r['player_id'], 'QB', TARGET, r['kickoff'])
            np.testing.assert_equal(p[0], expected)
            self.assertTrue(latest is None or latest < r['kickoff'])

    def test_baseline_mismatch_stops_before_any_spy_fit(self):
        rows, games, queries = fixture()
        baseline = bindings(rows, games, queries)
        baseline['W01-pass_att-H-CURRENT-COMMON']['own_training_features_sha256'] = 'bad'
        with self.assertRaisesRegex(ValueError, 'baseline'), patch.object(
                runner.laws, 'FittedLawModel', side_effect=AssertionError('real model')):
            list(runner.observed_loop(rows=rows, games=games, queries=queries,
                year=2024, baseline=baseline, role_contract=ROLES,
                model_factory=lambda _: self.fail('must not construct a model'),
                before_fit=lambda: self.fail('must not fit'), guard=lambda: None, targets=(TARGET,)))

    def test_own_prior_query_and_cutoff_fields_all_fail_closed(self):
        rows, games, queries = fixture()
        expected = bindings(rows, games, queries)['W01-pass_att-H-CURRENT-COMMON']
        for name in runner.BINDING_FIELDS:
            mutated = dict(expected, **{name: 'invalid'})
            with self.subTest(name=name), self.assertRaises(ValueError):
                runner.check_baseline(expected, mutated)

    def test_missing_week_duplicate_future_pre2022_rejected(self):
        rows, games, queries = fixture()
        baseline = bindings(rows, games, queries)
        for bad in (queries[:-1], queries+[queries[0]], [dict(q, season=2025) for q in queries]):
            with self.assertRaises(ValueError):
                list(runner.observed_loop(rows=rows, games=games, queries=bad,
                    year=2024, baseline=baseline, role_contract=ROLES,
                    model_factory=lambda _: self.fail('model'), before_fit=lambda: None,
                    guard=lambda: None, targets=(TARGET,)))
        for year in (2021, 2025):
            with self.assertRaises(ValueError):
                runner.Features(rows+[dict(rows[0], season=year)], 2024, (TARGET,), ROLES)

    def test_exact_observed_window_absent_group_missing_group_and_floor(self):
        rows, games, queries = fixture()
        # Remove complete QB group week14; observed week15 with unknown target
        # occupies one slot; absent week14 does not occupy a scheduled-game slot.
        rows = [r for r in rows if not(r['season'] == 2024 and r['week'] == 14)]
        for r in rows:
            if r['season'] == 2024 and r['week'] == 15:
                r['values'][TARGET] = None
        hist = inputs.build_history(rows, (TARGET,))
        cutoff = games['2024-18-A-B']['kickoff']
        values, audit = hist.at('B', 'QB', TARGET, cutoff, feature_floor=2024)
        self.assertEqual(values['complete_target_games4'], 3)
        self.assertEqual(values['qualified_rows4'], 16)
        complete = [sum(20+w+j for j in range(4)) for w in (12, 13, 16)]
        # Strictly earlier availability excludes week17; window=12,13,15,16.
        self.assertEqual(values['qualified_allowed_mean4'], sum(complete)/3)
        self.assertLess(audit['latest_local_available'], cutoff)

    def test_context_opens_only_2022_through_evalyear_and_preserves_missing(self):
        rows, games, _ = fixture(2022)
        rows[0]['played'] = False
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'stats_player_week_2022.csv'
            fields = ['season_type','season','week','game_id','player_id','position','team','opponent_team','attempts','carries','targets']
            with path.open('w', newline='') as f:
                writer = csv.DictWriter(f, fields); writer.writeheader()
                writer.writerows(dict(season_type='REG', season=r['season'],week=r['week'],
                    game_id=r['game_id'],player_id=r['player_id'],position='QB',team='A',
                    opponent_team='B',attempts='20',carries='0',targets='') for r in rows)
            bound = runner.attach_context_through_year(rows, games, tmp, 2022)
            self.assertEqual(bound[0]['workload'], dict(attempts=None,carries=None,targets=None))
            self.assertEqual(bound[1]['workload']['targets'], None)
            # No2023..2026 files exist: attempting to open them would fail.

    def test_fabricated_retention_receipt_cannot_load_nfl_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp/'FROZEN_PROTOCOL.json').write_text('{}')
            fake = tmp/'fake.json'
            fake.write_text(json.dumps(dict(state=runner.retention.GATE_STATE,
                all_required_archives_verified=True, all_required_members_verified=True,
                missing_required_parts=0, completed_at_utc='2026-10-30T00:00:00Z')))
            with patch.object(runner.seasonal, 'load_source', side_effect=AssertionError('NFL read')), \
                 self.assertRaises(ValueError):
                runner.execute(public=tmp, private=tmp/'private', source_root=tmp,
                    queries_path=fake, baseline_path=fake, source_protocol_path=fake,
                    baseline_evidence_root=tmp, restoration_gate=fake,
                    verifier_receipt=fake, software_receipt=fake, worker_release=fake)

    def test_prepare_no_overwrite_and_rejects_future_source_contract(self):
        contract = dict(evaluation_season=2025,evaluation_weeks=list(range(1,19)),
            targets=list(runner.TARGETS), window='FOUR_OBSERVED_QUALIFIED_POSITION_GROUPS',
            source_ids=[dict(name='games.csv',sha256='a'*64)]+[
                dict(name=f'stats_player_week_{y}.csv',sha256='b'*64) for y in range(2022,2026)],
            source_protocol_sha256='c'*64,frozen_queries_sha256='d'*64,
            baseline_bindings_sha256='e'*64,
            budget=dict(max_threads=2,max_fit_calls=1,wall_seconds=1,cpu_seconds=1,
                max_peak_memory_bytes=1024,max_private_bytes=1024,max_source_rows=10,max_forecast_rows=10))
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)/'new'
            p = runner.prepare(contract=contract, public=output)
            self.assertEqual(p['state'], 'FROZEN_METADATA_NOT_ADMITTED')
            old = (output/'FROZEN_PROTOCOL.json').read_bytes()
            with self.assertRaises(ValueError): runner.prepare(contract=contract, public=output)
            self.assertEqual((output/'FROZEN_PROTOCOL.json').read_bytes(), old)
            contract['source_ids'].append(dict(name='stats_player_week_2026.csv',sha256='f'*64))
            with self.assertRaises(ValueError): runner.prepare(contract=contract, public=Path(tmp)/'other')
        with contextlib.redirect_stderr(__import__('io').StringIO()):
            with self.assertRaises(SystemExit): main(['execute'])
            with self.assertRaises(SystemExit): main(['baseline'])

    def test_existing_fit_facts_accept_new_metadata_without_original_training_matrix(self):
        rows, games, queries = fixture()
        binding = bindings(rows, games, queries)['W01-pass_att-H-CURRENT-COMMON']
        # This is the actual retained seasonal FIT schema, with no training-matrix field.
        fit = {k: binding[k] for k in ('target','policy_id','training_n',
            'training_membership_sha256','fit_cutoff','feature_floor',
            'prior_parameters','prior_position_sample_counts')}
        fit['method'] = 'leaf'
        runner.compare_retained_fit(binding, fit)
        changed = dict(fit, training_n=1)
        with self.assertRaises(ValueError): runner.compare_retained_fit(binding, changed)

    def test_failed_private_forecast_save_does_not_create_scored_rows(self):
        rows, games, queries = fixture()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); public = root/'public'; public.mkdir()
            (public/'FROZEN_PROTOCOL.json').write_text('{}')
            private = root/'private'
            p = dict(evaluation_season=2024, source_vintage='synthetic fixture',
                budget=dict(wall_seconds=10,cpu_seconds=10,max_peak_memory_bytes=2**40,
                            max_private_bytes=1,max_forecast_rows=10,max_fit_calls=1))
            baseline = {runner.slot(w,t,pol):{} for w in runner.WEEKS
                        for t in runner.TARGETS for pol in runner.plan.policies(2024)}
            row = dict(queries[0], prediction=0., actual=21., fallback='none',
                procedure_id='synthetic',policy_id='H-CURRENT-COMMON',history_regime='H-CURRENT',
                product_id='mean',distribution_summary=None)
            with patch.object(runner, '_verify_inputs', return_value=(p, {}, baseline, {'reconstruction_run_id':'synthetic'})), \
                 patch.object(runner.seasonal, 'load_source', return_value=(rows,games,{})), \
                 patch.object(runner, 'attach_context_through_year', return_value=rows), \
                 patch.object(runner, '_read_json', return_value=queries), \
                 patch.object(runner, 'observed_loop', return_value=iter([{'kind':'FORECAST','slot':'synthetic','records':[row]}])), \
                 patch.object(runner.laws, 'FittedLawModel', side_effect=AssertionError('real model')):
                receipt = runner.execute(public=public,private=private,source_root=root,
                    queries_path=root/'q',baseline_path=root/'b',source_protocol_path=root/'s',
                    baseline_evidence_root=root,restoration_gate=root/'g',
                    verifier_receipt=root/'v',software_receipt=root/'sw',worker_release=__file__)
            self.assertEqual(receipt['state'], 'PARTIAL_STOPPED')
            self.assertEqual(receipt['forecast_output_views'], 0)
            self.assertEqual(receipt['score_views'], 0)
            self.assertEqual(json.loads((public/'SCORES.json').read_text()), [])
            self.assertEqual(receipt['private_output_bytes'], 0)
            self.assertFalse((private/'predictions'/'synthetic.json.gz').exists())

    def test_public_failure_does_not_leak_private_exception_paths(self):
        rows, games, queries = fixture()
        marker = '/approved-private/owner-only/SECRET_LOCATOR'
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); public = root/'public'; public.mkdir()
            (public/'FROZEN_PROTOCOL.json').write_text('{}')
            p = dict(evaluation_season=2024, source_vintage='synthetic fixture',
                budget=dict(wall_seconds=10,cpu_seconds=10,max_peak_memory_bytes=2**40,
                            max_private_bytes=100_000,max_forecast_rows=10,max_fit_calls=1))
            with patch.object(runner, '_verify_inputs', return_value=(p, {}, {}, {'reconstruction_run_id':'synthetic'})), \
                 patch.object(runner.seasonal, 'load_source', side_effect=FileNotFoundError(marker)), \
                 patch.object(runner.laws, 'FittedLawModel', side_effect=AssertionError('real model')):
                receipt = runner.execute(public=public,private=root/'private',source_root=root,
                    queries_path=root/'q',baseline_path=root/'b',source_protocol_path=root/'s',
                    baseline_evidence_root=root,restoration_gate=root/'g',
                    verifier_receipt=root/'v',software_receipt=root/'sw',worker_release=__file__)
            self.assertNotIn(marker, json.dumps(receipt))
            self.assertEqual(receipt['failures'][0]['type'], 'FileNotFoundError')
            import gzip
            detail = root/'private'/receipt['failures'][0]['private_detail']['member']
            self.assertIn(marker, gzip.decompress(detail.read_bytes()).decode())

    def _run_synthetic_fit_fault(self, events, private_budget=1):
        rows, games, queries = fixture()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); public = root/'public'; public.mkdir()
            (public/'FROZEN_PROTOCOL.json').write_text('{}')
            p = dict(evaluation_season=2024, source_vintage='synthetic fixture',
                budget=dict(wall_seconds=10,cpu_seconds=10,max_peak_memory_bytes=2**40,
                            max_private_bytes=private_budget,max_forecast_rows=10,max_fit_calls=1))
            baseline = {runner.slot(w,t,pol):{} for w in runner.WEEKS
                        for t in runner.TARGETS for pol in runner.plan.policies(2024)}
            with patch.object(runner, '_verify_inputs', return_value=(p, {}, baseline, {'reconstruction_run_id':'synthetic-v2'})), \
                 patch.object(runner.seasonal, 'load_source', return_value=(rows,games,{})), \
                 patch.object(runner, 'attach_context_through_year', return_value=rows), \
                 patch.object(runner, '_read_json', return_value=queries), \
                 patch.object(runner, 'observed_loop', side_effect=events), \
                 patch.object(runner.laws, 'FittedLawModel', side_effect=AssertionError('real model')):
                receipt = runner.execute(public=public,private=root/'private',source_root=root,
                    queries_path=root/'q',baseline_path=root/'b',source_protocol_path=root/'s',
                    baseline_evidence_root=root,restoration_gate=root/'g',
                    verifier_receipt=root/'v',software_receipt=root/'sw',worker_release=__file__)
            return receipt, json.loads((public/'GRID_STATUS.json').read_text())

    def test_first_fit_evidence_save_failure_preserves_attempted_unretained_slot(self):
        cell = 'W01-pass_att-H-MULTI-COMMON-D1'
        def events(**kwargs):
            yield dict(kind='FIT_REGISTERED',slot=cell)
            kwargs['before_fit']()
            yield dict(kind='FIT_STARTED',slot=cell)
            yield dict(kind='FIT',slot=cell,audit=dict(state='FITTED_RETAINED',alias_of=None),
                model=object(),train_features=np.zeros((1,24)),query_features=np.zeros((1,24)),
                training=[],queries=[],query_packets=[])
        receipt, grid = self._run_synthetic_fit_fault(events)
        row = next(r for r in grid if r['slot'] == cell)
        self.assertEqual(receipt['actual_fit_calls'], 1)
        self.assertEqual(receipt['fit_attempted_cells'], 1)
        self.assertEqual(receipt['unretained_fit_attempt_cells'], 1)
        self.assertEqual(receipt['forecast_output_views'], 0)
        self.assertEqual(receipt['score_views'], 0)
        self.assertEqual(row['state'], 'FIT_ATTEMPTED_UNRETAINED')
        self.assertEqual(row['algorithm_state'], 'FIT_SUCCEEDED')
        self.assertTrue(row['fit_attempted'])
        self.assertFalse(row['model_retained'])

    def test_post_fit_guard_failure_keeps_started_attempt(self):
        cell = 'W01-pass_att-H-MULTI-COMMON-D2'
        calls = []
        def events(**kwargs):
            yield dict(kind='FIT_REGISTERED',slot=cell)
            kwargs['before_fit']()
            yield dict(kind='FIT_STARTED',slot=cell)
            SpyModel(calls).fit(np.zeros((60,29)),np.zeros(60),['QB']*60)
            raise RuntimeError('TIME_BUDGET')
        receipt, grid = self._run_synthetic_fit_fault(events)
        row = next(r for r in grid if r['slot'] == cell)
        self.assertEqual(len(calls), 1)
        self.assertEqual(receipt['actual_fit_calls'], 1)
        self.assertEqual(row['state'], 'FIT_ATTEMPTED_UNRETAINED')
        self.assertTrue(row['fit_attempted'])
        self.assertEqual(row['algorithm_state'], 'FIT_RESULT_NOT_YET_OBSERVED')
        self.assertEqual(receipt['score_views'], 0)

    def test_no_fit_and_reused_result_retention_failures_do_not_invent_fit_calls(self):
        cell = 'W01-pass_att-H-CURRENT-COMMON-D1'
        for state, alias, wanted in [
            ('NO_FIT_INSUFFICIENT_TRAINING',None,'NO_FIT_FALLBACK_EVIDENCE_UNRETAINED'),
            ('REUSED_IDENTICAL_POLICY:FITTED_RETAINED','earlier','REUSED_RESULT_EVIDENCE_UNRETAINED')]:
            def events(**kwargs):
                yield dict(kind='FIT',slot=cell,audit=dict(state=state,alias_of=alias),
                    model=None,train_features=np.zeros((0,24)),query_features=np.zeros((1,24)),
                    training=[],queries=[],query_packets=[])
            receipt, grid = self._run_synthetic_fit_fault(events)
            row = next(r for r in grid if r['slot'] == cell)
            self.assertEqual(receipt['actual_fit_calls'], 0)
            self.assertEqual(row['state'], wanted)
            self.assertFalse(row['fit_attempted'])
            self.assertEqual(row['computation_reused'], alias is not None)

    def test_started_event_precedes_spy_optimizer_and_post_fit_guard(self):
        rows, games, queries = fixture()
        baseline = bindings(rows, games, queries)
        calls = []
        def guard():
            if calls:
                raise RuntimeError('synthetic stop after optimizer')
        stream = runner.observed_loop(rows=rows,games=games,queries=queries,
            year=2024,baseline=baseline,role_contract=ROLES,
            model_factory=lambda _:SpyModel(calls),before_fit=lambda:None,
            guard=guard,targets=(TARGET,))
        seen = []
        with self.assertRaisesRegex(RuntimeError, 'after optimizer'):
            for event in stream:
                seen.append(event)
                if event['kind'] == 'FIT_STARTED':
                    self.assertEqual(calls, [])
        started = [e for e in seen if e['kind'] == 'FIT_STARTED']
        self.assertEqual(len(started), 1)
        self.assertTrue(any(e['kind'] == 'FIT_REGISTERED' and e['slot'] == started[0]['slot'] for e in seen))
        self.assertFalse(any(e['kind'] == 'FIT' and e['slot'] == started[0]['slot'] for e in seen))


if __name__ == '__main__':
    unittest.main()
