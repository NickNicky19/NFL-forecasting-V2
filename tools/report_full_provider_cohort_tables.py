"""Readable cohort and K projections of sealed full-provider scores, no regrading."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2 import full_provider_prop_replay as wave
from tools.report_full_provider_prop_pool import format_cell


def main(out):
    scores=json.loads((out/'SCORES.json').read_bytes())
    receipt=json.loads((out/'RUN_RECEIPT.json').read_bytes())
    source_sha=wave.sha(out/'SCORES.json')
    if source_sha!=receipt['public_score_sha256']:raise ValueError('sealed scores changed')
    groups=['top10','top15','top20','rank1_10','rank11_15','rank16_20','rank21plus','workload_high','workload_middle','workload_low']
    lookup={(r['strategy'],r['cohort_id'],r['side']):r for r in scores if r['target']=='ALL'and r['K']is None}
    lines=['# Shared player/workload cohorts: retained statistical directions','','These aggregate all ten supported targets in the one thirteen-game Week 7 source panel. Player ranks are target-specific; they are not top-ranked picks. Membership is joined from the original 1,973 W7 cohort records by canonical game/player/target/population: 446 supported rows match, including all 167 qualified formerly unselected records. Sixteen unknown appearances remain an explicit unknown-membership group. No rank or workload membership is inferred from target-game performance. Cohorts were reconstructed after the games with earlier feature clocks and are descriptive, not original pregame lists.','','Every cell retains selected count, wins/losses, decided denominator, hit rate and unknowns. Exact category-by-cohort rows, source/position bands, coverage and uncertainty remain in [COHORT_VIEWS.csv](COHORT_VIEWS.csv). All prices and bookmaker settlements remain unavailable.']
    for strategy in wave.STRATEGIES:
        lines+=['',f'## {strategy}','','| Shared cohort | Predicted Over | Predicted Under | Combined |','|---|---|---|---|']
        for group in groups:
            lines.append('| '+group+' | '+' | '.join(format_cell(lookup[strategy,'reconstructed:'+group,side])for side in('over','under','Combined'))+' |')
        lines.append('| membership unknown | '+' | '.join(format_cell(lookup[strategy,'cohort_unknown',side])for side in('over','under','Combined'))+' |')
    with(out/'COHORT_READABLE.md').open('x')as f:f.write('\n'.join(lines)+'\n')
    lookup={(r['strategy'],r['target'],r['K'],r['rank_scope'],r['side']):r for r in scores if r['K']is not None}
    lines=['# Top-ranked picks: bounded retrospective K rules','','K is per category within this thirteen-game source snapshot. Each row compares three distinct lists: combined-side, Over-only and Under-only. A combined top-20 is not twenty Overs plus twenty Unders. Rank uses the saved point-line absolute gap within category, unrounded beyond the retained source precision, stable canonical ties and no realized-result or participation filter. All source rows share the same retention bound before the thirteen games. These newly frozen lists are retrospective source-snapshot rules, not original weekly picks, chronological rolling lists or cross-category rankings. Fewer eligible candidates produce fewer picks.','','All counts are exact projections of sealed scores; no extra crossing, fit or selection was performed. [Machine-readable K views](TOPK_VIEWS.csv) retain every actual-side partition of each list, abstentions, failures, uncertainty and coverage.']
    for strategy in wave.STRATEGIES:
        lines+=['',f'## {strategy}','','| Category | K | Combined-side list | Over-only list | Under-only list |','|---|---|---|---|---|']
        for target in wave.TARGETS:
            for k in(6,10,20):
                lines.append('| '+target+' | '+str(k)+' | '+' | '.join(format_cell(lookup[strategy,target,k,scope,'Combined'])for scope in('Combined','over','under'))+' |')
    with(out/'TOPK_READABLE.md').open('x')as f:f.write('\n'.join(lines)+'\n')
    wave.write(out/'READABLE_COHORT_K_RECEIPT.json',dict(state='SOURCE_BOUND_READABLE_PROJECTION',source_score_sha256=source_sha,code_sha256=wave.sha(Path(__file__)),new_grades=0,new_fits=0,new_forecasts=0,cohort_report_sha256=wave.sha(out/'COHORT_READABLE.md'),topk_report_sha256=wave.sha(out/'TOPK_READABLE.md')))
    print(json.dumps(dict(state='PASS',source_score_sha256=source_sha,new_grades=0)))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--public',required=True,type=Path);main(p.parse_args().public)
