"""Verify source-bound startup empirical comparisons without rescoring rows."""
import argparse,collections,hashlib,json,math
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--receipt',type=Path,required=True);a=ap.parse_args();base=HERE.parent/'historical-startup';count=0;bindings=[];reasons=collections.Counter()
    for f in sorted(base.glob('**/INDEX_COMPARISON_ANNOTATIONS_V1.json')):
        ann=read(f);source=f.parent/'SCORES.json';rows=read(source);assert ann['source_score_sha256']==sha(source);assert len(ann['rows'])==len(rows);counts=collections.Counter()
        for index,z in enumerate(ann['rows']):
            assert z['source_row_index']==index;r=rows[index];v=z['comparison'];counts[v['status']]+=1
            if v['status']=='UNESTABLISHED':
                assert v['reason'];reasons[v['reason']]+=1;continue
            assert v['status']=='PAIRED_RETAINED_ROWS';j=v['comparator_source_row_index'];ref=rows[j];assert j!=index;assert ref['procedure_id']=='empirical-player-history-control-v1';assert ref['history_regime']==r['history_regime']==v['comparator_history_regime'];assert ref['target']==r['target']and ref['season']==r['season']and ref['window_id']==r['window_id'];assert ref['fallback_view']==r['fallback_view']=='FULL_SYSTEM';assert ref['n']==r['n']==v['paired_n']>0;assert ref['membership_sha256']==r['membership_sha256']==v['membership_sha256'];assert ref['source_outcome_index_sha256']==r['source_outcome_index_sha256'];assert ref['population']==r['population']and ref['position']==r['position'];assert ref['evaluation_weeks']==r['evaluation_weeks'];assert v['comparator_record_id']==ref['record_id']and v['comparator_procedure_id']==ref['procedure_id']and v['comparator_product_id']==ref['product_id'];assert(ROOT/v['comparator_source_artifact']).resolve()==source.resolve()
            metric='brier'if r['target']=='anytime_td'else'mae';assert v['metric']==metric;assert ref['product_id']==('event_probability'if metric=='brier'else'lower_median');assert math.isclose(v['candidate_error'],r[metric],rel_tol=1e-12,abs_tol=1e-12)and math.isclose(v['comparator_error'],ref[metric],rel_tol=1e-12,abs_tol=1e-12);assert v['uncertainty']['status']=='NOT_RECOMPUTED_FROM_AGGREGATE_SOURCES';assert'Procedure-plus-information'in v['scope'];count+=1
        bindings.append(dict(source=str(source.relative_to(ROOT)),score_sha256=sha(source),annotation_sha256=sha(f),views=len(rows),status_counts=dict(counts)))
    assert len(bindings)==5 and count==4608
    out=dict(state='PASS_EXACT_MASK_EMPIRICAL_STARTUP_COMPARISON_ANNOTATIONS',paired_comparisons=count,source_bindings=bindings,unestablished_reasons=dict(reasons),verified='Every paired FULL view shares exact label-index hash, scored membership, target, window, season, history and population with the declared empirical reference. Errors retain candidate-minus-comparator orientation. No uncertainty interval is inferred from aggregates.',limits=['Own learned/fallback views are not paired comparisons. Different feature-memory policies make this a procedure-plus-information reference, not an isolated learner effect.','2022 RECENT proxy and partial chart labels are unchanged.'],new_scores=0,new_fits=0,new_inference=0)
    with a.receipt.open('x')as f:json.dump(out,f,indent=2);f.write('\n')
    print(json.dumps(dict(state=out['state'],paired_comparisons=count,sources=len(bindings))))
if __name__=='__main__':main()
