"""Read-only independent current-window audit; no fitting or inference."""
import argparse,collections,csv,gzip,hashlib,json,math,resource,sys,time
from decimal import Decimal,ROUND_HALF_EVEN
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from nfl_v2.shared_subgroups import packet_rows
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def canon(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def close(a,b):
    if a is None or b is None:assert a is b,(a,b)
    elif isinstance(a,str)or isinstance(b,str):assert a==b,(a,b)
    else:assert math.isclose(a,b,abs_tol=1e-7,rel_tol=1e-9),(a,b)
def proc(s):return 'empirical-player-history-control-v1'if s=='v2-qualified-partial-chart-direct-wave-v1:empirical'else s.removesuffix(':common-feature-memory')
def product(s):return'mean'if s=='empirical_mean'else s
def normalize(r,source):
    if int(r.get('season',2026))!=2026 or r.get('population')!='primary':return None
    w=int(r['week'])
    if not 1<=w<=7:return None
    pr='empirical-player-history-control-v1'if source=='empirical'else'hgb-direct-history-controls-v1:'+r['objective']if source=='hgb'else r['procedure_id']
    return(r['target'],proc(pr),r['history_regime'],product(r.get('product_id')or r.get('product')or r.get('objective'))),w
def selected(k):return k[1].startswith('v2-chronological')or('ordered_leaf_cdf'in k[1]and k[3]in('lower_median','event_probability'))or(k[0]=='nick-chart-ppr-v1'and k[3]=='lower_median')or('qb-rb-specialization'in k[1]and k[3]=='absolute_loss_point')
class Acc:
    def __init__(self):
        self.issued=self.n=self.available=self.missing=self.fb=self.sfb=self.issuedbits=self.bits=self.games=self.players=self.inf=0;self.origins=collections.Counter();self.ae=self.se=self.bias=self.log=0.;self.maximum=None;self.prec=collections.Counter()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--public',type=Path,required=True);ap.add_argument('--private-root',type=Path,required=True);ap.add_argument('--receipt',type=Path,required=True);ap.add_argument('--allow-known-v2-precision',action='store_true');a=ap.parse_args();start=time.monotonic();p=read(a.public/'FROZEN_PROTOCOL.json');run=read(a.public/'RUN_RECEIPT.json');scores=read(a.public/'SCORES.json');assert sha(a.public/'SCORES.json')==run['score_sha256'];assert sha(a.public/'FROZEN_PROTOCOL.json')==run['protocol_sha256'];assert sha(a.public/'SOURCE_SNAPSHOT.py')==p['code_sha256']
    roster={tuple(r['key']):r for r in p['fixed_and_policy_roster']};chosen={k for k in roster if selected(k)};assert len(roster)==656 and sum(k[1].startswith('v2-chronological')for k in roster)==36
    decisions=read(ROOT/p['selector_decisions_path']);assert sha(ROOT/p['selector_decisions_path'])==p['selector_decisions_sha256'];routes=collections.defaultdict(list);expected=[]
    for r in decisions:
        src=(r['target'],proc(r['chosen_procedure_id']),'H-MULTI',product(r['chosen_product_id']));dest=(r['target'],'v2-chronological-category-score-memory-selector-v2:'+r['policy_id'],'H-MULTI','event_probability_policy'if r['target']=='anytime_td'else'point_choice_policy');expected.append(dict(week=r['evaluation_week'],chosen=list(src),policy=list(dest),earlier_score_weeks=r['current_score_weeks_available']));routes[r['evaluation_week'],src].append(dest)
    assert p['registered_routes']==expected and len(expected)==252
    data=collections.defaultdict(Acc);qids={};outcomes={};games={};players={};scanned=used=0
    for b in p['raw_sources']:
        f=a.private_root/b['member'];assert sha(f)==b['sha256'];iterator=packet_rows(f)if b['kind']=='packet'else csv.DictReader(gzip.open(f,'rt'))
        for r in iterator:
            scanned+=1;norm=normalize(r,b['source_id'])
            if norm is None:continue
            k,w=norm
            if k not in roster:continue
            assert r['game_id'].startswith('2026_'+str(w).zfill(2)+'_');point=None if r['prediction']in(None,'')else float(r['prediction']);actual=None if r['actual']in(None,'')else float(r['actual']);fb=r['fallback'];assert fb
            q=tuple(r[x]for x in('game_id','player_id','target','population','position'))
            if q not in qids:qids[q]=len(qids);outcomes[q]=actual
            else:assert outcomes[q]==actual
            if r['game_id']not in games:games[r['game_id']]=len(games)
            if r['player_id']not in players:players[r['player_id']]=len(players)
            bit=1<<qids[q];window='W1_W4_STARTUP'if w<=4 else'W5_W7_LATER';origin='LEARNED_ONLY'if fb=='none'else'FALLBACK_ONLY'
            for dest in[k]+routes[w,k]:
                for part in('FULL_SYSTEM',origin):
                    z=data[dest,window,part];assert not(z.issuedbits&bit);z.issuedbits|=bit;z.issued+=1;z.available+=point is not None;z.missing+=actual is None;z.fb+=fb!='none';z.origins[fb]+=1
                    if point is None or actual is None:continue
                    z.n+=1;z.sfb+=fb!='none';z.bits|=bit;z.games|=1<<games[r['game_id']];z.players|=1<<players[r['player_id']]
                    if dest not in chosen:continue
                    e=point-actual;ab=abs(e);z.ae+=ab;z.se+=e*e;z.bias+=e;z.maximum=ab if z.maximum is None else max(z.maximum,ab)
                    grid=None
                    if dest[0]=='nick-chart-ppr-v1'and k[3]=='lower_median':
                        x=Decimal(str(point))*50;y=Decimal(str(actual))*50;xi=int(x.to_integral_value(rounding=ROUND_HALF_EVEN));yi=int(y.to_integral_value(rounding=ROUND_HALF_EVEN));assert abs(x-xi)<Decimal('0.00001')and abs(y-yi)<Decimal('0.00001');grid=abs(xi-yi)
                    z.prec['exact_rate']+=point==actual
                    for t in(1,5,10):z.prec[f'abs_lt_{t}']+=grid<50*t if grid is not None else ab<t;z.prec[f'abs_le_{t}']+=grid<=50*t if grid is not None else ab<=t
                    if dest[0]=='anytime_td':
                        assert 0<=point<=1 and actual in(0,1);mass=point if actual else 1-point
                        if not mass:z.inf+=1
                        else:z.log-=math.log(mass)
            used+=1
            if used%10000==0:assert time.monotonic()-start<300
    universe=hashlib.sha256(canon(sorted((i,q,outcomes[q])for q,i in qids.items()))).hexdigest();lookup={};precision_differences=[];raw_views=0;examples=[]
    for r in scores:
        k=tuple(r[x]for x in('target','procedure_id','history_regime','product_id'));w=r['window_id'];part=r['fallback_view'];lookup[k,w,part]=r;z=data[k,w,part]
        assert r['n']==z.n and r['forecast_rows']==z.issued and r['available_prediction_rows']==z.available and r['missing_actual_n']==z.missing and r['missing_prediction_n']==z.issued-z.available and r['fallback_rows']==z.fb and r['scored_fallback_rows']==z.sfb and r['fallback_source_counts']==dict(z.origins)
        close(r['fallback_rate'],z.fb/z.issued if z.issued else None);close(r['scored_fallback_rate'],z.sfb/z.n if z.n else None);assert r['unique_games']==z.games.bit_count()and r['unique_players']==z.players.bit_count()and r['unique_target_player_game_rows']==z.bits.bit_count();assert r['source_outcome_index_sha256']==universe and r['membership_sha256']==hashlib.sha256(bytes.fromhex(universe)+z.bits.to_bytes((len(qids)+7)//8,'little')).hexdigest();assert r['p90_abs']is None and r['p95_abs']is None;assert r['evaluation_weeks']==([1,2,3,4]if w=='W1_W4_STARTUP'else[5,6,7]);assert r['new_fits']==r['new_model_inference']==r['new_forecasts']==r['new_NFL_observations']==0
        if k in chosen:
            for m,total in [('mae',z.ae),('mse',z.se),('bias',z.bias)]:close(r[m],total/z.n if z.n else None)
            close(r['max_abs'],z.maximum);close(r['rmse'],math.sqrt(z.se/z.n)if z.n else None)
            for name,v in r['precision_counts'].items():
                if v['numerator']!=z.prec[name]:precision_differences.append(dict(record_id=r['record_id'],target=k[0],procedure_id=k[1],metric=name,published=v['numerator'],expected=z.prec[name]))
                assert v['denominator']==z.n;close(v['rate'],v['numerator']/z.n if z.n else None)
            if k[0]=='anytime_td':close(r['brier'],z.se/z.n if z.n else None);assert r['infinite_log_losses']==z.inf;close(r['log_loss'],'Infinity'if z.inf else z.log/z.n if z.n else None)
            raw_views+=1
    precision_reference_differences=[]
    for k,reference in roster.items():
        full=[lookup[k,w,'FULL_SYSTEM']for w in('W1_W4_STARTUP','W5_W7_LATER')];ref=reference['source_record'];n=sum(r['n']for r in full);assert n==ref['n']and sum(r['forecast_rows']for r in full)==ref['forecast_rows']
        for m in('mae','mse','bias'):
            if ref.get(m)is not None:close(sum((r[m]or 0)*r['n']for r in full),ref[m]*n)
        for name,v in ref.get('precision_counts',{}).items():
            total=sum(r['precision_counts'][name]['numerator']for r in full)
            if total!=v['numerator']:precision_reference_differences.append(dict(recipe=list(k),metric=name,previous=v['numerator'],new=total))
        for w in('W1_W4_STARTUP','W5_W7_LATER'):
            aa,bb,cc=(lookup[k,w,v]for v in('FULL_SYSTEM','LEARNED_ONLY','FALLBACK_ONLY'));za,zb,zc=(data[k,w,v]for v in('FULL_SYSTEM','LEARNED_ONLY','FALLBACK_ONLY'));assert za.issuedbits==(zb.issuedbits|zc.issuedbits)and not zb.issuedbits&zc.issuedbits;assert za.bits==(zb.bits|zc.bits)and not zb.bits&zc.bits
            for f in('forecast_rows','available_prediction_rows','missing_actual_n','missing_prediction_n','n','fallback_rows','scored_fallback_rows'):assert aa[f]==bb[f]+cc[f]
            for m in('mae','mse','bias'):close((aa[m]or 0)*aa['n'],(bb[m]or 0)*bb['n']+(cc[m]or 0)*cc['n'])
            for name,v in aa['precision_counts'].items():assert v['numerator']==bb['precision_counts'][name]['numerator']+cc['precision_counts'][name]['numerator']
            if k[0]=='pass_yd'and k[1]=='v2-distribution-controls-reconstruction-v2:ordered_leaf_cdf'and k[2]in('H-CURRENT','H-MULTI'):examples.append({n:aa[n]for n in('history_regime','window_id','n','mae','fallback_rows')})
    if precision_differences or precision_reference_differences:assert a.allow_known_v2_precision and all(z['target']=='nick-chart-ppr-v1'and z['procedure_id'].startswith('v2-chronological')for z in precision_differences)
    assert len(scores)==3936 and len(data)==3936 and scanned==run['raw_rows_scanned']and used==run['primary_fixed_prediction_rows_used']and len(games)==107 and len(qids)==13906
    out=dict(state='PASS_EXCEPT_PRESERVED_V2_CHART_POLICY_PRECISION'if precision_differences else'PASS_INDEPENDENT_CURRENT_STARTUP_COUNTS_ROUTES_MEMBERSHIP_METRICS',score_sha256=sha(a.public/'SCORES.json'),protocol_sha256=sha(a.public/'FROZEN_PROTOCOL.json'),fixed_recipe_cells=620,registered_policy_output_cells=36,original_frozen_policy_decisions_checked=252,all_identity_count_membership_views_checked=3936,fullperiod_count_loss_reference_checks=656,balanced_raw_recipe_subset=len(chosen),balanced_raw_loss_precision_views=raw_views,precision_differences=precision_differences,previous_fullperiod_precision_differences=precision_reference_differences,unique_target_player_game_ids=len(qids),unique_games=len(games),unique_players=len(players),passing_yard_examples=examples,wall_seconds=time.monotonic()-start,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,limits=['Raw losses/precision separately reproduced for balanced subset including all36 frozen policies, all chart medians and base Leaf controls; all656 FULL loss sums checked against accepted native references.','Own nonfallback pools differ by method/history. Current-score selector policy consumes H-MULTI forecasts and is not strict-current information.','W1-4 versus W5-7 only; partial chart labels and source-vintage reconstruction unchanged.'],new_fits=0,new_inference=0,new_scores=0,new_private_bytes=0)
    with a.receipt.open('x')as f:json.dump(out,f,indent=2);f.write('\n')
    print(json.dumps({k:out[k]for k in('state','score_sha256','all_identity_count_membership_views_checked','balanced_raw_recipe_subset','balanced_raw_loss_precision_views','wall_seconds')}))
if __name__=='__main__':main()
