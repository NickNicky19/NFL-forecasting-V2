"""Independent saved-histogram math; no fit/predict/apply/transform calls."""
import argparse, collections, gzip, hashlib, json, math, pickle, sys
from datetime import datetime, timezone
from pathlib import Path
import numpy as np

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads(p.read_bytes())
def gz(p): return json.loads(gzip.decompress(p.read_bytes()))
def prior_mean(p):
    if p['kind']=='geometric': return p['q']/(1-p['q'])
    if p['kind']=='signed': return p['center']
    if p['kind']=='zero': return 0.
    raise ValueError('unexpected prior')
def prior_cdf(p,k):
    if p['kind']=='geometric': return 0. if k<0 else 1-p['q']**(k+1)
    if p['kind']=='signed':
        d=k-p['center'];return p['q']**(-d)/(1+p['q']) if d<0 else 1-p['q']**(d+1)/(1+p['q'])
    if p['kind']=='zero':return float(k>=0)
    raise ValueError('unexpected prior')
def median(cdf):
    lo,hi=-1,1
    while cdf(lo)>=.5:lo=lo*2-1
    while cdf(hi)<.5:hi=hi*2+1
    while hi-lo>1:
        m=(lo+hi)//2
        if cdf(m)>=.5:hi=m
        else:lo=m
    return hi
def forbidden(*a,**kw): raise AssertionError('model computation forbidden in independent audit')

def main():
    ap=argparse.ArgumentParser()
    for k in ('repo','private-root','source-root','output'):ap.add_argument('--'+k,type=Path,required=True)
    a=ap.parse_args();sys.path.insert(0,str(a.repo))
    from nfl_v2 import hgb_control as source, qualified_defense_inputs as inputs
    from nfl_v2.distribution_wave_v2 import FittedLawModel, Design
    # Defense aggregation uses the bound source loader, but feature formulas,
    # chronological slicing and point calculations below are independent.
    FittedLawModel.fit=FittedLawModel.predict=forbidden
    Design.fit=Design.transform=Design.impute=forbidden
    pub=a.repo/'reports/execution-closure-02/B'
    protocol=read(pub/'FROZEN_ADAPTER_CHECK_V1.json')
    assert sha(pub/'FROZEN_ADAPTER_CHECK_V1.json')=='7920a6c984454784af1ecd3b27df8f16b560a44ce0ed04ca6879669fb2514333'
    root=a.repo/'reports/continuation-20261030c/qualified-defense-information-v1'
    original=read(root/'FROZEN_PROTOCOL.json')
    for s in original['source_ids']:assert sha(a.source_root/s['name'])==s['sha256']
    rows,_,_=source.load_source(a.source_root,original)
    inputs.attach_context(rows,source.schedules(a.source_root/'games.csv'),a.source_root)
    dh=inputs.build_history(rows,('pass_td','pass_cmp','rec_yd'))
    players=collections.defaultdict(list)
    for r in rows:players[r['player_id']].append(r)
    for rr in players.values():rr.sort(key=lambda r:(r['available'],r['kickoff'],r['game_id']))
    receipt=read(pub/'ADAPTER_PARITY_RECEIPT_V1.json'); reported={r['slot']:r for r in receipt['results']}
    checks=[];totals=collections.Counter();max_mean_error=0.
    for cell in protocol['cells']:
        fit=read(a.repo/cell['fit_path']);fr=read(a.repo/cell['forecast_path'])
        assert sha(a.repo/cell['fit_path'])==cell['fit_sha256']
        assert sha(a.repo/cell['forecast_path'])==cell['forecast_sha256']
        for b in [fit['model'],fit['query_features'],fr['packet']]:
            f=a.private_root/b['bundle_name'];assert sha(f)==b['sha256'] and f.stat().st_size==b['bytes']
        # Only B's previously authenticated origin model, never foreign pickle.
        model=pickle.loads(gzip.decompress((a.private_root/fit['model']['bundle_name']).read_bytes()))
        assert type(model) is FittedLawModel and model.family=='ordered_leaf_cdf' and model.target==fit['target']
        qrows=gz(a.private_root/fit['query_features']['bundle_name']);saved=gz(a.private_root/fr['packet']['bundle_name'])['rows']
        by={(r['game_id'],r['player_id'],r['product_id']):r for r in saved}
        counts=collections.Counter();width=len(fit['feature_columns']);assert len(model.design.median)==width
        assert len(model.estimator.estimators_[0].tree_.feature)>0
        assert model.estimator.n_features_in_==2*width
        for pack in qrows:
            q=pack['query'];cut=q['cutoff'];target=q['target'];role=q['position']
            own=[r for r in players[q['player_id']] if r['available']<cut][-8:]
            vals=[]
            for n in (3,8):
                vv=[r['values'][target]for r in own[-n:] if r['values'][target]is not None]
                vals.extend([sum(vv)/len(vv)if vv else math.nan,float(len(vv))])
            for lag in range(1,5):
                r=own[-lag]if len(own)>=lag else None;v=r['values'][target]if r else None
                vals.extend([v if v is not None else math.nan,(cut-r['kickoff'])/86400 if r else math.nan,float(v is None)])
            vals.extend(float(role==p)for p in source.POSITIONS)
            local=[r for r in dh.opponents.get((q['defense'],role,target),[])if r['available']<cut and r['season']>=2022][-4:]
            league=[r for r in dh.league.get((role,target),[])if r['available']<cut and r['season']>=2022]
            targets=[r['target_sum']for r in local if r['target_sum']is not None]
            rates=[r for r in local if r['opportunities']is not None]
            extra=[math.fsum(targets)/len(targets)if targets else math.nan,len(targets),sum(r['rows']for r in local),sum(r['known_rows']for r in local)]
            if fit['information_group']=='D2':
                good=[r for r in league if r['opportunities']is not None]
                n=sum(r['opportunities']for r in good);y=sum(r['rate_target_sum']for r in good)
                r0=y/n if n else None;ln=math.fsum(r['opportunities']for r in rates);ly=math.fsum(r['rate_target_sum']for r in rates)
                shr=(dh.kappa*r0+ly)/(dh.kappa+ln)if r0 is not None else None
                extra.extend([shr,shr-r0 if shr is not None else None,ln,len(rates),(cut-max(r['kickoff']for r in local))/86400 if local else None])
            vals.extend(math.nan if v is None else v for v in extra)
            assert np.allclose(np.asarray(vals),np.asarray(pack['features'],float),rtol=1e-13,atol=1e-12,equal_nan=True)
            clocks=[own[-1]['available']if own else None,max((r['available']for r in local),default=None)]
            if fit['information_group']=='D2':clocks.append(max((r['available']for r in league),default=None))
            clock=max((v for v in clocks if v is not None),default=None)
            assert clock==pack['latest_consumed_feature_available'] and (clock is None or clock<cut)
            assert [r['game_id']for r in local]==pack['defense_audit']['local_game_ids']
            sr=by[q['game_id'],q['player_id'],'mean'];pr=fit['prior_parameters'][role]
            if vals[3]<=0:
                mean=prior_mean(pr);med=median(lambda k:prior_cdf(pr,k));fallback='cold_start_role_prior'
            else:
                ids=sr['law_reference']['leaf_ids'];assert len(ids)==len(model.hist)
                # Stored sparse histogram lookup only: no tree traversal.
                weights=sum((h.getrow(i).toarray().ravel()/len(ids) for h,i in zip(model.hist,ids)),np.zeros(len(model.support)))
                assert abs(float(weights.sum())-1)<1e-10
                weights/=weights.sum();mean=.95*float(weights@model.support)+.05*prior_mean(pr)
                med=median(lambda k:.95*float(weights[model.support<=k].sum())+.05*prior_cdf(pr,k));fallback='none'
            err=abs(mean-sr['prediction']);max_mean_error=max(max_mean_error,err);assert err<=1e-10
            mr=by[q['game_id'],q['player_id'],'lower_median'];assert med==mr['prediction']
            assert sr['fallback']==mr['fallback']==fallback
            counts[fallback]+=1
        expected=reported[cell['slot']]
        assert len(qrows)==expected['query_rows'] and dict(counts)==expected['fallback_query_counts']
        assert 2*len(qrows)==expected['point_values_checked']
        totals.update(query_rows=len(qrows),point_values=2*len(qrows),models=1,fallback=counts['cold_start_role_prior'],learned=counts['none'],feature_values=len(qrows)*width)
        checks.append(dict(slot=cell['slot'],query_rows=len(qrows),raw_width=width,imputed_width=2*width,
            fallback_counts=dict(counts),saved_histogram_point_math='PASS',independent_source_feature_formulas='PASS',
            local_consumed_game_identity_and_clock='PASS',model_sha256=fit['model']['sha256']))
    assert totals['query_rows']==receipt['query_rows_checked']==2878
    assert totals['point_values']==receipt['point_values_checked']==5756
    assert totals['models']==receipt['models_restored']==21
    out=dict(state='PASS_INDEPENDENT_STORED_HISTOGRAM_AND_SOURCE_FEATURE_REVIEW',
      at_utc=datetime.now(timezone.utc).isoformat(),protocol_sha256=sha(pub/'FROZEN_ADAPTER_CHECK_V1.json'),
      runner_receipt_sha256=sha(pub/'ADAPTER_PARITY_RECEIPT_V1.json'),checker_sha256=sha(Path(__file__)),
      totals=dict(totals),maximum_mean_absolute_roundoff=max_mean_error,origin_checks=checks,
      representative_batch_single_checks_reported_not_repeated=receipt['single_row_checks'],
      model_predict_apply_transform_fit_calls=0,forecast_inference=0,new_scoring=0,new_weeks=0,
      independent_calculation='Original B hash-qualified pickle read for histogram/support arrays only; own prior CDF/median/mean and feature formulas; original source loader/defense source-group builder reused explicitly.',
      source_clock_limits='Strict kickoff+7day availability assumption; no authentication of historical publication/quote clocks. Shared availability timestamp can describe defense freshness rather than own target age.',
      qualification='Three median products already have seven numerical weeks; these software checks add zero actual-line/Top Picks weeks, no fresh query/origin/source validation and no production admission.',
      unavailable_scope='No unavailable source/model conditions simulated with an actual model; caller must authenticate immutable source/origin/features before adapter. No claim that matching names can detect independently shuffled raw values.',
      production_scope='Owner Chromium failure before generation/capture is not an arithmetic defect; full-board Top Picks replay remains owner-only.')
    if a.output.exists():raise FileExistsError(a.output)
    a.output.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(dict(state=out['state'],totals=dict(totals))))

if __name__=='__main__':main()
