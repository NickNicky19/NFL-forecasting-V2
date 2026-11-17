"""Bind paired comparisons to immutable carry score rows without changing them."""
import argparse,gzip,json,math,hashlib
from pathlib import Path
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def key(r):return tuple(r[k]for k in('game_id','player_id','target','population'))
def run(public_root,private_root):
    public_root,private_root=map(Path,(public_root,private_root));score=public_root/'SCORES.json';scores=json.loads(score.read_bytes());receipt=json.loads((public_root/'RUN_RECEIPT.json').read_bytes());blob=(private_root/'CARRY_CONTROL_ROWS.json.gz').read_bytes()
    if hashlib.sha256(blob).hexdigest()!=receipt['private_rows_sha256']:raise ValueError('frozenprivatecarryrowhash')
    records=json.loads(gzip.decompress(blob))['methods'];mapping={name:{key(r):r for r in rows}for name,rows in records.items()};baseline=mapping['prior_best_mean'];shared=set.intersection(*[{k for k,r in rs.items()if r['actual']is not None and r['fallback']=='none'}for rs in mapping.values()]);output=[]
    for i,s in enumerate(scores):
        name=s['record_id'].split(':')[1];view=s['fallback_view'];rs=[r for k,r in mapping[name].items()if r['population']==s['population']and(view=='full_system'or view=='own_learned_only'and r['fallback']=='none'or view=='fallback_only'and r['fallback']!='none'or view=='all_five_learned_overlap'and k in shared)];rows=[r for r in rs if r['actual']is not None and r['prediction']is not None]
        if len(rows)!=s['n']:raise ValueError('frozencarryviewcountmismatch')
        if not rows:comparison=dict(status='UNESTABLISHED',reason='nosupportedoutcomesinthisfrozenview')
        else:
            y=[abs(baseline[key(r)]['prediction']-r['actual'])for r in rows];candidate=math.fsum(abs(r['prediction']-r['actual'])for r in rows)/len(rows)
            if candidate!=s['mae']:raise ValueError('candidateviewmaemismatch')
            comparator=math.fsum(y)/len(rows);delta=candidate-comparator
            comparison=dict(status='PAIRED_RETAINED_ROWS',comparison_purpose='control_self_reproduction'if name=='prior_best_mean'else'strongest_prior_mean_control',comparator_procedure_id='hgb-direct-history-controls-v1:squared_error_mean',comparator_history_regime='H-MULTI',comparator_product_id='squared_error_mean',metric='mae',candidate_error=candidate,comparator_error=comparator,paired_n=len(rows),membership_sha256=hashlib.sha256(canonical(sorted(key(r)for r in rows))).hexdigest(),cutoff_policy='samehistoricalsourcequerygameand7dayavailability;comparatorrestrictedtoexactcandidatescoredviewIDs',uncertainty=dict(week_clusters=len({r['week']for r in rows}),week_interval=None,reason='sevenexposedweeks;separatepairedcontrastfileprovidesgameclustersensitivitynotmultiplicityadjusted'),absolute_error_delta=delta,relative_error_delta=delta/comparator if comparator else None,relative_delta_reason=None if comparator else'zero_comparator_error_denominator')
        output.append(dict(source_record_id=s['record_id'],source_row_index=i,comparison=comparison))
    result=dict(source_score_sha256=hashlib.sha256(score.read_bytes()).hexdigest(),rows=output,additional_pairwise_contrasts='PAIRED_CONTRASTS.json',relative_sign='candidate-minus-comparator;negativefavorscandidate;improvementfieldinoriginalcontrastsisoppositesign',new_fits=0,new_forecasts=0)
    with(public_root/'COMPARISON_ANNOTATIONS.json').open('xb')as h:h.write(canonical(result))
    return dict(rows=len(output),bound=sum(r['comparison']['status']=='PAIRED_RETAINED_ROWS'for r in output),source_score_sha256=result['source_score_sha256'])
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for a in('public-root','private-root'):p.add_argument('--'+a,type=Path,required=True)
    print(json.dumps(run(**vars(p.parse_args()))))
