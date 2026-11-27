"""Present frozen aggregates; no forecast, grading, fitting or private inputs."""
import collections, hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'reports/player-context-completion-decision-01/B'

def cell(m):
    n=m['denominators']['decided'];s=m['denominators']['outer_rows']
    rate='N/A' if not n else f"{100*m['WIN']/n:.2f}%"
    return f"{s}; {m['WIN']}–{m['LOSS']}/{n} ({rate})"

def exact_method(name):
    if name in ('E1','E3','P1'):return 'B-player-context-matchup-01-v1:'+name
    if name=='F2':return 'B-QB-CHARTED-CATCHABILITY-CONTEXT-v1:F2'
    return name

def main():
    table=json.loads((BASE/'depth-scores-v2/COMMON_CONTROL_TABLE.json').read_text())
    out=['# All frozen direction policies','', 'Counts are selected; wins–losses/decided (rate). Same 112 offers across 2026 W5–8; weekly pools have28. Full-board Brier uses every eligible supported probability, independently of whether the selection gate abstains. Not original picks, verified settlement, or new NFL observations.','']
    for window in ['ALL',5,6,7,8]:
        out += [f'## Window {window}','','| Procedure key | Policy | Over | Under | Combined | Eligible / selected / unavailable / abstained | Full-board Brier |','|---|---|---|---|---|---|---|']
        for r in table:
            if r['window']!=window:continue
            sides={x['side']:x['metrics']for x in r['sides']};m=sides['Combined'];p=r['probability']['brier']
            out.append('| '+ ' | '.join([exact_method(r['method']),r['policy'],cell(sides['over']),cell(sides['under']),cell(m),f"{m['selection_pool_count']} / {m['denominators']['outer_rows']} / {m['technical_unavailable']} / {m['admitted_rule_abstentions']}",'N/A'if p is None else f'{p:.6f}'])+' |')
        out.append('')
    (BASE/'ALL_DIRECTION_POLICY_TABLES_V1.md').write_text('\n'.join(out).rstrip()+'\n')
    scores=json.loads((BASE/'depth-scores-v2/SCORES.json').read_text());groups=collections.defaultdict(dict)
    for r in scores:
        if r.get('product_id')=='ROLLING_TOP_K_DIAGNOSTIC':groups[r['procedure_id'],r['week'],r['rank_scope'],r['K']][r['side']]=r['selection_metrics']
    out=['# Frozen rolling Top-K policies','', 'K is per category/week and named combined/Over/Under ranking pool. Chronological kickoff batches fill remaining slots; ties are fixed. Quote timing is unverified, so these are retrospective diagnostics, not executable original weekly lists. Rows reuse saved grades; no padded picks.','', '| Procedure | Week | Ranking pool | K | Over | Under | Combined |','|---|---|---|---|---|---|---|']
    for (proc,w,pool,k),d in sorted(groups.items()):out.append('| '+' | '.join([proc,str(w),pool,str(k),cell(d['over']),cell(d['under']),cell(d['Combined'])])+' |')
    (BASE/'ALL_TOP_K_TABLES_V1.md').write_text('\n'.join(out).rstrip()+'\n')
    per=json.loads((BASE/'depth-scores-v2/PER_PLAYER_NUMERICAL.json').read_text());lookup={(r['season'],r['method'],r['player_id'],r['product']):r for r in per};summaries=[]
    for year in (2025,2026):
        for a,b in [('D2','D1'),('C2','C1')]:
            for product in ('mean','lower_median'):
                aa=[r for r in per if r['season']==year and r['method'].endswith(':'+a)and r['product']==product]
                pairs=[(r,lookup[year,r['method'].rsplit(':',1)[0]+':'+b,r['player_id'],product])for r in aa]
                deltas=[r['mae']-s['mae']for r,s in pairs];n=sum(r['n']for r,s in pairs)
                summaries.append(dict(season=year,candidate=a,control=b,product=product,players=len(pairs),scored_rows=n,opportunity_weighted_MAE_delta=sum((r['mae']-s['mae'])*r['n']for r,s in pairs)/n,equal_player_MAE_delta=sum(deltas)/len(deltas),players_lower_error=sum(x<0 for x in deltas),players_higher_error=sum(x>0 for x in deltas),players_tied=sum(x==0 for x in deltas),single_case_players=sum(r['n']==1 for r,s in pairs),few_case_limit='Descriptive exposed-player summary; players are not independent NFL games or a per-player routing policy. No per-player winner selected.'))
    (BASE/'PER_PLAYER_COMPARISON_SUMMARY_V1.json').write_text(json.dumps(dict(source_sha256=hashlib.sha256((BASE/'depth-scores-v2/PER_PLAYER_NUMERICAL.json').read_bytes()).hexdigest(),rows=summaries,new_fits=0,new_grades=0,new_NFL_observations=0),indent=2)+'\n')
    out=['# Player support and weighting','', 'D1/D2/C1/C2 identify B-QB-DEPTH-CATCHABILITY-v2 arms. Derived from the frozen broad-population per-player losses. Negative delta favors the candidate. Both fixed procedures use the same player cases; these are descriptive summaries, not independently chosen player algorithms or significance claims.','', '| Season | Contrast | Product | Players / rows | Opportunity-weighted delta | Equal-player delta | Lower / higher / tied error players | Single-case players |','|---|---|---|---|---|---|---|---|']
    for r in summaries:out.append(f"| {r['season']} | {r['candidate']}−{r['control']} | {r['product']} | {r['players']} / {r['scored_rows']} | {r['opportunity_weighted_MAE_delta']:.6f} | {r['equal_player_MAE_delta']:.6f} | {r['players_lower_error']} / {r['players_higher_error']} / {r['players_tied']} | {r['single_case_players']} |")
    (BASE/'PER_PLAYER_COMPARISON_SUMMARY_V1.md').write_text('\n'.join(out).rstrip()+'\n')
    print(json.dumps(dict(direction_rows=len(table),topK_rows=len(groups),player_summary_rows=len(summaries),new_fits=0,new_grades=0)))

if __name__=='__main__':main()
