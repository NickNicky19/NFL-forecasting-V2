"""Restore original B native indices in memory; export no offer identities/lines."""
from __future__ import annotations
import argparse, collections, datetime, gzip, hashlib, importlib.util, json, math, pathlib, sys
from decimal import Decimal
from scipy import stats

ROOT=pathlib.Path(__file__).resolve().parents[4];OUT=pathlib.Path(__file__).resolve().parent
def read(p):
    p=pathlib.Path(p);b=p.read_bytes();return json.loads(gzip.decompress(b)if p.suffix=='.gz'else b)
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def key(r):return r['game_id'],r['player_id'],r['target']
def cdf(p,k):
    if k<0:return 0.
    if p['kind']=='gamma_poisson_count':
        return 1.if p['mean']==0 else float(stats.nbinom.cdf(k,p['shape'],p['shape']/(p['shape']+p['mean'])))
    if p['kind']=='leaf_mixture':
        empirical=sum(w for v,w in zip(p['support'],p['weights'])if v<=k)
        prior=p['prior'];value=1-prior['q']**(k+1)if prior['kind']=='geometric'else 1.if prior['kind']=='zero'else None
        if value is None:raise ValueError('Independent prior law unsupported')
        return (1-p['mixture'])*empirical+p['mixture']*value
    raise ValueError('Independent source law unsupported')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--sources',type=pathlib.Path,required=True);a=ap.parse_args()
    source_paths={int(w):pathlib.Path(p)for w,p in read(a.sources).items()};offers=[];bindings=[]
    for week in range(5,10):
        source=read(source_paths[week]);count=0
        for r in source['rows']:
            if r.get('target')not in('pass_cmp','pass_att'):continue
            if week==8 and not(r.get('panel')=='ORIGINAL_PROVIDER_T90'and r.get('strategy')=='original'and not r.get('method_key')):continue
            if r.get('season')!=2026 or int(r['week'])!=week or r.get('position')!='QB':raise ValueError('Source contract changed')
            if r['target']!='pass_cmp':continue
            offers.append(r);count+=1
        bindings.append({'source_id':f'B_RETAINED_2026_W{week}_QB_OFFERS','sha256':sha(source_paths[week]),'bytes':source_paths[week].stat().st_size,'filtered_CMP_rows':count})
    assert len(offers)==142 and len({key(r)for r in offers})==142
    canonical=sorted(range(len(offers)),key=lambda i:key(offers[i]));inverse=[None]*142
    for canonical_i,original_i in enumerate(canonical):inverse[original_i]=canonical_i
    # This is the exact old source iterator/filter/enumeration; ordinals are
    # commitment identities, not a newly chosen ranking rule.
    prediction_paths=sorted((ROOT/'reports/information-first-20261112-01/B/completion-wave-v1/predictions').glob('2026-W*.json.gz'))
    predictions={(r['method'],key(r)):r for p in prediction_paths for r in read(p)['rows']if r['method']in('B0','B2')}
    original_scores_path=ROOT/'reports/information-first-20261112-01/B/completion-scores-v1/SCORES.json';scores=read(original_scores_path)
    expected={}
    for r in scores:
        if r.get('procedure_id')not in('B-FTN-BALL-QUALITY-COMPLETION-v1:B0','B-FTN-BALL-QUALITY-COMPLETION-v1:B2'):continue
        if r.get('product_id')not in('P90','ROLLING_TOP_K_DIAGNOSTIC')or r.get('week')not in ['ALL',5,6,7,8,9]or r.get('cohort_id')!='ALL':continue
        method=r['procedure_id'].rsplit(':',1)[1]
        expected[method,r['product_id'],r['K'],r['rank_scope'],str(r['week']),r['side']]=r
    assert len(expected)==360
    checks=0;problems=[];policies=[];weekly=[]
    def check(ok,label):
        nonlocal checks
        checks+=1
        if not ok:problems.append(label)
    for method in ['B0','B2']:
        graded=[]
        for original_i,o in enumerate(offers):
            p=predictions[method,key(o)];under=cdf(p['law'],math.floor(o['line']));over=1-under
            sd='over'if over>under else'under'if under>over else None
            actual,line=Decimal(str(o['actual'])),Decimal(str(o['line']))
            state='PUSH'if actual==line else'WIN'if sd and((actual>line)==(sd=='over'))else'LOSS'if sd else'ABSTAIN'
            graded.append({'i':original_i,'o':o,'side':sd,'confidence':max(over,under),'state':state,'over':over,'under':under})
        for policy,K,pool in [('P90',None,None)]+[('ROLLING_TOP_K_DIAGNOSTIC',K,pool)for pool in ['Combined','over','under']for K in [6,10,20]]:
            chosen=[]
            for week in range(5,10):
                board=[r for r in graded if r['o']['week']==week];picked=[]
                if policy=='P90':picked=[r for r in board if r['side']and r['confidence']>=.9]
                else:
                    for kickoff in sorted({r['o']['kickoff']for r in board}):
                        batch=[r for r in board if r['o']['kickoff']==kickoff and r['side']and(pool=='Combined'or r['side']==pool)]
                        batch.sort(key=lambda r:(-r['confidence'],r['o']['game_id'],r['o']['player_id'],str(r['o']['line'])))
                        picked.extend(batch[:max(0,K-len(picked))])
                chosen+=picked
                weekly.append({'method':method,'policy':policy,'K':K,'rank_scope':pool,'week':week,'selected':len(picked),
                  'original_filtered_index_membership_sha256':digest(sorted(r['i']for r in picked)),
                  'canonical_identity_membership_sha256':digest(sorted(key(r['o'])for r in picked))})
            for window in ['ALL']+list(map(str,range(5,10))):
                selected=chosen if window=='ALL'else[r for r in chosen if r['o']['week']==int(window)]
                for side in ['over','under','Combined']:
                    rr=selected if side=='Combined'else[r for r in selected if r['side']==side]
                    old=expected[method,policy,K,pool,window,side];w=sum(r['state']=='WIN'for r in rr);l=sum(r['state']=='LOSS'for r in rr)
                    check(digest(sorted(r['i']for r in rr))==old['query_membership_sha256'],'Original ordinal selected membership')
                    check(w==old['selection_metrics']['WIN']and l==old['selection_metrics']['LOSS']and len(rr)==old['forecast_rows'],'Independent own-side grades/counts')
            policies.append({'method':method,'policy':policy,'K':K,'rank_scope':pool,'selected':len(chosen),
              'original_filtered_index_membership_sha256':digest(sorted(r['i']for r in chosen)),
              'canonical_identity_membership_sha256':digest(sorted(key(r['o'])for r in chosen)),
              'wins':sum(r['state']=='WIN'for r in chosen),'losses':sum(r['state']=='LOSS'for r in chosen)})
    result={'id':'B_OWNER_LOCAL_NATIVE142_ORDINAL_BRIDGE_v1','at_UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'state':'PASS_ORIGINAL20_NATIVE_POLICIES_REPRODUCED'if not problems else'FAIL_WITH_ORIGINALS_PRESERVED',
      'checks':checks,'problems':problems,'original_filtered_offer_count':142,'category':'pass_cmp','season':2026,'weeks':[5,6,7,8,9],
      'source_bindings':bindings,'original_iterator':{'path':'reports/player-context-matchup-01/B/independent/inventory_retained_qb_offers_v1.py','sha256':sha(ROOT/'reports/player-context-matchup-01/B/independent/inventory_retained_qb_offers_v1.py')},
      'original_policy_code':{'path':'tools/score_ftn_completion_information.py','sha256':sha(ROOT/'tools/score_ftn_completion_information.py')},
      'original_scores':{'path':str(original_scores_path.relative_to(ROOT)),'sha256':sha(original_scores_path)},
      'prediction_bindings':[{'path':str(p.relative_to(ROOT)),'sha256':sha(p)}for p in prediction_paths],
      'canonical_order':'Sort the unique admitted native142 completion rows by(game_id,player_id,target), each ascending. One row/player-game-target; line/book fields do not break ties because these identities are unique.',
      'canonical_to_original_filtered_index':canonical,'original_filtered_to_canonical_index':inverse,
      'original_identity_order_sha256':digest([key(r)for r in offers]),'canonical_identity_order_sha256':digest([key(offers[i])for i in canonical]),
      'all20_original_policy_commitments':policies,'weekly_commitments':weekly,
      'meaning':'The old grade commitments hash sorted original filtered142 indices. They are not hashes of a newly lexical re-enumeration. The old confidence rank tie is lexical game/player/line; original indices identify membership, not a hidden tie rule.',
      'A_receipt_or_private_gate_execution':'NOT_OBSERVED;A alone applies the bridge to its admitted panel and checks all20 native memberships before any early-week extension.',
      'new_M2_selector_scope':'New M2 recipes and coverage/threshold products require their own records. This output does not transfer old FTN weeks/selection qualification to M2.',
      'protected_rows_exported':0,'new_private_derivative_bytes':0,'new_quotes_or_outcomes':0,'new_source_reads':0,'new_model_fits':0,'new_early_week_scores':0,
      'verification_limit':'Reproduces original B owner-local native iterator/membership and public original policy commitments. It does not inspect A private rows or prove A intake/parity, authentic quote timing or original issuance.'}
    (OUT/'OWNER_LOCAL_NATIVE_ORDINAL_BRIDGE_V1.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'state':result['state'],'checks':checks,'problems':problems[:5],'policies':len(policies),'rows':len(offers)}))
    if problems:raise SystemExit(1)

if __name__=='__main__':main()
