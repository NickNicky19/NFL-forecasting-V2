"""Paired proper-score contrasts from retained loss rows; no CDF or grading."""
import argparse,collections,gzip,hashlib,json,math,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2.shared_subgroups import canonical,sha,now,write
from nfl_v2.paired_uncertainty import paired_losses
from tools.numerical_championship import csvwrite
BASE=Path(__file__).resolve().parents[1]/'reports/completion-20261031g/roster'

def main(a):
 out=a.output
 if out.exists():raise ValueError('fresh paired-loss output required')
 out.mkdir(parents=True);sources=[]
 for week in(6,7):
  for member in(f'completion-20261031g-w{week}-rolling-method-comparison-v1',f'completion-20261031g-w{week}-complete-leaf-law-v1'):
   for name in('GRADED_METHOD_ROWS.json.gz','FROZEN_SELECTIONS_AND_K.json.gz')if'rolling'in member else('GRADED_COMPLETE_LEAF_LAWS.json.gz','FROZEN_LAW_DIRECTIONS_K.json.gz'):
    p=a.private_root/member/name;sources.append(dict(logical_member=member+'/'+name,sha256=sha(p)))
 write(out/'FROZEN_PROTOCOL.json',dict(at=now(),code_sha256=sha(__file__),paired_helper_sha256=sha(Path(__file__).resolve().parents[1]/'nfl_v2/paired_uncertainty.py'),source_members=sources,contrasts='BaseLeafminusGLM,C02minusGLM, sameexacthistory/strictinformationpolicy/category; W6,W7andcumulativeW6-7. AllcachedBrier+categoricalregionlogloss rows, not probabilities frompoints.',pairing='Exact week/sourceindex/game/player/target/line/actual identity; intersect qualifiedproperloss support beforelosscomparisons, preserveownfullsupport. No Ffixedoverlap.',uncertainty='Wholeweek bootstrap only>=8weeks; here1or2 insufficient. Existing gamecluster95%sensitivity and500weekresample rule whereapplicable; exposed/multiplicityunadjusted.',new_fits=0,new_CDF_evaluations=0,new_direction_grades=0))
 data=collections.defaultdict(dict);public={};fulln={}
 for week in(6,7):
  parent=BASE/f'w{week}-rolling-method-comparison-v1';leaf=BASE/f'w{week}-complete-leaf-law-v1';pg=a.private_root/f'completion-20261031g-w{week}-rolling-method-comparison-v1';lg=a.private_root/f'completion-20261031g-w{week}-complete-leaf-law-v1';pf=json.loads(gzip.decompress((pg/'FROZEN_SELECTIONS_AND_K.json.gz').read_bytes()));pgr=json.loads(gzip.decompress((pg/'GRADED_METHOD_ROWS.json.gz').read_bytes()));lf=json.loads(gzip.decompress((lg/'FROZEN_LAW_DIRECTIONS_K.json.gz').read_bytes()));lgr=json.loads(gzip.decompress((lg/'GRADED_COMPLETE_LEAF_LAWS.json.gz').read_bytes()))
  pbs={r['record_id']:(i,r)for i,r in enumerate(json.loads((parent/'SCORES.json').read_bytes()))};lbs={r['record_id']:(i,r)for i,r in enumerate(json.loads((leaf/'SCORES.json').read_bytes()))}
  for tag,pl in pf['plans'].items():
   target,proc,arm,product=pl['recipe']
   if pl['rule']!='P2'or'regularized_glm_law'not in proc:continue
   strict='strict'in proc;key=(target,arm,strict,'GLM');rows={r['source_row_index']:r for r in pgr['graded'][tag]};i,pub=pbs['METHOD-PROB-'+tag];public[week,key]=dict(source_artifact=(parent/'SCORES.json').relative_to(a.root).as_posix(),source_artifact_sha256=sha(parent/'SCORES.json'),source_row_index=i,record_id=pub['record_id']);fulln[week,key]=pub['n']
   for r in pgr['probability_rows']:
    if r['method_id']!=tag:continue
    idx=r['source_row_index'];x=rows[idx];q=(week,idx);data[key][q]=dict(brier=r['half3class_brier'],log_loss=math.inf if r['categorical_log_loss']=='Infinity'else r['categorical_log_loss'],game=x['game_id'],identity=(x['game_id'],x['player_id'],x['target'],str(x['line']),x['actual']))
  for tag,pl in lf['plans'].items():
   target,proc,arm=pl['recipe'];strict='strict'in proc;family='C02'if'c02'in proc else'BASE_LEAF';key=(target,arm,strict,family);rows={r['source_row_index']:r for r in lgr['graded'][tag]};i,pub=lbs['LEAF-PROB-'+tag];public[week,key]=dict(source_artifact=(leaf/'SCORES.json').relative_to(a.root).as_posix(),source_artifact_sha256=sha(leaf/'SCORES.json'),source_row_index=i,record_id=pub['record_id']);fulln[week,key]=pub['n']
   for r in lgr['proper_losses']:
    if r['method_id']!=tag:continue
    idx=r['source_row_index'];x=rows[idx];q=(week,idx);data[key][q]=dict(brier=r['brier'],log_loss=math.inf if r['log_loss']=='Infinity'else r['log_loss'],game=x['game_id'],identity=(x['game_id'],x['player_id'],x['target'],str(x['line']),x['actual']))
 comparisons=[];annotations=[]
 for key,aa in sorted(data.items()):
  target,arm,strict,family=key
  if family=='GLM':continue
  ck=(target,arm,strict,'GLM');bb=data[ck]
  for weeks in((6,),(7,),(6,7)):
   aq={q for q in aa if q[0]in weeks};bq={q for q in bb if q[0]in weeks};qq=sorted(aq&bq)
   for q in qq:
    if aa[q]['identity']!=bb[q]['identity']:raise ValueError('pairedlaw labels/identity differ')
   for metric in('brier','log_loss'):
    u=paired_losses([aa[q][metric]for q in qq],[bb[q][metric]for q in qq],[q[0]for q in qq],[aa[q]['game']for q in qq]);cid='PAIR-ACTUAL-PROB-'+hashlib.sha256(canonical([key,weeks,metric])).hexdigest()[:24];row=dict(comparison_id=cid,record_kind='derived_paired_proper_probability_loss_comparison',target=target,history_regime=arm,strict_current_information=strict,candidate_family=family,comparator_family='GLM',metric=metric,evaluation_seasons=[2026],evaluation_weeks=list(weeks),probability_conditioning='MODELED_APPEARANCE',probability_score_contract='HALF_MULTICLASS_BRIER_OVER_UNDER_PUSH_V1'if metric=='brier'else'CATEGORICAL_OVER_UNDER_PUSH_LOG_LOSS',candidate_own_n=len(aq),comparator_own_n=len(bq),common_loss_mask_is_both_full_masks=aq==bq,membership_sha256=hashlib.sha256(canonical([[q,aa[q]['identity']]for q in qq])).hexdigest(),candidate_source_records=[public[w,key]for w in weeks],comparator_source_records=[public[w,ck]for w in weeks],evidence='NEW_PAIRED_COMPARISON_FROM_EXISTING_LOSS_ROWS',new_NFL_observations=0,**u);comparisons.append(row)
    if len(weeks)==1 and metric=='brier'and aq==bq:annotations.append(dict(**public[weeks[0],key],comparison=dict(comparison_id=cid,status='EXACT_FULL_MASK_PAIRED_ACTUAL_LINE_PROPER_SCORE',metric='brier',candidate_error=u['candidate_error'],comparator_error=u['comparator_error'],absolute_error_change=u['delta'],relative_error_change=u['relative_error_change'],paired_n=u['n'],comparator_procedure_id=public[weeks[0],ck]['record_id'],comparator_source=public[weeks[0],ck],uncertainty=u,scope='Same history/strictpolicy/category/actualoffer rows; candidateprocedure difference retained.')))
 write(out/'PAIRED_PROBABILITY_COMPARISONS.json',comparisons);csvwrite(out/'PAIRED_PROBABILITY_COMPARISONS.csv',comparisons);write(out/'PROPER_SCORE_COMPARISON_ANNOTATIONS.json',annotations);write(out/'RUN_RECEIPT.json',dict(state='COMPLETE_CACHED_PROPER_LOSS_COMMON_ROW_COMPARISONS',at=now(),comparisons=len(comparisons),proper_source_row_annotations=len(annotations),all_comparisons_full_masks=sum(r['common_loss_mask_is_both_full_masks']for r in comparisons),source_sha256=sha(out/'FROZEN_PROTOCOL.json'),new_fits=0,new_CDF_evaluations=0,new_direction_grades=0,new_issued_forecasts=0,new_NFL_observations=0));print(json.dumps(dict(comparisons=len(comparisons),source_annotations=len(annotations),full_mask_comparisons=sum(r['common_loss_mask_is_both_full_masks']for r in comparisons))))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--private-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);main(p.parse_args())
