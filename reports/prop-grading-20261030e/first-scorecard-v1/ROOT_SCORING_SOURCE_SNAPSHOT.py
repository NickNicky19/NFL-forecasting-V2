"""Original independent scoring implementation. No upstream imports."""
import math
from decimal import Decimal, InvalidOperation
from statistics import fmean

CHART_WEIGHTS = {
    'passing_yards': .04, 'passing_TD': 4, 'interceptions_thrown': -1,
    'rushing_yards': .1, 'rushing_TD': 6, 'receptions': 1,
    'receiving_yards': .1, 'receiving_TD': 6, 'fumbles_lost': -1,
    'passing_2pt': 2, 'rushing_2pt': 2, 'receiving_2pt': 2,
    'offensive_fumble_recovery_TD': 6, 'kick_return_TD': 6,
    'punt_return_TD': 6, 'field_goal_return_TD': 6,
}
COUNTS = {'pass_td', 'pass_cmp', 'pass_att', 'pass_int', 'rush_att', 'rec'}
TARGETS = ('pass_yd','pass_td','pass_cmp','pass_att','pass_int','rush_yd',
           'rush_att','rec','rec_yd','rush_rec_yd','nick-chart-ppr-v1','anytime_td')

def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)

def valid_actual(target, value):
    if not finite(value):
        return False
    if target in COUNTS:
        return value >= 0 and int(value) == value
    if target == 'anytime_td':
        return value in (0, 1)
    return True  # Signed yards and chart points are retained.

def chart_points(components):
    """None means an incomplete/invalid component contract, never zero-fill."""
    if any(not finite(components.get(k)) for k in CHART_WEIGHTS):
        return None
    yard_fields = {'passing_yards', 'rushing_yards', 'receiving_yards'}
    if any(v < 0 or int(v) != v for k, v in components.items()
           if k in CHART_WEIGHTS and k not in yard_fields):
        return None
    return math.fsum(CHART_WEIGHTS[k] * components[k] for k in CHART_WEIGHTS)

def anytime_td(rushing_td, receiving_td):
    if any(v is not None and (not finite(v) or v < 0 or int(v) != v)
           for v in (rushing_td, receiving_td)):
        return None
    if any(finite(v) and v > 0 for v in (rushing_td, receiving_td)):
        return 1
    if all(finite(v) and v == 0 for v in (rushing_td, receiving_td)):
        return 0
    return None

def quantile(values, p):
    """Linear interpolation at index (n-1)p; frozen for all diagnostics."""
    if not values:
        return None
    a = sorted(values); x = (len(a)-1)*p; i = math.floor(x); j = math.ceil(x)
    return a[i] + (a[j]-a[i])*(x-i)

def point_metrics(predictions, actuals, target):
    if len(predictions) != len(actuals):
        raise ValueError('unaligned vectors')
    if not predictions:
        return {'n': 0, 'mae': None, 'mse': None, 'rmse': None, 'bias': None}
    if not all(finite(p) and valid_actual(target,y) for p,y in zip(predictions,actuals)):
        raise ValueError('invalid/missing score input')
    if target == 'anytime_td' and any(p < 0 or p > 1 for p in predictions):
        raise ValueError('invalid event probability')
    e = [p-y for p,y in zip(predictions,actuals)]; a = list(map(abs,e))
    mse = fmean(x*x for x in e)
    r = {'n': len(e), 'mae': fmean(a), 'mse': mse, 'rmse': math.sqrt(mse),
         'bias': fmean(e), 'p90_abs': quantile(a,.9), 'p95_abs': quantile(a,.95),
         'max_abs': max(a), 'exact_rate': fmean(x==0 for x in a)}
    for tolerance in (1,5,10):
        r[f'abs_lt_{tolerance}'] = fmean(x<tolerance for x in a)
        r[f'abs_le_{tolerance}'] = fmean(x<=tolerance for x in a)
    if target == 'anytime_td':
        r['brier'] = mse; r['prevalence'] = fmean(actuals)
        losses=[]
        for p,y in zip(predictions,actuals):
            q=p if y else 1-p
            losses.append(-math.log(q) if q else math.inf)
        r['log_loss'] = fmean(losses)  # No post-evaluation clipping.
    return r

def event_probabilities(support, mass, line):
    if len(support)!=len(mass) or not support or len(set(support))!=len(support):
        raise ValueError('invalid discrete law')
    values = [exact_decimal(x) for x in support]
    threshold = exact_decimal(line)
    if len(set(values)) != len(values):
        raise ValueError('duplicate exact support')
    if any(not finite(x) or x<0 for x in mass) or not math.isclose(math.fsum(mass),1,rel_tol=0,abs_tol=1e-12):
        raise ValueError('invalid normalized mass')
    return {name: math.fsum(p for y,p in zip(values,mass) if test(y))
            for name,test in [('over',lambda y:y>threshold),('under',lambda y:y<threshold),('push',lambda y:y==threshold)]}

def expected_net(p_win,p_loss,decimal_odds):
    if not all(finite(x) for x in (p_win,p_loss,decimal_odds)) or min(p_win,p_loss)<0 or p_win+p_loss>1+1e-12 or decimal_odds<=1:
        raise ValueError('invalid refund-on-push/void inputs')
    return p_win*(decimal_odds-1)-p_loss

def settle(actual, line, side, decimal_odds, state='played'):
    """Legacy refund wrapper; callers certify scope. New adapters use grade_settlement.

    Original chart floats cannot recover their component grid here. Use exact
    components/certified source values before grading; never round a forecast.
    """
    if side not in ('over','under') or not finite(line) or not finite(decimal_odds) or decimal_odds<=1:
        raise ValueError('invalid offer')
    if state in ('void','canceled'):
        return ('void',0.)
    if state!='played' or not finite(actual):
        return ('unresolved',None)
    crossing = threshold_crossing(actual,line,side)
    if crossing == 'PUSH':return ('push',0.)
    return ('win',decimal_odds-1) if crossing == 'WIN' else ('loss',-1.)


def exact_decimal(value):
    """The recorded decimal value, without rounding or inferred source precision."""
    if isinstance(value,bool) or value is None:
        raise ValueError('missing/boolean decimal')
    try:
        result = Decimal(str(value))
    except (InvalidOperation,ValueError):
        raise ValueError('invalid decimal') from None
    if not result.is_finite():raise ValueError('nonfinite decimal')
    return result


def chart_points_exact(components):
    """Exact chart from complete source primitives; legacy chart_points is retained."""
    if any(k not in components for k in CHART_WEIGHTS):return None
    try:values = {k:exact_decimal(components[k]) for k in CHART_WEIGHTS}
    except ValueError:return None
    yards = {'passing_yards','rushing_yards','receiving_yards'}
    if any(v != v.to_integral_value() or (k not in yards and v < 0) for k,v in values.items()):
        return None
    return sum((exact_decimal(CHART_WEIGHTS[k])*values[k] for k in values),Decimal(0))


def threshold_crossing(actual,line,side,*,target=None):
    """Statistical direction only. Eligibility and bookmaker rules are separate."""
    if side not in ('over','under'):raise ValueError('invalid side')
    if target is not None and target not in TARGETS:raise ValueError('unknown target contract')
    L=exact_decimal(line)
    if actual is None:return 'MISSING_ACTUAL'
    y=exact_decimal(actual)
    integer_targets = COUNTS | {'pass_yd','rush_yd','rec_yd','rush_rec_yd','anytime_td'}
    if target in integer_targets and y != y.to_integral_value():
        raise ValueError('fractional official integer statistic')
    if target in COUNTS and y < 0:raise ValueError('negative count')
    if target == 'anytime_td' and y not in (0,1):raise ValueError('invalid TD event')
    if target == 'nick-chart-ppr-v1' and y/Decimal('.02') != (y/Decimal('.02')).to_integral_value():
        raise ValueError('uncertified/off-grid chart actual; require exact components or source grid')
    if y == L:return 'PUSH'
    return 'WIN' if (y>L if side=='over' else y<L) else 'LOSS'


def grade_settlement(actual,line,side,*,target,participation,outcome_state,
                     contract,outcome_contract,decimal_odds=None):
    """Eight explicit states. Unknown contract never becomes a settled wager."""
    result={'state':'UNRESOLVED_CONTRACT','net':None,'reason':None}
    try:
        exact_decimal(line)
        if side not in ('over','under'):raise ValueError('invalid side')
    except ValueError:
        result['reason']='invalid_threshold_or_side';return result
    if target not in TARGETS:
        result['reason']='unknown_target_contract';return result
    required=('statistic','period','overtime','scoring_contract','event_scope')
    if not contract or contract.get('verified') is not True or not outcome_contract:
        result['reason']='verified_settlement_and_outcome_contract_required';return result
    if any(contract.get(k) is None or contract.get(k)!=outcome_contract.get(k) for k in required):
        result['reason']='scope_period_overtime_scoring_or_event_mismatch';return result
    metadata=('contract_id','version','book','jurisdiction','rule_source_id',
              'stat_correction_policy','injury_protection_rule')
    if any(not contract.get(k) for k in metadata):
        result['reason']='versioned_book_jurisdiction_rules_required';return result
    if contract['period']!='full_game' or contract['overtime'] is not True:
        result['reason']='original_full_game_including_overtime_target_required';return result
    if contract['statistic']!=target or contract.get('payout_kind')!='cash_refund':
        result['reason']='statistic_or_payout_contract_unsupported';return result
    if target=='anytime_td' and contract['event_scope']!='rushing_or_receiving_only':
        result['reason']='TD_event_contract_mismatch';return result
    if outcome_state=='pending':result.update(state='PENDING',reason='outcome_not_final');return result
    if outcome_state in ('verified_void','canceled'):
        if contract.get('void_rule')!='cash_refund':
            result['reason']='void_rule_unverified';return result
        result.update(state='VOID',net=Decimal(0),reason='verified_cash_refund');return result
    if participation=='DNP':
        if contract.get('dnp_rule')=='cash_refund':
            result.update(state='VOID',net=Decimal(0),reason='verified_DNP_refund')
        else:result['reason']='DNP_rule_unverified'
        return result
    if participation!='PLAYED':
        result.update(state='UNKNOWN_PARTICIPATION',reason='appearance_not_verified');return result
    if outcome_state!='final':result['reason']='finality_contract_unverified';return result
    if actual is None:result.update(state='MISSING_ACTUAL',reason='played_stat_missing');return result
    state=threshold_crossing(actual,line,side,target=target)
    if state=='PUSH' and contract.get('tie_rule')!='cash_refund':
        result['reason']='tie_rule_unverified';return result
    result.update(state=state,reason=None)
    if state=='PUSH':result['net']=Decimal(0)
    elif decimal_odds is not None:
        odds=exact_decimal(decimal_odds)
        if odds<=1:raise ValueError('invalid decimal odds')
        result['net']=odds-1 if state=='WIN' else Decimal(-1)
    return result


def expected_value(p_win,p_loss,decimal_odds,*,conditioning,p_nonvoid=None):
    """Refund EV, explicitly per placed or per nonvoid unit; no invented void law."""
    win,loss,odds=map(exact_decimal,(p_win,p_loss,decimal_odds))
    if min(win,loss)<0 or win+loss>1 or odds<=1:raise ValueError('invalid EV inputs')
    value=win*(odds-1)-loss
    if conditioning=='unconditional_placed':
        if p_nonvoid is not None:raise ValueError('already unconditional')
        return {'EV_placed':value,'EV_nonvoid':None}
    if conditioning!='conditional_nonvoid':raise ValueError('conditioning required')
    if p_nonvoid is None:return {'EV_nonvoid':value,'EV_placed':None}
    nonvoid=exact_decimal(p_nonvoid)
    if not 0<=nonvoid<=1:raise ValueError('invalid nonvoid probability')
    return {'EV_nonvoid':value,'EV_placed':nonvoid*value}
