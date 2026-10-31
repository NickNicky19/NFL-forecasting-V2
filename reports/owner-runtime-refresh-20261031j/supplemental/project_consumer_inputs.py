"""Only identity/offer/forecast-summary fields required by actual browser validators."""
import argparse,hashlib,json,pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[3]))
from nfl_v2 import prop_evidence_metadata_v2 as lexical

ALLOWED={'season','week','id','game_id','key','kickoff','model','reference_model','line','line_from','adj','over','n'}
def main(cache,out,pub):
 if out.exists():raise ValueError('fresh isolated inputs required')
 out.mkdir(parents=True)
 for name in ['pointer.json','payload.json','consumer.js','app.js','board.json']:(out/('fresh_'+name)).symlink_to((cache/name).resolve())
 raw=(cache/'board.json').read_bytes();old=lexical.ALLOWED;lexical.ALLOWED=ALLOWED
 try:x,skipped=lexical.project_metadata(raw.decode())
 finally:lexical.ALLOWED=old
 board={'season':x['season'],'week':x['week'],'execution_model':{'model':x.get('execution_model',{}).get('model')},'games':[{'id':g['id'],'kickoff':g['kickoff']}for g in x['games']],'players':[{'id':p['id'],'game_id':p.get('game_id'),'reference_model':p.get('reference_model'),'props':[{k:q.get(k)for k in ['key','line','line_from','adj','over','n']}for q in p.get('props',[])]}for p in x['players']]}
 body=json.dumps(board,separators=(',',':')).encode();(out/'IDENTITY_ONLY_BOARD.json').write_bytes(body)
 receipt={'schema':'j-consumer-input-projection-v1','source_board_sha256':hashlib.sha256(raw).hexdigest(),'projection_sha256':hashlib.sha256(body).hexdigest(),'allowlist':sorted(ALLOWED),'unknown_scalar_values_not_decoded':skipped,'NFL_statistic_scalars_decoded':0,'NFL_outcomes_used':0,'scope':'Includes offered lines, recorded forecast points and prior-history over/n summaries needed by actual selected validator. Excludes all actual/outcome/stats/results containers; no target-game outcome values decoded.','private_projected_bytes':len(body),'code_sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()}
 (pub/'BOARD_METADATA_PROJECTION_RECEIPT.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--cache',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);p.add_argument('--public',type=pathlib.Path,required=True);a=p.parse_args();main(a.cache,a.output,a.public)
