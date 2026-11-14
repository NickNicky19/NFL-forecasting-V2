"""Lagged FTN ball-quality inputs, with explicit source denominators.

FTN Data via nflverse, CC BY-SA 4.0 for charting-derived inputs/models.
The declared canonical seven-day reconstruction is not publication proof.
"""
from __future__ import annotations

import math

FLAGS = ('is_throw_away', 'is_interception_worthy')
VERSION = 'B-FTN-LAGGED-BALL-QUALITY-INFORMATION-v1'


def _number(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _count(value):
    result = _number(value)
    if result is None or result < 0 or result != int(result):
        raise ValueError('Count must be explicit finite nonnegative integer')
    return int(result)


def _key(row):
    return str(row['game_id']), str(row['player_id'])


def _qualified_qb(row):
    return (row.get('position') == 'QB' and row.get('physical_participation') is True
            and row.get('target_parity') is True)


class QBFTNInformation:
    """Take canonical earlier appearances first, then join source information."""

    def __init__(self, history, quality_rows, *, window=8, strength=20.):
        if window != 8 or strength != 20.:
            raise ValueError('This fixed information comparison uses own8/strength20')
        self.history, self.window, self.strength = history, window, strength
        canonical = {_key(r): r for r in history.all_rows if _qualified_qb(r)}
        self.quality = {}
        self.source_row_diagnostics = dict(non_target_rows=0, unknown_clock_rows=0)
        seen = set()
        for source in quality_rows:
            identity = _key(source)
            if identity in seen:
                raise ValueError('Duplicate FTN passer-game identity/version')
            seen.add(identity)
            base = canonical.get(identity)
            if base is None:
                self.source_row_diagnostics['non_target_rows'] += 1
                continue
            for field in ('season', 'week', 'team', 'opponent', 'kickoff'):
                if field in source and source[field] != base.get(field):
                    raise ValueError('FTN canonical identity/context conflict: ' + field)
            # A wholly absent source clock follows the declared canonical
            # reconstruction. An explicitly unknown clock never inherits it.
            clock = _number(source['available'] if 'available' in source else base.get('available'))
            base_clock = _number(base.get('available'))
            kickoff = _number(base.get('kickoff'))
            if clock is None or base_clock is None or kickoff is None:
                self.source_row_diagnostics['unknown_clock_rows'] += 1
                continue
            if clock != base_clock or clock != kickoff + 7 * 86400:
                raise ValueError('Changed FTN versus canonical seven-day information policy')
            eligible = _count(source['eligible_throws'])
            if eligible != _count(base['attempts']):
                raise ValueError('FTN credited-attempt denominator differs from canonical QB history')
            charted = _count(source.get('charted_throws', source.get('matched_chart_rows')))
            if charted > eligible:
                raise ValueError('Chart matches exceed eligible throws')
            flags = {}
            for name in FLAGS:
                value = source.get('flags', {}).get(name)
                if value is None:
                    flags[name] = dict(known=0, positive=0, unknown=eligible)
                    continue
                known, positive = _count(value['known']), _count(value['positive'])
                unknown = _count(value.get('unknown', eligible - known))
                if not 0 <= positive <= known <= charted <= eligible or known + unknown != eligible:
                    raise ValueError('Invalid FTN flag numerator/denominator/presence')
                flags[name] = dict(known=known, positive=positive, unknown=unknown)
            self.quality[identity] = dict(available=clock, eligible_throws=eligible,
                                          charted_throws=charted, flags=flags)

    def _eligible(self, cutoff, *, player=None):
        result = []
        for row in self.history.all_rows:
            clock, kickoff = _number(row.get('available')), _number(row.get('kickoff'))
            if (not _qualified_qb(row) or clock is None or kickoff is None or not clock < cutoff
                    or player is not None and row['player_id'] != player):
                continue
            if not kickoff < clock:
                raise ValueError('Historical outcome available before its own game')
            result.append(row)
        return sorted(result, key=lambda r: (r['kickoff'], r['game_id'], r['player_id']))

    def describe(self, query):
        cutoff = _number(query.get('kickoff'))
        if cutoff is None:
            raise ValueError('Finite query cutoff required')
        earlier = self._eligible(cutoff)
        own = self._eligible(cutoff, player=query['player_id'])[-self.window:]
        eligible_throws = sum(_count(r['attempts']) for r in own)
        joined = [(r, self.quality.get(_key(r))) for r in own]
        joined = [(r, c) for r, c in joined if c is not None and c['available'] < cutoff]
        charted = sum(c['charted_throws'] for r, c in joined)
        support = dict(charted_fraction=charted / eligible_throws if eligible_throws else None,
                       charted_fraction_missing=not eligible_throws,
                       charted_throws_log1p=math.log1p(charted))
        details = {}
        global_eligible_throws = sum(_count(r['attempts']) for r in earlier)
        for name in FLAGS:
            observed = [(r, c) for r, c in joined if c['flags'][name]['known'] > 0]
            known = sum(c['flags'][name]['known'] for r, c in joined)
            positive = sum(c['flags'][name]['positive'] for r, c in joined)
            pool = [(r, self.quality.get(_key(r))) for r in earlier]
            pool = [(r, c) for r, c in pool if c is not None and c['available'] < cutoff
                    and c['flags'][name]['known'] > 0]
            pk = sum(c['flags'][name]['known'] for r, c in pool)
            pp = sum(c['flags'][name]['positive'] for r, c in pool)
            # Fixed Beta(1,1) league mean; own support shrinks20 throws toward
            # it. The no-own/no-pooled indicators retain fallback provenance.
            pooled = (pp + 1.) / (pk + 2.)
            latest = max((c['available'] for r, c in observed), default=None)
            age = (cutoff - latest) / 86400 if latest is not None else None
            details[name] = dict(known=known, positive=positive,
                unknown=eligible_throws - known, eligible_throws=eligible_throws,
                raw=positive / known if known else None,
                prior_known=pk, prior_positive=pp, pooled_beta_mean=pooled,
                shrunk=(positive + self.strength * pooled) / (known + self.strength),
                own_age_days=age, latest_own_source_available=latest,
                latest_prior_source_available=max((c['available'] for r, c in pool), default=None),
                latest_own_flag_game=None if not observed else observed[-1][0]['game_id'],
                fallback='OBSERVED_OWN_SHRUNK' if known else 'EARLIER_QB_POOL_PRIOR' if pk else 'FIXED_BETA11_PRIOR_NO_SOURCE')
            prefix = name + ':'
            support.update({prefix + 'known_fraction': known / eligible_throws if eligible_throws else None,
                prefix + 'known_fraction_missing': not eligible_throws,
                prefix + 'known_log1p': math.log1p(known), prefix + 'own_age_days': age,
                prefix + 'own_age_missing': age is None, prefix + 'own_known_missing': not known,
                prefix + 'pooled_known_missing': not pk})
        return dict(version=VERSION, flags=details, support=support,
            trace=dict(own_window_game_ids=[r['game_id'] for r in own],
                own_window_appearances=len(own),
                own_quality_record_game_ids=[r['game_id'] for r, c in joined],
                own_chart_game_ids=[r['game_id'] for r, c in joined if c['charted_throws']],
                eligible_throws=eligible_throws, charted_throws=charted,
                latest_own_chart_source_available=max((c['available'] for r, c in joined if c['charted_throws']), default=None),
                global_eligible_QB_games=len(earlier)),
            source_tier='CURRENT_VINTAGE_DECLARED_SEVEN_DAY_RECONSTRUCTION_NOT_AUTHENTICATED_FTN_PUBLICATION',
            complete_required_charting=all(v['known'] == eligible_throws and
                                           v['prior_known'] == global_eligible_throws
                                           for v in details.values()),
            license='FTN Data via nflverse, CC-BY-SA-4.0',
            interpretation='Lagged charted throwaway and interception-worthy rates; not completion identity, pure accuracy, alignment, pressure or target-game context.')


def support_feature_order():
    """Trace diagnostics; not appended when source support is equivalent."""
    names = ['charted_fraction', 'charted_fraction_missing', 'charted_throws_log1p']
    for name in FLAGS:
        names += [name + ':' + suffix for suffix in
                  ('known_fraction', 'known_fraction_missing', 'known_log1p', 'own_age_days',
                   'own_age_missing', 'own_known_missing', 'pooled_known_missing')]
    return names


def feature_order(arm):
    if arm not in ('B0', 'B1', 'B2'):
        raise ValueError('Unknown information arm')
    if arm in ('B0', 'B1'):
        return []
    return [name + ':shrunk' for name in FLAGS]


def feature_values(description, arm):
    if arm == 'B2' and not description['complete_required_charting']:
        raise ValueError('Partial FTN history requires the exact frozen B0 fallback')
    return [float(description['flags'][name[:-7]]['shrunk'])
            for name in feature_order(arm)]
