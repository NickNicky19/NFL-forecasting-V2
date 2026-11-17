"""Lossless retained-output packaging after an aggregate-size guard.

No model, prediction, grading, selector, probability or canonical row is changed.
The original failed output is retained locally and as an exact public capsule.
The original8MiB cap remains in force for the new complete representation.
"""
import argparse,datetime,gzip,hashlib,io,json,resource,shutil,tarfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'reports/information-skill-01/B'
def digest(b):return hashlib.sha256(b).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--original-retention-dir',type=Path,required=True);args=parser.parse_args()
 if args.original_retention_dir.resolve().is_relative_to(ROOT):raise ValueError('Owner-local original retention must be outside publicGit')
 start=time.monotonic();cpu=time.process_time();old=BASE/'evaluation-v1';new=BASE/'evaluation-v2';ret=BASE/'retention/failed-evaluation-v1'
 if new.exists()or ret.exists():raise FileExistsError('Preserve prior attempts; no overwrite')
 files=sorted(p for p in old.iterdir()if p.is_file());original={p.name:p.read_bytes()for p in files};cap=8388608;oldbytes=sum(map(len,original.values()))
 if oldbytes<=cap:raise ValueError('Expected original guarded failure')
 ret.mkdir(parents=True);new.mkdir();members=[]
 for name,data in original.items():
  dest=name+'.gz'if name=='PAIRED_COMPARISONS_V1.json'else name
  encoded=gzip.compress(data,compresslevel=9,mtime=0)if dest!=name else data
  (new/dest).write_bytes(encoded)
  recovered=gzip.decompress(encoded)if dest!=name else encoded
  if recovered!=data:raise ValueError('Lossless decoded-byte identity failed')
  json.loads(gzip.decompress(data)if name.endswith('.gz')else data)
  members.append(dict(original_path='evaluation-v1/'+name,original_bytes=len(data),original_sha256=digest(data),new_path='evaluation-v2/'+dest,new_bytes=len(encoded),new_sha256=digest(encoded),recovered_original_bytes_identical=True))
 manifest=dict(id='B_INFORMATION_SKILL_FAILED_EVAL_EXACT_BYTES_v1',failure='8MiB aggregate output cap, after calculations before final receipt; not a model or score failure',original_bytes=oldbytes,cap=cap,members=members)
 mb=(json.dumps(manifest,indent=2)+'\n').encode();(ret/'MANIFEST.json').write_bytes(mb);buf=io.BytesIO()
 with gzip.GzipFile(fileobj=buf,mode='wb',mtime=0)as gz:
  with tarfile.open(fileobj=gz,mode='w')as t:
   for name,data in original.items():
    info=tarfile.TarInfo('evaluation-v1/'+name);info.size=len(data);info.mode=0o644;info.mtime=0;t.addfile(info,io.BytesIO(data))
   info=tarfile.TarInfo('MANIFEST.json');info.size=len(mb);info.mode=0o644;info.mtime=0;t.addfile(info,io.BytesIO(mb))
 (ret/'ORIGINAL_FAILED_OUTPUTS.tar.gz').write_bytes(buf.getvalue())
 scores=json.loads(original['SCORES.json']);assert digest((new/'SCORES.json').read_bytes())==digest(original['SCORES.json'])
 read=lambda name:json.loads(gzip.decompress(original[name])if name.endswith('.gz')else original[name])
 tables=read('MAIN_TABLES_V1.json.gz');selective=read('SELECTIVE_TABLES_V1.json.gz');broad=read('BROAD_NUMERICAL_TABLES_V1.json.gz');proper=read('PROBABILITY_TABLES_V1.json.gz');pairs=read('PAIRED_COMPARISONS_V1.json')
 identity={'id':'B_INFORMATION_SKILL_LOSSLESS_EVALUATION_REPRESENTATION_v1','UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'state':'LOSSLESS_REPACK_WITH_CAP_UNCHANGED;NO_RESCORING','original_failure_bytes':oldbytes,'unchanged_cap':cap,'original_manifest':str((ret/'MANIFEST.json').relative_to(ROOT)),'original_capsule':str((ret/'ORIGINAL_FAILED_OUTPUTS.tar.gz').relative_to(ROOT)),'original_capsule_sha256':digest(buf.getvalue()),'decoded_identity_verified_files':len(members),'all_original_decoded_bytes_identical':True,'canonical_SCORES_sha256':digest(original['SCORES.json']),'canonical_records':len(scores),'changed_scientific_rows':0,'new_grading_runs':0,'new_fits':0,'compressed_file_only':'PAIRED_COMPARISONS_V1.json -> .json.gz','members':members}
 save(new/'LOSSLESS_REPRESENTATION_RECEIPT_V1.json',identity)
 receipt=dict(state='EXECUTED_SKILL_LOCAL_NOT_C_ADMITTED;OUTPUT_PRESERVING_REPRESENTATION_REPAIR',at_UTC=identity['UTC'],models=['SKILL_C0','SKILL_C1','SKILL_R0','SKILL_R1'],native_CMP_offers=142,actual_offer_weeks=[5,6,7,8,9],missing_offer_weeks=[1,2,3,4],numeric_weeks=list(range(1,10)),native_games=71,main_views=len(tables),selective_views=len(selective),broad_numeric_views=len(broad),proper_probability_views=len(proper),canonical_views=len(scores),paired_views=len(pairs),own_list_comparisons=len(read('OWN_LIST_COMPARISONS_V1.json')),frozen_policy_count_per_method=19,CPU_seconds=None,original_score_CPU='Actual sample unavailable: original guard tested processCPU<600 andwall<900 before writes; no invented CPU. Conservatively charge600seconds plus explicit unmetered write/qualification tail. No scorer rerun.',CPU_conservative_charge_seconds=600,original_timing_limitation='The completed calculations emitted all bound aggregates, then size guard stopped before RUN_RECEIPT. Encoding repair preserves all originalbytes; no auto cap extension.',repack_CPU_seconds=time.process_time()-cpu,repack_wall_seconds=time.monotonic()-start,source_reads_by_execution=0,new_fits=0,new_NFL_observations=0,original_pregame_selections=0,private_restricted_rows_written=0,code_sha256=read('EXECUTION_INPUT_BINDINGS_V1.json')['code_sha256'],evidence='Retained real-lines current-vintage7day diagnostic; quoteclocks/main-altunknown; not originalissuance',C_or_website_admission=False,decoded_equivalence_receipt='LOSSLESS_REPRESENTATION_RECEIPT_V1.json',public_bytes_before_final_receipt=sum(p.stat().st_size for p in new.iterdir()if p.is_file()))
 save(new/'RUN_RECEIPT_V1.json',receipt)
 newbytes=sum(p.stat().st_size for p in new.iterdir()if p.is_file());assert newbytes<=cap
 # Retain the untouched original directory outside public Git; exact capsule stays public.
 private=args.original_retention_dir
 if private.exists():raise FileExistsError('Original private retention destination exists')
 private.parent.mkdir(parents=True,exist_ok=True);shutil.move(str(old),str(private));old.mkdir()
 save(old/'GUARD_FAILURE_AND_RETENTION_V1.json',dict(state='ORIGINAL_SIZE_GUARD_FAILURE_PRESERVED',original_bytes=oldbytes,unchanged_cap=cap,exact_public_capsule=str((ret/'ORIGINAL_FAILED_OUTPUTS.tar.gz').relative_to(ROOT)),capsule_sha256=digest(buf.getvalue()),lossless_current_representation='evaluation-v2',new_public_bytes=newbytes,no_rescoring=True,original_source_CPU_unknown=True))
 print(json.dumps(dict(state='LOSSLESS_CAP_PRESERVING_REPRESENTATION_COMPLETE',original_bytes=oldbytes,cap=cap,new_bytes=newbytes,canonical_records=len(scores),decoded_identical=True,new_fits=0,new_scoring_runs=0,repack_CPU_seconds=time.process_time()-cpu)))
if __name__=='__main__':main()
