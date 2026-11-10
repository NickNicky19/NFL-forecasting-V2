"""Independent Decimal arithmetic for prefit control review; no raw offer export."""
import csv,gzip,hashlib,importlib.util,json,math
from collections import defaultdict,Counter
from decimal import Decimal
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).resolve().parent

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dig(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def key(r):return r['game_id'],r['player_id'],r['target']
def number(v):
 try:
  x=Decimal(str(v));return x if x.is_finite()else None
 except Exception:return None

def aggregate(pairs):
 counts={s:Counter()for s in('over','under','Combined')};errors=[]
 for offer,value in pairs:
  p,l,y=map(number,[value,offer['line'],offer['actual']])
  if p is None:counts['Combined']['unavailable']+=1;continue
  if y is not None:errors.append(float(abs(p-y)))
  side='over'if p>l else'under'if p<l else None
  if side is None:counts['Combined']['abstain']+=1;continue
  state='unknown'if y is None else'push'if y==l else'win'if(side=='over')==(y>l)else'loss'
  counts[side][state]+=1;counts['Combined'][state]+=1
 out={s:dict(c,decided=c['win']+c['loss'],rate=c['win']/(c['win']+c['loss'])if c['win']+c['loss']else None)for s,c in counts.items()}
 return dict(side_counts=out,available=len(pairs),games=len({r['game_id']for r,v in pairs}),weeks=sorted({r['week']for r,v in pairs}),mae=sum(errors)/len(errors)if errors else None)

spec=importlib.util.spec_from_file_location('qualified_offer_reader',ROOT/'reports/player-context-matchup-01/B/independent/inventory_retained_qb_offers_v1.py');reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)
source_paths=json.load(open('/tmp/b-context-offer-sources.json'))
offers=[r for w,p in sorted(source_paths.items())for r in reader.iter_offers(Path(p),int(w))]
assert len(offers)==224 and len({key(r)for r in offers})==224
board={key(r):r for r in offers}
result=dict(check_id='B-PROFILE-INCREMENT-PREFIT-INDEPENDENT-CONTROL-REVIEW-v1',root_head='613800b90396e98ae0898b18930e61bffa6639f0',calculation='Decimal comparisons of retained unrounded points versus retained line and qualified actual; no author scoring or summary function called. Existing qualified offer parser reused only for input contract.',source_sha256=sorted(sha(p)for p in source_paths.values()),board_id_sha256=dig(sorted([list(key(r))+[str(r['line'])]for r in offers])),board_counts={t:len([r for r in offers if r['target']==t])for t in('pass_att','pass_cmp')},results=[])
for target in('pass_att','pass_cmp'):
 rr=[r for r in offers if r['target']==target]
 for method,field in [('SAVED_ADJUSTED','prediction'),('SAVED_RAW','raw_prediction')]:result['results'].append(dict(method=method,target=target,history='ARCHIVED_FIXED_SOURCE',product='saved_precision_point',**aggregate([(r,r.get(field))for r in rr])))
 for method,point in [('ALWAYS_OVER',10**6),('ALWAYS_UNDER',-10**6)]:result['results'].append(dict(method=method,target=target,history='SAME_BOARD',product='constant_direction',**aggregate([(r,point)for r in rr])))
forecast_groups=defaultdict(dict)
for path in sorted((ROOT/'reports/player-context-matchup-01/B/qb-wave-v1/predictions').glob('2026-W*.json.gz')):
 payload=json.load(gzip.open(path,'rt'))
 for r in payload['rows']:
  if key(r)in board and r['method']in('E0','E1','E2','E3','P1','P2','P3','COMMON_EXPOSURE'):
   for product in('mean','lower_median'):forecast_groups[(r['procedure_id'],'H-RECENT',product,r['target'])][key(r)]=r[product]
for g,entries in forecast_groups.items():
 proc,hist,product,target=g;result['results'].append(dict(method=proc,target=target,history=hist,product=product,**aggregate([(board[k],v)for k,v in entries.items()])))
# Current retained 2026 file only; 2025 source cannot cover any offered game key.
retained_paths=json.load(open('/tmp/b-context-retained-control-paths.json'))
current=[p for p in retained_paths if 'seasonal-rolling-2025'not in str(p)]
result['retained_source_sha256']=[sha(p)for p in current]
old=defaultdict(dict)
for path in current:
 with gzip.open(path,'rt')as f:
  for r in csv.DictReader(f):
   if key(r)not in board or r['position']!='QB':continue
   if r['product_id']not in('mean','lower_median'):continue
   v=number(r['prediction'])
   if v is None:continue
   g=(r['procedure_id'],r['history_regime'],r['product_id'],r['target'])
   assert key(r)not in old[g]
   old[g][key(r)]=str(v)
for g,entries in old.items():
 proc,hist,product,target=g;result['results'].append(dict(method=proc,target=target,history=hist,product=product,**aggregate([(board[k],v)for k,v in entries.items()])))
result['limitations']=['Owner-local protected board was inspected; only deterministic permitted aggregates and hashes retained publicly. No C private-row parity or admission implied.','Timing-unverified actual-line diagnostics; current revised football source, seven-day proxy; not issued selections, settlement or profit.','Retained old families cover only W5-7 subset; no C02 current offered coverage. Do not rank84-row result against112-row total.','This is prefit control review and independent verification, zero new fit, zero new forecast, zero new actual-line week.']
body=json.dumps(result,indent=2,allow_nan=False)+'\n';dest=OUT/'PREFIT_CONTROL_REVIEW_V1.json';assert not dest.exists();dest.write_text(body)
for r in result['results']:
 if r['history']=='H-RECENT' or r['history']=='ARCHIVED_FIXED_SOURCE':
  c=r['side_counts']['Combined'];print(r['target'],r['method'],r['history'],r['product'],c,r['available'])
