"""Metadata-first finite K extension roster and lossless saved-row adapter."""
import argparse,collections,gc,gzip,hashlib,json,math,resource,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2.shared_subgroups import canonical,sha,write,now
from tools.run_right_wrong_diagnostic import csvwrite

def main(a):
 start=time.monotonic()
 if a.output.exists()or a.private_output.exists():raise ValueError('fresh extension preflight required')
 root=json.loads(a.root_protocol.read_bytes());prior=json.loads((a.repo/'reports/point-prop-diagnostic-20261031i/point-offer/v1/FROZEN_PROTOCOL.json').read_bytes());recipes=root['stage_A']['recipes'];controls=root['stage_A']['saved_controls'];targets=list(root['tolerances']);cells={}
 for target in targets:
  for recipe in recipes:cells[target,*recipe]=dict(recipe=[target,*recipe],requested_by='FROZEN_SAME_I_LIBRARY')
  for c in controls:cells[target,c,'ARCHIVED','saved_precision_point']=dict(recipe=[target,c,'ARCHIVED','saved_precision_point'],requested_by='FROZEN_SAVED_CONTROL_LIBRARY')
 extra=('pass_int','v2-c02-explicit-lag-block-removal-leaf-cdf-v1','H-CURRENT','lower_median');cells[extra]=dict(recipe=list(extra),requested_by='ALREADY_PUBLISHED_CURRENT_CATEGORY_LEADER')
 fixed_anchor=('v2-distribution-controls-reconstruction-v2:ordered_leaf_cdf','H-MULTI','lower_median');bindings=[];inputrows=[];attempts=[]
 for week in[5,6,7]:
  folder='baselines-coverage-20261031h-w5-method-comparison-v1'if week==5 else f'completion-20261031g-w{week}-rolling-method-comparison-v1';private=a.private_root/folder;files={}
  for member in['FROZEN_SELECTIONS_AND_K.json.gz','GRADED_METHOD_ROWS.json.gz']:
   file=private/member;binding=next(r for r in prior['source_bindings']if r['week']==week and r['member']==member)
   if sha(file)!=binding['sha256']:raise ValueError('sourceplan/grades changed')
   bindings.append(dict(binding));files[member]=file
  packet=json.loads(gzip.decompress(files['FROZEN_SELECTIONS_AND_K.json.gz'].read_bytes()));plans={tuple(v['recipe']):(tag,v)for tag,v in packet['plans'].items()if v['rule']=='P1'};grades=json.loads(gzip.decompress(files['GRADED_METHOD_ROWS.json.gz'].read_bytes()))['graded']
  for key,cell in sorted(cells.items()):
   target,proc,arm,product=key;tag=None;maskref=None
   if arm=='ARCHIVED':
    anchor=tuple(root['stage_A']['focals'].get(target,fixed_anchor));found=plans.get((target,*anchor))
    if found:
     anchor_tag,_=found;link=next((x for x in packet['baseline_links']if x['method_id']==anchor_tag and x['control']==proc),None)
     if link:tag=link['control_id'];maskref=dict(anchor_recipe=[target,*anchor],anchor_method_id=anchor_tag)
   else:
    found=plans.get(key)
    if found:tag=found[0]
   if tag is None or tag not in grades:
    attempts.append(dict(recipe=list(key),week=week,status='SAVED_EXACT_RECIPE_NOT_LOCATED',next_action='Qualify exact saved recipe/adapter; no alias substitution or new fit',control_mask=maskref));continue
   source=grades[tag];mask=[];admitted=0
   for r in source:
    point=r.get('ranking_point');available=bool(r.get('admitted')and point is not None and math.isfinite(float(point)));mask.append((week,r['source_row_index'],r.get('game_id'),r.get('player_id'),target));admitted+=available
    if target not in root['stage_A']['targets']:
     inputrows.append(dict(recipe=list(key),week=week,source_row_index=r['source_row_index'],game_id=r.get('game_id'),player_id=r.get('player_id'),target=target,position=r.get('position'),population=r.get('population'),line=r.get('line'),line_from=r.get('line_from'),actual=r.get('actual'),point=point,admitted=available,selected_side=r.get('selected_side'),statistical_state=r.get('statistical_state'),participation=r.get('participation'),fallback=r.get('fallback')if arm!='ARCHIVED'else None,origin='V2_RETAINED_POINT'if arm!='ARCHIVED'else'SAVED_POINT_METADATA_LIMITED',decision_time=r.get('source_server_clock',r.get('server_retained_by')),kickoff=r.get('kickoff'),source_method_id=tag,source_field='ranking_point',source_id=folder,source_grade_sha256=sha(files['GRADED_METHOD_ROWS.json.gz'])))
   attempts.append(dict(recipe=list(key),week=week,status='COMPLETED_STAGE_A_REUSE'if target in root['stage_A']['targets']else'EXACT_SAVED_ROW_REPLAYABLE',outer_rows=len(source),admitted_metadata_rows=admitted,source_method_id=tag,fullsource_mask_sha256=hashlib.sha256(canonical(sorted(mask,key=str))).hexdigest(),control_mask=maskref))
  del grades,packet;gc.collect()
  if time.monotonic()-start>300 or resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>1073741824:raise RuntimeError('bounded metadata preflight')
 a.output.mkdir(parents=True);a.private_output.mkdir(parents=True);blob=gzip.compress(canonical(dict(schema='K-STAGE-B-SAVED-ROW-ADAPTER-V1',rows=inputrows)),mtime=0)
 if len(blob)>4*1024*1024:raise ValueError('preflight normalizedinputcapacity; preserve sources withoutaddinglargebacklog')
 file=a.private_output/'NORMALIZED_EXTENSION_INPUT_ROWS.json.gz'
 with file.open('xb')as f:f.write(blob)
 grid=[]
 for key,cell in sorted(cells.items()):
  weekly=[r for r in attempts if tuple(r['recipe'])==key];done=all(r['status']in['COMPLETED_STAGE_A_REUSE','EXACT_SAVED_ROW_REPLAYABLE']for r in weekly);grid.append(dict(cell,status='COMPLETED_STAGE_A_REUSE'if key[0]in root['stage_A']['targets']else'REPLAYABLE_FROZEN_EXACT_SAVED_ROWS'if done else'EXACT_SOURCE_BLOCKED',weeks=weekly,next_action='Reuse StageA, no duplicatediagnostics'if key[0]in root['stage_A']['targets']else'Freeze stageBcode/input protocol then replay newbucket/band diagnostics'if done else'Locate exact missingweek/source; no model/history/product substitution'))
 write(a.output/'EXACT_EXTENSION_ROSTER.json',grid);csvwrite(a.output/'EXACT_EXTENSION_ROSTER.csv',grid)
 receipt=dict(schema='k-stage-b-finite-metadata-roster-preflight-v1',state='FROZEN_SOURCE_ROSTER_BEFORE_EXTENSION_DIAGNOSTIC_METRICS',at=now(),root_protocol_sha256=sha(a.root_protocol),code_sha256=sha(__file__),source_bindings=bindings,roster_sha256=sha(a.output/'EXACT_EXTENSION_ROSTER.json'),requested_recipe_category_cells=len(cells),reused_stage_A_cells=sum(r['status']=='COMPLETED_STAGE_A_REUSE'for r in grid),extension_replayable_cells=sum(r['status']=='REPLAYABLE_FROZEN_EXACT_SAVED_ROWS'for r in grid),blocked_cells=sum(r['status']=='EXACT_SOURCE_BLOCKED'for r in grid),normalized_input_artifact_id='K-STAGE-B-NORMALIZED-EXTENSION-INPUT-V1',normalized_input_sha256=sha(file),normalized_input_rows=len(inputrows),normalized_input_bytes=len(blob),estimated_output_private_bytes_upper=len(blob)*5+1048576,combined_existing_stage_A_private_bytes=474426,private_total_capacity=12582912,control_mask_rule='Existing Ifocal mask forPY/PC; fixedbaseLeafH-MULTIlower_median mask forothercategories, namedexplicitly. Not full-offer controlcoverage claim.',not_applicable_targets={'nick-chart-ppr-v1':'No authenticatedexactchartofferedthresholds; no manufacturedmarket','anytime_td':'Event probability is a differentproduct; no authenticatedcompatibleYes/Nothreshold diagnostic admittedhere'},new_fits=0,new_inference=0,new_grades=0,new_diagnostic_metrics=0,resources=dict(wall_seconds=time.monotonic()-start,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024))
 write(a.output/'PREFLIGHT_RECEIPT.json',receipt);print(json.dumps(receipt))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--root-protocol',type=Path,required=True);p.add_argument('--private-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--private-output',type=Path,required=True);a=p.parse_args();main(a)
