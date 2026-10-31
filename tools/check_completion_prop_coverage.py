"""Check multi-source selected-side partitions and source-version projection.

This checks saved aggregates; it never scores a new NFL outcome.
"""
import collections
import json
import math
from tools.check_analysis_index_coverage import read_bound

SIDES=('over','under','Combined')
DIMS=('evaluation_panel_id','procedure_id','history_regime','product_id','strategy','decision_rule','target','cohort_id','K','rank_scope','time_panel_id','horizon_id','fallback_view')

def require(ok,reason):
    if not ok:raise ValueError(reason)

def rate(value,n,d):
    require(value is None if not d else isinstance(value,(float,int))and math.isfinite(value)and math.isclose(value,n/d,rel_tol=0,abs_tol=1e-12),'Incorrect weighted rate or null denominator')

def check_rows(rows):
    groups=collections.defaultdict(dict);proper=0;selected=0
    for r in rows:
        if r['record_kind']=='prop_threshold_probability_evaluation':
            require(r['probability_conditioning']=='MODELED_APPEARANCE'and r['probability_score_contract']=='HALF_MULTICLASS_BRIER_OVER_UNDER_PUSH_V1','Unsupported probability contract')
            require(r.get('mae')is None and r.get('mse')is None,'Probability product gained native MAE')
            require(r.get('brier')is None if not r['n']else 0<=r['brier']<=1,'Invalid probability support or Brier')
            proper+=1;continue
        if r['record_kind']!='prop_selection_evaluation':continue
        side=r['side'];require(side in SIDES,'Selected side missing');key=tuple(r.get(k)for k in DIMS)
        require(side not in groups[key],'Duplicate selected-side view');groups[key][side]=r
        m=r['selection_metrics'];s=m['status_counts'];d=m['denominators'];n=r['forecast_rows'];w=s['WIN'];loss=s['LOSS'];push=s['PUSH']
        require(all(type(v)is int and v>=0 for v in s.values()),'Invalid status counts')
        require(s.get('ABSTAIN',0)==0 and sum(s.values())==n==d['outer_rows'],'Selected status partition failed')
        require(m['WIN']==w and m['LOSS']==loss and m['PUSH']==push and r['n']==d['decided']==w+loss,'Decided denominator failed')
        require(d['supported_threshold_outcomes']==w+loss+push and d['unresolved']==n-w-loss-push,'Support denominator failed')
        rate(m['hit_rate'],w,w+loss);rate(r['selection_loss_rate'],loss,w+loss)
        require(sum(m['bookmaker_settlement_status_counts'].values())==n,'Bookmaker-state count failed')
        if r['settlement_status']=='UNRESOLVED_CONTRACT':require(all(m['returns'][k]is None for k in('ROI','net','drawdown')),'Unknown settlement gained returns')
        selected+=1
    for g in groups.values():
        require(set(g)==set(SIDES),'Missing selected Over/Under/Combined')
        a,b,c=(g[s]for s in SIDES)
        for f in('n','forecast_rows'):require(c[f]==a[f]+b[f],'Combined count must equal Over plus Under')
        for f in('status_counts','denominators','bookmaker_settlement_status_counts'):
            aa,bb,cc=(r['selection_metrics'][f]for r in(a,b,c));keys=set(aa)|set(bb)|set(cc)
            require(all(cc.get(k,0)==aa.get(k,0)+bb.get(k,0)for k in keys),'Combined status counts must equal Over plus Under')
    return dict(selection_views=selected,groups=len(groups),proper_views=proper)

def validate(manifest):
    require(manifest['scope']=='completion-multi-source-v1','Wrong completion scope');counts=collections.Counter();sources=set()
    for b in manifest['source_scores']:
        require(b['path']not in sources,'Repeated canonical source');sources.add(b['path']);rows=json.loads(read_bound(b));require(len(rows)==b['rows'],'Source view count changed');counts.update(check_rows(rows))
    projection=json.loads(read_bound(manifest['complete_law_projection']))
    require(len(projection['source_rules'])==3,'Fixed and rolling panels must remain separate')
    for rule in projection['source_rules']:
        pred=rule['exclude_parent_only_when'];require(pred['signature_fields']==['target','procedure_id','history_regime'],'Wrong law replacement dimensions')
        require('P2'in pred['predicate']and 'prop_threshold_probability_evaluation'in pred['predicate'],'Replacement must be scoped to law/P2')
        for b in rule['parent_sources']+rule['complete_leaf_sources']:read_bound(b)
    for b in manifest['cohort_supersession_maps']:
        obj=json.loads(read_bound(b));require(bool(obj),'Empty cohort correction mapping')
    require(manifest['unsupported_actual_offer_targets']==['nick-chart-ppr-v1','anytime_td'],'Unsupported offered contracts silently changed')
    return dict(state='PASS_PROP_SCOREBOARD_COMPLETION_COVERAGE',source_arrays=len(sources),**counts,new_grades=0,NFL_outcome_rows_read=0)
