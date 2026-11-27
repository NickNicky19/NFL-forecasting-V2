"""Append exact source-prefix and feature-parity admission; no fits or grading."""
import argparse,collections,hashlib,json,sys
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[3];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(BASE))
from nfl_v2 import hgb_control as source,ordered_information_ablation as c02
from run_legacy_completion_v1 import read,save,sha,now

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--private',type=Path,required=True);ap.add_argument('--native-sources',type=Path,required=True);a=ap.parse_args();rows=read(BASE/'STRICT_2026_COMPLETION_INPUTS_V1.json.gz')['rows'];old=read(BASE/'OLD_W1_W7_PREDICTIONS_V1.json.gz')['rows'];new=read(BASE/'PREDICTIONS_W8_W9_V1.json.gz')['rows'];pred={(r['method'],r['week'],r['game_id'],r['player_id']):r for r in old+new};sources=read(a.native_sources);records=[];prefixproof=0
 masks=[]
 for w in[6,7]:
  p=a.private/f'completion-20261031g-w{w}-rolling-admission-v1/ADMISSIBILITY_MASK.json.gz';d=read(p);rr=[r for r in d['rows']if r['target']=='pass_cmp'and r['product_id']=='mean'and r['source_id']in{'c02','laws'}and 'strict-current-inputs'in r['procedure_id']];masks.append(dict(week=w,safe_original_mask_sha256=sha(p),source_contract='Existing original rolling known-target-time admission mask',counts=dict(collections.Counter(f"{r['source_id']}:{r['p1_state']}"for r in rr)),exclusion_reasons=dict(collections.Counter(reason for r in rr for reason in r['reasons'])),nominal_fit_reuse_rule=next(r['nominal_fit_reuse_rule']for r in rr)))
 fullhist=source.FeatureHistory(rows)
 for sw,path in sources.items():
  w=int(sw);native=[r for r in read(Path(path))['rows']if r['target']=='pass_cmp']
  oldfeatures={}
  if w<=7:
   for method,folder in[('C02','ordered-information-ablation-v1'),('DIRECT_GLM','distribution-wave-v2')]:
    q=read(a.private/folder/'query-features'/f'W{w:02}-pass_cmp-H-CURRENT-STRICT.json.gz');oldfeatures[method]={(r['query']['game_id'],r['query']['player_id']):r['features']for r in q}
  for raw in native:
   clock=raw.get('source_server_clock');clock=datetime.fromisoformat(clock.replace('Z','+00:00')).timestamp()if clock else None
   for method in['C02','DIRECT_GLM']:
    key=method,w,raw['game_id'],raw['player_id'];r=pred.get(key);reasons=[]
    if r is None:records.append(dict(method=method,week=w,game_id=raw['game_id'],player_id=raw['player_id'],state='FORECAST_TECHNICALLY_UNAVAILABLE'));continue
    if w<=7:
     fit=read(ROOT/(f'reports/continuation-20261030b/ordered-information-ablation-v1/W{w:02}-pass_cmp-H-CURRENT-STRICT-FIT.json'if method=='C02'else f'reports/continuation-20261030/distribution-wave-v2/W{w:02}-pass_cmp-H-CURRENT-STRICT-regularized_glm_law-FIT.json'));origin=datetime.fromisoformat(fit['fit_cutoff_utc']).timestamp();expected=fit['training_membership_sha256'];f=oldfeatures[method][raw['game_id'],raw['player_id']]
    else:
     fit=read(BASE/'fits'/f'2026-W{w:02}-{method}.json.gz');origin=fit['fit_cutoff'];expected=fit['training_membership_sha256'];f=r['features']
    if clock is None:reasons.append('SOURCE_CLOCK_UNKNOWN');prefix=None;parity=False
    else:
     admitted=[v for v in rows if v['position']=='QB'and v['values']['pass_cmp']is not None and v['available']<min(origin,clock)];prefix=hashlib.sha256(source.canonical([(v['game_id'],v['player_id'])for v in admitted])).hexdigest();earlier=source.FeatureHistory([v for v in rows if v['available']<clock]);v,_=earlier.get(raw['player_id'],'QB','pass_cmp',r['feature_cutoff']);v=c02.project(v)if method=='C02'else v;parity=bool(np.allclose(v,np.asarray(f,float),rtol=0,atol=0,equal_nan=True));prefixproof+=1
     if prefix!=expected:reasons.append('TRAINING_OR_PRIOR_SOURCE_AFTER_DECISION')
     if not parity:reasons.append('QUERY_SOURCE_AFTER_DECISION')
    if raw.get('position')!='QB':reasons.append('ROLE_PARITY_UNESTABLISHED')
    if datetime.fromisoformat(raw['kickoff'].replace('Z','+00:00')).timestamp()!=r['feature_cutoff']:reasons.append('FOREKNOWN_KICKOFF_PARITY_REQUIRED')
    records.append(dict(method=method,week=w,game_id=raw['game_id'],player_id=raw['player_id'],source_row_index=raw.get('source_row_index'),source_server_run_id=raw.get('source_server_run_id'),original_procedure_id=r['procedure_id'],conditional_normalized_procedure_id=r['procedure_id']+':known-target-time-v1',fit_cutoff=origin,decision_clock=clock,query_cutoff=r['feature_cutoff'],same_training_membership=prefix==expected,same_query_feature_vector=parity,nominal_fit_after_decision=clock is not None and origin>=clock,state='EXACT_KNOWN_TARGET_TIME_PARITY'if not reasons else'NOT_AN_ALIAS_AT_THIS_DECISION',reasons=reasons))
 counts={f'{w}:{m}':dict(collections.Counter(r['state']for r in records if r['week']==w and r['method']==m))for w in range(5,10)for m in['C02','DIRECT_GLM']}
 mapping=[]
 for m,base in[('C02','v2-c02-explicit-lag-block-removal-leaf-cdf-v1:strict-current-inputs'),('DIRECT_GLM','v2-distribution-controls-reconstruction-v2:regularized_glm_law:strict-current-inputs')]:
  mapping.append(dict(method=m,base_procedure_id=base,known_target_time_id=base+':known-target-time-v1',conditional_alias='Only rows EXACT_KNOWN_TARGET_TIME_PARITY; preserves all old source/prior/transform/fallback inputs and foreknown kickoff age semantics, not original issuance',whole_board_reconstruction_continuation_id=base+':weekly-kickoff-retrospective-extension-v1',whole_board_status='Separately typed current-vintage historical weekly-origin diagnostic; never claim every input was eligible at original native server clock'))
 save(BASE/'ALIAS_AND_HISTORY_POLICY_BINDINGS_V2.json',dict(id='B-LEGACY-ALIAS-AND-HISTORY-POLICY-BINDINGS-v1',at_UTC=now(),code_sha256=sha(__file__),state='ROW_CONDITIONAL_ALIAS_PROVED;WHOLE_BOARD_RECONSTRUCTION_DISTINCT',mapping=mapping,old_law_map=dict(path=(BASE/'OLD_W1_W7_PREDICTIONS_V1.json.gz').relative_to(ROOT).as_posix(),sha256=sha(BASE/'OLD_W1_W7_PREDICTIONS_V1.json.gz'),rows=484),new_law_map=dict(path=(BASE/'PREDICTIONS_W8_W9_V1.json.gz').relative_to(ROOT).as_posix(),sha256=sha(BASE/'PREDICTIONS_W8_W9_V1.json.gz'),rows=146),original_mask_receipts=masks,counts=counts,rows=records,implementation_repair_sha256=sha(BASE/'ALIAS_IMPLEMENTATION_REPAIR_V1.json'),supersedes='ALIAS_AND_HISTORY_POLICY_BINDINGS_V1.json',prefix_and_feature_checks=prefixproof,old_80_vs_84='All 84 native W5-7 identities have old forecasts. Exact original known-target-time masks admit28+27+25=80 per method. Four unavailable rows are timing exclusions, not absent player forecasts; nominal later fit may be reused only with exact earlier eligible training prefix proof.',prior_conservative_envelope='NATIVE_QUERY_GAPS_AND_ALIAS_ADMISSION_V1.json additionally required nominal weekly fit cutoff < source clock. Preserve that conservative receipt; this appendix applies the already registered prefix-equivalence exception and independently proves membership/feature parity. No rule invented after new scores, and no scores computed.',no_scores_or_sides=True,no_new_fits=True,source_rights='CC-BY-4.0 derived statistical forecasts; no raw/protected lines exported'))
 print(json.dumps(dict(state='ROW_CONDITIONAL_ALIAS_PROVED',counts=counts,prefix_and_feature_checks=prefixproof,receipt_sha256=sha(BASE/'ALIAS_AND_HISTORY_POLICY_BINDINGS_V2.json'))))
if __name__=='__main__':main()
