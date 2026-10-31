"""Descriptive retained-prediction diagnostics, using the existing threshold grader.

Selected-side/outcome groups are posterior explanatory views, never a new
selection rule, causal attribution, calibrated probability or forecast repair.
"""
from __future__ import annotations
import collections,hashlib,math
from datetime import datetime
from decimal import Decimal
from . import scoring

BUCKETS=('OVER_WIN','OVER_LOSS','UNDER_WIN','UNDER_LOSS')
VALID_PARTICIPATION={'PLAYED','VERIFIED_PLAYED_POSITIVE_PHYSICAL'}

def clock(value):
    dt=datetime.fromisoformat(value.replace('Z','+00:00'))
    if dt.utcoffset()is None:raise ValueError('aware diagnostic clock required')
    return dt

def band(value,tolerance):
    if not math.isfinite(value)or not math.isfinite(tolerance)or tolerance<=0:raise ValueError('finite diagnostic value and positive tolerance required')
    value=abs(value)
    return 'LE_T'if value<=tolerance else'GT_T_LE_2T'if value<=2*tolerance else'GT_2T'

def gap_band(value,tolerance):
    if not math.isfinite(value)or not math.isfinite(tolerance)or tolerance<=0:raise ValueError('finite signed gap and positive tolerance required')
    if value < -2*tolerance:return 'LT_NEG_2T'
    if value < -tolerance:return 'GE_NEG_2T_LT_NEG_T'
    if value < 0:return 'GE_NEG_T_LT_0'
    if value == 0:return 'EQ_0'
    if value <= tolerance:return 'GT_0_LE_T'
    if value <= 2*tolerance:return 'GT_T_LE_2T'
    return 'GT_2T'

def stable_key(row):
    index=row['source_row_index'];index_key=(0,index)if isinstance(index,int)else(1,str(index))
    return(clock(row['decision_time']),int(row['week']),index_key,str(row.get('game_id','')),str(row.get('player_id','')))

def diagnose(row,*,tolerance,rule='P1',lineage=None):
    out=dict(row)
    out.update(bucket=None,signed_error=None,absolute_error=None,prediction_minus_line=None,actual_minus_line=None,forecast_gap_band=None,absolute_error_band=None,close_wrong=None,large_error_right=None)
    facts=dict(lineage or {})
    if facts.get('components')is not None and not facts.get('component_forecast_qualified'):
        raise ValueError('component forecasts require explicit compatible frozen evidence')
    out['feature_lineage']=facts.get('feature_lineage')
    out['feature_lineage_null_reason']=None if facts.get('feature_lineage')is not None else'ACTUAL_CONSUMED_FEATURE_VALUES_NOT_RETAINED_IN_JOINED_DIAGNOSTIC'
    out['source_age']=facts.get('source_age')
    out['source_age_null_reason']=None if facts.get('source_age')is not None else'NO_QUALIFIED_CONSUMED_FEATURE_SOURCE_CLOCK_IN_JOINED_RECORD'
    out['pregame_role']=facts.get('pregame_role')
    out['pregame_role_null_reason']=None if facts.get('pregame_role')is not None else'ROLE_NOT_AUTHENTICATED_BEYOND_RETAINED_POSITION_AND_POPULATION'
    out['components']=facts.get('components')
    out['component_null_reason']=facts.get('component_null_reason','DIRECT_PROCEDURE_HAS_NO_EXPLICIT_FORECAST_COMPONENTS')if facts.get('components')is None else None
    if not row.get('admitted'):
        out['diagnostic_exclusion_reason']='FORECAST_NOT_DECISION_ELIGIBLE';return out
    if row.get('point')is None or row.get('line')is None:
        out['diagnostic_exclusion_reason']='MISSING_POINT_OR_RECORDED_LINE';return out
    point,line=float(row['point']),float(row['line'])
    if not math.isfinite(point)or not math.isfinite(line):raise ValueError('nonfinite retained forecast/line')
    selected=row.get('selected_side');state=row.get('statistical_state')
    if rule=='P1':
        expected='over'if point>line else'under'if point<line else None
        if selected!=expected:raise ValueError('saved P1direction disagrees with original unrounded point')
    elif rule!='ORIGINAL_RECORDED_SELECTION':raise ValueError('unsupported diagnostic rule; no probability inference')
    if row.get('decision_time')and row.get('kickoff')and clock(row['decision_time'])>=clock(row['kickoff']):raise ValueError('admitted decision is not pregame')
    dp,dl=Decimal(str(row['point'])),Decimal(str(row['line']))
    out['prediction_minus_line']=float(dp-dl);out['forecast_gap_band']=gap_band(float(dp-dl),tolerance)
    if selected not in('over','under'):
        out['diagnostic_exclusion_reason']='ABSTAIN';return out
    if row.get('participation')not in VALID_PARTICIPATION:
        out['diagnostic_exclusion_reason']='UNVERIFIED_PARTICIPATION';return out
    if state in('VOID','PENDING','MISSING_ACTUAL','UNKNOWN_PARTICIPATION','UNRESOLVED_CONTRACT'):
        out['diagnostic_exclusion_reason']='NONDECIDED_'+str(state);return out
    if row.get('actual')is None:
        out['diagnostic_exclusion_reason']='MISSING_ACTUAL';return out
    actual=float(row['actual'])
    if not math.isfinite(actual):raise ValueError('nonfinite actual is not zero')
    expected=scoring.threshold_crossing(actual,line,selected,target=row['target'])
    if state!=expected:raise ValueError('retained statistical state differs from existing exact grader')
    da=Decimal(str(row['actual']));error=dp-da
    out.update(signed_error=float(error),absolute_error=float(abs(error)),actual_minus_line=float(da-dl),absolute_error_band=band(float(error),tolerance),exact_decimal_algebra={'g':str(dp-dl),'d':str(da-dl),'e':str(error)})
    if state not in('WIN','LOSS'):
        out['diagnostic_exclusion_reason']='NONDECIDED_'+str(state);return out
    out.update(bucket=selected.upper()+'_'+state,diagnostic_exclusion_reason=None,close_wrong=state=='LOSS'and abs(error)<=Decimal(str(tolerance)),large_error_right=state=='WIN'and abs(error)>2*Decimal(str(tolerance)))
    return out

def representatives(rows):
    eligible=[r for r in rows if r.get('bucket')in BUCKETS];out=[]
    for bucket in BUCKETS:
        rr=sorted([r for r in eligible if r['bucket']==bucket],key=stable_key)
        out.append({'selection':'EARLIEST_CHRONOLOGICAL','bucket':bucket,'row':rr[0]if rr else None,'null_reason':None if rr else'NO_RETAINED_CASE_IN_FROZEN_BUCKET'})
    for status in('WIN','LOSS'):
        rr=sorted([r for r in eligible if r['statistical_state']==status],key=lambda r:(-r['absolute_error'],stable_key(r)))
        out.append({'selection':'LARGEST_ABSOLUTE_ERROR_'+status,'bucket':rr[0]['bucket']if rr else None,'row':rr[0]if rr else None,'null_reason':None if rr else'NO_RETAINED_DECIDED_CASE'})
    return out

def aggregate(rows,*,tolerance):
    """Four buckets plus fixed gap/error bands; no duplicate whole-panel score."""
    result=[]
    for bucket in BUCKETS:
        rr=[r for r in rows if r.get('bucket')==bucket]
        for dimension,values in [('BUCKET',['ALL']),('FORECAST_GAP_BAND',['LT_NEG_2T','GE_NEG_2T_LT_NEG_T','GE_NEG_T_LT_0','EQ_0','GT_0_LE_T','GT_T_LE_2T','GT_2T']),('ABSOLUTE_ERROR_BAND',['LE_T','GT_T_LE_2T','GT_2T'])]:
            for value in values:
                selected=rr if dimension=='BUCKET'else[r for r in rr if r[dimension.lower()]==value]
                n=len(selected);num=sum(r['absolute_error']<=tolerance for r in selected);strict=sum(r['absolute_error']<tolerance for r in selected)
                result.append({'bucket':bucket,'dimension':dimension,'band':value,'n':n,'mae':math.fsum(r['absolute_error']for r in selected)/n if n else None,'mse':math.fsum(r['signed_error']**2 for r in selected)/n if n else None,'bias':math.fsum(r['signed_error']for r in selected)/n if n else None,'max_abs_error':max((r['absolute_error']for r in selected),default=None),'precision_tolerance':tolerance,'abs_le_t_numerator':num,'abs_lt_t_numerator':strict,'precision_denominator':n,'abs_le_t':num/n if n else None,'abs_lt_t':strict/n if n else None,'close_wrong':sum(r['close_wrong']for r in selected),'large_error_right':sum(r['large_error_right']for r in selected),'unique_games':len({r['game_id']for r in selected}),'unique_weeks':len({r['week']for r in selected}),'fallback_counts':dict(collections.Counter(str(r.get('fallback','UNKNOWN'))for r in selected)),'null_reason':None if n else'EMPTY_FROZEN_DIAGNOSTIC_BUCKET'})
    return result
