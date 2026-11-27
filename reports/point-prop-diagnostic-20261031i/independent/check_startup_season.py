"""Independent historical-window audit: all identities/counts; balanced raw-loss subset."""
import argparse,collections,csv,gzip,hashlib,json,math,time,resource
from decimal import Decimal,ROUND_HALF_EVEN
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent;PUB=HERE.parent/'historical-startup/v1'
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def canon(z):return json.dumps(z,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def close(a,b):
    if a is None or b is None:assert a is b,(a,b)
    elif isinstance(a,str)or isinstance(b,str):assert a==b,(a,b)
    else:assert math.isclose(a,b,abs_tol=1e-7,rel_tol=1e-9),(a,b)
def key(r):
    proc=r['procedure_id'];proc='empirical-player-history-control-v1'if proc=='v2-qualified-partial-chart-direct-wave-v1:empirical'else proc.removesuffix(':common-feature-memory');return(r['target'],proc,r['history_regime'],'mean'if r['product_id']=='empirical_mean'else r['product_id'],r['policy_id'])
def selected(k):return ('ordered_leaf_cdf'in k[1]and k[3]in ('lower_median','event_probability'))or(k[0]=='nick-chart-ppr-v1'and k[3]=='lower_median')or('qb-rb-specialization'in k[1]and k[3]=='absolute_loss_point')
class Count:
    def __init__(self):self.issued=self.n=self.available=self.missing=self.fb=self.sfb=0;self.origins=collections.Counter();self.issuedbits=self.bits=self.games=self.players=0;self.ae=self.se=self.bias=self.log=0.;self.inf=0;self.maximum=None;self.prec=collections.Counter()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--private-root',type=Path,required=True);ap.add_argument('--season',type=int,required=True,choices=[2022,2023,2024,2025]);ap.add_argument('--receipt',type=Path);a=ap.parse_args();start=time.monotonic();year=a.season;p=read(PUB/'FROZEN_PROTOCOL.json');spec=next(s for s in p['seasons']if s['season']==year);run=read(PUB/str(year)/'RUN_RECEIPT.json');assert sha(PUB/'FROZEN_PROTOCOL.json')==run['protocol_sha256'];assert sha(PUB/'SOURCE_SNAPSHOT.py')==p['code_sha256'];assert sha(PUB/str(year)/'SCORES.json')==run['score_sha256'];roster={tuple(k)for k in spec['recipe_roster']};chosen={k for k in roster if selected(k)};assert len(roster)==457 and len(chosen)==63
    weekly={}
    for b in spec['weekly_summary_bindings']:
        file=ROOT/b['path'];assert sha(file)==b['sha256']
        for i,r in enumerate(read(file)):
            if r.get('population')!='primary'or r.get('position')!='ALL'or r.get('fallback_view')!='ALL'or type(r.get('week'))is not int:continue
            if year==2025 and'continuity-repair'not in b['path']and'qb-rb-specialization'in r['procedure_id']:continue
            k=key(r);assert(k,r['week'])not in weekly;weekly[k,r['week']]=r
    assert len(weekly)==8226 and{w for k,w in weekly}==set(range(1,19))
    accum=collections.defaultdict(Count);qmap={};outcomes={};games={};players={};scanned=used=0;raw_zero_grid_disagreements=0
    for b in spec['raw_sources']:
        file=a.private_root/b['member'];assert sha(file)==b['sha256']
        with gzip.open(file,'rt',newline='')as f:
            for r in csv.DictReader(f):
                scanned+=1
                if r['population']!='primary':continue
                if year==2025 and b['source_id']=='season'and'qb-rb-specialization'in r['procedure_id']:continue
                k=key(r)
                if k not in roster:continue
                week=int(r['week']);assert int(r['season'])==year and 1<=week<=18;assert int(r['game_id'].split('_')[0])==year and int(r['game_id'].split('_')[1])==week
                y=None if r['actual']in ('',None)else float(r['actual']);pred=None if r['prediction']in ('',None)else float(r['prediction']);assert pred is None or math.isfinite(pred);assert y is None or math.isfinite(y);fb=r['fallback'];assert fb
                q=(r['game_id'],r['player_id'],r['target'],r['population'],r['position'])
                if q not in qmap:qmap[q]=len(qmap);outcomes[q]=y
                else:assert outcomes[q]==y
                if r['game_id']not in games:games[r['game_id']]=len(games)
                if r['player_id']not in players:players[r['player_id']]=len(players)
                window='W1_W4_STARTUP'if week<=4 else'W5_W18_LATER';origin='LEARNED_ONLY'if fb=='none'else'FALLBACK_ONLY';bit=1<<qmap[q]
                for partition in ('FULL_SYSTEM',origin):
                    z=accum[k,window,partition];assert not(z.issuedbits&bit);z.issuedbits|=bit;z.issued+=1;z.available+=pred is not None;z.missing+=y is None;z.fb+=fb!='none';z.origins[fb]+=1
                    if pred is None or y is None:continue
                    z.n+=1;z.sfb+=fb!='none';z.bits|=bit;z.games|=1<<games[r['game_id']];z.players|=1<<players[r['player_id']]
                    if k not in chosen:continue
                    err=pred-y;ab=abs(err);z.ae+=ab;z.se+=err*err;z.bias+=err;z.maximum=ab if z.maximum is None else max(z.maximum,ab)
                    if k[0]=='nick-chart-ppr-v1'and k[3]=='lower_median':
                        x=Decimal(str(pred))*50;v=Decimal(str(y))*50;xi=int(x.to_integral_value(rounding=ROUND_HALF_EVEN));yi=int(v.to_integral_value(rounding=ROUND_HALF_EVEN));assert abs(x-xi)<Decimal('0.00001')and abs(v-yi)<Decimal('0.00001');exact=abs(xi-yi);raw_zero_grid_disagreements+=int((pred==y)!=(xi==yi));z.prec['exact_rate']+=xi==yi
                    else:exact=None;z.prec['exact_rate']+=pred==y
                    for t in (1,5,10):z.prec[f'abs_lt_{t}']+=exact<50*t if exact is not None else ab<t;z.prec[f'abs_le_{t}']+=exact<=50*t if exact is not None else ab<=t
                    if k[0]=='anytime_td':
                        assert 0<=pred<=1 and y in (0,1);mass=pred if y else 1-pred
                        if mass==0:z.inf+=1
                        else:z.log-=math.log(mass)
                used+=1
                if used%10000==0:assert time.monotonic()-start<300
    universe=hashlib.sha256(canon(sorted((code,q,outcomes[q])for q,code in qmap.items()))).hexdigest();scores=read(PUB/str(year)/'SCORES.json');lookup={};raw_views=full_views=0;example=[]
    for s in scores:
        k=tuple(s[n]for n in ['target','procedure_id','history_regime','product_id','policy_id']);window=s['window_id'];part=s['fallback_view'];z=accum[k,window,part];lookup[k,window,part]=s
        assert s['n']==z.n and s['forecast_rows']==z.issued and s['available_prediction_rows']==z.available and s['missing_actual_n']==z.missing and s['missing_prediction_n']==z.issued-z.available;assert s['fallback_rows']==z.fb and s['scored_fallback_rows']==z.sfb and s['fallback_source_counts']==dict(z.origins);close(s['fallback_rate'],z.fb/z.issued if z.issued else None);close(s['scored_fallback_rate'],z.sfb/z.n if z.n else None);assert s['unique_games']==z.games.bit_count()and s['unique_players']==z.players.bit_count()and s['unique_target_player_game_rows']==z.bits.bit_count()
        assert s['source_outcome_index_sha256']==universe;bits=z.bits.to_bytes((len(qmap)+7)//8,'little');assert s['membership_sha256']==hashlib.sha256(bytes.fromhex(universe)+bits).hexdigest();assert s['p90_abs']is None and s['p95_abs']is None;assert s['history_status']==('SOURCE_LIMITED_2022_ONLY_RECENT_PROXY'if year==2022 and k[2]=='H-RECENT'else'REGISTERED_SEASON_RELATIVE_HISTORY');assert 'NOT_ORIGINAL_ISSUANCE'in s['source_vintage'];assert s['evaluation_weeks']==(list(range(1,5))if window=='W1_W4_STARTUP'else list(range(5,19)))
        if part=='FULL_SYSTEM':
            rr=[weekly[k,w]for w in s['evaluation_weeks']];assert z.n==sum(r['n']for r in rr)
            for metric in ['mae','mse','bias']:close(s[metric],math.fsum(r['n']*r[metric]for r in rr if r['n'])/z.n if z.n else None)
            full_views+=1
        if k in chosen:
            for metric,total in [('mae',z.ae),('mse',z.se),('bias',z.bias)]:close(s[metric],total/z.n if z.n else None)
            close(s['max_abs'],z.maximum);close(s['rmse'],math.sqrt(z.se/z.n)if z.n else None)
            for name,v in s['precision_counts'].items():assert v['numerator']==z.prec[name]and v['denominator']==z.n;close(v['rate'],z.prec[name]/z.n if z.n else None)
            if k[0]=='anytime_td':close(s['brier'],z.se/z.n if z.n else None);assert s['infinite_log_losses']==z.inf;close(s['log_loss'],'Infinity'if z.inf else z.log/z.n if z.n else None)
            raw_views+=1
            if k[0]=='pass_yd'and k[1]=='v2-distribution-controls-reconstruction-v2:ordered_leaf_cdf'and k[2]in ('H-CURRENT','H-MULTI')and part=='FULL_SYSTEM':example.append({n:s[n]for n in ['history_regime','window_id','n','mae','bias','fallback_rows']})
    for k in roster:
        for window in ['W1_W4_STARTUP','W5_W18_LATER']:
            allrow,learn,fall=(lookup[k,window,v]for v in ['FULL_SYSTEM','LEARNED_ONLY','FALLBACK_ONLY']);aa,bb,cc=(accum[k,window,v]for v in ['FULL_SYSTEM','LEARNED_ONLY','FALLBACK_ONLY']);assert aa.issuedbits==(bb.issuedbits|cc.issuedbits)and not(bb.issuedbits&cc.issuedbits);assert aa.bits==(bb.bits|cc.bits)and not(bb.bits&cc.bits)
            for field in ['forecast_rows','available_prediction_rows','missing_actual_n','missing_prediction_n','n','fallback_rows','scored_fallback_rows']:assert allrow[field]==learn[field]+fall[field]
            for metric in ['mae','mse','bias']:close((allrow[metric]or 0)*allrow['n'],(learn[metric]or 0)*learn['n']+(fall[metric]or 0)*fall['n'])
            for name,pv in allrow['precision_counts'].items():assert pv['numerator']==learn['precision_counts'][name]['numerator']+fall['precision_counts'][name]['numerator']
    assert len(scores)==2742 and full_views==914 and raw_views==378;assert run['distinct_target_player_game_ids']==len(qmap)and run['unique_games']==len(games)==(271 if year==2022 else 272) and run['unique_players']==len(players);assert used==run['retained_primary_prediction_rows_used']and scanned==run['raw_rows_scanned'];assert raw_zero_grid_disagreements==0
    receipt=dict(state='PASS_INDEPENDENT_STARTUP_IDENTITIES_PARTITIONS_WEEKLY_REFERENCES_AND_BALANCED_RAW_SUBSET',season=year,protocol_sha256=sha(PUB/'FROZEN_PROTOCOL.json'),score_sha256=sha(PUB/str(year)/'SCORES.json'),exact_recipes=457,all_scored_views_identity_support_membership_checked=2742,fullsystem_window_views_reproduced_from_prior_weekly_metrics=914,balanced_raw_recipe_subset=63,balanced_raw_loss_precision_views_reproduced=378,subset_targets=12,all_origin_count_loss_precision_partitions_checked=True,unique_target_player_game_ids=len(qmap),unique_games=len(games),unique_players=len(players),chart_exact_float_grid_disagreements=raw_zero_grid_disagreements,passing_yard_examples=example,wall_seconds=time.monotonic()-start,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,limits=['Conditionalrawloss/precisionreproductionis63of457recipes,notall457. AllFULLlossescheckearlierweeklyaggregates.','Ownnonfallbackpooldiffersacrossarms;notcommon-learnedhistoryeffect.','2022RECENTsource-limitedproxyandqualifiedpartialcharttargetremain;nostrongerclaim.'],new_fits=0,new_inference=0,new_scores=0,new_private_bytes=0)
    file=a.receipt or HERE/f'STARTUP_{year}_INDEPENDENT_REVIEW.json'
    with file.open('x')as f:json.dump(receipt,f,indent=2);f.write('\n')
    print(json.dumps(receipt))
if __name__=='__main__':main()
