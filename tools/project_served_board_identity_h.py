"""Project a served board's identities without decoding NFL statistic scalars."""
from __future__ import annotations
import argparse,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2 import prop_evidence_metadata_v2 as lexical

ALLOWED={'season','week','id','game_id','key','kickoff'}

def project(raw):
    prior=lexical.ALLOWED;lexical.ALLOWED=ALLOWED
    try:x,skipped=lexical.project_metadata(raw)
    finally:lexical.ALLOWED=prior
    board=dict(season=x['season'],week=x['week'],games=[dict(id=g['id'],kickoff=g['kickoff'])for g in x['games']],players=[dict(id=p['id'],game_id=p.get('game_id'),props=[dict(key=q['key'])for q in p.get('props',[])])for p in x['players']])
    return board,skipped

def main(a):
    raw=a.source.read_bytes();board,skipped=project(raw.decode());body=json.dumps(board,separators=(',',':')).encode()
    with a.output.open('xb')as f:f.write(body)
    receipt=dict(source_board_sha256=hashlib.sha256(raw).hexdigest(),projection_sha256=hashlib.sha256(body).hexdigest(),code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),allowlist=sorted(ALLOWED),unknown_scalar_values_not_decoded=skipped,NFL_statistic_scalars_decoded=0,NFL_outcomes_used=0)
    print(json.dumps(receipt))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);main(p.parse_args())
