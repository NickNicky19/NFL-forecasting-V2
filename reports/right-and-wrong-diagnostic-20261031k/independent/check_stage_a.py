"""Independent exact partition/math/example replay, not a new grading pipeline."""
import argparse,collections,datetime,gzip,hashlib,json,math
from decimal import Decimal,localcontext
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
BUCKETS=('OVER_WIN','OVER_LOSS','UNDER_WIN','UNDER_LOSS')
GB=('LT_NEG_2T','GE_NEG_2T_LT_NEG_T','GE_NEG_T_LT_0','EQ_0','GT_0_LE_T','GT_T_LE_2T','GT_2T');EB=('LE_T','GT_T_LE_2T','GT_2T')
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def canon(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def close(a,b):
    if a is None or b is None:assert a is b,(a,b)
    else:assert math.isclose(float(a),float(b),rel_tol=1e-10,abs_tol=1e-8),(a,b)
def clock(s):
    x=datetime.datetime.fromisoformat(s.replace('Z','+00:00'));assert x.utcoffset()is not None;return x
def qkey(r):return(int(r['week']),r['source_row_index'],r['game_id'],r['player_id'],r['target'])
def stable(r):return(clock(r['decision_time']),int(r['week']),(0,r['source_row_index'])if isinstance(r['source_row_index'],int)else(1,str(r['source_row_index'])),str(r.get('game_id','')),str(r.get('player_id','')))
def gapband(g,t):
    matches=[g< -2*t,-2*t<=g< -t,-t<=g<0,g==0,0<g<=t,t<g<=2*t,g>2*t];assert sum(matches)==1;return GB[matches.index(True)]
def errorband(e,t):return EB[0]if abs(e)<=t else EB[1]if abs(e)<=2*t else EB[2]
def derive(r,t):
    z=dict(bucket=None,error=None,g=None,d=None,gapband=None,errorband=None,exclusion=None,close_wrong=None,large_right=None)
    if not r['admitted']:z['exclusion']='FORECAST_NOT_DECISION_ELIGIBLE';return z
    if r['point']is None or r['line']is None:z['exclusion']='MISSING_POINT_OR_RECORDED_LINE';return z
    p,l=(Decimal(str(r[k]))for k in('point','line'));assert p.is_finite()and l.is_finite();side='over'if p>l else'under'if p<l else None;assert side==r['selected_side'];assert clock(r['decision_time'])<clock(r['kickoff']);z['g']=p-l;z['gapband']=gapband(p-l,t)
    if side is None:z['exclusion']='ABSTAIN';return z
    if r['participation']not in('PLAYED','VERIFIED_PLAYED_POSITIVE_PHYSICAL'):z['exclusion']='UNVERIFIED_PARTICIPATION';return z
    if r['statistical_state']in('VOID','PENDING','MISSING_ACTUAL','UNKNOWN_PARTICIPATION','UNRESOLVED_CONTRACT'):z['exclusion']='NONDECIDED_'+r['statistical_state'];return z
    if r['actual']is None:z['exclusion']='MISSING_ACTUAL';return z
    y=Decimal(str(r['actual']));assert y.is_finite()and y==y.to_integral_value();assert r['target']=='pass_yd'or y>=0;delta=y-l;state='PUSH'if delta==0 else'WIN'if(delta>0)==(side=='over')else'LOSS';assert r['statistical_state']==state;e=p-y;assert e==(p-l)-(y-l);z.update(error=e,d=delta,errorband=errorband(e,t))
    if state=='PUSH':z['exclusion']='NONDECIDED_PUSH';return z
    z.update(bucket=side.upper()+'_'+state,close_wrong=state=='LOSS'and abs(e)<=t,large_right=state=='WIN'and abs(e)>2*t)
    if state=='LOSS':assert abs(e)>abs(p-l)and(e>0)==(side=='over')
    return z
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--public',type=Path,required=True);ap.add_argument('--input',type=Path,required=True);ap.add_argument('--private',type=Path,required=True);ap.add_argument('--receipt',type=Path,required=True);a=ap.parse_args();p=read(a.public/'FROZEN_PROTOCOL.json');run=read(a.public/'RUN_RECEIPT.json');assert sha(a.public/'FROZEN_PROTOCOL.json')==run['protocol_sha256'];assert sha(a.input)==p['source_sha256'];assert sha(a.public/'SCORES.json')==run['score_sha256'];private=a.private/'RIGHT_WRONG_ROWS_AND_EXAMPLES.json.gz';assert sha(private)==run['private_sha256'];source=json.loads(gzip.decompress(a.input.read_bytes()));packet=json.loads(gzip.decompress(private.read_bytes()));roster={tuple(x['recipe']):x for x in p['roster']};old={};expected=collections.defaultdict(dict)
    for r in source['rows']:
        k=tuple(r['recipe'])
        if r.get('population_diagnostic')or k not in roster:continue
        identity=(k,qkey(r));assert identity not in old;old[identity]=r;expected[k][qkey(r)]=r
    assert len(old)==len(packet['rows'])==3024 and len(roster)==36
    byrecipe=collections.defaultdict(list);derived={};caseids={};focal_examples=[]
    with localcontext()as ctx:
        ctx.prec=50
        for r in packet['rows']:
            k=tuple(r['recipe']);key=(k,qkey(r));before=old[key];assert all(r[n]==v for n,v in before.items());t=Decimal(str(p['tolerances'][r['target']]));d=derive(before,t);derived[key]=d;byrecipe[k].append(r);assert r['bucket']==d['bucket']and r['diagnostic_exclusion_reason']==d['exclusion'];assert r['forecast_gap_band']==d['gapband']and r['absolute_error_band']==d['errorband'];close(r['prediction_minus_line'],d['g']);close(r['actual_minus_line'],d['d']);close(r['signed_error'],d['error']);close(r['absolute_error'],abs(d['error'])if d['error']is not None else None);assert r['close_wrong']==d['close_wrong']and r['large_error_right']==d['large_right'];assert r['components']is None and r['component_null_reason']=='DIRECT_MARGINAL_HAS_NO_EXPLICIT_COMPONENT_FORECASTS';assert r['SUPPORTED_PREGAME_INFORMATION_POSSIBLY_MISSED']is None and r['CAUSE_OR_REMEDY_UNTESTED'].startswith('CAUSE_UNRESOLVED');assert r['bookmaker_settlement']=='UNRESOLVED_CONTRACT_PARALLEL_TO_STATISTICAL_GRADE';assert r['retained_numeric_tokens']=={n:str(before[n])if before[n]is not None else None for n in('point','line','actual')}
            if d['error']is not None:assert r['exact_decimal_algebra']==dict(g=str(d['g']),d=str(d['d']),e=str(d['error']))
            cid='K-CASE-'+hashlib.sha256(canon([p['version'],k,qkey(r)])).hexdigest()[:24];assert r['case_id']==cid and cid not in caseids;caseids[cid]=r
        summaries=read(a.public/'METHOD_BUCKET_SUMMARIES.json');scores=read(a.public/'SCORES.json');assert len(summaries)==36 and len(scores)==1584
        for s in summaries:
            k=tuple(s[x]for x in('target','procedure_id','history_regime','product_id'));rr=byrecipe[k];admitted=sum(bool(r['admitted'])for r in rr);assert s['outer_opportunities']==84==len(rr)and s['admitted_forecasts']==admitted and s['unavailable_forecasts']==84-admitted;counts=collections.Counter(derived[k,qkey(r)]['bucket']for r in rr if derived[k,qkey(r)]['bucket']);assert s['bucket_counts']=={b:counts[b]for b in BUCKETS};outside=collections.Counter(derived[k,qkey(r)]['exclusion']or'DECIDED'for r in rr)
            for side in('OVER','UNDER'):outside[side+'_selected']=sum(r['selected_side']==side.lower()and r['admitted']for r in rr)
            assert s['outside_counts']==dict(outside);assert s['close_wrong']==sum(bool(derived[k,qkey(r)]['close_wrong'])for r in rr)and s['large_error_right']==sum(bool(derived[k,qkey(r)]['large_right'])for r in rr);assert s['diagnostic_only']is True and s['default_rank_eligible']is False
        for s in scores:
            k=tuple(s[x]for x in('target','procedure_id','history_regime','product_id'));t=Decimal(str(p['tolerances'][s['target']]));rr=[r for r in byrecipe[k]if derived[k,qkey(r)]['bucket']==s['bucket']and(s['dimension']=='BUCKET'or derived[k,qkey(r)]['gapband'if s['dimension']=='FORECAST_GAP_BAND'else'errorband']==s['band'])];ds=[derived[k,qkey(r)]for r in rr];n=len(rr);assert s['n']==n and s['forecast_rows']==n;errors=[d['error']for d in ds];close(s['mae'],sum(map(abs,errors))/n if n else None);close(s['mse'],sum(e*e for e in errors)/n if n else None);close(s['bias'],sum(errors)/n if n else None);close(s['max_abs_error'],max(map(abs,errors),default=None));close(s['rmse'],(sum(e*e for e in errors)/n).sqrt()if n else None);num=sum(abs(e)<=t for e in errors);strict=sum(abs(e)<t for e in errors);assert s['abs_le_t_numerator']==num and s['abs_lt_t_numerator']==strict and s['precision_denominator']==n;close(s['abs_le_t'],Decimal(num)/n if n else None);close(s['abs_lt_t'],Decimal(strict)/n if n else None);assert s['close_wrong']==sum(bool(d['close_wrong'])for d in ds)and s['large_error_right']==sum(bool(d['large_right'])for d in ds);assert s['unique_games']==len({r['game_id']for r in rr})and s['unique_weeks']==len({r['week']for r in rr});assert s['fallback_counts']==dict(collections.Counter(str(r.get('fallback','UNKNOWN'))for r in rr));known=[r for r in rr if r.get('fallback')is not None];f=sum(r['fallback']!='none'for r in known);assert s['fallback_rows']==(f if len(known)==n else None);assert s['membership_sha256']==hashlib.sha256(canon(sorted(qkey(r)for r in rr))).hexdigest();assert s['diagnostic_only']is True and s['default_rank_eligible']is False and s['outcome_conditioned_membership']is True and s['conditioning']=='SELECTED_SIDE_AND_REALIZED_OUTCOME';assert s['null_reason']==(None if n else'EMPTY_FROZEN_DIAGNOSTIC_BUCKET')
        assert len(packet['examples'])==216;public=read(a.public/'PUBLIC_EXAMPLE_MANIFEST.json');assert len(public)==216
        for e,pe in zip(packet['examples'],public):
            assert{n:v for n,v in e.items()if n!='row'}==pe;k=tuple(e['recipe']);rr=[r for r in byrecipe[k]if derived[k,qkey(r)]['bucket']]
            if e['selection']=='EARLIEST_CHRONOLOGICAL':rr=[r for r in rr if r['bucket']==e['bucket']];rr.sort(key=stable)
            else:rr=[r for r in rr if r['statistical_state']==e['selection'].split('_')[-1]];rr.sort(key=lambda r:(-abs(derived[k,qkey(r)]['error']),stable(r)))
            assert e['row']==(rr[0]if rr else None);assert e['case_id']==(rr[0]['case_id']if rr else None)
            if k[1]in('hgb-direct-history-controls-v1:absolute_error_point','v2-qualified-position-defense-information-wave-v1:D1')and e['selection']=='EARLIEST_CHRONOLOGICAL':focal_examples.append(dict(recipe=list(k),bucket=e['bucket'],case_id=e['case_id']))
    focals=[]
    for s in summaries:
        if(s['target'],s['procedure_id'],s['product_id'])in[('pass_yd','hgb-direct-history-controls-v1:absolute_error_point','absolute_error_point'),('pass_cmp','v2-qualified-position-defense-information-wave-v1:D1','lower_median')]:focals.append({k:s[k]for k in('target','procedure_id','outer_opportunities','admitted_forecasts','bucket_counts','large_error_right','close_wrong')})
    out=dict(state='PASS_INDEPENDENT_K_STAGE_A_EXACT_ROWS_BUCKET_BANDS_METRICS_AND_EXAMPLES',root_protocol_sha256=p['root_protocol_sha256'],stage_protocol_sha256=sha(a.public/'FROZEN_PROTOCOL.json'),score_sha256=sha(a.public/'SCORES.json'),input_sha256=sha(a.input),private_derivative_sha256=sha(private),checker_sha256=sha(Path(__file__)),exact_recipe_target_outputs=36,source_rows_and_scalar_identity_checks=3024,all_diagnostic_metric_views_recomputed=1584,all_frozen_examples_verified=216,focal_summaries=focals,opaque_first_focal_case_witnesses=focal_examples,scope=['Separate Decimal calculation checks retained statistical grades, signed identities, all T/2T bounds and source row immutability; no producer diagnostic functions used.','Bookmaker unresolved contracts remain parallel; no betting settlement/price/ROI inferred.','Actual feature/model/context provenance receives a separate source audit; components remain absent for direct marginals.','These are posterior descriptive groups, not earlier-executable cohorts, causal tests, repairs or new ranking contenders.'],new_models=0,new_inference=0,new_NFL_forecasts=0,new_NFL_observations=0,new_private_exports=0)
    with a.receipt.open('x')as f:json.dump(out,f,indent=2);f.write('\n')
    print(json.dumps(dict(state=out['state'],views=1584,examples=216,focals=focals)))
if __name__=='__main__':main()
