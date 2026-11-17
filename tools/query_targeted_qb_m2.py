"""Owner-local exact-line adapter over immutable saved M2 predictions.

Caller supplies permitted canonical opportunity rows. Output contains offers:
retain it only in the caller's approved private route, never public research Git.
This is not current inference, original issuance, a grader or a selector.
"""
import argparse,gzip,hashlib,json,math,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from nfl_v2.targeted_qb_m2 import restore_law
from nfl_v2.player_context_matchup import exact_probabilities

def read(p):
    b=p.read_bytes();return json.loads(gzip.decompress(b)if p.suffix=='.gz'else b)
def lookup(directory,method):
    out={}
    for p in sorted(directory.glob('*.json.gz')):
        if not p.name.startswith('2026-'):continue
        body=read(p);digest=hashlib.sha256(p.read_bytes()).hexdigest()
        for r in body['rows']:
            if r['method']!=method:continue
            key=(r['game_id'],r['player_id'],r['target'])
            if key in out:raise ValueError('Duplicate saved forecast identity')
            out[key]=(r,dict(artifact=p.name,sha256=digest,row_sha256=hashlib.sha256(json.dumps(r,sort_keys=True,separators=(',',':')).encode()).hexdigest()))
    return out
def project(q,item,policy):
    base={k:q.get(k)for k in ('game_id','player_id','target','season','week','line','source','book','decision_cutoff')}
    if item is None:return dict(base,status='UNAVAILABLE_SAVED_FORECAST',side=None,probabilities=None)
    r,binding=item
    for f in ('season','week'):
        if q.get(f)is not None and q[f]!=r[f]:raise ValueError('Saved forecast season/week conflict')
    line=float(q['line'])
    if not math.isfinite(line):raise ValueError('Nonfinite line')
    if policy=='P2_STATISTICAL_LAW':
        law=restore_law(r['law']);probs=exact_probabilities(law,line)
        side='OVER'if probs['over']>probs['under']else'UNDER'if probs['under']>probs['over']else'ABSTAIN'
        point=None
    else:
        field='mean'if policy=='P1_MEAN'else'lower_median';point=float(r[field]);probs=None
        if not math.isfinite(point):raise ValueError('Nonfinite typed point')
        side='OVER'if point>line else'UNDER'if point<line else'ABSTAIN'
    return dict(base,status='SAVED_HISTORICAL_OUTPUT_AVAILABLE',procedure_id=r['procedure_id'],method=r['method'],
      policy=policy,typed_point=point,probabilities=probs,side=side,fallback=r.get('fallback'),
      source_binding=binding,fit_cutoff=r['fit_cutoff'],feature_cutoff=r['feature_cutoff'],
      source_vintage='CURRENT_VINTAGE_SEVEN_DAY_RECONSTRUCTION',original_issuance=False,
      limitation='Caller must independently qualify offers/outcomes/clocks/rights; this adapter creates no historical availability, venue settlement or primary admission.')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--predictions',type=pathlib.Path,required=True);p.add_argument('--queries',type=pathlib.Path,required=True)
    p.add_argument('--output',type=pathlib.Path,required=True);p.add_argument('--method',required=True)
    p.add_argument('--policy',choices=['P1_MEAN','P1_LOWER_MEDIAN','P2_STATISTICAL_LAW'],required=True);a=p.parse_args()
    if a.output.resolve().is_relative_to(ROOT):raise ValueError('Private opportunity output cannot be written in public V2 tree')
    qs=read(a.queries);qs=qs['rows']if isinstance(qs,dict)else qs
    if not isinstance(qs,list)or len(qs)>20000:raise ValueError('Bounded opportunity list required')
    saved=lookup(a.predictions,a.method);rows=[]
    for q in qs:
        if q['target']not in ('pass_cmp','pass_att'):raise ValueError('Exact target contract required')
        rows.append(project(q,saved.get((q['game_id'],q['player_id'],q['target'])),a.policy))
    with a.output.open('x')as f:json.dump(dict(rows=rows,kind='OWNER_LOCAL_SAVED_OUTPUT_EXACT_LINE_PROJECTION_NOT_GRADES'),f,separators=(',',':'),allow_nan=False)
    print(json.dumps({'queries':len(qs),'available':sum(r['status']=='SAVED_HISTORICAL_OUTPUT_AVAILABLE'for r in rows),'method':a.method,'policy':a.policy,'new_fits':0,'new_original_decisions':0}))
