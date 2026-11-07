"""Additional metadata/value-copy lineage audit; does not recompute grades or losses."""
import argparse,gzip,hashlib,json,datetime
from pathlib import Path
HERE=Path(__file__).resolve().parent
def read(p):return json.loads(Path(p).read_bytes())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--private-root',type=Path,required=True);a=ap.parse_args();q=a.private_root;joined=json.loads(gzip.decompress((q/'ORIGINAL_JOINED_ROWS_V1.json.gz').read_bytes()))['rows'];grades=json.loads(gzip.decompress((q/'ORIGINAL_AND_TOP_GRADED_ROWS_V1.json.gz').read_bytes()))['rows'];by={r['source_row_index']:r for r in joined};n=fields=flags=0
 for r in grades:
  if not r['panel'].startswith('ORIGINAL_'):continue
  original=by[r['source_row_index']]
  for k,v in original.items():assert r[k]==v;fields+=1
  n+=1
 for r in joined:
  b=read(q/'source-metadata'/('board-'+r['source_head']+'.json'));key=r['source_player_id'],r['source_game_id'],r['target']
  for side,flag in(('over','top_over'),('under','top_under')):
   membership={(str(x.get('player_id')),str(x.get('game_id')),x.get('key'))for x in b.get('picks',{}).get(side,[])};assert r[flag]==(key in membership);flags+=1
 top=0
 for r in grades:
  if not r['panel'].startswith('SAVED_TOP_LIST:'):continue
  p=read(q/'source-metadata'/('selected-'+r['panel'].split(':')[1]+'.json'));rows=[x for side,rr in p['picks'].items()for x in rr if x['direction']==r['selected_side']and str(x['player_id'])==r['source_player_id']and str(x['game_id'])==r['source_game_id']and x['key']==r['target']];assert len(rows)==1;top+=1
 census=[]
 for p in(q/'source-metadata').glob('selected-*.json'):
  x=read(p);census.append((x.get('season'),x.get('week')))
 output={'state':'PASS_ORIGINAL_JOINED_TO_GRADED_SOURCE_FIELD_AND_TOP_MEMBERSHIP_COPIES','at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_join_sha256':sha(q/'ORIGINAL_JOINED_ROWS_V1.json.gz'),'source_grades_sha256':sha(q/'ORIGINAL_AND_TOP_GRADED_ROWS_V1.json.gz'),'all_board_strategy_rows_preserve_joined_fields':n,'source_fields_compared':fields,'raw_source_board_top_flags_verified':flags,'raw_list_player_game_target_side_matches':top,'retained_selected_source_packet_count':len(census),'retained_week8_packet_count':sum(x==(2026,8)for x in census),'other_period_packet_count':sum(x!=(2026,8)for x in census),'new_grades_losses_or_inference':0,'metadata_only':True,'checker_sha256':sha(__file__)}
 with(HERE/'ORIGINAL_SOURCE_COPY_LINEAGE_REVIEW_V1.json').open('x')as f:json.dump(output,f,indent=2);f.write('\n')
 print(json.dumps(output))
if __name__=='__main__':main()
