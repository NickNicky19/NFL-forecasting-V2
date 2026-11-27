"""Reconstruct owner-local audit views directly from retained chunks and offers.

No parent scorer imports or invocation; no model inference.
"""
import argparse,collections,csv,gzip,hashlib,json,math
from datetime import datetime,timezone
from decimal import Decimal
from pathlib import Path


def read(path):return json.loads(gzip.decompress(path.read_bytes()) if path.suffix=='.gz' else path.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def stamp(v):return datetime.fromisoformat(v).timestamp()
def status(y,line,side):return 'PUSH' if Decimal(str(y))==Decimal(str(line)) else 'WIN' if ((Decimal(str(y))>Decimal(str(line)))==(side=='over')) else 'LOSS'


def run(croot,chunks,scored,private_file,out):
    versions={}
    for dataset in read(croot/'reports/abc-championship/C_INPUT_BINDINGS.json')['datasets']:
        p=croot/dataset['path'];assert sha(p)==dataset['SHA256']
        for r in read(p)['rows']:versions[r['record_id']]=r
    first={};fields=('category','game_id','player_id','method_id','method_version','selector_id','policy_id','venue','product','line_tier','evidence_tier')
    for r in versions.values():
        key=tuple(r[k] for k in fields);clock=(stamp(r['decision_UTC']),r['scoring_snapshot_id'])
        if key not in first or clock<first[key][0]:first[key]=(clock,r)
    c=[r for _,r in first.values() if r['venue']=='pinnacle' and r['season']==2026 and r['week']<=8]
    offers={r['offer_id']:r for r in c if r['method_id']=='P2_LAW'}
    lookups=collections.defaultdict(dict)
    def add(r):
        if r['target'] not in ('pass_yd','rush_yd','rec','rec_yd') or int(r['season'])!=2026 or int(r['week']) not in (2,3) or r['population']!='primary':return
        pid='B::'+r['procedure_id']+'::'+r['policy_id']+'::'+r['product_id'];key=(pid,r['target']);identity=(r['game_id'],r['player_id'])
        val=dict(r,point=r['prediction'],used_fallback=r['fallback'])
        if identity in lookups[key]:assert lookups[key][identity]==val
        lookups[key][identity]=val
    for folder in ('distribution-wave-v2','ordered-information-ablation-v1','hgb-history-v1','count-ablation-wave-v1'):
        for p in sorted((chunks/folder/'prediction-chunks').glob('W0[23]-*.json.gz')):
            data=read(p)['rows']
            if not data or data[0]['target'] not in ('pass_yd','rush_yd','rec','rec_yd'):continue
            if folder=='distribution-wave-v2' and data[0].get('family')!='regularized_glm_law':continue
            for r in data:
                r=dict(r)
                if folder=='hgb-history-v1':
                    r['procedure_id']=r['run_id']+':'+r['objective'];r['policy_id']=r['history_regime']+'-COMMON';r['product_id']=r['objective']
                add(r)
    with gzip.open(chunks/'empirical-history-diagnostic-v1/predictions.csv.gz','rt') as f:
        for r in csv.DictReader(f):
            if r['season']!='2026' or r['week'] not in ('2','3') or r['target'] not in ('pass_yd','rush_yd','rec','rec_yd') or r['population']!='primary':continue
            r=dict(r,season=2026,week=int(r['week']),procedure_id='empirical-player-history-control-v1',policy_id=r['history_regime']+'-EMPIRICAL',product_id=r['product'],prediction=float(r['prediction']) if r['prediction'] else None,actual=float(r['actual']) if r['actual'] else None,cutoff=float(r['cutoff_epoch_utc']),latest_feature_available=float(r['latest_training_available_epoch_utc']) if r['latest_training_available_epoch_utc'] else None)
            add(r)
    generated={};rows_by_method={};cby=collections.defaultdict(dict)
    for r in c:cby[(r['category'],r['method_id'])][r['offer_id']]=r
    for (pid,target),lookup in lookups.items():
        rr=[]
        for oid,q in offers.items():
            if q['category']!=target:continue
            b=lookup.get((q['game_id'],q['player_id']));point=None if b is None else b['point']
            if b:
                assert b['cutoff']==stamp(q['decision_UTC'])==stamp(q['kickoff_UTC'])
                assert b['position']==q['position']
                if b['actual'] is not None and q['actual'] is not None:assert Decimal(str(b['actual']))==Decimal(str(q['actual']))
            if point is None:side=None;state='UNAVAILABLE_FORECAST'
            elif Decimal(str(point))==Decimal(str(q['line'])):side=None;state='ABSTAIN'
            else:
                side='over' if Decimal(str(point))>Decimal(str(q['line'])) else 'under'
                state='UNKNOWN_PARTICIPATION' if q['appearance']!='PLAYED' else 'MISSING_ACTUAL' if q['actual'] is None else status(q['actual'],q['line'],side)
            rr.append(dict(oid=oid,game=q['game_id'],player=q['player_id'],week=q['week'],point=point,actual=q['actual'],side=side,status=state,fallback=b['used_fallback'] if b else None,position=q['position']))
        rows_by_method[(pid,target)]=rr
        for week in ('ALL','2','3'):
            rweek=[r for r in rr if week=='ALL' or r['week']==int(week)]
            for side in ('over','under','Combined'):
                sub=[r for r in rweek if r['side'] is not None and (side=='Combined' or side==r['side'])]
                count=collections.Counter(r['status'] for r in sub);num=[r for r in sub if r['point'] is not None and r['actual'] is not None and r['status'] in ('WIN','LOSS','PUSH')]
                generated[(pid,target,week,side)]=dict(selected=len(sub),wins=count['WIN'],losses=count['LOSS'],decided=count['WIN']+count['LOSS'],eligible=len(rweek),status_counts=dict(count),technical_unavailable=sum(r['status']=='UNAVAILABLE_FORECAST' for r in rweek),abstentions=sum(r['status']=='ABSTAIN' for r in rweek),fallback_issued=sum(r['fallback'] not in ('none',False,None,'NOT_RETAINED') for r in rweek),mae=sum(abs(r['point']-r['actual']) for r in num)/len(num) if num else None,bias=sum(r['point']-r['actual'] for r in num)/len(num) if num else None,numerical_n=len(num))
    scores=read(scored/'SCORES.json');assert len(scores)==len(generated)==1044
    for s in scores:
        g=generated[(s['procedure_id'],s['target'],str(s['week']),s['side'])];m=s['selection_metrics']
        assert s['forecast_rows']==g['selected'] and s['n']==g['decided']
        assert m['WIN']==g['wins'] and m['LOSS']==g['losses']
        assert m['selection_pool_count']==g['eligible']
        assert m['technical_unavailable']==g['technical_unavailable'] and m['admitted_rule_abstentions']==g['abstentions'] and m['fallback_issued']==g['fallback_issued']
        for key in ('mae','bias'):
            assert (g[key] is None and s[key] is None) or abs(g[key]-s[key])<1e-10
        assert s['numerical_n']==g['numerical_n']
        for state,n in m['status_counts'].items():assert n==g['status_counts'].get(state,0)
    # Side reconciliation and exact weekly->cumulative consistency.
    for pid,target in rows_by_method:
        for week in ('ALL','2','3'):
            a,b,total=(generated[(pid,target,week,k)] for k in ('over','under','Combined'))
            for key in ('selected','wins','losses','decided'):assert total[key]==a[key]+b[key]
        for side in ('over','under','Combined'):
            total,a,b=(generated[(pid,target,week,side)] for week in ('ALL','2','3'))
            for key in ('selected','wins','losses','decided','eligible'):assert total[key]==a[key]+b[key]
    # Pairwise counts and cluster-normal sensitivity independently checked.
    paired=read(scored/'PAIRED_CONTROLS.json')
    for p in paired:
        aa={r['oid']:r for r in rows_by_method[(p['procedure_id'],p['target'])] if p['week_view']=='ALL' or r['week']==int(p['week_view'])}
        bb=cby[(p['target'],p['control_id'])];rows=[(a,bb[oid]) for oid,a in aa.items() if a['status'] in ('WIN','LOSS') and bb[oid]['status'] in ('WIN','LOSS')]
        assert len(rows)==p['common_decided']
        aw=sum(a['status']=='WIN' for a,b in rows);bw=sum(b['status']=='WIN' for a,b in rows)
        assert aw==p['candidate_wins'] and bw==p['control_wins'] and aw-bw==p['win_difference']
        assert sum(a['side'].upper()!=b['selected_side'] for a,b in rows)==p['disagreements']
        # Parent stores loss-rate delta, the negative of candidate win-rate change.
        diffs=collections.defaultdict(list)
        for a,b in rows:diffs[a['game']].append(int(a['status']=='LOSS')-int(b['status']=='LOSS'))
        n=len(rows);delta=sum(map(sum,diffs.values()))/n if n else None
        assert delta==p['uncertainty']['delta']
        if len(diffs)>=8:
            se=math.sqrt(len(diffs)/(len(diffs)-1)*sum((sum(v)-len(v)*delta)**2 for v in diffs.values()))/n
            assert abs(se-p['uncertainty']['game_cluster_sensitivity_se'])<1e-13
    # Check derivative row bytes then reconstruct every retained row's selection/state independently.
    manifest=read(scored/'PRIVATE_DERIVATIVE_MANIFEST.json');assert sha(private_file)==manifest['sha256']
    stored=read(private_file)['rows'];assert len(stored)==sum(len(v) for v in rows_by_method.values())==28552
    index={(pid,target,r['oid']):r for (pid,target),rr in rows_by_method.items() for r in rr}
    assert len(index)==len(stored)
    for r in stored:
        g=index[(r['method_key'],r['target'],r['offer_id'])]
        assert r['selected_side']==g['side'] and r['statistical_state']==g['status'] and r['prediction']==g['point'] and r['actual']==g['actual'] and r['fallback']==g['fallback']
    # Own-pool leaders include ties, and separate side leaders are independently reproduced.
    leaders=[]
    for target in ('pass_yd','rush_yd','rec','rec_yd'):
        full=[(pid,g) for (pid,t,w,side),g in generated.items() if t==target and w=='ALL' and side=='Combined' and g['decided']]
        best=max(g['wins']/g['decided'] for pid,g in full)
        side_maxima={}
        for side in ('over','under'):
            ss=[(pid,g) for (pid,t,w,s),g in generated.items() if t==target and w=='ALL' and s==side and g['decided']]
            m=max(g['wins']/g['decided'] for pid,g in ss)
            side_maxima[side]=[dict(procedure_id=pid) for pid,g in ss if g['wins']/g['decided']==m]
        leaders.append(dict(target=target,leaders=[pid for pid,g in full if g['wins']/g['decided']==best],rate=best,side_maxima=side_maxima))
    leader_details=[]
    for entry in leaders:
        target=entry['target'];rows=[(pid,g) for (pid,t,w,side),g in generated.items() if t==target and w=='ALL' and side=='Combined']
        best=max(g['wins']/g['decided'] for pid,g in rows if g['decided'])
        ids=sorted(pid for pid,g in rows if g['decided'] and g['wins']/g['decided']==best)
        assert ids==sorted(entry['leaders']) and best==entry['rate']
        for side in ('over','under'):
            sub=[(pid,g) for (pid,t,w,s),g in generated.items() if t==target and w=='ALL' and s==side and g['decided']]
            maximum=max(g['wins']/g['decided'] for pid,g in sub)
            assert sorted(pid for pid,g in sub if g['wins']/g['decided']==maximum)==sorted(x['procedure_id'] for x in entry['side_maxima'][side])
        pid=ids[0];g=generated[(pid,target,'ALL','Combined')]
        relevant=[p for p in paired if p['procedure_id']==pid and p['target']==target and p['week_view']=='ALL']
        strong=max(relevant,key=lambda p:p['control_wins']/p['common_decided'] if p['common_decided'] else -1)
        weeks={w:generated[(pid,target,w,'Combined')]['wins']/generated[(pid,target,w,'Combined')]['decided'] for w in ('2','3')}
        leader_details.append(dict(target=target,representative_tied_leader=pid,own_combined=dict(wins=g['wins'],decided=g['decided'],rate=best),same_procedure_weekly_rates=weeks,strongest_matched_C_control=strong['control_id'],control_wins=strong['control_wins'],candidate_wins=strong['candidate_wins'],common_decided=strong['common_decided'],candidate_win_change=strong['win_difference']))
    learned=read(scored/'LEARNED_FALLBACK_SCOPE.json')
    for view in learned:
        rr=rows_by_method[(view['procedure_id'],view['target'])]
        if view['scope']=='LEARNED_ONLY':sub=[r for r in rr if r['fallback']=='none']
        elif view['scope']=='FALLBACK_ONLY':sub=[r for r in rr if r['fallback'] not in ('none',None)]
        else:sub=[r for r in rr if r['status']=='UNAVAILABLE_FORECAST']
        assert len(sub)==view['issued'] and sum(r['status'] in ('WIN','LOSS') for r in sub)==view['decided'] and sum(r['status']=='WIN' for r in sub)==view['wins']
    result=dict(state='PASS_ARITHMETIC_AND_SCOPE_WITH_EXPLICIT_QUALIFICATIONS',at_utc=datetime.now(timezone.utc).isoformat(),source='Direct independent reconstruction from retained chunks and C original rows; parent scorer not imported or invoked.',protocol_sha256=sha(scored/'FROZEN_PACKAGE.json'),scores_sha256=sha(scored/'SCORES.json'),private_sha256=sha(private_file),category_method_product_cells=len(rows_by_method),score_views_verified=len(scores),side_triplets_verified=len(scores)//3,paired_control_views_verified=len(paired),private_rows_verified=len(stored),learned_fallback_views_verified=len(learned),leaders=leader_details,qualifications=['This extension has no D1/D2 defense windows; source procedure contracts remain distinct.','B registered primary rushing supports QB/RB; three C WR rushing offers are technical population unavailability here despite retained B extended forecasts.','All C source clocks remain timing-unverified diagnostics, not authenticated original pregame issuance.','Two exposed weeks cannot establish seasonal persistence or a release-ready selection policy.','No full training re-inference or source-vintage authentication; latest-feature field and row cutoffs checked separately.'])
    out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('croot',type=Path);p.add_argument('chunks',type=Path);p.add_argument('scored',type=Path);p.add_argument('private_file',type=Path);p.add_argument('out',type=Path);a=p.parse_args();run(a.croot,a.chunks,a.scored,a.private_file,a.out)
