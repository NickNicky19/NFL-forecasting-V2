"""Bounded immutable GitHub retention for public-safe comparison derivatives."""
import argparse, datetime, gzip, hashlib, io, json, pathlib, tarfile, urllib.request

ROOT=pathlib.Path(__file__).resolve().parents[1]
BASE=ROOT/'reports/w1w9-comparison-closure-01/B'
REPO='NickNicky19/NFL-forecasting-V2'
def sha(b):return hashlib.sha256(b).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True,allow_nan=False)+'\n')
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()

def build():
    excluded={'PUBLICATION_CAPSULE_V1.tar.gz','PUBLICATION_MANIFEST_V1.json','PUBLICATION_READBACK_V1.json','PUBLICATION_READ_ATTEMPTS_V1.jsonl','METADATA_READBACK_V1.json','FINAL_CI_RECEIPT_V1.json'}
    paths=[p for p in BASE.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name not in excluded and p.suffix!='.pyc']
    paths += [ROOT/p for p in ['tools/assemble_w1w9_completion.py','tools/extend_existing_qb_origins_w9.py','tools/register_w1w9_closure_20261114.py','tools/publish_w1w9_closure.py','registries/RESULT_ARTIFACTS.json','registries/ANALYSIS_ARTIFACTS.json','registries/CURRENT_RESULTS_INDEX.json','START_HERE.md','TASK_LEDGER.md']]
    extra=ROOT/'tools/register_w1w9_att_supplement_20261114.py'
    if extra.exists():paths.append(extra)
    members=[];buffer=io.BytesIO()
    with tarfile.open(fileobj=buffer,mode='w',format=tarfile.PAX_FORMAT)as tar:
        for p in sorted(set(paths)):
            data=p.read_bytes();name=str(p.relative_to(ROOT));info=tarfile.TarInfo(name);info.size=len(data);info.mtime=0;info.mode=0o644
            tar.addfile(info,io.BytesIO(data));members.append({'path':name,'bytes':len(data),'sha256':sha(data)})
    data=gzip.compress(buffer.getvalue(),compresslevel=9,mtime=0);capsule=BASE/'PUBLICATION_CAPSULE_V1.tar.gz';capsule.write_bytes(data)
    public_bytes=sum(p.stat().st_size for p in BASE.rglob('*') if p.is_file() and '__pycache__'not in p.parts)
    assert public_bytes<33554432,(public_bytes,'Public package cap')
    manifest={'id':'B_W1W9_PUBLICATION_MANIFEST_v1','capsule':str(capsule.relative_to(ROOT)),'sha256':sha(data),'bytes':len(data),'members':members,'public_package_bytes':public_bytes,
      'rights':'Own public-safe code, aggregates, source bindings and trusted JSON derivatives; FTN Data via nflverse CC-BY-SA-4.0, ordinary nflverse statistics separate CC-BY-4.0. No protected raw offers/rosters/private locators/credentials.',
      'admission':'LOCAL_B_NOT_C_ADMITTED_OR_ORIGINAL_SITE_ACTIVATION','time_semantics':'Retrospective current-vintage diagnostics; real retained source lines with quote clocks and main-alt unresolved. No original future picks.'}
    save(BASE/'PUBLICATION_MANIFEST_V1.json',manifest)
    print(json.dumps({'capsule_bytes':len(data),'members':len(members),'public_bytes':public_bytes}))

def get(url):
    log=BASE/'PUBLICATION_READ_ATTEMPTS_V1.jsonl'
    attempts=log.read_text().splitlines() if log.exists() else []
    assert len(attempts)<12,'Final publication read budget exhausted; do not retry'
    with log.open('a')as f:f.write(json.dumps({'attempt':len(attempts)+1,'UTC':now(),'url':url})+'\n')
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'B-bounded-research-retention'}),timeout=30)as r:return r.read()

def readback(commit):
    root=f'https://raw.githubusercontent.com/{REPO}/{commit}/';mp=BASE/'PUBLICATION_MANIFEST_V1.json'
    mb=get(root+str(mp.relative_to(ROOT)));assert mb==mp.read_bytes();m=json.loads(mb)
    data=get(root+m['capsule']);assert len(data)==m['bytes']and sha(data)==m['sha256']
    with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz')as tar:
        entries=tar.getmembers();assert len(entries)==len(m['members']);by={z.name:z for z in entries}
        assert len(by)==len(entries)
        for r in m['members']:
            member=by[r['path']];assert member.isfile();b=tar.extractfile(member).read()
            assert len(b)==r['bytes']and sha(b)==r['sha256']
            assert (ROOT/r['path']).read_bytes()==b
    receipt={'id':'B_W1W9_PUBLICATION_READBACK_v1','state':'EXACT_IMMUTABLE_CAPSULE_AND_ALL_MEMBERS_VERIFIED','at_UTC':now(),'producer_commit':commit,'repository':REPO,'manifest_sha256':sha(mb),'capsule_sha256':sha(data),'members_verified':len(m['members']),'HTTP_GETs':2,'individual_member_raw_URL_GETs':0,'method':'DIRECT_IMMUTABLE_RAW_MANIFEST_AND_CAPSULE;READ_EACH_MEMBER_WITHOUT_EXTRACTION','C_receipt':False,'consumer_receipt':False,'production_activation':False}
    save(BASE/'PUBLICATION_READBACK_V1.json',receipt);print(json.dumps(receipt))

def exports(commit):
    path=ROOT/'reports/abc-championship/EXPORT_INDEX.json';old=path.read_bytes();x=json.loads(old);prior=BASE/'PREVIOUS_EXPORT_INDEX_V23.json.gz'
    if not prior.exists():prior.write_bytes(gzip.compress(old,compresslevel=9,mtime=0))
    else:assert json.loads(gzip.decompress(prior.read_bytes()))['exports']==x['exports'][:1698]
    m=json.loads((BASE/'PUBLICATION_MANIFEST_V1.json').read_bytes());r=json.loads((BASE/'PUBLICATION_READBACK_V1.json').read_bytes());assert r['producer_commit']==commit
    assert len(x['exports'])==1698,'Do not duplicate publication entries'
    for z in m['members']+[{'path':str((BASE/'PUBLICATION_CAPSULE_V1.tar.gz').relative_to(ROOT)),'bytes':m['bytes'],'sha256':m['sha256']}]:
        entry={'artifact_id':'B-EXPORT-'+sha((commit+':'+z['path']).encode())[:16],**z,'producer_commit':commit,'retrieval_url':f'https://raw.githubusercontent.com/{REPO}/{commit}/'+z['path'],
          'readback_verified':True,'readback_UTC':r['at_UTC'],'readback_method':'EXACT_IMMUTABLE_CAPSULE_MEMBER_BYTES'if z['path']!=m['capsule']else'DIRECT_IMMUTABLE_RAW_URL_BYTES','individual_raw_URL_GET':z['path']==m['capsule'],
          'kind':'FROZEN_W1_W9_B_CONTRIBUTION_EXISTING_PROCEDURES','rights':m['rights'],'retention':'IMMUTABLE_GITHUB_READBACK','admission':m['admission'],'periods':'2026W1–9fixed226completiondiagnostic;nativeW5–9completion/attemptpanels;othercategoriesremainpartial'}
        x['exports'].append(entry)
    x.update(schema_version='B-ABC-EXPORT-INDEX-v24',at_utc=now(),canonical_state='C_COORDINATED_W1W9_COMPARISON_B_FIXED226_COMPLETE_WITHIN_SCOPE_GLOBAL_ALL_CANDIDATES_PARTIAL_NO_ACTIVATION')
    x['w1w9_comparison_closure_20261114']={'producer_commit':commit,'report':'reports/w1w9-comparison-closure-01/B/README.md','manifest':'reports/w1w9-comparison-closure-01/B/PUBLICATION_MANIFEST_V1.json','readback':'reports/w1w9-comparison-closure-01/B/PUBLICATION_READBACK_V1.json','scope':'Exact nine-week compatible diagnostic for complete B completion products; private A early aggregate commitments, not private-row verification. A later controls and C consolidated intake outstanding. Native ATT kept separate from old annual87. No new original selections or production admission.','C_admission':'NOT_OBSERVED_FOR_THIS_NEW_PACKAGE','old_exports_preserved':1698,'new_exports':len(m['members'])+1}
    save(path,x);print(json.dumps({'old':1698,'new':len(m['members'])+1,'all':len(x['exports'])}))

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('action',choices=['build','readback','exports']);a.add_argument('--commit');p=a.parse_args()
    if p.action=='build':build()
    elif p.action=='readback':readback(p.commit)
    else:exports(p.commit)
