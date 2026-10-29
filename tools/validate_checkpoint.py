#!/usr/bin/env python3
"""Validate retained checkpoint artifacts without source-row or network access."""
import csv,hashlib,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
def main():
 parsed=0
 for p in ROOT.rglob('*.json'):
  if '.git' in p.parts:continue
  json.loads(p.read_text(),parse_constant=lambda v:(_ for _ in ()).throw(ValueError('nonfinite JSON')));parsed+=1
 grid=json.loads((ROOT/'registries/EXPERIMENT_GRID.json').read_text())
 assert len({x['cell_id'] for x in grid})==len(grid)
 targets={'pass_yd','pass_td','pass_cmp','pass_att','pass_int','rush_yd','rush_att','rec','rec_yd','rush_rec_yd','nick-chart-ppr-v1','anytime_td'}
 rank=json.loads((ROOT/'reports/TOP5_BY_CATEGORY_PRODUCT.json').read_text())
 assert {x['target'] for x in rank}==targets
 assert all(x['rank'] is None and x['score'] is None for x in rank)
 refs=json.loads((ROOT/'registries/PROCEDURE_REFERENCES.json').read_text())
 for x in refs:
  a={c['history_regime'] for c in grid if c.get('procedure_reference_id')==x['reference_id']}
  assert {'H-CURRENT','H-RECENT','H-MULTI'}<=a
 requests=json.loads((ROOT/'registries/REQUESTS.json').read_text())
 assert len({x['request_id'] for x in requests})==len(requests)
 assert len([x for x in requests if x['request_id'][-1:].isdigit() and x['request_id'].rstrip('12345') in {'PY','PA','PC','PT','PI','RA','RY','R','REY','RR','AT','PPR'}])==60
 scores=json.loads((ROOT/'reports/ALL_METHOD_SCORES.json').read_text())
 assert sum(x['evidence']=='REPORTED_NOT_REPRODUCED' for x in scores)==4832
 assert sum(x['evidence']=='REPRODUCED_FROM_DATA' for x in scores)==66
 assert len({x['record_id'] for x in scores})==len(scores)
 receipt=json.loads((ROOT/'reports/replay/REPLAY_RECEIPT.json').read_text())
 assert receipt['reproduction_checks']==receipt['reproduction_passed']==168
 assert receipt['new_fits']==receipt['new_forecasts']==0
 assert receipt['supported_unique_player_game_target']==59 and receipt['outcome_games']==1
 with (ROOT/'registries/EXECUTIONS.jsonl').open() as f:
  executions=[json.loads(line) for line in f if line.strip()]
 assert len({x['run_id'] for x in executions})==len(executions)
 for directory in ('reports','registries','docs','config'):
  for p in (ROOT/directory).rglob('*'):
   if p.is_file() and p.suffix in ('.json','.csv','.md','.jsonl'):
    s=p.read_text();assert not any(token in s for token in ('s3://','sediment://','/workspace/','sk-proj-')),(p,'private locator or credential marker')
 for pair in [('reports/ALL_METHOD_SCORES',len(scores)),('registries/EXPERIMENT_GRID',len(grid)),('registries/REQUEST_METHOD_CROSSWALK',len(requests))]:
  with (ROOT/(pair[0]+'.csv')).open() as f:assert len(list(csv.DictReader(f)))==pair[1]
 print(json.dumps({'status':'PASS','JSON_files_parsed':parsed,'grid_cells':len(grid),'request_index_items':len(requests),'reported_cells':4832,'reproduced_primary_all_role_views':66,'initial_checkpoint_new_fits':0,'scope':'initial-checkpoint artifact/schema/privacy-marker checks; continuation fits are recorded in their separate run receipts; not independent NFLtruth'}))
if __name__=='__main__':main()
