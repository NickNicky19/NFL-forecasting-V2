"""Independent C02 future-only capture replay; no future labels or fits."""
import argparse
from collections import Counter,defaultdict
from functools import lru_cache
import gzip,hashlib,json,math,pickle,sys,warnings
from pathlib import Path
import numpy as np
from threadpoolctl import threadpool_limits
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'reports/continuation-20261030'))
from check_new_wave_prefixes import load,clock,canonical
from check_retained_distribution_math import summaries
PUBLIC=ROOT/'reports/continuation-20261030b/c02-future-shadow-v1';POSITIONS=('QB','RB','WR','TE');KEEP=(0,1,2,3,16,17,18,19)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def decode(p):return json.loads(gzip.decompress(p.read_bytes()))
def close(a,b):assert(a is None and b is None)or(a is not None and b is not None and math.isclose(float(a),float(b),rel_tol=5e-11,abs_tol=4e-10)),(a,b)
def verify(private,source):
    p=json.loads((PUBLIC/'FROZEN_PROTOCOL.json').read_text());run=json.loads((PUBLIC/'RUN_RECEIPT.json').read_text());counts=Counter()
    assert sha(ROOT/'nfl_v2/c02_future_shadow.py')==p['code_sha256'];assert sha(PUBLIC/'FROZEN_PROTOCOL.json')==run['protocol_sha256']
    for name,digest in p['helper_code_sha256'].items():assert sha(ROOT/'nfl_v2'/name)==digest
    assert sha(ROOT/'nfl_v2/distribution_laws.py')==p['law_code_sha256']
    review=ROOT/'reports/continuation-20261030b/C02_FUTURE_PREFIT_REVIEW.json';registration=json.loads((PUBLIC/'EXECUTION_REGISTRATION.json').read_text());assert registration['independent_prefit_review_sha256']==sha(review)
    assert clock(json.loads(review.read_text())['reviewed_at_utc'])<=clock(registration['actual_started_at'])
    assert sha(private/'frozen-queries.json')==p['frozen_queries_sha256'];queries=json.loads((private/'frozen-queries.json').read_text());querymap={q['query_id']:q for q in queries};assert len(querymap)==2229
    packet=private/run['packet']['bundle_name'];assert sha(packet)==run['packet']['sha256'];records=decode(packet)['rows']
    assert len(records)==run['output_views']==32488 and run['actual_Week8_outcomes_read']==run['score_views']==0
    aggregate={};cuts=clock(p['fixed_query_asof_utc']);aggregate_persistence=clock(run['actual_aggregate_persistence_completed_at'])
    for r in records:
        q=querymap[r['query_id']];assert r['actual']is None and r['actual_status']=='PENDING_FUTURE'and r['week']==8
        assert r['feature_cutoff_utc']==p['fixed_query_asof_utc']
        ident=(r['variant'],r['policy_id'],r['product_id'],r['query_id']);assert ident not in aggregate;aggregate[ident]=r
        if r['prediction']is not None:
            assert r['issued_at_utc']==r['actual_generated_at'];assert cuts<=clock(r['issued_at_utc'])<aggregate_persistence<clock(q['owner_input_cutoff_utc'])<clock(q['kickoff_utc'])
            close(r['actual_horizon_seconds'],clock(q['kickoff_utc'])-clock(r['issued_at_utc']))
            if r['target']=='anytime_td':assert 0<=r['prediction']<=1
            counts['issued']+=1
        else:assert r['status']=='ABSTAIN'and r['abstention_reason'];counts['abstained']+=1
    assert counts['issued']==run['issued']==32376 and counts['abstained']==run['abstained']==112
    for k,r in aggregate.items():
        if k[0]!='retained_ordered_control':continue
        other=aggregate[('c02_explicit_lag_block_removed',)+k[1:]]
        for field in('fallback','abstention_reason','actual','feature_cutoff_utc','latest_feature_available','training_fit_cutoff_utc'):assert r[field]==other[field]
        counts['variant_common_query_and_fallback_pairs']+=1
    rows,history,games=load(source,p)
    @lru_cache(None)
    def feature(player,position,target,cutoff,floor):
        rs=[r for r in history.get(player,[])if r['season']>=floor and r['available']<cutoff][-8:];out=[]
        for w in(3,8):
            ys=[float(r['values'][target])for r in rs[-w:]if r['values'][target]is not None];out.extend((sum(ys)/len(ys)if ys else None,float(len(ys))))
        for lag in range(1,5):
            r=rs[-lag]if len(rs)>=lag else None;y=r['values'][target]if r else None;out.extend((float(y)if y is not None else None,(cutoff-r['kickoff'])/86400 if r else None,float(y is None)))
        out.extend(float(position==v)for v in POSITIONS)
        return out,rs[-1]['available']if rs else None
    bindings=json.loads((PUBLIC/'RETAINED_CONTROL_BINDINGS.json').read_text());local=json.loads((private/'CONTROL_BINDINGS_PRIVATE.json').read_text());assert len(bindings)==48
    reconstructed=set()
    with threadpool_limits(limits=2):
        for binding in bindings:
            name=binding['key'].replace(':','--');fit=json.loads((PUBLIC/(name+'-FIT.json')).read_text());fr=json.loads((PUBLIC/(name+'-FORECAST.json')).read_text());target=binding['target'];floor=binding['feature_floor'];origin=clock(binding['fit_cutoff_utc']);policy=p['policies'][binding['policy_id']]
            roles=set(POSITIONS)if target=='nick-chart-ppr-v1'else set(p['source_role_contract']['primary'][target]+p['source_role_contract']['extended'].get(target,[]))
            train=[r for r in rows if r['position']in roles and r['values'][target]is not None and r['season']>=max(floor,policy['fit_floor'])and r['available']<origin]
            assert len(train)==fit['training_n']==binding['training_n'];membership=hashlib.sha256(canonical([(r['game_id'],r['player_id'])for r in train])).hexdigest();assert membership==fit['training_membership_sha256']==binding['training_membership_sha256']
            assert max((r['available']for r in train),default=None)==fit['latest_training_label_available']<origin
            oldpath=Path(local[binding['key']]['receipt_path']);assert sha(oldpath)==binding['receipt_sha256'];old=json.loads(oldpath.read_text())
            for field in('training_membership_sha256','prior_parameters','prior_position_sample_counts'):assert old[field]==fit[field]
            maxima=[feature(r['player_id'],r['position'],target,r['kickoff'],floor)[1]for r in train];assert all(m is None or m<r['kickoff']for r,m in zip(train,maxima));assert max((m for m in maxima if m is not None),default=None)==fit['latest_training_feature_available'];counts['raw_training_control_clock_checks']+=7
            fp=private/fit['query_features']['bundle_name'];assert sha(fp)==fit['query_features']['sha256'];entries=decode(fp)
            for entry in entries:
                q=entry['query'];full,maximum=feature(q['player_id'],q['position'],target,cuts,floor)
                for a,b in zip(full,entry['full_features']):close(a,b);counts['independent_raw_query_feature_values']+=1
                for a,b in zip([full[i]for i in KEEP],entry['candidate_features']):close(a,b);counts['independent_raw_query_feature_values']+=1
                assert maximum==entry['latest_feature_available']and(maximum is None or maximum<cuts)
            slotpath=private/fr['packet']['bundle_name'];assert sha(slotpath)==fr['packet']['sha256'];slot=decode(slotpath)['rows'];assert len(slot)==fr['output_views']
            for r in slot:
                ident=(r['variant'],r['policy_id'],r['product_id'],r['query_id']);assert r==aggregate[ident];assert ident not in reconstructed;reconstructed.add(ident)
                if r['prediction']is not None:assert clock(r['issued_at_utc'])<=clock(fr['actual_persistence_completed_at'])<clock(r['owner_input_cutoff_utc'])
            models={}
            for variant,path,digest in [('retained_ordered_control',Path(local[binding['key']]['model_path']),binding['model_sha256']),('c02_explicit_lag_block_removed',private/fit['model']['bundle_name'],fit['model']['sha256'])]:
                assert sha(path)==digest;models[variant]=pickle.loads(gzip.decompress(path.read_bytes()));counts[variant+'_model_hashes_verified']+=1
            assert clock(fit['actual_fit_started_at'])>=clock(registration['actual_started_at']);assert clock(fit['actual_fit_completed_at'])<=clock(fr['actual_persistence_completed_at'])
            byquery={r['query_id']:r for r in slot if r['prediction']is not None};eligible=[e for e in entries if e['query']['query_id']in byquery];chosen=[]
            for want_fallback in(False,True):
                item=next((e for e in eligible if(e['full_features'][3]<=0)==want_fallback),None)
                if item:chosen.append(item)
            for e in chosen:
                q=e['query']
                for variant,model in models.items():
                    sample=next(r for r in slot if r['query_id']==q['query_id']and r['variant']==variant);law=fit['prior_parameters'][q['position']]
                    if e['full_features'][3]>0:
                        f=e['full_features']if variant=='retained_ordered_control'else e['candidate_features'];x=np.asarray([[math.nan if v is None else v for v in f]]);design=np.column_stack((np.where(np.isfinite(x),x,model.design.median),~np.isfinite(x))).astype(float);leaf=model.estimator.apply(design)[0];weights=sum((h[leaf[j]].toarray().ravel()/len(model.hist)for j,h in enumerate(model.hist)),start=np.zeros(len(model.support)));weights/=weights.sum();law=dict(kind='mixture',support=model.support,weights=weights,prior=law)
                    d=summaries(law,None);scale=50 if target=='nick-chart-ppr-v1'else 1
                    for field in('mean','lower_median','q05','q95','interval90_width'):close(sample['distribution_summary'][field],d[field]/scale);counts['independent_fixed_model_law_fields']+=1
                    close(sample['distribution_summary']['zero_mass'],d['zero_mass']);assert sample['distribution_summary']['crps']is None and sample['distribution_summary']['nll']is None;counts['representative_existing_model_laws']+=1
    assert len(reconstructed)==len(aggregate)
    assert run['actual_fit_calls']==run['retained_new_models']==run['retained_control_models']==run['completed_cells']==48
    assert run['resource']['wall_seconds']<=p['budget']['wall_seconds']and run['resource']['cpu_seconds']<=p['budget']['cpu_seconds']and run['resource']['peak_rss_bytes']<=p['budget']['max_peak_memory_bytes']
    return dict(status='PASS_CAPTURE_RAW_PREFIX_STRICT_FLOOR_CONTROL_TRAINING_AND_LAW_REPLAY',counts=dict(counts),future_views=len(records),query_cells=2229,query_games=13,score_views=0,asof_utc=p['fixed_query_asof_utc'],aggregate_persistence_utc=run['actual_aggregate_persistence_completed_at'],protocol_sha256=sha(PUBLIC/'FROZEN_PROTOCOL.json'),packet_sha256=sha(packet),prefit_review_sha256=sha(review),evidence='ACTUAL_PROSPECTIVE_RESEARCH_SHADOW; old-current-vintage training rows with conservative seven-day availability',limits='New current issuance of retained ordered model weights and new C02 candidates; no original captures replaced, no future outcomes or skill measured, owner admission pending',new_fits=0,new_forecasts=0,week8_outcomes_read=0)
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--private-root',type=Path,required=True);parser.add_argument('--source-root',type=Path,required=True);args=parser.parse_args();report=verify(args.private_root,args.source_root);Path(__file__).with_name('C02_FUTURE_INDEPENDENT_REVIEW.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
