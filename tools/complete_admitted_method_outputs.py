"""Missing-only public projection from retained graded method rows; no regrading."""
import argparse,collections,gzip,hashlib,json,resource,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2 import full_provider_prop_replay as core
from nfl_v2.shared_subgroups import canonical,sha,now,write
from tools.numerical_championship import csvwrite
VERSION='v2-admitted-methods-actual-threshold-W7-20261031g-v2'
def main(a):
 start,cpu=time.monotonic(),time.process_time();out=a.output;priv=a.private;source=json.loads((out/'FROZEN_PROTOCOL.json').read_bytes())
 if sha(core.__file__)!=source['core_sha256']:raise ValueError('shared projection core changed')
 completed=[dict(path=p.relative_to(a.root).as_posix(),sha256=sha(p))for p in(out/'SCORES.json',out/'category-pass_yd/SCORES.json')]
 write(out/'MISSING_ONLY_PROJECTION_REGISTRATION.json',dict(at=now(),state='FROZEN_MISSING_ONLY_NO_NEW_GRADES',helper_sha256=sha(__file__),source_grade_sha256=sha(priv/'GRADED_METHOD_ROWS.json.gz'),source_selection_sha256=sha(priv/'FROZEN_SELECTIONS_AND_K.json.gz'),existing_completed_scores=completed,budget=dict(wall_seconds=180,max_RSS_bytes=1073741824),new_fits=0,new_inference=0,new_direction_grades=0,new_probability_losses=0))
 frozen=json.loads(gzip.decompress((priv/'FROZEN_SELECTIONS_AND_K.json.gz').read_bytes()));g=json.loads(gzip.decompress((priv/'GRADED_METHOD_ROWS.json.gz').read_bytes()));graded=g['graded'];plans=frozen['plans'];controls=frozen['controls'];ks=frozen['Kplans'];links=frozen['baseline_links'];cohorts=core.cohort_names([r for rr in graded.values()for r in rr]);main=json.loads((out/'SCORES.json').read_bytes());checks=[];supp=[]
 def guard():
  if time.monotonic()-start>180 or resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>1073741824:raise RuntimeError('bounded missing projection')
 for target in core.TARGETS:
  folder=out/('category-'+target);path=folder/'SCORES.json'
  if path.exists():
   rows=json.loads(path.read_bytes());supp.append(dict(path=path.relative_to(a.root).as_posix(),sha256=sha(path),rows=len(rows),state='PRESERVED_COMPLETED_BYTES'));continue
  rows=[]
  for tag,rr in graded.items():
   pl=plans.get(tag);isc=pl is None;recipe=pl['recipe']if pl else(controls[tag]['target'],'MATCHED_RETAINED_CONTROL:'+controls[tag]['control'],'ARCHIVED','saved_precision_control');tt,proc,history,product=recipe
   if tt!=target:continue
   rule=pl['rule']if pl else'CONTROL'
   def emit(pool,chosen,cohort,K=None,scope=None,rankeligible=None):
    views=[]
    for side in('over','under','Combined'):
     z=[r for r in chosen if side=='Combined'or r['selected_side']==side];v=core.score_row(z,pool,strategy=tag,target=target,cohort=cohort,side=side,K=K,rank_scope=scope,rank_eligible=rankeligible);v.update(record_id='ADMIT-'+hashlib.sha256(canonical([tag,cohort,side,K,scope])).hexdigest()[:24],procedure_id=proc+(':known-target-time-v1'if not isc else''),history_regime=history,product_id=product,decision_rule=rule,method_id=tag,evaluation_panel_id=VERSION,time_panel_id='2026_W7_ADMITTED_METHOD_RECONSTRUCTION_462_13_GAMES',horizon_id='ASOF_2026_10_23T174953_KNOWN_TARGET_KICKOFF',selection_evidence='RETROSPECTIVE_RULE_REPLAY',source_vintage='Qualifiedretainedthreshold/context plus current-vintage7d footballreconstruction; neveroriginalmethodissuance',probability_conditioning=source['conditioning']if rule=='P2'else None);v['selection_metrics'].update(full_offer_universe=len(pool),admitted_forecast_opportunities=sum(r['admitted']for r in pool),unavailable_forecast_opportunities=sum(not r['admitted']for r in pool),fallback_issued=sum(r['admitted']and r['fallback']not in(None,'none')for r in pool));rows.append(v);views.append(v)
    core.check_triplet(views);checks.append([tag,cohort,K,scope])
   for cohort in cohorts:
    if cohort=='ALL':continue
    pool=[r for r in rr if core.in_cohort(r,cohort)];emit(pool,[r for r in pool if r['selected_side']],cohort)
   if not isc:
    lookup={r['source_row_index']:r for r in rr}
    for kp in ks:
     if kp['method_id']==tag:emit(rr,[lookup[i]for i in kp['source_indices']],'FIXED_PARTIAL_WEEK_TOP_PICK_SUBSET',kp['K'],kp['rank_scope'],kp['eligible_pool_n'])
   guard()
  folder.mkdir();write(path,rows);supp.append(dict(path=path.relative_to(a.root).as_posix(),sha256=sha(path),rows=len(rows),state='COMPLETED_MISSING_PROJECTION_FROM_RETAINED_GRADES'))
 paired=[]
 for link in links:
  rr=graded[link['method_id']];base={r['source_row_index']:r for r in graded[link['control_id']]};paired.append(dict(link,paired_selected_decisive=core.pilot.bootstrap(rr,base),scope='Same admitted input rows; bothselected/nonpush qualified outcomes for pairedhit diagnostic; completepool coverage retained separately'))
 common=[]
 for target in core.TARGETS:
  tags=[tag for tag,pl in plans.items()if pl['recipe'][0]==target and pl['rule']=='P1'];sets=[{r['source_row_index']for r in graded[tag]if r['admitted']}for tag in tags];ids=set.intersection(*sets)if sets else set();full=len(next((rr for tag,rr in graded.items()if plans.get(tag,{}).get('recipe',[None])[0]==target),[]));common.append(dict(target=target,methods=len(tags),common_admitted_rows=len(ids),full_offer_rows=full,state='NO_ALL_METHOD_COMMON_INTERSECTION'if not ids else'COMMON_MASK_AVAILABLE',mask_sha256=hashlib.sha256(canonical(sorted(ids))).hexdigest()))
 write(out/'SUPPLEMENTAL_SCORE_ARTIFACTS.json',supp);write(out/'PAIRED_CONTROL_COMPARISONS.json',paired);write(out/'COMMON_INTERSECTION.json',common);write(out/'SIDE_RECONCILIATION_PROJECTION_COMPLETION.json',dict(triplets=len(checks),checks=checks,main_and_first_category='Preserved existingsource scorebytes; independentchecker covers allcombinedsidecounts.'))
 csvwrite(out/'METHOD_SELECTION_ALL_SIDES.csv',[r for r in main if r['record_kind']=='prop_selection_evaluation']);csvwrite(out/'PROBABILITY_AND_POINT_PRODUCTS.csv',[r for r in main if r['record_kind']!='prop_selection_evaluation'])
 # All original completed bytes must remain exactly equal.
 for r in completed:
  if sha(a.root/r['path'])!=r['sha256']:raise ValueError('completed source score bytes changed')
 rec=dict(state='COMPLETE_BOUNDED_ADMITTED_METHOD_THRESHOLD_REPLAY_WITH_MISSING_ONLY_PROJECTION',at=now(),protocol_sha256=sha(out/'FROZEN_PROTOCOL.json'),main_score_sha256=sha(out/'SCORES.json'),main_score_views=len(main),supplement_score_views=sum(r['rows']for r in supp),score_views=len(main)+sum(r['rows']for r in supp),method_output_recipes=len(plans),control_masks=len(controls),probability_views=sum(r['record_kind']=='prop_threshold_probability_evaluation'for r in main),point_views=sum(r['record_kind']=='forecast_evaluation_view'for r in main),derived_probability_rows=len(g['probability_rows']),topK_lists=len(ks),source_offers=462,new_fits=0,new_inference=0,new_direction_grades_in_recovery=0,new_probability_losses_in_recovery=0,new_issued_forecasts=0,new_NFL_observations=0,Week8_outcomes_read=0,private_derivative_bytes=sum(x.stat().st_size for x in priv.iterdir()if x.is_file()),projection_resources=dict(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024),failed_initial_process_resources='Notcaptured; do notclaimprojectionusageistotalinitialexecutionusage')
 write(out/'RUN_RECEIPT.json',rec);print(json.dumps(rec))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--output',type=Path,required=True);p.add_argument('--private',type=Path,required=True);a=p.parse_args();a.output=a.output.resolve();main(a)
