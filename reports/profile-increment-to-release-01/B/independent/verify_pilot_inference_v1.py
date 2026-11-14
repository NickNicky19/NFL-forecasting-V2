"""Independent typed-tree traversal and profile-column arithmetic, zero fits."""
import gzip,hashlib,json,math
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[4];OUT=Path(__file__).resolve().parent
BASE=ROOT/'reports/profile-increment-to-release-01/B';WAVE=BASE/'opportunity-wave-v1'
def read(p):
    p=Path(p);b=p.read_bytes();return json.loads(gzip.decompress(b)if p.suffix=='.gz'else b)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def identity(r):return r['game_id'],r['player_id']
def finite(v):return v is not None and math.isfinite(float(v))
def profile_value(profile,block,name):
    group,field=name.split('_',1);p=profile[group]
    if block=='R1_support':return p['counts'][field]
    if field.endswith('_per_game'):return p['volume'][field[:-9]]['shrunk_per_game']
    if field.endswith('_dropback_mix'):
        context,j=field[:-13].rsplit('_',1)
        return p['contexts'][context][int(j)]['dropback_frequency']['raw']
    return p['rates'][field]['shrunk']
def manual_law(model,feature,prior_q):
    median=model['design']['median'];assert len(median)==len(feature)
    x=np.asarray([float(v)if finite(v)else median[i]for i,v in enumerate(feature)]+[0. if finite(v)else 1. for v in feature],dtype=np.float32)
    support=np.asarray(model['support']);weights=np.zeros(len(support))
    for tree in model['trees']:
        node=0;visited=set()
        while tree['left'][node]!=-1:
            assert node not in visited;visited.add(node)
            node=tree['left'][node]if x[tree['feature'][node]]<=tree['threshold'][node]else tree['right'][node]
        assert len(visited)<=8
        h=tree['leaf_histogram'];total=0.
        for i,j,value in zip(h['rows'],h['columns'],h['values']):
            if i==node:weights[j]+=value/len(model['trees']);total+=value
        assert abs(total-1)<1e-10
    weights/=weights.sum()
    def cdf(value):
        y=math.floor(value);return .95*float(weights[support<=y].sum())+.05*(0. if y<0 else 1-prior_q**(y+1))
    mean=.95*float(weights@support)+.05*prior_q/(1-prior_q)
    median=next(i for i in range(10000)if cdf(i)>=.5)
    return mean,median,weights,cdf

def main():
    orders=read(WAVE/'FEATURE_ORDER_V1.json')['orders'];rows=sorted(read(ROOT/'reports/player-context-matchup-01/B/source-fields-v3/DERIVED_QB_GAME_INPUTS.json.gz'),key=lambda r:(r['kickoff'],r['game_id'],r['player_id']))
    profiles={identity(p['identity']):p for p in read(BASE/'source-profiles/QB_OPPORTUNITY_ASOF_PROFILES_V2.json.gz')}
    payload=read(WAVE/'predictions/2025-W01.json.gz');forecast=payload['rows'];r0={identity(r):r for r in forecast if r['method']=='R0'}
    cutoff=payload['fit_cutoff'];train=[r for r in rows if r['physical_participation']and r['target_parity']and r['season']>=2024 and r['available']<cutoff]
    target_mean=max(.05,sum(r['official_completions']for r in train)/len(train));q=target_mean/(1+target_mean)
    by={r['method']:read(WAVE/'fits'/('2025-W01-'+r['method']+'.json.gz'))for r in forecast if r['method']!='R0'}
    max_mean=max_mass=max_feature=0.;models=set();feature_checks=0;predictions=0;priority_checks=0
    for r in forecast:
        k=identity(r);prior=[p for p in rows if p['physical_participation']and p['target_parity']and p['available']<r['feature_cutoff']]
        own=[p for p in prior if p['player_id']==r['player_id']][-8:];recent=[p for p in prior if p['season']>=r['season']-1]
        mu=(sum(p['official_attempts']for p in own)+4*sum(p['official_attempts']for p in recent)/len(recent))/(len(own)+4)
        assert r['profile_priority']['member']==bool(own and mu>=10)
        assert abs(r['profile_priority']['reference_expected_attempts']-mu)<1e-12;priority_checks+=1
        if r['method']=='R0':continue
        model=by[r['method']]['model'];models.add(r['method']);assert len(r['features'])==len(orders[r['method']])
        for index,label in enumerate(orders[r['method']]):
            if index<len(orders['R0']):
                a,b=r['features'][index],r0[k]['features'][index]
                assert a==b or not finite(a)and not finite(b)
                continue
            if label.endswith(':MISSING'):continue
            block,name=label.split(':',1);v=profile_value(profiles[k],block,name);missing=not finite(v);v=0. if missing else float(v)
            if block=='R1_support':v=math.log1p(v)
            actual=r['features'][index];delta=abs(actual-v);max_feature=max(max_feature,delta);assert delta<1e-12
            assert r['features'][index+1]==float(missing);feature_checks+=1
        assert abs(r['law']['prior']['q']-q)<1e-14
        mean,median,weight,cdf=manual_law(model,r['features'],q)
        max_mean=max(max_mean,abs(mean-r['mean']));max_mass=max(max_mass,float(np.max(np.abs(weight-np.asarray(r['law']['weights'])))))
        assert abs(mean-r['mean'])<1e-10 and median==r['lower_median']
        assert abs(weight.sum()-1)<1e-12 and np.isfinite(weight).all()and(weight>=0).all()
        pp=[cdf(y)for y in range(-1,101)];assert all(a<=b+1e-14 for a,b in zip(pp,pp[1:]))and pp[0]==0
        for line in(19,19.5,20):
            under=cdf(math.ceil(line)-1);over=1-cdf(math.floor(line));push=cdf(line)-cdf(line-1)if line==int(line)else 0.
            assert min(under,over,push)>=-1e-12 and abs(under+over+push-1)<1e-12
        predictions+=1
    receipt=dict(id='B-OPPORTUNITY-PILOT-INDEPENDENT-INFERENCE-v1',status='PASS_IN_CHECKED_SCOPE',origin=[2025,1],models=sorted(models),model_sha256={arm:sha(WAVE/'fits'/('2025-W01-'+arm+'.json.gz'))for arm in models},prediction_artifact_sha256=sha(WAVE/'predictions/2025-W01.json.gz'),feature_order_sha256=sha(WAVE/'FEATURE_ORDER_V1.json'),training_rows=len(train),new_fits=0,checked_predictions=predictions,priority_checks=priority_checks,profile_value_checks=feature_checks,max_feature_difference=max_feature,max_mean_difference=max_mean,max_empirical_mass_difference=max_mass,independence='Manual numerical profile-column arithmetic and explicit32-tree traversal, independently derived earlier-label geometric prior and cohort reference. Author feature builder, forest restoration, law and scorer not called.',limits=['One deterministic earliest2025 origin; no independent fresh augmented fit claimed.','No probability, accuracy, improvement, five-week or production admission follows from software/inference parity.','Canonical public data/source vintage remains current revised seven-day reconstruction, not authenticated original pregame.'])
    dest=OUT/'PILOT_INDEPENDENT_INFERENCE_V1.json';assert not dest.exists();dest.write_text(json.dumps(receipt,indent=2,allow_nan=False)+'\n');print(json.dumps(receipt,indent=2))

if __name__=='__main__':main()
