"""Additional common-row views from completed saved-row grading; no refit/replay."""
import argparse,collections,gzip,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools import grade_saved_week8 as core,grade_week8_captured_library as library
from nfl_v2.recorded_prop_grading import canonical


def main(private,public):
    parent=public/'captured-library-v2';out=public/'comparable-products-v3';out.mkdir(exist_ok=False)
    data=json.loads(gzip.decompress((private/'CAPTURED_LIBRARY_NUMERIC_ROWS_V1.json.gz').read_bytes()))['rows']
    policy=core.read(parent/'COMMON_PANEL_DEFINITION.json');primary=set(policy['primary_captures']);groups=collections.defaultdict(list)
    for r in data:
        r['scored']=r['error']is not None
        groups[library.group(r)].append(r)
    members=collections.defaultdict(list);exclusions=[]
    for g,rr in groups.items():
        if g[0]not in primary:continue
        eligible_outputs=sum(r['original_forecast_issued']and r['T90_eligible']for r in rr)
        if not eligible_outputs:
            exclusions.append(dict(method_key=library.view_id(g),capture=g[0],procedure=g[1],history=g[2],product=g[3],target=g[-1],rows=len(rr),reason='NO_CAPTURED_ISSUED_COMPATIBLE_OUTPUT; preserved as unavailable, not confidence abstention'))
            continue
        members[g[-1]].append({library.key(r)for r in rr if r['scored']and r['T90_eligible']})
    common={t:set.intersection(*sets)for t,sets in members.items()}
    definition=dict(state='ADDITIONAL_COMPARABLE_ISSUED_PRODUCT_MASK_NO_OLD_METRIC_CHANGE',at_utc=core.now(),parent_numeric_scores_sha256=core.sha(parent/'SCORES.json'),private_rows_sha256=core.sha(private/'CAPTURED_LIBRARY_NUMERIC_ROWS_V1.json.gz'),
        primary_captures=sorted(primary),exclusion_rule='Only entire products with zero genuinely issued/T90-eligible outputs are inapplicable. This property is established from frozen forecasts without labels/losses. No losing or fallback method excluded.',
        old_all_product_intersection_retained=True,scope_exclusions=exclusions,common_final_rows={t:len(v)for t,v in common.items()},
        limitations='SourceAB/C blocked Leaf contexts carry a single absolute_error_point placeholder; no such issued Leaf point product exists. Those raw rows remain unavailable with exact original identity. Classic anytime adjusted point is absent; raw expected TD count is not event probability. Excluding these nonoutputs avoids an empty comparison but does not improve coverage of any forecast system.')
    core.save(out/'FROZEN_COMPARISON_SCOPE_V3.json',definition)
    numeric=[]
    for g,rr in sorted(groups.items()):
        if g[0]not in primary or not any(r['original_forecast_issued']and r['T90_eligible']for r in rr):continue
        cc=[r for r in rr if r['T90_eligible']and library.key(r)in common.get(g[-1],set())]
        numeric.append(library.numeric(cc,g,'ALL_ISSUED_COMPATIBLE_METHOD_COMMON_FINAL_ROWS_V3'))
    # Selection views use the same forecast/outcome keys and the same frozen
    # provider-labelled threshold rows; side pools still differ by chosen side.
    grades=json.loads(gzip.decompress((private/'CAPTURED_LIBRARY_P1_ROWS_V1.json.gz').read_bytes()))['rows'];by=collections.defaultdict(list)
    for r in grades:
        if r['capture_version']in primary and library.key(r)in common.get(r['target'],set()):by[r['method_key']].append(r)
    source={r['method_key']:r for r in core.read(parent/'SCORES.json')};sides=[]
    for mid,rr in sorted(by.items()):
        m=source[mid];ss=core.aggregate(rr,panel='COMMON_ISSUED_METHOD_ROWS_SAVED_T90_THRESHOLD_P1_V3:'+m['capture_version'],method=m['procedure_id']+':'+mid,track='C_RESEARCH_REPLAY',strategy='P1',pool=rr)
        for r in ss:
            if r['target']!=m['target']:continue
            r.update(method_key=mid,base_procedure_id=m['procedure_id'],capture_version=m['capture_version'],history_regime=m['history_regime'],product_id=m['product_id'],information_policy=m['information_policy'],availability_arm=m['availability_arm']);sides.append(r)
    core.save(out/'SCORES.json',numeric);core.save(out/'SELECTION_SCORES.json',sides);core.write_csv(out/'NUMERICAL_TABLE.csv',numeric)
    table=core.wide(sides);core.save(out/'SELECTION_SIDE_TABLE.json',table);core.write_csv(out/'SELECTION_SIDE_TABLE.csv',table)
    core.save(out/'RUN_RECEIPT.json',dict(state='NEW_COMMON_COMPARISONS_FROM_RETAINED_GRADED_ROWS',at_utc=core.now(),numeric_views=len(numeric),side_views=len(sides),source_projection_hash=core.sha(private/'CAPTURED_LIBRARY_NUMERIC_ROWS_V1.json.gz'),new_fits=0,new_inference=0,new_forecasts=0,new_raw_outcome_rows_acquired=0,old_scores_unchanged=True,scoring_code_sha256=core.sha(library.__file__),code_sha256=core.sha(__file__)))
    print(json.dumps(dict(state='COMMON_COMPARISONS_SCORED',common=definition['common_final_rows'],no_captured_product_cells=len(exclusions),numeric_views=len(numeric),side_views=len(sides))))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--private-root',type=Path,required=True);p.add_argument('--public-root',type=Path,required=True);a=p.parse_args();main(a.private_root,a.public_root)
