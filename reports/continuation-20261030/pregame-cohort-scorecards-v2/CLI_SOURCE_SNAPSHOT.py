#!/usr/bin/env python3
"""New saved-row cohort evaluation; no refits or new NFL outcomes."""
import argparse,gzip,hashlib,json,sys,datetime,csv
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from nfl_v2.pregame_views import source_history,memberships,evaluate,read_predictions


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('source-root','old-query-document','old-hgb-protocol','cohort-protocol','public-output','private-output'):
  p.add_argument('--'+name,required=True,type=Path)
 p.add_argument('--predictions',action='append',required=True,help='explicit adapter kind:path (empirical,hgb,normalized)')
 p.add_argument('--future-query-document',type=Path)
 p.add_argument('--future-cutoff-utc')
 a=p.parse_args();pub=a.public_output;private=a.private_output
 if pub.exists() or private.exists():raise SystemExit('fresh immutable output directories required')
 pub.mkdir(parents=True);private.mkdir(parents=True)
 protocol=json.loads(a.old_hgb_protocol.read_text())
 for source in protocol['source_ids']:
  if sha(a.source_root/source['name'])!=source['sha256']:raise SystemExit('source bytes changed')
 queries=json.loads(a.old_query_document.read_text())['historical']
 registration=dict(registered_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
  cohort_protocol_sha256=sha(a.cohort_protocol),code_sha256=sha(ROOT/'nfl_v2/pregame_views.py'),
  old_query_document_sha256=sha(a.old_query_document),new_nfl_fits=0,new_nfl_outcomes=0,inputs=[])
 for item in a.predictions:
  kind,name=item.split(':',1);path=Path(name)
  files=sorted(path.glob('W0[1-7]-*.json.gz')) if kind=='hgb' else [path]
  registration['inputs'].append(dict(adapter=kind,files=[dict(artifact_id=x.name,sha256=sha(x)) for x in files]))
 (pub/'EXECUTION_REGISTRATION.json').write_text(json.dumps(registration,indent=2)+'\n')
 history,games,counts=source_history(a.source_root,protocol)
 origins={w:min(g['kickoff'] for g in games.values() if g['season']==2026 and g['week']==w)-5400 for w in range(1,8)}
 member,summary=memberships(queries,history,origins)
 with gzip.open(private/'memberships.json.gz','wt') as f:json.dump([dict(key=k,**v) for k,v in member.items()],f,separators=(',',':'))
 if a.future_query_document:
  if not a.future_cutoff_utc:raise ValueError('frozen future feature cutoff required')
  cutoff=datetime.datetime.fromisoformat(a.future_cutoff_utc).timestamp()
  future=json.loads(a.future_query_document.read_text())['week8']
  future=[dict(q,week=8,population='frozen_exante_feed') for q in future]
  current=datetime.datetime.now(datetime.timezone.utc).timestamp()
  if any(current>=datetime.datetime.fromisoformat(q['kickoff_utc']).timestamp()-5400 for q in future):raise ValueError('future cohort deadline no longer open')
  fm,fs=memberships(future,history,{8:cutoff})
  with gzip.open(private/'future-memberships.json.gz','wt') as f:json.dump([dict(key=k,**v) for k,v in fm.items()],f,separators=(',',':'))
  (pub/'FUTURE_EXANTE_COHORT_COVERAGE.json').write_text(json.dumps(dict(state='FROZEN_UNSCORED_PREGAME_COHORT',coverage=fs,query_document_sha256=sha(a.future_query_document),membership_sha256=sha(private/'future-memberships.json.gz'),feature_cutoff_utc=a.future_cutoff_utc,actual_frozen_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),query_cells=len(future),unique_games=len({q['game_id'] for q in future}),elapsed_first_game_excluded=True,not_actual_T90_snapshot=True,actuals_read=0),indent=2)+'\n')
 records=[]
 for item in a.predictions:
  kind,name=item.split(':',1);records.extend(read_predictions(kind,Path(name)))
 scores=evaluate(records,member,registration['cohort_protocol_sha256'])
 (pub/'SCORES.json').write_text(json.dumps(scores,separators=(',',':'),allow_nan=False)+'\n')
 fields=list(dict.fromkeys(k for r in scores for k in r))
 with (pub/'SCORES.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows({k:json.dumps(v,sort_keys=True) if isinstance(v,(dict,list)) else v for k,v in row.items()} for row in scores)
 (pub/'MEMBERSHIP_COVERAGE.json').write_text(json.dumps(summary,indent=2)+'\n')
 receipt=dict(state='SCORED_NEW_COHORT_VIEWS',completed_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
  query_cells=len(queries),retained_prediction_views=len(records),score_views=len(scores),new_nfl_fits=0,new_nfl_forecasts=0,
  unique_games=len({r['game_id'] for r in records}),unique_player_games=len({(r['game_id'],r['player_id']) for r in records}),
  membership_sha256=sha(private/'memberships.json.gz'),score_sha256=sha(pub/'SCORES.json'),code_sha256=registration['code_sha256'],
  limitations='Pregame-feature-defined cohorts within retrospective stat-row universe; not authenticated exante starter/offer/role news; seven-day availability assumption; no frozen live selection policy')
 (pub/'RUN_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
if __name__=='__main__':main()
