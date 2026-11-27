"""Separate rank-sum AUC and reliability arithmetic on retained ALL-policy rows."""
import argparse,collections,gzip,hashlib,json,math
from pathlib import Path


def read(p):return json.loads(gzip.decompress(p.read_bytes())if p.suffix=='.gz'else p.read_bytes())
def auc(rows):
    groups=collections.defaultdict(lambda:[0,0])
    for r in rows:groups[r['probabilities']['over']][int(r['actual']>r['line'])]+=1
    positives=sum(v[1]for v in groups.values());negatives=sum(v[0]for v in groups.values())
    if not positives or not negatives:return None
    smaller_negatives=0;u=0.
    for p,(neg,pos)in sorted(groups.items()):u+=pos*smaller_negatives+.5*pos*neg;smaller_negatives+=neg
    return u/(positives*negatives)

def run(private,out):
    j=read(private);allrows=[r for r in j['rows']if r['selection_policy']=='ALL'];diagnostics=read(out/'DISCRIMINATION_RELIABILITY.json');assert len(diagnostics)==8;summary=[]
    for d in diagnostics:
        rr=[r for r in allrows if r['target']==d['target']and r['method_key'].endswith('::B'+str(d['arm']))and(d['week']=='ALL'or r['week']==int(d['week']))and r['probabilities']is not None and r['actual']is not None and r['participation']=='VERIFIED_PLAYED_POSITIVE_PHYSICAL'];assert len(rr)==d['n'];score=auc(rr);assert score==d['over_auc']or abs(score-d['over_auc'])<1e-12
        assert abs(math.fsum(r['probabilities']['over']for r in rr)/len(rr)-d['mean_predicted_over'])<1e-12 and sum(r['actual']>r['line']for r in rr)/len(rr)==d['actual_over_rate']
        assert sum(b['n']for b in d['reliability_bins'])==len(rr)
        for b in d['reliability_bins']:
            sub=[r for r in rr if b['lo']<=r['probabilities']['over']<(b['hi']if b['hi']<1 else 1.000000001)];assert len(sub)==b['n']
            p=math.fsum(r['probabilities']['over']for r in sub)/len(sub)if sub else None;y=sum(r['actual']>r['line']for r in sub)/len(sub)if sub else None
            assert p==b['mean_probability']or(p is not None and abs(p-b['mean_probability'])<1e-12);assert y==b['over_frequency']
        summary.append(dict(target=d['target'],arm=d['arm'],week=d['week'],n=len(rr),AUC=score))
    pt=[d for d in summary if d['target']=='pass_td'];assert pt[0]['AUC']==pt[1]['AUC']
    rec=[d for d in summary if d['target']=='rec'and d['week']=='ALL'];result=dict(state='PASS_INDEPENDENT_RANK_SUM_AND_RELIABILITY',source_rows_sha256=hashlib.sha256(private.read_bytes()).hexdigest(),diagnostic_sha256=hashlib.sha256((out/'DISCRIMINATION_RELIABILITY.json').read_bytes()).hexdigest(),views_verified=8,summary=summary,PT_fixed_intercept_preserves_AUC=True,rec_pooled_AUC_delta=next(d['AUC']for d in rec if d['arm']==1)-next(d['AUC']for d in rec if d['arm']==0),scope='AUC is independent pairwise rank-sum arithmetic; proper calibration scores, direction accuracy and coverage remain separate. Rolling fitted intercepts can alter pooled cross-batch ranks; no causal feature explanation or new forecast.')
    (out/'INDEPENDENT_DISCRIMINATION_RELIABILITY_V1.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('private',type=Path);p.add_argument('out',type=Path);a=p.parse_args();run(a.private,a.out)
