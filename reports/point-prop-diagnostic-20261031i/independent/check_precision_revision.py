"""Verify the narrow scoring revision against the prior independent raw witness."""
import collections,hashlib,json,math
from pathlib import Path
HERE=Path(__file__).resolve().parent;BASE=HERE.parent/'historical-startup';ROOT=HERE.parents[2]
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    oldpath=BASE/'current-2026-v2/SCORES.json';newpath=BASE/'current-2026-precision-v3/SCORES.json';mappingpath=newpath.with_name('SOURCE_BOUND_SCORING_REPLACEMENTS.json');old=read(oldpath);new=read(newpath);mapping=read(mappingpath);witness=read(HERE/'STARTUP_2026_INDEPENDENT_REVIEW_V2_PRESERVED.json');p=read(newpath.with_name('FROZEN_PROTOCOL.json'));run=read(newpath.with_name('RUN_RECEIPT.json'))
    assert sha(oldpath)==mapping['old_source_sha256']==witness['score_sha256'];assert sha(newpath)==mapping['new_source_sha256']==run['score_sha256'];assert sha(newpath.with_name('FROZEN_PROTOCOL.json'))==run['protocol_sha256'];assert sha(newpath.with_name('SOURCE_SNAPSHOT.py'))==p['code_sha256'];assert len(new)==len(mapping['replacements'])==18
    corrections={(v['record_id'],v['metric']):v['expected']for v in witness['precision_differences']};changed_rows=0;changed_counts=0;seen=set();summed=collections.defaultdict(collections.Counter)
    for v in mapping['replacements']:
        a=old[v['old_source_row_index']];b=new[v['new_source_row_index']];assert a['record_id']==v['old_record_id']==b['replaces_source_record_id'];assert b['record_id']==v['new_record_id']and b['record_id']!=a['record_id'];assert v['old_record_id']not in seen;seen.add(v['old_record_id']);assert a['target']=='nick-chart-ppr-v1'and a['procedure_id'].startswith('v2-chronological')and a['product_id']=='point_choice_policy';assert b['correction_kind']=='PRECISION_ONLY_NO_FORECAST_OR_NATIVE_LOSS_CHANGE';changes=0
        for name,value in a.items():
            if name not in('record_id','precision_counts'):assert b[name]==value,(name,a['record_id'])
        for name,q in a['precision_counts'].items():
            fixed=b['precision_counts'][name];expected=corrections.get((a['record_id'],name),q['numerator']);assert fixed['numerator']==expected and fixed['denominator']==q['denominator']==b['n'];assert fixed['rate']==(expected/b['n']if b['n']else None);assert b[name]==fixed['rate'];changes+=fixed['numerator']!=q['numerator']
            if b['fallback_view']=='FULL_SYSTEM':summed[b['procedure_id']][name]+=expected
        changed_rows+=bool(changes);changed_counts+=changes
    expectedaffected={r['record_id']for r in old if r['target']=='nick-chart-ppr-v1'and r['procedure_id'].startswith('v2-chronological')};assert expectedaffected==seen
    grid=read(ROOT/p['reference_grid_path']);checked=0
    for r in grid:
        if r['procedure_id']not in summed or r['target']!='nick-chart-ppr-v1':continue
        for name,v in r['precision_counts'].items():assert summed[r['procedure_id']][name]==v['numerator'];checked+=1
    assert checked==21 and changed_rows==run['rows_with_actual_precision_count_change']==15 and changed_counts==len(corrections)
    out=dict(state='PASS_NARROW_CHART_POLICY_PRECISION_VERSION',parent_source_sha256=sha(oldpath),corrected_score_sha256=sha(newpath),replacement_mapping_sha256=sha(mappingpath),independent_raw_witness_sha256=sha(HERE/'STARTUP_2026_INDEPENDENT_REVIEW_V2_PRESERVED.json'),new_versions=18,rows_with_changed_precision=changed_rows,changed_precision_cells=changed_counts,fullperiod_precision_reference_checks=checked,native_losses_counts_membership_and_fallback_unchanged=True,original_3936_source_unchanged=True,scope='Expected precision counts come from the separately written107-recipe current raw audit, using the actual underlying selected product; no second NFL loss evaluation or model inference.',new_fits=0,new_inference=0,new_native_loss_scores=0,new_private_bytes=0)
    with(HERE/'CURRENT_STARTUP_PRECISION_V3_INDEPENDENT_REVIEW.json').open('x')as f:json.dump(out,f,indent=2);f.write('\n')
    print(json.dumps(out))
if __name__=='__main__':main()
