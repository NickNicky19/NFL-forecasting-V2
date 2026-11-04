"""Independent analytic audit of saved parametric event probabilities; no B scorer imports."""
import argparse,collections,gzip,hashlib,json,math
from decimal import Decimal,ROUND_FLOOR
from pathlib import Path


def read(path):return json.loads(gzip.decompress(path.read_bytes()) if path.suffix=='.gz' else path.read_bytes())
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def cdf(par,k):
    k=math.floor(k);kind=par['kind']
    if kind=='zero':return float(k>=0)
    if kind=='geometric':return 0. if k<0 else 1-float(par['q'])**(k+1)
    if kind=='signed':
        q=float(par['q']);d=k-int(par['center'])
        return q**(-d)/(1+q) if d<0 else 1-q**(d+1)/(1+q)
    if kind=='poisson':
        mu=float(par['mean'])
        if k<0:return 0.
        if mu==0:return 1.
        return min(1.,math.fsum(math.exp(-mu+i*math.log(mu)-math.lgamma(i+1)) for i in range(k+1)))
    if kind=='bernoulli':return 0. if k<0 else 1-float(par['p']) if k<1 else 1.
    raise AssertionError('Unsupported retained law '+kind)

def probabilities(par,line):
    line=Decimal(str(line));floor=int(line.to_integral_value(rounding=ROUND_FLOOR));at=cdf(par,floor)
    under=cdf(par,floor-1) if line==floor else at
    return dict(over=1-at,under=under,push=at-under if line==floor else 0.)

def exact_state(y,line,side):
    y,line=Decimal(str(y)),Decimal(str(line))
    return 'PUSH' if y==line else 'WIN' if (y>line)==(side=='over') else 'LOSS'

def proper(rows):
    rr=[r for r in rows if r['p'] is not None and r['actual'] is not None and r['appearance']=='PLAYED'];loss=[];logs=[]
    for r in rr:
        y,L=Decimal(str(r['actual'])),Decimal(str(r['line']));outcome='over' if y>L else 'under' if y<L else 'push'
        loss.append(.5*math.fsum((r['p'][key]-int(key==outcome))**2 for key in ('under','push','over')))
        p=r['p'][outcome];logs.append(-math.log(p) if p>0 else math.inf)
    return dict(n=len(rr),brier=math.fsum(loss)/len(loss) if loss else None,log_loss=math.inf if any(math.isinf(x) for x in logs) else math.fsum(logs)/len(logs) if logs else None,infinite_log_losses=sum(math.isinf(x) for x in logs))

def run(croot,source,out,private_file,receipt):
    versions={}
    for d in read(croot/'reports/abc-championship/C_INPUT_BINDINGS.json')['datasets']:
        for r in read(croot/d['path'])['rows']:versions[r['record_id']]=r
    first={};fields=('category','game_id','player_id','method_id','method_version','selector_id','policy_id','venue','product','line_tier','evidence_tier')
    for r in versions.values():
        k=tuple(r[x] for x in fields);clock=(r['decision_UTC'],r['scoring_snapshot_id'])
        if k not in first or clock<first[k][0]:first[k]=(clock,r)
    c=[r for _,r in first.values() if r['venue']=='pinnacle' and r['season']==2026 and r['week']<=8]
    offers={r['offer_id']:r for r in c if r['method_id']=='P2_LAW'};controls=collections.defaultdict(dict)
    for r in c:controls[r['offer_id']][r['method_id']]=r
    lookups=collections.defaultdict(dict)
    for f in source.glob('W0[23]-*-regularized_glm_law.json.gz'):
        for r in read(f)['rows']:
            if r['target'] not in ('pass_yd','rush_yd','rec','rec_yd') or r['product_id']!='mean' or r['population']!='primary':continue
            pid='B::'+r['procedure_id']+'::'+r['policy_id']+'::P2_EXACT_LINE_CDF-v1';lookups[pid,r['target']][r['game_id'],r['player_id']]=r
    allrows={};kind_counts=collections.Counter();monotonic=0
    for (pid,target),lookup in lookups.items():
        rows=[]
        for oid,q in offers.items():
            if q['category']!=target:continue
            b=lookup.get((q['game_id'],q['player_id']));params=None
            if b:
                params=b['law_reference'].get('parametric') or b['law_reference'].get('fallback_prior')
            p=None if params is None else probabilities(params,q['line'])
            if p is not None:
                kind_counts[params['kind']]+=1
                assert abs(sum(p.values())-1)<1e-12 and min(p.values())>=-1e-12
                lower=probabilities(params,float(q['line'])-1);higher=probabilities(params,float(q['line'])+1)
                assert lower['over']>=p['over']-1e-12>=higher['over']-2e-12 and lower['under']<=p['under']+1e-12<=higher['under']+2e-12
                monotonic+=1
            side=None if p is None or abs(p['over']-p['under'])<=1e-12 else 'over' if p['over']>p['under'] else 'under'
            state='UNAVAILABLE_FORECAST' if p is None else 'ABSTAIN' if side is None else 'UNKNOWN_PARTICIPATION' if q['appearance']!='PLAYED' else 'MISSING_ACTUAL' if q['actual'] is None else exact_state(q['actual'],q['line'],side)
            rows.append(dict(oid=oid,side=side,state=state,p=p,line=q['line'],actual=q['actual'],appearance=q['appearance'],week=q['week']))
        allrows[pid,target]=rows
    j=read(out/'SCORES.json');sideviews=[s for s in j if s['record_kind']=='prop_selection_evaluation'];probviews=[s for s in j if s['record_kind']=='prop_threshold_probability_evaluation'];assert len(sideviews)==144 and len(probviews)==48
    for s in sideviews:
        rr=[r for r in allrows[s['procedure_id'],s['target']] if (s['week']=='ALL' or r['week']==int(s['week'])) and r['side'] is not None and (s['side']=='Combined' or r['side']==s['side'])];counts=collections.Counter(r['state'] for r in rr);n=counts['WIN']+counts['LOSS'];m=s['selection_metrics']
        assert s['forecast_rows']==len(rr) and s['n']==n and m['WIN']==counts['WIN'] and m['LOSS']==counts['LOSS']
        for k,v in m['status_counts'].items():assert v==counts[k]
        got=proper(rr);seen=m['probability_scores'];assert got['n']==seen['n']
        for key in ('brier','log_loss'):
            a,b=got[key],seen[key];b=math.inf if b=='Infinity' else b
            assert (a is None and b is None) or a==b or abs(a-b)<1e-9
    for s in probviews:
        rr=[r for r in allrows[s['procedure_id'],s['target']] if s['week']=='ALL' or r['week']==int(s['week'])];g=proper(rr)
        assert s['n']==g['n'] and s['forecast_rows']==len(rr)
        for key in ('brier','log_loss'):
            x=s[key];x=math.inf if x=='Infinity' else x
            assert (x is None and g[key] is None) or x==g[key] or abs(x-g[key])<1e-9
        assert s['infinite_log_losses']==g['infinite_log_losses']
    baselines=read(out/'PROBABILITY_BASELINES.json')
    for s in baselines:
        rr=[r for r in allrows[s['procedure_id'],s['target']] if (s['week_view']=='ALL' or r['week']==int(s['week_view'])) and r['p'] is not None and r['actual'] is not None and r['appearance']=='PLAYED'];cr=[];own=[]
        for r in rr:
            if s['control']=='NEUTRAL_HALFPOINT_50_50':
                if Decimal(str(r['line']))%1!=Decimal('.5'):continue
                p=dict(over=.5,under=.5,push=0.)
            else:
                b=controls[r['oid']].get(s['control'])
                if b is None or b.get('p_over') is None:continue
                p={k:b['p_'+k] for k in ('under','over','push')}
            cr.append(dict(r,p=p));own.append(r)
        a,b=proper(own),proper(cr)
        assert s['n']==a['n']==b['n']
        if a['n']:
            assert abs(s['candidate_brier']-a['brier'])<1e-11 and abs(s['control_brier']-b['brier'])<1e-11 and abs(s['brier_delta']-(a['brier']-b['brier']))<1e-11
            if s['control']=='NEUTRAL_HALFPOINT_50_50':assert b['brier']==.25
    manifest=read(out/'PRIVATE_DERIVATIVE_MANIFEST.json');assert digest(private_file)==manifest['sha256'];stored=read(private_file)['rows'];assert len(stored)==3872
    idx={(pid,target,r['oid']):r for (pid,target),rr in allrows.items() for r in rr}
    for r in stored:
        expected=idx[r['method_key'],r['target'],r['offer_id']];assert r['selected_side']==expected['side'] and r['statistical_state']==expected['state']
        if expected['p'] is None:assert r['probabilities'] is None
        else:assert all(abs(r['probabilities'][k]-expected['p'][k])<1e-11 for k in ('under','over','push'))
    summary=[]
    for target in ('pass_yd','rush_yd','rec','rec_yd'):
        candidates=[r for r in probviews if r['target']==target and r['week']=='ALL' and r['n']]
        best=min(candidates,key=lambda r:r['brier']);summary.append(dict(target=target,lowest_glm_brier=best['brier'],procedure_id=best['procedure_id'],n=best['n'],beats_neutral_025=best['brier']<.25))
    result=dict(state='PASS_SEPARATE_ANALYTIC_FORMULAS',score_sha256=digest(out/'SCORES.json'),side_views_verified=len(sideviews),proper_views_verified=len(probviews),baseline_views_verified=len(baselines),private_rows_verified=len(stored),analytic_law_rows=sum(kind_counts.values()),law_kinds=dict(kind_counts),changed_line_monotonicity_checks=monotonic,lowest_scores=summary,limits=['PoissonCDF independently summed from log-PMF terms; signed/geometric/zero CDFs directly calculated; no parent scorer or Law import.','Current/revised source and timing-unverified quote contracts retained.','No recalibration, fitting, model re-inference, profit or release-readiness claim.'])
    receipt.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('croot',type=Path);p.add_argument('source',type=Path);p.add_argument('out',type=Path);p.add_argument('private_file',type=Path);p.add_argument('receipt',type=Path);a=p.parse_args();run(a.croot,a.source,a.out,a.private_file,a.receipt)
