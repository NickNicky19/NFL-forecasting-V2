"""Independent synthetic/statical review of recovery adapter; no remote transfer."""
import copy,hashlib,importlib.util,io,json,os,tarfile,tempfile
from datetime import datetime,timezone
from pathlib import Path
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[2]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run():
 p=HERE.parent/'recovery-preflight/VERIFY_FRESH_ARCHIVES.py';spec=importlib.util.spec_from_file_location('independent_restore_target',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 checks=[]
 def ok(name,fn):fn();checks.append({'check':name,'pass':True})
 def reject(name,fn):
  try:fn()
  except (ValueError,KeyError):checks.append({'check':name,'pass':True});return
  raise AssertionError('expected rejection: '+name)
 with tempfile.TemporaryDirectory(prefix='k-restore-independent-')as d:
  root=Path(d);fresh=root/'fresh';fresh.mkdir();payload=b'preserved evidence\n';digest=hashlib.sha256(payload).hexdigest();marker='REQUIRED_FILES_PRIVATE.json';mapblob=b'{"synthetic":true}'
  def tar(path,entries):
   with tarfile.open(path,'w:gz')as t:
    for name,b in entries:
     z=tarfile.TarInfo(name);z.size=len(b);t.addfile(z,io.BytesIO(b))
  good=root/'good.tar.gz';tar(good,[('blobs/'+digest,payload),(marker,mapblob)])
  def positive_catalog():
   cat,obj,blob=m.catalog(good,delta=True);assert cat['blobs/'+digest]==(digest,len(payload))and obj=={'synthetic':True}and blob==mapblob
  ok('delta stream hashes every member and exact compact manifest',positive_catalog)
  for label,entries in [('wrong content address',[('blobs/'+'0'*64,payload),(marker,mapblob)]),('duplicate member',[('blobs/'+digest,payload),('blobs/'+digest,payload),(marker,mapblob)]),('parent traversal',[('../blobs/'+digest,payload),(marker,mapblob)]),('absolute member',[('/blobs/'+digest,payload),(marker,mapblob)]),('missing manifest',[('blobs/'+digest,payload)])]:
   path=root/(label.replace(' ','_')+'.tar.gz');tar(path,entries);reject('reject '+label,lambda path=path:m.catalog(path,delta=True))
  wire=good.read_bytes();split=len(wire)//2;parts=[wire[:split],wire[split:]];meta={'parts':[],'archive_bytes':len(wire),'archive_sha256':hashlib.sha256(wire).hexdigest()};actual=[]
  for i,b in enumerate(parts):
   f=fresh/f'p{i}';f.write_bytes(b);meta['parts'].append({'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)});actual.append({'workspace_path':str(f)})
  target=root/'assembled.tar.gz'
  def positive_assembly():m.assemble_delta(meta,actual,target);assert target.read_bytes()==wire
  ok('exact ordered part assembly and whole hash',positive_assembly)
  reject('reject overwrite of assembled file',lambda:m.assemble_delta(meta,actual,target))
  bad=copy.deepcopy(meta);bad['parts'][0]['sha256']='0'*64;reject('reject changed part hash',lambda:m.assemble_delta(bad,actual,root/'bad-assembled.tar.gz'))
  source=root/'source.json';source.write_text('{"fixture":true}');queue={'parts':[]};records=[]
  for i,entry in enumerate(actual):
   queue['parts'].append({'artifact_id':'FIXTURE','index':i,'sha256':meta['parts'][i]['sha256'],'bytes':meta['parts'][i]['bytes'],'provider_reference':{'provider_object_id':f'fixture-{i}'}})
   records.append(dict(entry,index=i,status='DOWNLOADED',unshared=True,provider_object_id=f'fixture-{i}',source_receipt={'path':str(source),'sha256':sha(source)}))
  ok('complete fresh private provenance-bound local part records',lambda:m.fresh_downloads('FIXTURE',meta,queue,records,fresh))
  bad=copy.deepcopy(records);bad[0]['unshared']=False;reject('reject public or unknown part privacy',lambda:m.fresh_downloads('FIXTURE',meta,queue,bad,fresh))
  bad=copy.deepcopy(records);bad[0]['provider_object_id']='different';reject('reject wrong upload object',lambda:m.fresh_downloads('FIXTURE',meta,queue,bad,fresh))
  bad=copy.deepcopy(records);bad[0]['source_receipt']['sha256']='0'*64;reject('reject changed source receipt',lambda:m.fresh_downloads('FIXTURE',meta,queue,bad,fresh))
  reject('reject incomplete fresh part census',lambda:m.fresh_downloads('FIXTURE',meta,queue,records[:-1],fresh))
  reject('reject original area substituted for fresh part area',lambda:m.fresh_downloads('FIXTURE',meta,queue,records,root/'other-fresh'))
  canonical_marker='__V2_PRIVATE_MEMBERS__.json';canonical_manifest=json.dumps({'members':[{'name':'data','bytes':len(payload),'sha256':digest}]}).encode();canonical=root/'canonical.tar.gz';tar(canonical,[('data',payload),(canonical_marker,canonical_manifest)])
  ok('canonical archive exact manifest and payload census',lambda:m.catalog(canonical,delta=False))
  extra=root/'extra.tar.gz';tar(extra,[('data',payload),('extra',payload),(canonical_marker,canonical_manifest)]);reject('reject unlisted canonical payload',lambda:m.catalog(extra,delta=False))
 plan,prior=m.fixed_inputs();assert len(prior)==20;checks.append({'check':'all four public frozen bindings and20 affirmative prior object proofs revalidated','pass':True})
 encoding=m.read(m.BASE/'RECOVERY_MAP_ENCODING_INDEPENDENT_READBACK.json');assert encoding['semantic_objects_identical']is True and encoding['archive_map_member_sha256']!=encoding['external_private_map_sha256'];checks.append({'check':'compact and pretty map hashes are explicitly distinct and pinned','pass':True})
 out={'state':'PASS_STATIC_AND_SYNTHETIC_RESTORE_ADAPTER_NOT_ACTUAL_RESTORATION','at_utc':datetime.now(timezone.utc).isoformat(),'adapter_sha256':sha(p),'unchanged_canonical_verifier_sha256':sha(REPO/'tools/private_bundle.py'),'unchanged_gate_sha256':sha(REPO/'nfl_v2/expanded_retention_gate.py'),'checks':checks,'checks_passed':len(checks),'real_NFL_payloads_decoded':0,'remote_transfers':0,'original_or_fresh_private_archives_reassembled_in_this_check':0,'inner_files_extracted':0,'new_fits_or_inference':0,'gate_cleared':False,'qualification':'Synthetic fixtures check branch behavior only. Actual64 approved-object fetch/visibility/source-receipt chains, whole archives and all member joins require the subsequent separately reviewed restoration receipts. Positive inherited20 objects remain inherited, not newly downloaded.'}
 with(HERE/'RESTORE_ADAPTER_STATIC_AND_FIXTURE_REVIEW.json').open('x')as f:json.dump(out,f,indent=2);f.write('\n')
 print(json.dumps({'state':out['state'],'checks_passed':len(checks),'adapter_sha256':out['adapter_sha256']}))
if __name__=='__main__':run()
