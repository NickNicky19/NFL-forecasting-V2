"""Read-only independent compressed append/inheritance and paired-annotation check."""
import argparse,collections,csv,gzip,hashlib,json,math,time,resource
from pathlib import Path

def read(p):return json.loads(p.read_bytes())
def sha(p):
 h=hashlib.sha256()
 with p.open('rb')as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def close(a,b):assert a==b or(isinstance(a,(float,int))and isinstance(b,(float,int))and math.isclose(a,b,abs_tol=2e-10,rel_tol=2e-10)),(a,b)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();start=time.monotonic();root=a.root;pub=root/'reports/completion-20261031g';m=read(pub/'results-index-v1/INDEX_MANIFEST.json');oldpath=root/m['previous_sharded_checkpoint']['artifact'];assert sha(oldpath)==m['previous_sharded_checkpoint']['sha256'];old=read(oldpath);oldsh={r['path']:r for r in old['shards']};oldcsv={r['path']:r for r in old['csv_parts']};assert all(r in m['shards']for r in oldsh.values())and all(r in m['csv_parts']for r in oldcsv.values());assert len(oldsh)==101 and len(oldcsv)==17
 annfile=pub/'roster/paired-probability-v1/INDEX_COMPARISON_ANNOTATIONS_V1.json';ann=read(annfile);want={(r['source_artifact'],r['record_id']):r for r in ann};assert len(want)==160;checked={};ids=set();newids=set();kinds=collections.Counter();newkinds=collections.Counter();by_source=collections.Counter();rawbytes=0;compressed=0;newparts=0
 for b in m['shards']:
  file=root/b['path'];assert file.stat().st_size==b['bytes']and sha(file)==b['sha256'];body=file.read_bytes();new=b['path']not in oldsh
  if b.get('compression')=='gzip':
   body=gzip.decompress(body);assert len(body)==b['uncompressed_bytes']and hashlib.sha256(body).hexdigest()==b['uncompressed_sha256'];assert len(body)<=m['max_shard_bytes'];compressed+=1;rawbytes+=len(body)
  rows=json.loads(body);assert len(rows)==b['records'];newparts+=new
  for r in rows:
   rid=r['test_id'];assert rid not in ids;ids.add(rid);kinds[r['kind']]+=1
   if new:newids.add(rid);newkinds[r['kind']]+=1;by_source[r['source_artifact']]+=1
   key=(r.get('source_artifact'),r.get('source_record_id'))
   if key in want:
    z=want[key];c=r['reporting_comparison'];expected=dict(z['comparison']);expected['status']='PAIRED_RETAINED_ROWS';expected['membership_sha256']=z['membership_sha256'];assert c==expected;assert r['source_artifact_sha256']==z['source_artifact_sha256'];assert r['n']==c['paired_n'];close(r['metrics']['brier'],c['candidate_error']);assert key not in checked;checked[key]=r['test_id']
  del rows,body
 assert len(ids)==m['record_count']==438393;assert len(newids)==279306;assert kinds==collections.Counter(m['by_kind']);assert len(checked)==160;assert newparts==compressed==213
 csv_ids=set();csvrows=0;headers=set();newcsv=0
 for b in m['csv_parts']:
  file=root/b['path'];assert file.stat().st_size==b['bytes']and sha(file)==b['sha256'];new=b['path']not in oldcsv;op=gzip.open if b.get('compression')=='gzip'else open
  with op(file,'rt',newline='')as f:
   reader=csv.DictReader(f);headers.add(tuple(reader.fieldnames))
   if not new:continue
   newcsv+=1;n=0
   for r in reader:
    assert r['test_id']not in csv_ids;csv_ids.add(r['test_id']);n+=1
    if r['source_record_id']in {z['record_id']for z in ann}:assert r['comparison_status']=='PAIRED_RETAINED_ROWS'
   assert n==b['rows'];csvrows+=n
 assert csv_ids==newids and csvrows==279306 and newcsv==28
 for b in m['input_manifests']:assert sha(root/b['source_artifact'])==b['sha256']
 report=dict(state='PASS_INDEPENDENT_FINAL_COMPRESSED_INDEX_APPEND_INHERITANCE_AND_COMPARISONS',manifest_sha256=sha(pub/'results-index-v1/INDEX_MANIFEST.json'),records=len(ids),new_records=len(newids),inherited_records=len(ids)-len(newids),by_kind=dict(kinds),new_by_kind=dict(newkinds),inherited_unchanged_JSON_shards=len(oldsh),new_lossless_gzip_JSON_shards=newparts,uncompressed_new_JSON_bytes=rawbytes,inherited_unchanged_CSV_parts=len(oldcsv),new_gzip_CSV_parts=newcsv,new_CSV_rows=csvrows,CSV_JSON_new_ID_sets_equal=True,distinct_CSV_headers=len(headers),source_manifests_hash_checked=len(m['input_manifests']),sparse_full_mask_proper_annotations_checked=len(checked),sparse_annotations_sha256=sha(annfile),no_duplicate_test_IDs=True,new_fits=0,new_inference=0,new_grades=0,resources=dict(wall_seconds=time.monotonic()-start,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024),scope='Index continuity, exact stored/decompressed bytes, identities/counts and inclusion of all160 independently checked proper-score comparisons. SourceNFLarithmetic verified in separate receipts; records remain evaluationviews, not learners/fits/games.')
 with a.output.open('x')as f:json.dump(report,f,indent=2);f.write('\n')
 print(json.dumps(report))
if __name__=='__main__':main()
