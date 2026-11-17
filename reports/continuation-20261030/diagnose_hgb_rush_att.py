#!/usr/bin/env python3
"""Restore original retained HGB rush-att internals, never fit or query new rows.

Inputs remain private. Only public-safe aggregate diagnostics leave this tool.
Historical training frames are reconstructed and membership-hash checked; no
original retained train-frame file is claimed. No Week8 outcomes are acquired.
"""
import argparse
import collections
import gzip
import hashlib
import json
import math
import pickle
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from threadpoolctl import threadpool_limits

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from nfl_v2 import hgb_control as old
from nfl_v2.shadow_grading import canonical,digest,utc


def read_json(path):return json.loads(Path(path).read_bytes())
def sha(path):return digest(Path(path).read_bytes())


def json_safe(value):
    if isinstance(value,dict):return{str(k):json_safe(v)for k,v in value.items()}
    if isinstance(value,(list,tuple)):return[json_safe(v)for v in value]
    if isinstance(value,(float,np.floating))and not math.isfinite(value):return 'Infinity'if value>0 else '-Infinity'if value<0 else 'NaN'
    if isinstance(value,np.generic):return value.item()
    return value


def restore(root,descriptor,decode_json=False):
    blob=(root/descriptor['name']).read_bytes()
    if len(blob)!=descriptor['bytes']or digest(blob)!=descriptor['sha256']:raise ValueError('compressed artifact mismatch')
    body=gzip.decompress(blob)
    if digest(body)!=descriptor['uncompressed_sha256']:raise ValueError('original artifact body mismatch')
    return json.loads(body)if decode_json else body


def feature_function(source_rows):
    """Independent reconstruction of the consumed20columns, not a new feature."""
    import bisect
    by_player=collections.defaultdict(list)
    for r in source_rows:by_player[r['player_id']].append(r)
    clocks={}
    for pid,rows in by_player.items():
        rows.sort(key=lambda r:(r['available'],r['kickoff'],r['game_id']))
        clocks[pid]=[r['available']for r in rows]
    def get(pid,pos,cutoff):
        right=bisect.bisect_left(clocks.get(pid,[]),cutoff)
        recent=by_player[pid][max(0,right-8):right]
        x=[]
        for width in (3,8):
            ys=[r['values']['rush_att']for r in recent[-width:]if r['values']['rush_att']is not None]
            x.extend((sum(ys)/len(ys)if ys else math.nan,float(len(ys))))
        for lag in range(1,5):
            r=recent[-lag]if len(recent)>=lag else None;y=r['values']['rush_att']if r else None
            x.extend((y if y is not None else math.nan,(cutoff-r['kickoff'])/86400 if r else math.nan,float(y is None)))
        x.extend(float(pos==p)for p in ('QB','RB','WR','TE'))
        return x,recent[-1]['available']if recent else None
    return get


def summary(rows):
    values=[r['values']['rush_att']for r in rows]
    return dict(n=len(rows),zeros=values.count(0),zero_fraction=values.count(0)/len(values)if values else None,
        median=float(np.median(values))if values else None,mean=float(np.mean(values))if values else None,
        positive=sum(v>0 for v in values),unique_games=len({r['game_id']for r in rows}),
        positions=dict(collections.Counter(r['position']for r in rows)))


def diagnose(source_root,metadata_root,private_root,output_root,private_output):
    source_root,metadata_root,private_root,output_root,private_output=map(Path,(source_root,metadata_root,private_root,output_root,private_output))
    frozen=read_json(output_root/'HGB_RUSH_ATT_DIAGNOSIS_PROTOCOL.json')
    for item in frozen['artifacts']:
        if sha(ROOT/item['public_safe_id'])!=item['sha256']:raise ValueError('scope-pinned code or metadata changed')
    protocol=read_json(metadata_root/'FROZEN_PROTOCOL.json')
    if sha(Path(old.__file__))!=protocol['code_sha256']:raise ValueError('original model code changed')
    if sha(Path(old.empirical.__file__))!=protocol['helper_code_sha256']:raise ValueError('original helper changed')
    for source in protocol['source_ids']:
        if sha(source_root/source['name'])!=source['sha256']:raise ValueError('original source bytes changed')
    if sha(private_root/'frozen-queries.json')!=protocol['frozen_queries_sha256']:raise ValueError('original query bytes changed')
    # The original loader explicitly rejects2026week>7 before reading target values.
    rows,games,source_counts=old.load_source(source_root,protocol)
    eligible=[r for r in rows if r['position']in old.allowed_roles(protocol,'rush_att')and r['values']['rush_att']is not None]
    get_features=feature_function(rows)
    trainx=np.asarray([get_features(r['player_id'],r['position'],r['kickoff'])[0]for r in eligible],dtype=float)
    manifest=[];diagnostics=[];private_rows=[];feature_checks=[]
    for week in range(1,9):
        for arm in ('H-CURRENT','H-RECENT','H-MULTI'):
            for objective in ('absolute_error_point','squared_error_mean'):
                slot=f'W{week:02}-rush_att-{arm}-{objective}'
                fit_path=metadata_root/(slot+'-FIT.json');forecast_path=metadata_root/(slot+'-FORECAST.json')
                fit,forecast=read_json(fit_path),read_json(forecast_path)
                cutoff=utc(fit['fit_cutoff_utc']).timestamp();floor=2026 if arm=='H-CURRENT'else 2025 if arm=='H-RECENT'else 2022
                indices=[i for i,r in enumerate(eligible)if floor<=r['season']<=2026 and r['available']<cutoff]
                train=[eligible[i]for i in indices];x=trainx[indices];y=np.asarray([r['values']['rush_att']for r in train])
                membership=digest(canonical([(r['game_id'],r['player_id'])for r in train]))
                if membership!=fit['training_membership_sha256']or len(train)!=fit['training_n']:raise ValueError('reconstructed training membership mismatch')
                queries=restore(private_root,fit['query_features'],True)
                for q in queries:
                    if q['query'].get('blocked_reason'):continue
                    r=q['query'];computed,latest=get_features(r['player_id'],r['position'],r['cutoff'])
                    original=np.asarray([math.nan if v is None else v for v in q['features']])
                    if not np.allclose(original,computed,rtol=0,atol=1e-12,equal_nan=True)or latest!=q['latest_feature_available']:raise ValueError('query feature reconstruction differs')
                chunks=restore(private_root,forecast['packet'],True)['rows']
                if len(chunks)!=len(queries):raise ValueError('query/chunk count mismatch')
                qx=np.asarray([[math.nan if v is None else v for v in q['features']]for q in queries])
                result=dict(slot=slot,origin=week,history_regime=arm,objective=objective,fit_state=fit['state'],
                    fit_cutoff_utc=fit['fit_cutoff_utc'],training_membership_sha256=membership,training=summary(train),
                    training_roles={p:summary([r for r in train if r['position']==p])for p in ('QB','RB','WR','TE')},
                    primary_RB=summary([r for r in train if r['position']=='RB']),
                    extended_QB_WR_TE=summary([r for r in train if r['position']!='RB']),
                    proposed_QB_RB_only=summary([r for r in train if r['position']in ('QB','RB')]),
                    query_rows=len(chunks),query_positions=dict(collections.Counter(r['position']for r in chunks)),
                    feature_reconstruction_matches=True,feature_columns=list(old.FEATURES),new_fits=0,new_forecasts=0)
                if fit['model']:
                    model_body=restore(private_root,fit['model'])
                    # These self-generated model bytes must first pass their original digest.
                    model=pickle.loads(model_body)
                    raw=model._raw_predict(qx).ravel();predicted=model.predict(qx)
                    if not np.allclose(raw,predicted,rtol=0,atol=1e-12):raise ValueError('raw output differs from original predict API')
                    baseline=float(model._baseline_prediction.ravel()[0]);nodes=[t[0].nodes for t in model._predictors]
                    splits=[n for tree in nodes for n in tree if not n['is_leaf']]
                    used=collections.Counter(old.FEATURES[int(n['feature_idx'])]for n in splits)
                    gradients=model._loss.gradient(y,np.full(len(y),baseline))
                    observed_gradient_counts=dict(collections.Counter(map(float,gradients)))
                    signatures=collections.Counter((old.FEATURES[int(n['feature_idx'])],float(n['num_threshold']),bool(n['missing_go_to_left']))for n in splits)
                    first=nodes[0];last=nodes[-1]
                    root_gradient=float(sum(gradients));root_hessian=len(y)
                    root_split_count=[int(n['count'])for n in first if n['is_leaf']]
                    # With uniformgradient-1,H=1 and rootvalue0 this reproduces
                    # the installed splitgain; it is not a fitted counterfactual.
                    root_gain_if_uniform=sum(n*n/(n+10)for n in root_split_count)if len(root_split_count)==2 else None
                    result.update(model_sha256=fit['model']['sha256'],baseline=baseline,n_iterations=model.n_iter_,
                        tree_node_counts=dict(collections.Counter(len(t)for t in nodes)),tree_leaf_counts=dict(collections.Counter(int(sum(n['is_leaf']for n in t))for t in nodes)),
                        actually_used_split_features=dict(used),split_signatures=[dict(feature=k[0],threshold=k[1],missing_go_left=k[2],count=v)for k,v in signatures.items()],
                        first_tree=[dict(value=float(n['value']),count=int(n['count']),feature=old.FEATURES[int(n['feature_idx'])]if not n['is_leaf']else None,threshold=float(n['num_threshold'])if not n['is_leaf']else None,gain=float(n['gain']),is_leaf=bool(n['is_leaf']))for n in first],
                        last_tree_leaf_values=[float(n['value'])for n in last if n['is_leaf']],
                        initial_gradient_counts=observed_gradient_counts,initial_gradient_sum=root_gradient,initial_constant_hessian_sum=root_hessian,
                        root_gain_uniform_gradient_reconstruction=root_gain_if_uniform,
                        training_feature_support={name:dict(nonmissing=int(np.isfinite(x[:,i]).sum()),zeros=int((x[:,i]==0).sum()),unique_nonmissing=int(len(np.unique(x[np.isfinite(x[:,i]),i]))))for i,name in enumerate(old.FEATURES)})
                    mismatches=0;projected_changes=0
                    for q,record,p in zip(queries,chunks,raw):
                        if q['query']['player_id']!=record['player_id']:raise ValueError('original query order differs')
                        if record['status']=='ABSTAIN':continue
                        projected=max(0.,float(p))
                        mismatches+=not math.isclose(projected,record['prediction'],rel_tol=0,abs_tol=1e-12)
                        projected_changes+=float(p)!=projected
                        if week==8:private_rows.append(dict(query_id=record['query_id'],player_id=record['player_id'],game_id=record['game_id'],position=record['position'],history_regime=arm,objective=objective,original_prediction=record['prediction'],restored_raw_prediction=float(p),restored_projected_prediction=projected,source_feature_cutoff=record['cutoff'],latest_feature_available=record['latest_feature_available']))
                    if mismatches:raise ValueError('original issued predictions not reproduced')
                    result.update(retained_query_prediction_mismatches=mismatches,projection_changed_rows=projected_changes,
                        raw_prediction_min=float(np.min(raw)),raw_prediction_max=float(np.max(raw)),
                        query_feature_consumption={name:dict(nonmissing=int(np.isfinite(qx[:,i]).sum()),zeros=int((qx[:,i]==0).sum()))for i,name in enumerate(old.FEATURES)})
                issued=[r for r in chunks if r['status']!='ABSTAIN']
                result.update(issued_rows=len(issued),issued_zero_predictions=sum(r['prediction']==0 for r in issued),
                    issued_roles={p:dict(n=sum(r['position']==p for r in issued),zeros=sum(r['position']==p and r['prediction']==0 for r in issued),min=min((r['prediction']for r in issued if r['position']==p),default=None),max=max((r['prediction']for r in issued if r['position']==p),default=None))for p in ('QB','RB','WR','TE')})
                diagnostics.append(result)
                manifest.append(dict(slot=slot,fit_receipt_sha256=sha(fit_path),forecast_receipt_sha256=sha(forecast_path),model_sha256=fit['model']['sha256']if fit['model']else None,query_features_sha256=fit['query_features']['sha256'],prediction_chunk_sha256=forecast['packet']['sha256'],training_membership_sha256=membership))
    private_output.mkdir(exist_ok=False,parents=True)
    private_body=gzip.compress(canonical(dict(schema='v2-original-retained-RA-restoration-diagnostic-v1',rows=private_rows)),mtime=0)
    (private_output/'RESTORED_QUERY_DIAGNOSTICS.json.gz').write_bytes(private_body)
    result=dict(version=frozen['version'],completed_at_utc=datetime.now(timezone.utc).isoformat(),state='RETAINED_ARTIFACT_DIAGNOSIS_NO_NEW_FORECAST',diagnostic_protocol_sha256=sha(output_root/'HGB_RUSH_ATT_DIAGNOSIS_PROTOCOL.json'),source_counts=source_counts,source_ids=protocol['source_ids'],metadata_manifest=manifest,models=diagnostics,private_query_diagnostics_sha256=digest(private_body),new_fits=0,new_forecasts=0,week8_outcomes_read=0,train_frames='reconstructed from pinned source/helper semantics; exact original membership hashes; original feature snapshots reproduced independently',scope_limit='No new forecast skill experiment, postgame label, repair, deployment or pristine evaluation claim')
    body=canonical(json_safe(result))
    with(output_root/'HGB_RUSH_ATT_COLLAPSE_DIAGNOSIS.json').open('xb')as h:h.write(body)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for arg in ('source-root','metadata-root','private-root','output-root','private-output'):parser.add_argument('--'+arg,type=Path,required=True)
    with threadpool_limits(limits=2):result=diagnose(**vars(parser.parse_args()))
    print(json.dumps(dict(models=len(result['models']),new_fits=0,new_forecasts=0,week8_outcomes_read=0,completed_at_utc=result['completed_at_utc']),indent=2))
