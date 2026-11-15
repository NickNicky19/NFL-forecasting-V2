"""Typed saved-origin adapter; caller supplies qualified canonical queries.

No source acquisition, fit, credentials, arbitrary deserialization or grading.
Private callers must retain original offer and issuance clocks separately.
"""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools.run_player_context_wave import read,write
from nfl_v2.opportunity_information import restore_law
from nfl_v2.player_context_matchup import exact_probabilities
def main():
 p=argparse.ArgumentParser();p.add_argument('--predictions',type=Path,required=True);p.add_argument('--queries',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if a.output.resolve().is_relative_to(ROOT):raise ValueError('Owner-local raw joins must remain outside public repository')
 saved={}
 for f in sorted(a.predictions.glob('2026-W*.json.gz')):
  for r in read(f)['rows']:
   key=(r['method'],r['game_id'],r['player_id'],r['target'])
   if key in saved:raise ValueError('Duplicate saved prediction')
   saved[key]=r
 out=[]
 body=read(a.queries);queries=body['rows']if isinstance(body,dict)else body
 for q in queries:
  key=tuple(q[k]for k in ('method','game_id','player_id','target'));r=saved.get(key)
  if r is None:out.append(dict(query=q,status='UNAVAILABLE_FORECAST'));continue
  for k in ('team','opponent','season','week'):
   if k in q and q[k]!=r[k]:raise ValueError('Canonical context mismatch: '+k)
  law=restore_law(r['law']);row=dict(query=q,procedure_id=r['procedure_id'],point=r['mean'],lower_median=r['lower_median'],output_type='CORRECT_EXPECTED_COUNT',fallback=r['fallback'],status='READY',historical_reconstruction=True)
  if q.get('line')is not None:
   probs=exact_probabilities(law,q['line']);row['probs']=probs
   row['law_side']='OVER'if probs['over']>probs['under']else'UNDER'if probs['under']>probs['over']else'ABSTAIN'
   row['mean_side']='OVER'if row['point']>q['line']else'UNDER'if row['point']<q['line']else'ABSTAIN'
  out.append(row)
 a.output.parent.mkdir(parents=True,exist_ok=True)
 if a.output.exists():raise FileExistsError('Never overwrite old protected join')
 a.output.write_text(json.dumps(dict(rows=out),allow_nan=False)+'\n')
if __name__=='__main__':main()
