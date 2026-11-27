"""Download only the approved pinned runtime; no football decoding or fitting."""
from __future__ import annotations
import argparse,hashlib,importlib.metadata,io,json,os,pathlib,subprocess,sys,tarfile,urllib.request,zipfile
TORCH='https://download-r2.pytorch.org/whl/cpu/torch-2.6.0%2Bcpu-cp312-cp312-linux_x86_64.whl'
TORCH_SHA='59e78aa0c690f70734e42670036d6b541930b8eabbaa18d94e090abf14cc4d91'
REV='a626a1b67049b0b1748ebe8c92f7df40aaebd334';HFREV='4dcd344ece2c00be9e831fdd35bed57b5ad83e19'
MODEL='tabicl-classifier-v2-20260212.ckpt';MODEL_SHA='bdc7dbd5e4ff21f8f0456fcf90c6b7cdf72dbea960f2d05b19bec19f9b3d4ed0'
PINS=['sympy==1.13.1','filelock==3.20.0','networkx==3.6','Jinja2==3.1.6','MarkupSafe==3.0.3','fsspec==2025.10.0','einops==0.8.1','tqdm==4.67.1','huggingface-hub==0.26.5','tokenizers==0.20.3','requests==2.32.5','urllib3==2.5.0']
EXPECTED={'_sklearn/classifier.py':'97884ad8ed401db15e5c0f85f22173f644bcd18762d5083b90725d7aa0c3d5ad','_sklearn/base.py':'7f8f284ca91bf1f5a016179834e508890b3f5368c4a48a7dcb6cb4b83a30051a','__about__.py':'0ca93ed5bfab66c245c458b526827b4e612f204434adff82f470195b0be3b8cd'}
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def get(url,path,limit,expected=None,length=None):
 if path.exists():
  if expected and digest(path)==expected and(length is None or path.stat().st_size==length):return
  raise ValueError('Unverified existing bytes; no replacement/retry')
 h=hashlib.sha256();n=0
 with urllib.request.urlopen(url,timeout=45)as r,path.open('xb')as f:
  while True:
   b=r.read(1048576)
   if not b:break
   n+=len(b)
   if n>limit:raise ValueError('Bounded source response exceeded')
   h.update(b);f.write(b)
  f.flush();os.fsync(f.fileno())
 if(expected and h.hexdigest()!=expected)or(length is not None and n!=length):raise ValueError('Pinned source length/hash mismatch')
def main():
 p=argparse.ArgumentParser();p.add_argument('--runtime',type=pathlib.Path,required=True);a=p.parse_args();r=a.runtime;w=r/'wheels';w.mkdir(exist_ok=True);site=r/'site';site.mkdir(exist_ok=True)
 # Fixed package names/versions, binary only, dependencies never auto-resolved.
 subprocess.run([sys.executable,'-m','pip','download','--disable-pip-version-check','--no-cache-dir','--only-binary=:all:','--no-deps','--index-url','https://pypi.org/simple','--dest',str(w),*PINS],check=True)
 tw=w/'torch-2.6.0+cpu-cp312-cp312-linux_x86_64.whl';get(TORCH,tw,240000000,TORCH_SHA)
 lock=[]
 for wheel in sorted(w.glob('*.whl')):
  with zipfile.ZipFile(wheel)as z:
   names=[x for x in z.namelist()if x.endswith('.dist-info/METADATA')];metadata=z.read(names[0]).decode();license_lines=[l for l in metadata.splitlines()if l.startswith(('Name:','Version:','License:','License-Expression:','Requires-Dist:'))]
   lock.append(dict(file=wheel.name,bytes=wheel.stat().st_size,sha256=digest(wheel),uncompressed_bytes=sum(i.file_size for i in z.infolist()),metadata=license_lines))
 if sum(p.stat().st_size for p in r.rglob('*')if p.is_file())+sum(x['uncompressed_bytes']for x in lock)>1073741824:raise ValueError('Compressed+unpacked fixed runtime cannot fit storage cap')
 (r/'DEPENDENCY_LOCK.json').write_text(json.dumps({'fixed_versions':PINS,'torch':'2.6.0+cpu','wheels':lock},indent=2)+'\n')
 subprocess.run([sys.executable,'-m','pip','install','--disable-pip-version-check','--no-cache-dir','--no-deps','--no-compile','--target',str(site),*[str(x)for x in sorted(w.glob('*.whl'))]],check=True)
 for wheel in w.glob('*.whl'):wheel.unlink() # Source hashes/lock retained; no duplicate package cache.
 archive=r/'tabicl-source.tar.gz';get('https://api.github.com/repos/soda-inria/tabicl/tarball/'+REV,archive,25000000)
 source=r/'source';source.mkdir(exist_ok=True)
 with tarfile.open(archive,'r:gz')as tf:
  for member in tf.getmembers():
   parts=pathlib.PurePosixPath(member.name).parts[1:]
   if not parts or not member.isfile():continue
   if parts[:2]!=('src','tabicl')and parts!=('LICENSE',):continue
   if '..'in parts or member.size>5000000:raise ValueError('Unsupported source archive member')
   dest=source.joinpath(*parts);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(tf.extractfile(member).read())
 for path,expected in EXPECTED.items():
  if digest(source/'src/tabicl'/path)!=expected:raise ValueError('Frozen source bytes differ '+path)
 archive.unlink()
 get('https://huggingface.co/jingang/TabICL/resolve/'+HFREV+'/'+MODEL,r/MODEL,110368038,MODEL_SHA,110368038)
 actual={}
 for name in ['numpy','scipy','scikit-learn','psutil','typing-extensions','mpmath','packaging','PyYAML','certifi','charset-normalizer','idna','setuptools']:
  actual[name]=importlib.metadata.version(name)
 (r/'BASE_ENVIRONMENT.json').write_text(json.dumps(actual,indent=2)+'\n')
 print(json.dumps({'state':'DOWNLOADED_PINNED_RUNTIME_NOT_YET_LOADED','checkpoint_bytes':110368038,'checkpoint_sha256':digest(r/MODEL),'source_commit':REV,'dependency_wheels':len(lock),'runtime_bytes':sum(p.stat().st_size for p in r.rglob('*')if p.is_file()),'NFL_fits':0}))
if __name__=='__main__':main()
