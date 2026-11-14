"""Independent B calculation of one additional frozen website selector week.

Reuses B's earlier independently implemented selector/presence equations. Actual
production selector is called only for parity; no author scoring helper is used.
Only supplied immutable source evidence is read. Protected boards stay owner-local.
"""
import argparse,collections,csv,datetime,gzip,hashlib,json,math,sys,time,copy
from pathlib import Path
from zoneinfo import ZoneInfo

N=collections.Counter()
def ck(value,name):
    if not value:raise AssertionError(name)
    N[name]+=1

def sha(body):return hashlib.sha256(body).hexdigest()
def load(path):return json.loads(path.read_bytes())
def utc(value):
    d=datetime.datetime.fromisoformat(value.replace('Z','+00:00'))
    ck(d.tzinfo is not None,'awareclock')
    return d

count_keys={'pass_td','pass_cmp','pass_att','pass_int','rush_att','rec','gp','off_snp'}

def num(x):return type(x) in (int,float) and math.isfinite(x)

def tm(x):return {'LA':'LAR'}.get(x,x)

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

def summary(rows):
    def one(rr):
        c=collections.Counter(r['result']for r in rr);n=c['hit']+c['miss']
        return dict(selected=len(rr),wins=c['hit'],losses=c['miss'],decided=n,unknown=c['unresolved'],push=c['push'],dnp=c['dnp'],rate=c['hit']/n if n else None)
    return dict(**one(rows),own_sides={s:one([r for r in rows if r['direction']==s])for s in ['over','under']})


def main():
    global P,actual_rank
    ap=argparse.ArgumentParser();ap.add_argument('--inputs',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    start=time.monotonic();cpu=time.process_time();r=a.inputs;out=a.out;out.mkdir(parents=True,exist_ok=True)
    dest=out/'B_FIFTH_WEEK_INDEPENDENT_REVIEW_V1.json';ck(not dest.exists(),'createonly')
    bindings=load(r/'output/data/selector-replay-v1/input-bindings-v1.json');fetched=load(r/'W4_INPUTS_FETCH.json')
    for b in fetched:
        body=(r/b['local_relative_path']).read_bytes();ck(sha(body)==b['sha256']and len(body)==b['bytes'],'immutableinput')
    W=r/'website';C=r/'C';sys.path[:0]=[str(W/'tools')]
    import weekly_selected_rankings as actual_rank
    import weekly_adaptive_overlay as actual_overlay
    P=actual_rank.POLICY;ck(sha((W/'tools/weekly_selected_rankings.py').read_bytes())=='7889c35cefa0df1ba0be53ee749182f243eba35a4f4c63b2c01db023e701e14f','frozenranker')
    run=load(C/'reports/player-context-matchup-01/v1.1/RUN.json');orig={o['origin']:o for o in run['origins']}
    fr=json.loads(gzip.decompress((C/'artifacts/player-context-matchup-01/v1.1/FEATURE_EXPORT.json.gz').read_bytes()));fm={(x['origin'],x['game_id'],x['player_id']):x for x in fr}
    points={}
    for x in json.loads(gzip.decompress((C/'artifacts/player-context-matchup-01/v1.1/NUMERICAL_ROWS.json.gz').read_bytes())):
        if x['procedure']!='P1':continue
        key=(x['origin'],x['game_id'],x['player_id']);f=fm[key];models=[k for k in run['models']if k.endswith('/'+x['origin']+'-P1.json.gz')]
        ck(len(models)==1 and x['position']==f['position']and num(x['mean']),'savedpointbinding')
        points[key]=dict(x,team=f['team'],opponent=f['opponent'],kickoff_UTC=f['kickoff_UTC'],model_sha256=run['models'][models[0]],fit_cutoff_UTC=orig[x['origin']]['fit_cutoff_UTC'])
    bridges=collections.defaultdict(set)
    for p in ['sources/propline-v7/historical_identity_crosswalk.json.gz','artifacts/reliability-v8/IDENTITY_CROSSWALK.json.gz']:
        for x in json.loads(gzip.decompress((C/p).read_bytes())):
            n=str(x.get('native_player_id',''))
            if x.get('player_id')and n.startswith('espn:')and n[5:].isdigit():bridges[n[5:]].add(x['player_id'])
    def schedule(path):
        rows={}
        for x in csv.DictReader(path.open()):
            if not x['gameday']or not x['gametime']:continue
            t=datetime.datetime.fromisoformat(x['gameday']+'T'+x['gametime']).replace(tzinfo=ZoneInfo('America/New_York')).astimezone(datetime.timezone.utc)
            rows[x['game_id']]=dict(game_id=x['game_id'],season=int(x['season']),week=int(x['week']),home=x['home_team'],away=x['away_team'],kickoff=t)
        return rows
    sa=schedule(C/'prospective/runs/C-FWD-v4-20261101-0009-P2-pass_yd/sources/schedule.csv');sb=schedule(C/'prospective/runs/C-FWD-v4-20261105-W09-JAXBAL-remainder/sources/schedule.csv')
    relevant={k for k,x in sa.items()if x['season']==2026 and 1<=x['week']<=8}
    ck(relevant=={k for k,x in sb.items()if x['season']==2026 and 1<=x['week']<=8}and all(sa[k]['kickoff']==sb[k]['kickoff']for k in relevant),'scheduleclockparity')
    boundaries=sorted((x['kickoff']+datetime.timedelta(days=7),k)for k,x in sa.items())
    board=load(r/'selector-inputs/W4_FULL_ORIGINAL_BOARD.private.json');games={g['id']:g for g in board['games']};now=utc(board['generated_at']);statuses={}
    for g in games.values():
        end=utc(g['kickoff']);rr=[x for x in sa.values()if x['season']==2026 and x['week']==4 and(tm(x['home']),tm(x['away']))==(tm(g['home']),tm(g['away']))]
        ck(len(rr)==1 and rr[0]['kickoff']==end,'eventidentityclock')
        gid=rr[0]['game_id'];fits=[x for k,x in points.items()if k[1]==gid];ready=all(utc(x['fit_cutoff_UTC'])<=now for x in fits)
        hits=[(t.isoformat(),k)for t,k in boundaries if now<=t<end]if g['state']=='pre'and now<end else[]
        state='RECONSTRUCTED_PREFIX_INVARIANT'if g['state']=='pre'and now<end and not hits and ready else'HAS_BOUNDARY'if g['state']=='pre'and now<end and hits else'UNRESOLVED'
        statuses[g['id']]=dict(status=state,gid=gid,boundaries=hits,fitready=ready)
    overrides={};coverage=collections.Counter()
    for pl in board['players']:
        g=games[pl['game_id']]
        if not eligible(pl)or g['state']!='pre'or utc(g['kickoff'])<=now:continue
        for prop in pl['props']:
            if prop['key']!='rec'or prop.get('line_from')not in('dk','sleeper')or not num(prop.get('line')):continue
            if pl['pos']not in('WR','TE'):reason='UNSUPPORTED_ROLE_REFERENCE'
            elif len(bridges.get(str(pl.get('espn_id')),set()))!=1:reason='MISSING_OR_CONFLICTING_ID_REFERENCE'
            else:
                point=points.get(('2026-W04',statuses[g['id']]['gid'],next(iter(bridges[str(pl['espn_id'])]))))
                if point is None:reason='MISSING_EXACT_PLAYER_GAME_POINT_REFERENCE'
                elif tm(point['team'])!=tm(pl['team'])or tm(point['opponent'])!=tm(pl['opp'])or point['position']!=pl['pos']or utc(point['kickoff_UTC'])!=utc(g['kickoff']):reason='IDENTITY_ROLE_EVENT_MISMATCH_REFERENCE'
                elif not num(point['mean'])or utc(point['fit_cutoff_UTC'])>now:reason='MODEL_POINT_OR_FIT_CLOCK_REFERENCE'
                elif statuses[g['id']]['status']!='RECONSTRUCTED_PREFIX_INVARIANT':reason='QUERY_HORIZON_UNQUALIFIED_REFERENCE'
                else:reason='C_P1_MEAN_RECONSTRUCTED_PREFIX_INVARIANT';overrides[(pl['game_id'],pl['id'],'rec')]=point
            coverage[reason]+=1
    ck(dict(coverage)=={'UNSUPPORTED_ROLE_REFERENCE':3,'QUERY_HORIZON_UNQUALIFIED_REFERENCE':5,'C_P1_MEAN_RECONSTRUCTED_PREFIX_INVARIANT':4},'newW4coverage')
    # Finality comes from the separately versioned explicit completed sources,
    # never from a legacy Final string alone.
    finals=set();finality=[]
    for f in bindings['current_finality_sources']:
        body=gzip.decompress((W/'output/data/verified-int-v1/sources'/(f['raw_SHA256']+'.json.gz')).read_bytes());ck(sha(body)==f['raw_SHA256'],'finalityrawhash');j=json.loads(body);h=j['header'];co=h['competitions'][0];t=co['status']['type']
        ck(str(h['id'])==f['event']and t.get('completed')is True and t.get('state')=='post','explicitfinality')
        g=games[f['event']];ck(utc(co['date'])==utc(g['kickoff']),'finalkickoff');teams={v['team']['abbreviation']for v in co['competitors']};ck(teams=={g['home'],g['away']},'finalteams')
        finals.add(f['event']);finality.append(dict(event=f['event'],raw_sha256=f['raw_SHA256'],explicit_completed=True))
    stats=load(W/'data/cache/stat-keys-presence-strict-v3/stats_2026_04.json');v7=load(W/'output/data/verified-int-v1/index-v2.json');v7cases={(str(x['game_id']),str(x['player_id']),x['week']):x for x in v7['cases']}
    players={pl['id']:pl for pl in board['players']};policies={};allrows=[]
    for name,override in [('saved_control',{}),('candidate',overrides)]:
        own=independently_select(board,override);parity=copy.deepcopy(board)
        for pl in parity['players']:
            for prop in pl['props']:
                q=override.get((pl['game_id'],pl['id'],prop['key']))
                if q:prop['adj']=q['mean']
        digest=actual_overlay.digest(parity);doc=actual_overlay.prepare_overlay(parity,digest,{},{},website_source_sha='ccfaa987f5416ca6abce2570f9fee8c4c41c1d3e',prepared_at=board['generated_at'])
        actual=actual_rank.prepare(parity,digest,doc,actual_overlay.digest(doc),now=board['generated_at'],website_source_sha='ccfaa987f5416ca6abce2570f9fee8c4c41c1d3e')
        rr=[]
        for side in ['over','under']:
            ck(len(own[side])==len(actual['picks'][side]),'productionlength')
            for item,app in zip(own[side],actual['picks'][side]):
                for field in ['player_id','game_id','key','direction','line','line_from','adj','score']:ck(item[field]==app[field],'productionmembershipvalue')
                pl=players[item['player_id']];value,state,why=independently_grade(board,pl,item,stats.get(pl['id']),finals)
                original_state=state;verified_case=None
                if item['key']=='pass_int'and(item['game_id'],item['player_id'],4)in v7cases:
                    case=v7cases[item['game_id'],item['player_id'],4]
                    ck(case['direction']==side and case['line']==item['line']and case['team']==pl['team']and case['position']=='QB','V7exactfrozencase')
                    value=case['verified_value'];ck(type(value)is int and value>=0,'V7explicitcount');state='push'if value==item['line']else'hit'if(value>item['line'])==(side=='over')else'miss';verified_case=case['case_id']
                    ck(state==case['corrected_grade'],'V7grade')
                row=dict(item,policy=name,result=state,actual=value,week=4,original_state_before_V7=original_state,V7_case_id=verified_case)
                rr.append(row);allrows.append(row)
        policies[name]=rr
    owner=load(r/'output/data/selector-replay-v1/five-week-summary-v2.json');w4=next(x for x in owner['weeks']if x['week']==4)
    control=policies['saved_control'];candidate=policies['candidate'];models=[x for x in candidate if x['source']=='C_P1_MEAN_RECONSTRUCTED'];fallback=[x for x in candidate if x['source']=='SAVED_WEBSITE_REFERENCE']
    key=lambda x:(x['game_id'],x['player_id'],x['key'],x['direction'])
    keys={k:{key(x)for x in vv}for k,vv in policies.items()};common=keys['saved_control']&keys['candidate'];membership=dict(same_side_common=len(common),control_only=len(keys['saved_control']-common),candidate_only=len(keys['candidate']-common))
    for name,rr in [('control',control),('candidate',candidate),('candidate_generated',models),('candidate_fallback',fallback)]:
        result=summary(rr)
        for field in ['selected','wins','losses','decided','unknown','push','dnp','rate']:ck(result[field]==w4[name][field],'ownerW4independentaggregate')
        for side in ['over','under']:
            for field in ['selected','wins','losses','decided','unknown','rate']:ck(result['own_sides'][side][field]==w4[name]['own_sides'][side][field],'ownerW4sides')
    ck(membership==w4['membership'],'ownerW4membership')
    # Reuse immutable B's original four-week check and contribution accounting;
    # append the one source-bound shared W6 reported-zero measurement only.
    repo=Path(__file__).resolve().parents[4];prior=load(repo/'reports/follow-through-release-defensive-source-01/B/selector-review/SELECTOR_CONTRIBUTION_ACCOUNTING_V1.json');delta=load(r/'output/data/verified-int-v1/replay-grade-delta.json')
    ck(len(delta['changes'])==2 and {x['policy']for x in delta['changes']}=={'saved_control','candidate'},'oneW6case2policyrecords')
    ck(all(x['week']==6 and x['game_id']=='401872999'and x['player_id']=='11559'and x['direction']=='over'and x['key']=='pass_int'and x['line']==.5 and x['old_grade']=='unresolved'and x['corrected_grade']=='miss'and x['verified_actual']==0 for x in delta['changes']),'W6Penixfixedsidezerodelta')
    weeks=[]
    for o in owner['weeks']:
        if o['week']==4:weeks.append(o);continue
        old=next(x for x in prior['weeks']if x['week']==o['week'])
        for name,oldkey in [('control','control_full_system'),('candidate','candidate_full_system'),('candidate_generated','candidate_generated_selected'),('candidate_fallback','fallback_generated_selected')]:
            z=old[oldkey]
            ck(z['selected']==o[name]['selected']and z['wins']==o[name]['wins'],'old4selectedwinsunchanged')
            extra=int(o['week']==6 and name!='candidate_generated');ck(z['losses']+extra==o[name]['losses']and z['unresolved']-extra==o[name]['unknown'],'old4explicitgradeversion')
            for side in ['over','under']:
                t=z['own_sides'][side];extra=int(o['week']==6 and name!='candidate_generated'and side=='over')
                ck(t['wins']==o[name]['own_sides'][side]['wins']and t['losses']+extra==o[name]['own_sides'][side]['losses'],'old4ownsidegradeversion')
        ck(old['common_same_side_selected']==o['membership']['same_side_common']and old['control_only_memberships']['selected']==o['membership']['control_only']and old['candidate_only_memberships']['selected']==o['membership']['candidate_only'],'old4membershipunchanged')
        weeks.append(o)
    cumulative={}
    for name in ['control','candidate','candidate_generated','candidate_fallback']:
        z={k:sum(x[name][k]for x in weeks)for k in ['selected','wins','losses','decided','unknown']};z['rate']=z['wins']/z['decided']if z['decided']else None;z['own_sides']={s:{k:sum(x[name]['own_sides'][s][k]for x in weeks)for k in ['selected','wins','losses','decided','unknown']}for s in ['over','under']}
        for s in ['over','under']:
            t=z['own_sides'][s];t['rate']=t['wins']/t['decided']if t['decided']else None
        cumulative[name]=z
    canonical=json.dumps(allrows,sort_keys=True,separators=(',',':')).encode();(r/'B_W4_RECONSTRUCTED_SELECTED_PRIVATE.json').write_bytes(canonical)
    public_bindings=[{k:v for k,v in x.items()if k not in ['local_relative_path','local_name']}for x in fetched]
    result=dict(id='B_FIFTH_FROZEN_SELECTOR_WEEK_INDEPENDENT_REVIEW_v1',verified_UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),state='PASS_ADDITIONAL_W4_CALCULATION_AND_SCOPED_FIVE_WEEK_RECONCILIATION',website_receipt_comment=6840647997,website_receipt_raw_sha256='626b5c9247c6e594f8856c6046a293b3d1fa6f6e8ece624fa20abbc4f72f8f20',website_published_commit='b2dcc88604ccf925a2f0a144ffb8f3d57018fb3f',owner_protocol=owner['protocol'],policy_unchanged=True,input_bindings=public_bindings,new_W4=dict(control=summary(control),candidate=summary(candidate),candidate_generated=summary(models),reference_fallback=summary(fallback),membership=membership,rec_opportunity_states=dict(coverage),point_overrides=len(overrides),full_available_batch=dict(future_games=2,excluded_started_games=14,players=65,props=292,DK_tagged_lines=84,eligible_players=15),B_reconstructed_selected_rows=27,B_reconstructed_decoded_canonical_sha256=sha(canonical),owner_private_selected_file_sha256=owner['new_W4_selected_file_SHA256'],owner_private_file_parity='NOT_INSPECTED_DIFFERENT_OR_UNSPECIFIED_SERIALIZATION;NO_BYTES_OR_COMBINED_HASH_CLAIM'),grade_version_reconciliation=dict(original_B_four_week_control='48W45L/93+3unknown',original_B_four_week_candidate='50W43L/93+3unknown',shared_W6_case=dict(player='Michael Penix',player_id='11559',game_id='401872999',category='pass_int',side='over',line=.5,verified_zero=0,old='unresolved',new='miss',membership_unchanged=True),four_week_after_measurement_control='48W46L/94+2unknown',four_week_after_measurement_candidate='50W44L/94+2unknown',new_W4_separate_from_measurement=True,delta_sha256=sha((r/'output/data/verified-int-v1/replay-grade-delta.json').read_bytes())),weeks=weeks,cumulative=cumulative,membership={k:sum(x['membership'][k]for x in weeks)for k in ['same_side_common','control_only','candidate_only']},duration=dict(scored_blocks=[[2026,w]for w in range(4,9)],five_week_floor='MET_AT_DECLARED_PARTIAL_CONDITIONAL_RETROSPECTIVE_TIER',candidate_generated_selected_by_week=[dict(week=x['week'],candidate=x['candidate_generated']['selected'],fallback=x['candidate_fallback']['selected'])for x in weeks],candidate_contributing_weeks=[x['week']for x in weeks if x['candidate_generated']['selected']],W8_fallback_only=True,do_not_reset_count_or_invent_new_gate=True),decision='SHADOW;NOT_PRIMARY_ADMITTED;NO_NEW_MAPPING_OR_RELEASE',finality=finality,assertions=dict(N),limits=['W4completeavailablebatchis2futuregames/14startedexcluded;notfullpreSundayNFLweek.','Originalquote/providerpublicationclocksandstatrowqueryuniverseunauthenticated;chronologicalprefixreconstructiononly.','SamefrozenC-P1meanWRTEreceptionsubstitutiondoesnottestallA/B/Ccategorywinners.','OwnerW4private27selectedfilebytesnotobtained;B independentlyreconstructedfrompublicsourcebindingsandmatchedpublishedmembershipcounts/ownsideaggregatesandrealproductionfunction.','Old4weekpriorBverified192rowsreusedplusonesourceboundW6grade-onlydelta;no newcombinedfull-rowhashinvented.','Fiveexposedweeklyclusters/differentselecteddenominators/10candidate-generatedpicksdonotprovefutureorincumbentsuperiority.','Noindependentfit/rawchartingvintage/sportsbooksettlement/consumeradmissionorwebsitewrite.'],new_fits=0,new_forecast_inference=0,new_original_selected_picks=0,new_NFL_games=0,new_additional_scored_policy_week=1,production_writes=0,resources=dict(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu),code_sha256=sha(Path(__file__).read_bytes()))
    dest.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print(json.dumps(dict(state=result['state'],W4=result['new_W4']['control'],candidate=result['new_W4']['candidate'],cumulative=cumulative,membership=result['membership'],assertions=dict(N))))


if __name__=='__main__':main()
