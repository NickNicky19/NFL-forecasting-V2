"""Derived paired MAE only; existing native control metrics are reused."""
import csv,gzip,hashlib,importlib.util,json,math,sys
from decimal import Decimal
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];OUT=Path(__file__).resolve().parent;BASE=OUT.parent
sys.path.insert(0,str(ROOT))
from nfl_v2.paired_uncertainty import paired_losses
def read(p):
 p=Path(p);b=p.read_bytes();return json.loads(gzip.decompress(b)if p.suffix=='.gz'else b)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dig(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def key(r):return r['game_id'],r['player_id'],r['target']
def dec(v):
 result=Decimal(str(v));assert result.is_finite();return result
spec=importlib.util.spec_from_file_location('retained_offers',ROOT/'reports/player-context-matchup-01/B/independent/inventory_retained_qb_offers_v1.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
offerpaths=read('/tmp/b-context-offer-sources.json');offers={key(r):r for w,p in sorted(offerpaths.items())for r in m.iter_offers(Path(p),int(w))if r['target']=='pass_cmp'};assert len(offers)==112
predictions={};prediction_sources=[]
for p in sorted((BASE/'aligned-wave-v1/predictions').glob('2026-W*.json.gz')):
 if int(p.name[6:8])not in range(5,9):continue
 prediction_sources.append(dict(path=str(p.relative_to(ROOT)),sha256=sha(p)))
 for r in read(p)['rows']:
  if r['method']in('F2','F3')and key(r)in offers:
   assert dec(r['actual'])==dec(offers[key(r)]['actual']);predictions[r['method'],key(r)]=r
reference_path=ROOT/'reports/profile-increment-to-release-01/B/independent/PREFIT_CONTROL_REVIEW_V1.json';references=read(reference_path)['results']
strict={};archive_hashes=[];control_id='v2-distribution-controls-reconstruction-v2:ordered_leaf_cdf:strict-current-inputs'
for p in read('/tmp/b-context-retained-control-paths.json'):
 if'seasonal-rolling-2025'in str(p):continue
 archive_hashes.append(sha(p))
 with gzip.open(p,'rt')as f:
  for r in csv.DictReader(f):
   if key(r)not in offers or r['position']!='QB'or r['history_regime']!='H-CURRENT'or r['procedure_id']!=control_id or r['product_id']not in('mean','lower_median'):continue
   k=r['product_id'],key(r);assert k not in strict and dec(r['actual'])==dec(offers[key(r)]['actual']);strict[k]=r
assert len(strict)==168
result=[]
for arm in('F2','F3'):
 for product in('mean','lower_median'):
  for control in('SAVED_ADJUSTED','SAVED_RAW',control_id):
   keys=sorted(offers)if control!=control_id else sorted(k for p,k in strict if p==product)
   candidate=[];comparator=[];games=[];weeks=[]
   for k in keys:
    row=offers[k];pred=predictions[arm,k];actual=dec(row['actual']);value=strict[product,k]['prediction']if control==control_id else row['prediction'if control=='SAVED_ADJUSTED'else'raw_prediction']
    candidate.append(float(abs(dec(pred[product])-actual)));comparator.append(float(abs(dec(value)-actual)));games.append(row['game_id']);weeks.append((2026,row['week']))
   pair=paired_losses(candidate,comparator,weeks,games)
   reference=next(r for r in references if r['target']=='pass_cmp'and r['method']==control and r['product']==(product if control==control_id else'saved_precision_point')and r['history']==('H-CURRENT'if control==control_id else'ARCHIVED_FIXED_SOURCE'))
   assert len(keys)==reference['available']and abs(pair['comparator_error']-reference['mae'])<1e-10
   result.append(dict(kind='NUMERICAL_PAIRED_MAE',season=2026,target='pass_cmp',window='MATCHED_OFFERS_W5_W8',actual_weeks=sorted({r[1]for r in weeks}),candidate='B-QB-ALIGNED-FRESHNESS-v1:'+arm,control=control,product=product,control_product=product if control==control_id else'saved_precision_point',control_functional='TYPED_LEAF_MEAN_OR_LOWER_MEDIAN'if control==control_id else'FUNCTIONAL_AND_ORIGINAL_ISSUANCE_UNVERIFIED_RETAINED_PRECISION_POINT',scope='EXACT_COMPATIBLE_RETAINED_OFFERED_PLAYER_MASK',shared_mask_sha256=dig(sorted([list(k)+[str(offers[k]['line'])]for k in keys])),eligible_offers=112,shared_rows=len(keys),rows_outside_shared_panel=112-len(keys),candidate_evidence='CURRENT_REVISED_SOURCE_48H_RECONSTRUCTED_TIMING_SENSITIVITY_UNVERIFIED_QUOTES',control_evidence='RETAINED_STRICT_CURRENT_7D_RECONSTRUCTION'if control==control_id else'ARCHIVED_REFERENCE_POINT_ISSUANCE_AND_FUNCTIONAL_UNVERIFIED',comparison_limit='Complete-procedure numerical comparison on identical player/game/outcome rows; no isolated learner, freshness, expected-mean or original-issuance attribution.',reused_control_metric_source=str(reference_path.relative_to(ROOT)),reused_control_metric_source_sha256=sha(reference_path),new_predictions=0,new_native_scores=0,**pair))
dest=OUT/'NUMERICAL_STRONG_SAVED_CONTROL_PAIRS_V1.json';assert not dest.exists();dest.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
receipt=dict(id='B-NUMERICAL-STRONG-CONTROLS-DERIVED-PAIR-RECEIPT-v1',paired_artifact_sha256=sha(dest),derived_pairs=len(result),existing_control_metric_source_sha256=sha(reference_path),offer_source_sha256=sorted(sha(p)for p in offerpaths.values()),strict_control_archive_sha256=archive_hashes,candidate_prediction_sources=prediction_sources,reused_native_control_metrics=True,new_fits=0,new_predictions=0,new_native_scores=0,new_NFL_calendar_weeks=0,restricted_rows_exported=False,calculation='Independent Decimal absolute errors versus existing qualified labels; standard registered paired-loss uncertainty helper applied to those separately calculated arrays. Four/threeweeks are insufficient for the registered week bootstrap; game sensitivity only.',limits=['Savedraw/adjusted sourcepoint functional and actual original issuance not verified; do not relabel them expectedmean or live served incumbent.','StrictCURRENT native controls use a different complete history/feature policy and only84sharedrows; own112/84percentages are not directly ranked.','Observed paired loss does not establish permanent superiority or authorize a production switch.'])
(OUT/'NUMERICAL_STRONG_CONTROL_RECEIPT_V1.json').write_text(json.dumps(receipt,indent=2)+'\n')
for r in result:print(r['candidate'],r['product'],r['control'],'n',r['n'],'MAEs',r['candidate_error'],r['comparator_error'],'delta',r['delta'],'SE95',r['game_normal95_sensitivity'])
