from pathlib import Path
import json,urllib.request,concurrent.futures,hashlib,time
D=Path(__file__).parent
manifest=json.loads((D/'block4.json').read_bytes())
def one(x):
    root=D/('C' if x['repository'].endswith('NFL-forecasting-NGS-C') else 'website')
    path=(D/'selector-inputs'/x['local_name']) if x.get('local_name') else root/x['path']
    path.parent.mkdir(parents=True,exist_ok=True)
    url='https://raw.githubusercontent.com/'+x['repository']+'/'+x['ref']+'/'+x['path']
    if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest()==x['sha256']:
        raw=path.read_bytes();via='existing exact bytes'
    else:
        raw=urllib.request.urlopen(url,timeout=45).read();via='immutable public GitHub'
        assert hashlib.sha256(raw).hexdigest()==x['sha256'],(x['path'],'hash mismatch')
        path.write_bytes(raw)
    assert hashlib.sha256(raw).hexdigest()==x['sha256']
    if 'bytes' in x: assert len(raw)==x['bytes']
    return {**x,'bytes':len(raw),'verification':'PASS','via':via,'local_relative_path':str(path.relative_to(D))}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool: rows=list(pool.map(one,manifest['inputs']))
(D/'FETCH_VERIFICATION.json').write_text(json.dumps({'observed_UTC':__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),'inputs':rows,'count':len(rows),'bytes':sum(x['bytes']for x in rows)},indent=2)+'\n')
print(json.dumps({'count':len(rows),'bytes':sum(x['bytes']for x in rows),'verification':'PASS'}))
