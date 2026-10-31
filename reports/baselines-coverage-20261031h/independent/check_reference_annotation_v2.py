"""Validate corrected comparison orientation against retained original paired records."""
import hashlib,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];H=Path(__file__).resolve().parent.parent
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def close(a,b):
    if a is None or b is None:assert a is b,(a,b)
    else:assert math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-12),(a,b)
def main():
    correction=read(H/'INDEX_REFERENCE_ANNOTATION_CORRECTION_V2.json');registry={r['artifact']:r for r in read(ROOT/'registries/RESULT_ARTIFACTS.json')};checked=reverse=empty=0;bindings=[]
    for b in correction['bindings']:
        old=ROOT/b['old_projection'];new=ROOT/b['new_projection'];source=ROOT/b['source_artifact'];assert sha(old)==b['old_sha256']and sha(new)==b['new_sha256'];assert registry[b['source_artifact']]['comparison_annotations']==b['new_projection']
        v1=read(old);v2=read(new);rows=read(source);assert v1['source_score_sha256']==v2['source_score_sha256']==sha(source);assert len(v1['rows'])==len(v2['rows'])==len(rows)
        cache={}
        for a1,a2 in zip(v1['rows'],v2['rows']):
            assert a1['source_row_index']==a2['source_row_index'];r=rows[a2['source_row_index']];c=a2['comparison']
            if c['status']=='UNESTABLISHED':assert a1==a2;empty+=1;continue
            assert c['status']=='PAIRED_RETAINED_ROWS'and c['paired_n']==r['n'];close(c['candidate_error'],r['brier']);u=c['uncertainty'];path=c['paired_source_artifact']
            if path not in cache:cache[path]={p['comparison_id']:p for p in read(ROOT/path)}
            p=cache[path][c['paired_comparison_id']];rev=r['reference_id']!='candidate';sgn=-1 if rev else 1;delta=sgn*p['delta'];close(u['delta'],delta);close(c['candidate_error']-c['comparator_error'],delta);close(u['relative_error_change'],delta/c['comparator_error']if c['comparator_error']else None)
            assert c['membership_sha256']==p['membership_sha256'];assert u['n']==p['n']==r['n'];close(u['candidate_error'],c['candidate_error']);close(u['comparator_error'],c['comparator_error'])
            for k in ('game_normal95_sensitivity','week_interval'):
                want=None if p.get(k)is None else([-p[k][1],-p[k][0]]if rev else p[k]);got=u.get(k)
                if want is None:assert got is None
                else:
                    for x,y in zip(got,want):close(x,y)
            assert u['weekly_paired_sums_counts']=={k:dict(v,loss_difference_sum=sgn*v['loss_difference_sum'])for k,v in p['weekly_paired_sums_counts'].items()}
            if rev:
                assert u['procedure_id']==r['procedure_id']and u['comparator']==c['comparator_procedure_id'];assert u['candidate_infinite_rows']==p['comparator_infinite_rows']and u['comparator_infinite_rows']==p['candidate_infinite_rows'];reverse+=1
            checked+=1
        bindings.append(dict(source_artifact=b['source_artifact'],source_sha256=sha(source),v1_sha256=sha(old),v2_sha256=sha(new)))
    report=dict(state='PASS_REFERENCE_ANNOTATION_V2_CORRECTION_AND_V1_PRESERVATION',checked_finite_paired_annotations=checked,reversed_reference_annotations=reverse,unchanged_unestablished_annotations=empty,bindings=bindings,canonical_scores_changed=False,new_fits=0,new_inference=0,new_grades=0)
    with (H/'independent/REFERENCE_ANNOTATION_V2_INDEPENDENT_REVIEW.json').open('x')as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps(report))
if __name__=='__main__':main()
