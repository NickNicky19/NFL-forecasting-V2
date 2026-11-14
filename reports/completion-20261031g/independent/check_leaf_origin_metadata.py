"""Check exact learned/prior law origins without using inherited recipe fallback aliases."""
import argparse,collections,functools,hashlib,importlib.util,json,math
from pathlib import Path
sp=importlib.util.spec_from_file_location('p',Path(__file__).with_name('check_w7_methods.py'));p=importlib.util.module_from_spec(sp);sp.loader.exec_module(p)
read,zipped,sha,close,member=p.read,p.zipped,p.sha,p.close,p.member

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--private',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();pub=a.root/'reports/completion-20261031g/roster/actual-method-period-summary-v2';data={};decomp={}
 names={'F7':'fixed-w7-complete-leaf-law-v1','W6':'w6-complete-leaf-law-v1','W7':'w7-complete-leaf-law-v1'}
 for panel,n in names.items():
  priv=a.private/('completion-20261031g-'+n);g=zipped(priv/'GRADED_COMPLETE_LEAF_LAWS.json.gz');f=zipped(priv/'FROZEN_LAW_DIRECTIONS_K.json.gz');km={(x['method_id'],x['K'],x['scope']):set(x['source_indices'])for x in f['Kplans']};loss={(x['method_id'],x['source_row_index']):(x['brier'],x['log_loss'])for x in g['proper_losses']};data[n]=(g,f,km,loss)
  for tag,pl in f['plans'].items():
   t,proc,h=pl['recipe'];rr=g['graded'][tag]
   for view in('FULL_SYSTEM','LEARNED_LAW_ONLY','FALLBACK_LAW_ONLY'):
    zz=[x for x in rr if x['admitted']and(view=='FULL_SYSTEM'or(x['source']=='REUSED_ELIGIBLE_FALLBACK_LAW')==(view=='FALLBACK_LAW_ONLY'))];vv=[loss[tag,x['source_row_index']]for x in zz if(tag,x['source_row_index'])in loss];decomp[panel,t,proc,h,view]=(len(zz),len(vv),math.fsum(x[0]for x in vv)/len(vv)if vv else None,'Infinity'if any(x[1]=='Infinity'for x in vv)else math.fsum(x[1]for x in vv)/len(vv)if vv else None,sum(x[1]=='Infinity'for x in vv))
 @functools.lru_cache(maxsize=4)
 def source(path,h):
  pth=a.root/path;assert sha(pth)==h;return read(pth)
 annotations=read(pub/'COMPLETE_LEAF_LAW_ORIGIN_ANNOTATIONS_V2.json')
 for z in annotations:
  r=source(z['source_artifact'],z['source_artifact_sha256'])[z['source_row_index']];assert r['record_id']==z['record_id'];n=Path(z['source_artifact']).parts[3];g,f,km,loss=data[n]
  if r['record_kind']=='prop_threshold_probability_evaluation':tag=r['record_id'].removeprefix('LEAF-PROB-');rr=g['graded'][tag]
  else:
   tag=r['method_id'];rr=g['graded'][tag]
   if r['K']is None:rr=[x for x in rr if member(x,r['cohort_id'])and x['selected_side']and(r['side']=='Combined'or x['selected_side']==r['side'])]
   else:rr=[x for x in rr if x['source_row_index']in km[tag,r['K'],r['rank_scope']]and(r['side']=='Combined'or x['selected_side']==r['side'])]
  eligible=[x for x in rr if x['admitted']];fb=[x for x in eligible if x['source']=='REUSED_ELIGIBLE_FALLBACK_LAW'];learned=[x for x in eligible if x['source']=='RECOVERED_SAVED_LEAF_IDS_HISTOGRAM_NO_MODEL_INFERENCE'];assert len(fb)+len(learned)==len(eligible);assert(z['actual_source_eligible_count'],z['actual_source_fallback_count'],z['actual_source_learned_count'])==(len(eligible),len(fb),len(learned));close(z['actual_source_fallback_rate'],len(fb)/len(eligible)if eligible else None)
  vals=[x for x in eligible if(tag,x['source_row_index'])in loss];vf=[x for x in fb if(tag,x['source_row_index'])in loss];vl=[x for x in learned if(tag,x['source_row_index'])in loss];assert(z['actual_source_scored_eligible_count'],z['actual_source_scored_fallback_count'],z['actual_source_scored_learned_count'])==(len(vals),len(vf),len(vl));assert z['bookmaker_unresolved_contract_selected_rows']==(r['forecast_rows']if r['record_kind']=='prop_selection_evaluation'else None)
 decomposition=read(pub/'COMPLETE_LEAF_FALLBACK_DECOMPOSITION.json')
 for r in decomposition:
  n,ns,b,ll,inf=decomp[r['panel'],r['target'],r['procedure_id'],r['history_regime'],r['view']];assert(r['admitted_law_rows'],r['scored_law_rows'],r['infinite_log_losses'])==(n,ns,inf);close(r['brier'],b);close(r['log_loss'],ll)
 assert len(annotations)==23280 and len(decomposition)==720
 out=dict(state='PASS_INDEPENDENT_EXPLICIT_LAW_ORIGIN_METADATA_AND_FALLBACK_LOSSES',source_bound_annotations=len(annotations),full_learned_fallback_metric_views=len(decomposition),private_generic_fallback_field_not_used=True,complete_leaf_score_bytes_unchanged=True,new_fits=0,new_inference=0,new_grades=0)
 with a.output.open('x')as f:json.dump(out,f,indent=2);f.write('\n')
 print(json.dumps(out))
if __name__=='__main__':main()
