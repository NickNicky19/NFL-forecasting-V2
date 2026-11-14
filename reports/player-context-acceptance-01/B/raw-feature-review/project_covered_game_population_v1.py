"""New numerical covered-game projection of frozen outputs, no prop grader.
Protected boards supply only a game-membership mask; no lines or protected rows
are published. Existing277/W5_PLUS131/offered112 evaluations are reused.
"""
import argparse,collections,gzip,hashlib,json,sys,datetime,math
from pathlib import Path

def read(p):
 b=Path(p).read_bytes();return json.loads(gzip.decompress(b)if str(p).endswith('.gz')else b)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def h(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--repo',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
 for w in range(5,9):ap.add_argument('--week'+str(w),type=Path,required=True)
 a=ap.parse_args();sys.path.insert(0,str(a.repo));from nfl_v2.scoring import point_metrics
 b=a.repo/'reports/player-context-matchup-01/B';sources=[];offers=[]
 for w in range(5,9):
  p=getattr(a,'week'+str(w));sources.append(dict(source_id='OWNER_LOCAL_QB_BOARD_W'+str(w),sha256=sha(p)))
  for r in read(p)['rows']:
   if r.get('target')not in('pass_cmp','pass_att'):continue
   if w==8 and not(r.get('panel')=='ORIGINAL_PROVIDER_T90'and r.get('strategy')=='original'and not r.get('method_key')):continue
   offers.append(r)
 assert len(offers)==224;covered_games={r['game_id']for r in offers};assert len(covered_games)==56
 protocol=dict(id='B-RAW-VERIFIED-COVERED-GAME-POPULATION-v1',registered_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
  owner='B',source_producer_commit='2fa855fc4dd7e9e495126dea93ba90a33fee4be3',new_fits=0,new_forecasts=0,new_prop_grades=0,new_NFLobservations=0,
  purpose='Isolate week/game/offeredmembership beforeinterpreting277vs112numericaldifferences; no causalmodelrepair.',
  source_board_bindings=sources,covered_game_membership_sha256=h(sorted(covered_games)),covered_games=56,
  rules='2026W5-8allQBswithin56offerboardgameIDs; no original-sidefilter or outcome-dependentmembership. Onlynew129-rownativepointviews emitted. Otherpanels reused.',
  methods=['B-player-context-matchup-01-v1:COMMON_EXPOSURE/pass_att','B-player-context-matchup-01-v1:E0/pass_cmp','B-player-context-matchup-01-v1:E3/pass_cmp','B-QB-CHARTED-CATCHABILITY-CONTEXT-v1:F2/pass_cmp'],products=['mean','lower_median'],
  source_tier='Current/revisedsource+7dayreconstruction; noauthenticpregamequoteexecutionclaim.',permissions='Public-derivedstat/forecastsCCBY4;FTNdependentF2CCBYSA4FTNData vianflverse. Protectedboards usedowner-local asmaskonly; no publicofferrows.',
  scoring_code_sha256=sha(a.repo/'nfl_v2/scoring.py'),adapter_sha256=sha(__file__))
 p=a.out/'COVERED_GAME_PROJECTION_REGISTRATION_V1.json';assert not p.exists();p.write_text(json.dumps(protocol,indent=2)+'\n')
 forecasts=[];bindings=[]
 for wave in('qb-wave-v1','qb-charting-wave-v1'):
  for w in range(5,9):
   p=b/wave/'predictions'/f'2026-W{w:02}.json.gz';bindings.append(dict(path=str(p.relative_to(a.repo)),sha256=sha(p)));forecasts+=read(p)['rows']
 selected=[]
 for r in forecasts:
  if r['method']in('COMMON_EXPOSURE','E0','E3','F2'):selected.append(r)
 groups=collections.defaultdict(list)
 for r in selected:groups[r['procedure_id'],r['target']].append(r)
 rows=[]
 for(proc,target),outer in sorted(groups.items()):
  subset=[r for r in outer if r['game_id']in covered_games];assert len(outer)==131 and len(subset)==129
  assert len({(r['game_id'],r['player_id'])for r in subset})==129
  for product in('mean','lower_median'):
   good=[r for r in subset if r['actual']is not None];assert len(good)==129
   m=point_metrics([r[product]for r in good],[r['actual']for r in good],target)
   prec={}
   for name in('exact_rate','abs_lt_1','abs_le_1','abs_lt_5','abs_le_5','abs_lt_10','abs_le_10'):
    if name=='exact_rate':hits=sum(r[product]==r['actual']for r in good)
    else:
     _,op,k=name.split('_');hits=sum(abs(r[product]-r['actual'])<int(k)if op=='lt'else abs(r[product]-r['actual'])<=int(k)for r in good)
    prec[name]=dict(numerator=hits,denominator=len(good),rate=hits/len(good))
   rows.append(dict(record_id='B-COVERED-GAMES-'+h([proc,target,product])[:24],record_kind='forecast_evaluation_view',procedure_id=proc,target=target,product_id=product,
    evaluation_panel_id='B-2026-W5-W8-QB-COVERED56GAMES-NATIVE-v1',history_regime='H-RECENT',feature_memory_policy='2022_EXPANDING',
    season=2026,week='COVERED_GAME_W5_W8',evaluation_seasons=[2026],evaluation_weeks=[5,6,7,8],period='full_game',statistic_period='full_game',season_type='REG',overtime=True,position='QB',
    population='RETROSPECTIVE_OFFICIAL_QB_STAT_ROWS_NOT_EXANTE_ROSTER',fallback_view='FULL_SYSTEM',**m,forecast_rows=129,outer_query_rows=129,technical_unavailable=0,
    fallback_rows=sum(r['fallback']not in(None,'none')for r in subset),scored_fallback_rows=sum(r['fallback']not in(None,'none')for r in good),
    unique_games=len({r['game_id']for r in subset}),unique_players=len({r['player_id']for r in subset}),unique_player_games=len(subset),
    query_membership_sha256=h(sorted((r['game_id'],r['player_id'],target)for r in subset)),precision_counts=prec,
    evidence='RETROSPECTIVE_NUMERICAL_POPULATION_DIAGNOSTIC_SAVED_OUTPUTS_NO_REFIT',source_vintage='CURRENT_REVISED_SOURCE_SEVEN_DAY_RECONSTRUCTION',
    horizon_id='KICKOFF_LEFT_LIMIT_SEVEN_DAY_RECONSTRUCTION',original_issuance=False,selection_evidence='NO_NEW_SELECTION_POLICY_OR_LINES',
    coverage=dict(full_sameweek_QB_queries=131,covered_game_QB_queries=129,offered_QB_queries=112,query_rows_in_missing_game=2,not_offered_within_covered_games=17),
    new_fits=0,new_forecasts=0,new_prop_grades=0,new_NFLobservations=0,source_board_membership_unverified_quote_timing=True,
    native_metric_note='Same56gamesandweeksforcovered129vsoffered112. Counts/pointlosses only; no offeredlineinventedforthe17otherQBqueries.'))
 p=a.out/'SCORES.json';assert not p.exists();p.write_text(json.dumps(rows,separators=(',',':'),allow_nan=False)+'\n')
 p=a.out/'COVERED_GAME_PREDICTION_BINDINGS_V1.json';p.write_text(json.dumps(dict(parent_prediction_artifacts=bindings,score_sha256=sha(a.out/'SCORES.json'),source_board_bindings=sources,new_score_views=len(rows),new_NFLobservations=0),indent=2)+'\n')
 print(json.dumps(dict(new_views=len(rows),summary=[dict(procedure_id=r['procedure_id'],product=r['product_id'],n=r['n'],games=r['unique_games'],MAE=r['mae'],bias=r['bias'])for r in rows])))
if __name__=='__main__':main()
