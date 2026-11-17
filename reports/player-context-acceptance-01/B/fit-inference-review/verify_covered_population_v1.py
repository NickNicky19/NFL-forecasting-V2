"""Independent arithmetic on the covered-game scope, no fit/inference/grading."""
import argparse,collections,gzip,hashlib,json,math,time
from datetime import datetime,timezone
from pathlib import Path

def read(p):
    p=Path(p);b=p.read_bytes();return json.loads(gzip.decompress(b)if p.suffix=='.gz'else b)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def mh(rows):return hashlib.sha256(json.dumps(sorted((r['game_id'],r['player_id'],r['target'])for r in rows),separators=(',',':')).encode()).hexdigest()
def metrics(rows,product):
    assert rows and all(r['actual']is not None and r[product]is not None for r in rows)
    err=[r[product]-r['actual']for r in rows];ae=[abs(e)for e in err];n=len(rows);ordered=sorted(ae)
    def quant(p):
        at=(n-1)*p;i=math.floor(at);j=math.ceil(at);return ordered[i]+(ordered[j]-ordered[i])*(at-i)
    m=dict(n=n,mae=math.fsum(ae)/n,mse=math.fsum(e*e for e in err)/n,bias=math.fsum(err)/n,p90_abs=quant(.9),p95_abs=quant(.95),max_abs=max(ae))
    precision={'exact_rate':sum(e==0 for e in err)}
    for k in(1,5,10):precision['abs_lt_'+str(k)]=sum(e<k for e in ae);precision['abs_le_'+str(k)]=sum(e<=k for e in ae)
    return m,precision
def close(a,b):return isinstance(a,(int,float))and isinstance(b,(int,float))and math.isclose(a,b,abs_tol=1e-11,rel_tol=1e-12)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repository',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    for w in range(5,9):ap.add_argument('--week'+str(w),type=Path,required=True)
    a=ap.parse_args();root=a.repository.resolve();out=a.out;start=time.monotonic();base=root/'reports/player-context-matchup-01/B';new=root/'reports/player-context-acceptance-01/B/raw-feature-review'
    scores=read(new/'SCORES.json');projection=read(new/'TIME_GAME_OFFERED_NUMERICAL_PROJECTION_V2.json');assert len(scores)==len(projection)==8
    offers=[];source=[]
    for week in range(5,9):
        path=getattr(a,'week'+str(week));rows=read(path)['rows'];kept=[]
        for r in rows:
            if r.get('target')not in('pass_cmp','pass_att')or r.get('position')!='QB':continue
            if week==8 and not(r.get('panel')=='ORIGINAL_PROVIDER_T90'and r.get('strategy')=='original'and not r.get('method_key')):continue
            assert r['season']==2026 and int(r['week'])==week
            kept.append(r)
        assert len(kept)==56;offers+=kept;source.append(dict(week=week,source_id='B_RETAINED_QB_OFFER_BOARD_W'+str(week),source_sha256=sha(path),source_bytes=path.stat().st_size,offers=len(kept)))
    games={r['game_id']for r in offers};assert len(games)==56
    offerkeys={t:{(r['game_id'],r['player_id'])for r in offers if r['target']==t}for t in('pass_cmp','pass_att')}
    assert all(len(v)==112 for v in offerkeys.values())
    loaded=[];forecast_bindings=[]
    for wave in('qb-wave-v1','qb-charting-wave-v1'):
        for p in sorted((base/wave/'predictions').glob('2026-W*.json.gz')):
            loaded+=read(p)['rows'];forecast_bindings.append(dict(path=str(p.relative_to(root)),sha256=sha(p),bytes=p.stat().st_size))
    same=[]
    for r in scores:
        key=(r['procedure_id'],r['product_id']);target=r['target'];allq=[q for q in loaded if q['procedure_id']==key[0]];assert len(allq)==277
        assert len({(q['game_id'],q['player_id'])for q in allq})==277
        weeks=[q for q in allq if q['week']in(5,6,7,8)];covered=[q for q in weeks if q['game_id']in games];offered=[q for q in covered if(q['game_id'],q['player_id'])in offerkeys[target]]
        assert[len(allq),len(weeks),len(covered),len(offered)]==[277,131,129,112]
        mm,pc=metrics(covered,key[1]);assert r['n']==129 and r['forecast_rows']==129 and r['technical_unavailable']==0
        for k,v in mm.items():assert close(v,r[k]),(key,k,v,r[k])
        for k,v in pc.items():assert r['precision_counts'][k]['numerator']==v and r['precision_counts'][k]['denominator']==129
        assert r['query_membership_sha256']==mh(covered)
        assert r['unique_games']==len({q['game_id']for q in covered})==56
        assert r['unique_players']==len({q['player_id']for q in covered})
        assert r['fallback_rows']==sum(q.get('fallback')not in(None,'none','NONE','learned','NOT_APPLICABLE')for q in covered)
        p=next(q for q in projection if(q['procedure_id'],q['product'])==key)
        expectedstages={'ALL_W1_8':allq,'SAME_WEEKS_ALL_GAMES':weeks,'SAME_WEEKS_COVERED_GAMES':covered,'OFFERED112':offered}
        for view in p['ordered_views']:
            qq=expectedstages[view['stage']];m,_=metrics(qq,key[1]);assert view['n']==m['n']and view['games']==len({q['game_id']for q in qq})
            assert close(view['MAE'],m['mae'])and close(view['bias'],m['bias'])
        same.append(dict(procedure_id=key[0],product=key[1],stages=[dict(stage=k,n=len(v),games=len({q['game_id']for q in v}),membership_sha256=mh(v),**{kk:vv for kk,vv in metrics(v,key[1])[0].items()if kk!='n'})for k,v in expectedstages.items()],new_source_record_id=r['record_id'],new_precision_counts=pc))
    receipt=dict(state='PASS_INDEPENDENT_COVERED_GAME_NUMERICAL_AND_TIME_POPULATION_PARTITIONS',at_utc=datetime.now(timezone.utc).isoformat(),source_score_sha256=sha(new/'SCORES.json'),source_projection_sha256=sha(new/'TIME_GAME_OFFERED_NUMERICAL_PROJECTION_V2.json'),verifier_sha256=sha(__file__),source_boards=source,forecast_bindings=forecast_bindings,checked_views=same,
        new_score_views_verified=8,stage_views_verified=32,partitions=dict(all_W1_8=277,same_W5_W8=131,board_covered56games=129,offered=112,time_window_exclusions=146,missing_game_queries=2,other_QB_queries_in_covered_games=17,total_outside_offered=165),
        interpretation='277v112 changes time window, game coverage and offered-player membership. 129v112 fixes W5-8and56games, exposing descriptive participant-versus-offered composition. Outside-board165are not165abstentions or technicalfailures. No causal role/learner effect established by population differences.',
        rights='Permittedpublicforecastderivednumericalaggregates; protected offerrows/identities/lines not exported.',new_fits=0,new_inference=0,new_NFL_prop_grades=0,new_NFL_observations=0,old_scores_unchanged=True,wall_seconds=time.monotonic()-start)
    p=out/'COVERED_GAME_NUMERICAL_SCOPE_REVIEW_V1.json';assert not p.exists();p.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({k:receipt[k]for k in('state','new_score_views_verified','stage_views_verified','partitions','new_fits','new_NFL_prop_grades','wall_seconds')}))
if __name__=='__main__':main()
