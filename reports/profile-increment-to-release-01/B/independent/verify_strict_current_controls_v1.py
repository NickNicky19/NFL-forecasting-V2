"""Shared-mask verification for retained stricter-history controls; no row export."""
import csv,gzip,hashlib,importlib.util,json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).resolve().parent
def read(p):
    p=Path(p)
    return json.loads(gzip.decompress(p.read_bytes())if p.suffix=='.gz'else p.read_bytes())
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def key(r):return r['game_id'],r['player_id'],r['target']
def side(point,line):return 'over'if Decimal(str(point))>Decimal(str(line))else'under'if Decimal(str(point))<Decimal(str(line))else None
def grade(point,offer):
    s=side(point,offer['line']);actual=Decimal(str(offer['actual']));line=Decimal(str(offer['line']))
    return None if s is None or actual==line else (s=='over')==(actual>line)
def aggregate(points,board):
    c={s:dict(win=0,loss=0,push=0,abstain=0)for s in('over','under','Combined')}
    for k,p in points.items():
        r=board[k];s=side(p,r['line']);g=grade(p,r)
        if s is None:c['Combined']['abstain']+=1;continue
        state='push'if g is None else'win'if g else'loss'
        c[s][state]+=1;c['Combined'][state]+=1
    for x in c.values():x['decided']=x['win']+x['loss'];x['rate']=x['win']/x['decided']if x['decided']else None
    return dict(sides=c,rows=len(points),games=len({board[k]['game_id']for k in points}),weeks=sorted({board[k]['week']for k in points}),mask_sha256=digest(sorted([list(k)+[str(board[k]['line'])]for k in points])))

sp=importlib.util.spec_from_file_location('offer_reader',ROOT/'reports/player-context-matchup-01/B/independent/inventory_retained_qb_offers_v1.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
board={key(r):r for w,p in read('/tmp/b-context-offer-sources.json').items()for r in m.iter_offers(Path(p),int(w))}
new={}
for p in sorted((ROOT/'reports/player-context-matchup-01/B/qb-wave-v1/predictions').glob('2026-W*.json.gz')):
    for r in read(p)['rows']:
        if key(r)in board and r['method']in('E3','COMMON_EXPOSURE'):
            for product in('mean','lower_median'):new[(r['target'],product,key(r))]=r[product]
old=defaultdict(dict);fallback=defaultdict(int)
for p in read('/tmp/b-context-retained-control-paths.json'):
    if 'seasonal-rolling-2025'in str(p):continue
    with gzip.open(p,'rt')as f:
        for r in csv.DictReader(f):
            if key(r)not in board or r['position']!='QB'or r['history_regime']!='H-CURRENT'or r['family']!='ordered_leaf_cdf'or'strict-current-inputs'not in r['procedure_id']or r['product_id']not in('mean','lower_median'):continue
            if 'reconstruction-v2:'not in r['procedure_id']:continue
            assert Decimal(r['actual'])==Decimal(str(board[key(r)]['actual']))
            group=r['target'],r['product_id'];assert key(r)not in old[group]
            old[group][key(r)]=r['prediction'];fallback[group]+=r['fallback']not in('none','NONE','learned','NOT_APPLICABLE','')
rows=[]
for(target,product),points in old.items():
    ref=aggregate(points,board)
    row=dict(target=target,retained_procedure='v2-distribution-controls-reconstruction-v2:ordered_leaf_cdf:strict-current-inputs',history='H-CURRENT strict feature memory/priors',product=product,retained=ref,reported_fallback_rows=fallback[target,product],controls=[])
    for method in('SAVED_ADJUSTED','SAVED_RAW','E3'if target=='pass_cmp'else'COMMON_EXPOSURE','ALWAYS_OVER','ALWAYS_UNDER'):
        products=('mean','lower_median')if method in('E3','COMMON_EXPOSURE')else('saved_precision_point',)
        for cp in products:
            control={k:board[k]['prediction'if method=='SAVED_ADJUSTED'else'raw_prediction']if method in('SAVED_ADJUSTED','SAVED_RAW')else 1000000 if method=='ALWAYS_OVER'else-1000000 if method=='ALWAYS_UNDER'else new[target,cp,k]for k in points}
            ca=aggregate(control,board);paired=[(grade(points[k],board[k]),grade(control[k],board[k]))for k in points]
            row['controls'].append(dict(method=method,product=cp,**ca,candidate_only_correct=sum(a is True and b is False for a,b in paired),control_only_correct=sum(a is False and b is True for a,b in paired)))
    rows.append(row)
payload=dict(id='B-PROFILE-INCREMENT-STRICT-CURRENT-SHARED-MASK-REVIEW-v1',calculation='Independent Decimal point/line/actual comparisons; author scorer not called; old/current outcome equality asserted rowwise.',results=rows,limits=['H-CURRENT strict-input control and new H-RECENT E3 differ in history policy; this is a complete-system comparator, not isolated profile effect.','Only W5-7 retained offers; cannot inherit W8 coverage or compare own84 percentage with full112 percentage.','Reported fallback status is kept separate; no assertion of learned-only improvement.','Owner-local protected records remain private; aggregates do not establish C raw-row parity or admission.'])
dest=OUT/'STRICT_CURRENT_SHARED_MASK_REVIEW_V1.json';assert not dest.exists();dest.write_text(json.dumps(payload,indent=2,allow_nan=False)+'\n')
for row in rows:
    print(row['target'],row['product'],'strict',row['retained']['sides']['Combined'],'fallback',row['reported_fallback_rows'])
    for c in row['controls']:print('control',c['method'],c['product'],c['sides']['Combined'])
