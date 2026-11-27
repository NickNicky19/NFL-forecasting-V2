"""Prepare one proposed completion-classifier panel, without fitting a model.

The protected native rows stay in memory. Public output contains only schema,
counts and cryptographic commitments. No TabICL/PyTorch import, installation,
download, model load, prediction, grading, or allocation grant occurs here.
"""
from __future__ import annotations
import argparse,collections,hashlib,json,math,resource,sys,time
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from nfl_v2 import player_context_matchup as ctx
from nfl_v2.hgb_control import FEATURES
from tools.run_player_context_wave import read,sha,write,now
SOURCE_SHA='dbdbf73a23fea1d7d8c90fde666163853f492b0e9686ae068b829b2bc2816a39'
CONTEXT=ROOT/'reports/information-first-20261112-01/B/completion-wave-v1/QB_CONTEXT_W1_W9_INPUTS_V1.json.gz'
CONTEXT_SHA='45aaab99d41f2e2643066c001355b26430f55dca06e7c7e366eace252f2e021b'
OUT=ROOT/'reports/predictive-value-next-01/B/TABICLV2_INPUT_ADMISSION_V1.json'
def instant(v):
 if isinstance(v,(float,int)):return float(v)
 return datetime.fromisoformat(v.replace('Z','+00:00')).timestamp()
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--existing-cmp-grades',type=Path,required=True);a=p.parse_args();start=time.process_time()
 if sha(a.existing_cmp_grades)!=SOURCE_SHA or sha(CONTEXT)!=CONTEXT_SHA:raise ValueError('Frozen approved source hashes differ')
 body=read(a.existing_cmp_grades);source=body['rows']if isinstance(body,dict)else body
 rows=[r for r in source if r['model_key']=='B0'and r['policy']=='P1_MEAN']
 if len(rows)!=142 or len({(r['game_id'],r['player_id'],r.get('target',r.get('category')))for r in rows})!=142:raise ValueError('Exact deduplicated native142 required')
 contexts=ctx.load_inputs(CONTEXT);history=ctx.ContextHistory(contexts,8,20.);lookup={(r['game_id'],r['player_id']):r for r in contexts}
 records=[];clock_differences=0
 for r in rows:
  q=lookup[r['game_id'],r['player_id']]
  if r.get('target',r.get('category'))!='pass_cmp'or r.get('actual')is None or not r['available'] or float(r['line'])%1!=.5:raise ValueError('Qualified halfpoint completion contract required')
  if not q.get('physical_participation')or not q.get('target_parity')or q['official_completions']!=r['actual']:raise ValueError('Existing qualified actual identity differs')
  if q['available']!=q['kickoff']+7*86400:raise ValueError('Do not change retained seven-day reconstruction')
  x,info=history.base_history.get(q['player_id'],'QB','pass_cmp',q['kickoff']);x=np.r_[np.asarray(x,float),float(r['line'])]
  if len(x)!=len(FEATURES)+1:raise ValueError('Fixed feature order')
  if q['season']!=2026 or q['week']!=r['week']:raise ValueError('Canonical origin mismatch')
  clock_differences+=instant(r['kickoff'])!=q['kickoff']
  records.append(dict(game_id=q['game_id'],player_id=q['player_id'],week=r['week'],kickoff=q['kickoff'],label_available=q['available'],y=int(r['actual']>r['line']),x=x))
 expected={5:28,6:28,7:28,8:28,9:30}
 if dict(collections.Counter(r['week']for r in records))!=expected:raise ValueError('Frozen weekly board differs')
 folds=[]
 for w in range(5,10):
  tests=[r for r in records if r['week']==w];origin=min(r['kickoff']for r in tests);games={r['game_id']for r in tests}
  train=[r for r in records if r['label_available']<origin and r['game_id']not in games]
  if any(r['kickoff']>=origin for r in train):raise ValueError('Future row entered training')
  def commitment(rr):return digest(sorted((r['game_id'],r['player_id'],r['week'])for r in rr))
  def matrix_commitment(rr):
   # Explicit missingness bytes and finite-value bytes, no NaN JSON ambiguity.
   z=np.asarray([r['x']for r in rr],dtype='<f8').reshape(len(rr),len(FEATURES)+1)
   return hashlib.sha256(np.isfinite(z).tobytes()+np.where(np.isfinite(z),z,0.).tobytes()).hexdigest()
  folds.append(dict(week=w,fit_cutoff_UTC=datetime.fromtimestamp(origin,timezone.utc).isoformat(),test_rows=len(tests),training_rows=len(train),training_Over=sum(r['y']for r in train),training_Under=sum(1-r['y']for r in train),training_games=len({r['game_id']for r in train}),test_games=len(games),train_membership_sha256=commitment(train),test_membership_sha256=commitment(tests),train_design_sha256=matrix_commitment(train),query_design_sha256=matrix_commitment(tests),startup_fallback=len(train)==0))
 if [r['training_rows']for r in folds]!=[0,0,28,56,86]:raise ValueError('Stop and investigate changed earlier-label context')
 write(OUT,dict(id='B-TABICLV2-CMP-DIRECT-PILOT-INPUT-v1',UTC=now(),state='PREPARED_NO_FIT_NO_PREDICTION_NO_ALLOCATION',feature_order=list(FEATURES)+['offered_halfpoint_line'],folds=folds,eligible=142,unique_player_games=142,games=len({r['game_id']for r in records}),available_actual_offer_weeks=[5,6,7,8,9],missing_actual_offer_weeks=[1,2,3,4],learned_candidate_weeks=[7,8,9],startup_fallback_weeks=[5,6],startup_fallback_rows=56,learned_query_rows=86,source_grade_sha256=SOURCE_SHA,context_sha256=CONTEXT_SHA,preparation_code_sha256=sha(Path(__file__)),source_canonical_clock_differences=clock_differences,clock_scope='Retained canonical feature/query clocks and prior +7d labels; source clock retained separately in original admitted grade/source bindings. No new clock or identity relabeling.',evidence='CURRENT_VINTAGE7DAY_RECONSTRUCTION;QUOTE_CLOCK_UNKNOWN;MAIN_ALT_UNCLASSIFIED;EXPOSED;STATROW_CONDITIONAL_UNIVERSE',split='Whole game excluded at origin; repeated books already deduplicated; no heldout labels used in raw features. Preprocessing not fitted here.',private_rows_written=0,new_fits=0,new_predictions=0,new_grades=0,new_CPU_allowance=0,incremental_CPU_seconds=time.process_time()-start,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024))
 print(json.dumps(dict(state='PREPARED_NO_FIT',fold_training_rows=[r['training_rows']for r in folds],features=len(FEATURES)+1,clock_differences=clock_differences,CPU_seconds=time.process_time()-start)))
if __name__=='__main__':main()
