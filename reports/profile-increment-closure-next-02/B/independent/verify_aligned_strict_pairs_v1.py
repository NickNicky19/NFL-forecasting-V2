"""Independent exact-line row grades against retained strongest84-row control."""
import csv,gzip,hashlib,importlib.util,json,math
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];OUT=Path(__file__).resolve().parent;WAVE=OUT.parent/'aligned-wave-v1'
def read(p):
    p=Path(p);b=p.read_bytes();return json.loads(gzip.decompress(b)if p.suffix=='.gz'else b)
def key(r):return r['game_id'],r['player_id'],r['target']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def cdf(law,x):
    y=math.floor(x);return(1-law['mixture'])*math.fsum(w for s,w in zip(law['support'],law['weights'])if s<=y)+law['mixture']*(0. if y<0 else 1-law['prior']['q']**(y+1))
def event_side(r,line):
    under=cdf(r['law'],math.ceil(line)-1);over=1-cdf(r['law'],math.floor(line))
    return'over'if over>under else'under'if under>over else None
def point_side(p,l):return'over'if Decimal(str(p))>Decimal(str(l))else'under'if Decimal(str(p))<Decimal(str(l))else None
def win(side,r):
    if side is None or Decimal(str(r['actual']))==Decimal(str(r['line'])):return None
    return(side=='over')==(Decimal(str(r['actual']))>Decimal(str(r['line'])))

spec=importlib.util.spec_from_file_location('offers',ROOT/'reports/player-context-matchup-01/B/independent/inventory_retained_qb_offers_v1.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
offers={key(r):r for w,p in read('/tmp/b-context-offer-sources.json').items()for r in m.iter_offers(Path(p),int(w))if r['target']=='pass_cmp'}
strict={};sources=[]
for p in read('/tmp/b-context-retained-control-paths.json'):
    if'seasonal-rolling-2025'in str(p):continue
    sources.append(sha(p))
    with gzip.open(p,'rt')as f:
        for r in csv.DictReader(f):
            if key(r)not in offers or r['position']!='QB'or r['history_regime']!='H-CURRENT'or r['product_id']!='mean'or r['procedure_id']!='v2-distribution-controls-reconstruction-v2:ordered_leaf_cdf:strict-current-inputs':continue
            assert key(r)not in strict;assert Decimal(r['actual'])==Decimal(str(offers[key(r)]['actual']));strict[key(r)]=r
assert len(strict)==84
forecasts={(r['method'],key(r)):r for p in sorted((WAVE/'predictions').glob('2026-W*.json.gz'))for r in read(p)['rows']if key(r)in strict}
result=[]
for arm in('F2','F3'):
    for control in('STRICT_CURRENT_LEAF_MEAN','SAVED_ADJUSTED'):
        rr=[];side_counts={s:dict(wins=0,losses=0)for s in('over','under')}
        for k,b in strict.items():
            r=offers[k];pred=forecasts[arm,k];assert pred['actual']==r['actual'];cs=event_side(pred,r['line']);bs=point_side(b['prediction']if control=='STRICT_CURRENT_LEAF_MEAN'else r['prediction'],r['line'])
            a,z=win(cs,r),win(bs,r);assert a is not None and z is not None
            side_counts[cs]['wins'if a else'losses']+=1;rr.append((r,a,z,cs,bs))
        n=len(rr);ae=sum(not a for r,a,b,cs,bs in rr)/n;be=sum(not b for r,a,b,cs,bs in rr)/n;delta=ae-be
        groups=defaultdict(list)
        for r,a,b,cs,bs in rr:groups[r['game_id']].append(float(not a)-float(not b))
        se=math.sqrt(len(groups)/(len(groups)-1)*sum((sum(v)-delta*len(v))**2 for v in groups.values()))/n
        result.append(dict(kind='OFFER_DIRECTION_PAIRED_LOSS',season=2026,window='ALL',candidate=arm,control='v2-distribution-controls-reconstruction-v2:ordered_leaf_cdf:strict-current-inputs'if control=='STRICT_CURRENT_LEAF_MEAN'else'SAVED_ADJUSTED',policy='P2_STATISTICAL_LAW',control_policy='P1_MEAN_UNROUNDED'if control=='STRICT_CURRENT_LEAF_MEAN'else'REGISTERED_SAVED_PRECISION_POINT',n=n,candidate_error=ae,comparator_error=be,delta=delta,relative_error_change=delta/be if be else None,relative_error_missing_reason=None if be else 'zero_comparator_error_denominator',candidate_wins=sum(a for r,a,b,cs,bs in rr),control_wins=sum(b for r,a,b,cs,bs in rr),candidate_only_correct=sum(a and not b for r,a,b,cs,bs in rr),control_only_correct=sum(b and not a for r,a,b,cs,bs in rr),own_selected_sides=side_counts,week_clusters=len({r['week']for r,a,b,cs,bs in rr}),actual_weeks=sorted({r['week']for r,a,b,cs,bs in rr}),game_clusters=len(groups),week_interval=None,week_interval_status='INSUFFICIENT_WEEK_CLUSTERS',game_cluster_sensitivity_se=se,game_normal95_sensitivity=[delta-1.96*se,delta+1.96*se],status='FINITE_PAIRED_LOSS_COMPARISON',selection_limit='Descriptive exposed-development sample, not selection/multiplicity adjusted; not parity admission.',history_limit='Candidate H-RECENT aligned48h olderfeaturememory versus stricterCURRENT7dcontrol; complete-system comparator, not isolated clock/history effect.',evidence='CURRENT_REVISED_SOURCE_48H_RECONSTRUCTED_TIMING_SENSITIVITY_UNVERIFIED_QUOTES',shared_mask_sha256=digest(sorted([list(k)+[str(offers[k]['line'])]for k in strict])),restricted_row_export=False))
dest=OUT/'NEW_ARM_STRICT_CURRENT_PAIRS_V1.json';assert not dest.exists();dest.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
receipt=dict(id='B-ALIGNED-NEW-ARMS-STRONG84-INDEPENDENT-RECEIPT-v1',pair_artifact_sha256=sha(dest),retained_source_sha256=sources,score_path='Independent Decimal original-line/actual/point comparison and independently derived exact-law tails. Existing common scorer and author summary function were not called.',rows=len(result),new_fits=0,new_forecasts=0,private_rows_exported=False)
(OUT/'NEW_ARM_STRICT_CURRENT_PAIRS_RECEIPT_V1.json').write_text(json.dumps(receipt,indent=2)+'\n')
for r in result:print(r['candidate'],r['control'],r['candidate_wins'],r['control_wins'],r['n'],r['delta'])
