"""Exact chart labels from the specifically qualified frozen NFLverse snapshots.

This is a source-specific partial mapping, not generic fantasy-score parity.
The caller must verify source bytes, complete games and appearance separately.
No source acquisition or model execution occurs here.
"""
from decimal import Decimal, InvalidOperation

POLICY_ID = 'v2-nick-chart-ppr-nflverse-explicit-zero-subset-v2'
POLICY_SHA256 = '3a53c4d67bdedff7320c32390439d9f2964ef5c3233ec74bef1a201740680511'
CSV_SHA256_BY_SEASON = {
    2022:'ad426c3fe5bf1cc30c3f137fdfe96d054e19d400879ee4413129da49fa7b54be',
    2023:'f19cb71a5de0dce7fd09376026237c9ee9d5a93fe13815a2ea3ec2d37204cb17',
    2024:'3ddc45a84f759aa348ce465ae001752c530575455717657cdfe1f8abfcdb4759',
    2025:'e5e0615b3d96a3eaebfaee91e55afb4a4e7fe0caf057454177bcd7d6ad4bcfc2',
    2026:'8301e4e3ab62af3f65d201251676dd79f912dce7a87a402835fe5ea4fb5d0379',
}
FIELDS = {
    'passing_yards':'passing_yards','passing_TD':'passing_tds',
    'interceptions_thrown':'passing_interceptions','rushing_yards':'rushing_yards',
    'rushing_TD':'rushing_tds','receptions':'receptions','receiving_yards':'receiving_yards',
    'receiving_TD':'receiving_tds','fumbles_lost':'fumbles_lost_total',
    'passing_2pt':'passing_2pt_conversions','rushing_2pt':'rushing_2pt_conversions',
    'receiving_2pt':'receiving_2pt_conversions',
}
WEIGHTS_TIMES_50 = {
    'passing_yards':2,'passing_TD':200,'interceptions_thrown':-50,
    'rushing_yards':5,'rushing_TD':300,'receptions':50,'receiving_yards':5,
    'receiving_TD':300,'fumbles_lost':-50,'passing_2pt':100,'rushing_2pt':100,
    'receiving_2pt':100,'offensive_fumble_recovery_TD':300,'kick_return_TD':300,
    'punt_return_TD':300,'field_goal_return_TD':300,
}
RARE = tuple(k for k in WEIGHTS_TIMES_50 if k not in FIELDS)
SIGNED_YARDS = {'passing_yards','rushing_yards','receiving_yards'}


def _integer(value, *, signed=False):
    if value is None or isinstance(value,bool):return None
    try:number=Decimal(str(value))
    except (InvalidOperation,ValueError):return None
    if not number.is_finite() or number!=number.to_integral_value() or (number<0 and not signed):return None
    return int(number)


def chart_label(row, *, source_sha256, appearance_verified, game_completed_verified):
    """Return supported point/grid value, or explicit missing reason and components.

    Both rare supersets must be explicitly zero; positive rare cases are never
    substituted by those broad totals. The hash argument is a binding declaration;
    callers must actually verify the source bytes before calling this function.
    """
    year=_integer(row.get('season'));week=_integer(row.get('week'))
    if (year not in CSV_SHA256_BY_SEASON or source_sha256!=CSV_SHA256_BY_SEASON[year]
            or row.get('season_type')!='REG' or week is None or not 1<=week<=18
            or (year==2026 and week>7)):
        raise ValueError('row/source outside qualified immutable regular-season panel')
    if type(appearance_verified)is not bool or type(game_completed_verified)is not bool:
        raise ValueError('explicit appearance and game-finality qualification required')
    components={k:_integer(row.get(field),signed=k in SIGNED_YARDS) for k,field in FIELDS.items()}
    f=_integer(row.get('fumble_recovery_tds'));s=_integer(row.get('special_teams_tds'))
    rare_zero=f==s==0
    components.update({k:0 if rare_zero else None for k in RARE})
    reason=(
        'GAME_COMPLETION_NOT_VERIFIED' if not game_completed_verified else
        'APPEARANCE_NOT_VERIFIED' if not appearance_verified else
        'MISSING_OR_INVALID_DIRECT_COMPONENT' if any(components[k]is None for k in FIELDS) else
        'EXCEPTIONAL_TD_ATTRIBUTION_UNRESOLVED' if not rare_zero else None)
    scaled=None if reason else sum(WEIGHTS_TIMES_50[k]*components[k] for k in WEIGHTS_TIMES_50)
    return dict(target_id='nick-chart-ppr-v1',policy_id=POLICY_ID,policy_sha256=POLICY_SHA256,
        status='SUPPORTED_EXPLICIT_SUPERSET_ZERO' if reason is None else reason,
        components=components,rare_zero_contract_satisfied=rare_zero,
        points_times_50=scaled,points=None if scaled is None else scaled/50,
        point_grid_denominator=50,source_sha256=source_sha256,
        appearance_verified=appearance_verified,game_completed_verified=game_completed_verified)
