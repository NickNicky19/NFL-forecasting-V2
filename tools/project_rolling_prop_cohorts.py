"""Correct subgroup-clock admission using retained grades, without regrading."""
import argparse,collections,csv,gzip,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2 import full_provider_prop_replay as shared
from nfl_v2 import recorded_prop_grading as pilot
from tools.report_rolling_archive_props import cell


def main(a):
    if a.output.exists():raise ValueError('preserve completed projection')
    a.output.mkdir(parents=True);receipt=json.loads((a.source_public/'RUN_RECEIPT.json').read_bytes());assert pilot.sha(a.source_private/'GRADED_ROWS.json.gz')==receipt['private_grades_sha256']
    protocol=dict(protocol_id='v2-rolling-archive-shared-cohort-clock-correction-v3',registered_at_utc=pilot.now(),source_score_sha256=receipt['score_sha256'],source_grade_sha256=receipt['private_grades_sha256'],memberships_sha256=pilot.sha(a.memberships),code_sha256=pilot.sha(__file__),state='FROZEN_SAVED_GRADE_PROJECTION_NO_REGRADE',rule='Exactgame/GSIS/target/population key; require originalweeklyranking_cutoff<=actualsourceclock and latest_available<ranking_cutoff. WholeweekfirstT90 was the actual cohortorigin; priorv2mistakenlyexpected targetkickoff andadmittednone. ThusThursdayearlierclock remainsunknown; no targetoutcome/gradefilter. Diagnosticretrospectivemembership notoriginallyissuedstarlist.',correction_kind='COHORT_MEMBERSHIP_TIMING_CORRECTION_NO_PREDICTION_OR_SELECTION_CHANGE',exposure='Originalweekresults alreadyexposed; purelydeterministic sourcecontractcorrection, notnewholdout or outcome-selectedsubgroup.',new_fits=0,new_forecasts=0,new_threshold_grades=0)
    pilot.write(a.output/'FROZEN_PROTOCOL.json',protocol);grades=json.loads(gzip.decompress((a.source_private/'GRADED_ROWS.json.gz').read_bytes()))['rows'];member={tuple(r['key']):r for r in json.loads(gzip.decompress(a.memberships.read_bytes()))}
    for r in grades:
        m=member.get((r['game_id'],r['player_id'],r['target'],r['population']));ok=m and m['ranking_cutoff']<=pilot.aware(r['source_server_clock']).timestamp()and(m.get('latest_available')is None or m['latest_available']<m['ranking_cutoff'])
        r['source_cohorts']=list(m['cohorts'])if ok else[]
    cohorts=['reconstructed:'+c for c in sorted({c for r in grades for c in r['source_cohorts']if c!='all'})]+['cohort_unknown'];scores=[];metadata=[];flat=[];annotations=[];baseline={r['source_row_index']:r for r in grades if r['strategy']==shared.ADJUSTED};cache={}
    for strategy in shared.STRATEGIES:
        for target in('ALL',)+shared.TARGETS:
            tt=[r for r in grades if r['strategy']==strategy and(target=='ALL'or r['target']==target)]
            for cohort in cohorts:
                pool=[r for r in tt if shared.in_cohort(r,cohort)];selected=[r for r in pool if r['selected_side']];trip=[]
                for side in('over','under','Combined'):
                    rr=[r for r in selected if side=='Combined'or r['selected_side']==side];s=shared.score_row(rr,pool,strategy=strategy,target=target,cohort=cohort,side=side)
                    week=grades[0]['week'];s.update(record_id='ROLLING-COHORT-'+hashlib.sha256(pilot.canonical([week,strategy,target,cohort,side])).hexdigest()[:24],procedure_id='v2-server-retained-per-game-T90-archive-selection-v2:'+strategy,week=week,evaluation_weeks=[week],evaluation_panel_id=protocol['protocol_id']+f':W{week}',time_panel_id=f'2026_W{week}_FULL14_PER_GAME_SERVER_BEFORE_T90',horizon_id='PER_GAME_LATEST_SERVER_RETAINED_BEFORE_T90_QUOTE_AGE_UNKNOWN',scoring_version='v3_cohort_timing_correction',correction_kind=protocol['correction_kind'])
                    decided=[r for r in rr if r['statistical_state']in('WIN','LOSS')];paired=[r for r in decided if baseline[r['source_row_index']]['statistical_state']in('WIN','LOSS')]
                    if paired:
                        ck=(strategy,tuple(sorted(r['source_row_index']for r in paired)))
                        if ck not in cache:cache[ck]=pilot.bootstrap(paired,baseline)
                        comp=dict(status='PAIRED_RETAINED_ROWS',comparator_procedure_id=s['procedure_id'].rsplit(':',1)[0]+':'+shared.ADJUSTED,comparator_history_regime='ARCHIVED_COMPONENT_MEMORY_UNKNOWN',comparator_product_id=s['product_id'],metric='selection_loss_rate',candidate_error=sum(r['statistical_state']=='LOSS'for r in paired)/len(paired),comparator_error=sum(baseline[r['source_row_index']]['statistical_state']=='LOSS'for r in paired)/len(paired),paired_n=len(paired),membership_sha256=hashlib.sha256(pilot.canonical(sorted(r['source_row_index']for r in paired))).hexdigest(),uncertainty=cache[ck],cutoff_policy=s['horizon_id'])
                    else:comp=dict(status='UNESTABLISHED',reason='No common decided selections.')
                    annotations.append(dict(source_row_index=len(scores),comparison=comp));scores.append(s);trip.append(s)
                    metadata.append(dict(record_id=s['record_id'],alias_of_record_id=None,unique_players=s['unique_players'],unique_player_games=s['unique_player_games'],unique_weeks=1 if decided else 0,decided_unique_games=len({r['game_id']for r in decided}),decided_unique_players=len({r['player_id']for r in decided}),decided_unique_player_games=len({(r['game_id'],r['player_id'])for r in decided}),decided_week_count=1 if decided else 0,registered_week_count=1,registered_weeks=[week],selected_week_count=1 if rr else 0,overtime=True,season_type='REG',statistic_period='full_game'))
                    m=s['selection_metrics'];flat.append(dict(record_id=s['record_id'],strategy=strategy,target=target,cohort=cohort,side=side,season=2026,week=week,eligible=len(pool),selected=s['forecast_rows'],wins=m['WIN'],losses=m['LOSS'],decided=s['n'],hit_rate=m['hit_rate'],push=m['PUSH'],unknown=m['status_counts']['UNKNOWN_PARTICIPATION'],missing_actual=m['status_counts']['MISSING_ACTUAL'],abstentions=m['abstentions_outside_selected_partition'],coverage=m['selection_coverage'],game_uncertainty=json.dumps(m['game_uncertainty'])))
                shared.check_triplet(trip)
    pilot.write(a.output/'SCORES.json',scores);source_sha=pilot.sha(a.output/'SCORES.json');pilot.write(a.output/'METADATA_SUPPLEMENT.json',dict(source_score_sha256=source_sha,rows=metadata));pilot.write(a.output/'COMPARISON_ANNOTATIONS.json',dict(source_score_sha256=source_sha,identity='source_row_index',rows=annotations))
    with(a.output/'COHORT_VIEWS.csv').open('x',newline='')as f:w=csv.DictWriter(f,fieldnames=list(flat[0]));w.writeheader();w.writerows(flat)
    lookup={(r['strategy'],r['cohort_id'],r['side']):r for r in scores if r['target']=='ALL'};lines=[f'# Week {week}: corrected shared cohort-clock diagnostics','','The existing weekly cohort origin is the first game T-minus-90, rather than every target kickoff. This deterministic saved-grade projection corrects admission only. All predictions, saved selections, outcomes, crossing grades and K memberships remain unchanged. Exact cohort origin must precede the actual source clock, so the earlier Thursday captures retain unknown membership. All groups are postgame reconstructed diagnostics; identical competitor membership is retained. Original v2 unknown-only views survive. [Every category and actual side](COHORT_VIEWS.csv).','']
    for strategy in shared.STRATEGIES:
        lines +=[f'## {strategy}','','| Cohort | Predicted Over | Predicted Under | Combined |','|---|---|---|---|']
        for cohort in cohorts:lines.append('| '+cohort+' | '+' | '.join(cell(lookup[strategy,cohort,side])for side in('over','under','Combined'))+' |')
        lines+=['']
    (a.output/'README.md').write_text('\n'.join(lines)+'\n');pilot.write(a.output/'RUN_RECEIPT.json',dict(state='COMPLETE_SHARED_COHORT_CLOCK_CORRECTION_SAVED_GRADES_ONLY',source_grade_sha256=receipt['private_grades_sha256'],source_score_sha256=receipt['score_sha256'],score_sha256=source_sha,score_views=len(scores),source_outer_rows=receipt['outer_rows'],cohort_tags=cohorts,qualified_membership_rows=sum(bool(r['source_cohorts'])for r in grades if r['strategy']=='original'),new_fits=0,new_forecasts=0,new_threshold_grades=0))
    print(dict(state='PASS',week=week,views=len(scores),qualified=sum(bool(r['source_cohorts'])for r in grades if r['strategy']=='original')))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-public',type=Path,required=True);p.add_argument('--source-private',type=Path,required=True);p.add_argument('--memberships',type=Path,required=True);p.add_argument('--output',type=Path,required=True);main(p.parse_args())
