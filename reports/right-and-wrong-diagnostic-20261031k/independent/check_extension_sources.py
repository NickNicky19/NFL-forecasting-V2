"""Independently bind K extension rows to retained grades/plans, no rescoring."""
import argparse,collections,gzip,hashlib,json,math
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];BASE=HERE.parent
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def canon(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--private-root',type=Path,required=True);a=ap.parse_args();pre=read(BASE/'stage-b-preflight-v2/PREFLIGHT_RECEIPT.json');roster=read(BASE/'stage-b-preflight-v2/EXACT_EXTENSION_ROSTER.json');assert sha(BASE/'stage-b-preflight-v2/EXACT_EXTENSION_ROSTER.json')==pre['roster_sha256'];root=read(BASE/'FROZEN_PROTOCOL.json');p=read(BASE/'stage-b-v1/FROZEN_PROTOCOL.json');source=a.private_root/'right-and-wrong-diagnostic-20261031k-stage-b-input-v2/NORMALIZED_EXTENSION_INPUT_ROWS.json.gz';assert sha(source)==p['source_sha256']==pre['normalized_input_sha256'];rows=json.loads(gzip.decompress(source.read_bytes()))['rows'];index={};seen=set();boundrows=0;controlrows=0
    for r in rows:
        key=(int(r['week']),r['source_method_id'],r['source_row_index']);assert key not in index;index[key]=r
    assert len(rows)==31908 and len(roster)==181;assert sum(r['status']=='COMPLETED_STAGE_A_REUSE'for r in roster)==36 and sum(r['status']=='REPLAYABLE_FROZEN_EXACT_SAVED_ROWS'for r in roster)==145
    wanted={(tuple(r['recipe']),x['week']):x for r in roster if r['status']=='REPLAYABLE_FROZEN_EXACT_SAVED_ROWS'for x in r['weeks']};assert len(wanted)==435
    for week in(5,6,7):
        refs={x['member']:x for x in pre['source_bindings']if x['week']==week};folder=refs['GRADED_METHOD_ROWS.json.gz']['source_id'];gradepath=a.private_root/folder/'GRADED_METHOD_ROWS.json.gz';planpath=a.private_root/folder/'FROZEN_SELECTIONS_AND_K.json.gz';assert sha(gradepath)==refs['GRADED_METHOD_ROWS.json.gz']['sha256']and sha(planpath)==refs['FROZEN_SELECTIONS_AND_K.json.gz']['sha256'];plans=json.loads(gzip.decompress(planpath.read_bytes()));grades=json.loads(gzip.decompress(gradepath.read_bytes()))['graded'];recipes={tuple(v['recipe']):tag for tag,v in plans['plans'].items()if v['rule']=='P1'}
        for(recipe,w),entry in wanted.items():
            if w!=week:continue
            target,proc,arm,product=recipe;tag=entry['source_method_id'];assert tag in grades
            if arm!='ARCHIVED':assert recipes[recipe]==tag
            else:
                anchor=(target,'v2-distribution-controls-reconstruction-v2:ordered_leaf_cdf','H-MULTI','lower_median');assert entry['control_mask']['anchor_recipe']==list(anchor)and entry['control_mask']['anchor_method_id']==recipes[anchor];link=next(x for x in plans['baseline_links']if x['method_id']==recipes[anchor]and x['control']==proc);assert link['control_id']==tag
            rr=grades[tag];mask=[];admitted=0
            for r in rr:
                q=(week,tag,r['source_row_index']);z=index[q];assert q not in seen;seen.add(q);assert tuple(z['recipe'])==recipe;point=r.get('ranking_point');available=bool(r.get('admitted')and point is not None and math.isfinite(float(point)));assert z['point']==point and z['admitted']==available;admitted+=available;assert z['decision_time']==r.get('source_server_clock',r.get('server_retained_by'));assert z['fallback']==(r.get('fallback')if arm!='ARCHIVED'else None);assert z['source_grade_sha256']==refs['GRADED_METHOD_ROWS.json.gz']['sha256']and z['source_id']==folder and z['source_field']=='ranking_point'
                for name in('game_id','player_id','target','position','population','line','line_from','actual','selected_side','statistical_state','participation','kickoff'):assert z.get(name)==r.get(name)
                mask.append((week,r['source_row_index'],r.get('game_id'),r.get('player_id'),target));boundrows+=1;controlrows+=arm=='ARCHIVED'
            assert len(rr)==entry['outer_rows']and admitted==entry['admitted_metadata_rows'];assert hashlib.sha256(canon(sorted(mask,key=str))).hexdigest()==entry['fullsource_mask_sha256']
    assert seen==set(index)and boundrows==31908;targets={r['target']for r in rows};assert len(targets)==8 and not targets&set(root['stage_A']['targets']);assert pre['blocked_cells']==0 and set(pre['not_applicable_targets'])=={'anytime_td','nick-chart-ppr-v1'}
    out=dict(state='PASS_INDEPENDENT_K_EXTENSION_SOURCE_ADAPTER_AND_FINITE_ROSTER',preflight_sha256=sha(BASE/'stage-b-preflight-v2/PREFLIGHT_RECEIPT.json'),source_sha256=sha(source),checker_sha256=sha(Path(__file__)),finite_roster_cells=181,reused_StageA_cells=36,new_extension_cells=145,exact_weekly_plan_and_grade_cells=435,normalized_rows_exactly_reproduced=boundrows,controls_on_explicit_baseLeaf_matched_masks=controlrows,new_numeric_categories=8,total_numeric_categories_with_A=10,unsupported_targets=['anytime_td','nick-chart-ppr-v1'],scope='Every normalized point is retained ranking_point; source identity, actual, side, state, cutoff, population and fallback match saved grades. Controls remain explicitly restricted by matched baseline masks with outer rows retained; no full-offer control-coverage or originalV2issuance claim. No previous scoring totals were regenerated.',new_model_calls=0,new_forecasts=0,new_grades=0,new_private_exports=0)
    with(HERE/'EXTENSION_SOURCE_ADAPTER_INDEPENDENT_REVIEW.json').open('x')as f:json.dump(out,f,indent=2);f.write('\n')
    print(json.dumps(dict(state=out['state'],rows=boundrows,cells=145,categories=8)))
if __name__=='__main__':main()
