"""Exact side-aware law-origin metadata; canonical scores remain unchanged."""
import argparse,collections,gzip,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2 import full_provider_prop_replay as core
from nfl_v2.shared_subgroups import write,sha,now
PANELS={'fixed-w7-complete-leaf-law-v1':'completion-20261031g-fixed-w7-complete-leaf-law-v1','w6-complete-leaf-law-v1':'completion-20261031g-w6-complete-leaf-law-v1','w7-complete-leaf-law-v1':'completion-20261031g-w7-complete-leaf-law-v1'}
def main(a):
 data=json.loads((a.report/'COMPLETE_LEAF_LAW_ORIGIN_ANNOTATIONS.json').read_bytes());out=[];cache={}
 for folder,member in PANELS.items():
  priv=a.private_root/member;g=json.loads(gzip.decompress((priv/'GRADED_COMPLETE_LEAF_LAWS.json.gz').read_bytes()));f=json.loads(gzip.decompress((priv/'FROZEN_LAW_DIRECTIONS_K.json.gz').read_bytes()));loss={(r['method_id'],r['source_row_index'])for r in g['proper_losses']};km={(r['method_id'],r['K'],r['scope']):set(r['source_indices'])for r in f['Kplans']}
  for row in data:
   if('/'+folder+'/')not in row['source_artifact']:continue
   name=row['source_artifact']
   if name not in cache:
    p=a.root/name
    if sha(p)!=row['source_artifact_sha256']:raise ValueError('canonical source changed')
    cache[name]=json.loads(p.read_bytes())
   r=cache[name][row['source_row_index']]
   if r['record_kind']=='prop_threshold_probability_evaluation':tag=r['record_id'].removeprefix('LEAF-PROB-');chosen=[x for x in g['graded'][tag]if x['admitted']]
   else:
    tag=r['method_id'];pool=g['graded'][tag]
    if r.get('K')is not None:chosen=[x for x in pool if x['source_row_index']in km[tag,r['K'],r['rank_scope']]]
    else:chosen=[x for x in pool if core.in_cohort(x,r['cohort_id'])and x['selected_side']]
    chosen=[x for x in chosen if r['side']=='Combined'or x['selected_side']==r['side']]
   eligible=[x for x in chosen if x['admitted']];fallback=[x for x in eligible if x['source']=='REUSED_ELIGIBLE_FALLBACK_LAW'];scored=[x for x in eligible if(tag,x['source_row_index'])in loss];sf=[x for x in fallback if(tag,x['source_row_index'])in loss]
   z={k:v for k,v in row.items()if not k.startswith('exact_law_origin_')};z.update(actual_source_fallback_count=len(fallback),actual_source_learned_count=len(eligible)-len(fallback),actual_source_eligible_count=len(eligible),actual_source_scored_fallback_count=len(sf),actual_source_scored_learned_count=len(scored)-len(sf),actual_source_scored_eligible_count=len(scored),actual_source_fallback_rate=len(fallback)/len(eligible)if eligible else None,fallback_rate_denominator='Eligiblelawswithinexactselectedside/cohort/Kview; properALLlawrowsincludesalldirectionties',inherited_private_fallback_metadata='Notauthoritative; useexplicitsavedlaworigin only');out.append(z)
 write(a.report/'COMPLETE_LEAF_LAW_ORIGIN_ANNOTATIONS_V2.json',out);write(a.report/'LAW_ORIGIN_ANNOTATION_CORRECTION.json',dict(at=now(),state='METADATA_ONLY_SIDE_FILTER_AND_SCHEMA_CORRECTION',superseded_source='COMPLETE_LEAF_LAW_ORIGIN_ANNOTATIONS.json',superseded_sha256=sha(a.report/'COMPLETE_LEAF_LAW_ORIGIN_ANNOTATIONS.json'),current_source='COMPLETE_LEAF_LAW_ORIGIN_ANNOTATIONS_V2.json',current_sha256=sha(a.report/'COMPLETE_LEAF_LAW_ORIGIN_ANNOTATIONS_V2.json'),rows=len(out),reason='V1KoriginannotationsdidnotfilterthechosenKpoolbyselectedside;v2doesandexposesqualifiedorigin/eligible/scoredcounts. No canonicalgrade/probability/point/law or scorechanges.',code_sha256=sha(__file__),new_scores=0,new_model_inference=0,new_fits=0));print(json.dumps(dict(corrected_origin_annotations=len(out))))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--report',type=Path,required=True);p.add_argument('--private-root',type=Path,required=True);main(p.parse_args())
