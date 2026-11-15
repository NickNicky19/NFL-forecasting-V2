"""Readback-bound public-safe retention; metadata is not model admission."""
import argparse,datetime,gzip,hashlib,io,json,pathlib,tarfile,urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[1]
BASE=ROOT/'reports/targeted-accuracy-w1w9-01/B'
def sha(b):return hashlib.sha256(b).hexdigest()
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def build(phase):
    dest=BASE/'retention'/phase;dest.mkdir(parents=True,exist_ok=False)
    if phase=='prefit-v1':
        files=[ROOT/'nfl_v2/targeted_qb_m2.py',ROOT/'tools/run_targeted_qb_m2.py',pathlib.Path(__file__),
          BASE/'wave-v1/FROZEN_PROTOCOL_V1.json',BASE/'wave-v1/ENVIRONMENT_V1.json',BASE/'ADOPTION_AND_BUDGET_V1.json',
          BASE/'evaluation/FROZEN_EVALUATION_PROTOCOL_V1.json']
        files+=list((BASE/'prior-source').glob('*'))+[f for f in(BASE/'independent').glob('PREFIT*.json')]
    elif phase=='pilot-v1':
        files=list((BASE/'wave-v1').rglob('*'))+[ROOT/'nfl_v2/targeted_qb_m2.py',ROOT/'tools/run_targeted_qb_m2.py',pathlib.Path(__file__)]
        files += list((BASE/'independent').glob('*SOFTWARE*.json'))
    else:
        files=list(BASE.rglob('*'))+[ROOT/'nfl_v2/targeted_qb_m2.py',ROOT/'tools/run_targeted_qb_m2.py',pathlib.Path(__file__)]
        files += [ROOT/p for p in ['registries/RESULT_ARTIFACTS.json','registries/ANALYSIS_ARTIFACTS.json','registries/CURRENT_RESULTS_INDEX.json','START_HERE.md','TASK_LEDGER.md']]
        helper=ROOT/'tools/register_targeted_m2.py'
        if helper.exists():files.append(helper)
    files += [ROOT/'reports/information-first-20261112-01/B/completion-wave-v1/QB_CONTEXT_W1_W9_INPUTS_V1.json.gz',
              ROOT/'reports/player-context-completion-decision-01/B/source-depth-v1/FTN_DEPTH_QB_GAME_INPUTS.json.gz']
    files=[f for f in sorted(set(files))if f.is_file()and'__pycache__'not in f.parts and 'retention'not in f.relative_to(BASE).parts if f.is_relative_to(BASE)] if False else files
    selected=[]
    for f in sorted(set(files)):
        if not f.is_file()or'__pycache__'in f.parts or f.suffix=='.pyc':continue
        if f.is_relative_to(BASE/'retention'):continue
        selected.append(f)
    buf=io.BytesIO();members=[]
    with tarfile.open(fileobj=buf,mode='w')as t:
        for f in selected:
            b=f.read_bytes();name=str(f.relative_to(ROOT));i=tarfile.TarInfo(name);i.size=len(b);i.mtime=0;i.mode=0o644;t.addfile(i,io.BytesIO(b));members.append(dict(path=name,bytes=len(b),sha256=sha(b)))
    b=gzip.compress(buf.getvalue(),compresslevel=9,mtime=0);cp=dest/'CAPSULE.tar.gz';cp.write_bytes(b)
    total=sum(f.stat().st_size for f in BASE.rglob('*')if f.is_file()and'__pycache__'not in f.parts)
    assert total<33554432,(total,'Registeredpublicbytecap')
    m=dict(id='B_M2_RETENTION_'+phase,state='BUILT_BEFORE_PHASE_EXECUTION_OR_FINAL_PUBLICATION',capsule=str(cp.relative_to(ROOT)),sha256=sha(b),bytes=len(b),members=members,
      public_bytes=total,rights='Public-safeQBstatisticalderivatives and trustedJSON models; FTN Data via nflverse CC-BY-SA4.0 chartderivatives; ordinarynflverseCC-BY4.0. No protectedraw offer/roster/private locator/secret.',
      scientific_admission='LOCAL_NOT_C_ADMITTED;NO_ORIGINAL_SITE_CHANGE')
    save(dest/'MANIFEST.json',m);print(json.dumps({'phase':phase,'members':len(members),'bytes':len(b),'total_public':total}))
def readback(phase,commit):
    dest=BASE/'retention'/phase;log=BASE/'retention/READ_ATTEMPTS.jsonl'
    records=[json.loads(x)for x in log.read_text().splitlines()]if log.exists()else[]
    category='prefit'if phase in('prefit-v1','pilot-v1')else'final'
    count=sum(r['category']==category for r in records);cap=6 if category=='prefit'else 12
    def get(path):
        nonlocal count
        assert count<cap,'Registeredreadbackbudget';count+=1
        url=f'https://raw.githubusercontent.com/NickNicky19/NFL-forecasting-V2/{commit}/{path}'
        with log.open('a')as f:f.write(json.dumps(dict(UTC=now(),category=category,phase=phase,url=url,attempt=count))+'\n')
        with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'B-bounded-M2-retention'}),timeout=30)as r:return r.read()
    mp=dest/'MANIFEST.json';mb=get(str(mp.relative_to(ROOT)));assert mb==mp.read_bytes();m=json.loads(mb);b=get(m['capsule']);assert sha(b)==m['sha256']and len(b)==m['bytes']
    with tarfile.open(fileobj=io.BytesIO(b),mode='r:gz')as t:
        by={z.name:z for z in t.getmembers()};assert len(by)==len(m['members'])
        for z in m['members']:
            member=by[z['path']];assert member.isfile();data=t.extractfile(member).read();assert sha(data)==z['sha256']and len(data)==z['bytes'];assert data==(ROOT/z['path']).read_bytes()
    receipt=dict(state='EXACT_GITHUB_IMMUTABLE_CAPSULE_AND_ALL_MEMBERS_READBACK',UTC=now(),phase=phase,commit=commit,members=len(m['members']),manifest_sha256=sha(mb),capsule_sha256=sha(b),HTTP_GETs=2,category_attempts_so_far=count,member_individual_raw_URL_GETs=0,C_receipt=False,original_site_use=False)
    save(dest/'READBACK.json',receipt);print(json.dumps(receipt))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['build','readback']);p.add_argument('phase');p.add_argument('--commit');a=p.parse_args()
    if a.action=='build':build(a.phase)
    else:readback(a.phase,a.commit)
