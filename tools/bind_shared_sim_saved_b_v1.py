"""Join frozen B outputs to website-admitted cases, without outcomes or fitting.

Private plans bind already-retained bodies. Output ordinals refer to the exact
canonical case file; raw identities, lines and source/training rows are excluded.
This is not a grader or simulator. C retains the one canonical grade join.
"""
from __future__ import annotations
import argparse,collections,csv,datetime,gzip,hashlib,json,math,pathlib,resource,time
from zoneinfo import ZoneInfo

def canonical(x):
    return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def sha(b):return hashlib.sha256(b).hexdigest()
def finite(v):
    try:return v not in (None,'') and not isinstance(v,bool) and math.isfinite(float(v))
    except (TypeError,ValueError):return False
def number(v):return float(v) if finite(v) else None
def team_key(v):return 'LAR' if v=='LA' else v
def epoch(v):
    if finite(v):return float(v)
    if isinstance(v,str) and v:
        try:return datetime.datetime.fromisoformat(v.replace('Z','+00:00')).timestamp()
        except ValueError:return None
    return None
CSV_RELEVANT_KEYS=set()
CSV_PROJECTED_CACHE={}
def matches(row,select):
    for k,v in select.items():
        if isinstance(v,list):
            if row.get(k) not in v:return False
        elif k=='season':
            if str(row.get(k))!=str(v):return False
        elif row.get(k)!=v:return False
    return True
def projection(row,arm):
    """Only fields consumed by lookup, never target outcomes/support scores."""
    names=('season','week','game_id','player_id','target','position','team',
           'opponent','history_regime','population','run_id','procedure_id',
           'method','objective','product_id','product','policy_id','information_group',
           'prediction','mean','lower_median','law','fallback','status','blocked_reason',
           'cutoff','fit_cutoff','feature_cutoff','latest_feature_available',
           'latest_source_available','kickoff')
    return {k:row.get(k) for k in names if k in row}
def forecast_rows(packet):
    if 'CSV' in packet['serializer']:
        key=packet['sha256']
        if key not in CSV_PROJECTED_CACHE:
            selected=[]
            with gzip.open(packet['local'],'rt',newline='') as handle:
                for row in csv.DictReader(handle):
                    identity=(str(row.get('game_id')),str(row.get('player_id')),row.get('target'))
                    if identity in CSV_RELEVANT_KEYS:selected.append(projection(row,None))
            CSV_PROJECTED_CACHE[key]=selected
        yield from CSV_PROJECTED_CACHE[key]
    else:
        from nfl_v2.shared_subgroups import packet_rows
        yield from packet_rows(packet['local'])
def law_probabilities(payload,line):
    from nfl_v2.player_context_matchup import CountLaw,exact_probabilities
    from nfl_v2.distribution_laws import Law
    kind=payload.get('kind')
    if kind=='gamma_poisson_count':law=CountLaw(payload['mean'],payload['shape'])
    elif kind=='leaf_mixture':
        law=Law('mixture',support=payload['support'],weights=payload['weights'],
                prior=Law(**payload['prior']),mixture=payload['mixture'])
    elif kind in ('zero','poisson','geometric','signed','bernoulli'):
        law=Law(**payload)
    else:raise ValueError('Unregistered saved law kind: '+str(kind))
    p=exact_probabilities(law,float(line))
    if not all(math.isfinite(v) and -1e-12<=v<=1+1e-12 for v in p.values()):
        raise ValueError('Invalid exact saved probabilities')
    if abs(sum(p.values())-1)>1e-12:raise ValueError('Saved law mass')
    return p
def prior_identity_maps(identity):
    """Rebuild strict earlier-event-week stable IDs; ignore team/availability."""
    source=identity['source_bindings']['roster'];path=pathlib.Path(source['local_path'])
    b=path.read_bytes()
    if len(b)!=source['bytes'] or sha(b)!=source['sha256']:raise ValueError('Roster bytes')
    import io
    rows=list(csv.DictReader(io.StringIO(gzip.decompress(b).decode())))
    # Header spelling is the explicit source contract, never names/fuzzy matching.
    source_field=identity.get('frame_player_id_source_field')
    if source_field!='sleeper_id':raise ValueError('Canonical website player namespace must be explicitly Sleeper')
    if not rows or not {'season','week','game_type',source_field,'gsis_id'}<=set(rows[0]):raise ValueError('Roster schema')
    out={}
    for week in range(4,10):
        pairs=collections.defaultdict(set);reverse=collections.defaultdict(set)
        for r in rows:
            if str(r.get('season'))!='2026' or r.get('game_type')!='REG' or not r.get('week') or int(r['week'])>=week:continue
            espn,gsis=r.get(source_field),r.get('gsis_id')
            if not espn or not gsis:continue
            pairs[str(espn)].add(gsis);reverse[gsis].add(str(espn))
        from nfl_v2.identity import unique_gsis_bridge
        out[week]=unique_gsis_bridge([(k,z) for k,v in pairs.items() for z in v],source_id='B_RETAINED_PRIOR_EVENT_WEEK_SLEEPER_GSIS_RECONSTRUCTION')
    return out
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for key in ('plan','cases','identity','freeze','output','report'):ap.add_argument('--'+key,required=True,type=pathlib.Path)
    args=ap.parse_args();cpu=time.process_time();wall=time.monotonic()
    plan_bytes=args.plan.read_bytes();plan=json.loads(plan_bytes);freeze=json.loads(args.freeze.read_bytes())
    if sha(plan_bytes)!=freeze['private_plan_sha256']:raise ValueError('Private plan freeze')
    case_bytes=args.cases.read_bytes()
    if sha(case_bytes)!='19ccf34b3037e1790ee3b2bf61d3357f33e63916779c2f36023a232f6a66ea18':raise ValueError('Canonical case freeze')
    cases=[json.loads(line) for line in case_bytes.splitlines()]
    if len(cases)!=3474 or len({r['case_id'] for r in cases})!=3474:raise ValueError('Full canonical frame')
    identity_bytes=args.identity.read_bytes()
    if sha(identity_bytes)!=freeze['private_identity_body_sha256']:raise ValueError('Unfrozen identity adapter body')
    identity=json.loads(identity_bytes);idmaps=prior_identity_maps(identity)
    schedule=identity['source_bindings']['schedule'];sbytes=pathlib.Path(schedule['local_path']).read_bytes()
    if len(sbytes)!=schedule['bytes'] or sha(sbytes)!=schedule['sha256']:raise ValueError('Schedule bytes')
    import io
    text=gzip.decompress(sbytes).decode() if sbytes[:2]==b'\x1f\x8b' else sbytes.decode()
    game_map={}
    for row in csv.DictReader(io.StringIO(text)):
        if row.get('season')!='2026' or row.get('game_type')!='REG' or not row.get('week') or not 4<=int(row['week'])<=9 or not row.get('espn'):continue
        event=str(row['espn']);value={k:row[k] for k in ('game_id','season','game_type','week','gameday','gametime','away_team','home_team')}
        if event in game_map and game_map[event]!=value:raise ValueError('Ambiguous retained event map')
        game_map[event]=value
    if game_map!=identity['ESPN_game_to_canonical_game']:raise ValueError('Identity map differs from verified schedule body')
    bridges={};bridge_counts=collections.Counter();dual=[]
    for ordinal,case in enumerate(cases):
        i=case['identity'];g=game_map.get(str(i['game_id']));p=idmaps[int(i['week'])].get(str(i['player_id']))
        reason=None
        if not g:reason='MISSING_EXPLICIT_EVENT_ID'
        elif int(g['week'])!=int(i['week']) or g['game_type']!='REG':reason='EVENT_WEEK_CONFLICT'
        elif {team_key(g['home_team']),team_key(g['away_team'])}!={team_key(i['team']),team_key(i['opponent'])}:reason='EVENT_TEAMS_CONFLICT'
        elif not p:reason='MISSING_PRIOR_EXPLICIT_PLAYER_ID'
        if reason:bridges[ordinal]={'reason':reason};bridge_counts[reason]+=1;continue
        native=datetime.datetime.fromisoformat(g['gameday']+'T'+g['gametime']).replace(tzinfo=ZoneInfo('America/New_York')).timestamp()
        canonical_kickoff=epoch(case['kickoff_utc'])
        if canonical_kickoff is None:raise ValueError('Missing canonical schedule clock')
        difference=native-canonical_kickoff
        if difference:dual.append({'week':int(i['week']),'difference_seconds':difference})
        bridges[ordinal]={'key':(g['game_id'],p,i['category']),'native_kickoff':native,'canonical_kickoff':canonical_kickoff,'reason':None}
        bridge_counts['EXACT_CURRENT_VINTAGE_IDENTITY']+=1
    hash_verified={};source_stats={};results=[];summaries=[];consumed=hashlib.sha256();source_rows=collections.Counter()
    CSV_RELEVANT_KEYS.update(v['key'] for v in bridges.values() if not v['reason'])
    if args.output.exists() or args.report.exists():raise ValueError('Fresh outputs required')
    for arm in plan['candidates']:
        relevant=[(j,r) for j,r in enumerate(cases) if r['identity']['category']==arm['category']]
        wanted={bridges[j]['key'] for j,r in relevant if not bridges[j]['reason']}
        saved=collections.defaultdict(list)
        if relevant and not arm['law_blocked']:
            for packet in arm['packets']:
                path=pathlib.Path(packet['local']);st=path.stat();marker=(str(path),st.st_size,st.st_mtime_ns)
                if marker not in hash_verified:
                    raw=path.read_bytes()
                    if len(raw)!=packet['bytes'] or sha(raw)!=packet['sha256']:raise ValueError('Saved body commitment')
                    hash_verified[marker]=packet['sha256'];del raw
                elif hash_verified[marker]!=packet['sha256']:raise ValueError('Conflicting body commitments')
                source_stats[str(path)]=(st.st_size,st.st_mtime_ns)
                for row in forecast_rows(packet):
                    if not matches(row,arm['selectors']):continue
                    week=int(row['week'])
                    if not 4<=week<=9:continue
                    key=(str(row.get('game_id')),str(row.get('player_id')),row.get('target'))
                    if key not in wanted:continue
                    clean=projection(row,arm);consumed.update(canonical([arm['candidate_id'],clean]));source_rows[arm['candidate_id']]+=1
                    saved[key].append(clean)
        output=[];counts=collections.Counter();weekly={w:collections.Counter() for w in range(4,10)}
        for ordinal,case in relevant:
            i=case['identity'];bridge=bridges[ordinal];r={'case_ordinal':ordinal,'status':None,'point':None,'mean_sibling':None,'median_sibling':None,'probabilities':None,'fallback':None,'source_clock_state':None,'primary_T90_comparability':'NOT_ESTABLISHED'}
            if arm['law_blocked']:r['status']='LAW_QUERY_BINDING_REQUIRED'
            elif bridge['reason']:r['status']=bridge['reason']
            elif i['position'] not in arm['roles']:r['status']='UNSUPPORTED_ROLE'
            else:
                candidates=[]
                for row in saved.get(bridge['key'],[]):
                    if int(row['week'])!=int(i['week']):continue
                    if row.get('position') not in (None,'',i['position']):continue
                    if team_key(row.get('team')) not in (None,'',team_key(i['team'])):continue
                    if team_key(row.get('opponent')) not in (None,'',team_key(i['opponent'])):continue
                    candidates.append(row)
                # Duplicate views can collapse only when all consumed forecast fields agree.
                unique={canonical(row):row for row in candidates}
                if len(unique)>1:r['status']='CONFLICTING_SAVED_OUTPUTS'
                elif not unique:r['status']='MISSING_FROZEN_ORIGIN_OR_QUERY'
                else:
                    row=next(iter(unique.values()));kickoff=min(bridge['native_kickoff'],bridge['canonical_kickoff']);deadline=kickoff-90*60
                    origins=[epoch(row.get(k)) for k in ('cutoff','fit_cutoff','feature_cutoff')]
                    origins=[v for v in origins if v is not None]
                    observed=[epoch(row.get(k)) for k in ('latest_feature_available','latest_source_available')]
                    observed=[v for v in observed if v is not None]
                    # An origin/filter cutoff is not an observed publication clock.
                    # Preserve B's original kickoff-left-limit product. A mismatch
                    # with C's T90 is an explicit comparison limit, never silently
                    # promoted to common-horizon evidence or mistaken for no output.
                    if any(v>kickoff+1e-8 for v in origins+observed):r['status']='SOURCE_CANONICAL_KICKOFF_CLOCK_CONFLICT'
                    elif row.get('blocked_reason'):r['status']='SAVED_SOURCE_BLOCKED'
                    else:
                        r['source_clock_state']='DECLARED_KICKOFF_LEFT_LIMIT;OBSERVED_LATEST_BEFORE_T90' if observed and all(v<=deadline for v in observed) else 'DECLARED_KICKOFF_LEFT_LIMIT;SOURCE_AVAILABILITY_PARTIAL_OR_NOT_T90'
                        r['primary_T90_comparability']='ORIGINAL_ORIGIN_DIFFERS;C_ADMISSION_REQUIRED' if any(v>deadline for v in origins) else 'CLOCK_FIELDS_NOT_SUFFICIENT_FOR_AUTHENTICATION'
                        r['fallback']=row.get('fallback')
                        r['mean_sibling']=number(row.get('mean'))
                        r['median_sibling']=number(row.get('lower_median'))
                        if arm['modern']:
                            payload=row.get('law')
                            if not isinstance(payload,dict):r['status']='EXPLICIT_LAW_MISSING'
                            else:
                                r['probabilities']=law_probabilities(payload,i['line'])
                                r['point']=number(row.get('mean')) if arm['output']=='mean' else None
                                r['status']='AVAILABLE' if arm['output']!='mean' or r['point'] is not None else 'NONFINITE_SAVED_POINT'
                        else:
                            r['point']=number(row.get(arm['point_field']))
                            r['status']='AVAILABLE' if r['point'] is not None else 'NONFINITE_SAVED_POINT'
            counts[r['status']]+=1;weekly[int(i['week'])][r['status']]+=1
            if r['status']=='AVAILABLE':
                f=r['fallback'];attribution='RECORDED_NO_FALLBACK' if f=='none' else 'FALLBACK_ATTRIBUTION_UNKNOWN' if f in (None,'') else 'RECORDED_FALLBACK'
                counts[attribution]+=1;weekly[int(i['week'])][attribution]+=1
            output.append(r)
        results.append({'candidate_id':arm['candidate_id'],'category':arm['category'],'exact_procedure_id':arm['procedure'],'primary_output':arm['output'],'rows':output})
        summaries.append({'candidate_id':arm['candidate_id'],'category':arm['category'],'primary_output':arm['output'],'eligible_category_cases':len(relevant),'counts':dict(counts),'weekly':[{'week':w,'counts':dict(weekly[w])} for w in range(4,10)],'graded':False,'actual_line_scored_weeks':[]})
        if time.process_time()-cpu>75 or time.monotonic()-wall>1200:raise RuntimeError('Conservative B join completion-reserve stop')
    for path,stat in source_stats.items():
        st=pathlib.Path(path).stat()
        if (st.st_size,st.st_mtime_ns)!=stat:raise ValueError('Saved input changed during lookup')
    payload={'schema':'B-SHARED-SIM-ORDINAL-SAVED-FORECASTS-v1','state':'FORECAST_BINDINGS_ONLY_NOT_GRADED','canonical_case_sha256':sha(case_bytes),'full_case_count':3474,'outcome_contract':'Websitev1; unknowns not loaded or filtered','freeze_sha256':sha(args.freeze.read_bytes()),'output_semantics':'Only exact own B derived forecasts/availability keyed by canonical case ordinal. No source identities/line/book/outcome/roster/training/context/model state. Non-category cases are NOT_APPLICABLE in the full frame.','candidates':results}
    out=gzip.compress(canonical(payload)+b'\n',mtime=0);args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_bytes(out)
    if gzip.decompress(args.output.read_bytes())!=canonical(payload)+b'\n':raise ValueError('Independent disk reopen')
    report={'id':'B-SHARED-SIM-CANONICAL-SAVED-JOIN-v1','state':'COMPLETED_UNGRADED_SAVED_OUTPUT_BINDINGS','UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'canonical_case_sha256':sha(case_bytes),'full_frame':3474,'known_unknown_outcomes_not_consumed':464,'new_fits':0,'new_SIM_trajectories':0,'new_grades':0,'identity_source_scope':'Current-vintage exact IDs using strictly prior REG event-week roster identity links only. No name match/status/absence inference; not authenticated pregame vintage.','identity_counts':dict(bridge_counts),'dual_clock_case_counts':dict(collections.Counter(str(x['difference_seconds']) for x in dual)),'packet_bodies_verified':len(hash_verified),'candidate_count':len(summaries),'candidate_summaries':summaries,'source_rows_projected':dict(source_rows),'consumed_forecast_projection_sha256':consumed.hexdigest(),'output':{'bytes':len(out),'sha256':sha(out),'local_reopen':'PASS','public_disclosure':'PENDING_EXACT_CONTENT_REVIEW;not automatically protected-input publication'},'resource':{'CPU_seconds':time.process_time()-cpu,'wall_seconds':time.monotonic()-wall,'peak_RSS_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'metering_limit':'Controlled worker process only; task preparation/reporting/controller accounted separately.'},'C_worker_checks':'NOT_RUN;this saved-output join is not Cworker mutation/conservation/fit reproduction','original_reproduction_failures':'FAILED_UNCHANGED','C_admission':'PENDING'}
    args.report.write_bytes(canonical(report)+b'\n')
    print(json.dumps({'state':report['state'],'candidate_count':len(summaries),'available_case_procedure_bindings':sum(x['counts'].get('AVAILABLE',0) for x in summaries),'CPU_seconds':report['resource']['CPU_seconds'],'wall_seconds':report['resource']['wall_seconds'],'output_bytes':len(out),'new_grades':0}))
if __name__=='__main__':main()
