"""Verify explicit pool-versus-selected law fallback denominator semantics."""
import argparse,collections,gzip,hashlib,json,math
from pathlib import Path

def read(p):return json.loads(p.read_bytes())
def gz(p):return json.loads(gzip.decompress(p.read_bytes()))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def close(a,b):assert a==b or(isinstance(a,(float,int))and isinstance(b,(float,int))and math.isclose(a,b,abs_tol=1e-12,rel_tol=1e-12)),(a,b)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--private',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();pub=a.root/'reports/completion-20261031g';rows=read(pub/'ROLLING_CUMULATIVE_SELECTION_RESULTS.json');cache={};grades={};counts=collections.Counter();combined_checked=0
 for r in rows:
  values=[];denoms=[];scopes=[];comb_selected=[]
  for z in r['source_records']:
   path=z['path']
   if path not in cache:cache[path]={x['record_id']:x for x in read(a.root/path)}
   x=cache[path][z['record_id']]
   if r['procedure_id'].startswith('v2-server-retained'):
    values.append(None);denoms.append(None);scopes.append('UNRETAINED');continue
   n=Path(path).parts[3];leaf='complete-leaf-law'in n
   if n not in grades:grades[n]=gz(a.private/('completion-20261031g-'+n)/('GRADED_COMPLETE_LEAF_LAWS.json.gz'if leaf else'GRADED_METHOD_ROWS.json.gz'))['graded']
   rr=grades[n][x['method_id']]
   if leaf:
    rr=[v for v in rr if v['selected_side']and(x['side']=='Combined'or v['selected_side']==x['side'])];v=sum(t['source']=='REUSED_ELIGIBLE_FALLBACK_LAW'for t in rr);d=len(rr);scope='SELECTED_SIDE_SUBSET'
   else:
    pool=[v for v in rr if v['admitted']];v=sum(t['fallback']not in(None,'none')for t in pool);d=len(pool);scope='ADMITTED_FORECAST_POOL'
    if x['side']=='Combined':comb_selected.append(sum(t['selected_side']is not None and t['fallback']not in(None,'none')for t in pool))
   values.append(v);denoms.append(d);scopes.append(scope)
  assert len(set(scopes))==1;scope=scopes[0];v=sum(values)if all(x is not None for x in values)else None;d=sum(denoms)if all(x is not None for x in denoms)else None;assert(r['fallback_scope'],r['fallback'],r['fallback_denominator'])==(scope,v,d);close(r['fallback_rate'],v/d if d else None);counts[scope]+=1
  if comb_selected:assert sum(comb_selected)==v;combined_checked+=1
 out=dict(state='PASS_INDEPENDENT_FINAL_FALLBACK_SCOPE_COUNTS_AND_RATES',source_bound_aggregate_rows=len(rows),scope_counts=dict(counts),combined_parent_pool_equals_selected_proofs=combined_checked,machine_results_sha256=sha(pub/'ROLLING_CUMULATIVE_SELECTION_RESULTS.json'),controls_missing_fallback_null=True,pool_counts_not_misrepresented_as_side_partitions=True,new_fits=0,new_inference=0,new_grades=0)
 with a.output.open('x')as f:json.dump(out,f,indent=2);f.write('\n')
 print(json.dumps(out))
if __name__=='__main__':main()
