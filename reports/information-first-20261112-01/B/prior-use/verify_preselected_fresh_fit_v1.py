"""One preselected 2026W1B2 fresh fit, independent of author fit/restore.

Direct sklearn estimator + manual preprocessing and leaf histograms. Raw FTN
rate reconstruction is separate from the author's feature constructor.
"""
import argparse
import collections
import datetime
import gzip
import hashlib
import json
import math
import sys
import warnings
from pathlib import Path

import numpy as np
from sklearn.ensemble import ExtraTreesRegressor
from threadpoolctl import threadpool_limits

ROOT=Path(__file__).resolve().parents[4]
FLAGS=('is_throw_away','is_interception_worthy')


def read(path):
    data=path.read_bytes()
    return json.loads(gzip.decompress(data)if path.suffix=='.gz'else data)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,default=ROOT)
    ap.add_argument('--wave',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();root=a.root.resolve();wave=a.wave.resolve()
    if a.out.exists():raise FileExistsError('Do not repeat this verification fit')
    source=root/'reports/information-first-20261112-01/B/source-qualification/FTN_BALL_QUALITY_QB_GAME_INPUTS_V1.json.gz'
    inputfile=wave/'QB_CONTEXT_W1_W9_INPUTS_V1.json.gz';featurefile=wave/'FEATURE_INPUTS_V1.json.gz'
    fitfile=wave/'fits/2026-W01-B2.json.gz';forecastfile=wave/'predictions/2026-W01.json.gz'
    saved=read(fitfile);payload=saved['model'];cutoff=saved['fit_cutoff']
    data=sorted(read(inputfile),key=lambda r:(r['kickoff'],r['game_id'],r['player_id']))
    all_qb=[r for r in data if r.get('position')=='QB'and r.get('physical_participation')is True and r.get('target_parity')is True]
    fmap={(r['game_id'],r['player_id']):r for r in read(featurefile)}
    chart={(r['game_id'],r['player_id']):r for r in read(source)}
    old={}
    for path in sorted((root/'reports/profile-increment-to-release-01/B/opportunity-wave-v1/predictions').glob('*.json.gz')):
        for r in read(path)['rows']:
            if r['method']=='R3':old[r['game_id'],r['player_id']]=r
    train=[r for r in all_qb if r['season']>=2025 and r['available']<cutoff]
    queries=[r for r in data if(r['season'],r['week'])==(2026,1)]
    checked_rates=0
    def vector(q):
        nonlocal checked_rates
        key=q['game_id'],q['player_id'];base=old[key]['features']
        assert base==fmap[key]['B0_features']
        earlier=[r for r in all_qb if math.isfinite(r['available'])and r['available']<q['kickoff']]
        own=[r for r in earlier if r['player_id']==q['player_id']][-8:]
        values=[]
        for flag in FLAGS:
            def totals(records):
                positive=known=0
                for r in records:
                    c=chart.get((r['game_id'],r['player_id']))
                    if c is None or c.get('available')is None or not c['available']<q['kickoff']:continue
                    positive+=c['flags'][flag]['positive'];known+=c['flags'][flag]['known']
                return positive,known
            pp,pk=totals(earlier);pos,known=totals(own)
            values.append((pos+20*((pp+1)/(pk+2)))/(known+20))
        np.testing.assert_allclose(values,fmap[key]['B2_appended'],rtol=0,atol=1e-14);checked_rates+=2
        return list(base)+values
    X=np.asarray([vector(r)for r in train],float);Y=np.asarray([r['official_completions']for r in train],float)
    Q=np.asarray([vector(r)for r in queries],float)
    # Independent median fill + explicit missing-indicator design.
    medians=np.asarray([np.median(c[np.isfinite(c)]) if np.isfinite(c).any() else 0. for c in X.T])
    def design(x):return np.column_stack((np.where(np.isfinite(x),x,medians),~np.isfinite(x))).astype(float)
    Z=design(X);ZQ=design(Q)
    np.testing.assert_array_equal(medians,payload['design']['median'])
    np.testing.assert_allclose(Z.mean(0),payload['design']['mean'],rtol=0,atol=1e-12)
    scale=Z.std(0);scale=np.where(scale>1e-12,scale,1.)
    np.testing.assert_allclose(scale,payload['design']['scale'],rtol=0,atol=1e-12)
    started=datetime.datetime.now(datetime.timezone.utc).isoformat()
    with threadpool_limits(limits=2):
        model=ExtraTreesRegressor(**payload['forest_config']).fit(Z,Y)
    leaf=model.apply(Z);qleaf=model.apply(ZQ);support=np.unique(Y)
    np.testing.assert_array_equal(support,payload['support'])
    hist_checks=0;tree_checks=0
    for j,estimator in enumerate(model.estimators_):
        tree=estimator.tree_;bound=payload['trees'][j]
        for name,value in [('left',tree.children_left),('right',tree.children_right),('feature',tree.feature),('threshold',tree.threshold)]:
            np.testing.assert_array_equal(value,bound[name]);tree_checks+=len(value)
        h=bound['leaf_histogram'];actual={(r,c):v for r,c,v in zip(h['rows'],h['columns'],h['values'])}
        expected={}
        for node in np.unique(leaf[:,j]):
            yy=Y[leaf[:,j]==node];counts=collections.Counter(yy)
            for k,y in enumerate(support):
                if counts[y]:expected[int(node),k]=counts[y]/len(yy)
        assert set(actual)==set(expected)
        for key,value in expected.items():assert abs(value-actual[key])<1e-14;hist_checks+=1
    predictions={(r['game_id'],r['player_id']):r for r in read(forecastfile)['rows']if r['method']=='B2'}
    mu=max(.05,float(Y.mean()));geometric_q=mu/(1+mu);prior_mean=geometric_q/(1-geometric_q)
    mean_error=0.;median_checks=0
    for i,q in enumerate(queries):
        weights=np.zeros(len(support))
        for j in range(len(model.estimators_)):
            yy=Y[leaf[:,j]==qleaf[i,j]];counts=collections.Counter(yy)
            weights+=np.asarray([counts[y]/len(yy)for y in support])/len(model.estimators_)
        assert abs(float(weights.sum())-1)<1e-12
        point=.95*float(weights@support)+.05*prior_mean
        median=next(k for k in range(int(support.max())+1)if .95*float(weights[support<=k].sum())+.05*(1-geometric_q**(k+1))>=.5)
        bound=predictions[q['game_id'],q['player_id']]
        mean_error=max(mean_error,abs(point-bound['mean']));assert abs(point-bound['mean'])<1e-10
        assert median==bound['lower_median'];median_checks+=1
    bindings=[dict(path=str(p.relative_to(root)),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size)
              for p in [source,inputfile,featurefile,fitfile,forecastfile,Path(__file__).resolve()]]
    result=dict(id='B-FTN-PRESELECTED-2026W1B2-FRESH-FIT-v1',state='PASS',started_UTC=started,
        finished_UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),new_verification_fits=1,new_research_procedures=0,
        author_fit_or_design_or_restore_imported=False,training_rows=len(train),query_rows=len(queries),fit_cutoff=cutoff,
        max_training_available=max(r['available']for r in train),independent_FTN_rate_assertions=checked_rates,
        exact_tree_array_checks=tree_checks,leaf_histogram_checks=hist_checks,median_checks=median_checks,max_mean_error=mean_error,
        bindings=bindings,scope='Onepreselected2026W1B2fit,manualtraining-onlydesign/directExtraTrees/independentleafmasses+geometricmixture;nootherorigins,offeredgradesororiginalvintageauthentication.')
    a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))


if __name__=='__main__':main()
