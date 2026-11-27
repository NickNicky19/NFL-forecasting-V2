"""Readable source-bound projections of completed rolling archive grades."""
import argparse,csv,gzip,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2 import full_provider_prop_replay as shared
from nfl_v2 import recorded_prop_grading as pilot
from tools.report_full_provider_prop_pool import rows_for


def cell(r):
    m=r['selection_metrics'];u=m['status_counts'];rate='N/A'if not r['n']else f"{m['hit_rate']*100:.2f}%"
    return f"{r['forecast_rows']} selected; {m['WIN']}W/{m['LOSS']}L; {r['n']} decided; {rate}; {m['PUSH']} push; {u['VOID']} void; {u['PENDING']} pending; {u['MISSING_ACTUAL']} missing; {u['UNKNOWN_PARTICIPATION']} unknown"


def main(a):
    scores=json.loads((a.public/'SCORES.json').read_bytes());receipt=json.loads((a.public/'RUN_RECEIPT.json').read_bytes());score_sha=pilot.sha(a.public/'SCORES.json')
    assert score_sha==receipt['score_sha256']and pilot.sha(a.private/'GRADED_ROWS.json.gz')==receipt['private_grades_sha256']
    grades=json.loads(gzip.decompress((a.private/'GRADED_ROWS.json.gz').read_bytes()))['rows'];ks=json.loads(gzip.decompress((a.private/'FROZEN_ROLLING_K_MEMBERSHIPS.json.gz').read_bytes()))['rows']
    kmap={(k['strategy'],k['target'],k['rank_scope'],k['K']):set(k['source_row_indices'])for k in ks};baseline={r['source_row_index']:r for r in grades if r['strategy']==shared.ADJUSTED}
    metadata=[];comparisons=[];flat=[];cache={}
    for i,s in enumerate(scores):
        rr=rows_for(s,grades,kmap);decided=[r for r in rr if r['statistical_state']in('WIN','LOSS')]
        assert len(rr)==s['forecast_rows']and len(decided)==s['n']and hashlib.sha256(pilot.canonical(sorted(r['source_row_index']for r in rr))).hexdigest()==s['query_membership_sha256']
        metadata.append(dict(record_id=s['record_id'],alias_of_record_id=None,unique_players=s['unique_players'],unique_player_games=s['unique_player_games'],unique_weeks=1 if decided else 0,decided_unique_games=len({r['game_id']for r in decided}),decided_unique_players=len({r['player_id']for r in decided}),decided_unique_player_games=len({(r['game_id'],r['player_id'])for r in decided}),decided_week_count=1 if decided else 0,registered_week_count=1,registered_weeks=[s['week']],selected_week_count=1 if rr else 0,overtime=True,season_type='REG',statistic_period='full_game'))
        paired=[r for r in decided if baseline[r['source_row_index']]['statistical_state']in('WIN','LOSS')]
        if paired:
            key=(s['strategy'],tuple(sorted(r['source_row_index']for r in paired)))
            if key not in cache:cache[key]=pilot.bootstrap(paired,baseline)
            comp=dict(status='PAIRED_RETAINED_ROWS',comparator_procedure_id=s['procedure_id'].rsplit(':',1)[0]+':'+shared.ADJUSTED,comparator_history_regime='ARCHIVED_COMPONENT_MEMORY_UNKNOWN',comparator_product_id=s['product_id'],metric='selection_loss_rate',candidate_error=sum(r['statistical_state']=='LOSS'for r in paired)/len(paired),comparator_error=sum(baseline[r['source_row_index']]['statistical_state']=='LOSS'for r in paired)/len(paired),paired_n=len(paired),membership_sha256=hashlib.sha256(pilot.canonical(sorted(r['source_row_index']for r in paired))).hexdigest(),uncertainty=cache[key],cutoff_policy=s['horizon_id'])
        else:comp=dict(status='UNESTABLISHED',reason='No common decided selections with saved-adjusted control.')
        comparisons.append(dict(source_row_index=i,comparison=comp));m=s['selection_metrics'];u=m['status_counts']
        flat.append(dict(record_id=s['record_id'],procedure=s['procedure_id'],strategy=s['strategy'],season=2026,week=s['week'],target=s['target'],horizon=s['horizon_id'],evidence=s['selection_evidence'],cohort=s['cohort_id'],K=s['K'],rank_scope=s['rank_scope'],side=s['side'],eligible=m['eligible_rank_pool_n'],selected=s['forecast_rows'],wins=m['WIN'],losses=m['LOSS'],decided=s['n'],hit_rate=m['hit_rate'],error_rate=s['selection_loss_rate'],push=m['PUSH'],void=u['VOID'],pending=u['PENDING'],missing_actual=u['MISSING_ACTUAL'],unknown_participation=u['UNKNOWN_PARTICIPATION'],book_unresolved=s['forecast_rows'],abstentions=m['abstentions_outside_selected_partition'],coverage=m['selection_coverage'],players=s['unique_players'],games=s['unique_games'],weeks=1 if decided else 0,game_uncertainty=json.dumps(m['game_uncertainty'],separators=(',',':')),price=None,probability=None,EV=None,ROI=None,CLV=None))
    pilot.write(a.public/'METADATA_SUPPLEMENT.json',dict(source_score_sha256=score_sha,rows=metadata));pilot.write(a.public/'COMPARISON_ANNOTATIONS.json',dict(source_score_sha256=score_sha,identity='source_row_index',rows=comparisons))
    for name,rows in [('ALL_SELECTION_VIEWS.csv',flat),('COHORT_VIEWS.csv',[r for r in flat if r['K']is None and r['cohort']!='ALL']),('ROLLING_K_VIEWS.csv',[r for r in flat if r['K']is not None])]:
        with(a.public/name).open('x',newline='')as f:w=csv.DictWriter(f,fieldnames=list(flat[0]));w.writeheader();w.writerows(rows)
    week=scores[0]['week'];lookup={(s['strategy'],s['target'],s['cohort_id'],s['side']):s for s in scores if s['K']is None}
    lines=[f'# Week {week}: full fourteen-game rolling original and saved-point controls','',f"This adds {receipt['outer_rows']} provider-labelled thresholds across all fourteen scheduled Week {week} games. Each game's archive version was selected using only the latest independently server-retained head before T-minus-90; actual server clocks differ by game. Source bytes and saved sides are authentic at those retained captures. Quote age, input vintage, cash execution and bookmaker settlement remain unqualified. Labels reuse the qualified current-vintage NFLverse target source. No source is relabelled as an authenticated historical input vintage.",'','Saved original sides remain separate from new retrospective point rules. No-side originals stay abstentions. Missing points cause only the corresponding point rule to abstain. Original internal precision and fallback provenance are unavailable; retained points are used exactly without extra rounding. All probabilities, prices, EV, ROI and CLV remain null.','', '## Every category, strategy and selected side','']
    for strategy in shared.STRATEGIES:
        lines +=[f'### {strategy}','','| Category | Predicted Over | Predicted Under | Combined |','|---|---|---|---|']
        for target in('ALL',)+shared.TARGETS:lines.append('| '+target+' | '+' | '.join(cell(lookup[strategy,target,'ALL',side])for side in('over','under','Combined'))+' |')
        lines +=['| nick-chart-ppr-v1 | N/A: no exact matching offered threshold contract | N/A | N/A |','| anytime_td | N/A: no exact rushing/receiving event offer contract | N/A | N/A |','']
    lines +=['## Player and workload diagnostics','','These are target-specific reconstructed player cohorts, assembled after games with earlier input clocks. They are not originally issued star lists. The same eligible membership is used for every competitor. Admission requires saved feature availability by the source decision time; the ranking cutoff uses the known scheduled target time. Unknown membership remains visible. Full category/cohort/side tables and uncertainty are in [COHORT_VIEWS.csv](COHORT_VIEWS.csv).','']
    for strategy in shared.STRATEGIES:
        lines +=[f'### {strategy}','','| Cohort | Predicted Over | Predicted Under | Combined |','|---|---|---|---|']
        for c in ['top10','top15','top20','rank1_10','rank11_15','rank16_20','rank21plus','workload_high','workload_middle','workload_low']:
            if(strategy,'ALL','reconstructed:'+c,'Combined')in lookup:lines.append('| '+c+' | '+' | '.join(cell(lookup[strategy,'ALL','reconstructed:'+c,side])for side in('over','under','Combined'))+' |')
        lines.append('| membership unknown | '+' | '.join(cell(lookup[strategy,'ALL','cohort_unknown',side])for side in('over','under','Combined'))+' |');lines+=['']
    lines +=['## Rolling K timing and remaining limits','','K6/10/20 applies per category, week and strategy with separate combined-side, Over-only and Under-only pools. At each increasing source-clock batch the rule ranks that batch by absolute saved point-line gap within category and uses remaining slots. It cannot revise earlier choices using later batches. The membership was frozen before labels. These are newly replayed rolling rules, not fixed weekly lists or original saved K recommendations. [Every K/category/actual-side result](ROLLING_K_VIEWS.csv).','','Counts reconcile Over plus Under exactly. Hit rate is wins divided by wins plus losses; empty decided sides are N/A. Pushes, unknowns, missing actuals and abstentions remain separate. Bookmaker settlement remains unresolved even for statistically decided cases. One week cannot support a whole-week interval; game-cluster bootstrap sensitivity is exposed descriptive evidence without multiplicity adjustment. Different selected pools and coverage must be retained when comparing side rates.','','[All views](ALL_SELECTION_VIEWS.csv) · [Canonical scores](SCORES.json) · [Protocol](FROZEN_GRADING_PROTOCOL_V2.json) · [Source membership](METADATA_QUALIFICATION_RECEIPT.json) · [Run receipt](RUN_RECEIPT.json) · [Paired exact-case annotations](COMPARISON_ANNOTATIONS.json). The earlier F fixed-Friday Week 7 panel and every original source/capture hash remain unchanged. No fits, inference, new forecast, Week 8 outcome read, collector, wager or production write occurred.']
    with(a.public/'README.md').open('x')as f:f.write('\n'.join(lines)+'\n')
    pilot.write(a.public/'REPORT_RECEIPT.json',dict(state='COMPLETE_SOURCE_BOUND_READABLE_AND_INDEX_METADATA',source_score_sha256=score_sha,source_grades_sha256=receipt['private_grades_sha256'],metadata_rows=len(metadata),paired_rows=len(comparisons),code_sha256=pilot.sha(__file__),new_grades=0,new_fits=0,new_forecasts=0))
    print(dict(state='PASS',week=week,rows=len(scores),new_grades=0))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--public',type=Path,required=True);p.add_argument('--private',type=Path,required=True);main(p.parse_args())
