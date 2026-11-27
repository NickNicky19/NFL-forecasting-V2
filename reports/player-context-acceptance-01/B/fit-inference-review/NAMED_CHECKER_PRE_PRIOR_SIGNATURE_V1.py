"""No-fit review of the newly added optional named consumer guard."""
import argparse,gzip,hashlib,json,sys
from datetime import datetime,timezone
from pathlib import Path
def digest(b):return hashlib.sha256(b).hexdigest()
def read(p):
    b=Path(p).read_bytes();return json.loads(gzip.decompress(b)if str(p).endswith('.gz')else b)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repository',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();root=a.repository.resolve();sys.path.insert(0,str(root))
    import numpy as np
    from nfl_v2.player_context_named_adapter_v3 import NamedLeafAdapter,ADAPTER_VERSION
    from nfl_v2.player_context_matchup import VERSION,load_inputs,restored_forest_law
    from nfl_v2.distribution_laws import prior
    b=root/'reports/player-context-matchup-01/B';schema=(b/'qb-wave-v1/FEATURE_ORDER_V1.json').read_bytes();receipt=(b/'qb-wave-v1/fits/2025-W01-E1.json.gz').read_bytes();packet=read(b/'qb-wave-v1/predictions/2025-W01.json.gz');names=json.loads(schema)['orders']['E1']
    inputs=load_inputs(b/'source-fields-v3/DERIVED_QB_GAME_INPUTS.json.gz');train=[r for r in inputs if r.get('physical_participation')and r['target_parity']and r['season']>=2024 and r['available']<packet['fit_cutoff']]
    pr=prior([r['official_completions']for r in train],'pass_cmp')
    kwargs=dict(schema_bytes=schema,expected_schema_sha256=digest(schema),receipt_bytes=receipt,expected_receipt_sha256=digest(receipt),arm='E1',fallback_prior=pr,producer_version=VERSION)
    adapter=NamedLeafAdapter(**kwargs);original=[r for r in packet['rows']if r['method']=='E1'];records=[dict(query_id=r['game_id']+':'+r['player_id'],feature_names=names,feature_values=r['features'])for r in original]
    expected={r['game_id']+':'+r['player_id']:r for r in original};got=adapter.predict_batch(list(reversed(records)));error=0
    for r in got:
        saved=expected[r['query_id']];error=max(error,abs(r['law'].mean-saved['mean']));assert r['law'].quantile(.5)==saved['lower_median']
        single=adapter.predict_one(feature_names=names,feature_values=next(x['features']for x in original if x['game_id']+':'+x['player_id']==r['query_id']))
        assert single.mean==r['law'].mean
    assert error<1e-10
    rejected=[]
    def must_reject(label,call):
        try:call()
        except ValueError:rejected.append(label);return
        raise AssertionError('Guard did not reject '+label)
    perm=list(names);perm[0],perm[1]=perm[1],perm[0]
    must_reject('same_width_wrong_feature_name_order',lambda:adapter.predict_one(feature_names=perm,feature_values=records[0]['feature_values']))
    must_reject('wrong_schema_hash',lambda:NamedLeafAdapter(**dict(kwargs,expected_schema_sha256='0'*64)))
    must_reject('wrong_receipt_hash',lambda:NamedLeafAdapter(**dict(kwargs,expected_receipt_sha256='0'*64)))
    must_reject('wrong_arm',lambda:NamedLeafAdapter(**dict(kwargs,arm='E0')))
    must_reject('duplicate_query_id',lambda:adapter.predict_batch([records[0],records[0]]))
    must_reject('empty_query_id',lambda:adapter.predict_batch([dict(records[0],query_id='')]))
    invalid=list(records[0]['feature_values']);invalid[0]=float('inf')
    must_reject('infinite_input_not_unknown',lambda:adapter.predict_one(feature_names=names,feature_values=invalid))
    unknown=list(records[0]['feature_values']);unknown[0]=None
    actual=adapter.predict_one(feature_names=names,feature_values=unknown)
    old=restored_forest_law(read(b/'qb-wave-v1/fits/2025-W01-E1.json.gz')['model'],np.asarray(unknown,float),pr)
    assert actual.mean==old.mean and actual.quantile(.5)==old.quantile(.5)
    result=dict(state='PASS_OPT_IN_NAMED_LEAF_GUARD_WITH_SCOPED_CALLER_REQUIREMENTS',at_utc=datetime.now(timezone.utc).isoformat(),adapter_version=ADAPTER_VERSION,adapter_source_sha256=digest((root/'nfl_v2/player_context_named_adapter_v3.py').read_bytes()),
        schema_sha256=digest(schema),receipt_sha256=digest(receipt),queries=34,single_batch_reverse_identity_parity=True,maximum_mean_roundoff=error,guards_rejected=rejected,
        explicit_unknown_uses_fitted_imputer=True,new_NFL_fits=0,synthetic_fits=0,new_forecasts=0,changed_saved_NFL_rows=0,old_consumer_unchanged=True,
        limits=['Opt-inE0-E3leaf consumer guard; no FTN named schema or GLM change.','This check uses correct earlier-training prior; constructor still accepts caller-provided prior object, so its identity/cutoff needs separate binding.','Query-model temporal/horizon contract remains external because this wrapper does not receive source/decision clocks.','Names protect declared column order; they cannot prove a caller attached truthful numerical values to those names.'])
    p=a.out/'NAMED_ADAPTER_V3_REVIEW_V1.json';assert not p.exists();p.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
