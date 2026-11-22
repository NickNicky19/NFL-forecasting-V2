"""Scoped independent verification of two already-published C mean products.

Reopens retained C exclusion commitments; freezes exact C masks before opening
canonical grades. No source collection, new scorer, fit, policy or prediction.
All case ordinals and source rows stay outside the public report.
"""
from __future__ import annotations
import argparse, collections, datetime, gzip, hashlib, json, math, pathlib, time
from decimal import Decimal
from bind_shared_sim_saved_b_v1 import prior_identity_maps, team_key

def sha(b): return hashlib.sha256(b).hexdigest()
def compact(v): return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ('canonical','base','identity','private_masks','exclusions','published','output'):
        ap.add_argument('--'+name.replace('_','-'),type=pathlib.Path,required=True)
    a=ap.parse_args(); start=time.process_time(); checks=[]
    def check(ok,label):
        checks.append(label)
        if not ok: raise ValueError(label)
    cb=(a.canonical/'comparison_inputs/cases.jsonl').read_bytes()
    check(sha(cb)=='19ccf34b3037e1790ee3b2bf61d3357f33e63916779c2f36023a232f6a66ea18','canonical cases')
    cases=[json.loads(x) for x in cb.splitlines()]
    pb=a.private_masks.read_bytes(); fixed=json.loads(pb)
    eb=a.exclusions.read_bytes(); excluded=json.loads(eb)['blocked_cells']
    byhash={sha(r['case_id'].encode()):i for i,r in enumerate(cases)}
    blocked={}
    for x in excluded:
        i=byhash[x['case_id_SHA256']]; q=cases[i]['identity']
        check(q['category']==x['category'] and q['week']==x['week'],'exclusion identity')
        check(i not in blocked,'no duplicate exclusions'); blocked[i]=x['reason']
    check({str(k):v for k,v in blocked.items()}==fixed['C_identity_blocked_ordinals'],'independent exclusion mapping')
    expected={'rec':'8a0b7aeaeafa260a2d63f2e0f40185de7599710831cdca5abdcef95636f6e963','rec_yd':'2995d71a621a0b6d224ec6c8078a413f135033efe3e94514e332b29394729358'}
    masks={}; bindings=[]
    for cat in expected:
        old=set(fixed['B_fixed_masks'][cat]); keep=old-set(blocked)
        ids=sorted(cases[i]['case_id'] for i in keep)
        h=sha(json.dumps(ids,separators=(',',':')).encode())
        check(len(old)==671 and len(keep)==638 and h==expected[cat],'exact C mask '+cat)
        masks[cat]=keep; bindings.append(dict(category=cat,available=len(keep),available_case_mask_SHA256=h))
    # Only after both immutable C availability commitments pass may grades open.
    bb=a.base.read_bytes()
    check(sha(bb)=='907decacb4ce8ca1b4990ba6ec3eef43049e62b12ae4f4a526776ab4e926faee','retained source predictions')
    identity=json.loads(a.identity.read_bytes()); players=prior_identity_maps(identity)
    rows={}
    for x in json.loads(gzip.decompress(bb)):
        if x['season']==2026 and x['arm']=='M3-0':
            key=(x['week'],x['game_id'],x['player_id'],x['category'])
            r={k:x.get(k) for k in ('mean','position','team','learned','fallback')}
            check(key not in rows or rows[key]==r,'source duplicate parity'); rows[key]=r
    ob=(a.canonical/'grading_only/outcomes.v1.jsonl').read_bytes()
    check(sha(ob)=='666885cbdc2ae7551f637b3d4a6999f15c07db956861f3f0374fad9c91b3a5ad','canonical outcomes')
    outcomes={r['case_id']:r['actual'] for r in map(json.loads,ob.splitlines())}
    bench={r['case_id']:r for r in map(json.loads,(a.canonical/'comparison_inputs/benchmarks.jsonl').read_bytes().splitlines())}
    machine=json.loads(gzip.decompress(a.published.read_bytes()))
    check(sha(a.published.read_bytes())=='ed8d013b994df3953b3b0a4998d57c81f5bb38885fad874dc478c9f2f15dc969','published C aggregate')
    def side(x,l):
        d=Decimal(str(x))-Decimal(str(l))
        return 'OVER' if d>0 else 'UNDER' if d<0 else 'ABSTAIN'
    def grade(s,y,l):
        if y is None:return 'UNKNOWN'
        actual=side(y,l)
        return 'PUSH' if actual=='ABSTAIN' else 'ABSTAIN' if s=='ABSTAIN' else 'WIN' if s==actual else 'LOSS'
    results=[]
    for cat,keep in masks.items():
        method=f'C-M3-v1.1::{cat}::M3-0::base::MEAN_POINT'; sides={s:collections.Counter() for s in ('OVER','UNDER','COMBINED')}; weekly=collections.defaultdict(collections.Counter); pairs={k:collections.Counter() for k in ('W0','W1')}; pairids={k:[] for k in pairs}; native=collections.Counter()
        for i in sorted(keep):
            case=cases[i];q=case['identity']; event=identity['ESPN_game_to_canonical_game'][str(q['game_id'])];player=players[q['week']][str(q['player_id'])]
            r=rows[q['week'],event['game_id'],player,cat]
            check(r['position']==q['position'] and team_key(r['team'])==team_key(q['team']),'source row identity')
            check(type(r['mean']) in (int,float) and math.isfinite(r['mean']),'finite source mean')
            s=side(r['mean'],q['line']); status=grade(s,outcomes[case['case_id']],q['line'])
            native['native' if r['learned'] is True else 'fallback' if r['fallback'] else 'attribution_unknown']+=1
            for sk in ('COMBINED',s) if s in ('OVER','UNDER') else ('COMBINED',):
                sides[sk]['selected']+=int(s!='ABSTAIN');sides[sk][status]+=1
            weekly[q['week']][status]+=1;weekly[q['week']]['available']+=1
            for ctrl,field in [('W0','W0_literal_saved_adj'),('W1','W1_literal_provider_or_adjusted_fallback')]:
                bs=side(bench[case['case_id']][field],q['line']);bz=grade(bs,outcomes[case['case_id']],q['line'])
                if status not in ('WIN','LOSS') or bz not in ('WIN','LOSS'):continue
                v=pairs[ctrl];v['common_decided']+=1;v['primary_wins']+=int(status=='WIN');v['control_wins']+=int(bz=='WIN');v['primary_only_wins']+=int(status=='WIN' and bz=='LOSS');v['control_only_wins']+=int(status=='LOSS' and bz=='WIN');pairids[ctrl].append(case['canonical_case_key'])
        published=next(x for x in machine['scores'] if x['method']==method and x['category']==cat and x['week']=='ALL')
        for s,record in sides.items():
            for f,k in [('wins','WIN'),('losses','LOSS'),('selected','selected'),('selected_unknown','UNKNOWN')]:check((published[s][f] or 0)==record[k],f'{cat}/{s}/{f}')
        for control,v in pairs.items():
            p=next(x for x in machine['saved_control_vs_website']['paired'] if x['candidate']==method and x['control']==control and x['category']==cat and x['week']=='ALL')
            for k in ('common_decided','primary_wins','control_wins','primary_only_wins','control_only_wins'):check(v[k]==p[k],f'{cat}/{control}/{k}')
        results.append(dict(category=cat,procedure=method,own_sides={s:dict(v) for s,v in sides.items()},weekly={str(k):dict(v) for k,v in sorted(weekly.items())},attribution=dict(native),paired={k:{**dict(v),'common_decided_canonical_key_SHA256':sha(json.dumps(sorted(pairids[k]),separators=(',',':')).encode())} for k,v in pairs.items()}))
    result=dict(id='B-C-FIXED-MASK-MEAN-VERIFICATION-v1',UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),state='PASS_SCOPED',checks=len(checks),masks=bindings,results=results,source_hashes=dict(canonical=sha(cb),source_predictions=sha(bb),C_exclusions=sha(eb),private_fixed_input=sha(pb)),mask_freeze_before_grade_join=True,no_new_canonical_scores=True,new_fits=0,new_simulations=0,limits=['Two frozen C mean-point products only; not independent fit/source-clock reproduction','No law/median/CDF/private full selector parity asserted','Original 671-versus638 finding preserved and resolved using actual C exclusion evidence','Different-policy mask reconciliation does not establish a C defect or change historical scores'],CPU_seconds=time.process_time()-start)
    a.output.write_bytes(compact(result)+b'\n');print(json.dumps({'state':result['state'],'checks':len(checks),'CPU':result['CPU_seconds'],'results':results}))
if __name__=='__main__':main()
