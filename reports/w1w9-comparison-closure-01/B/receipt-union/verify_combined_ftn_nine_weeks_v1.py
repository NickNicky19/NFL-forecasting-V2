"""Independent fixed-panel direction arithmetic, without author grader imports.

A early records remain hash-bound owner-local aggregates. Native rows/laws are
recomputed manually. FTN-derived output: CC-BY-SA-4.0, FTN Data via nflverse.
"""
import argparse,collections,gzip,hashlib,json,math
from datetime import datetime,timezone
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[4]
BASE=ROOT/'reports/w1w9-comparison-closure-01/B/receipt-union'
OLD=ROOT/'reports/information-first-20261112-01/B/completion-wave-v1/predictions'
NS='B-FTN-BALL-QUALITY-COMPLETION-v1:'


def read(p):
    p=Path(p);body=p.read_bytes();return json.loads(gzip.decompress(body)if p.suffix=='.gz'else body)

def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def empty(n=0):return dict(eligible=n,available=0,selected=0,unavailable=0,unknown=0,abstained=0,push=0,void=0,fallback=0,wins=0,losses=0,decided=0,Over=dict(wins=0,losses=0,decided=0,selected=0,unknown=0),Under=dict(wins=0,losses=0,decided=0,selected=0,unknown=0))

def rate(x):
    x=dict(x);x['accuracy']=x['wins']/x['decided']if x['decided']else None
    for s in ['Over','Under']:
        if s in x:x[s]=dict(x[s],accuracy=x[s]['wins']/x[s]['decided']if x[s]['decided']else None)
    return x

def cdf(law,k):
    if k<0:return 0.
    assert law['kind']=='leaf_mixture'and law['prior']['kind']=='geometric'
    q=law['prior']['q'];b=law['mixture'];return (1-b)*sum(w for v,w in zip(law['support'],law['weights'])if v<=k)+b*(1-q**(k+1))

def metrics(rows):
    z=empty(len(rows));numerical=[];logs=[]
    for r in rows:
        if r['unavailable']:z['unavailable']+=1;continue
        z['available']+=1;z['fallback']+=int(r['fallback']);sd=r['side']
        if sd is None:z['abstained']+=1;continue
        z['selected']+=1;part=z['Over'if sd=='OVER'else'Under'];part['selected']+=1
        if r['actual']is None:z['unknown']+=1;part['unknown']+=1;continue
        if r['actual']==r['line']:z['push']+=1;continue
        hit=(r['actual']>r['line'])==(sd=='OVER');z['wins'if hit else'losses']+=1;z['decided']+=1;part['wins'if hit else'losses']+=1;part['decided']+=1
        if r['point']is not None:numerical.append(r['point']-r['actual'])
        if r['prob']is not None:
            event='over'if r['actual']>r['line']else'under'if r['actual']<r['line']else'push';logs.append(-math.log(r['prob'][event]))
    z=rate(z);z['numerical']=dict(n=len(numerical),MAE=sum(abs(v)for v in numerical)/len(numerical)if numerical else None,MSE=sum(v*v for v in numerical)/len(numerical)if numerical else None,bias=sum(numerical)/len(numerical)if numerical else None)
    z['three_state_log_loss']=sum(logs)/len(logs)if logs else None;z['law_events']=len(logs)
    return z

def early_summary(r):
    z=empty(r['eligible']);z.update(available=r['eligible']-r['unavailable'],selected=r['COMBINED']['selected'],unavailable=r['unavailable'],unknown=r['eligible']-r['COMBINED']['decided']-r['unavailable']-r['abstentions'],abstained=r['abstentions'],wins=r['COMBINED']['wins']or 0,losses=r['COMBINED']['losses']or 0,decided=r['COMBINED']['decided'],fallback=sum(n for k,n in r['fallback_states'].items()if k not in ['none','NONE','learned','NOT_APPLICABLE','']))
    for s in ['Over','Under']:
        a=r[s.upper()];z[s]=dict(wins=a['wins']or 0,losses=a['losses']or 0,decided=a['decided'],selected=a['selected'],unknown=0)
    z=rate(z);z['numerical']=dict(n=r['numerical']['scored'],MAE=r['numerical']['MAE'],MSE=r['numerical']['MSE'],bias=r['numerical']['bias']);z['three_state_log_loss']=r['probability']['three_state_log_loss'];z['law_events']=r['probability']['events'];return z

def sum_metrics(blocks):
    z=empty()
    for key in ['eligible','available','selected','unavailable','unknown','abstained','push','void','fallback','wins','losses','decided']:z[key]=sum(r[key]for r in blocks)
    for s in ['Over','Under']:
        for k in z[s]:z[s][k]=sum(r[s][k]for r in blocks)
    z=rate(z);n=sum(r['numerical']['n']for r in blocks);z['numerical']={'n':n}
    for k in ['MAE','MSE','bias']:z['numerical'][k]=sum(r['numerical']['n']*r['numerical'][k]for r in blocks if r['numerical']['n'])/n if n else None
    n=sum(r['law_events']for r in blocks);z['law_events']=n;z['three_state_log_loss']=sum(r['law_events']*r['three_state_log_loss']for r in blocks if r['law_events'])/n if n else None
    return z

def interval(blocks):
    sums=np.asarray([x['loss_difference_sum']for x in blocks],float);counts=np.asarray([x['n']for x in blocks],int);sample=np.random.default_rng(1703).integers(0,len(blocks),size=(500,len(blocks)));values=sums[sample].sum(axis=1)/counts[sample].sum(axis=1)
    return [float(v)for v in np.quantile(values,[.025,.975],method='linear')]

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--sources',type=Path,required=True);ap.add_argument('--early-source',type=Path,required=True);a=ap.parse_args()
    early=read(BASE/'A84_PUBLIC_ARITHMETIC_AND_SCOPE_V1.json')
    early_records={(r['candidate_id'],r['week_view']):r for r in early['records']};amap=read(a.sources);offers=[]
    for w in range(5,10):
        rows=[dict(r)for r in read(amap[str(w)])['rows']if r['target']=='pass_cmp'];assert len(rows)==(30 if w==9 else 28)
        assert len({(r['game_id'],r['player_id'])for r in rows})==len(rows)
        for r in rows:assert r['week']==w and r['actual']is not None and r['label_state']=='SUPPORTED'
        offers+=rows
    assert len(offers)==142 and collections.Counter(r['line_from'].lower()for r in offers)=={'dk':141,'sleeper':1}
    preds={}
    for w in range(5,10):
        x=read(OLD/f'2026-W{w:02}.json.gz')
        for r in x['rows']:
            if r['method']in ['B0','B1','B2']:preds[r['method'],r['game_id'],r['player_id']]=r
    policy_rows={};native_masks={};allweekly={};cumulative={};sourceblocks={};checks=0
    products=['mean','lower_median','P2'];ids=[NS+arm+'::'+p for arm in ['B0','B1','B2']for p in products]+['ALWAYS_OVER','ALWAYS_UNDER']
    for cid in ids:
        rows=[]
        for o in offers:
            y=float(o['actual']);line=float(o['line']);assert math.isfinite(y)and y>=0 and y==int(y)and math.isfinite(line)
            point=None;prob=None;fallback=False;unavailable=False
            if cid.startswith(NS):
                arm,p=cid[len(NS):].split('::');f=preds.get((arm,o['game_id'],o['player_id']));unavailable=f is None
                if not unavailable:
                    assert f['actual']==y and f['position']=='QB'and f['week']==o['week'];k=math.floor(line);under=cdf(f['law'],k-1 if line==k else k);at=cdf(f['law'],k);prob=dict(over=1-at,under=under,push=at-under);assert all(-1e-12<=v<=1+1e-12 for v in prob.values())and abs(sum(prob.values())-1)<1e-12
                    point=f[p]if p!='P2'else None;sd=('OVER'if point>line else'UNDER'if point<line else None)if point is not None else('OVER'if prob['over']>prob['under']else'UNDER'if prob['under']>prob['over']else None)
                    fallback=f.get('fallback')not in [None,'none','NONE','learned','NOT_APPLICABLE']
                    if arm=='B1':
                        b=preds['B0',o['game_id'],o['player_id']];assert f['mean']==b['mean']and f['lower_median']==b['lower_median']and f['law']==b['law'];checks+=3
                else:sd=None
            else:sd=cid.removeprefix('ALWAYS_')
            rows.append(dict(week=o['week'],game_id=o['game_id'],player_id=o['player_id'],line=line,actual=y,source=o['line_from'].lower(),side=sd,point=point,prob=prob,fallback=fallback,unavailable=unavailable))
        policy_rows[cid]=rows
    for sensitivity in ['PRIMARY_ALL_RETAINED_ACTUAL_SOURCE_LABELLED','DK_ONLY_SENSITIVITY']:
        for cid in ids:
            rows=policy_rows[cid];rows=rows if sensitivity.startswith('PRIMARY')else[r for r in rows if r['source']=='dk'];weekly={}
            for w in range(1,5):weekly[w]=early_summary(early_records[cid,w])
            for w in range(5,10):weekly[w]=metrics([r for r in rows if r['week']==w])
            total=sum_metrics(list(weekly.values()));assert total['eligible']==(226 if sensitivity.startswith('PRIMARY')else 225)
            allweekly[sensitivity,cid]=weekly;cumulative[sensitivity,cid]=total
            sourceblocks[sensitivity,cid]=dict(A_EARLY=sum_metrics([weekly[w]for w in range(1,5)]),NATIVE_LATE=sum_metrics([weekly[w]for w in range(5,10)]))
            native_masks[sensitivity,cid]=digest([(r['game_id'],r['player_id'],r['line'],r['source'],r['side'],r['actual'])for r in rows])
    # Published A pair disagreement counts are used only where actually supplied.
    ar=a.early_source
    A=read(ar);pair_lookup={(r['left'],r['right']):r for r in A['paired']if r['view']=='FULL_A_EARLY_BOARD'}
    pairs=[]
    requested=[(NS+'B2::'+p,NS+'B0::'+p)for p in products]+[(cid,c)for cid in ids if cid.startswith(NS)for c in ['ALWAYS_OVER','ALWAYS_UNDER']]
    for sensitivity in ['PRIMARY_ALL_RETAINED_ACTUAL_SOURCE_LABELLED','DK_ONLY_SENSITIVITY']:
        for left,right in requested:
            weekly=allweekly[sensitivity,left];other=allweekly[sensitivity,right];blocks=[dict(week=w,loss_difference_sum=(weekly[w]['losses']-other[w]['losses']),n=weekly[w]['decided'])for w in range(1,10)];assert all(weekly[w]['decided']==other[w]['decided']for w in range(1,10))
            native={}
            for cid in [left,right]:native[cid]=[r for r in policy_rows[cid]if sensitivity.startswith('PRIMARY')or r['source']=='dk']
            disagree_native=sum(a['side']!=b['side']for a,b in zip(native[left],native[right]));src=pair_lookup.get((left,right));rev=pair_lookup.get((right,left))
            if right=='ALWAYS_OVER':disagree_early=early_records[left,'ALL']['UNDER']['selected'];proof='Exact complete-board marginal selectedUndercountagainstconstantOver'
            elif right=='ALWAYS_UNDER':disagree_early=early_records[left,'ALL']['OVER']['selected'];proof='Exact complete-board marginal selectedOvercountagainstconstantUnder'
            elif src or rev:disagree_early=(src or rev)['side_disagreements'];proof='Published exact A84 paired record'
            else:disagree_early=None;proof='UNKNOWN_NOT_DERIVABLE_FROM_AGGREGATES'
            n=sum(v['n']for v in blocks);ci=interval(blocks);pairs.append(dict(sensitivity=sensitivity,left=left,right=right,n=n,candidate_wins=cumulative[sensitivity,left]['wins'],comparator_wins=cumulative[sensitivity,right]['wins'],accuracy_change=(cumulative[sensitivity,left]['wins']-cumulative[sensitivity,right]['wins'])/n,loss_difference_interval95=ci,accuracy_difference_interval95=[-ci[1],-ci[0]],week_clusters=9,replicates=500,seed=1703,rule='resetPCG64percontrast;resamplewholeweeks;sumlossdifferences/sumsampledrows',weekly_paired_sums_counts=blocks,early_disagreements=disagree_early,native_disagreements=disagree_native,total_disagreements=disagree_early+disagree_native if disagree_early is not None else None,early_disagreement_proof=proof,game_interval=None,game_interval_reason='Earlygame-leveldifferencesprivate; do notcombineoldgameintervals',selection_limit='Exposedretrospective/frozenproductroster;no multiplicity adjustment orfuture90claim'))
    summaries=[dict(sensitivity=s,candidate_id=cid,actual_weeks=list(range(1,10)),games=119,**z,source_strata=sourceblocks[s,cid],weekly=[dict(week=w,**r)for w,r in allweekly[s,cid].items()],native_grade_commitment=native_masks[s,cid])for(s,cid),z in cumulative.items()]
    primary=[x for x in summaries if x['sensitivity'].startswith('PRIMARY')and x['candidate_id'].startswith(NS)];best=max(z['accuracy']for z in primary);leaders=[z['candidate_id']for z in primary if z['accuracy']==best]
    result=dict(id='B_INDEPENDENT_FIXED_FTN_TRIO_NINE_WEEK_DIRECTION_REVIEW_v1',state='PASS_MANUAL_NATIVE_GRADES_AND_SCOPED_NINE_WEEK_AGGREGATE_COMBINATION',at_UTC=datetime.now(timezone.utc).isoformat(),scope='Only B0/B1/B2 mean/median/P2 andconstants onfrozen226panel; notall59Bproducts orA/B/Coverallchampionship',early_source_sha256=early['source_sha256'],native_source_rows=142,source_labels={'DK':141,'Sleeper_Picks_label':1},native_unique_games=71,early_owner_bound_games=48,combined_games=119,eligible=226,actual_weeks=list(range(1,10)),summary_records=summaries,paired_week_analyses=pairs,observed_leaders_within_checked_trio=leaders,leader_accuracy=best,partial_A_controls=[dict(candidate=r['candidate_id'],early_record=r['COMBINED'],full_panel_eligible=226,available=84,unavailable_later=142,actual_weeks=[1,2,3,4],status='PARTIAL_NOT_NINE_WEEK_LOSER',fallback_attribution='UNSPECIFIED_OR_BLANK_NOT_LEARNED_ONLY')for r in early['records']if r['week_view']=='ALL'and r['candidate_id'].startswith('A::')],selected_policy_nine_week_status='NOT_ESTABLISHED_FROM_AGGREGATES;EARLY_P90_TOPK_REPLAY_NOT_SUPPLIED;DO_NOT_FORCE_OR_BORROW_LATE_WEEK_SELECTIONS',probability_quality='Three-state logloss definition matched andweighted atsamequalifiedall-decidedpoints; no crosssourceBrier orAUCaggregation.',verification_limits=['A84 public rows are aggregate/private-commitment checked, not rawprivateoffer/membership inspected.','Native 142 grades,sourcefields/identities/lawCDF/ownside recomputed withoutauthorgrader.','Weekblock intervals use9exactweeklypairedsums,notaverageofsourceintervals; earlygame-levelSEnotreconstructed.','All226arecurrent-vintage/quote-timing-unverifieddiagnostics withmain-altUNCLASSIFIED, notoriginallive/singlebook/fullleaguecoverage.','119gamescoverednotfullscheduledleagueofferuniverse.','Six/9triooutputviews andaliasesare notindependent fitted families.'],B1_native_alias_assertions=checks,new_source_fetches=0,new_fits=0,new_inference=0,new_original_picks=0,canonical_scores_written=False,code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    out=BASE/'INDEPENDENT_COMBINED_FTN_NINE_WEEK_V1.json';assert not out.exists();out.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(state=result['state'],leaders=leaders,rate=best,primary=[{k:r[k]for k in ['candidate_id','wins','losses','decided','accuracy']}for r in primary],pairs=len(pairs))))

if __name__=='__main__':main()
