#!/usr/bin/env python3
"""Create a fresh hash manifest of the staged public file tree; never overwrite."""
import argparse,datetime,hashlib,json,pathlib,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=pathlib.Path,required=True);a=p.parse_args();out=a.output.resolve()
 if not out.is_relative_to(ROOT) or out.exists():raise SystemExit('new repository-relative output required')
 rows=[]
 for name in subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0'):
  if not name:continue
  b=subprocess.check_output(['git','show',':'+name],cwd=ROOT)
  rows.append(dict(path=name,bytes=len(b),sha256=hashlib.sha256(b).hexdigest()))
 body=dict(schema='v2-public-staged-tree-hashes-v1',created_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),parent_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),scope='all staged public tracked files before this manifest; immutable historical manifest retained; hashes establish bytes, not source truth',files=rows,file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows))
 out.write_text(json.dumps(body,indent=2)+'\n');print(json.dumps({k:body[k] for k in ('file_count','total_bytes','created_at_utc')}))
if __name__=='__main__':main()
