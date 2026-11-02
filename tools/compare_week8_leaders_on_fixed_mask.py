"""Pair Week8 leaders with the incumbent on the existing all-method mask."""
import argparse,collections,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools import grade_saved_week8 as core,grade_week8_captured_library as lib
from nfl_v2.shared_subgroups import packet_rows
from nfl_v2.paired_uncertainty import paired_losses


def run(private,public):
    scores=core.read(public/'comparable-products-v3/SCORES.json');wanted={r['method_key']:r for r in scores};masks=collections.defaultdict(set)
    for r in packet_rows(private/'CAPTURED_LIBRARY_NUMERIC_ROWS_V1.json.gz'):
        mid=lib.view_id(lib.group(r))
        if mid in wanted and r['error']is not None and r['T90_eligible']:masks[mid].add(lib.key(r))
    common={t:set.intersection(*(masks[r['method_key']]for r in scores if r['target']==t))for t in core.TARGETS}
    for r in scores:assert len(common[r['target']])==r['n']
    leaders=core.read(public/'checkpoint-summary-v1/NUMERICAL_TIES.json');inc={r['target']:r for r in scores if r['capture_version']=='WEBSITE_ADAPTIVE_ORIGINAL_3907'};ids={r['method_key']for r in leaders}|{r['method_key']for r in inc.values()};points=collections.defaultdict(dict)
    for r in packet_rows(private/'CAPTURED_LIBRARY_NUMERIC_ROWS_V1.json.gz'):
        mid=lib.view_id(lib.group(r));key=lib.key(r)
        if mid in ids and key in common[r['target']]and r['error']is not None and r['T90_eligible']:points[mid][key]=r
    rows=[]
    for r in leaders:
        target=r['target']
        if target not in inc:continue
        aa=points[r['method_key']];bb=points[inc[target]['method_key']];keys=sorted(common[target]);assert set(aa)==set(bb)==set(keys);squared=target=='anytime_td';loss=lambda d,k:d[k]['error']**2 if squared else abs(d[k]['error'])
        rows.append(dict(target=target,candidate_method_key=r['method_key'],incumbent_method_key=inc[target]['method_key'],scope='EXACT_EXISTING_ALL_ISSUED_COMPATIBLE_METHOD_COMMON_FINAL_MASK_V3',**paired_losses([loss(aa,k)for k in keys],[loss(bb,k)for k in keys],[8]*len(keys),[k[0]for k in keys]),metric='Brier'if squared else'MAE',information_contract='Saved original forecasts at different earlier capture/source clocks, both pregame; no pure learner or currentlyserved improvement claim.'))
    out=public/'checkpoint-summary-v1';core.save(out/'LEADERS_VS_ADAPTIVE_ON_FIXED_COMMON_MASK_V2.json',rows);core.write_csv(out/'LEADERS_VS_ADAPTIVE_ON_FIXED_COMMON_MASK_V2.csv',rows)
    print(json.dumps(dict(state='EXACT_COMMON_MASK_PAIRED',comparisons=len(rows),new_fits=0,new_inference=0,new_forecasts=0)))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--private-root',type=Path,required=True);p.add_argument('--public-root',type=Path,required=True);a=p.parse_args();run(a.private_root,a.public_root)
