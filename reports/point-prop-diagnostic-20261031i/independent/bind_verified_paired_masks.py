"""Bind already verified paired comparisons to exact retained masks; no new losses."""
import argparse,collections,gzip,hashlib,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent;PUB=HERE.parent/'point-offer/v1'
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def canon(z):return json.dumps(z,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--private-root',type=Path,required=True);ap.add_argument('--receipt',type=Path,default=HERE/'PAIRED_MASK_BINDINGS_V1.json');a=ap.parse_args();prior=read(HERE/'POINT_OFFER_INDEPENDENT_REVIEW_V1.json');assert prior['state'].startswith('PASS_');assert sha(PUB/'SCORES.json')==prior['score_sha256']
    run=read(PUB/'RUN_RECEIPT.json');file=a.private_root/'point-prop-diagnostic-20261031i-point-offer-v1/POINT_DIAGNOSTIC_ROWS.json.gz';assert sha(file)==run['private_sha256'];data=collections.defaultdict(dict)
    for r in json.loads(gzip.decompress(file.read_bytes()))['rows']:
        if not r.get('population_diagnostic'):data[tuple(r['recipe'])][r['week'],r['source_row_index']]=r
    scores=read(PUB/'SCORES.json');points={}
    for i,s in enumerate(scores):
        if s['record_kind']=='forecast_evaluation_view':points[tuple(s[k]for k in ['target','procedure_id','history_regime','product_id']),s['membership_sha256']]=(i,s)
    rows=[];pairs=read(PUB/'PAIRED_MAE_COMPARISONS.json')
    for i,p in enumerate(pairs):
        key=(p['target'],*p['candidate_recipe']);fk=(p['target'],*p['comparator_recipe']);aa=data[key];bb=data[fk];qq=sorted(q for q in aa if aa[q]['admitted']and bb[q]['admitted']and(p['context']!='FOCAL_COMMON_LEARNED_ONLY'or aa[q]['fallback']==bb[q]['fallback']=='none'));assert all(aa[q]['actual']is not None and aa[q]['participation']=='VERIFIED_PLAYED_POSITIVE_PHYSICAL'for q in qq);assert len(qq)==p['n']
        for q in qq:assert all(aa[q][f]==bb[q][f]for f in ['game_id','player_id','target','line','actual','decision_time'])
        mh=hashlib.sha256(canon(qq)).hexdigest();idx,point=points[key,mh];fidx,fpoint=points[fk,mh];assert point['n']==fpoint['n']==p['n'];assert math.isclose(point['mae'],p['candidate_error'],abs_tol=1e-12)and math.isclose(fpoint['mae'],p['comparator_error'],abs_tol=1e-12)
        identityhash=hashlib.sha256(canon([(q[0],q[1],aa[q]['game_id'],aa[q]['player_id'],aa[q]['target'],aa[q]['line'],aa[q]['actual'],aa[q]['decision_time'])for q in qq])).hexdigest()
        rows.append(dict(paired_source_row_index=i,paired_source_artifact=(PUB/'PAIRED_MAE_COMPARISONS.json').relative_to(ROOT).as_posix(),paired_source_sha256=sha(PUB/'PAIRED_MAE_COMPARISONS.json'),target=p['target'],context=p['context'],candidate_recipe=p['candidate_recipe'],focal_recipe=p['comparator_recipe'],paired_n=p['n'],membership_sha256=mh,identity_label_cutoff_membership_sha256=identityhash,candidate_source_artifact=(PUB/'SCORES.json').relative_to(ROOT).as_posix(),candidate_source_sha256=sha(PUB/'SCORES.json'),candidate_source_row_index=idx,candidate_source_record_id=point['record_id'],focal_source_row_index=fidx,focal_source_record_id=fpoint['record_id'],source_metric='MAE',status='VERIFIED_EXACT_PAIRED_RETAINED_MASK'))
    assert len(rows)==68
    body=dict(state='INDEPENDENT_EXACT_PAIRED_MASK_BINDINGS_NO_NEW_LOSSES',identity='paired_source_row_index',source_score_sha256=sha(PUB/'SCORES.json'),source_pair_sha256=sha(PUB/'PAIRED_MAE_COMPARISONS.json'),row_membership_definition='Sorted (week, source_row_index); same stablegame/player/target/line/actual/decision clock independently verified. Focal and candidate source points both have this exact scored mask.',rows=rows,new_scores=0,new_fits=0,new_inference=0)
    with a.receipt.open('x')as f:json.dump(body,f,indent=2);f.write('\n')
    print(json.dumps(dict(state=body['state'],paired_rows=len(rows),binding_sha256=sha(a.receipt))))
if __name__=='__main__':main()
