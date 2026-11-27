"""Compare saved controls on identical original-selected opportunities, no regrade."""
from __future__ import annotations
import argparse,collections,csv,gzip,hashlib,json,resource,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2 import full_provider_prop_replay as shared
from nfl_v2 import recorded_prop_grading as pilot

VERSION='v2-H-original-selected-matched-controls-v1'

def main(a):
    start=time.monotonic();a.public.mkdir(parents=True,exist_ok=True)
    bindings=json.loads(a.inputs.read_bytes());sources=[]
    for z in bindings['sources']:
        receipt=json.loads(Path(z['public'],'RUN_RECEIPT.json').read_bytes())
        path=Path(z['private'],'GRADED_ROWS.json.gz')
        assert pilot.sha(path)==receipt['private_grades_sha256']
        sources.append(dict(week=z['week'],grade_sha256=pilot.sha(path),source_score_sha256=receipt['score_sha256'],receipt_sha256=pilot.sha(Path(z['public'],'RUN_RECEIPT.json'))))
    protocol=dict(protocol_id=VERSION,registered_at_utc=pilot.now(),state='FROZEN_BEFORE_NEW_SAVED_ROW_AGGREGATES',code_sha256=pilot.sha(__file__),sources=sources,memberships_sha256=pilot.sha(a.memberships),rule='Within each frozen week retain exactly original_side in over/under, regardless of outcome, point availability or participation. Reuse all five previously graded strategy rows on identical opportunity IDs. Never recalculate side or threshold grade. Controls retain their own pre-outcome selected side and abstentions. Report full provider-pool cumulative separately.',cohorts='Same exact game/player/target/population diagnostic memberships for every strategy; weekly ranking cutoff<=source clock and latest_available<ranking cutoff. Source positions retained. No outcome filtering. Repeated and overlapping cohorts are views, not independent samples.',periods='W5 partial14/15; W6 all14; W7 all14; disjoint cumulative W5-7 covers42/43 scheduled games. Not season-to-date Weeks1-7.',comparison='Paired loss differences against original on identical original-selected cases with both rules decided. Native hit-rate numerators and denominators separate by pre-outcome selected side; side pools may differ. Game-cluster descriptive bootstrap; only3weeks insufficient for robust week uncertainty.',prices='All price/probability/EV/ROI/CLV null. Statistical crossing separate from unresolved bookmaker settlement.',exposure='Previously exposed research outcomes; this is new saved-row comparison, not untouched holdout.',budget=dict(max_wall_seconds=180,max_RSS_bytes=1073741824,max_threads=2,new_fits=0,new_inference=0,new_threshold_grades=0))
    pilot.write(a.public/'FROZEN_PROTOCOL.json',protocol)
    members={tuple(m['key']):m for m in json.loads(gzip.decompress(a.memberships.read_bytes()))}
    rows=[];offset=0
    for z in bindings['sources']:
        rr=json.loads(gzip.decompress(Path(z['private'],'GRADED_ROWS.json.gz').read_bytes()))['rows']
        for r in rr:
            r['original_source_row_index']=r['source_row_index'];r['source_row_index']+=offset
            assert r['week']==z['week']
            m=members.get((r['game_id'],r['player_id'],r['target'],r['population']))
            ok=m and m['ranking_cutoff']<=pilot.aware(r['source_server_clock']).timestamp()and(m.get('latest_available')is None or m['latest_available']<m['ranking_cutoff'])
            r['source_cohorts']=list(m['cohorts'])if ok else[]
        offset+=max(r['original_source_row_index']for r in rr)+1;rows.extend(rr)
    keys=[(r['week'],r['source_row_index'],r['strategy'])for r in rows];assert len(keys)==len(set(keys))
    original={r['source_row_index']:r for r in rows if r['strategy']=='original'}
    assert len({r['game_id']for r in original.values()})==42
    cohorts=['ALL','position:QB','position:RB','position:WR','position:TE','cohort_unknown']+['reconstructed:'+c for c in sorted({c for r in rows for c in r['source_cohorts']if c!='all'})]
    scores=[];annotations=[];metadata=[];flat=[];cache={};case_masks=[]
    periods=[('W5',[5]),('W6',[6]),('W7',[7]),('W5_7',[5,6,7])]
    for period,weeks in periods:
      for pool_policy in(['ORIGINAL_SELECTED','FULL_PROVIDER_POOL']if period=='W5_7'else['ORIGINAL_SELECTED']):
       for strategy in shared.STRATEGIES:
        for target in('ALL',)+shared.TARGETS:
         for cohort in(cohorts if pool_policy=='ORIGINAL_SELECTED'else['ALL']):
          pool=[r for r in rows if r['week']in weeks and r['strategy']==strategy and(target=='ALL'or r['target']==target)and shared.in_cohort(r,cohort)and(pool_policy=='FULL_PROVIDER_POOL'or r['original_side']in('over','under'))]
          selected=[r for r in pool if r['selected_side']];trip=[]
          for side in('over','under','Combined'):
            rr=[r for r in selected if side=='Combined'or r['selected_side']==side]
            s=shared.score_row(rr,pool,strategy=strategy,target=target,cohort=cohort,side=side)
            ident=[VERSION,period,pool_policy,strategy,target,cohort,side]
            s.update(record_id='MATCHED-ORIGINAL-'+hashlib.sha256(pilot.canonical(ident)).hexdigest()[:24],procedure_id=VERSION+':'+strategy,week=weeks[0]if len(weeks)==1 else None,evaluation_weeks=weeks,time_panel_id='2026_'+period+'_ROLLING_PARTIAL42_OF43'if len(weeks)>1 else'2026_'+period+'_ROLLING_ORIGINAL_SELECTED',evaluation_panel_id=VERSION+':'+period+':'+pool_policy,horizon_id='PER_GAME_LATEST_SERVER_RETAINED_BEFORE_T90_QUOTE_AGE_UNKNOWN',population_policy=pool_policy,aggregation='disjoint_micro_average'if len(weeks)>1 else'weekly',cohort_id=cohort)
            paired=[r for r in rr if r['statistical_state']in('WIN','LOSS')and original[r['source_row_index']]['statistical_state']in('WIN','LOSS')]
            ck=(strategy,tuple(sorted(r['source_row_index']for r in paired)))
            if ck not in cache:cache[ck]=pilot.bootstrap(paired,original)
            candidate_loss=sum(r['statistical_state']=='LOSS'for r in paired)/len(paired)if paired else None
            control_loss=sum(original[r['source_row_index']]['statistical_state']=='LOSS'for r in paired)/len(paired)if paired else None
            comp=dict(status='PAIRED_COMMON_DECIDED_ORIGINAL_SELECTED'if paired else'UNESTABLISHED',comparator_procedure_id=VERSION+':original',metric='selection_loss_rate',candidate_error=candidate_loss,comparator_error=control_loss,absolute_error_change=candidate_loss-control_loss if paired else None,relative_error_change=(candidate_loss-control_loss)/control_loss if paired and control_loss else None,paired_n=len(paired),original_selected_mask=True,uncertainty=cache[ck],membership_sha256=hashlib.sha256(pilot.canonical(sorted(r['source_row_index']for r in paired))).hexdigest())
            annotations.append(dict(source_row_index=len(scores),comparison=comp));scores.append(s);trip.append(s)
            decided=[r for r in rr if r['statistical_state']in('WIN','LOSS')]
            metadata.append(dict(record_id=s['record_id'],alias_of_record_id=None,registered_weeks=weeks,registered_week_count=len(weeks),unique_weeks=len({r['week']for r in decided}),decided_week_count=len({r['week']for r in decided}),selected_week_count=len({r['week']for r in rr}),unique_players=s['unique_players'],unique_player_games=s['unique_player_games'],decided_unique_games=len({r['game_id']for r in decided}),decided_unique_players=len({r['player_id']for r in decided if r['player_id']}),decided_unique_player_games=len({(r['game_id'],r['player_id'])for r in decided if r['player_id']}),overtime=True,season_type='REG',statistic_period='full_game'))
            m=s['selection_metrics'];u=m['status_counts']
            flat.append(dict(record_id=s['record_id'],period=period,weeks=','.join(map(str,weeks)),pool_policy=pool_policy,strategy=strategy,target=target,cohort=cohort,side=side,eligible=len(pool),selected=s['forecast_rows'],wins=m['WIN'],losses=m['LOSS'],decided=s['n'],hit_rate=m['hit_rate'],error_rate=s['selection_loss_rate'],push=m['PUSH'],void=u['VOID'],pending=u['PENDING'],missing_actual=u['MISSING_ACTUAL'],unknown_participation=u['UNKNOWN_PARTICIPATION'],book_unresolved=s['forecast_rows'],abstentions=m['abstentions_outside_selected_partition'],coverage=m['selection_coverage'],game_interval=json.dumps(m['game_uncertainty']['game_interval']),paired_original_n=len(paired),candidate_error=candidate_loss,original_error=control_loss,paired_error_change=comp['absolute_error_change'],price=None,probability=None,EV=None,ROI=None,CLV=None))
          shared.check_triplet(trip)
    pilot.write(a.public/'SCORES.json',scores);score_sha=pilot.sha(a.public/'SCORES.json')
    pilot.write(a.public/'COMPARISON_ANNOTATIONS.json',dict(source_score_sha256=score_sha,identity='source_row_index',rows=annotations));pilot.write(a.public/'METADATA_SUPPLEMENT.json',dict(source_score_sha256=score_sha,rows=metadata))
    for name,rr in [('ALL_MATCHED_SELECTION_VIEWS.csv',flat),('MAIN_CATEGORY_VIEWS.csv',[r for r in flat if r['cohort']=='ALL']),('TOP_PLAYER_WORKLOAD_VIEWS.csv',[r for r in flat if r['cohort'].startswith('reconstructed:')])]:
        with(a.public/name).open('x',newline='')as f:w=csv.DictWriter(f,fieldnames=list(flat[0]));w.writeheader();w.writerows(rr)
    pilot.write(a.public/'UNSUPPORTED_TARGETS.json',[dict(target=t,side=side,strategy=strategy,state='UNAVAILABLE',hit_rate=None,reason='NO_MATCHING_EXACT_TARGET_THRESHOLD_IN_SOURCE')for t in('anytime_td','nick-chart-ppr-v1')for strategy in shared.STRATEGIES for side in('over','under','Combined')])
    receipt=dict(state='COMPLETE_NEW_MATCHED_ORIGINAL_SELECTED_SAVED_GRADE_COMPARISON',protocol_sha256=pilot.sha(a.public/'FROZEN_PROTOCOL.json'),source_bindings=sources,score_sha256=score_sha,score_views=len(scores),unique_source_opportunities=len(original),unique_games=42,registered_weeks=[5,6,7],missing_periods='Weeks1-4;Week5Thursday;no full W1-7 original panel',new_fits=0,new_inference=0,new_forecasts=0,new_threshold_grades=0,reused_strategy_grade_rows=len(rows),wall_seconds=time.monotonic()-start,max_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
    assert receipt['wall_seconds']<=180 and receipt['max_RSS_bytes']<=1073741824
    pilot.write(a.public/'RUN_RECEIPT.json',receipt)
    lines=['# Original-selected controls on the same opportunities','','Week5 adds fourteen newly qualified games. Weeks6 and7 reuse frozen grades. Cumulative means only these42 of43 scheduled games in Weeks5–7. It does not cover Weeks1–4 or the Week5 Thursday game. This is statistical crossing with conditional-on-verified-appearance labels; bookmaker settlement, prices, probabilities and returns remain unestablished. No existing forecast or grade was changed.','','The comparison universe is exactly the source records with a saved original Over or Under before outcomes. Every control sees that same opportunity set, retains its own chosen side, and preserves abstentions and unknowns. Thus a difference cannot be explained by excluding the original unselected board. Earlier source-vintage uncertainty remains. The full-provider-pool cumulative results are a separate panel.','','| Period | Strategy | Predicted Over W/L; rate | Predicted Under W/L; rate | Combined W/L; rate | Selected / eligible |','|---|---|---|---|---|---|']
    lookup={(r['period'],r['pool_policy'],r['strategy'],r['target'],r['cohort'],r['side']):r for r in flat}
    def cell(r):return f"{r['wins']}/{r['losses']}; "+('N/A'if not r['decided']else f"{r['hit_rate']:.2%}")
    for period,weeks in periods:
      for strategy in shared.STRATEGIES:
        rr=[lookup[period,'ORIGINAL_SELECTED',strategy,'ALL','ALL',s]for s in('over','under','Combined')];lines.append('| '+period+' | '+strategy+' | '+' | '.join(cell(r)for r in rr)+f" | {rr[-1]['selected']}/{rr[-1]['eligible']} |")
    lines+=['','All category, selected-side, position, top10/15/20, disjoint player-ranking bands and workload rows are retained in [machine-readable results](ALL_MATCHED_SELECTION_VIEWS.csv). These cohorts are reconstructed diagnostics with earlier source clocks, not original issued star lists. K pick strategies remain the separately frozen rolling K6/10/20 products in the weekly source panels; this analysis does not silently create a new original-selected K rule.','','[Category tables](MAIN_CATEGORY_VIEWS.csv) · [Top-player/workload views](TOP_PLAYER_WORKLOAD_VIEWS.csv) · [Canonical scores](SCORES.json) · [Exact-case comparator and uncertainty](COMPARISON_ANNOTATIONS.json) · [Frozen scope](FROZEN_PROTOCOL.json).','', 'Side rates always use their own wins/(wins+losses), and Combined uses summed counts. Unknowns and bookmaker-unresolved records stay separate. One-to-three weeks are too few for a strong temporal uncertainty claim; game-cluster intervals are descriptive sensitivity and do not adjust selection or multiplicity.']
    (a.public/'README.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps([r for r in flat if r['period']=='W5_7'and r['cohort']=='ALL'and r['target']=='ALL'and r['side']=='Combined']))

if __name__=='__main__':
    from threadpoolctl import threadpool_limits
    _thread_bound=threadpool_limits(2)
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--inputs',type=Path,required=True);p.add_argument('--memberships',type=Path,required=True);p.add_argument('--public',type=Path,required=True);main(p.parse_args())
