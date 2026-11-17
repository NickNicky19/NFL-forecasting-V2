#!/usr/bin/env python3
"""Independent source-prefix, membership, overlap and score replay; no fits.

Does not import the cohort builder, its source loader or production scorer.
Only retained W1–7 observations and frozen query metadata are read.
"""
import argparse,collections,csv,gzip,hashlib,json,math,re,sys,time
from datetime import datetime,timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[2]
CORE=('H-CURRENT','H-RECENT','H-MULTI')
COUNTS={'pass_td','pass_cmp','pass_att','pass_int','rush_att','rec'}
PHYSICAL_COUNTS=('attempts','completions','carries','targets','receptions','sacks_suffered','passing_tds','rushing_tds','receiving_tds','passing_2pt_conversions','rushing_2pt_conversions','receiving_2pt_conversions','punt_returns','kickoff_returns','def_tackles_solo','def_tackles_with_assist','def_tackle_assists','def_sacks','def_interceptions','fumble_recovery_own','fumble_recovery_opp','fg_att','pt_att')
PHYSICAL_YARDS=('passing_yards','rushing_yards','receiving_yards','sack_yards_lost','punt_return_yards','kickoff_return_yards','def_interception_yards','fumble_recovery_yards_own','fumble_recovery_yards_opp','misc_yards')


def canon(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def digest(body):return hashlib.sha256(body).hexdigest()
def sha(path):return digest(Path(path).read_bytes())
def jread(path):return json.loads(Path(path).read_bytes())
def aware(value):
    t=datetime.fromisoformat(value.replace('Z','+00:00'))
    if t.tzinfo is None:raise ValueError('naive clock')
    return t.timestamp()
def numeric(value):
    if value in(None,''):return None
    x=float(value)
    if not math.isfinite(x):return None
    return x
def valid_count(value):return value is not None and value>=0 and value==int(value)
def player(q):return q['player_id']if q.get('player_id')else'UNQUALIFIED_QUERY:'+q['query_id']
def identity(q):return(q['game_id'],player(q),q['target'],q['population'])
def same(a,b):return a==b or(isinstance(a,(int,float))and isinstance(b,(int,float))and math.isclose(a,b,rel_tol=1e-11,abs_tol=1e-11))


def independent_source(cache,protocol):
    for source in protocol['source_ids']:
        if sha(cache/source['name'])!=source['sha256']:raise ValueError('pinned source mismatch')
    games={}
    with(cache/'games.csv').open()as f:
        for r in csv.DictReader(f):
            if r['game_type']!='REG'or int(r['season'])not in range(2022,2027):continue
            if int(r['season'])==2026 and int(r['week'])>8:continue
            k=datetime.fromisoformat(r['gameday']+'T'+r['gametime']).replace(tzinfo=ZoneInfo('America/New_York')).timestamp()
            games[r['game_id']]=(int(r['season']),int(r['week']),k,r['home_team'],r['away_team'])
    histories=collections.defaultdict(list);seen=set();source_n=qualified=played_n=unknown=0
    for year in range(2022,2027):
        with(cache/f'stats_player_week_{year}.csv').open()as f:
            for r in csv.DictReader(f):
                source_n+=1
                if r['season_type']!='REG'or int(r['season'])!=year or(year==2026 and int(r['week'])>7):continue
                if r['position']not in{'QB','RB','WR','TE'}or not re.fullmatch(r'00-\d{7}',r['player_id']):continue
                game=games[r['game_id']]
                if game[:2]!=(year,int(r['week']))or(r['team'],r['opponent_team'])not in((game[3],game[4]),(game[4],game[3])):raise ValueError('source game/team mismatch')
                key=r['game_id'],r['player_id']
                if key in seen:raise ValueError('duplicate source identity')
                seen.add(key)
                counts=[numeric(r[k])for k in PHYSICAL_COUNTS];yards=[numeric(r[k])for k in PHYSICAL_YARDS]
                played=any(valid_count(v)and v>0 for v in counts)or any(v is not None and v!=0 for v in yards)
                values=tuple(numeric(r[k])if played else None for k in('attempts','carries','targets'))
                if any(v is not None and not valid_count(v)for v in values):raise ValueError('invalid opportunity support')
                histories[r['player_id']].append((game[2]+7*86400,r['game_id'],values));qualified+=1;played_n+=played;unknown+=not played
    for values in histories.values():values.sort(key=lambda r:(r[0],r[1]))
    return histories,games,dict(source_rows=source_n,qualified_slots=qualified,played_slots=played_n,unknown_participation_slots=unknown)


def opportunity(target,values):
    if target.startswith('pass_'):return values[0]
    if target in{'rush_att','rush_yd'}:return values[1]
    if target in{'rec','rec_yd'}:return values[2]
    if target in{'rush_rec_yd','anytime_td'}:return values[1]+values[2]if values[1]is not None and values[2]is not None else None
    raise ValueError('unknown target')


def reconstruct(queries,histories,origins):
    groups=collections.defaultdict(list)
    for q in queries:groups[int(q['week']),q['target'],q['population']].append(q)
    result={};ties=unranked=missing_slots=exact_boundary=0
    for(week,target,pop),qs in groups.items():
        cutoff=origins[week];profiles={}
        for q in qs:
            pid=player(q)
            if pid in profiles:raise ValueError('duplicate player/week/target/pop')
            available=[r for r in histories.get(pid,[])if r[0]<cutoff]
            selected=available[-3:];values=[opportunity(target,r[2])for r in selected];ys=[v for v in values if v is not None]
            exact_boundary+=sum(r[0]==cutoff for r in histories.get(pid,[]))
            missing_slots+=sum(v is None for v in values)
            profiles[pid]=dict(mean=math.fsum(ys)/len(ys)if ys else None,supported_slots=len(ys),history_slots=len(selected),latest_available=max((r[0]for r in selected),default=None))
        ranked=sorted((pid for pid in profiles if profiles[pid]['mean']is not None),key=lambda pid:(-profiles[pid]['mean'],pid));rank={pid:i+1 for i,pid in enumerate(ranked)}
        values=[profiles[pid]['mean']for pid in ranked];ties+=sum(a==b for a,b in zip(values,values[1:]))
        for q in qs:
            pid=player(q);profile=profiles[pid];n=rank.get(pid);v=profile['mean'];views=['all']
            if n is None:views.append('unranked');unranked+=1
            else:
                views.extend('top'+str(k)for k in(10,15,20)if n<=k)
                views.append('rank1_10'if n<=10 else'rank11_15'if n<=15 else'rank16_20'if n<=20 else'rank21plus')
            lo,hi=(20,35)if target.startswith('pass_')else(3,7)if target in{'rec','rec_yd'}else(5,12)
            band='unknown'if v is None else'zero'if v==0 else'low'if v<=lo else'middle'if v<=hi else'high'
            views.append('workload_'+band)
            result[identity(q)]=dict(rank=n,cohorts=views,ranking_cutoff=cutoff,**profile)
    return result,dict(query_profiles=len(result),tied_adjacent_rank_values=ties,unranked=unranked,missing_selected_slots=missing_slots,exact_availability_boundaries_excluded=exact_boundary)


def compare_memberships(reconstructed,path):
    saved=json.loads(gzip.decompress(path.read_bytes()));bykey={tuple(r['key']):{k:v for k,v in r.items()if k!='key'}for r in saved}
    if set(bykey)!=set(reconstructed):raise ValueError('membership identity census mismatch')
    mismatches=[]
    for key,want in reconstructed.items():
        got=bykey[key]
        if set(got)!=set(want)or any(not same(got[k],v)for k,v in want.items()):mismatches.append(digest(canon(key)))
    return mismatches


Record=collections.namedtuple('Record','proc product target pop arm key prediction actual fallback week family')


def retained_records(registration,paths,member):
    result=[];seen=set();actuals={};actual_conflicts=0
    aliases={k:k for k in member}
    def normalize(row,kind):
        nonlocal actual_conflicts
        if str(row.get('season',2026))!='2026'or int(row['week'])>7:return
        key=identity(row)
        if key not in member:raise ValueError('record outside frozen membership')
        proc=row.get('procedure_id')or('empirical-player-history-control-v1'if kind=='empirical'else'hgb-direct-history-controls-v1:'+row['objective'])
        product=row.get('product_id')or row.get('product')or row['objective'];arm=row['history_regime']
        prediction=numeric(row.get('prediction'));actual=numeric(row.get('actual'));fallback=row.get('fallback')
        if fallback is None:raise ValueError('missing explicit fallback')
        if actual is not None and(row['target']in COUNTS and not valid_count(actual)or row['target']=='anytime_td'and actual not in(0,1)):raise ValueError('invalid label support')
        if row['target']=='anytime_td'and prediction is not None and not 0<=prediction<=1:raise ValueError('invalid probability')
        if key in actuals and actuals[key]!=actual:actual_conflicts+=1
        actuals[key]=actual
        rid=proc,product,arm,key
        if rid in seen:raise ValueError('duplicate forecast view')
        seen.add(rid)
        result.append(Record(sys.intern(proc),sys.intern(product),sys.intern(row['target']),sys.intern(row['population']),sys.intern(arm),aliases[key],prediction,actual,sys.intern(fallback),int(row['week']),sys.intern(row.get('family')or kind)))
    for spec,path in zip(registration['inputs'],paths):
        kind=spec['adapter'];files=sorted(path.glob('W0[1-7]-*.json.gz'))if kind=='hgb'else[path]
        if[(f.name,sha(f))for f in files]!=[(r['artifact_id'],r['sha256'])for r in spec['files']]:raise ValueError('registered prediction byte mismatch')
        for file in files:
            if kind=='hgb':
                packet=json.loads(gzip.decompress(file.read_bytes()))
                if not isinstance(packet,dict)or not isinstance(packet.get('rows'),list):raise ValueError('original wrapper contract')
                for row in packet['rows']:normalize(row,kind)
            else:
                with gzip.open(file,'rt',newline='')as f:
                    for row in csv.DictReader(f):normalize(row,kind)
    if actual_conflicts:raise ValueError('label disagreement across competitors')
    return result


def regroup(records,member):
    learned={};procsets=collections.defaultdict(dict)
    for r in records:
        key=r.proc,r.product,r.target,r.pop
        values=learned.setdefault((*key,r.arm),set());procsets[key][r.arm]=values
        if r.fallback=='none'and r.prediction is not None and r.actual is not None:values.add(r.key)
    three={key:set.intersection(*(arms.get(a,set())for a in CORE))for key,arms in procsets.items()}
    allsets=collections.defaultdict(list)
    for(proc,product,target,pop,arm),values in learned.items():allsets[target,pop].append(values)
    shared={key:set.intersection(*sets)for key,sets in allsets.items()}
    groups=collections.defaultdict(list)
    for r in records:
        views=['full_system']
        if r.fallback=='none':views.append('own_learned_only')
        if r.key in three[r.proc,r.product,r.target,r.pop]:views.append('three_history_learned_overlap')
        if r.key in shared[r.target,r.pop]:views.append('all_competitor_learned_overlap')
        for cohort in member[r.key]['cohorts']:
            for view in views:groups[r.proc,r.product,r.target,r.pop,r.arm,cohort,view].append(r)
    return groups,shared


def metrics(rows,target):
    scored=[r for r in rows if r.prediction is not None and r.actual is not None];e=[r.prediction-r.actual for r in scored];a=sorted(map(abs,e));n=len(e)
    result=dict(n=n,unique_games=len({r.key[0]for r in scored}),forecast_rows=len(rows),fallback_rows=sum(r.fallback!='none'for r in rows),scored_fallback_rows=sum(r.fallback!='none'for r in scored),missing_actual_n=sum(r.prediction is not None and r.actual is None for r in rows),fallback_n=sum(r.prediction is not None and r.fallback!='none'for r in rows),constant_zero_n=sum(r.prediction is not None and r.fallback=='constant_zero'for r in rows))
    issued=sum(r.prediction is not None for r in rows);result['fallback_rate']=result['fallback_n']/issued if issued else None
    if not n:return dict(result,mae=None,mse=None,rmse=None,bias=None),scored
    mse=math.fsum(x*x for x in e)/n
    def q(p):
        t=(n-1)*p;i,j=math.floor(t),math.ceil(t);return a[i]+(a[j]-a[i])*(t-i)
    result.update(mae=math.fsum(a)/n,mse=mse,rmse=math.sqrt(mse),bias=math.fsum(e)/n,p90_abs=q(.9),p95_abs=q(.95),max_abs=max(a),exact_rate=sum(x==0 for x in e)/n)
    for k in(1,5,10):result['abs_lt_'+str(k)]=sum(x<k for x in a)/n;result['abs_le_'+str(k)]=sum(x<=k for x in a)/n
    if target=='anytime_td':
        prevalence=math.fsum(r.actual for r in scored)/n;mass=[r.prediction if r.actual else 1-r.prediction for r in scored]
        inf=sum(x<=0 for x in mass)
        result.update(brier=mse,prevalence=prevalence,prevalence_reference_brier=prevalence*(1-prevalence),log_loss='Infinity'if inf else math.fsum(-math.log(x)for x in mass)/n,infinite_log_losses=inf)
    return result,scored


def check(args):
    started=time.monotonic();pub=args.public_root;receipt=jread(pub/'RUN_RECEIPT.json');reg=jread(pub/'EXECUTION_REGISTRATION.json')
    if sha(pub/'SCORES.json')!=receipt['score_sha256']:raise ValueError('frozen score byte mismatch')
    if sha(args.old_queries)!=reg['old_query_document_sha256']:raise ValueError('original fixed query bytes mismatch')
    if sha(args.private_root/'memberships.json.gz')!=receipt['membership_sha256']:raise ValueError('private membership byte mismatch')
    histories,games,source_counts=independent_source(args.source_root,jread(args.old_protocol))
    qs=jread(args.old_queries)['historical'];origins={w:min(g[2]for g in games.values()if g[:2]==(2026,w))-5400 for w in range(1,8)}
    member,member_summary=reconstruct(qs,histories,origins);membership_mismatch=compare_memberships(member,args.private_root/'memberships.json.gz')
    future_meta=jread(pub/'FUTURE_EXANTE_COHORT_COVERAGE.json')
    if sha(args.future_queries)!=future_meta['query_document_sha256']or sha(args.private_root/'future-memberships.json.gz')!=future_meta['membership_sha256']:raise ValueError('future frozen bytes mismatch')
    future=[dict(q,week=8,population='frozen_exante_feed')for q in jread(args.future_queries)['week8']]
    future_member,future_summary=reconstruct(future,histories,{8:aware(future_meta['feature_cutoff_utc'])});future_mismatch=compare_memberships(future_member,args.private_root/'future-memberships.json.gz')
    records=retained_records(reg,[args.empirical,args.hgb_chunks,args.distributions,args.counts],member)
    if len(records)!=receipt['retained_prediction_views']:raise ValueError('prediction census mismatch')
    groups,shared=regroup(records,member);scores=jread(pub/'SCORES.json');mismatches=[];checked=0;date_mismatches=0;cluster_mismatches=0;cohort_masks={};max_diff=0.
    for s in scores:
        key=tuple(s[k]for k in('procedure_id','product_id','target','population','history_regime','cohort_id','fallback_view'))
        if key not in groups:raise ValueError('score group not independently reconstructed')
        rows=groups.pop(key);want,scored=metrics(rows,s['target']);errors=[]
        for field,v in want.items():
            if not same(v,s.get(field)):errors.append(field)
            if isinstance(v,(int,float))and isinstance(s.get(field),(int,float)):max_diff=max(max_diff,abs(v-s[field]))
        if digest(canon(sorted(r.key for r in rows)))!=s['cohort_membership_sha256']or digest(canon(sorted(r.key for r in scored)))!=s['scored_membership_sha256']:errors.append('membership_hash')
        if errors:mismatches.append(dict(record_id=s['record_id'],fields=errors))
        actual_weeks=sorted({r.week for r in scored});query_weeks=sorted({r.week for r in rows})
        date_mismatches+=s['evaluation_weeks']!=actual_weeks
        losses=collections.defaultdict(list)
        for r in scored:losses[r.key[0]].append((r.prediction-r.actual)**2 if r.target=='anytime_td'else abs(r.prediction-r.actual))
        n=len(scored);g=len(losses);mean=math.fsum(v for vs in losses.values()for v in vs)/n if n else None
        se=math.sqrt(g/(g-1)*math.fsum((math.fsum(vs)-len(vs)*mean)**2 for vs in losses.values())/n**2)if g>=8 else None
        u=s['uncertainty'];cluster_mismatches+=not same(se,u['game_cluster_sensitivity_se'])or u['week_clusters']!=len(actual_weeks)or u['week_interval']is not None
        if s['fallback_view']=='all_competitor_learned_overlap':
            mask=s['scored_membership_sha256'];common=s['target'],s['population'],s['cohort_id']
            cohort_masks.setdefault(common,set()).add(mask)
        checked+=1
    if groups:raise ValueError('independently derived score groups omitted')
    # Representative individual win/loss from retained new and old RA points.
    paired=collections.defaultdict(dict)
    for r in records:
        if r.target=='rush_att'and r.pop=='primary'and r.arm=='H-CURRENT'and r.actual is not None:
            if r.proc=='hgb-direct-history-controls-v1:absolute_error_point':paired[r.key]['old']=r
            if r.proc=='v2-hgb-rush-att-qb-rb-specialization-v1:common-feature-memory':paired[r.key]['new']=r
    examples={}
    for key,pair in paired.items():
        if len(pair)!=2:continue
        a,b=pair['new'],pair['old'];da=abs(a.prediction-a.actual);db=abs(b.prediction-b.actual)
        side='win'if da<db else'loss'if da>db else'tie'
        if side in('win','loss')and side not in examples:examples[side]=dict(query_sha256=digest(canon(key)),new_absolute_error=da,old_absolute_error=db,paired_difference=da-db)
    result=dict(version='v2-independent-pregame-cohort-rawprefix-score-qa-v1',status='PASS'if not(membership_mismatch or future_mismatch or mismatches or cluster_mismatches or any(len(x)>1 for x in cohort_masks.values()))else'FAIL',completed_at_utc=datetime.now(timezone.utc).isoformat(),software_code_sha256=sha(__file__),cohort_builder_code_sha256=reg['code_sha256'],checked_score_sha256=receipt['score_sha256'],source_counts=source_counts,historical_membership=member_summary,future_membership=future_summary,historical_membership_mismatches=len(membership_mismatch),future_membership_mismatches=len(future_mismatch),retained_prediction_views=len(records),distinct_games=len({r.key[0]for r in records}),distinct_player_games=len({r.key[:2]for r in records}),distinct_historical_query_cells=len(member),aggregate_views_checked=checked,metric_or_hash_mismatch_count=len(mismatches),metric_or_hash_mismatches=mismatches[:20],max_absolute_numeric_reproduction_difference=max_diff,cluster_sensitivity_mismatch_count=cluster_mismatches,views_evaluation_weeks_differ_from_actual_supported_weeks=date_mismatches,all_competitor_masks_with_inconsistent_competitor_hashes=sum(len(v)>1 for v in cohort_masks.values()),shared_learned_counts=[dict(target=k[0],population=k[1],query_cells=len(v))for k,v in sorted(shared.items())],actual_cohort_names=sorted({s['cohort_id']for s in scores}),representative_paired_win_loss=examples,new_fits=0,new_forecasts=0,week8_outcomes_read=0,wall_seconds=time.monotonic()-started,limits=['Ranks are genuinely earlier-feature-defined within a retrospective observed-stat-row query universe, not authentic historical exante roster/offer eligibility','Source seven-day availability is assumed, not historical publication authenticated','Common workloadselector uses2022-start history even on strictly2026-feature model views; protocol discloses selector is diagnostic, not a pure-current selectedsystem','Seven weeks are insufficient for eight-week cluster intervals; game sandwich sensitivity is not independent-selection significance','All_competitor overlap includes every observed method/product/history/strict policy; it is explicitly restrictive, not independent new NFL evidence','Future1795query/13game cohort is separately frozen/unscored at shared00:27asof and lateractualfreeze, not an exactT90snapshot'])
    with args.output.open('xb')as f:f.write(canon(result))
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for arg in('source-root','old-protocol','old-queries','future-queries','public-root','private-root','empirical','hgb-chunks','distributions','counts','output'):p.add_argument('--'+arg,type=Path,required=True)
    r=check(p.parse_args());print(json.dumps({k:v for k,v in r.items()if k not in('shared_learned_counts','metric_or_hash_mismatches')},indent=2))
