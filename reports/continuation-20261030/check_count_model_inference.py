"""Replay only already-fitted, digest-verified count models; never refit."""
import gzip,json,math,pickle,sys
from pathlib import Path
from collections import Counter
import numpy as np
from threadpoolctl import threadpool_limits
from check_new_wave_prefixes import load,sha,clock

def audit(public,private,source):
    p=json.loads((public/'FROZEN_PROTOCOL.json').read_text());rows,_,_=load(source,p);counts=Counter()
    with threadpool_limits(limits=2):
        for file in sorted(public.glob('*-FIT.json')):
            fit=json.loads(file.read_text());d=fit['query_features'];fp=private/d['name'];assert sha(fp)==d['sha256'];entries=json.loads(gzip.decompress(fp.read_bytes()))
            receipt=json.loads((public/(fit['slot']+'-FORECAST.json')).read_text());d=receipt['packet'];fp=private/d['name'];assert sha(fp)==d['sha256'];rs=json.loads(gzip.decompress(fp.read_bytes()))['rows']
            assert len(entries)==len(rs);model=None
            if fit['model']:
                d=fit['model'];fp=private/d['name'];assert sha(fp)==d['sha256'];model=pickle.loads(gzip.decompress(fp.read_bytes()));counts['retained_models_replayed']+=1
                assert model.n_iter_==64
                for k,v in p['params'].items():assert model.get_params()[k]==v
                assert model.loss==('absolute_error'if'rush-att-qb-rb'in fit['family']else'poisson')
                good=[i for i,e in enumerate(entries)if not e['query']['blocked_reason']]
                x=np.asarray([[math.nan if v is None else v for v in entries[i]['features']]for i in good],dtype=float)
                predictions=model.predict(x)
                for i,v in zip(good,predictions):
                    if rs[i]['prediction']is None:continue
                    assert math.isclose(max(0.,float(v)),rs[i]['prediction'],rel_tol=4e-13,abs_tol=5e-11)
                    counts['fitted_prediction_views_checked']+=1
            else:
                floor=p['policies'][fit['policy_id']]['fit_floor'];roles=set(fit['training_roles']);target=fit['target']
                for e,r in zip(entries,rs):
                    q=e['query']
                    if q['blocked_reason']:assert r['prediction']is None;continue
                    eligible=[s for s in rows if s['season']>=floor and s['position']==q['position']and s['position']in roles and s['values'][target]is not None and s['available']<q['cutoff']]
                    own=[s for s in eligible if s['player_id']==q['player_id']];chosen=own or eligible;ys=sorted(s['values'][target]for s in chosen)
                    expected=(ys[(len(ys)-1)//2]if'rush-att-qb-rb'in fit['family']else sum(ys)/len(ys))if ys else 0
                    assert math.isclose(float(expected),r['prediction'],rel_tol=4e-13,abs_tol=5e-11)
                    assert r['fallback_n']==len(chosen);assert r['latest_fallback_available']==max((s['available']for s in chosen),default=None)
                    counts['fallback_prediction_views_checked']+=1
    return dict(status='PASS_ALL_RETAINED_COUNT_MODELS_AND_FALLBACKS',counts=dict(counts),protocol_sha256=sha(public/'FROZEN_PROTOCOL.json'),run_receipt_sha256=sha(public/'RUN_RECEIPT.json'),new_fits=0,new_forecasts=0,actual_week8_labels_read=0)

if __name__=='__main__':
    result=audit(Path(sys.argv[1]),Path(sys.argv[2]),Path(sys.argv[3]));(Path(__file__).parent/'COUNT_MODEL_INFERENCE_REVIEW.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
