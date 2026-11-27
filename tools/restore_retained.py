#!/usr/bin/env python3
"""Read pinned public Git objects through an existing authorized gh installation.

No raw evidence is written to the public repository; no interactive credentials,
Actions, Odds API, workflows, model fits or publication are involved.
"""
import argparse,base64,gzip,hashlib,json,pathlib,subprocess,os
ROOT=pathlib.Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--private-dir',type=pathlib.Path,required=True);p.add_argument('--include-later-week7',action='store_true');a=p.parse_args()
 dest=a.private_dir.resolve()
 if dest==ROOT or ROOT in dest.parents:raise SystemExit('private-dir must be outside repository')
 m=json.loads((ROOT/'registries/PUBLIC_REPLAY_SOURCE_IDS.json').read_text())
 dest.mkdir(parents=True,exist_ok=True);os.chmod(dest,0o700)
 def fetch(meta, repository=None):
  # Existing CLI/proxy authentication only; errors propagate without reading secrets.
  r=subprocess.run(['gh','api',f"repos/{repository or m['repository']}/git/blobs/{meta['blob_sha']}"],check=True,capture_output=True,text=True,timeout=90)
  obj=json.loads(r.stdout);body=base64.b64decode(obj['content'],validate=False)
  if len(body)!=meta['bytes'] or hashlib.sha1(b'blob '+str(len(body)).encode()+b'\0'+body).hexdigest()!=meta['blob_sha']:raise ValueError('Git blob byte verification failed')
  if 'sha256' in meta and hashlib.sha256(body).hexdigest()!=meta['sha256']:raise ValueError('SHA256 mismatch')
  return body
 forecast=fetch(m['forecast']);(dest/'forecast.json.gz').write_bytes(forecast)
 original=fetch(m['original_scorecard']);(dest/'original-scorecard.json').write_bytes(gzip.decompress(original))
 wrappers=[];out=[]
 for x in m['outcomes']:
  body=fetch(x);wrappers.append(dict(blob_sha=x['blob_sha'],content=base64.b64encode(body).decode()))
  out.append(json.loads(gzip.decompress(body)))
 (dest/'outcomes-base64.json').write_text(json.dumps(wrappers))
 (dest/'outcomes.json').write_text(json.dumps(out))
 if a.include_later_week7:
  later=m['later_label_source']
  for kind,name in [('stats','production-stats-2026-w07.json'),('schedule','production-week-2026-w07.json')]:
   (dest/name).write_bytes(fetch(later[kind],later['repository']))
 receipt={'schema':m['schema'],'source_commit':m['commit'],'restored_outcomes':len(out),'sha256_forecast':hashlib.sha256(forecast).hexdigest(),'source_truth':'not independently authenticated','durability':'local only; originals recoverable from pinned Git objects subject access/retention'}
 (dest/'RESTORE_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
if __name__=='__main__':main()
