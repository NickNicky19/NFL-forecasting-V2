#!/usr/bin/env python3
"""Account for located procedure references without inventing runnable methods."""
import json,csv,pathlib,collections
ROOT=pathlib.Path(__file__).resolve().parents[1]
def main():
 out=ROOT/'reports/continuation-20261029';refs=json.loads((ROOT/'registries/PROCEDURE_REFERENCES.json').read_text());rows=[]
 for r in refs:
  rows.append(dict(reference_id=r['reference_id'],procedure_label=r['procedure_label'],canonical_procedure_id=r.get('canonical_procedure_id'),target=r['target'],product=r['product_id'],history_regime='ORIGINAL_CONTRACT_UNRESOLVED',state='BLOCKED_NO_QUALIFIED_EXACT_MODEL_QUERY_BINDING',issued_rows=None,accuracy=None,error=None,metric_reason='No authenticated future vector/exact adapter; reference labels are not distinct runnable models. Do not fill with unrelated controls.',source_id=r['source_id']))
 owner=json.loads((out/'WEEK8_CAPTURE_STATUS.json').read_text())
 for r in owner['by_category']:
  rows.append(dict(reference_id='OWNER-P2-'+r['category'],procedure_label='EXISTING_OWNER_SELECTED_WRAPPER',target=r['category'],product=';'.join(r.get('functionals',[])),history_regime='OWNER_ORIGINAL_CONTRACT',state='ORIGINAL_PUBLIC_SELECTED_FEED_RETAINED' if r.get('selected_rows_retained') else 'OWNER_TARGET_BLOCKED_OR_UNSUPPORTED',issued_rows=r.get('selected_rows_retained',0),accuracy=None,error=None,metric_reason='Week8 outcomes pending; underlying all-method vectors not censused; originals retained',source_id='OWNER-W8-ORIGINAL-PUBLIC-3907CA38'))
 shadow=json.loads((out/'week8-shadow-v2/PROCEDURE_MATRIX.json').read_text());groups=collections.defaultdict(collections.Counter)
 for r in shadow:
  key=r['target'],r['product'],r['history_regime'];groups[key][r['state']]+=r['rows']
  if r['state']=='ISSUED_SHADOW' and r['reason_or_fallback']!='none':groups[key]['fallback']+=r['rows']
 for (target,product,history),c in sorted(groups.items()):
  rows.append(dict(reference_id=f'V2-W8-{target}-{product}-{history}',procedure_label='v2-week8-empirical-history-shadow-v2',canonical_procedure_id='empirical-per-player-history-control',target=target,product=product,history_regime=history,state='ISSUED_RESEARCH_SHADOW_WITH_ABSTENTIONS',issued_rows=c['ISSUED_SHADOW'],abstention_rows=c['ABSTAIN'],fallback_rows=c['fallback'],accuracy=None,error=None,metric_reason='PENDING_WEEK8_OUTCOMES; actual22:51:33UTC capture; CARGB past owner input cutoff; no official publication',source_id='V2-PRIVATE-WEEK8-0001'))
 rows.append(dict(reference_id='V2-W8-CHART-PPR',procedure_label='chartPPRfutureadapter',target='nick-chart-ppr-v1',product='displaypoint',state='BLOCKED_EXACT_COMPONENT_CURRENT_SOURCE_CONTRACT',issued_rows=0,accuracy=None,error=None,metric_reason='All16 component law/consumer contract unavailable; oldsitePPR different target'))
 hgb=json.loads((out/'hgb-history-v1/WEEK8_PROCEDURE_MATRIX.json').read_text())
 receipt=json.loads((out/'hgb-history-v1/WEEK8_CAPTURE_RECEIPT.json').read_text())
 if hgb['source_prediction_sha256']!=receipt['packet']['sha256']:raise ValueError('HGB Week8 matrix/forecast binding mismatch')
 for r in hgb['rows']:
  target,product,history=r['target'],r['product'],r['history_regime']
  rows.append(dict(reference_id=f'V2-W8-HGB-{target}-{product}-{history}',procedure_label='hgb-direct-history-controls-v1',canonical_procedure_id='hgb-direct-history-controls-v1:'+product,target=target,product=product,history_regime=history,state='ISSUED_RESEARCH_SHADOW_WITH_ABSTENTIONS',issued_rows=r.get('FORECASTED',0),abstention_rows=r.get('ABSTAIN',0),fallback_rows=r.get('fallback_rows',0),late_owner_input_cutoff_rows=r.get('LATER_THAN_OWNER_INPUT_CUTOFF',0),accuracy=None,error=None,metric_reason='PENDING_WEEK8_OUTCOMES; actual23:16:53UTC capture; CARGB past owner input cutoff; no official publication',source_id='V2-PRIVATE-HGB-0001'))
 (out/'WEEK8_ALL_METHOD_STATUS.json').write_text(json.dumps(rows,indent=2)+'\n');keys=list(dict.fromkeys(k for r in rows for k in r))
 with (out/'WEEK8_ALL_METHOD_STATUS.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)
 print(json.dumps({'rows':len(rows),'by_status':dict(collections.Counter(r['state'] for r in rows)),'reference_rows_are_not_distinct_methods':True}))
if __name__=='__main__':main()
