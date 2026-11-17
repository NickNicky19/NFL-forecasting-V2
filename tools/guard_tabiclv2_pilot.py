"""Finite external controller for the one approved B pilot, not a scheduler.

Private command/working paths and full logs stay in the supplied state directory.
Public summaries omit them. All stages share one cumulative ledger; no reset.
"""
from __future__ import annotations
import argparse,datetime,json,os,pathlib,resource,signal,subprocess,time
import psutil
CPU=600.;WALL=1200.;RESERVE=180.;RSS=2147483648;STORAGE=1073741824
EXPERIMENT='B-TABICLV2-CMP-DIRECT-PILOT-v1'
def utc():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def atomic(path,value):
 tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(value,indent=2)+'\n');os.chmod(tmp,0o600);os.replace(tmp,path)
def size(root):return sum(p.stat().st_size for p in root.rglob('*')if p.is_file()and not p.is_symlink())if root.exists()else 0
def main():
 p=argparse.ArgumentParser();p.add_argument('--state-dir',type=pathlib.Path,required=True);p.add_argument('--runtime',type=pathlib.Path,required=True);p.add_argument('--stage',required=True);p.add_argument('--completion',action='store_true');p.add_argument('--canary',action='store_true');p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args();a.state_dir.mkdir(parents=True,exist_ok=True);os.chmod(a.state_dir,0o700);path=a.state_dir/'RESOURCE_LEDGER.json'
 if path.exists():d=json.loads(path.read_text())
 else:
  d=dict(experiment=EXPERIMENT,grant='EXECUTION-AUTHORIZATION-02',started_UTC=utc(),started_epoch=time.time(),CPU_seconds=0.434595710,known_preparation_CPU_seconds=0.434595710,CPU_cap=CPU,wall_cap=WALL,completion_CPU_reserve=RESERVE,completion_wall_reserve=RESERVE,stages=[],unmetered='Prior failed preparation/import/tool/orchestration and review/search tails not completely metered; known charges carried, no complete-total assertion.');atomic(path,d)
 if d['experiment']!=EXPERIMENT or any(x['stage']==a.stage for x in d['stages']):raise ValueError('No duplicate stage/reset under this cumulative grant')
 reserve=0 if a.completion else RESERVE;elapsed=time.time()-d['started_epoch'];cpu_before=d['CPU_seconds']
 if cpu_before>=CPU-reserve or elapsed>=WALL-reserve:raise RuntimeError('Complete stage and reserves cannot fit')
 command=a.command[1:]if a.command[:1]==['--']else a.command
 if not command:raise ValueError('Explicit bounded command required')
 a.runtime.mkdir(parents=True,exist_ok=True);os.chmod(a.runtime,0o700)
 env=dict(os.environ);env.update(OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2',MKL_NUM_THREADS='2',NUMEXPR_NUM_THREADS='2',VECLIB_MAXIMUM_THREADS='2',TOKENIZERS_PARALLELISM='false',HF_HUB_OFFLINE='1',HF_DATASETS_OFFLINE='1',PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1',PIP_NO_CACHE_DIR='1',TMPDIR=str(a.runtime/'tmp'),XDG_CACHE_HOME=str(a.runtime/'cache'),HF_HOME=str(a.runtime/'hf'))
 for name in ('tmp','cache','hf'):(a.runtime/name).mkdir(exist_ok=True)
 logpath=a.state_dir/(a.stage+'.log');start=time.monotonic();ru=resource.getrusage(resource.RUSAGE_CHILDREN);own=time.process_time();peak=0;peakstorage=size(a.runtime);reason=None;lastcpu=0.
 with logpath.open('w')as log:
  child=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True);proc=psutil.Process(child.pid)
  while child.poll()is None:
   processes=[]
   try:processes=[proc]+proc.children(recursive=True)
   except psutil.NoSuchProcess:pass
   active=0.;rss=0
   for q in processes:
    try:t=q.cpu_times();active+=t.user+t.system;rss+=q.memory_info().rss
    except (psutil.NoSuchProcess,psutil.AccessDenied):pass
   lastcpu=max(lastcpu,active);peak=max(peak,rss);peakstorage=max(peakstorage,size(a.runtime))
   spent=time.process_time()-own+lastcpu
   if cpu_before+spent>=CPU-reserve:reason='CUMULATIVE_CPU_COMPLETION_RESERVE'
   elif a.canary and spent>=90.:reason='FIRST_ORIGIN_CANARY_CPU90'
   elif time.time()-d['started_epoch']>=WALL-reserve:reason='CUMULATIVE_WALL_COMPLETION_RESERVE'
   elif peak>RSS:reason='RSS2GIB_LIMIT'
   elif peakstorage>STORAGE:reason='TOTAL_RUNTIME_STORAGE1GIB_LIMIT'
   if reason:
    try:os.killpg(child.pid,signal.SIGTERM)
    except ProcessLookupError:pass
    try:child.wait(timeout=1)
    except subprocess.TimeoutExpired:
     try:os.killpg(child.pid,signal.SIGKILL)
     except ProcessLookupError:pass
    break
   time.sleep(.1)
  code=child.wait()
 end=resource.getrusage(resource.RUSAGE_CHILDREN);childcpu=end.ru_utime+end.ru_stime-ru.ru_utime-ru.ru_stime;stagecpu=max(lastcpu,childcpu)+time.process_time()-own;d['CPU_seconds']+=stagecpu;d['wall_seconds']=time.time()-d['started_epoch'];row=dict(stage=a.stage,UTC=utc(),CPU_seconds=stagecpu,wall_seconds=time.monotonic()-start,peak_aggregate_RSS_bytes=peak,peak_runtime_storage_bytes=peakstorage,returncode=code,stop_reason=reason,state='PASS'if code==0 and reason is None else'SAFE_STOP_OR_FAILURE');d['stages'].append(row);atomic(path,d)
 print(json.dumps(dict(row,cumulative_CPU=d['CPU_seconds'],cumulative_wall=d['wall_seconds'],CPU_remaining=CPU-d['CPU_seconds'],wall_remaining=WALL-d['wall_seconds'])));raise SystemExit(0 if row['state']=='PASS'else 2)
if __name__=='__main__':main()
