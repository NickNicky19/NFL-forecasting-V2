"""Independently verify typed candidate source bindings and actual admission state."""
import argparse,hashlib,json,math
from pathlib import Path

def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def same(a,b):return a==b or(isinstance(a,(int,float))and isinstance(b,(int,float))and math.isclose(a,b,abs_tol=1e-10,rel_tol=1e-10))
def unit(proc):
 if proc.startswith('empirical-player-history-control-v1'):return'EMPIRICAL_TARGET_HISTORY'
 if 'c02-explicit-lag-block-removal'in proc:return'C02_LAG_BLOCK_REMOVAL_LEAF_CDF'
 if 'ordered_leaf_cdf'in proc:return'ORDERED_LEAF_CDF'
 if 'absolute_error_point'in proc:return'HGB_ABSOLUTE_ERROR'
 if 'log_loss_probability'in proc:return'HGB_BINARY_LOGLOSS'
 raise AssertionError(proc)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();pub=a.root/'reports/completion-20261031g';rows=read(pub/'CATEGORY_RELEASE_PACKAGES.json');grid=read(pub/'roster/finite-v2/CURRENT_METHOD_COMPARISONS.json');census=read(pub/'UPCOMING_CATEGORY_CAPTURE_STATUS.json');dec={r['category']:r for r in read(pub/'EXECUTIVE_CATEGORY_DECISIONS.json')};cor=read(pub/'CATEGORY_RELEASE_OPTION_CORRECTION_RECEIPT.json');assert sha(pub/'CATEGORY_RELEASE_PACKAGES.json')==cor['current_sha256']and sha(pub/'roster/finite-v2/CURRENT_METHOD_COMPARISONS.json')==cor['source_current_grid_sha256'];assert len(rows)==cor['exact_bound_options']==12;proof=[]
 for r in rows:
  x=r['owner_review_static_option'];assert x is not None;matches=[g for g in grid if(g['target'],g['procedure_id'],g['history_regime'],g['product_id'])==(r['category'],x['procedure_id'],x['history_regime'],x['product_id'])];assert len(matches)==1;g=matches[0]
  for k in('n','forecast_rows','mae','brier','source_artifact','source_test_id','information_policy','horizon'):assert same(x[k],g[k]),(r['category'],k,x[k],g[k])
  cc=next(c for c in census if(c['category'],c['base_procedure_id'])==(r['category'],unit(x['procedure_id'])));assert cc['eligible_for_owner_capture_package'];assert r['raw_numerical_leader']==dec[r['category']]['current_numerical'];assert r['owner_admission']=='NOT_OBSERVED'and not any(r[k]for k in('merged','deployed','served_values_verified'));assert r['new_G_threshold_policy_future_state']=='UNCAPTURED_PROSPECTIVELY_NEW_IDENTITY';assert r['option_state']=='MODEL_SOURCE_PACKAGE_AVAILABLE_NOT_ALL_OPERATIONAL_CHECKS_PASSED';proof.append(dict(category=r['category'],procedure_id=x['procedure_id'],history_regime=x['history_regime'],product_id=x['product_id'],source_test_id=x['source_test_id'],model_source_metadata_available=True,operational_admission='NOT_OBSERVED'))
 own=read(pub/'FINAL_OWNER_AND_CAPTURE_METADATA_READBACK.json');assert own['read_only']and not any(own[k]for k in('new_capture_execution_observed','owner_admission_observed','served_change_verified','new_job_dispatches'));assert own['owner_acknowledgement'].startswith('NOT_OBSERVED')
 report=dict(state='PASS_INDEPENDENT_EXACT_CATEGORY_REVIEW_BINDINGS_NO_RELEASE_ADMISSION',category_packages_sha256=sha(pub/'CATEGORY_RELEASE_PACKAGES.json'),correction_receipt_sha256=sha(pub/'CATEGORY_RELEASE_OPTION_CORRECTION_RECEIPT.json'),source_grid_sha256=sha(pub/'roster/finite-v2/CURRENT_METHOD_COMPARISONS.json'),source_census_sha256=sha(pub/'UPCOMING_CATEGORY_CAPTURE_STATUS.json'),owner_readback_sha256=sha(pub/'FINAL_OWNER_AND_CAPTURE_METADATA_READBACK.json'),source_bound_options=len(proof),candidates=proof,admitted_categories=0,merged_categories=0,deployed_categories=0,served_verified_categories=0,approval_status='Prepared typed candidate packages for retained-owner review; operational checks and admission remain unmet. No unilateral release.',new_fits=0,new_inference=0,new_grades=0,limitations=['Available-model/source metadata does not replace deterministic runtime, consumer/fallback/staleness/rollback checks.','ArchivedR0/currentserved comparisons and later scientificvalidation retain exact originalscope; no pointprofitability claim.','Chart labels remain qualifiedpartialcomponents; probabilitypolicy is separate from numericMAE.','New G reconstruction/selection identities are not prospectively captured by oldbaseforecast packets.'])
 with a.output.open('x')as f:json.dump(report,f,indent=2);f.write('\n')
 print(json.dumps({k:v for k,v in report.items()if k not in('candidates','limitations')}))
if __name__=='__main__':main()
