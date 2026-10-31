"""Prepared147-cell strict-current2026 adapter. No fit or capture entrypoint."""
import hashlib,json
from pathlib import Path
import numpy as np
from . import hgb_control as source, empirical_benchmark as empirical
VERSION='v2-original-hgb-2026-strict-retrospective-design-v1'
def current_rows(rows):
 return [r for r in rows if r['season']==2026 and 1<=r['week']<=7]
def training_rows(rows,target,origin,roles):
 return [r for r in current_rows(rows) if r['position']in roles and r['available']<origin and r['values'][target]is not None]
def training_features(rows,target,origin,roles):
 pool=training_rows(rows,target,origin,roles);history=source.FeatureHistory(current_rows(rows));x=[];maxima=[]
 for row in pool:
  features,latest=history.get(row['player_id'],row['position'],target,row['kickoff'])
  if latest is not None and latest>=row['kickoff']:raise ValueError('historical training feature chronology')
  x.append(features);maxima.append(latest)
 return pool,np.asarray(x),maxima
def query_features(rows,player,position,target,cutoff):
 x,latest=source.FeatureHistory(current_rows(rows)).get(player,position,target,cutoff)
 if latest is not None and latest>=cutoff:raise ValueError('query chronology')
 return x,latest
def fit_eligible(values,target):return len(values)>=40 and(target!='anytime_td'or len(set(values))==2)
def fallback(rows,target,player,position,cutoff,objective):
 pool=[r for r in current_rows(rows)if r['available']<cutoff and r['values'][target]is not None and r['position']==position];own=[r for r in pool if r['player_id']==player];chosen=own or pool;values=[r['values'][target]for r in chosen]
 if not values:return dict(value=0.,fallback='constant_zero',n=0,own_n=0)
 value=sorted(values)[(len(values)-1)//2]if objective=='absolute_error_point'else sum(values)/len(values)
 return dict(value=value,fallback='own_empirical'if own else'position_empirical',n=len(values),own_n=len(own))
def prepare(*,queries,base_protocol,output,private_output):
 output,private_output=Path(output),Path(private_output);output.mkdir(parents=True);private_output.mkdir(parents=True);old=json.loads(Path(base_protocol).read_text());allqueries=json.loads(Path(queries).read_text())['historical'];frozen=[q for q in allqueries if q['season']==2026 and 1<=q['week']<=7 and q['target']in source.TARGETS]
 if len(frozen)!=15574 or len({q['game_id']for q in frozen})!=107:raise ValueError('original fixedhistoricalmembershiprequired')
 source.immutable_json(private_output/'FROZEN_QUERY_METADATA.json',frozen);grid=[dict(week=week,target=target,objective=objective,history_regime='H-CURRENT',policy_id='H-CURRENT-STRICT',procedure_id='hgb-direct-history-controls-v1:'+objective+':strict-current-inputs',state='PREPARED_NOT_FITTED',fit_floor=2026,feature_memory_floor=2026)for week in range(1,8)for target in source.TARGETS for objective in source.objectives(target)]
 assert len(grid)==147
 p=dict(version=VERSION,state='PREPARED_ONLY_NO_EXECUTION_AUTHORIZATION_IN_THIS_SUBTASK',registered_at=source.now(),code_sha256=source.sha(__file__),helpers={Path(m.__file__).name:source.sha(m.__file__)for m in(source,empirical)},source_ids=old['source_ids'],original_protocol_sha256=source.sha(base_protocol),original_query_packet_sha256=source.sha(queries),frozen_historical_query_sha256=source.sha(private_output/'FROZEN_QUERY_METADATA.json'),query_cells=15574,player_games=len({(q['game_id'],q['player_id'])for q in frozen}),games=107,evaluation_season=2026,evaluation_weeks=list(range(1,8)),grid=grid,nominal_fit_opportunities=147,source_role_contract=old['source_role_contract'],feature_contract=old['feature_contract'],params=source.PARAMS,feature_memory='Onlyeligible2026REGW1–7NFLoutcomes, no olderNFLlabels/features/priors/calibration/playerencodings/retrieval/transformtraining. Architecture/settingspreviouslychosenandexposed.',chronology='Sameoriginalweeklyearliestkickoffrefitclock;labels kickoff+7daysstrictlybeforeorigin;trainingfeatures atownkickoff;pergamequeryfeatures atkickoffleft-limit;notrelabeledT90',startup='Min40rows/binarytwo-class requirement; same2026-onlyownhistory thenpositionempirical, thenliteral0; fullsystemW1retained; commonlearnedmaskseparate',reuse='Do not refit completedcommon-memory2026equivalents. This strictpolicy hasdifferentfeatureframe; source2026futurestrict21models have a latercutoff and cannotstandinforhistoricalweeklymodels.',future='No newWeek8capture oroutcomes; existingfuturestrictadapterremainsunchanged',chart='Outsideoriginal11-targetHGBrecipe; notsilentlyadded. Existingchartfamiliesretain theirresults.',budget_prepared=dict(max_fit_calls=147,wall_seconds=600,cpu_seconds=900,max_threads=2,max_rss_bytes=2147483648,max_private_bytes=268435456,hyperparameter_searches=0),execution_prerequisites=['Rootsole-workercoordination andexplicitfuturewaveexecutionregistration','Independentprefitreviewofcompletedrunner/resourceguards','Retainnewmodels/queryrows/predictionswithsafehashesandprivatecapacity','Independentnative/error/scorerchecksandmatchedexistingcommonpolicycomparison'],new_fit_calls=0,new_forecasts=0,CURRENT_2026_Week8_outcomes_read=0)
 source.immutable_json(output/'PREPARED_PROTOCOL_NO_FITS.json',p);return p
