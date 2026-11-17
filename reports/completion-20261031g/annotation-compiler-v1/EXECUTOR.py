"""Split already computed metadata corrections by immutable source artifact."""
import collections,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'reports/completion-20261031g'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 groups=collections.defaultdict(dict);inputs=[]
 for p in sorted((BASE/'roster').glob('*/metadata-and-control-k-v1/*ANNOTATIONS.json')):
  rows=json.loads(p.read_text());inputs.append(dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p),rows=len(rows)))
  for r in rows:
   source=r['source_artifact'];idx=r['source_row_index'];g=groups[source].setdefault(idx,dict(source_row_index=idx,record_id=r['record_id']))
   if g['record_id']!=r['record_id']:raise ValueError('source correction identity conflict')
   if sha(ROOT/source)!=r['source_artifact_sha256']:raise ValueError('immutable source changed')
   if 'precision_counts'in r:g['precision_counts']=r['precision_counts']
   if 'probability_scores'in r:g['probability_scores']=r['probability_scores']
   if 'admitted_rule_abstentions'in r:g['denominators']={k:v for k,v in r.items()if k not in('source_artifact','source_artifact_sha256','source_row_index','record_id')}
 bindings=[]
 for source,rows in sorted(groups.items()):
  p=(ROOT/source).with_name('CURRENT_REPORTING_ANNOTATIONS.json')
  if p.exists():raise ValueError('immutable annotation projection already exists')
  body=dict(source_score_sha256=sha(ROOT/source),semantics='Source-bound corrected probability/coverage/precision metadata only; source forecasts, selections, losses and original bytes preserved.',rows=[rows[i]for i in sorted(rows)])
  p.write_text(json.dumps(body,separators=(',',':'),allow_nan=False)+'\n');bindings.append(dict(source_artifact=source,projection=p.relative_to(ROOT).as_posix(),sha256=sha(p),rows=len(rows)))
 (BASE/'REPORTING_ANNOTATION_MANIFEST.json').write_text(json.dumps(dict(state='SOURCE_BOUND_COMPILED_NO_NEW_SCORES',inputs=inputs,bindings=bindings),indent=2)+'\n');print(json.dumps(dict(artifacts=len(bindings),rows=sum(b['rows']for b in bindings))))
if __name__=='__main__':main()
