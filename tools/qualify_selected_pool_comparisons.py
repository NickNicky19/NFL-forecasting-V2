"""Normalize explicit retained common-pool comparison labels for index delivery."""
import argparse,json,hashlib,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main(source):
 registry=ROOT/'registries/RESULT_ARTIFACTS.json';items=json.loads(registry.read_text());item=next(r for r in items if r['artifact']==source);p=ROOT/item['comparison_annotations'];data=json.loads(p.read_text());scores=json.loads((ROOT/source).read_text());byid={r['record_id']:r for r in scores};labels=0;subsets=0
 for a in data['rows']:
  c=a['comparison']
  if c['status']=='UNESTABLISHED':continue
  if c['status']!='PAIRED_COMMON_DECIDED_ORIGINAL_SELECTED':raise ValueError('unsupported original status')
  c['original_status']=c['status'];c['status']='PAIRED_RETAINED_ROWS';labels+=1;r=scores[a['source_row_index']]if'source_row_index'in a else byid[a['source_record_id']];same=c['paired_n']==r['n']and math.isclose(c['candidate_error'],r[c['metric']],rel_tol=1e-10,abs_tol=1e-10)
  if not same:
   assert 0<c['paired_n']<=r['n'];c.update(status='PAIRED_SUBSET_RETAINED_ROWS',complete_scored_view_n=r['n'],comparison_scope='Common decided original-selected rows; complete selected pools remain separately reported.');subsets+=1
 data['original_projection_sha256']=hashlib.sha256(p.read_bytes()).hexdigest();data['normalization_note']='Index vocabulary only; original scores, masks and paired losses unchanged.';out=p.with_name('INDEX_SELECTED_POOL_COMPARISON_ANNOTATIONS_V1.json');assert not out.exists();out.write_text(json.dumps(data,separators=(',',':'))+'\n');item['comparison_annotations']=out.relative_to(ROOT).as_posix();registry.write_text(json.dumps(items,indent=2)+'\n');print(json.dumps(dict(comparison_labels_normalized=labels,explicit_paired_subsets=subsets,source_scores_changed=0)))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--artifact',required=True);main(p.parse_args().artifact)
