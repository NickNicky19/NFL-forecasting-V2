"""Two pre-existing native RRselector ties through the shared Kengine only."""
import argparse,gzip,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools import run_right_wrong_diagnostic as engine
from nfl_v2 import right_wrong_diagnostic as diagnostic,scoring
from nfl_v2.shared_subgroups import canonical,sha,write,now

VERSION='v2-right-wrong-native-rr-selector-ties-v1'
RECIPES=[['rush_rec_yd','v2-chronological-category-selector:'+name,'H-MULTI','selected_point']for name in ['FROZEN_2025_BEST','POOLED_2025_AND_AVAILABLE_2026_MEMORY']]
def load_rows(path,root_protocol):
 groups={tuple(k):{}for k in RECIPES}
 for row in json.loads(gzip.decompress(path.read_bytes()))['rows']:
  key=tuple(row['recipe'])
  if key not in groups:raise ValueError('outside two pre-existing native selector ties')
  q=engine.row_key(row)
  if q in groups[key]:raise ValueError('duplicate retainedselector offer')
  groups[key][q]=row
 return groups,0
def prepare(a):
 if a.output.exists()or a.private_output.exists():raise ValueError('fresh two-cellcompletion identity required')
 rows=[];bindings=[];metadata=[];native=a.root/'reports/baselines-coverage-20261031h/CATEGORY_DECISIONS.json';source=json.loads(native.read_bytes());rr=next(r for r in source if r['category']=='rush_rec_yd')
 for recipe in RECIPES:
  nativeproc=recipe[1].replace('v2-chronological-category-selector:','v2-chronological-category-score-memory-selector-v2:')
  if not any(w['procedure_id']==nativeproc for w in rr['native_winners']):raise ValueError('not a pre-existing native tie')
 for week in[5,6,7]:
  folder='baselines-coverage-20261031h-w5-method-comparison-v1'if week==5 else f'completion-20261031g-w{week}-rolling-method-comparison-v1';private=a.private_root/folder;planfile=private/'FROZEN_SELECTIONS_AND_K.json.gz';gradefile=private/'GRADED_METHOD_ROWS.json.gz';packet=json.loads(gzip.decompress(planfile.read_bytes()));grades=json.loads(gzip.decompress(gradefile.read_bytes()))['graded'];plans={tuple(v['recipe']):(tag,v)for tag,v in packet['plans'].items()if v['rule']=='P1'};grade_sha=sha(gradefile)
  bindings.append(dict(week=week,source_id=folder,plan_sha256=sha(planfile),grade_sha256=grade_sha))
  for recipe in RECIPES:
   tag,plan=plans[tuple(recipe)];source_rows=grades[tag];metadata.append(dict(recipe=recipe,week=week,source_method_id=tag,outer_rows=len(source_rows),admitted_metadata_rows=sum(bool(r['admitted'])and r.get('point')is not None for r in plan['rows'])))
   for r in source_rows:
    rows.append(dict(recipe=recipe,week=week,source_row_index=r['source_row_index'],game_id=r['game_id'],player_id=r['player_id'],target=r['target'],position=r['position'],line=r['line'],actual=r['actual'],point=r.get('ranking_point'),admitted=bool(r['admitted']and r.get('ranking_point')is not None),selected_side=r['selected_side'],statistical_state=r['statistical_state'],participation=r['participation'],fallback=r.get('fallback'),origin='V2_RETAINED_POINT',decision_time=r.get('source_server_clock',r.get('server_retained_by')),kickoff=r['kickoff'],source_method_id=tag,source_field='ranking_point',source_id=folder,source_grade_sha256=grade_sha))
 a.output.mkdir(parents=True);a.private_output.mkdir(parents=True);blob=gzip.compress(canonical(dict(rows=rows)),mtime=0)
 with a.input.open('xb')as f:f.write(blob)
 lineage=a.root/'reports/right-and-wrong-diagnostic-20261031k/lineage/INSPECT_RETAINED_LINEAGE.py';rp=json.loads(a.root_protocol.read_bytes());p=dict(version=VERSION,state='FROZEN_BEFORE_TWO_RETAINED_NATIVE_TIE_DIAGNOSTIC_CELLS',at=now(),root_protocol_path=a.root_protocol.relative_to(a.root).as_posix(),root_protocol_sha256=sha(a.root_protocol),pre_existing_native_leader_source=native.relative_to(a.root).as_posix(),pre_existing_native_leader_source_sha256=sha(native),amendment_reason='Close two pre-existing RRnative co-leader policyoutputs omittedfrom bounded181celllibrary; no newalgorithmoroutcome-selected expansion',source_artifact_id='K-RR-SELECTOR-TIE-NORMALIZED-INPUT-V1',source_sha256=sha(a.input),source_bytes=len(blob),source_bindings=bindings,roster=metadata,code_sha256=sha(engine.__file__),adapter_sha256=sha(__file__),core_sha256=sha(diagnostic.__file__),grader_sha256=sha(scoring.__file__),lineage_helper_path=lineage.relative_to(a.root).as_posix(),lineage_helper_sha256=sha(lineage),realized_context_helper_sha256=sha(lineage.parent/'REALIZED_CONTEXT_LOOKUP.py'),tolerances=rp['tolerances'],diagnostic_only=True,default_rank_eligible=False,budget=rp['budget'])
 write(a.output/'FROZEN_PROTOCOL.json',p);(a.output/'ADAPTER_SOURCE_SNAPSHOT.py').write_bytes(Path(__file__).read_bytes());print(json.dumps(dict(protocol_sha256=sha(a.output/'FROZEN_PROTOCOL.json'),cells=2,metadata=metadata,input_bytes=len(blob))))
def run(a):
 p=json.loads((a.output/'FROZEN_PROTOCOL.json').read_bytes())
 if sha(__file__)!=p['adapter_sha256']:raise ValueError('frozen two-cell adapter changed')
 engine.VERSION=VERSION;engine.load_rows=load_rows;original=engine.write
 def bound_write(path,obj):
  if Path(path).name=='RUN_RECEIPT.json':obj=dict(obj,private_artifact_id='K-RR-SELECTOR-TIE-ROWS-EXAMPLES-V1',stage='RR_NATIVE_TIE_COMPLETION',additional_cells=2,previous_stage_A_B_cells=181)
  return original(path,obj)
 engine.write=bound_write;engine.run(a)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','run']);p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--root-protocol',type=Path,required=True);p.add_argument('--private-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--private-output',type=Path,required=True);a=p.parse_args();a.root_protocol=a.root_protocol.resolve();a.output=a.output.resolve();a.input=a.private_output/'NORMALIZED_NATIVE_TIE_INPUT_ROWS.json.gz';prepare(a)if a.action=='prepare'else run(a)
