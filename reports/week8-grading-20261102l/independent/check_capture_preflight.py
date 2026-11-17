"""Research-capture byte/receipt audit only; no forecast or outcome scalar parsing."""
import argparse,datetime,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_bytes())
def main():
 a=argparse.ArgumentParser();a.add_argument('--private-root',type=Path,required=True);args=a.parse_args()
 # Private runtime paths are selectors, never published as source locators.
 cases=[
 ('EARLY_EMPIRICAL','week8-shadow-v2/shadow-forecasts.json.gz','reports/continuation-20261029/week8-shadow-v2/CAPTURE_RECEIPT.json','private_forecast_sha256'),
 ('EARLY_HGB','hgb-history-v1/WEEK8_SHADOWS.json.gz','reports/continuation-20261029/hgb-history-v1/WEEK8_CAPTURE_RECEIPT.json','packet'),
 ('COMMON_ASOF_EMPIRICAL','empirical-common-asof-shadow-v1/shadow-forecasts.json.gz','reports/continuation-20261030/empirical-common-asof-shadow-v1/CAPTURE_RECEIPT.json','private_forecast_sha256'),
 ('DISTRIBUTION_WAVE','distribution-wave-v2/WEEK8_OPEN_T90_SHADOWS.json.gz','reports/continuation-20261030/distribution-wave-v2/WEEK8_CAPTURE_RECEIPT.json','packet'),
 ('COUNT_ABLATION','count-ablation-wave-v1/WEEK8_OPEN_T90_SHADOWS.json.gz','reports/continuation-20261030/count-ablation-wave-v1/WEEK8_CAPTURE_RECEIPT.json','packet'),
 ('CHART_WAVE','chart-wave-v1/WEEK8_CHART_SHADOWS.json.gz','reports/continuation-20261030/chart-wave-v1/WEEK8_CAPTURE_RECEIPT.json','packet'),
 ('AVAILABILITY_AB','availability-wave-v1/AB-STAGED_SHADOWS.json.gz','reports/continuation-20261030b/availability-wave-v1/AB-RUN_RECEIPT.json','packet'),
 ('AVAILABILITY_C','availability-wave-v1/C-STAGED_SHADOWS.json.gz','reports/continuation-20261030b/availability-wave-v1/C-RUN_RECEIPT.json','packet'),
 ('C02','c02-future-shadow-v1/STAGED_SHADOWS.json.gz','reports/continuation-20261030b/c02-future-shadow-v1/RUN_RECEIPT.json','packet'),
 ('STRICT_HGB','strict-hgb-future-v1/STAGED_SHADOWS.json.gz','reports/continuation-20261030c/strict-hgb-future-v1/EXPORT_RECEIPT.json','source_packet_sha256'),
 ('D1_D2','continuation-20261030c/SMALL_AND_DEFENSE_STAGING/qualified-defense-information-v1/WEEK8_PAIRED_SHADOWS.json.gz','reports/continuation-20261030c/qualified-defense-information-v1/WEEK8_CAPTURE_RECEIPT.json','packet')]
 proofs=[]
 for tag,relative,public,key in cases:
  path=args.private_root/relative;source=ROOT/public;receipt=read(source);expected=receipt[key]['sha256']if key=='packet'else receipt[key];assert sha(path)==expected
  expected_bytes=receipt[key].get('bytes')if key=='packet'else receipt.get('private_forecast_bytes')
  if expected_bytes is not None:assert path.stat().st_size==expected_bytes
  proofs.append({'capture_version':tag,'capture_receipt':public,'capture_receipt_sha256':sha(source),'forecast_sha256':expected,'forecast_bytes':path.stat().st_size,'local_bytes_equal_saved_capture':True})
 bind=read(args.private_root/'hgb-history-v1/GRADING_BINDINGS.json');assert sha(args.private_root/'hgb-history-v1/GRADING_BINDINGS.json')=='319272d2cce01ed3573817bc5021af70753a50947fa6b7809f5acf32850f0a0b'
 out={'state':'PASS_11_SPECIFIED_RESEARCH_CAPTURE_BYTE_BINDINGS_NOT_NEW_GRADES','at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'parent_protocol_sha256':sha(HERE.parent/'FROZEN_GRADING_PROTOCOL_V1.json'),'captures':proofs,'HGB_original_binding_manifest_verified':True,'forecast_or_outcome_values_parsed':0,'Week8_labels_or_scores_inspected':0,'new_model_calls_or_transfers':0,'qualification':'This scoped research packet census does not count website/list versions, every historical method, new fits or independent NFL observations. Local byte equality is not a new off-host restoration proof; use original accepted restoration receipts. Existing packets and all histories/output functionals remain separate.','checker_sha256':sha(__file__)}
 with(HERE/'CAPTURE_BYTE_PREFLIGHT_REVIEW_V1.json').open('x')as f:json.dump(out,f,indent=2);f.write('\n')
 print(json.dumps({'state':out['state'],'verified_capture_versions':len(proofs),'forecast_values_parsed':0,'outcomes_read':0}))
if __name__=='__main__':main()
