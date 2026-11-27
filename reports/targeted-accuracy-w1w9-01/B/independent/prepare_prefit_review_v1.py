"""Freeze representative correctness cases before inspecting M2 scores."""
import datetime, gzip, hashlib, json, pathlib

ROOT=pathlib.Path(__file__).resolve().parents[4]
OUT=pathlib.Path(__file__).resolve().parent
SOURCE=ROOT/'reports/information-first-20261112-01/B/completion-wave-v1/QB_CONTEXT_W1_W9_INPUTS_V1.json.gz'

def main():
    rows=json.loads(gzip.decompress(SOURCE.read_bytes()))
    rows=sorted(rows,key=lambda r:(r['kickoff'],r['game_id'],r['player_id']))
    eligible=lambda q:[r for r in rows if r['available']<q['kickoff']and r['player_id']==q['player_id']and r['physical_participation']and r['target_parity']]
    domain=[r for r in rows if r['season']==2026 and 1<=r['week']<=9]
    keys=lambda r:{k:r[k]for k in ['season','week','game_id','player_id','team','opponent','kickoff']}
    preselected=[]
    for week in (1,5,9):
        candidates=[r for r in domain if r['week']==week]
        ordinary=[r for r in candidates if r['official_attempts']>0 and len(eligible(r))>=4]
        q=sorted(ordinary,key=lambda r:(r['game_id'],r['player_id']))[0]
        preselected.append(dict(case='ORDINARY_W'+str(week),**keys(q),earlier_own_games=len(eligible(q)),
          selection='First canonical game/player within predeclared origin and >=4 earlier supported own games; no model score or comparative win inspected.'))
    for name,predicate in [
      ('SPARSE_OWN_HISTORY',lambda r:len(eligible(r))<=1),
      ('KNOWN_PLAYED_ZERO_COMPLETIONS',lambda r:r['physical_participation']and r['official_completions']==0),
      ('HISTORICAL_TEAM_CHANGE',lambda r:eligible(r)and eligible(r)[-1]['team']!=r['team'])]:
        candidates=[r for r in domain if predicate(r)]
        if candidates:
            q=sorted(candidates,key=lambda r:(r['kickoff'],r['game_id'],r['player_id']))[0]
            preselected.append(dict(case=name,**keys(q),earlier_own_games=len(eligible(q)),selection='First chronological canonical qualifying case; source boundary selection, not comparative success selection.'))
        else:preselected.append(dict(case=name,state='NO_NATIVE_CASE;USE_SEPARATE_SYNTHETIC_CONTRACT_FIXTURE'))
    plan={'id':'B_M2_INDEPENDENT_PREFIT_REVIEW_v1','at_UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'state':'CONDITIONAL_PASS_FOR_BOUNDED_M2_MECHANISM','source':{'path':str(SOURCE.relative_to(ROOT)),'sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'rows':len(rows)},
      'old_equivalents':[
        {'code':'nfl_v2/player_context_matchup.py','scope':'P1/P2 existing conditional logistic25down-depth contexts, earlier own rate, opponent/offense residuals, team/defense and optional shrunk QB intercepts, predicted mixture and common NB exposure, exact binomial thinning.'},
        {'code':'nfl_v2/qb_depth_catchability.py','scope':'C1/C2 existing depth-specific chart-support and catchability values with same conditional binomial objective and predicted context mix.'}],
      'new_primary_mechanism':'One bounded context-dependent completion beta-binomial dispersion fit using immutable earlier-origin conversion means, holding the predicted attempt law and mean fixed. Mean/architecture claims stay separate.',
      'proposed_likelihood':'C|A,Theta~Binomial(A,Theta); Theta~Beta(m*kappa,(1-m)*kappa); A~existing gamma-Poisson law. kappa is a regularized function of qualified earlier profile summaries. No realized target-game A/mix enters inference.',
      'conditions':[
        'Use earlier out-of-time conversion means for downstream dispersion training. Admit only labels with available<origin; old source vintage is current-revised+7d reconstruction, not authenticated publication.',
        'Check saved conversion components and exposure for exact identities; no points-to-probability inference. Zero exposure and endpoint means need declared degenerate handling.',
        'Keep original mean and exposure parameters identical across binomial and BB arms. Same direct controls do not become coherent joint models.',
        'Lagged destination entropy is a known-destination summary, not alignment; unsupported receiver groups remain blocked. Lagged ydstogo summaries are not full conditional distance bins.',
        'Fit only kappa with frozen bounds/penalties/settings; report active-bound behavior, convergence and support. No post-outcome settings search.',
        'Conditional BB integrates uncertainty in conversion but does not jointly estimate future rosters or all future context mixtures. Full requested source/model scope remains partial.',
        'Preserve missing/zero flags, unknown quote clocks/main-alt and historical stat-row population limitation. No new production qualification follows.'
      ],
      'representative_cases':preselected,
      'additional_synthetic_contract_cases':['UNSEEN_PLAYER_AND_TEAM_EFFECT','MISSING_DESTINATION','MISSING_DISTANCE','TRUE_ZERO_DISTANCE','UNKNOWN_CURRENT_QUERY_OUTCOME','STRICT_AVAILABILITY_EQUALITY_BOUNDARY','INTEGER_LINE_PUSH','NONFINITE_PARAMETER_REJECTION'],
      'independent_verification':[
        'Author A-sum marginal law versus independent beta-integral of NB thinning; finite/nonnegative PMF, total mass plus explicit attempt-tail bound, monotone CDF, integer pushes and arbitrary-tail queries.',
        'E[C]=M*m; Var[C]=M*m+(M*M+M*M/r)*(m*m+rho*m*(1-m))-(M*m)**2; structural joint support0<=C<=A.',
        'Representative safeJSON restoration, feature-order rejection, batch/single/shuffled identity, output typing, no correction duplication.',
        'Freshly rebuild earlier design arrays after future/target outcome mutation; identical eligible inputs imply identical deterministic fit objective. Do not use feature caches for this check.',
        'Separate synthetic strong-signal positive control outside NFL scoring; a calibrated confidence number, actual hit rate and supported accuracy claim remain separate.'
      ],
      'independent_scope_limit':'No private A offer rows/source clocks/fit parity, no new NFL fit, no author scores inspected at preselection. Later verified scope will be appended separately.',
      'NFL_fits':0,'new_source_read_attempts':0,'new_model_gains_claimed':False}
    (OUT/'PREFIT_DESIGN_REVIEW_V1.json').write_text(json.dumps(plan,indent=2)+'\n')
    print(json.dumps({'state':plan['state'],'representative_cases':len(preselected),'source_rows':len(rows)}))

if __name__=='__main__':main()
