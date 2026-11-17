"""One fixed information ablation on the retained E3 completion law.

The profiles describe earlier opportunity denominators. They are neither
starter labels nor the realized workload/context of the query game.
"""
import math
import numpy as np

VERSION = 'B-QB-OPPORTUNITY-PROFILE-INCREMENT-v1'
ARMS = ('R0', 'R1', 'R2', 'R3')
RATES = ('dropback_per_opportunity', 'attempt_per_dropback', 'sack_per_dropback',
         'scramble_per_dropback', 'spike_per_attempt')
VOLUMES = ('opportunities', 'dropbacks', 'credited_attempts', 'sacks')


def extra_names(arm):
    if arm not in ARMS:
        raise ValueError('Unknown arm')
    names = []
    if arm != 'R0':
        names += [('R1_support', f'{g}_{n}') for g in ('own', 'offense', 'defense')
                  for n in ('opportunities', 'unknown_dropback')]
    if arm in ('R2', 'R3'):
        names += value_names('R2_player_values', ('own', 'offense'))
        names += [('R2_player_values', 'own_QB_dropback_share'),
                  ('R2_player_values', 'own_QB_attempt_share')]
    if arm == 'R3':
        names += value_names('R3_defense_values', ('defense',))
    return names


def value_names(block, groups):
    out = []
    for g in groups:
        out += [(block, f'{g}_{r}') for r in RATES
                if g != 'own' or r != 'dropback_per_opportunity']
        out += [(block, f'{g}_{v}_per_game') for v in VOLUMES]
        out += [(block, f'{g}_{c}_{j}_dropback_mix')
                for c in ('down', 'distance', 'field') for j in range(5)]
    return out


def appended_features(groups, arm):
    values = []
    for block, name in extra_names(arm):
        v = groups[block].get(name)
        missing = v is None or not math.isfinite(float(v))
        v = 0. if missing else float(v)
        if block == 'R1_support':
            v = math.log1p(v)
        # Fixed neutral fill with an explicit indicator; no fit on future rows.
        values += [v, float(missing)]
    return np.asarray(values, dtype=float)


def feature_order(base_order, arm):
    return list(base_order) + [label for b, n in extra_names(arm)
                               for label in (b + ':' + n, b + ':' + n + ':MISSING')]


def direct_features(query, history, opportunity, arm):
    base = history.direct_features(query, 'E3')
    return np.concatenate([base, appended_features(opportunity.feature_groups(query), arm)])


def priority(query, history):
    d = history.describe(query)
    mean = history.exposure(query).mean
    return dict(policy='UNCHANGED_COMMON_EXPOSURE_HISTORY_PRIORITY-v1',
                member=bool(d['own_games'] > 0 and mean >= 10),
                reference_expected_attempts=mean, eligible_own_games=d['own_games'],
                inclusion_reason='EARLIER_OWN_HISTORY_AND_REFERENCE_ATTEMPTS_GE10'
                if d['own_games'] > 0 and mean >= 10 else 'BASIC_PROFILE_RETAINED',
                status='CONDITIONAL_RECONSTRUCTED_WORKLOAD_PROXY_NOT_AUTHENTICATED_EXPECTED_STARTER',
                qb_top20='NOT_APPLICABLE', recommendation_eligibility='SEPARATE_RETAINED_OFFER_CONTRACT')
