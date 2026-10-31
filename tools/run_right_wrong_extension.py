"""Finite source adapter to the SAME frozen K diagnostic engine; no new metric math."""
import argparse,gzip,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools import run_right_wrong_diagnostic as engine
from nfl_v2 import right_wrong_diagnostic as diagnostic,scoring
from nfl_v2.shared_subgroups import canonical,sha,write,now

VERSION='v2-right-wrong-diagnostic-stage-b-v1'

def load_extension_rows(path,root_protocol,roster_path):
 grid=json.loads(roster_path.read_bytes());allowed={tuple(r['recipe'])for r in grid if r['status']=='REPLAYABLE_FROZEN_EXACT_SAVED_ROWS'};groups={r:{}for r in allowed};duplicates=0
 for row in json.loads(gzip.decompress(path.read_bytes()))['rows']:
  key=tuple(row['recipe'])
  if key not in allowed:raise ValueError('normalized row outside frozen finite extension roster')
  q=engine.row_key(row)
  if q in groups[key]:
   if groups[key][q]!=row:raise ValueError('conflicting repeated source rows')
   duplicates+=1
  groups[key][q]=row
 if any(not r for r in groups.values()):raise ValueError('frozen extension recipe absent')
 return groups,duplicates

def setup(a):
 engine.VERSION=VERSION
 engine.load_rows=lambda path,root_protocol:load_extension_rows(path,root_protocol,a.roster)
 original_write=engine.write
 def stage_write(path,obj):
  # Source-binding metadata only. All bucket/band mathematics stay in oneengine.
  if Path(path).name=='RUN_RECEIPT.json':obj=dict(obj,private_artifact_id='K-STAGE-B-ROWS-EXAMPLES-V1',stage='B',metadata_preflight_sha256=sha(a.preflight),extension_roster_sha256=sha(a.roster))
  return original_write(path,obj)
 engine.write=stage_write

def prepare(a):
 if a.output.exists()or a.private_output.exists():raise ValueError('fresh extension outputs required')
 pre=json.loads(a.preflight.read_bytes());rp=json.loads(a.root_protocol.read_bytes())
 if sha(a.roster)!=pre['roster_sha256']or sha(a.input)!=pre['normalized_input_sha256']:raise ValueError('frozen metadata/input changed')
 groups,duplicates=load_extension_rows(a.input,rp,a.roster);lineage=a.root/'reports/right-and-wrong-diagnostic-20261031k/lineage/INSPECT_RETAINED_LINEAGE.py';a.output.mkdir(parents=True);a.private_output.mkdir(parents=True)
 p=dict(version=VERSION,state='FROZEN_BEFORE_NEW_EXTENSION_BUCKET_AND_BAND_METRICS',at=now(),root_protocol_path=a.root_protocol.relative_to(a.root).as_posix(),root_protocol_sha256=sha(a.root_protocol),source_artifact_id='K-STAGE-B-NORMALIZED-EXTENSION-INPUT-V1',source_sha256=sha(a.input),source_bytes=a.input.stat().st_size,metadata_preflight_sha256=sha(a.preflight),extension_roster_sha256=sha(a.roster),code_sha256=sha(engine.__file__),adapter_sha256=sha(__file__),core_sha256=sha(diagnostic.__file__),grader_sha256=sha(scoring.__file__),lineage_helper_path=lineage.relative_to(a.root).as_posix(),lineage_helper_sha256=sha(lineage),lineage_protocol_sha256=sha(lineage.parent/'FROZEN_LINEAGE_PROTOCOL.json'),realized_context_helper_sha256=sha(lineage.parent/'REALIZED_CONTEXT_LOOKUP.py'),realized_context_admission_sha256=sha(lineage.parent/'POSTGAME_CONTEXT_ADMISSION.json'),tolerances=rp['tolerances'],roster=[dict(recipe=list(k),outer_rows=len(rows),preoutcome_membership_sha256=hashlib.sha256(canonical(sorted(engine.row_key(r)for r in rows.values()))).hexdigest())for k,rows in sorted(groups.items())],reused_stage_A_cells=pre['reused_stage_A_cells'],diagnostic_only=True,default_rank_eligible=False,membership='Outcome-conditionedexplanatory groups; notselectablepregamecohorts',control_scope=pre['control_mask_rule'],metadata_adapter='ImportsunchangedStageAengine; substitutes only pre-frozen exactsource loader/version/receiptartifactlabel. All metricmath shared withStageA.',budget=rp['budget'])
 write(a.output/'FROZEN_PROTOCOL.json',p);(a.output/'ADAPTER_SOURCE_SNAPSHOT.py').write_bytes(Path(__file__).read_bytes());(a.output/'SHARED_EXECUTOR_SOURCE_SNAPSHOT.py').write_bytes(Path(engine.__file__).read_bytes());print(json.dumps(dict(protocol_sha256=sha(a.output/'FROZEN_PROTOCOL.json'),new_recipe_target_outputs=len(groups),rows=sum(len(x)for x in groups.values()))))

def run(a):
 p=json.loads((a.output/'FROZEN_PROTOCOL.json').read_bytes())
 for file,expected in [(Path(__file__),p['adapter_sha256']),(a.preflight,p['metadata_preflight_sha256']),(a.roster,p['extension_roster_sha256'])]:
  if sha(file)!=expected:raise ValueError('frozen extension source adapter changed')
 setup(a);engine.run(a)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','run']);p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--root-protocol',type=Path,required=True);p.add_argument('--preflight',type=Path,required=True);p.add_argument('--roster',type=Path,required=True);p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--private-output',type=Path,required=True);p.add_argument('--private-root',type=Path,required=True);a=p.parse_args();a.root_protocol=a.root_protocol.resolve();a.output=a.output.resolve();prepare(a)if a.action=='prepare'else run(a)
