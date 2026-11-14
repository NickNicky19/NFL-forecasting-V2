"""Session B independent check of the ONE website-owner frozen historical policy.

No fit, provider request, live overlay admission or competing mapping. Inputs are
the immutable public objects specifically supplied by the website owner.
"""
from pathlib import Path
from datetime import datetime,timezone,timedelta
from zoneinfo import ZoneInfo
import json,gzip,hashlib,base64,csv,collections,math,copy,sys,itertools,time,resource
D=Path(__file__).parent;W=D/'website';C=D/'C';S=D/'selector-inputs'
sys.path[:0]=[str(W/'tools'),str(W/'pull')]
import weekly_selected_rankings as actual_rank,weekly_adaptive_overlay as actual_overlay,grade as actual_grade
start=time.monotonic();N=collections.Counter()
def ck(v,kind):
    assert v,kind
    N[kind]+=1
def load(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def utc(x):
    t=datetime.fromisoformat(x.replace('Z','+00:00'));ck(t.tzinfo is not None,'aware_clock');return t
def num(x):return type(x) in (int,float) and math.isfinite(x)
def tm(x):return {'LA':'LAR'}.get(x,x)
manifest=load(D/'block4.json');protocol=load(D/'block0.json');fetch=load(D/'FETCH_VERIFICATION.json')
for m in fetch['inputs']:
    p=D/m['local_relative_path'];ck(sha(p)==m['sha256'],'immutable_input_hash');ck(p.stat().st_size==m['bytes'],'immutable_input_bytes')
ck(sha(W/'tools/weekly_selected_rankings.py')==protocol['production_ranker_sha256'],'actual_ranker_hash')
proofraw=gzip.decompress(base64.b64decode(manifest['proof_gzip_base64']));ck(hashlib.sha256(proofraw).hexdigest()==manifest['proof_uncompressed_sha256'],'decoded_proof_hash');proof=json.loads(proofraw)

# Reconstruct saved-point bindings directly, without running the owner's helper.
raw=load(C/'reports/player-context-matchup-01/v1.1/RUN.json')
feat=json.loads(gzip.decompress((C/'artifacts/player-context-matchup-01/v1.1/FEATURE_EXPORT.json.gz').read_bytes()))
rows=json.loads(gzip.decompress((C/'artifacts/player-context-matchup-01/v1.1/NUMERICAL_ROWS.json.gz').read_bytes()))
fm={(r['origin'],r['game_id'],r['player_id']):r for r in feat};ck(len(fm)==len(feat),'feature_key_unique')
orig={r['origin']:r for r in raw['origins']};points={}
for r in rows:
    if r['procedure']!='P1':continue
    k=(r['origin'],r['game_id'],r['player_id']);ck(k not in points,'saved_point_key_unique');f=fm[k]
    ck(r['position']==f['position'],'saved_point_role');ck(num(r['mean']) and r['mean']>=0,'finite_nonnegative_mean')
    models=[p for p in raw['models'] if p.endswith('/'+r['origin']+'-P1.json.gz')];ck(len(models)==1,'per_origin_model')
    points[k]=dict(r,team=f['team'],opponent=f['opponent'],kickoff_UTC=f['kickoff_UTC'],model_sha256=raw['models'][models[0]],fit_cutoff_UTC=orig[r['origin']]['fit_cutoff_UTC'])
ck(len(points)==2425,'saved_P1_count')
bridges=collections.defaultdict(set)
for path in ['sources/propline-v7/historical_identity_crosswalk.json.gz','artifacts/reliability-v8/IDENTITY_CROSSWALK.json.gz']:
    for r in json.loads(gzip.decompress((C/path).read_bytes())):
        native=str(r.get('native_player_id',''))
        if r.get('player_id') and native.startswith('espn:') and native[5:].isdigit():bridges[native[5:]].add(r['player_id'])

# Independent global-boundary census. This checks only the declared reconstructed
# clock predicate, and cannot authenticate missing original source vintages.
schedule_paths=[C/'prospective/runs/C-FWD-v4-20261101-0009-P2-pass_yd/sources/schedule.csv',C/'prospective/runs/C-FWD-v4-20261105-W09-JAXBAL-remainder/sources/schedule.csv']
def schedule(p):
    out={}
    for r in csv.DictReader(p.open()):
        if not r['gameday'] or not r['gametime']:continue
        k=datetime.fromisoformat(r['gameday']+'T'+r['gametime']).replace(tzinfo=ZoneInfo('America/New_York')).astimezone(timezone.utc)
        ck(r['game_id'] not in out,'source_game_unique');out[r['game_id']]=dict(game_id=r['game_id'],season=int(r['season']),week=int(r['week']),home=r['home_team'],away=r['away_team'],kickoff=k)
    return out
sa,sb=map(schedule,schedule_paths)
relevant={k for k,r in sa.items() if r['season']==2026 and 1<=r['week']<=8}
ck(relevant=={k for k,r in sb.items() if r['season']==2026 and 1<=r['week']<=8},'schedule_universe')
ck(all(sa[k]['kickoff']==sb[k]['kickoff'] for k in relevant),'schedule_121_clocks')
for week in [4,5,6,7]:
    final=load(W/f'output/data/weeks/2026_w{week:02d}.json');native={(tm(g['home']),tm(g['away'])):g for g in final['games']}
    rr=[r for r in sa.values() if r['season']==2026 and r['week']==week];ck(len(rr)==len(native),'previous_week_census')
    for r in rr:ck(utc(native[(tm(r['home']),tm(r['away']))]['kickoff'])==r['kickoff'],'previous_game_clock')
boundaries=sorted((r['kickoff']+timedelta(days=7),k) for k,r in sa.items())
P=actual_rank.POLICY
def eligible(p):
    minimum=P['minimum_projected_ppr'].get(p.get('pos'))
    return (minimum is not None and p.get('injury') not in P['unavailable'] and num(p.get('games_this_season')) and p['games_this_season']>=P['minimum_games'] and num(p.get('snap_share')) and p['snap_share']>=P['minimum_snap_share'] and num(p.get('proj_ppr')) and p['proj_ppr']>=minimum)
def order(p):return (-abs(p['score']),p['game_id'],p['player_id'],p['key'])
def independently_select(board,overrides):
    games={g['id']:g for g in board['games']};now=utc(board['generated_at']);choices={'over':[],'under':[]}
    for pl in board['players']:
        ck(eligible(pl)==actual_rank.eligible(pl),'eligible_function_parity')
        g=games[pl['game_id']]
        if not eligible(pl) or g['state']!='pre' or utc(g['kickoff'])<=now:continue
        best={}
        for prop in pl['props']:
            cat=P['categories'].get(prop['key']);line=prop.get('line');key=(pl['game_id'],pl['id'],prop['key']);pt=overrides.get(key);value=pt['mean'] if pt else prop.get('adj')
            if cat is None or prop.get('line_from') not in ('dk','sleeper') or not num(line) or not num(value):continue
            if type(prop.get('over')) is not int or type(prop.get('n')) is not int or not 0<=prop['over']<=prop['n']:continue
            if line<cat['minimum_line'] or not P['projection_line_ratio'][0]<=value/line<=P['projection_line_ratio'][1]:continue
            gap=value-line;score=gap/cat['scale']
            if abs(gap)<=cat['lean'] or abs(score)<P['minimum_score']:continue
            side='over' if gap>0 else 'under'
            item=dict(player_id=pl['id'],game_id=pl['game_id'],key=prop['key'],direction=side,line=line,line_from=prop['line_from'],adj=value,score=score,source='C_P1_MEAN_RECONSTRUCTED' if pt else 'SAVED_WEBSITE_REFERENCE',candidate_model_sha256=pt['model_sha256'] if pt else None)
            if side not in best or order(item)<order(best[side]):best[side]=item
        for side,item in best.items():choices[side].append(item)
    return {s:sorted(rr,key=order)[:P['top_n']] for s,rr in choices.items()}

# Independent raw presence/identity grading. We compare this with the actual v5
# helper on EVERY selected row; no owner aggregation helper is used.
count_keys={'pass_td','pass_cmp','pass_att','pass_int','rush_att','rec','gp','off_snp'}
def component(stats,key):
    x=stats.get(key);metadata=stats.get('_presence')
    if isinstance(metadata,dict) and key in metadata.get('invalid_fields',[]):return None
    if not num(x) or (key in count_keys and x<0) or int(x)!=x:return None
    return x
def independently_grade(board,pl,item,entry,finals):
    if item['game_id'] not in finals:return None,'pending','not_final'
    game=[g for g in board['games'] if g['id']==item['game_id']]
    if len(game)!=1 or item['game_id']!=pl['game_id']:return None,'unresolved','identity'
    game=game[0];op=game['away'] if pl['team']==game['home'] else game['home'] if pl['team']==game['away'] else None
    if op is None or pl.get('opp') not in (op,None) or not isinstance(entry,dict):return None,'unresolved','identity_or_absent_entry'
    if entry.get('team') not in (pl['team'],None) or entry.get('opp') not in (op,None):return None,'unresolved','source_identity'
    stats=entry.get('stats')
    if not isinstance(stats,dict):return None,'unresolved','missing_stats'
    meta=stats.get('_presence')
    if '_presence' in stats:
        original=meta.get('original_row') if isinstance(meta,dict) else None;context=meta.get('source_context') if isinstance(meta,dict) else None
        if not (isinstance(original,dict) and isinstance(context,dict) and meta.get('version')=='nfl-data-presence-strict-v3' and meta.get('kind')=='actual' and original.get('player_id')==pl['id'] and original.get('team')==pl['team'] and original.get('opponent')==op and (context.get('season'),context.get('week'))==(board['season'],board['week']) and original.get('stats')=={k:v for k,v in stats.items() if k!='_presence'}):return None,'unresolved','presence_binding'
    for key in ('gp','off_snp'):
        if stats.get(key) is not None and (not num(stats[key]) or stats[key]<0 or ('_presence' in stats and int(stats[key])!=stats[key])):return None,'unresolved','participation_invalid'
    played=(stats.get('gp') or 0)>0 or (stats.get('off_snp') or 0)>0;dnp=entry.get('participation_status')=='dnp' and bool(entry.get('participation_source'))
    if not played:return None,'dnp' if dnp else 'unresolved','dnp' if dnp else 'participation_unknown'
    if dnp:return None,'unresolved','participation_conflict'
    keys=('rush_yd','rec_yd') if item['key']=='rush_rec_yd' else (item['key'],)
    values=[component(stats,k) for k in keys]
    if any(v is None for v in values):return None,'unresolved','component_unknown'
    value=round(sum(values),2);line=item['line'];state='push' if value==line else 'hit' if (value>line)==(item['direction']=='over') else 'miss'
    return value,state,'reported_zero' if value==0 else 'reported_value'

allrows=[];weeks=[];bound_counts=collections.Counter();coverage_all=collections.Counter();parity_fields=['player_id','game_id','key','direction','line','line_from','adj','score'];examples={}
for week in protocol['weeks']:
    board=load(S/f'W{week}_FULL_ORIGINAL_BOARD.private.json');ck(sha(S/f'W{week}_FULL_ORIGINAL_BOARD.private.json')==protocol['inputs'][f'W{week}'],'protocol_board_hash')
    games={g['id']:g for g in board['games']};now=utc(board['generated_at']);status={};overrides={};coverage=collections.Counter()
    for g in board['games']:
        end=utc(g['kickoff']);rr=[r for r in sa.values() if r['season']==2026 and r['week']==week and (tm(r['home']),tm(r['away']))==(tm(g['home']),tm(g['away']))]
        ck(len(rr)==1 and rr[0]['kickoff']==end,'board_game_binding');rid=rr[0]['game_id'];prior_model=[r for k,r in points.items() if k[1]==rid];fitready=all(utc(r['fit_cutoff_UTC'])<=now for r in prior_model)
        eligible_game=g['state']=='pre' and now<end;hits=[[t.isoformat(),k] for t,k in boundaries if now<=t<end] if eligible_game else []
        state='RECONSTRUCTED_PREFIX_INVARIANT' if eligible_game and not hits and fitready else 'HAS_BOUNDARY' if eligible_game and hits else 'UNRESOLVED'
        supplied=proof['games'][f'{week}:{g["id"]}'];ck(state==supplied['status'],'independent_timing_state');ck(hits==supplied['global_boundaries'],'independent_all_global_boundaries');ck(fitready==supplied['fitted_origin_before_board'],'fit_clock')
        status[g['id']]=(state,rid);bound_counts[state]+=1
    for pl in board['players']:
        g=games[pl['game_id']]
        if not eligible(pl) or g['state']!='pre' or utc(g['kickoff'])<=now:continue
        for prop in pl['props']:
            if prop['key']!='rec' or prop.get('line_from') not in ('dk','sleeper') or not num(prop.get('line')):continue
            point=None
            if pl['pos'] not in ('WR','TE'):reason='UNSUPPORTED_ROLE_REFERENCE'
            elif len(bridges.get(str(pl.get('espn_id')),set()))!=1:reason='MISSING_OR_CONFLICTING_ID_REFERENCE'
            else:
                rid=status[g['id']][1];gsis=next(iter(bridges[str(pl['espn_id'])]));point=points.get((f'2026-W{week:02d}',rid,gsis))
                if point is None:reason='MISSING_EXACT_PLAYER_GAME_POINT_REFERENCE'
                elif tm(point['team'])!=tm(pl['team']) or tm(point['opponent'])!=tm(pl['opp']) or point['position']!=pl['pos'] or utc(point['kickoff_UTC'])!=utc(g['kickoff']):reason='IDENTITY_ROLE_EVENT_MISMATCH_REFERENCE'
                elif not num(point['mean']) or utc(point['fit_cutoff_UTC'])>now:reason='MODEL_POINT_OR_FIT_CLOCK_REFERENCE'
                elif status[g['id']][0]!='RECONSTRUCTED_PREFIX_INVARIANT':reason='QUERY_HORIZON_UNQUALIFIED_REFERENCE'
                else:reason='C_P1_MEAN_RECONSTRUCTED_PREFIX_INVARIANT';overrides[(pl['game_id'],pl['id'],'rec')]=point
            coverage[reason]+=1
    coverage_all.update(coverage);byid={p['id']:p for p in board['players']};policies={}
    stats=load(W/f'data/cache/stat-keys-presence-strict-v3/stats_2026_{week:02d}.json');final=load(W/f'output/data/weeks/2026_w{week:02d}.json');finals={g['id'] for g in final['games'] if g['state']=='post' and g.get('completed') is True and g.get('home_score') is not None and g.get('away_score') is not None}
    for name,override in [('saved_control',{}),('candidate',overrides)]:
        own=independently_select(board,override)
        # Execute actual unchanged production code on a separate in-memory
        # historical-input copy. This is diagnostic parity, not live admission.
        parityboard=copy.deepcopy(board)
        for pl in parityboard['players']:
            for p in pl['props']:
                q=override.get((pl['game_id'],pl['id'],p['key']))
                if q:p['adj']=q['mean']
        digest=actual_overlay.digest(parityboard);doc=actual_overlay.prepare_overlay(parityboard,digest,{},{},website_source_sha=protocol['main'],prepared_at=board['generated_at'])
        production=actual_rank.prepare(parityboard,digest,doc,actual_overlay.digest(doc),now=board['generated_at'],website_source_sha=protocol['main'])
        rr=[]
        for side in ('over','under'):
            ck(len(own[side])==len(production['picks'][side]),'actual_function_count_parity')
            for a,b in zip(own[side],production['picks'][side]):
                for field in parity_fields:ck(a[field]==b[field],'actual_function_membership_value_parity')
                pl=byid[a['player_id']];entry=stats.get(pl['id']);value,state,reason=independently_grade(board,pl,a,entry,finals)
                gv,gs=actual_grade._prop_result(a,side,actual_grade._bound_stats(board,pl,entry,game_id=a['game_id'])) if a['game_id'] in finals else (None,'pending')
                ck((value,state)==(gv,gs),'independent_raw_grading_parity')
                row=dict(a,result=state,actual=value,as_of_board_clock=board['generated_at'],original_issuance=False,week=week,policy=name);rr.append(row);allrows.append(row)
                for label,match in [('win',state=='hit'),('loss',state=='miss'),('unknown',state=='unresolved'),('reported_zero',reason=='reported_zero'),('candidate_model',a['source']=='C_P1_MEAN_RECONSTRUCTED'),('fallback',name=='candidate' and a['source']=='SAVED_WEBSITE_REFERENCE')]:
                    if label not in examples and match:examples[label]={**row,'presence_reason':reason,'raw_components':{k:entry.get('stats',{}).get(k) for k in (('rush_yd','rec_yd') if a['key']=='rush_rec_yd' else (a['key'],))} if isinstance(entry,dict) else None}
        policies[name]=rr
    key=lambda x:(x['game_id'],x['player_id'],x['key'],x['direction']);sides={n:collections.Counter(r['result'] for r in rr) for n,rr in policies.items()};sets={n:{key(r) for r in rr} for n,rr in policies.items()};common=sets['saved_control']&sets['candidate']
    removed=[r for r in policies['saved_control'] if key(r) not in common];added=[r for r in policies['candidate'] if key(r) not in common]
    weeks.append(dict(week=week,board_clock=board['generated_at'],board_games=len(games),board_player_games=len(board['players']),rec_opportunity_coverage=dict(coverage),candidate_point_overrides=len(overrides),candidate_selected_model_rows=sum(r['source']=='C_P1_MEAN_RECONSTRUCTED' for r in policies['candidate']),selected={n:len(rr) for n,rr in policies.items()},states={n:dict(v) for n,v in sides.items()},own_sides={n:{s:dict(collections.Counter(r['result'] for r in rr if r['direction']==s)) for s in ('over','under')} for n,rr in policies.items()},membership_common_same_side=len(common),control_only=len(removed),candidate_only=len(added),removed_states=dict(collections.Counter(r['result'] for r in removed)),added_states=dict(collections.Counter(r['result'] for r in added))))

fields=manifest['canonical_membership']['fields'];canonical=[{k:r[k] for k in fields} for r in allrows];commitment=hashlib.sha256(json.dumps(canonical,sort_keys=True,separators=(',',':')).encode()).hexdigest()
ck(commitment==manifest['canonical_membership']['canonical_sha256'],'entire_owner_canonical_membership_result_hash')
totals={}
for name in ('saved_control','candidate'):
    rr=[r for r in allrows if r['policy']==name];cnt=collections.Counter(r['result'] for r in rr);n=cnt['hit']+cnt['miss'];totals[name]=dict(selected=len(rr),states=dict(cnt),decided=n,accuracy=cnt['hit']/n,own_sides={s:dict(collections.Counter(r['result'] for r in rr if r['direction']==s)) for s in ('over','under')})
# Deterministic software boundaries are ZERO additional NFL observations.
fixtures=[({'stats':{'gp':1,'rec':None}},'rec','under',.5,None,'unresolved'),({'stats':{'gp':1,'rec':0}},'rec','under',.5,0,'hit'),({'stats':{'gp':1,'rush_yd':55,'rec_yd':None}},'rush_rec_yd','over',50.5,None,'unresolved'),({'stats':{'gp':1,'rec':2}},'rec','over',2,2,'push')]
fixture_results=[]
board={'season':2026,'week':5,'games':[{'id':'fixture','home':'A','away':'B'}]};pl={'id':'fixture','game_id':'fixture','team':'A','opp':'B'}
for entry,cat,side,line,v,st in fixtures:
    item={'game_id':'fixture','key':cat,'direction':side,'line':line};out=independently_grade(board,pl,item,entry,{'fixture'});ck(out[:2]==(v,st),'synthetic_presence_boundary');fixture_results.append(dict(category=cat,direction=side,line=line,expected_actual=v,expected_state=st,observed_actual=out[0],observed_state=out[1]))
result={'id':'B-INDEPENDENT-WEBSITE-FOUR-WEEK-SELECTOR-20261112-v1','verified_UTC':datetime.now(timezone.utc).isoformat(),'owner_protocol':protocol['id'],'owner_protocol_file_sha256':sha(D/'block0.json'),'owner_source_comment':'https://github.com/NickNicky19/nicks-expert-nfl-picks/pull/1#issuecomment-6812058949','owner_result_comment':'https://github.com/NickNicky19/nicks-expert-nfl-picks/pull/1#issuecomment-6812397309','state':'PASS_WITHIN_FOUR_WEEK_CONDITIONAL_RETROSPECTIVE_SCOPE','source_inputs_verified':len(fetch['inputs']),'source_input_bytes':fetch['bytes'],'actual_ranker_sha256':sha(W/'tools/weekly_selected_rankings.py'),'grader_sha256':sha(W/'pull/grade.py'),'canonical_membership_rows':len(canonical),'canonical_membership_sha256':commitment,'weeks':weeks,'cumulative':totals,'reconstructed_timing_predicate_counts':dict(bound_counts),'rec_opportunity_coverage':dict(coverage_all),'deterministic_examples':examples,'synthetic_boundary_checks':fixture_results,'assertion_counts':dict(N),'resources':{'wall_seconds':time.monotonic()-start,'process_peak_RSS_KiB':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss},'fits_new_model_inference_provider_requests_issued_picks_grades':0,'new_NFL_games_or_actual_offer_weeks':0,'tested_scored_historical_weeks':4,'five_week_primary_qualification':False,'current_v2_incumbent_historical_comparison':False,'independent_scope':['Reconstructed identities/roles and per-origin point/model bindings directly from permitted immutable original C saved-point sources.','Recomputed every game timing-admission predicate from both retained source schedules and site prior-game clocks; agrees with supplied conditional proof.','Independent selector calculation and actual unchanged production-function parity for BOTH complete historical policy lists.','Independent raw presence/identity/participation/statistic grading for all192 policy-pick rows agrees with actual v5 helper.','All192 canonical selected identity/value/side/result records exactly match owner commitment; no reliance on owner aggregate percentages.'],'not_verified':['Fresh fitted model or raw-to-feature reproduction; saved output/source schema, not a new fit audit.','Original C schedule/facts vintage bytes and explicit-unknown source clock preservation, actual pregame historical roster or originally issued candidate picks.','Per-offer bookmaker observation clocks, prices or venue settlements.','A fifth compatible board, five-week primary-selector eligibility, current-v2 reference historical inputs, prospective superiority, live consumer admission or deployment.'],'decision':'Four-week replay execution and arithmetic acknowledged; retain incumbent primary Top Picks. Candidate remains an exposed retrospective diagnostic, not established superiority.','remaining_owner_action':'Website owner resolves the fifth source-compatible full board and model/query timing closure under the frozen complete mapping; B independently verifies any extension; C records this actual receipt.'}
(D/'B_INDEPENDENT_SELECTOR_VERIFICATION_V1.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
(D/'B_CANONICAL_PICKS.local.json').write_text(json.dumps(canonical,indent=2,allow_nan=False)+'\n')
print(json.dumps({'state':result['state'],'totals':totals,'weeks':[{k:w[k] for k in ['week','candidate_point_overrides','candidate_selected_model_rows','states','control_only','candidate_only']}for w in weeks],'canonical_sha256':commitment,'assertion_counts':dict(N)},indent=2))
