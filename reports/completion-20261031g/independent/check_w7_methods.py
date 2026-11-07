"""Independent verification of new saved-method directions/probabilities/score views."""
import argparse
from collections import Counter,defaultdict
from decimal import Decimal
import gzip,hashlib,importlib.util,json,math
from pathlib import Path
import numpy as np

spec=importlib.util.spec_from_file_location('independent_numeric',Path(__file__).resolve().parents[2]/'championship-20261030f/independent/check_numerical_pairs.py');ind=importlib.util.module_from_spec(spec);spec.loader.exec_module(ind)
sha,canon=ind.sha,ind.canonical
def read(p):return json.loads(p.read_bytes())
def zipped(p):return json.loads(gzip.decompress(p.read_bytes()))
def close(a,b):
    if a is None or b is None:assert a is b
    elif isinstance(a,list):
        assert len(a)==len(b)
        for x,y in zip(a,b):close(x,y)
    elif isinstance(a,str)or isinstance(b,str):assert a==b
    else:assert math.isclose(a,b,abs_tol=2e-10,rel_tol=2e-10),(a,b)
def member(row,c):
    if c=='ALL':return True
    if c=='ORIGINAL_SELECTED':return row['original_side']in('over','under')
    if c=='ORIGINAL_ABSTAINED':return row['original_side']not in('over','under')
    if c.startswith('position:'):return row['position']==c.split(':',1)[1]
    if c.startswith('source:'):return row['line_from']==c.split(':',1)[1]
    if c.startswith('original_top_'):return row['top_'+c.rsplit('_',1)[1]]
    if c=='cohort_unknown':return not row['source_cohorts']
    assert c.startswith('reconstructed:');return c.split(':',1)[1]in row['source_cohorts']
def cdf(params,k):
    kind=params['kind']
    if kind=='zero':return float(k>=0)
    if kind=='bernoulli':return 0. if k<0 else 1-params['p']if k<1 else 1.
    if kind=='geometric':return 0. if k<0 else 1-params['q']**(k+1)
    if kind=='signed':
        q=params['q'];d=k-params['center'];return q**(-d)/(1+q)if d<0 else 1-q**(d+1)/(1+q)
    assert kind=='poisson';mu=params['mean']
    if k<0:return 0.
    term=math.exp(-mu);terms=[term]
    for j in range(1,k+1):term*=mu/j;terms.append(term)
    return min(1.,math.fsum(terms))
def probabilities(params,line):
    line=Decimal(str(line));lo=math.floor(line);integer=line==lo;f=cdf(params,lo);under=cdf(params,lo-1)if integer else f
    return dict(over=1-f,under=under,push=f-under if integer else 0.)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',type=Path,required=True);ap.add_argument('--private-root',type=Path,required=True);ap.add_argument('--wave-private',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();root=a.repo_root;public=root/'reports/completion-20261031g/roster/w7-method-comparison-v2';p=read(public/'FROZEN_PROTOCOL.json');run=read(public/'RUN_RECEIPT.json');freeze=read(public/'SELECTION_FREEZE_RECEIPT.json');assert sha(public/'FROZEN_PROTOCOL.json')==run['protocol_sha256'];assert sha(public/'SCORES.json')==run['main_score_sha256']
    f=a.wave_private/'FROZEN_SELECTIONS_AND_K.json.gz';assert sha(f)==freeze['sha256'];frozen=zipped(f);plans=frozen['plans'];controls=frozen['controls'];graded=zipped(a.wave_private/'GRADED_METHOD_ROWS.json.gz');grades=graded['graded'];assert set(grades)==set(plans)|set(controls)
    admission=zipped(a.private_root/'completion-20261031g-threshold-audit-v2/ADMISSIBILITY_MASK.json.gz')['rows'];assert sha(a.private_root/'completion-20261031g-threshold-audit-v2/ADMISSIBILITY_MASK.json.gz')==p['mask_sha256'];wanted={(m['source_member'],m['source_row_index_in_member']):m for m in admission if m['p1_state']=='ELIGIBLE_NEW_RETROSPECTIVE_SAVED_VECTOR'};points={};laws={}
    import csv
    for b in p['raw_sources']['members']:
        if not any(member==b['member']for member,index in wanted):continue
        file=a.private_root/b['member'];assert sha(file)==b['sha256'];it=ind.packets(file)if b['kind']=='packet'else csv.DictReader(gzip.open(file,'rt'))
        for i,row in enumerate(it):
            m=wanted.get((b['member'],i))
            if m is None:continue
            recipe=(m['target'],m['procedure_id'],m['history_regime'],m['product_id']);idx=m['source_row_index'];points[recipe,idx]=float(row['prediction'])
            if m['p2_state']=='ELIGIBLE_COMPLETE_SAVED_PARAMETRIC_LAW':
                law=row['law_reference'];law=json.loads(law)if isinstance(law,str)else law;params=law.get('fallback_prior',law.get('parametric'));lk=(m['target'],m['procedure_id'],m['history_regime'],'saved_parametric_law')
                if(lk,idx)in laws:assert laws[lk,idx]==params
                laws[lk,idx]=params
    joined_file=a.private_root/'championship-20261030f-full-pool-v1/JOINED_ROWS.json.gz';assert sha(joined_file)==p['joined_sha256'];joined=zipped(joined_file)['rows'];jb={r['source_row_index']:r for r in joined}
    choices={tuple(x['recipe']):tuple(x['chosen_recipe'])for x in frozen['composite_choices']};grade_count=0;win=loss=push=0;proper={}
    for tag,plan in plans.items():
        recipe=tuple(plan['recipe']);assert tag==hashlib.sha256(canon(recipe)).hexdigest()[:18];source_recipe=choices.get(recipe,recipe);expected_ids={i for r,i in points if r==source_recipe}if plan['rule']=='P1'else{i for r,i in laws if r==recipe}
        for z,row in zip(plan['rows'],grades[tag]):
            idx=z['source_row_index'];o=jb[idx];admitted=idx in expected_ids;assert z['admitted']==row['admitted']==admitted
            point=points[source_recipe,idx]if admitted and plan['rule']=='P1'else None;pp=probabilities(laws[recipe,idx],o['line'])if admitted and plan['rule']=='P2'else None
            close(z['point'],point);close(row['ranking_point'],point)
            if pp:
                for side in pp:close(z['probabilities'][side],pp[side]);close(row['probabilities'][side],pp[side])
                assert math.isclose(sum(pp.values()),1,abs_tol=1e-12)
                side='over'if pp['over']>pp['under']else'under'if pp['under']>pp['over']else None;rank=max(pp['over'],pp['under'])
            elif point is not None:
                difference=Decimal(str(point))-Decimal(str(o['line']));side='over'if difference>0 else'under'if difference<0 else None;rank=float(abs(difference))
            else:side=rank=None
            assert z['selected_side']==row['selected_side']==side;close(z['rank'],rank)
            assert(row['game_id'],row['player_id'],row['target'],row['actual'],row['participation'])==(o['game_id'],o['player_id'],o['target'],o['actual'],o['participation'])
            actual=o['actual'];line=Decimal(str(o['line']));state='ABSTAIN'if side is None else'UNKNOWN_PARTICIPATION'if o['participation']!='VERIFIED_PLAYED_POSITIVE_PHYSICAL'else'MISSING_ACTUAL'if actual is None else'PUSH'if Decimal(str(actual))==line else'WIN'if(Decimal(str(actual))>line if side=='over'else Decimal(str(actual))<line)else'LOSS';assert row['statistical_state']==state
            win+=state=='WIN';loss+=state=='LOSS';push+=state=='PUSH';grade_count+=1
            if pp is not None and actual is not None and o['participation']=='VERIFIED_PLAYED_POSITIVE_PHYSICAL':
                cls='over'if Decimal(str(actual))>line else'under'if Decimal(str(actual))<line else'push';b=.5*math.fsum((pp[s]-int(cls==s))**2 for s in pp);ll=-math.log(pp[cls])if pp[cls]>0 else'Infinity';proper[tag,idx]=(b,ll,cls)
    assert len(proper)==len(graded['probability_rows'])==1459
    for row in graded['probability_rows']:
        b,ll,cls=proper[row['method_id'],row['source_row_index']];close(row['half3class_brier'],b);close(row['categorical_log_loss'],ll);assert row['actual_class']==cls
    for tag,control in controls.items():
        admitted=set(control['admitted_ids'])
        for row in grades[tag]:
            o=jb[row['source_row_index']];idx=o['source_row_index'];assert row['admitted']==(idx in admitted);which=control['control'];point=o['raw_prediction']if which=='SAVED_RAW_PROJECTION_DIRECTION_RETAINED_PRECISION'else o['prediction']
            side=None if idx not in admitted else o['original_side']if which=='original'else'over'if which=='alwaysOver'else'under'if which=='alwaysUnder'else'over'if point>o['line']else'under'if point<o['line']else None
            assert row['selected_side']==side
            state='ABSTAIN'if side is None else'UNKNOWN_PARTICIPATION'if o['participation']!='VERIFIED_PLAYED_POSITIVE_PHYSICAL'else'PUSH'if o['actual']==o['line']else'WIN'if(o['actual']>o['line']if side=='over'else o['actual']<o['line'])else'LOSS';assert row['statistical_state']==state;grade_count+=1
    kmap={}
    for k in frozen['Kplans']:
        pool=[r for r in plans[k['method_id']]['rows']if r['selected_side']and(k['rank_scope']=='Combined'or r['selected_side']==k['rank_scope'])];ordered=sorted(pool,key=lambda r:(-r['rank'],r['source_row_index']));assert k['eligible_pool_n']==len(pool)and k['source_indices']==[r['source_row_index']for r in ordered[:k['K']]];kmap[k['method_id'],k['K'],k['rank_scope']]=k
    assert len(kmap)==5697
    sources=[dict(path=str(public/'SCORES.json'),sha256=run['main_score_sha256'])]+[dict(path=str(root/b['path']),sha256=b['sha256'])for b in read(public/'SUPPLEMENTAL_SCORE_ARTIFACTS.json')];allids=set();triplets=defaultdict(dict);selection_views=numeric_views=0;empty=0
    for source in sources:
        file=Path(source['path']);assert sha(file)==source['sha256']
        for r in read(file):
            assert r['record_id']not in allids;allids.add(r['record_id'])
            if r['record_kind']!='prop_selection_evaluation':
                numeric_views+=1;tag=r['record_id'].removeprefix('METHOD-NUM-').removeprefix('METHOD-PROB-');rr=[v for v in grades[tag]if v['admitted']and v['actual']is not None and v['participation']=='VERIFIED_PLAYED_POSITIVE_PHYSICAL'];assert r['n']==len(rr)
                if r['record_kind']=='prop_threshold_probability_evaluation':
                    vals=[proper[tag,v['source_row_index']]for v in rr];close(r['brier'],math.fsum(v[0]for v in vals)/len(vals)if vals else None);close(r['log_loss'],'Infinity'if any(v[1]=='Infinity'for v in vals)else math.fsum(v[1]for v in vals)/len(vals)if vals else None)
                else:
                    pp=[v['ranking_point']for v in rr];yy=[v['actual']for v in rr];errors=[x-y for x,y in zip(pp,yy)];n=len(errors)
                    for name,value in(dict(mae=math.fsum(map(abs,errors))/n,mse=math.fsum(x*x for x in errors)/n,bias=math.fsum(errors)/n).items()if n else [('mae',None),('mse',None),('bias',None)]):close(r[name],value)
                continue
            selection_views+=1;pool=grades[r['method_id']]
            if r['K']is None:pool=[v for v in pool if member(v,r['cohort_id'])];selected=[v for v in pool if v['selected_side']]
            else:
                kp=kmap[r['method_id'],r['K'],r['rank_scope']];selected=[v for v in pool if v['source_row_index']in set(kp['source_indices'])]
            rr=[v for v in selected if r['side']=='Combined'or v['selected_side']==r['side']];c=Counter(v['statistical_state']for v in rr);m=r['selection_metrics'];n=c['WIN']+c['LOSS'];assert(r['forecast_rows'],r['n'],m['WIN'],m['LOSS'],m['PUSH'])==(len(rr),n,c['WIN'],c['LOSS'],c['PUSH']);assert m['status_counts']=={state:c[state]for state in m['status_counts']};close(m['hit_rate'],c['WIN']/n if n else None);close(r['selection_loss_rate'],c['LOSS']/n if n else None);empty+=not n
            assert r['query_membership_sha256']==hashlib.sha256(canon(sorted(v['source_row_index']for v in rr))).hexdigest();assert m['admitted_forecast_opportunities']==sum(v['admitted']for v in pool);assert m['unavailable_forecast_opportunities']==sum(not v['admitted']for v in pool)
            dims=(r['method_id'],r['cohort_id'],r['K'],r['rank_scope']);assert r['side']not in triplets[dims];triplets[dims][r['side']]=[len(rr),n]+[c[state]for state in('WIN','LOSS','PUSH','UNKNOWN_PARTICIPATION','MISSING_ACTUAL','VOID','PENDING')]
    for group in triplets.values():
        assert set(group)=={'over','under','Combined'}
        assert group['Combined']==[x+y for x,y in zip(group['over'],group['under'])]
    assert len(allids)==73362 and numeric_views==633 and selection_views==72729 and win and loss
    report=dict(state='PASS_INDEPENDENT_W7_METHOD_POINTS_LAWS_GRADES_K_AND_ALL_SIDE_COUNTS',protocol_sha256=run['protocol_sha256'],main_scores_sha256=run['main_score_sha256'],source_offer_rows=462,method_output_products=len(plans),matched_control_masks=len(controls),grade_views_checked=grade_count,proper_probability_rows_checked=len(proper),point_probability_product_views=numeric_views,selection_score_views=selection_views,exact_side_triplets=len(triplets),total_score_views=len(allids),empty_or_unknown_views_with_null_accuracy=empty,frozen_K_lists=len(kmap),real_method_WIN_views=win,real_method_LOSS_views=loss,real_statistical_PUSH_views=push,new_fits=0,new_inference=0,new_forecasts=0,new_grades=0,new_NFL_observations=0,limits=['Output products and repeated score views are not distinct independent methods or NFL games.','P2 half-multiclass scores condition on modeled appearance; bookmaker nonvoid/price/ROI remain unestablished.','Unavailable rows and admitted rule-abstentions need separate denominator metadata; generic total nonselection includes both.','Matched-control K views are a separately tracked follow-up, not included among the5697 method K lists.'])
    with a.output.open('x')as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps({k:report[k]for k in('state','total_score_views','proper_probability_rows_checked','exact_side_triplets','real_method_WIN_views','real_method_LOSS_views','real_statistical_PUSH_views')}))


if __name__=='__main__':main()
