"""Disclose paired-subset comparison scope without changing retained scores."""
import hashlib,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 registry=ROOT/'registries/RESULT_ARTIFACTS.json';items=json.loads(registry.read_text());changed=0
 for item in items:
  if 'completion-20261031g'not in item['artifact']or not item.get('comparison_annotations'):continue
  original=ROOT/item['comparison_annotations'];annotation=json.loads(original.read_text());scores=json.loads((ROOT/item['artifact']).read_text());byid={r.get('record_id'):r for r in scores};count=0
  for a in annotation['rows']:
   c=a['comparison']
   if c.get('status')!='PAIRED_RETAINED_ROWS':continue
   row=scores[a['source_row_index']]if 'source_row_index'in a else byid[a['source_record_id']]
   loss=row.get('selection_loss_rate')if c['metric']=='selection_loss_rate'else row.get(c['metric']);same=c['paired_n']==row['n']and loss is not None and math.isclose(c['candidate_error'],loss,rel_tol=1e-10,abs_tol=1e-10)
   if not same:
    assert 0<c['paired_n']<=row['n'];c['status']='PAIRED_SUBSET_RETAINED_ROWS';c['comparison_scope']='Only common supported selected rows; paired candidate loss differs from complete scored-view loss. Both sample sizes remain visible.';c['complete_scored_view_n']=row['n'];count+=1
  if count:
   path=original.with_name('COMPARISON_ANNOTATIONS_PAIRED_SCOPE_V2.json');assert not path.exists();annotation['previous_projection_sha256']=sha(original);annotation['metadata_correction']='Pairedsubsetscope disclosure; predictions/labels/counts/paired losses unchanged.';path.write_text(json.dumps(annotation,indent=2)+'\n');item['comparison_annotations']=str(path.relative_to(ROOT));changed+=count
 registry.write_text(json.dumps(items,indent=2)+'\n');print(json.dumps(dict(paired_subset_scopes_corrected=changed,score_rows_changed=0)))
if __name__=='__main__':main()
