"""New rolling archive panels using the existing side chooser and exact grader."""
from __future__ import annotations
import argparse,collections,csv,gzip,hashlib,json,resource,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2 import full_provider_prop_replay as shared
from nfl_v2 import recorded_prop_grading as pilot
from nfl_v2 import scoring
from nfl_v2.prop_evidence_metadata_v2 import object_spans_in_array

VERSION='v2-server-retained-per-game-T90-archive-selection-v2'
PROTOCOL_FILE='FROZEN_GRADING_PROTOCOL_V2.json'
TARGETS=shared.TARGETS


def savegz(path,obj):
    with path.open('xb')as f:f.write(gzip.compress(pilot.canonical(obj),mtime=0))


def prepare(a):
    if(a.public/PROTOCOL_FILE).exists():raise ValueError('preserve prior freeze')
    receipt=json.loads((a.public/'METADATA_QUALIFICATION_RECEIPT.json').read_bytes())
    meta=a.private/f'FROZEN_W{a.week}_METADATA.json.gz';assert pilot.sha(meta)==receipt['metadata_sha256']
    binding=dict(labels=str(a.labels),memberships=str(a.memberships))
    pilot.write(a.private/'GRADING_INPUT_BINDING_V2.json',binding)
    p=dict(protocol_id=VERSION+f':W{a.week}',registered_at_utc=pilot.now(),state='FROZEN_BEFORE_NEW_LABELS_POINTS_OR_GRADES',week=a.week,
      code_sha256=pilot.sha(__file__),shared_grader_sha256=pilot.sha(Path(shared.__file__)),core_scoring_sha256=pilot.sha(Path(scoring.__file__)),side_chooser_bootstrap_sha256=pilot.sha(Path(pilot.__file__)),
      metadata_receipt_sha256=pilot.sha(a.public/'METADATA_QUALIFICATION_RECEIPT.json'),metadata_sha256=receipt['metadata_sha256'],source_assignment_sha256=pilot.sha(a.public/'FROZEN_ROLLING_SOURCE_ASSIGNMENTS.json'),
      label_source_sha256=pilot.sha(a.labels),memberships_sha256=pilot.sha(a.memberships),private_binding_sha256=pilot.sha(a.private/'GRADING_INPUT_BINDING_V2.json'),
      panel='All frozen provider-labelled finite ordinary-stat thresholds, including original no-side records, missing labels and hard cases. NoNFLfitting/inference.',
      strategies=list(shared.STRATEGIES),points='Use exact finite saved props.adj and props.proj fields with no additional rounding; missing/nonfinite point means ABSTAIN only for that point strategy. Retain original saved side regardless of missing modelmetadata. Internal-unroundedP1 unavailable. raw field does not authenticate externalprovider algorithm.',
      original='Saved props.lean is original at that selected pregame capture. Null stays original ABSTAIN; other strategies are retrospective, never rewritten original picks.',
      labels='Reuse already qualified restored empirical target/outcome rows, exact2026week/game/GSIS/target/sourceposition; identical outcomes/participation across retained history/product/populationviews. Explicit numericcredits with positivephysicalappearance only; playedmissing andunknown distinct; no absentfieldzero/DNP inference.',
      cohorts='Sourcepositions/sourcebook/originalmarkedTop/selected-vs-abstained plus existing target-specific top10/15/20,bands/workload memberships. Reconstructedcohorts are diagnostic; admit earlier source maxavailability<=decisiontime and knownscheduledrankingcutoff=kickoff, otherwisemembershipunknown. Do not rankplayers fromoutcomes.',
      K='RETROSPECTIVE_ROLLING_K6/10/20 percategory/week/strategy and separateCombined/Over/Under pools. At each increasing source-clock batch, rank that batch eligible saved directions by abs(savedpoint-line) withincategory, stablecanonicalties; take up to remaining slots, never use later batches to revise prior selections. No fixedweeklyK or probability/EVranking claim. FreezeK beforelabels.',
      scoring='Reuse shared full_provider_prop_replay.grade/score_row/check_triplet, recorded_prop_grading.choose_side/bootstrap and scoring.threshold_crossing/grade_settlement; reidentify onlynewpanel/version metadata. ALLbooksettlementunresolved; prices/probs/EV/ROI/CLVnull.',
      exposure='Exposed research seasons. Snapshot selection uses serverclock only, not scores. Every new selection is retrospective unless saved original side. NoWeek8labels.',
      budget=dict(max_wall_seconds=180,max_RSS_bytes=1073741824,max_private_bytes=8388608,max_threads=1,new_fits=0,new_forecasts=0,new_inference=0))
    pilot.write(a.public/PROTOCOL_FILE,p);(a.public/'GRADING_SOURCE_SNAPSHOT_V2.py').write_bytes(Path(__file__).read_bytes())
    return dict(state=p['state'],week=a.week,protocol_sha256=pilot.sha(a.public/PROTOCOL_FILE))


def run(a):
    start=time.monotonic();p=json.loads((a.public/PROTOCOL_FILE).read_bytes())
    assert pilot.sha(__file__)==p['code_sha256']and pilot.sha(Path(shared.__file__))==p['shared_grader_sha256']and pilot.sha(Path(scoring.__file__))==p['core_scoring_sha256']
    assert pilot.sha(a.private/'GRADING_INPUT_BINDING_V2.json')==p['private_binding_sha256'];bindings=json.loads((a.private/'GRADING_INPUT_BINDING_V2.json').read_bytes())
    assert pilot.sha(bindings['labels'])==p['label_source_sha256']and pilot.sha(bindings['memberships'])==p['memberships_sha256']
    meta=a.private/f'FROZEN_W{a.week}_METADATA.json.gz';assert pilot.sha(meta)==p['metadata_sha256'];rows=json.loads(gzip.decompress(meta.read_bytes()))['rows']
    source_receipt=json.loads((a.public/'METADATA_QUALIFICATION_RECEIPT.json').read_bytes());byhead=collections.defaultdict(list)
    for r in rows:byhead[r['source_head']].append(r)
    for source in source_receipt['source_sources']:
        f=a.private/f'W{a.week}_SOURCE_{source["head_sha"]}.json';assert pilot.sha(f)==source['source_sha256'];wanted=collections.defaultdict(list)
        for r in byhead[source['head_sha']]:wanted[r['source_player_index']].append(r)
        for i,raw in enumerate(object_spans_in_array(f.read_text(),'players')):
            if i not in wanted:continue
            player=json.loads(raw)
            for r in wanted[i]:
                q=player['props'][r['source_prop_index']]
                assert(str(player['id']),player['pos'],str(player['game_id']),q['key'],q['line'],q.get('lean'),q['line_from'])==(r['source_player_id'],r['position'],r['source_game_id'],r['target'],r['line'],r['original_side'],r['line_from'])
                r.update(prediction=q.get('adj')if scoring.finite(q.get('adj'))else None,raw_prediction=q.get('proj')if scoring.finite(q.get('proj'))else None,source_cohorts=[],population=None)
    memberships=json.loads(gzip.decompress(Path(bindings['memberships']).read_bytes()));member=collections.defaultdict(list)
    for m in memberships:member[tuple(m['key'][:3])].append(m)
    for r in rows:
        eligible=[m for m in member.get((r['game_id'],r['player_id'],r['target']),[])if(m.get('latest_available')is None or m['latest_available']<=pilot.aware(r['source_server_clock']).timestamp())and m.get('ranking_cutoff')==pilot.aware(r['kickoff']).timestamp()]
        cohorts={tuple(m['cohorts'])for m in eligible};r['source_cohorts']=list(next(iter(cohorts)))if len(cohorts)==1 else[]
    # Freeze the whole rolling pick rule before any new actual is decoded.
    ks=[]
    for strategy in shared.STRATEGIES:
        source=[]
        for r in rows:
            point=r['raw_prediction']if strategy==shared.RAW else r['prediction'];s=pilot.choose_side(dict(r,prediction=point),strategy if strategy in('original','alwaysOver','alwaysUnder')else'P1')
            if s:source.append(dict(r,selected_side=s,ranking_point=point))
        for target in TARGETS:
            tt=[r for r in source if r['target']==target]
            for scope in('Combined','over','under'):
                pool=[r for r in tt if scope=='Combined'or r['selected_side']==scope]
                for k in(6,10,20):
                    chosen=[]
                    for clock in sorted({r['source_server_clock']for r in pool}):
                        chosen.extend(sorted((r for r in pool if r['source_server_clock']==clock),key=shared.rank_key)[:max(0,k-len(chosen))])
                    ks.append(dict(strategy=strategy,target=target,rank_scope=scope,K=k,source_row_indices=[r['source_row_index']for r in chosen],eligible_pool_n=len(pool)))
    savegz(a.private/'FROZEN_ROLLING_K_MEMBERSHIPS.json.gz',dict(rows=ks));savegz(a.private/'FROZEN_POINT_AND_COHORT_INPUTS.json.gz',dict(rows=rows))
    pilot.write(a.public/'K_MEMBERSHIP_FREEZE_RECEIPT.json',dict(state='FROZEN_BEFORE_LABEL_DECODE',membership_sha256=pilot.sha(a.private/'FROZEN_ROLLING_K_MEMBERSHIPS.json.gz'),point_cohort_sha256=pilot.sha(a.private/'FROZEN_POINT_AND_COHORT_INPUTS.json.gz'),lists=len(ks),new_grades=0))
    wanted={(r['game_id'],r['player_id'],r['target'],r['position'])for r in rows};labels=collections.defaultdict(list)
    with gzip.open(bindings['labels'],'rt')as f:
        for v in csv.DictReader(f):
            if(v['season'],v['week'])!=('2026',str(a.week)):continue
            key=tuple(v[k]for k in('game_id','player_id','target','position'))
            if key in wanted:labels[key].append((v['actual'],v['participation'],v['population']))
    states=collections.Counter()
    for r in rows:
        vv=labels.get((r['game_id'],r['player_id'],r['target'],r['position']),[]);actuals={float(x)for x,s,pop in vv if x!=''};parts={s for x,s,pop in vv};pops={pop for x,s,pop in vv}
        if len(actuals)>1 or len(parts)>1:raise ValueError('retained label views conflict')
        played=parts=={'played'};actual=next(iter(actuals))if played and len(actuals)==1 else None
        if actual is not None and not actual.is_integer():raise ValueError('ordinary integer-valued label contract violated')
        state='SUPPORTED'if actual is not None else'MISSING_ACTUAL'if played else'APPEARANCE_UNKNOWN'
        r.update(actual=actual,label_state=state,participation='VERIFIED_PLAYED_POSITIVE_PHYSICAL'if played else'UNKNOWN',population='primary'if'primary'in pops else'extended'if'extended'in pops else None,price=None,probability=None)
        states[state]+=1
    savegz(a.private/'JOINED_ROWS.json.gz',dict(schema=VERSION,rows=rows));grades=shared.grade(rows);savegz(a.private/'GRADED_ROWS.json.gz',dict(schema=VERSION,rows=grades))
    scores=[];checks=[]
    def record(rr,pool,strategy,target,cohort,side,K=None,scope=None,rankn=None):
        s=shared.score_row(rr,pool,strategy=strategy,target=target,cohort=cohort,side=side,K=K,rank_scope=scope,rank_eligible=rankn)
        ident=[VERSION,a.week,strategy,target,cohort,side,K,scope];s.update(record_id='ROLLING-PROP-'+hashlib.sha256(pilot.canonical(ident)).hexdigest()[:24],procedure_id=VERSION+':'+strategy,week=a.week,evaluation_weeks=[a.week],time_panel_id=f'2026_W{a.week}_FULL14_PER_GAME_SERVER_BEFORE_T90',evaluation_panel_id=VERSION+f':W{a.week}',horizon_id='PER_GAME_LATEST_SERVER_RETAINED_BEFORE_T90_QUOTE_AGE_UNKNOWN',selection_evidence='ORIGINAL_RECORDED_SELECTION'if strategy=='original'and K is None else'RETROSPECTIVE_RULE_REPLAY')
        if K is not None:s['rolling_selection_policy']='CHRONOLOGICAL_BATCH_FIRST_REMAINING_SLOTS_WITHIN_CATEGORY'
        return s
    for strategy in shared.STRATEGIES:
        for target in('ALL',)+TARGETS:
            tt=[r for r in grades if r['strategy']==strategy and(target=='ALL'or r['target']==target)]
            for cohort in shared.cohort_names(grades):
                pool=[r for r in tt if shared.in_cohort(r,cohort)];selected=[r for r in pool if r['selected_side']];trip=[]
                for side in('over','under','Combined'):trip.append(record([r for r in selected if side=='Combined'or r['selected_side']==side],pool,strategy,target,cohort,side))
                shared.check_triplet(trip);scores.extend(trip);checks.append([strategy,target,cohort])
    lookup={(r['strategy'],r['source_row_index']):r for r in grades}
    for k in ks:
        pool=[r for r in grades if r['strategy']==k['strategy']and r['target']==k['target']];chosen=[lookup[k['strategy'],i]for i in k['source_row_indices']];trip=[]
        for side in('over','under','Combined'):trip.append(record([r for r in chosen if side=='Combined'or r['selected_side']==side],pool,k['strategy'],k['target'],'RETROSPECTIVE_ROLLING_K',side,k['K'],k['rank_scope'],k['eligible_pool_n']))
        shared.check_triplet(trip);scores.extend(trip)
    if time.monotonic()-start>180 or resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>1073741824 or sum(f.stat().st_size for f in a.private.rglob('*')if f.is_file())>8388608:raise RuntimeError('bounded shared-core replay limit')
    pilot.write(a.public/'SCORES.json',scores);pilot.write(a.public/'SIDE_RECONCILIATION.json',dict(state='PASS',triplets=len(scores)//3,all_actual_selected_side_partitions=True))
    pilot.write(a.public/'RUN_RECEIPT.json',dict(state='COMPLETE_REGISTERED_ROLLING_ORIGINAL_AND_SAVED_CONTROL_SCOPE',protocol_sha256=pilot.sha(a.public/PROTOCOL_FILE),outer_rows=len(rows),games=len({r['game_id']for r in rows}),label_states=dict(states),strategy_grade_rows=len(grades),score_views=len(scores),score_sha256=pilot.sha(a.public/'SCORES.json'),private_join_sha256=pilot.sha(a.private/'JOINED_ROWS.json.gz'),private_grades_sha256=pilot.sha(a.private/'GRADED_ROWS.json.gz'),private_bytes=sum(f.stat().st_size for f in a.private.rglob('*')if f.is_file()),wall_seconds=time.monotonic()-start,max_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,new_fits=0,new_forecasts=0,new_inference=0,Week8_outcomes_read=0))
    print(json.dumps([dict(strategy=s['strategy'],side=s['side'],selected=s['forecast_rows'],n=s['n'],WIN=s['selection_metrics']['WIN'],LOSS=s['selection_metrics']['LOSS'],hit=s['selection_metrics']['hit_rate'])for s in scores if s['target']=='ALL'and s['cohort_id']=='ALL']))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['prepare','run']);p.add_argument('--week',type=int,required=True);p.add_argument('--public',type=Path,required=True);p.add_argument('--private',type=Path,required=True);p.add_argument('--labels',type=Path);p.add_argument('--memberships',type=Path);a=p.parse_args();print(prepare(a))if a.mode=='prepare'else run(a)
