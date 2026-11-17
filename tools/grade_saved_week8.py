"""Versioned Week8 saved-row adapters using V2's existing scoring engine."""
from __future__ import annotations
import argparse, collections, csv, gzip, hashlib, json, math, sys
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from nfl_v2 import scoring, full_provider_prop_replay as shared
from nfl_v2.identity import unique_gsis_bridge
from nfl_v2.recorded_prop_grading import canonical
from nfl_v2 import chart_sources
from nfl_v2.precision_grid import chart_median_precision

VERSION='v2-saved-week8-partial-grading-v1'
TARGETS=tuple(scoring.TARGETS)
ORDINARY=shared.TARGETS
FIELDS={'pass_yd':'passing_yards','pass_td':'passing_tds','pass_cmp':'completions',
        'pass_att':'attempts','pass_int':'passing_interceptions','rush_yd':'rushing_yards',
        'rush_att':'carries','rec':'receptions','rec_yd':'receiving_yards'}
def now():return datetime.now(timezone.utc).isoformat()
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_bytes())
def save(path,value):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    with Path(path).open('x')as f:json.dump(value,f,indent=2,allow_nan=False);f.write('\n')
def savegz(path,value):
    with Path(path).open('xb')as f:f.write(gzip.compress(canonical(value),mtime=0))
def aware(value):return datetime.fromisoformat(value.replace('Z','+00:00'))
def finite(value):return scoring.finite(value)
def number(row,key):
    try:value=float(row[key])
    except (KeyError,ValueError,TypeError):return None
    return value if math.isfinite(value)else None


class Labels:
    def __init__(self,private):
        self.private=private;self.games={r['game_id']:r for r in csv.DictReader((private/'source-labels/fresh-games.csv').open())if(r['season'],r['game_type'],r['week'])==('2026','REG','8')}
        self.by_espn={str(r['espn']):k for k,r in self.games.items()}
        schedule=read(ROOT/'reports/week8-grading-20261102l/FROZEN_SOURCE_ASSIGNMENTS_V1.json')['assignments']
        self.frozen={r['game_id']:r for r in schedule}
        assert set(self.games)==set(self.frozen)
        self.events={e['id']:e for e in read(private/'source-labels/espn-week8-scoreboard-v2.json')['events']}
        self.status={};self.status_rows=[]
        for gid,g in self.games.items():
            event=self.events.get(g['espn']);kind=event['status']['type']if event else{}
            state='FINAL'if kind.get('completed')is True and kind.get('state')=='post'else'PENDING'if kind.get('state')in('pre','in')else'UNVERIFIED'
            if event:
                assert aware(event['date'])==aware(self.frozen[gid]['kickoff_utc'])
                if state=='FINAL':
                    scores={c['homeAway']:float(c['score'])for c in event['competitions'][0]['competitors']}
                    assert scores=={'home':float(g['home_score']),'away':float(g['away_score'])}
            self.status[gid]=state
            self.status_rows.append(dict(game_id=gid,espn_game_id=g['espn'],kickoff_utc=self.frozen[gid]['kickoff_utc'],state=state,source_finality=kind.get('name'),overtime=kind.get('detail')))
        self.stats={}
        for r in csv.DictReader((private/'source-labels/fresh-player-stats-2026.csv').open()):
            if(r['season'],r['week'],r['season_type'])!=('2026','8','REG'):continue
            gid=r['game_id'];assert gid in self.games
            g=self.games[gid];assert{r['team'],r['opponent_team']}=={g['home_team'],g['away_team']}
            key=gid,r['player_id'];assert key not in self.stats
            self.stats[key]=r
        chart=ROOT/'reports/week8-grading-20261102l/CHART_WEEK8_SOURCE_ADMISSION_V1.json'
        self.chart_admission=read(chart)if chart.exists()else None
        if self.chart_admission:
            assert sha(private/'source-labels/fresh-player-stats-2026.csv')==self.chart_admission['csv_sha256']
            assert self.chart_admission['all_csv_cells_match']is True and self.chart_admission['supported_weeks']==[8]
        binding=read(private/'LOCAL_INPUT_BINDINGS_V1.json');self.binding=binding
        assert sha(binding['identity_roster'])==binding['identity_roster_sha256']
        with gzip.open(binding['identity_roster'],'rt')as f:
            self.bridge=unique_gsis_bridge([(r['sleeper_id'],r['gsis_id'])for r in csv.DictReader(f)if r['season']=='2026'and int(r['week'])<=8 and r['sleeper_id']and r['gsis_id']],source_id='PRECAPTURE_WEEK8_IDENTITY_ONLY')
    def identity(self,player):
        player=str(player)
        return player if player.startswith('00-')else self.bridge.get(player)
    def game(self,game):return self.by_espn.get(str(game),str(game)if str(game)in self.games else None)
    def label(self,gid,pid,target):
        state=self.status.get(gid,'UNVERIFIED')
        if state=='PENDING':return dict(actual=None,participation='UNKNOWN',label_state='PENDING',outcome_state='pending')
        if state!='FINAL':return dict(actual=None,participation='UNKNOWN',label_state='UNVERIFIED_FINALITY',outcome_state='final')
        r=self.stats.get((gid,pid))
        if not r:return dict(actual=None,participation='UNKNOWN',label_state='IDENTITY_UNRESOLVED'if pid is None else'PARTICIPATION_UNKNOWN_NO_STAT_ROW',outcome_state='final')
        physical=any((number(r,k)or 0)>0 for k in('attempts','carries','targets','receptions','punt_returns','kickoff_returns'))
        if not physical:return dict(actual=None,participation='UNKNOWN',label_state='PARTICIPATION_NOT_ESTABLISHED_BY_PHYSICAL_CREDIT',outcome_state='final')
        if target in FIELDS:value=number(r,FIELDS[target])
        elif target=='rush_rec_yd':
            a,b=number(r,'rushing_yards'),number(r,'receiving_yards');value=a+b if a is not None and b is not None else None
        elif target=='anytime_td':
            a,b=number(r,'rushing_tds'),number(r,'receiving_tds');value=float(a+b>=1)if a is not None and b is not None else None
        elif target=='nick-chart-ppr-v1'and self.chart_admission:
            components={k:chart_sources._integer(r.get(field),signed=k in chart_sources.SIGNED_YARDS)for k,field in chart_sources.FIELDS.items()}
            f=chart_sources._integer(r.get('fumble_recovery_tds'));s=chart_sources._integer(r.get('special_teams_tds'))
            components.update({k:0 if f==s==0 else None for k in chart_sources.RARE})
            exact=scoring.chart_points_exact(components);value=float(exact)if exact is not None else None
        else:value=None
        if value is not None:assert scoring.valid_actual(target,value)
        return dict(actual=value,participation='VERIFIED_PLAYED_POSITIVE_PHYSICAL',label_state='SUPPORTED'if value is not None else'PLAYED_MISSING_EXACT_CHART_COMPONENTS'if target=='nick-chart-ppr-v1'else'PLAYED_MISSING_TARGET',outcome_state='final')


def base_row(labels,*,game,player,target,line,point,raw,side,index,position=None,**extra):
    gid=labels.game(game);pid=labels.identity(player)
    row=dict(source_row_index=index,source_player_id=str(player),source_game_id=str(game),game_id=gid,player_id=pid,
             target=target,position=position,line=line,prediction=point if finite(point)else None,raw_prediction=raw if finite(raw)else None,
             side=side,original_side=side,source_cohorts=[],top_over=False,top_under=False,line_from=None,
             season=2026,week=8,kickoff=labels.frozen[gid]['kickoff_utc']if gid else None,price=None,probability=None)
    row.update(extra);row.update(labels.label(gid,pid,target));return row


def aggregate(grades,*,panel,method,track,cohort='ALL',strategy='original',pool=None):
    result=[]
    for target in TARGETS:
        tt=[r for r in grades if r['target']==target];universe=tt if pool is None else[r for r in pool if r['target']==target]
        selected=[r for r in tt if r.get('selected_side')];trip=[]
        for side in('over','under','Combined'):
            rr=[r for r in selected if side=='Combined'or r['selected_side']==side]
            row=shared.score_row(rr,universe,strategy=strategy,target=target,cohort=cohort,side=side)
            ident=[VERSION,panel,method,track,cohort,strategy,target,side]
            row.update(record_id='W8-PROP-'+hashlib.sha256(canonical(ident)).hexdigest()[:24],procedure_id=method,
                       evaluation_panel_id=panel,time_panel_id='2026_W8_PARTIAL_FINAL_GAMES_ASOF',season=2026,week=8,
                       evaluation_seasons=[2026],evaluation_weeks=[8],evidence_track=track,
                       source_vintage='AUTHENTIC_RETAINED_PREGAME_RECORDS_CURRENT_VINTAGE_FINAL_LABELS',
                       horizon_id=panel,whole_week_complete=False,grading_version=VERSION,
                       selection_evidence='ORIGINAL_RECORDED_SELECTION'if track=='A_ORIGINAL'else'RETROSPECTIVE_RULE_REPLAY',
                       evidence='REPRODUCED_FROM_DATA')
            trip.append(row)
        shared.check_triplet(trip);result.extend(trip)
    return result


def wide(scores):
    groups=collections.defaultdict(dict)
    for r in scores:groups[r['evaluation_panel_id'],r['procedure_id'],r['strategy'],r['cohort_id'],r['target']][r['side']]=r
    result=[]
    for key,ss in sorted(groups.items()):
        r=dict(zip(('panel','procedure_id','strategy','cohort','target'),key))
        for side,prefix in(('over','over'),('under','under'),('Combined','combined')):
            v=ss[side];m=v['selection_metrics'];r.update({prefix+'_selected':v['forecast_rows'],prefix+'_wins':m['WIN'],prefix+'_losses':m['LOSS'],prefix+'_decided':v['n'],prefix+'_hit_rate':m['hit_rate']})
        c=ss['Combined'];m=c['selection_metrics'];r.update(eligible=m['selection_pool_count'],abstentions=m['abstentions_outside_selected_partition'],coverage=m['selection_coverage'],
                pending=m['status_counts']['PENDING'],push=m['PUSH'],unknown=m['status_counts']['UNKNOWN_PARTICIPATION'],missing_actual=m['status_counts']['MISSING_ACTUAL'],void=m['status_counts']['VOID'],
                unresolved_settlement=c['forecast_rows'],unique_games=c['unique_games'],uncertainty=m['game_uncertainty'])
        result.append(r)
    return result


def write_csv(path,rows):
    fields=list(dict.fromkeys(k for r in rows for k in r))
    with path.open('x',newline='')as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for r in rows:w.writerow({k:json.dumps(v,separators=(',',':'))if isinstance(v,(dict,list))else v for k,v in r.items()})


def run_original(private,public):
    out=public/'original-v1';out.mkdir(exist_ok=False);labels=Labels(private)
    assignment=read(public/'FROZEN_SOURCE_ASSIGNMENTS_V1.json');proofs={r['head']:r for r in assignment['proofs']}
    boards={h:read(private/f'source-metadata/board-{h}.json')for h in proofs}
    source=private/'source-metadata';board_rows=[];stats=collections.Counter()
    for a in assignment['assignments']:
        proof=a['selected_source']
        if proof is None:continue
        board=boards[proof['head']];assert(board['season'],board['week'])==(2026,8)
        tops={side:{(str(r.get('player_id')),str(r.get('game_id')),r.get('key'))for r in board.get('picks',{}).get(side,[])}for side in('over','under')}
        for player in board['players']:
            if str(player['game_id'])!=a['espn_game_id']:continue
            for q in player['props']:
                target=q['key']
                if target not in ORDINARY or not finite(q.get('line')):continue
                panel='ORIGINAL_PROVIDER_T90'if q.get('line_from')in('dk','sleeper')else'ORIGINAL_SITE_GENERATED_THRESHOLD_T90'
                k=str(player['id']),str(player['game_id']),target
                row=base_row(labels,game=player['game_id'],player=player['id'],target=target,line=q['line'],point=q.get('adj'),raw=q.get('proj'),side=q.get('lean'),index=len(board_rows),position=player.get('pos'),
                             panel=panel,line_from=q.get('line_from'),top_over=k in tops['over'],top_under=k in tops['under'],source_head=proof['head'],source_server_clock=proof['server_retained_at'],decision_time=board.get('saved_at'),forecast_method='WEBSITE_SAVED_ADJUSTED_OR_RAW',fallback='NOT_RETAINED')
                assert row['side']in(None,'over','under')
                board_rows.append(row)
    kk=[(r['game_id'],r['source_player_id'],r['target'])for r in board_rows];assert len(kk)==len(set(kk))
    all_grades=[];scores=[]
    for panel in sorted({r['panel']for r in board_rows}):
        rows=[r for r in board_rows if r['panel']==panel];grades=shared.grade(rows);all_grades.extend(grades)
        for strategy in shared.STRATEGIES:
            gg=[r for r in grades if r['strategy']==strategy]
            for cohort,sub in [('ALL',gg),('SAVED_BOARD_TOP_FLAGS',[r for r in gg if r['top_over']or r['top_under']])]:
                scores.extend(aggregate(sub,panel=panel,method='WEBSITE_ORIGINAL_LEANS'if strategy=='original'else strategy,track='A_ORIGINAL'if strategy=='original'else'B_REPLAY',strategy=strategy,cohort=cohort,pool=gg))
    lists=[];retained={};latest='ea2ce5f57146112bb4b5ccebcf8544b181192f50'
    for head,proof in proofs.items():
        dd=read(private/('selected_directory.json'if head==latest else f'selected-directory-{head}.json'))
        for d in dd:
            if d['name'].endswith('.receipt.json'):continue
            retained.setdefault(d['name'],[]).append(proof)
    substantive=('player_id','game_id','key','line','direction','adj','forecast_source','model_version','product','selected_at')
    first_record={};packets=[]
    for path in sorted(source.glob('selected-*.json')):
        packet=read(path)
        if(packet.get('season'),packet.get('week'))!=(2026,8):continue
        name=path.name[len('selected-'):];pp=retained.get(name,[])
        if not pp:continue
        proof=min(pp,key=lambda p:(p['server_retained_at'],p['head']))
        packets.append((proof['server_retained_at'],path,packet,proof))
        for side,rows in packet['picks'].items():
            for row in rows:
                assert row['direction']==side
                signature=hashlib.sha256(canonical({k:row.get(k)for k in substantive})).hexdigest()
                if signature not in first_record or first_record[signature]['server_retained_at']>proof['server_retained_at']:first_record[signature]=proof
    for clock,path,packet,proof in sorted(packets,key=lambda p:(p[0],p[1].name)):
        rows=[];late=0;keys=set()
        for side,rr in packet['picks'].items():
            for row in rr:
                target=row['key']
                if target not in ORDINARY:continue
                signature=hashlib.sha256(canonical({k:row.get(k)for k in substantive})).hexdigest();first=first_record[signature]
                r=base_row(labels,game=row['game_id'],player=row['player_id'],target=target,line=row['line'],point=row.get('adj'),raw=None,side=side,index=len(rows),
                           panel='SAVED_TOP_LIST:'+path.stem[9:],line_from=row.get('line_from'),decision_time=row.get('selected_at'),source_server_clock=first['server_retained_at'],source_head=first['head'],
                           forecast_method=row.get('model_version'),forecast_source=row.get('forecast_source'),original_record_signature=signature,fallback='NOT_RETAINED')
                key=r['game_id'],r['player_id']or r['source_player_id'],r['target'],str(r['line'])
                assert key not in keys;keys.add(key)
                if not r['kickoff']or aware(first['server_retained_at'])>=aware(r['kickoff'])or(row.get('selected_at')and aware(row['selected_at'])>=aware(r['kickoff'])):
                    late+=1;r['actual']=None;r['participation']='UNKNOWN';r['label_state']='NO_PROVED_PREGAME_RETENTION';r['outcome_state']='final'
                rows.append(r)
        grades=shared.grade(rows,strategies=('original',));all_grades.extend(grades)
        panel=rows[0]['panel']if rows else'SAVED_TOP_LIST:'+path.stem[9:]
        scores.extend(aggregate(grades,panel=panel,method=packet['policy']['version'],track='A_ORIGINAL',cohort='ACTUAL_SAVED_TOP_LIST',pool=grades))
        lists.append(dict(panel=panel,filename=path.name,packet_sha256=sha(path),prepared_at=packet['prepared_at'],server_retained_by=clock,source_head=proof['head'],policy=packet['policy']['version'],top_n_per_side=packet['policy'].get('top_n'),selected_by_side={s:len(rr)for s,rr in packet['picks'].items()},no_proved_pregame_rows=late,rows=len(rows)))
    primary=min(lists,key=lambda l:(l['server_retained_by'],l['packet_sha256']))if lists else None
    table=wide(scores)
    save(out/'SCORES.json',scores);save(out/'SIDE_TABLE.json',table);write_csv(out/'SIDE_TABLE.csv',table)
    save(out/'SAVED_LIST_VERSION_CENSUS.json',dict(versions=lists,primary=primary,rule='Earliest qualified server retention, then packet digest; original23/24/etc counts retained. No outcome-based selection.'))
    save(out/'GAME_COVERAGE.json',dict(evaluated_at_utc=now(),states=dict(collections.Counter(labels.status.values())),games=labels.status_rows,whole_week_complete=False))
    savegz(private/'ORIGINAL_AND_TOP_GRADED_ROWS_V1.json.gz',dict(rows=all_grades))
    savegz(private/'ORIGINAL_JOINED_ROWS_V1.json.gz',dict(rows=board_rows))
    save(out/'RUN_RECEIPT.json',dict(state='PARTIAL_WEEK_SCORED_FROM_SAVED_ORIGINALS',evaluated_at_utc=now(),outer_threshold_rows=len(board_rows),provider_rows=sum(r['panel']=='ORIGINAL_PROVIDER_T90'for r in board_rows),saved_list_versions=len(lists),primary_top_list=primary['panel']if primary else None,
         scoring_sha256=sha(scoring.__file__),shared_adapter_sha256=sha(shared.__file__),code_sha256=sha(__file__),source_label_sha256=sha(private/'source-labels/fresh-player-stats-2026.csv'),finality_sha256=sha(private/'source-labels/espn-week8-scoreboard-v2.json'),scores_sha256=sha(out/'SCORES.json'),private_grades_sha256=sha(private/'ORIGINAL_AND_TOP_GRADED_ROWS_V1.json.gz'),new_fits=0,new_forecasts=0,new_inference=0,offhost_restored=False))
    print(json.dumps(dict(state='PARTIAL_WEEK_SCORED',game_states=dict(collections.Counter(labels.status.values())),original_provider=[r for r in table if r['panel']=='ORIGINAL_PROVIDER_T90'and r['cohort']=='ALL'and r['strategy']=='original'],primary_top_list=primary)))


def run_original_research(private,public):
    from nfl_v2 import shadow_grading, hgb_shadow_grading
    labels=Labels(private);emp=Path(labels.binding['private_evidence_root'])/'week8-shadow-v2/shadow-forecasts.json.gz'
    packet=json.loads(gzip.decompress(emp.read_bytes()));queries={r['query_id']:r for r in packet['rows']};actuals=[]
    observed=read(private/'ACQUISITION_LABELS_V1.json')['receipts'][0]['observed_at_utc']
    for qid,q in queries.items():
        gid=q['game_id']
        if labels.status[gid]=='PENDING':continue
        lab=labels.label(gid,q['player_id'],q['target'])
        actuals.append(dict(query_id=qid,player_id=q['player_id'],game_id=gid,target=q['target'],contract_id=shadow_grading.CONTRACTS[q['target']],
            actual=lab['actual'],state='played'if lab['participation']=='VERIFIED_PLAYED_POSITIVE_PHYSICAL'else'unknown',game_completed=labels.status[gid]=='FINAL',
            finality='final'if labels.status[gid]=='FINAL'else'unverified',source_id='W8-NFLVERSE-EXPLICIT-FINAL-V1',revision_id='RETRIEVED-20261102-V1',available_utc=observed,observed_utc=observed))
    source=dict(source_id='W8-NFLVERSE-EXPLICIT-FINAL-V1',source_tier='current_vintage_final_snapshot',identity_contract_id='EXACT-2026-W8-GSIS-GAME-V1',
                statistic_contract_id='NFLVERSE-EXPLICIT-FULL-GAME-CREDITS-V1',participation_contract_id='POSITIVE-OFFENSIVE-OR-RETURN-CREDIT-V1',
                finality_contract_id='ESPN-FINAL-PLUS-NFLVERSE-SCORE-PARITY-V1',availability_basis_id='RETRIEVAL-BOUND-NOT-HISTORICAL-PUBLICATION-V1')
    labelpath=private/'ORIGINAL_1951_QUERY_LABEL_PACKET_V1.json';save(labelpath,dict(schema=shadow_grading.LABEL_SCHEMA,label_version_id='W8-20261102-FINAL13-PENDING1-V1',source_admissions=[source],labels=actuals))
    eroot=ROOT/'reports/continuation-20261029/week8-shadow-v2';hroot=ROOT/'reports/continuation-20261029/hgb-history-v1';cache=Path(labels.binding['private_evidence_root'])/'hgb-history-v1';asof=now()
    results=[]
    results.append(shadow_grading.grade_files(forecasts=emp,capture_receipt=eroot/'CAPTURE_RECEIPT.json',capture_protocol=eroot/'FROZEN_PROTOCOL.json',labels=labelpath,
        expected_forecast_sha256=sha(emp),expected_capture_receipt_sha256=sha(eroot/'CAPTURE_RECEIPT.json'),asof_utc=asof,run_id='V2-W8-20261102-EMPIRICAL-ORIGINAL-V1',public_output=public/'early-empirical-v1',private_output=private/'early-empirical-v1'))
    results.append(hgb_shadow_grading.grade_files(forecasts=cache/'WEEK8_SHADOWS.json.gz',capture_receipt=hroot/'WEEK8_CAPTURE_RECEIPT.json',capture_protocol=hroot/'FROZEN_PROTOCOL.json',
        frozen_queries=cache/'frozen-queries.json',capture_bindings=cache/'GRADING_BINDINGS.json',artifact_root=cache,labels=labelpath,
        expected_forecast_sha256='9c71eabb7fff13a5cceba6c43246343a10d7f77a3b62184f4ac090959f5a8d67',
        expected_capture_receipt_sha256='fca1f0db76e81559fcd7a7669d1d416f2b3842e2c5d027e17ea1921d327d131f',
        expected_protocol_sha256='8ea88fc4b558d57f46003aaba20cb10af604998f9a7c17c76eb2fb130215794e',
        expected_bindings_sha256='319272d2cce01ed3573817bc5021af70753a50947fa6b7809f5acf32850f0a0b',
        asof_utc=asof,run_id='V2-W8-20261102-HGB-ORIGINAL-V1',public_output=public/'early-hgb-v1',private_output=private/'early-hgb-v1'))
    print(json.dumps([{k:r.get(k)for k in('run_id','forecast_rows','scored_forecast_rows','query_states','whole_week_complete')}for r in results]))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['original','early-research']);p.add_argument('--private-root',type=Path,required=True);p.add_argument('--public-root',type=Path,required=True);a=p.parse_args()
    (run_original if a.action=='original'else run_original_research)(a.private_root,a.public_root)
