"""Decision eligibility and selection rules using the single scoring engine."""
from datetime import datetime, timedelta
from .scoring import exact_decimal, expected_value

IDENTITY=('event_id','player_id','target','period','scoring_contract')


def clock(value):
    if not isinstance(value,str):raise ValueError('timestamp required')
    result=datetime.fromisoformat(value.replace('Z','+00:00'))
    if result.tzinfo is None:raise ValueError('aware timestamp required')
    return result


def timing_violations(forecast,offer,decision,*,max_quote_age_seconds=900):
    """Authentic offer admission; original line-only diagnostics use another tier."""
    t=clock(decision);reasons=[]
    if max_quote_age_seconds<0:raise ValueError('negative quote age')
    for key in IDENTITY:
        if forecast.get(key) is None or forecast.get(key)!=offer.get(key):reasons.append('IDENTITY_'+key)
    kickoff=offer.get('kickoff')
    if kickoff is None:reasons.append('MISSING_KICKOFF')
    else:
        start=clock(kickoff)
        if t>=start:reasons.append('DECISION_NOT_PREGAME')
        horizon=offer.get('horizon_seconds',0)
        if isinstance(horizon,bool) or not isinstance(horizon,(int,float)) or horizon<0:
            raise ValueError('invalid registered horizon')
        if t>start-timedelta(seconds=horizon):reasons.append('MISSED_HORIZON')
    for key in ('feature_cutoff','training_label_cutoff','fallback_cutoff','calibration_cutoff'):
        if forecast.get(key) is None:reasons.append('MISSING_'+key)
        elif clock(forecast[key])>t:reasons.append('FUTURE_'+key)
    if forecast.get('evidence')!='RETROSPECTIVE_RULE_REPLAY':
        for key in ('issued_at','persisted_at'):
            if forecast.get(key) is None:reasons.append('MISSING_'+key)
            elif clock(forecast[key])>t:reasons.append('LATE_'+key)
        if forecast.get('issued_at'):
            issued=clock(forecast['issued_at'])
            if any(forecast.get(k) and clock(forecast[k])>issued for k in
                   ('feature_cutoff','training_label_cutoff','fallback_cutoff','calibration_cutoff')):
                reasons.append('INFORMATION_AFTER_ISSUANCE')
            if forecast.get('persisted_at') and clock(forecast['persisted_at'])<issued:
                reasons.append('PERSISTENCE_BEFORE_ISSUANCE')
    elif not forecast.get('information_tier'):reasons.append('RECONSTRUCTION_TIER_REQUIRED')
    for key in ('source_update','received_at'):
        if offer.get(key) is None:reasons.append('MISSING_QUOTE_'+key)
        elif clock(offer[key])>t:reasons.append('FUTURE_QUOTE_'+key)
    if offer.get('source_update') and offer.get('received_at'):
        update,received=clock(offer['source_update']),clock(offer['received_at'])
        if update>received:reasons.append('QUOTE_UPDATE_AFTER_RECEIPT')
        if (t-update).total_seconds()>max_quote_age_seconds:reasons.append('STALE_QUOTE')
    if offer.get('status')!='OPEN':reasons.append('QUOTE_NOT_OPEN')
    return sorted(set(reasons))


def choose_side(rule,*,point=None,line=None,probabilities=None,prices=None):
    if rule=='P1':
        if point is None or line is None:return None
        p,L=exact_decimal(point),exact_decimal(line)
        return 'over' if p>L else 'under' if p<L else None
    if rule not in ('P2','P3'):raise ValueError('unknown selection rule')
    if probabilities is None:return None
    p={k:exact_decimal(probabilities[k]) for k in ('over','under','push')}
    if min(p.values())<0 or abs(sum(p.values())-1)>exact_decimal('0.000000000001'):
        raise ValueError('incoherent conditional nonvoid law')
    if probabilities.get('conditioning')!='conditional_nonvoid':raise ValueError('conditioning required')
    if rule=='P2':return 'over' if p['over']>p['under'] else 'under' if p['under']>p['over'] else None
    candidates=[]
    for side,other in [('over','under'),('under','over')]:
        price=(prices or {}).get(side)
        if price is None:continue
        ev=expected_value(p[side],p[other],price,conditioning='conditional_nonvoid')['EV_nonvoid']
        if ev>0:candidates.append((ev,side))
    return sorted(candidates,key=lambda x:(-x[0],x[1]))[0][1] if candidates else None


def fixed_top_k(candidates,k,*,freeze_time,side=None,ranking_kind='probability',universe_first_kickoff=None):
    """A fixed weekly list. Caller supplies only earlier-defined ranking scores."""
    if k not in (6,10,20):raise ValueError('unregistered K')
    if side not in (None,'over','under'):raise ValueError('invalid side pool')
    t=clock(freeze_time)
    if universe_first_kickoff is not None and t>=clock(universe_first_kickoff):
        raise ValueError('freeze after declared universe first kickoff')
    if any(clock(r['kickoff'])<=t for r in candidates):raise ValueError('weekly freeze after kickoff')
    if any(clock(r['available_at'])>t or clock(r['decision_time'])>t for r in candidates):
        raise ValueError('candidate unavailable at weekly freeze')
    if len({r['selection_unit_id']for r in candidates})!=len(candidates):
        raise ValueError('duplicate selection unit')
    if len({(r['season'],r['week'])for r in candidates})>1:raise ValueError('one weekly universe required')
    if ranking_kind=='point_gap' and len({r['target']for r in candidates})>1:
        raise ValueError('raw point gaps cannot rank across categories')
    if ranking_kind not in ('point_gap','probability','EV'):raise ValueError('ranking contract required')
    rows=[r for r in candidates if side is None or r['side']==side]
    return sorted(rows,key=lambda r:(-exact_decimal(r['rank_score']),r['selection_unit_id']))[:k]


def rolling_top_k(batches,k,*,side=None,ranking_kind='probability'):
    """Chronological greedy allocation: take available picks up to remaining K."""
    if k not in (6,10,20):raise ValueError('unregistered K')
    selected=[];seen=set();previous=None;week=None;targets=set()
    for batch in batches:
        t=clock(batch['decision_time'])
        if previous is not None and t<=previous:raise ValueError('unordered decision batches')
        previous=t;rows=batch['candidates']
        targets.update(r['target']for r in rows)
        if ranking_kind=='point_gap' and len(targets)>1:
            raise ValueError('point-gap rolling K is per category')
        for row in rows:
            this_week=(row['season'],row['week'])
            if week is None:week=this_week
            if this_week!=week:raise ValueError('one rolling week required')
        if any(r['selection_unit_id']in seen for r in rows):raise ValueError('duplicate across batches')
        seen.update(r['selection_unit_id']for r in rows)
        ordered=fixed_top_k(rows,20,freeze_time=batch['decision_time'],side=side,ranking_kind=ranking_kind)
        selected.extend(ordered[:max(0,k-len(selected))])
    return selected
