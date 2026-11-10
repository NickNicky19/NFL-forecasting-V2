"""Bounded invariance/adapter and fitted-field use checks, no refitting."""
import copy,gzip,hashlib,json,math,sys
from collections import Counter,defaultdict
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[4];OUT=Path(__file__).resolve().parent;BASE=OUT.parent;WAVE=BASE/'opportunity-wave-v1'
sys.path.insert(0,str(ROOT))
from nfl_v2 import player_context_matchup as ctx,qb_opportunity_increment as inc
from nfl_v2.passing_opportunity_profiles import OpportunityHistory
from nfl_v2.qb_opportunity_adapter import QBOpportunityAdapter
def read(p):
    p=Path(p);b=p.read_bytes();return json.loads(gzip.decompress(b)if p.suffix=='.gz'else b)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

orders=read(WAVE/'FEATURE_ORDER_V1.json')['orders'];counts=defaultdict(Counter);used=defaultdict(set);models=Counter()
for p in sorted((WAVE/'fits').glob('*.json.gz')):
    record=read(p);arm=record['slot'].rsplit('-',1)[-1];model=record['model'];names=orders[arm];width=len(names);assert len(model['design']['median'])==width
    models[arm]+=1
    for tree in model['trees']:
        for f in tree['feature']:
            if f<0:continue
            assert f<2*width
            name=names[f%width];block=name.split(':',1)[0]if ':'in name else'RETAINED_E3'
            counts[arm][block]+=1;counts[arm]['ALL_SPLITS']+=1;used[arm].add(name+(':AUTO_MISSING'if f>=width else''))

# Fixed current origin, chosen before score inspection as in verifier scope.
protocol=WAVE/'FROZEN_PROTOCOL.json';model=WAVE/'fits/2026-W05-R3.json.gz'
adapter=QBOpportunityAdapter(ROOT,protocol,WAVE/'FEATURE_ORDER_V1.json',model,arm='R3',expected_protocol_sha256=sha(protocol),expected_model_sha256=sha(model))
q=copy.deepcopy(next(r for r in adapter.inputs if(r['season'],r['week'])==(2026,5)))
q['query_evidence']=dict(canonical_identity_verified=True,historical_team_verified=True,eligible_role_verified=True,source_id='SYNTHETIC_BOUND_ADAPTER_INVARIANCE_FIXTURE',source_sha256='c'*64,recorded_at=q['kickoff']-1)
for name in('official_completions','official_attempts','attempts','completions','physical_participation','target_parity','available','label_status','context_attempts','context_completions'):q.pop(name,None)
clock=dict(policy_id='SYNTHETIC_SOFTWARE_CLOCK_NOT_REAL_CAPTURE',evidence_sha256='d'*64,registered_at=q['kickoff']-2,source_received_at=q['kickoff']-1,source_expires_at=q['kickoff']+1000,model_expires_at=q['kickoff']+1000)
def predict(a,query):return a.predict(query,feature_names=a.expected_feature_order,clock_contract=clock,request_at=q['kickoff'],line=19.5)
baseline=predict(adapter,q);assert baseline['status']=='READY_ADAPTER_INFERENCE'
target=copy.deepcopy(q);target.update(official_completions=99999,official_attempts=99999,attempts=99999,completions=99999,actual_depth_mix=[99999]*25,available=None)
assert predict(adapter,target)==baseline
base_features=inc.direct_features(q,adapter.history,adapter.opportunity,'R3')
changed=copy.deepcopy(adapter.inputs);mutated_rows=0
for r in changed:
    if r['available']>=q['kickoff']:
        r['official_completions']=12345;r['official_attempts']=24690;r['attempts']=24690;r['completions']=12345
        r['context_attempts']=[24690]+[0]*24;r['context_completions']=[12345]+[0]*24;mutated_rows+=1
future=copy.deepcopy(changed[-1]);future.update(game_id='SYNTHETIC_FAR_FUTURE_GAME',season=2027,week=1,kickoff=q['kickoff']+100000000,available=q['kickoff']+100000000+604800);changed.append(future)
changed.sort(key=lambda r:(r['kickoff'],r['game_id'],r['player_id']))
original_membership=[(r['game_id'],r['player_id'],r['official_completions'])for r in adapter.inputs if r['physical_participation']and r['target_parity']and r['season']>=2025 and r['available']<adapter.fit_cutoff]
mutated_membership=[(r['game_id'],r['player_id'],r['official_completions'])for r in changed if r['physical_participation']and r['target_parity']and r['season']>=2025 and r['available']<adapter.fit_cutoff]
assert original_membership==mutated_membership
source=read(BASE/'source-profiles/PASSING_OPPORTUNITY_GAME_INPUTS_V2.json.gz')
source_changes=0
for group in('team_games','QB_games'):
    for r in source[group]:
        if r['available']>=q['kickoff']:
            r['counts']={k:v+99999 for k,v in r['counts'].items()}
            for cells in r['cells'].values():
                for cell in cells:
                    for k in cell:cell[k]+=99999
            source_changes+=1
adapter.history=ctx.ContextHistory(changed,8,20);adapter.opportunity=OpportunityHistory(source['team_games'],source['QB_games'])
mutated_features=inc.direct_features(q,adapter.history,adapter.opportunity,'R3')
assert np.array_equal(base_features,mutated_features,equal_nan=True)
assert predict(adapter,q)==baseline
wrong=adapter.expected_feature_order;wrong[0],wrong[1]=wrong[1],wrong[0]
try:adapter.predict(q,feature_names=wrong,clock_contract=clock,request_at=q['kickoff'])
except ValueError as e:assert str(e)=='Named feature order mismatch'
else:raise AssertionError('Same-width wrong order accepted')
batch=adapter.predict_batch([q],feature_names=adapter.expected_feature_order,clock_contract=clock,request_at=q['kickoff'],lines=[19.5]);assert batch==[baseline]
receipt=dict(id='B-OPPORTUNITY-MUTATION-FEATURE-USE-INDEPENDENT-v1',status='PASS_IN_CHECKED_SCOPE',model_counts=dict(models),split_counts={k:dict(v)for k,v in counts.items()},used_named_features={k:sorted(v)for k,v in used.items()},feature_use_claim='Inputs reached fitted trees; split frequency is descriptive software-path evidence, not causal importance or proof of predictive gain. Legitimate no-use remains permitted.',mutation_scope=dict(origin=[2026,5],arm='R3',forecast_model_sha256=sha(model),adapter_sha256=sha(ROOT/'nfl_v2/qb_opportunity_adapter.py'),mutated_future_QB_label_rows=mutated_rows,mutated_future_source_rows=source_changes,appended_future_rows=1,target_outcomes_and_realized_context_ignored=True,earlier_training_labels_and_membership_unchanged=True,feature_arrays_equal=True,adapter_output_equal=True,same_width_wrong_order_rejected=True,batch_single_equal=True),new_fits=0,new_issued_forecasts=0,limits=['Mutation check verifies fixed earlier-only construction, not unavailable original historical source vintage.','Synthetic membership/expiry fixtures are software evidence, not actual current-query qualification, capture, consumer receipt or deployment.','Unchanged forest-family representative fresh-fit review reused; no independent fresh augmented fit claimed.'])
dest=OUT/'MUTATION_FEATURE_USE_INDEPENDENT_REVIEW_V1.json';assert not dest.exists();dest.write_text(json.dumps(receipt,indent=2,allow_nan=False)+'\n')
print(json.dumps({k:v for k,v in receipt.items()if k!='used_named_features'},indent=2))
