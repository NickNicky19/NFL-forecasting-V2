"""Render postforecast component diagnostics; never fit, select or issue picks."""
import argparse,collections,datetime,gzip,hashlib,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'reports/information-skill-01/B'
def read(p):
 b=p.read_bytes();return json.loads(gzip.decompress(b)if p.suffix=='.gz'else b)
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--offered-graded-rows',type=Path,required=True);args=parser.parse_args()
 paths=sorted((BASE/'wave-v1/component-metrics').glob('*.json.gz'));rr=[r for p in paths for r in read(p)['rows']]
 private=args.offered_graded_rows
 offermask={(r['game_id'],r['player_id'])for r in read(private)['rows']if r['category']=='pass_cmp'};assert len(offermask)==142
 groups=[]
 mean=lambda a:sum(a)/len(a)if a else None
 for population in('BROAD_CONDITIONAL_STAT_ROW','IDENTICAL_NATIVE_OFFERED_PLAYER_MASK'):
  source=[r for r in rr if population.startswith('BROAD')or(r['game_id'],r['player_id'])in offermask]
  for method in('SKILL_C0','SKILL_C1','SKILL_R0','SKILL_R1'):
   for window in['ALL']+sorted({r['week']for r in source}):
    z=[r for r in source if r['method']==method and(window=='ALL'or r['week']==window)]
    valid=[r for r in z if r['physical_participation']and r['target_parity']]
    exposed=[r for r in valid if r['observed_attempts']>0]
    total=sum(r['observed_attempts']for r in exposed)
    attempts_error=[];workloadterm=[];conversionterm=[];diagnostic=[];forecast=[];nll=[];brier=[]
    for r in valid:
     a,c,p=r['observed_attempts'],r['observed_completions'],r['predicted_conversion'];u=r['predicted_attempt_mean']
     w=(u-a)*p;v=a*p-c;e=r['predicted_completion_mean']-c
     assert abs(w+v-e)<1e-10
     attempts_error.append(abs(u-a));workloadterm.append(abs(w));conversionterm.append(abs(v));diagnostic.append(abs(a*p-c));forecast.append(abs(e))
    for r in exposed:nll.append(r['mix_cross_entropy']);brier.append(r['mix_multinomial_Brier'])
    groups.append(dict(population=population,method=method,window=window,actual_weeks=sorted({r['week']for r in z}),eligible=len(z),qualified_component_games=len(valid),conversion_exposure_games=len(exposed),zero_attempt_games=len(valid)-len(exposed),unknown_or_incompatible=len(z)-len(valid),observed_attempts=total,
      context_cross_entropy_per_player_game=mean(nll),context_cross_entropy_per_attempt=sum(r['observed_attempts']*r['mix_cross_entropy']for r in exposed)/total if total else None,
      context_multiclass_Brier_per_player_game=mean(brier),conditional_conversion_logloss_per_attempt=sum(r['observed_attempts']*r['conditional_conversion_logloss']for r in exposed)/total if total else None,
      aggregate_observed_completion_rate=sum(r['observed_completions']for r in exposed)/total if total else None,
      actual_attempt_weighted_predicted_conversion=sum(r['observed_attempts']*r['predicted_conversion']for r in exposed)/total if total else None,
      attempt_mean_MAE=mean(attempts_error),full_completion_mean_MAE=mean(forecast),absolute_workload_error_term_mean=mean(workloadterm),absolute_conversion_error_term_mean=mean(conversionterm),
      actual_attempt_diagnostic_MAE=mean(diagnostic),diagnostic_label='NONDEPLOYABLE_ACTUAL_ATTEMPT_SUBSTITUTION;NOT_AN_ELIGIBLE_FORECAST',
      decomposition='e_C=(predicted_A-actual_A)*predicted_p+(actual_A*predicted_p-actual_C); signed terms add, absolute magnitudes do not; no causal percentage attribution'))
 result=dict(id='B_INFORMATION_SKILL_COMPONENT_DIAGNOSTICS_v1',UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in paths},private_offer_mask_source_sha256=hashlib.sha256(private.read_bytes()).hexdigest(),source_rows_unchanged=True,new_predictions=0,new_fits=0,new_offer_grades=0,metrics_are_postforecast_diagnostics_not_pregame_inputs=True,rows=groups)
 p=BASE/'COMPONENT_DIAGNOSTICS_V1.json';assert not p.exists();p.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
 for r in groups:
  if r['window']=='ALL':print(json.dumps({k:r[k]for k in('population','method','qualified_component_games','context_cross_entropy_per_attempt','conditional_conversion_logloss_per_attempt','attempt_mean_MAE','full_completion_mean_MAE','absolute_workload_error_term_mean','absolute_conversion_error_term_mean','actual_attempt_diagnostic_MAE')}))
if __name__=='__main__':main()
