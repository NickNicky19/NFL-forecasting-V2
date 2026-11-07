"""B owner-local saved-row answer to C's exact 111-RB mask request.

Reuses the current grader and retained decisions. No fit, model inference,
source collector, private-row copy, new procedure or independent C benchmark.
"""
import collections
import datetime as dt
from decimal import Decimal
import json
import resource
import sys
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools import abc_b_c_bound_replay as a

OUT=ROOT/'reports/post-wave-5w-v1/B-111-RB-common-mask-v2'
PRIVATE=Path('/workspace/evidence-private/abc-b-continuation-20261103')
MASK=Path('/workspace/scratch/postwave-C-public-masks.json.gz')
SNAPSHOT=PRIVATE/'c-snapshot'
CREf='d66f3b20493a8ddf72842e9895d0c2c916583520'


def main():
    start=time.monotonic();OUT.mkdir(exist_ok=False)
    assert a.sha(MASK)=='9268edcd0aac29efcc89bc96882f695da0e2108c38600c18d981b754e3d71324'
    mask=next(r for r in a.load(MASK) if r['mask_id']=='cd315248b591579c11060d611ef4006a29e2848a811a30f526e3d9727f990d85')
    ids=set(mask['offer_ids']);assert len(ids)==111 and mask['category']=='rush_yd'
    bindings=[('B_OWNER_LOCAL_C_MATCHED_ROWS_V2.json.gz','45cc345d19c0361e970107951e27b2b41779a6d86c5fdf5d06eedbae5ab348fb'),
              ('B_OWNER_LOCAL_C_ADDITIONAL_ROWS_V3.json.gz','fa2224d3d6cc99f6a865a45f667e4fe98412710d6b99b51b5dda7e598c12177d')]
    a.save(OUT/'FROZEN_PACKAGE.json',dict(
        id='B-C-111-RB-MASK-CLOSURE-v1',registered_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
        C_ref=CREf,protocol_id='ABC-ACTUAL-PROP-CHAMPIONSHIP-v2-C-1',
        protocol_sha256='fa19581487519a854948269bc1ce328cbbcdc734afee2464f1ff778d1ff241a1',
        mask_id=mask['mask_id'],source_public_mask_sha256=a.sha(MASK),
        choice_before_new_scores='All retained B rushing point procedures in V2/V3 on the C/A already frozen111RBmask, ALL/W2/W3; no winner-conditioned pruning.',
        actual_weeks=[2,3],role_scope='RB_ONLY_SAME_FROZEN_C_111_OPPORTUNITIES',
        P1='Retained unrounded point versus exact retained line; equality abstains; technical absence remains unavailable.',
        controls=['ALWAYS_UNDER','EARLIER_PREVALENCE_V8','P3_DIRECT'],
        evidence='Timing-unverified actual-line diagnostic; current/revised chronological reconstruction; not original issuance.',
        source_rows=[dict(safe_id=Path(n).stem,sha256=h)for n,h in bindings],
        budget=dict(new_fits=0,new_inference=0,new_private_bytes=0,max_wall_seconds=180,max_RSS_bytes=536870912,max_public_bytes=16777216,threads=1),
        release='C intake only; two scored weeks are not five-week qualification; no production change.'))
    bymethod=collections.defaultdict(dict)
    for name,digest in bindings:
        p=PRIVATE/name;assert a.sha(p)==digest
        for r in a.load(p)['rows']:
            if r['target']!='rush_yd' or r['offer_id'] not in ids:continue
            assert r['position']=='RB'
            k=r['method_key'];oid=r['offer_id']
            if oid in bymethod[k]:assert bymethod[k][oid]==r
            bymethod[k][oid]=r
    assert len(bymethod)==52 and all(set(v)==ids for v in bymethod.values())
    crows,_=a.c_rows(SNAPSHOT)
    controls={cid:[r for r in crows if r['offer_id']in ids and r['method_id']==cid] for cid in ['ALWAYS_UNDER','EARLIER_PREVALENCE_V8','P3_DIRECT']}
    assert all(len(rr)==111 for rr in controls.values())
    metadata={}
    for old in ['continuation-20261103-v2','continuation-20261103-v3']:
        for r in a.load(ROOT/'reports/abc-championship'/old/'SCORES.json'):
            if r['target']=='rush_yd':metadata.setdefault(r['procedure_id'],r)
    scores=[];pairs=[];summaries=[];maskmaps=[]
    for method,lookup in sorted(bymethod.items()):
        rows=[lookup[k] for k in sorted(ids)]
        for r in rows:
            if r['prediction'] is None:assert r['statistical_state']=='UNAVAILABLE_FORECAST'
            else:
                assert r['forecast_cutoff']==a.instant(r['decision_time'])==a.instant(r['kickoff'])
                assert r['latest_feature_available'] is None or r['latest_feature_available']<r['forecast_cutoff']
                if r['statistical_state'] in ['WIN','LOSS','PUSH']:
                    y,l,p=map(lambda v:Decimal(str(v)),(r['actual'],r['line'],r['prediction']))
                    side='over'if p>l else'under'if p<l else None
                    assert side==r['selected_side']
                    result='PUSH'if y==l else'WIN'if((y>l)==(side=='over'))else'LOSS'
                    assert result==r['statistical_state']
        m=metadata[method]
        meta=dict(product_id=m['product_id'],history_regime=m.get('history_regime'),
            information_policy=m.get('information_policy'),role_scope='RB_ONLY',population='C_FROZEN_111_RB_MASK',
            mask_id=mask['mask_id'],default_rank_eligible=False,
            shared_benchmark_status='B_OWNER_LOCAL_NEW_111_RB_SUBSET_AWAITING_C_INTAKE')
        for wk in ['ALL','2','3']:
            rr=[r for r in rows if wk=='ALL'or r['week']==int(wk)]
            scope='B_C_111_RB_MASK_CLOSURE_v1:W'+wk
            vv=a.score(rr,method,'rush_yd',wk,meta,scope)
            for v in vv:
                v.update(horizon_id=m['horizon_id'],source_vintage=m['source_vintage'])
                v['selection_metrics'].update(
                    fallback_status_unknown=sum(r.get('fallback')in[None,'NOT_RETAINED']for r in rr),
                    fallback_status_unknown_scope='ENTIRE_THIS_VIEW_ELIGIBLE_POOL')
            scores.extend(vv)
            if wk=='ALL':
                s=next(v for v in vv if v['side']=='Combined')
                summaries.append(dict(procedure_id=method,history=m.get('history_regime'),product=m['product_id'],
                    eligible=len(rr),selected=s['forecast_rows'],decided=s['n'],wins=s['selection_metrics']['WIN'],
                    losses=s['selection_metrics']['LOSS'],rate=s['selection_metrics']['hit_rate'],
                    unavailable=s['selection_metrics']['technical_unavailable'],
                    fallback=s['selection_metrics']['fallback_issued'],fallback_unknown=s['selection_metrics']['fallback_status_unknown'],
                    MAE=s['mae'],bias=s['bias'],games=s['unique_games']))
            decided=[r['offer_id']for r in rr if r['statistical_state']in['WIN','LOSS']]
            maskmaps.append(dict(procedure_id=method,week=wk,offer_ids=sorted(r['offer_id']for r in rr),decided_offer_ids=sorted(decided)))
            for cid,cr in controls.items():
                cr=[r for r in cr if wk=='ALL'or r['week']==int(wk)]
                ctl=[dict(r,statistical_state=r['status'],selected_side=r['selected_side'].lower())for r in cr]
                pairs.append(a.pair(rr,ctl,'rush_yd',method,cid,wk,scope))
    # Existing C controls are arithmetic validation, not B-produced predictions.
    cchecks=[]
    for cid,rr in controls.items():
        expected=mask['C_controls'][cid]
        actual={side:dict(wins=sum(r['status']=='WIN'for r in rr if side=='COMBINED'or r['selected_side']==side),
                          losses=sum(r['status']=='LOSS'for r in rr if side=='COMBINED'or r['selected_side']==side)) for side in ['OVER','UNDER','COMBINED']}
        for side,x in actual.items():
            assert x['wins']==(expected[side]['wins']or 0) and x['losses']==(expected[side]['losses']or 0)
        cchecks.append(dict(control=cid,independent_retained_source_count=actual,source_public_summary=expected))
    assert len(scores)==468 and len(pairs)==468
    a.save(OUT/'SCORES.json',scores);a.save(OUT/'PAIRED_CONTROLS.json',pairs)
    a.save(OUT/'PUBLIC_C_MASK_MEMBERSHIP_BINDINGS.json',maskmaps)
    a.save(OUT/'C_CONTROL_RECONCILIATION.json',cchecks)
    a.save(OUT/'CUMULATIVE_ALL_METHODS.json',summaries)
    a.save(OUT/'SIDE_TABLE.json',a.existing.wide(scores))
    a.existing.write_csv(OUT/'SIDE_TABLE.csv',a.existing.wide(scores))
    best=max(x['rate'] for x in summaries if x['rate']is not None)
    leaders=[x for x in summaries if x['rate']==best]
    public_bytes=sum(p.stat().st_size for p in OUT.iterdir()if p.is_file())
    wall=time.monotonic()-start;peak=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
    assert wall<180 and peak<536870912 and public_bytes<16777216
    a.save(OUT/'RUN_RECEIPT.json',dict(
        state='COMPLETE_OWNER_LOCAL_111_RB_SUBSET_NOT_C_ADMITTED',at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
        source_protocol_sha256=a.sha(OUT/'FROZEN_PACKAGE.json'),code_sha256=a.sha(__file__),
        exact_mask_id=mask['mask_id'],source_methods=52,score_views=len(scores),paired_views=len(pairs),
        source_NFL_player_games=111,source_games=32,actual_weeks=[2,3],
        newly_added_weeks=0,new_fits=0,new_inference=0,new_forecasts=0,new_private_bytes=0,new_NFL_observations=0,
        public_bytes=public_bytes,wall_seconds=wall,peak_RSS_bytes=peak,raw_observed_leaders=leaders,
        gate='Large-fit recovery gate unchanged; all restricted original rows remain in approved owner-local storage.',
        limits='C raw protocol offers and corrected labels reused; quote time/as-of football vintages unverified. 111RBmask is conditional subset, not all-board coverage. No new independent NFL sample or primary replacement qualification.'))
    print(json.dumps(dict(leaders=leaders,views=len(scores),pairs=len(pairs),wall=wall)))


if __name__=='__main__':main()
