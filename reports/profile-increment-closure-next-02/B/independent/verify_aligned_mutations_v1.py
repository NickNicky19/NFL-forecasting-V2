"""Actual new policy-path invariance with saved typed model, no refit."""
import copy,gzip,hashlib,importlib.util,json,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[4];OUT=Path(__file__).resolve().parent;BASE=OUT.parent;WAVE=BASE/'aligned-wave-v1'
sys.path.insert(0,str(ROOT))
from nfl_v2.qb_aligned_freshness import AlignedFreshnessBundle,ALTERNATIVE
def read(p):
 p=Path(p);b=p.read_bytes();return json.loads(gzip.decompress(b)if p.suffix=='.gz'else b)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
inputs=read(ROOT/'reports/player-context-matchup-01/B/source-fields-v3/DERIVED_QB_GAME_INPUTS.json.gz');source=read(ROOT/'reports/profile-increment-to-release-01/B/source-profiles/PASSING_OPPORTUNITY_GAME_INPUTS_V2.json.gz')
original=AlignedFreshnessBundle(inputs,source,policy_id=ALTERNATIVE)
q=copy.deepcopy(min((r for r in inputs if(r['season'],r['week'])==(2025,1)),key=lambda r:(r['kickoff'],r['game_id'],r['player_id'])))
cutoff=q['kickoff'];query={k:q[k]for k in('game_id','player_id','team','opponent','season','week','kickoff')}
changed=copy.deepcopy(inputs);changed_source=copy.deepcopy(source);mutated=0;mutated_source=0
for r in changed:
 if r['kickoff']+172800>=cutoff:
  r['official_completions']=12345;r['official_attempts']=24690;r['attempts']=24690;r['completions']=12345;r['context_attempts']=[24690]+[0]*24;r['context_completions']=[12345]+[0]*24;mutated+=1
future=copy.deepcopy(changed[-1]);future.update(game_id='SYNTHETIC_FAR_FUTURE_GAME',kickoff=cutoff+100000000,available=cutoff+100000000+604800,season=2027,week=1);changed.append(future)
for group in('team_games','QB_games'):
 for r in changed_source[group]:
  if r['kickoff']+172800>=cutoff:
   for k in r['counts']:r['counts'][k]+=99999
   for cells in r['cells'].values():
    for cell in cells:
     for k in cell:cell[k]+=99999
   mutated_source+=1
new=AlignedFreshnessBundle(changed,changed_source,policy_id=ALTERNATIVE)
spec=importlib.util.spec_from_file_location('manual_tree',ROOT/'reports/profile-increment-to-release-01/B/independent/verify_pilot_inference_v1.py');manual=importlib.util.module_from_spec(spec);spec.loader.exec_module(manual)
checks=[]
for arm in('F2','F3'):
 record=read(WAVE/'fits'/('2025-W01-'+arm+'.json.gz'));fit_cutoff=record['fit_cutoff'];training=original.training_rows(2025,fit_cutoff);modified=new.training_rows(2025,fit_cutoff)
 assert[(r['game_id'],r['player_id'],r['official_completions'])for r in training]==[(r['game_id'],r['player_id'],r['official_completions'])for r in modified]
 baseline=original.direct_features(query,arm);altered=new.direct_features(query,arm);assert np.array_equal(baseline,altered,equal_nan=True)
 with_target=dict(query,official_attempts=99999,official_completions=99999,actual_down_mix=[99999]*25,available=None)
 assert np.array_equal(baseline,new.direct_features(with_target,arm),equal_nan=True)
 mu=max(.05,sum(r['official_completions']for r in training)/len(training));priorq=mu/(1+mu)
 bm,bmed,bw,bcdf=manual.manual_law(record['model'],baseline,priorq);am,amed,aw,acdf=manual.manual_law(record['model'],altered,priorq)
 assert bm==am and bmed==amed and np.array_equal(bw,aw)
 checks.append(dict(arm=arm,feature_width=len(baseline),feature_equal=True,training_and_prior_unchanged=True,saved_model_mean_median_mass_equal=True,model_sha256=sha(WAVE/'fits'/('2025-W01-'+arm+'.json.gz'))))
receipt=dict(id='B-ALIGNED-FIXED-POLICY-MUTATION-INDEPENDENT-v1',status='PASS_IN_CHECKED_SCOPE',origin=[2025,1],wrapper_sha256=sha(ROOT/'nfl_v2/qb_aligned_freshness.py'),mutated_not_yet_48h_eligible_QB_rows=mutated,mutated_not_yet_48h_eligible_source_rows=mutated_source,added_future_rows=1,target_outcomes_and_realized_context_ignored=True,checks=checks,new_fits=0,new_original_forecasts=0,limits=['Futuremutation uses the48hpolicyeligibility, not the old7dmask: newlyeligibleoldergames arelegitimateF2/F3inputs.','This checks actualinternalpolicyfeature/saved-modelpath; nocurrentqualifieduniverse,capture,fullconsumeradapterorhistoricalsourceauthentication isclaimed.'])
dest=OUT/'ALIGNED_MUTATION_INDEPENDENT_REVIEW_V1.json';assert not dest.exists();dest.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
