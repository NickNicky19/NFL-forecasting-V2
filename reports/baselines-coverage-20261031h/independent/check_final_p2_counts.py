"""Independent retained-vector/count verification; never invokes a grader or model."""
import argparse, collections, gzip, hashlib, json, math
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
PRIVATE=None
HERE=Path(__file__).resolve().parent
PUB=HERE.parent/'probability/w5-w7-primary-p2-v1'
def read(p): return json.loads(p.read_bytes())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def gz(p): return json.loads(gzip.decompress(p.read_bytes()))
def canon(z): return json.dumps(z,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def equal(a,b):
    if a is None or b is None: assert a is b,(a,b)
    else: assert math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-12),(a,b)

def main():
    global PRIVATE
    parser=argparse.ArgumentParser();parser.add_argument('--private-root',type=Path,required=True);PRIVATE=parser.parse_args().private_root
    protocol=read(PUB/'FROZEN_PROTOCOL.json'); run=read(PUB/'RUN_RECEIPT.json')
    assert sha(PUB/'FROZEN_PROTOCOL.json')==run['protocol_sha256']
    assert sha(PUB/'SCORES.json')==run['score_sha256']
    assert sha(PUB/'SOURCE_SNAPSHOT.py')==protocol['code_sha256']
    files={}
    for s in protocol['source_bindings']:
        p=(ROOT if s['source_id'].startswith('reports/') else PRIVATE)/s['source_id']/s['member']
        assert sha(p)==s['sha256'];files[s['week'],s['leaf'],s['member']]=p
    outer={}
    for week,directory in [(5,'baselines-coverage-20261031h-source'),(6,'completion-20261031g-source'),(7,'completion-20261031g-source-w7')]:
        ct=collections.Counter(r['target'] for r in gz(PRIVATE/directory/f'FROZEN_W{week}_METADATA.json.gz')['rows'])
        outer.update({(week,k):v for k,v in ct.items()})
    raw=collections.defaultdict(dict); weekly={}; roster_keys=set()
    for week in (5,6,7):
        full_plans=gz(files[week,True,'FROZEN_LAW_DIRECTIONS_K.json.gz'])['plans']
        leaf_recipes={tuple(v['recipe']) for v in full_plans.values()}
        for leaf in (False,True):
            planfile='FROZEN_LAW_DIRECTIONS_K.json.gz' if leaf else 'FROZEN_SELECTIONS_AND_K.json.gz'
            plans=gz(files[week,leaf,planfile])['plans']
            grades=gz(files[week,leaf,'GRADED_COMPLETE_LEAF_LAWS.json.gz' if leaf else 'GRADED_METHOD_ROWS.json.gz'])['graded']
            expected={tag:pl for tag,pl in plans.items() if leaf or (pl['rule']=='P2' and tuple(pl['recipe'][:3]) not in leaf_recipes)}
            actual={r['method_id']:r for r in protocol['weekly_roster'] if r['week']==week and r['leaf']==leaf}
            assert set(actual)==set(expected)
            for tag,pl in expected.items():
                spec=actual[tag]; key=(spec['target'],spec['procedure_id'],spec['history_regime'],spec['product_id'])
                assert tuple(pl['recipe'][:3])==(key[0],key[1].removesuffix(':known-target-time-v1'),key[2])
                roster_keys.add((week,leaf,tag))
                for r in grades[tag]:
                    idx=(week,r['source_row_index']); assert idx not in raw[key]
                    row=dict(r);row['verified_origin_fallback']=r['source']=='REUSED_ELIGIBLE_FALLBACK_LAW' if leaf else r.get('fallback') not in (None,'none')
                    raw[key][idx]=row
            source=read(files[week,leaf,'SCORES.json'])
            for i,s in enumerate(source):
                if s.get('record_kind')=='prop_selection_evaluation' and s.get('decision_rule')=='P2' and s.get('K') is None and s.get('cohort_id')=='ALL' and s.get('method_id') in expected:
                    k=(s['target'],s['procedure_id'],s['history_regime'],s['product_id'],s['side'])
                    assert (week,k) not in weekly;weekly[week,k]=(i,s,files[week,leaf,'SCORES.json'])
    scores=read(PUB/'SCORES.json');triplets=collections.defaultdict(dict); bootstrap_checks=0;empty=0;examples={}
    for s in scores:
        key=tuple(s[k]for k in ('target','procedure_id','history_regime','product_id')); allrows=raw[key]
        rows={i:r for i,r in allrows.items() if r['selected_side'] and (s['side']=='Combined' or r['selected_side']==s['side'])}
        states=collections.Counter(r['statistical_state']for r in rows.values());m=s['selection_metrics'];n=states['WIN']+states['LOSS']; full=sum(outer[w,key[0]]for w in (5,6,7));admitted=sum(bool(r['admitted'])for r in allrows.values())
        assert s['forecast_rows']==len(rows) and s['n']==n
        assert all(m['status_counts'][st]==states[st] for st in m['status_counts'])
        assert m['selection_pool_count']==full and m['admitted_forecast_opportunities']==admitted
        assert m['unavailable_forecast_opportunities']==full-admitted
        assert m['admitted_rule_abstentions']==sum(r['admitted'] and r['selected_side'] is None for r in allrows.values())
        assert m['selected_any_side_in_pool']==sum(r['selected_side']is not None for r in allrows.values())
        assert m['admitted_pool_fallback_count']==sum(r['admitted'] and r['verified_origin_fallback']for r in allrows.values())
        fallback=sum(r['verified_origin_fallback']for r in rows.values())
        assert s['fallback_rows']==m['selected_side_fallback_count']==fallback
        assert m['selected_side_scored_fallback_count']==sum(r['verified_origin_fallback'] and r['statistical_state']in ('WIN','LOSS','PUSH') for r in rows.values())
        equal(s['fallback_rate'],fallback/len(rows)if rows else None);equal(m['hit_rate'],states['WIN']/n if n else None);equal(s['selection_loss_rate'],states['LOSS']/n if n else None);equal(m['selection_coverage'],len(rows)/full)
        assert s['unique_games']==len({r['game_id']for r in rows.values()})
        assert s['unique_players']==len({r['player_id']for r in rows.values()if r['player_id']})
        assert s['unique_player_games']==len({(r['game_id'],r['player_id'])for r in rows.values()if r['player_id']})
        assert s['query_membership_sha256']==hashlib.sha256(canon(sorted(rows))).hexdigest()
        assert m['bookmaker_settlement_status_counts']=={'UNRESOLVED_CONTRACT':len(rows)}
        assert s['brier']is None and s['log_loss']is None and m['returns']['net']is None
        assert m['denominators']==dict(outer_rows=len(rows),decided=n,supported_threshold_outcomes=n+states['PUSH'],unresolved=len(rows)-n-states['PUSH'])
        source_refs=[]
        for week in (5,6,7):
            if (week,key+(s['side'],)) not in weekly:continue
            idx,w,p=weekly[week,key+(s['side'],)];source_refs.append(dict(source_artifact=p.relative_to(ROOT).as_posix(),source_artifact_sha256=sha(p),source_row_index=idx,record_id=w['record_id']))
        assert s['source_records']==source_refs
        for st in m['status_counts']:
            assert states[st]==sum(weekly[w,key+(s['side'],)][1]['selection_metrics']['status_counts'][st]for w in (5,6,7)if(w,key+(s['side'],))in weekly)
        games=collections.defaultdict(lambda:[0,0])
        for r in rows.values():
            if r['statistical_state']in ('WIN','LOSS'):
                games[r['game_id']][0]+=r['statistical_state']=='WIN';games[r['game_id']][1]+=1
                examples.setdefault(r['statistical_state'],dict(target=key[0],procedure_id=key[1],history_regime=key[2],selected_side=r['selected_side'],source_row_index=r['source_row_index'],week=r['week'],state=r['statistical_state']))
        ci=m['game_uncertainty'];assert ci['game_clusters']==len(games) and ci['week_interval']is None
        equal(ci['estimate'],states['WIN']/n if n else None)
        if len(games)>=8:
            arr=np.array([games[g]for g in sorted(games)],float);draws=np.random.Generator(np.random.PCG64(1703)).integers(len(games),size=(500,len(games)));samples=arr[draws].sum(axis=1);interval=np.quantile(samples[:,0]/samples[:,1],[.025,.975])
            for a,b in zip(ci['game_interval'],interval):equal(a,float(b))
            bootstrap_checks+=1
        else:assert ci['game_interval']is None
        if not n:assert m['hit_rate']is None and s['null_reason']=='NO_DECIDED_SELECTIONS';empty+=1
        triplets[key][s['side']]=s
    for t in triplets.values():
        assert set(t)=={'over','under','Combined'}
        for field in ('forecast_rows','n','fallback_rows'):
            assert t['Combined'][field]==t['over'][field]+t['under'][field]
        for st in t['Combined']['selection_metrics']['status_counts']:
            assert t['Combined']['selection_metrics']['status_counts'][st]==sum(t[side]['selection_metrics']['status_counts'][st]for side in ('over','under'))
    assert len(scores)==414 and len(triplets)==138 and len(roster_keys)==383
    handoff=read(HERE.parent/'H_SCIENTIFIC_HANDOFF.json');addition=read(PUB/'ROOT_ADDITION_HANDOFF.json');total=0
    for b in handoff['canonical_score_sources']+[dict(path=addition['source_artifact'],sha256=addition['source_sha256'],rows=addition['rows'])]:
        p=ROOT/b['path'];assert sha(p)==b['sha256'];assert len(read(p))==b['rows'];total+=b['rows']
    for b in handoff['source_bound_annotations']:
        p=ROOT/b['path'];assert sha(p)==b['sha256'];assert len(read(p))==b['rows']
    assert total==104238
    receipt=dict(state='PASS_INDEPENDENT_FINAL_PRIMARY_P2_RETAINED_VECTORS_COUNTS_AND_HASHES',protocol_sha256=sha(PUB/'FROZEN_PROTOCOL.json'),scores_sha256=sha(PUB/'SCORES.json'),weekly_roster_entries=len(roster_keys),exact_law_products=len(triplets),side_views=len(scores),independent_game_bootstrap_intervals=bootstrap_checks,zero_decided_views=empty,canonical_H_sources=28,canonical_H_views=total,source_annotation_arrays=4,representative_saved_state_receipts=list(examples.values()),new_fits=0,new_inference=0,new_probabilities=0,new_grades=0,limitations=['W5-W7only;42of43games,notfullseason.','Source-selectedside groups;booksettlement/pricesunestablished.','ThreeexposedweeksinsufficientforweekCI;gamebootstrapdescriptive.','Fallbackoriginexact;admittedpoolandselectedsidedenominatorsremainseparate.'])
    out=HERE/'FINAL_P2_COUNTS_INDEPENDENT_REVIEW.json'
    with out.open('x')as f:json.dump(receipt,f,indent=2);f.write('\n')
    print(json.dumps(receipt))
if __name__=='__main__':main()
