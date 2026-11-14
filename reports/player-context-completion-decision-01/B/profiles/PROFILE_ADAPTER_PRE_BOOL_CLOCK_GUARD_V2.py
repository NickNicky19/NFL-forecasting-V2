"""Reusable, typed as-of profiles for the frozen B QB-context history.

Profiles describe eligible past observations. They neither qualify a query
universe nor constitute a forecast, offered selection or live capture.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime, timezone

import numpy as np
from scipy.stats import beta

from .player_context_matchup import ContextHistory, FIELD_NAMES, _sum

VERSION = 'B-QB-ASOF-PROFILE-v1'
DEPTHS = ('BEHIND_LOS', 'AIR_0_TO_LT10', 'AIR_10_TO_LT20', 'AIR_GE20', 'UNKNOWN')
DOWNS = ('1', '2', '3', '4', 'UNKNOWN')
HISTORICAL_UNIVERSE = 'RETROSPECTIVE_OFFICIAL_QB_STAT_ROWS_NOT_EXANTE_ROSTER'
SOURCE_TIER = 'CURRENT_REVISED_SOURCE_SEVEN_DAY_RECONSTRUCTION'


def _iso(t):
    return datetime.fromtimestamp(float(t), timezone.utc).isoformat()


def _ratio(n, d):
    if d == 0:
        return dict(numerator=n, denominator=d, estimate=None, state='UNDEFINED_ZERO_DENOMINATOR')
    return dict(numerator=n, denominator=d, estimate=n/d,
                state='KNOWN_ZERO' if n == 0 else 'OBSERVED_POSITIVE')


def _interval(alpha, beta_value):
    if alpha <= 0 or beta_value <= 0:
        return None
    return [float(beta.ppf(.05, alpha, beta_value)), float(beta.ppf(.95, alpha, beta_value))]


def _rows_summary(rows, cutoff):
    return dict(eligible_games=len(rows),
                game_ids=[r['game_id'] for r in rows],
                latest_game=None if not rows else rows[-1]['game_id'],
                latest_game_at=None if not rows else _iso(rows[-1]['kickoff']),
                latest_source_available_at=None if not rows else _iso(max(r['available'] for r in rows)),
                latest_game_age_days=None if not rows else (cutoff-max(r['kickoff'] for r in rows))/86400,
                latest_source_age_days=None if not rows else (cutoff-max(r['available'] for r in rows))/86400)


def _query_identity(query):
    fields = ('player_id', 'game_id', 'team', 'opponent', 'season', 'week', 'kickoff')
    identity = {k:query.get(k) for k in fields}
    identity['role'] = query.get('position', 'QB')
    identity['cutoff'] = query.get('cutoff', query.get('kickoff'))
    return identity


def _unavailable(query, reason, universe):
    identity = _query_identity(query)
    # Invalid supplied fields still yield serializable unavailable records.
    # Nonfinite clocks must not become non-standard JSON or a numerical zero.
    identity = {k:(v if isinstance(v,str) or (not isinstance(v,bool) and isinstance(v,(int,float)) and math.isfinite(v)) else None)
                for k,v in identity.items()}
    key = json.dumps(identity, sort_keys=True, separators=(',', ':'))
    return dict(profile_id=hashlib.sha256((VERSION+key).encode()).hexdigest(),
                profile_version=VERSION, identity=identity, status='UNAVAILABLE_PROFILE',
                reason=reason, query_universe=universe, source_tier=SOURCE_TIER)


def query_validation(query, universe):
    """Check supplied query evidence; do not inspect target outcomes."""
    identity = _query_identity(query)
    for key in ('player_id', 'game_id', 'team', 'opponent'):
        if not isinstance(identity[key], str) or not identity[key]:
            return 'MISSING_CANONICAL_'+key.upper()
    if identity['role'] != 'QB':
        return 'UNSUPPORTED_ROLE'
    for key in ('season', 'week', 'kickoff', 'cutoff'):
        if isinstance(identity[key], bool) or not isinstance(identity[key], (int, float)) or not math.isfinite(identity[key]):
            return 'INVALID_'+key.upper()
    if identity['cutoff'] > identity['kickoff']:
        return 'CUTOFF_AFTER_TARGET_KICKOFF'
    if universe == HISTORICAL_UNIVERSE:
        return None
    if universe != 'SUPPLIED_QUALIFIED_PREGAME_QUERY_UNIVERSE':
        return 'UNQUALIFIED_QUERY_UNIVERSE'
    evidence = query.get('query_evidence', {})
    if not isinstance(evidence,dict):
        return 'QUERY_EVIDENCE_UNAVAILABLE'
    required = ('canonical_identity_verified', 'historical_team_verified', 'eligible_role_verified')
    if not all(evidence.get(k) is True for k in required):
        return 'QUERY_IDENTITY_TEAM_OR_ROLE_UNVERIFIED'
    if not isinstance(evidence.get('source_id'), str) or not evidence['source_id']:
        return 'MISSING_QUERY_MEMBERSHIP_SOURCE'
    if re.fullmatch('[0-9a-f]{64}', str(evidence.get('source_sha256', ''))) is None:
        return 'MISSING_QUERY_MEMBERSHIP_SOURCE_HASH'
    clock = evidence.get('recorded_at')
    if not isinstance(clock, (int, float)) or not math.isfinite(clock) or clock > identity['cutoff']:
        return 'QUERY_MEMBERSHIP_NOT_RETAINED_BEFORE_CUTOFF'
    return None


class QBProfileAdapter:
    def __init__(self, rows, *, window=8, strength=20., depth_annotations=None):
        self.history = ContextHistory(rows, window=window, strength=strength)
        self.depth_annotations = depth_annotations
        self.depth_history = None
        if depth_annotations is not None:
            from .qb_depth_catchability import DepthHistory
            self.depth_history = DepthHistory(rows,list(depth_annotations.values()),window,strength)

    def build(self, query, *, universe):
        reason = query_validation(query, universe)
        if reason:
            return _unavailable(query, reason, universe)
        identity = _query_identity(query)
        cutoff = float(identity['cutoff'])
        # ContextHistory's query cutoff is named kickoff. The actual target
        # kickoff stays in the typed identity; no target outcomes are read.
        work = dict(query, kickoff=cutoff)
        history = self.history
        d = history.describe(work)
        own = history.player_rows(query['player_id'], cutoff)
        eligible = history.eligible(cutoff)
        a, c = history.global_counts(cutoff)
        oa, oc = _sum(own, 'context_attempts'), _sum(own, 'context_completions')
        total = float(oa.sum())
        league_mix = (a+1)/(a.sum()+25)
        contexts = []
        for j, (down, depth) in enumerate((down, depth) for down in DOWNS for depth in DEPTHS):
            alpha = float(oa[j]+20*league_mix[j])
            completion_alpha = float(oc[j]+history.strength*d['pooled'][j])
            completion_beta = float(oa[j]-oc[j]+history.strength*(1-d['pooled'][j]))
            contexts.append(dict(context_index=j, down=down, attempted_air_depth=depth,
                attempt_frequency=_ratio(float(oa[j]), total),
                completion_per_attempt=_ratio(float(oc[j]), float(oa[j])),
                shrunk_attempt_frequency=float(d['mix'][j]),
                shrunk_completion_per_attempt=float(d['own_rate'][j]),
                estimate_support=dict(own_attempts=float(oa[j]), own_completions=float(oc[j]),
                    league_attempts=float(a[j]), league_completions=float(c[j])),
                empirical_bayes_90pct_interval=dict(
                    attempt_mix=_interval(alpha, total+20-alpha),
                    completion_rate=_interval(completion_alpha, completion_beta))))
        defense = history.group_rows(query['opponent'], cutoff, True)
        da, dc = _sum(defense, 'context_attempts'), _sum(defense, 'context_completions')
        de = _sum(defense, 'expected_player_completions')
        opponent_context = [dict(context_index=j, attempts=float(da[j]), completions=float(dc[j]),
            expected_from_earlier_offense=float(de[j]), numerator=float(dc[j]-de[j]),
            denominator=float(da[j]+100), shrunk_residual=float(d['opponent_residual'][j]),
            own_mix_product=float(d['mix'][j]*d['opponent_residual'][j])) for j in range(25)]
        field_context = {}
        for name in FIELD_NAMES:
            cells = [r['field_context'][name] for r in own if r['field_context'][name]['mean'] is not None]
            numerator = sum(x['mean']*x['n'] for x in cells)
            denominator = sum(x['n'] for x in cells)
            field_context[name] = dict(weighted_sum=numerator, throws_with_observation=denominator,
                mean=numerator/denominator if denominator else None,
                state='OBSERVED' if denominator else 'ABSENT_DATA')
        exposure = history.exposure(work)
        destination_keys = sorted({k for r in own for k in r.get('pass_destination_counts', {})}
                                  | {'left', 'middle', 'right', 'UNKNOWN'})
        destinations = {side:sum(r.get('pass_destination_counts', {}).get(side, 0) for r in own)
                        for side in destination_keys}
        destination_denominator = sum(destinations.values())
        annotations = self._annotation_profile(own, cutoff, work)
        key = json.dumps(identity, sort_keys=True, separators=(',', ':'))
        result = dict(profile_id=hashlib.sha256((VERSION+key).encode()).hexdigest(), profile_version=VERSION,
            status='AVAILABLE_PROFILE', identity=identity, query_universe=universe,
            query_evidence=None if not isinstance(query.get('query_evidence'),dict) else
                {k:query['query_evidence'].get(k)for k in ('source_id','source_sha256','recorded_at',
                    'canonical_identity_verified','historical_team_verified','eligible_role_verified')},
            source_tier=SOURCE_TIER,
            membership_verification='Supplied evidence contract checked structurally; independent source identity/roster authentication remains the capture owner responsibility.',
            source_clocks=dict(cutoff_at=_iso(cutoff), target_kickoff_at=_iso(identity['kickoff']),
                availability_policy='kickoff+7days strictly less than cutoff; reconstructed, not authenticated publication',
                latest_global_source_at=None if not eligible else _iso(max(r['available'] for r in eligible))),
            history=dict(own_lookback_appearances=history.window, opponent_lookback_games=16,
                own=_rows_summary(own, cutoff), opponent=_rows_summary(defense, cutoff),
                global_eligible_QB_games=len(eligible), feature_memory='eligible2022+; training history separately bound'),
            fallback=d['fallback'], contexts=contexts, field_context=field_context,
            attempts=dict(definition='Official credited nonsack/nontwopoint pass attempts; not dropbacks',
                past_sum=float(sum(r['official_attempts'] for r in own)), past_games=len(own),
                past_mean=None if not own else float(np.mean([r['official_attempts'] for r in own])),
                frozen_exposure_law=None if exposure is None else exposure.parameters(),
                component_status='UNAVAILABLE_COMPONENT' if exposure is None else 'AVAILABLE_COMPONENT',
                unavailable_reason='NO_ELIGIBLE_LEAGUE_HISTORY' if exposure is None else None,
                conditioning='Retained physical-participation panel; no bookmaker nonvoid claim'),
            dropbacks=dict(state='UNAVAILABLE_SOURCE_FOR_THIS_PROFILE',
                reason='Accepted game input does not retain all QB-stint sack/scramble/designed-dropback counts.'),
            pass_destination=dict(counts=destinations, denominator=destination_denominator,
                fractions={side:_ratio(n, destination_denominator) for side,n in destinations.items()},
                meaning='Thrown-ball destination, not receiver starting alignment; offense-relative field orientation not newly authenticated'),
            charted_depth_annotations=annotations, opponent_context=opponent_context,
            role_stint=dict(state='PARTIAL',role='QB',historical_team=query['team'],
                limitation='Historical team is supplied by bound source/query; no forecast of starter/limited/replacement probabilities.'),
            not_supplied=dict(receiver_alignment='SOURCE_BLOCKED',all_routes='SOURCE_BLOCKED',
                future_game_script='NOT_MODELED',realized_target_context='EXCLUDED'),
            uncertainty_contract='Empirical-Bayes intervals summarize the declared pseudo-count model only; shared prior/football dependence and parameter uncertainty are not fully modeled. Not a predictive guarantee.',
            consumed_by_frozen_forecasts={
                'E0':'Own-target FeatureHistory counts/recency/age; consumes no new context block.',
                'E1':['contexts.shrunk_attempt_frequency','contexts.shrunk_completion_per_attempt','contexts.estimate_support.own_attempts','history.own','field_context'],
                'E2':'E1 plus opponent_context residual/support and opponent main residual',
                'E3':'E2 plus opponent_context.own_mix_product',
                'P1_P2_P3':'Own total completion tendency, context indicators, offense/defense residuals; information/parameter sharing remains procedure-specific.',
                'COMMON_EXPOSURE':'attempts.frozen_exposure_law',
                'C1_D1':'charted_depth_annotations.frozen_depth_describer.support',
                'C2_D2':'C1/D1 plus logit(charted_depth_annotations.frozen_depth_describer.shrunk)',
                'charting_limits':'Drop/contested rates and pooled-known-zero diagnostic are retained here but not separately added to C1/C2/D1/D2.'})
        return result

    def _annotation_profile(self, own, cutoff, query):
        if self.depth_annotations is None:
            return dict(state='UNAVAILABLE_SOURCE', reason='Depth-conditioned charting mapping not supplied; aggregate game flags are not depth-specific catchability.')
        cells = []
        for depth_index, depth in enumerate(DEPTHS):
            flags = {}
            for flag in ('is_catchable_ball','is_drop','is_contested_ball'):
                known = positive = 0
                for r in own:
                    item = self.depth_annotations.get((r['game_id'],r['player_id']))
                    if item is None:
                        continue
                    if item.get('available', r['available']) >= cutoff:
                        continue
                    f = item.get('flags', {}).get(flag)
                    if f is None:
                        continue
                    known += f['known'][depth_index];positive += f['positive'][depth_index]
                flags[flag] = dict(_ratio(positive, known),
                    annotation_state='NO_KNOWN_ANNOTATIONS' if not known else 'KNOWN_ANNOTATIONS')
            cells.append(dict(depth_index=depth_index,depth=depth,annotations=flags))
        frozen = dict(self.depth_history.describe(query))
        frozen['own_known_zero'] = [n==0 for n in frozen['known']]
        frozen['pooled_known_zero'] = [n==0 for n in frozen['pooled_known']]
        frozen['raw_state'] = ['UNDEFINED_ZERO_DENOMINATOR' if n==0 else 'KNOWN_ZERO' if p==0 else 'OBSERVED_POSITIVE'
                               for n,p in zip(frozen['known'],frozen['positive'])]
        frozen['pooled_raw_state'] = ['UNDEFINED_ZERO_DENOMINATOR' if n==0 else 'KNOWN_ZERO' if p==0 else 'OBSERVED_POSITIVE'
                                      for n,p in zip(frozen['pooled_known'],frozen['pooled_positive'])]
        return dict(state='SUPPLIED_DEPTH_MAPPING',contexts=cells,frozen_depth_describer=frozen,
            meaning='Each provider annotation has its own known-annotation denominator; no completion/catchability/drop accounting identity imposed.')

    def build_many(self, queries, *, universe):
        results = []
        identities = set()
        for query in queries:
            identity = json.dumps(_query_identity(query),sort_keys=True,separators=(',',':'))
            if identity in identities:
                raise ValueError('Duplicate supplied profile query identity')
            identities.add(identity)
            results.append(self.build(query,universe=universe))
        return results
