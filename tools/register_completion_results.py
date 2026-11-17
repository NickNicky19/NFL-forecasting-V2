"""Root-only append of immutable completion score sources and bound metadata."""
import json,hashlib,collections
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'reports/completion-20261031g'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 registry=ROOT/'registries/RESULT_ARTIFACTS.json';rows=json.loads(registry.read_text());known={r['artifact']for r in rows};corrections=json.loads((BASE/'REPORTING_ANNOTATION_MANIFEST_V2.json').read_text());projection={r['source_artifact']:r['projection']for r in corrections['bindings']};added=[];counts=collections.Counter()
 for path in sorted(BASE.rglob('*SCORES.json')):
  rel=path.relative_to(ROOT).as_posix()
  if rel in known:continue
  data=json.loads(path.read_text())
  if not isinstance(data,list)or not data:raise ValueError('empty/invalid score source requires separate failed registration: '+rel)
  if len({r['record_id']for r in data})!=len(data):raise ValueError('duplicate source recordID')
  item=dict(artifact=rel,state='SCORED',kind='completion_saved_row_or_retained_law_evaluation',version_note='Retained source forecasts/laws; new matched threshold/season/selection views, no new NFLfit or original issuance. Source timing/vintage/conditioning retained.')
  for key,filename in [('selection_metadata_projection','METADATA_SUPPLEMENT.json'),('comparison_annotations','COMPARISON_ANNOTATIONS.json')]:
   p=path.with_name(filename)
   if p.exists():
    obj=json.loads(p.read_text())
    if obj.get('source_score_sha256')!=sha(path):raise ValueError('sibling annotation source mismatch')
    item[key]=p.relative_to(ROOT).as_posix()
  if rel in projection:item['reporting_annotations']=projection[rel]
  rows.append(item);added.append(dict(path=rel,sha256=sha(path),rows=len(data)));counts.update(r['record_kind']for r in data)
 registry.write_text(json.dumps(rows,indent=2)+'\n');added=[];counts=collections.Counter()
 for item in rows:
  if not item['artifact'].startswith(BASE.relative_to(ROOT).as_posix()+'/')or item['state']!='SCORED':continue
  path=ROOT/item['artifact'];data=json.loads(path.read_text());added.append(dict(path=item['artifact'],sha256=sha(path),rows=len(data)));counts.update(r['record_kind']for r in data)
 (BASE/'NEW_CANONICAL_SCORE_MANIFEST.json').write_text(json.dumps(dict(state='REGISTERED_SOURCE_ARRAYS',sources=added,views=sum(r['rows']for r in added),by_kind=dict(counts),unit='Evaluation views, not methods/fits or independent NFLobservations',new_fits=0),indent=2)+'\n');print(json.dumps(dict(artifacts=len(added),views=sum(r['rows']for r in added),by_kind=dict(counts))))
if __name__=='__main__':main()
