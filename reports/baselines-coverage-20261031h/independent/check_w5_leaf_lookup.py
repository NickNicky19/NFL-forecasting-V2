"""Representative independent leaf-histogram/CDF lookup; no estimator execution."""
import argparse
from collections import defaultdict,Counter
from contextlib import ExitStack
from datetime import datetime,timezone
import csv,gzip,hashlib,importlib.util,json,math,pickle,sys
from pathlib import Path
from unittest.mock import patch
import numpy as np

spec=importlib.util.spec_from_file_location('independent_methods',Path(__file__).resolve().parents[2]/'completion-20261031g/independent/check_w7_methods.py');ind=importlib.util.module_from_spec(spec);spec.loader.exec_module(ind)
sha,canon=ind.sha,ind.canon
def read(p):return json.loads(p.read_bytes())
def unpack(p):return json.loads(gzip.decompress(p.read_bytes()))
def close(a,b):assert math.isclose(float(a),float(b),abs_tol=1e-9,rel_tol=1e-10),(a,b)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',type=Path,required=True);ap.add_argument('--private-root',type=Path,required=True);ap.add_argument('--law-private',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();sys.path.insert(0,str(a.repo_root.resolve()));public=a.repo_root/'reports/baselines-coverage-20261031h/actual-method-w5/law-recovery-v1';p=read(public/'FROZEN_PROTOCOL.json');run=read(public/'RUN_RECEIPT.json');assert sha(public/'FROZEN_PROTOCOL.json')==run['protocol_sha256'];models={r['fit_receipt']:r for r in p['models']};examples=[]
    for artifact in run['artifacts']:
        file=a.law_private/(artifact['panel_id']+'-LEARNED_LAW_AUGMENTATION.json.gz');assert sha(file)==artifact['sha256'];rows=unpack(file)['rows'];assert len(rows)==artifact['complete_law_offer_rows']
        for target in('pass_att','pass_int','rush_yd','rec_yd'):
            for family in('v2-distribution-controls-reconstruction-v2:ordered_leaf_cdf','v2-c02-explicit-lag-block-removal-leaf-cdf-v1'):
                eligible=[r for r in rows if r['target']==target and r['procedure_id']==family and r['history_regime']=='H-MULTI'];assert eligible;examples.append(dict(panel=artifact['panel_id'],row=min(eligible,key=lambda r:r['source_row_index'])))
    assert len(examples)==8;wanted=defaultdict(set)
    for e in examples:
        for i in e['row']['source_row_indices_in_member']:wanted[e['row']['source_member']].add(i)
    witnesses={}
    for member,indices in wanted.items():
        path=a.private_root/member;it=ind.ind.packets(path)if not member.endswith('.csv.gz')else csv.DictReader(gzip.open(path,'rt'))
        for i,r in enumerate(it):
            if i in indices:witnesses[member,i]=r
    from nfl_v2 import distribution_wave_v2 as base,distribution_wave as old
    from sklearn.ensemble import ExtraTreesRegressor
    def forbidden(*args,**kwargs):raise AssertionError('INFERENCE_FORBIDDEN')
    permodel=defaultdict(list)
    for e in examples:permodel[e['row']['fit_receipt']].append(e)
    checked=0;summary_witnesses=0;negative_tail_cases=0;count_cases=0;proof=[]
    with ExitStack()as stack:
        for cls,names in[(base.FittedLawModel,('fit','predict')),(old.FittedLawModel,('fit','predict')),(base.Design,('fit','transform')),(old.Design,('fit','transform')),(ExtraTreesRegressor,('fit','predict','apply','decision_path'))]:
            for name in names:stack.enter_context(patch.object(cls,name,forbidden))
        for fitpath,entries in permodel.items():
            fm=models[fitpath];fit=read(a.repo_root/fitpath);assert sha(a.repo_root/fitpath)==fm['fit_sha256'];file=a.private_root/fm['member'];assert sha(file)==fm['model_sha256'];model=pickle.loads(gzip.decompress(file.read_bytes()));assert len(model.hist)==32
            for e in entries:
                row=e['row'];params=row['params'];support=np.asarray(params['support']);assert np.array_equal(support,model.support);prior=fit['prior_parameters'][row['position']];assert params['prior']==prior and params['mixture']==.05
                raw=witnesses[row['source_member'],row['source_row_indices_in_member'][0]];detail=raw['law_reference'];detail=json.loads(detail)if isinstance(detail,str)else detail;leaf_ids=detail['leaf_ids'];assert len(leaf_ids)==32
                hist=[np.asarray(h[int(leaf)].toarray()).ravel()for h,leaf in zip(model.hist,leaf_ids)];assert all(math.isclose(math.fsum(v),1,abs_tol=1e-10)and np.all(v>=0)for v in hist)
                # Independent columnwise summation, followed by the original normalization.
                weights=np.asarray([math.fsum(float(h[j])for h in hist)/32 for j in range(len(support))]);weights/=weights.sum();assert np.allclose(weights,params['weights'],rtol=1e-10,atol=1e-12)
                def cdf(k):return .95*math.fsum(float(w)for y,w in zip(support,weights)if y<=k)+.05*ind.cdf(prior,k)
                def quantile(prob):
                    lo,hi=-1,1
                    while cdf(lo)>=prob:lo=2*lo-1
                    while cdf(hi)<prob:hi=2*hi+1
                    while hi-lo>1:
                        mid=(lo+hi)//2
                        if cdf(mid)>=prob:hi=mid
                        else:lo=mid
                    return hi
                pmu=0. if prior['kind']=='zero'else prior['p']if prior['kind']=='bernoulli'else prior['mean']if prior['kind']=='poisson'else prior['q']/(1-prior['q'])if prior['kind']=='geometric'else prior['center'];mean=.95*math.fsum(float(y*w)for y,w in zip(support,weights))+.05*pmu;zero=cdf(0)-cdf(-1);derived=dict(mean=mean,lower_median=quantile(.5),q05=quantile(.05),q95=quantile(.95),zero_mass=zero)
                floor=math.floor(row['line']);close(cdf(floor),row['cdf_at_line_floor']);close(cdf(floor-1),row['cdf_at_line_floor_minus_one']);assert cdf(floor-1)<=cdf(floor)<=cdf(floor+1)
                for i in row['source_row_indices_in_member']:
                    raw=witnesses[row['source_member'],i];summary=raw['distribution_summary'];summary=json.loads(summary)if isinstance(summary,str)else summary
                    for name,value in derived.items():close(value,summary[name])
                    product=raw['product_id'];close(float(raw['prediction']),derived['mean'if product=='mean'else'lower_median']);summary_witnesses+=1
                assert math.isclose((1-cdf(floor))+cdf(floor-1)+(cdf(floor)-cdf(floor-1)),1,abs_tol=1e-12)
                if row['target']in('pass_att','pass_int'):assert np.all(support>=0)and cdf(-1)==0;count_cases+=1
                else:
                    assert prior['kind']=='signed'and prior['q']>0
                    assert cdf(min(-1,math.floor(float(support[0]))-1))>0;negative_tail_cases+=1
                checked+=1;proof.append(dict(panel=e['panel'],target=row['target'],procedure_id=row['procedure_id'],history_regime=row['history_regime'],model_sha256=fm['model_sha256'],fit_sha256=fm['fit_sha256'],support_size=len(support),trees=32,law_payload_and_saved_summaries_match=True))
    receipt=dict(state='PASS_INDEPENDENT_REPRESENTATIVE_LEAF_HISTOGRAM_AND_LAW_REPRODUCTION',at=datetime.now(timezone.utc).isoformat(),protocol_sha256=run['protocol_sha256'],models_in_producer_manifest=len(models),models_independently_loaded=len(permodel),law_offer_cases_independently_rebuilt=checked,saved_mean_median_summary_witnesses=summary_witnesses,count_support_cases=count_cases,signed_negative_infinite_prior_tail_cases=negative_tail_cases,proof=proof,estimator_or_transform_calls=0,new_fits=0,new_inference=0,new_forecasts=0,new_scores=0,new_NFL_observations=0,scope='Representative8lawcases from8of80restoredW5models: base/C02, count/signedtargets. Independenthistogram masses,originalmoments/quantiles andwholelinepush/complements. No estimator/transform execution or newfit.')
    with a.output.open('x')as f:json.dump(receipt,f,indent=2);f.write('\n')
    print(json.dumps({k:receipt[k]for k in('state','models_independently_loaded','law_offer_cases_independently_rebuilt','saved_mean_median_summary_witnesses')}))


if __name__=='__main__':main()
