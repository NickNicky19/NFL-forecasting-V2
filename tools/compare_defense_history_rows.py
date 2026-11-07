"""Paired history contrasts and fallback decomposition from retained D1/D2 rows."""
import argparse,collections,csv,gzip,hashlib,json,math
from pathlib import Path
CORE=('H-CURRENT-COMMON','H-RECENT-COMMON','H-MULTI-COMMON')
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def identity(r):return tuple(r[k]for k in('game_id','player_id','target','population'))
def loss(r):return(r['prediction']-r['actual'])**2 if r['target']=='anytime_td'else abs(r['prediction']-r['actual'])
def write(p,x):
    with Path(p).open('xb')as h:h.write(canonical(x))
def run(public_root,private_root):
    public_root,private_root=map(Path,(public_root,private_root));panels=collections.defaultdict(lambda:collections.defaultdict(dict));receipts=[]
    for path in sorted(public_root.glob('W0[1-7]-*-FORECAST.json')):
        receipt=json.loads(path.read_bytes());d=receipt['packet'];blob=(private_root/d.get('bundle_name',d.get('name'))).read_bytes();body=gzip.decompress(blob)
        if hashlib.sha256(blob).hexdigest()!=d['sha256']:raise ValueError('retainedchunkhashmismatch')
        receipts.append(dict(receipt_name=path.name,receipt_sha256=sha(path),chunk_sha256=d['sha256']))
        for r in json.loads(body)['rows']:
            if int(r['week'])>7:raise ValueError('futurequerynotadmitted')
            k=(r['information_group'],r['target'],r['population'],r['product_id']);key=identity(r);policy=r['policy_id']
            if key in panels[k][policy]:raise ValueError('duplicateretainedquery')
            panels[k][policy][key]={f:r[f]for f in('game_id','week','target','prediction','actual','fallback')}
    pairs=[];decomposition=[];examples={};source_summary=[]
    for(group,target,pop,product),policies in sorted(panels.items()):
        if set(policies)!=set((*CORE,'H-CURRENT-STRICT')):raise ValueError('missinghistorypolicy')
        ids=set(policies[CORE[0]])
        if any(set(r)!=ids for r in policies.values()):raise ValueError('historyqueryidentitychanged')
        if any(r[k]['actual']!=policies[CORE[0]][k]['actual']for r in policies.values()for k in ids):raise ValueError('historylabelchanged')
        eligible={k for k in ids if all(policies[p][k]['actual']is not None and policies[p][k]['prediction']is not None for p in policies)}
        common={k for k in eligible if all(policies[p][k]['fallback']=='none'for p in CORE)}
        strictcommon={k for k in eligible if policies[CORE[0]][k]['fallback']=='none'and policies['H-CURRENT-STRICT'][k]['fallback']=='none'}
        source_summary.append(dict(information_group=group,target=target,population=pop,product_id=product,frozen_query_n=len(ids),supported_full_n=len(eligible),three_core_learned_common_n=len(common),strict_current_pair_learned_n=len(strictcommon),full_membership_sha256=hashlib.sha256(canonical(sorted(eligible))).hexdigest(),three_core_learned_membership_sha256=hashlib.sha256(canonical(sorted(common))).hexdigest()))
        for policy,rs in policies.items():
            supported=[r for k,r in rs.items()if k in eligible];fb=[r for r in supported if r['fallback']!='none'];learn=[r for r in supported if r['fallback']=='none'];total=math.fsum(loss(r)for r in supported);fbloss=math.fsum(loss(r)for r in fb);learnloss=math.fsum(loss(r)for r in learn)
            if not math.isclose(total,fbloss+learnloss,rel_tol=1e-12,abs_tol=1e-10):raise ValueError('fallbackdecompositionfailure')
            decomposition.append(dict(information_group=group,target=target,population=pop,product_id=product,policy_id=policy,metric='brier'if target=='anytime_td'else'mae',forecast_query_n=len(rs),supported_n=len(supported),missing_actual_n=len(rs)-len(supported),fallback_forecast_n=sum(r['fallback']!='none'for r in rs.values()),fallback_supported_n=len(fb),learned_supported_n=len(learn),full_error=total/len(supported)if supported else None,fallback_loss_sum=fbloss,learned_loss_sum=learnloss,total_loss_sum=total,fallback_error=fbloss/len(fb)if fb else None,own_learned_error=learnloss/len(learn)if learn else None,fallback_contribution_to_full_error=fbloss/len(supported)if supported else None,learned_contribution_to_full_error=learnloss/len(supported)if supported else None,interpretation='ownlearnedmeansdifferentcasesacrossarms;usecommonintersectionforpairedhistory'))
        contrasts=[(a,b,view,ks,'isolatedfitwindow_common2022featurememory')for a,b in[(CORE[1],CORE[0]),(CORE[2],CORE[0]),(CORE[2],CORE[1])]for view,ks in[('full_system',eligible),('three_core_learned_common',common)]]
        contrasts += [('H-CURRENT-STRICT',CORE[0],view,ks,'complete_information_policy_change_same2026fitlabels')for view,ks in[('full_system',eligible),('strict_current_pair_learned',strictcommon)]]
        for a,b,view,ks,meaning in contrasts:
            aa,bb=policies[a],policies[b];xs=[loss(aa[k])for k in sorted(ks)];ys=[loss(bb[k])for k in sorted(ks)];ds=[x-y for x,y in zip(xs,ys)];n=len(ds);bygame=collections.defaultdict(list);byweek=collections.defaultdict(list)
            for k,d in zip(sorted(ks),ds):bygame[aa[k]['game_id']].append(d);byweek[aa[k]['week']].append(d)
            delta=math.fsum(ds)/n if n else None;ca=math.fsum(xs)/n if n else None;cb=math.fsum(ys)/n if n else None;g=len(bygame);se=math.sqrt(g/(g-1)*math.fsum((math.fsum(v)-len(v)*delta)**2 for v in bygame.values())/n**2)if g>=8 else None
            pairs.append(dict(information_group=group,target=target,population=pop,product_id=product,candidate_policy_id=a,comparator_policy_id=b,view=view,comparison_kind=meaning,status='PAIRED_RETAINED_ROWS'if n else'UNESTABLISHED_NO_COMMON_LEARNED_ROWS',metric='brier'if target=='anytime_td'else'mae',paired_n=n,three_core_learned_common_n=len(common),candidate_error=ca,comparator_error=cb,error_delta=delta,relative_error_delta=delta/cb if cb else None,membership_sha256=hashlib.sha256(canonical(sorted(ks))).hexdigest(),unique_games=g,week_clusters=len(byweek),week_interval=None,game_cluster_sensitivity_se=se,game_normal95_sensitivity=[delta-1.96*se,delta+1.96*se]if se is not None else None,uncertainty='fewerthan8exposedweeks;gameSEsensitivitynotmultiplicityorhindsightselectionadjusted',weekly_paired_delta={str(w):math.fsum(v)/len(v)for w,v in byweek.items()}))
    result=dict(version='v2-qualified-defense-same-row-history-paired-contrasts-v1',source_score_sha256=sha(public_root/'SCORES.json'),source_protocol_sha256=sha(public_root/'FROZEN_PROTOCOL.json'),original_retained_chunks=receipts,panels=source_summary,paired_contrasts=pairs,fallback_decomposition=decomposition,artifact_kind='pairedcontrast_and_decomposition_sidecar_notnewunivariate_ranking_scoreboard',exposure='same2026W1-W7previouslyexaminedNFLgames;currentvintageparticipantdiagnostic;strictcomparisonscompleteinformationpolicy',new_fits=0,new_forecasts=0,week8_outcomes_read=0)
    write(public_root/'HISTORY_PAIRED.json',result)
    for name,rows in[('HISTORY_PAIRED.csv',pairs),('FALLBACK_DECOMPOSITION.csv',decomposition),('HISTORY_PANEL_SUPPORT.csv',source_summary)]:
        with(public_root/name).open('x',newline='')as h:
            w=csv.DictWriter(h,fieldnames=list(rows[0]));w.writeheader();w.writerows({k:json.dumps(v,sort_keys=True)if isinstance(v,(dict,list))else v for k,v in r.items()}for r in rows)
    return dict(paired_contrasts=len(pairs),fallback_decompositions=len(decomposition),distinct_target_product_population_panels=len(source_summary),new_fits=0,new_forecasts=0)
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for a in('public-root','private-root'):p.add_argument('--'+a,type=Path,required=True)
    print(json.dumps(run(**vars(p.parse_args()))))
