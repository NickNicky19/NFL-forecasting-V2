"""Lossless public report delivery; preserve all uncompressed originals."""
import argparse,csv,gzip,hashlib,json,shutil,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2.shared_subgroups import sha,now,write

def main(a):
 b=a.output;keep=a.preserve;keep.mkdir(parents=True,exist_ok=False);deliver=[]
 primary=[]
 with(b/'ALL_WEEKLY_METHOD_SIDE_TABLES.csv').open()as f:
  reader=csv.DictReader(f)
  for r in reader:
   if r['cohort_id']=='ALL'and not r['K']:primary.append(r)
 with(b/'ALL_METHOD_PRIMARY_SIDE_TABLES.csv').open('x',newline='')as f:
  writer=csv.DictWriter(f,fieldnames=list(primary[0]));writer.writeheader();writer.writerows(primary)
 for name in('ALL_WEEKLY_METHOD_SIDE_TABLES.csv','ALL_WEEKLY_METHOD_SIDE_TABLES.json','CUMULATIVE_W6_W7_METHOD_SIDE_TABLES.csv','CUMULATIVE_W6_W7_METHOD_SIDE_TABLES.json'):
  source=b/name;dest=source.with_name(source.name+'.gz');digest=sha(source);size=source.stat().st_size
  with source.open('rb')as src,dest.open('xb')as raw:
   with gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0,compresslevel=6)as out:shutil.copyfileobj(src,out,1024*1024)
  h=hashlib.sha256();total=0
  with gzip.open(dest,'rb')as f:
   while chunk:=f.read(1024*1024):h.update(chunk);total+=len(chunk)
  if h.hexdigest()!=digest or total!=size:raise ValueError('lossless delivery hash mismatch')
  source.rename(keep/name)
  deliver.append(dict(logical_uncompressed_name=name,uncompressed_sha256=digest,uncompressed_bytes=size,public_compressed_path=dest.relative_to(a.root).as_posix(),compressed_sha256=sha(dest),compressed_bytes=dest.stat().st_size,fresh_decompression_hash_equal=True,local_uncompressed_copy_preserved=True))
 p=b/'README.md';text=p.read_text()
 for r in deliver:text=text.replace('('+r['logical_uncompressed_name']+')','('+r['logical_uncompressed_name']+'.gz)')
 text=text.replace('## Where to find every winner and loss','[Compact primary method/side tables](ALL_METHOD_PRIMARY_SIDE_TABLES.csv) provide one row per method/history/output/rule on each panel. Full subgroup/K tables below are losslessly compressed for GitHub delivery; public gzip bytes recover the exact original CSV/JSON.\n\n## Where to find every winner and loss')
 p.write_text(text);write(b/'REPORT_DELIVERY_MANIFEST.json',dict(at=now(),files=deliver,primary_side_rows=len(primary),primary_csv_sha256=sha(b/'ALL_METHOD_PRIMARY_SIDE_TABLES.csv'),local_uncompressed_originals_preserved=True,private_locators_public=False,scientific_scores_changed=False))
 print(json.dumps(dict(delivered=len(deliver),compressed_bytes=sum(r['compressed_bytes']for r in deliver),uncompressed_bytes=sum(r['uncompressed_bytes']for r in deliver),primary_rows=len(primary))))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--output',type=Path,required=True);p.add_argument('--preserve',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();main(a)
