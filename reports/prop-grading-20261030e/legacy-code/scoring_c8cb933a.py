"""Original independent scoring implementation. No upstream imports."""
import math
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
    if not finite(line) or not all(finite(x) for x in support):
        raise ValueError('nonfinite support/line')
    if any(not finite(x) or x<0 for x in mass) or not math.isclose(math.fsum(mass),1,rel_tol=0,abs_tol=1e-12):
        raise ValueError('invalid normalized mass')
    return {name: math.fsum(p for y,p in zip(support,mass) if test(y))
            for name,test in [('over',lambda y:y>line),('under',lambda y:y<line),('push',lambda y:y==line)]}

def expected_net(p_win,p_loss,decimal_odds):
    if not all(finite(x) for x in (p_win,p_loss,decimal_odds)) or min(p_win,p_loss)<0 or p_win+p_loss>1+1e-12 or decimal_odds<=1:
        raise ValueError('invalid refund-on-push/void inputs')
    return p_win*(decimal_odds-1)-p_loss

def settle(actual, line, side, decimal_odds, state='played'):
    if side not in ('over','under') or not finite(line) or not finite(decimal_odds) or decimal_odds<=1:
        raise ValueError('invalid offer')
    if state in ('void','canceled'):
        return ('void',0.)
    if state!='played' or not finite(actual):
        return ('unresolved',None)
    if actual==line:
        return ('push',0.)
    win=(actual>line) if side=='over' else (actual<line)
    return ('win',decimal_odds-1) if win else ('loss',-1.)
