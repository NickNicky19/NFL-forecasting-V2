#!/usr/bin/env python3
"""New partial-week arithmetic control capture at a frozen shared as-of time.

No old packet is edited and no model is refitted. The existing empirical packet
schema/grader is reused with a new run, query membership and truthful clocks.
"""
import argparse,collections,gzip,hashlib,json,os,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from nfl_v2 import empirical_benchmark as emp
from nfl_v2.hgb_control import load_source,fit_floor
from nfl_v2.shadow_grading import CAPTURE_VERSION,QUERY_FIELDS,canonical,grade_bytes
from nfl_v2.week8_shadow import utc

def now():return datetime.now(timezone.utc)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,o):
 with p.open('xb') as f:f.write(canonical(o));f.flush();os.fsync(f.fileno())

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('source-root','query-document','old-protocol','old-hgb-protocol','public-output','private-output'):
  p.add_argument('--'+name,required=True,type=Path)
 p.add_argument('--asof-utc',required=True);a=p.parse_args();pub=a.public_output;private=a.private_output
 if pub.exists() or private.exists():raise ValueError('fresh outputs required')
 pub.mkdir(parents=True);private.mkdir(parents=True)
 origin=utc(a.asof_utc);queries=json.loads(a.query_document.read_text())['week8']
 queries=[{k:q[k] for k in QUERY_FIELDS} for q in queries]
 if any(now()>=utc(q['kickoff_utc'])-__import__('datetime').timedelta(minutes=90) for q in queries):raise ValueError('closed T90 game in new query set')
 proto=json.loads(a.old_protocol.read_text());hproto=json.loads(a.old_hgb_protocol.read_text())
 for s in proto['source_ids']:
  if sha(a.source_root/s['name'])!=s['sha256']:raise ValueError('source bytes changed')
 qbody=canonical(queries);(private/'frozen-queries.json').write_bytes(qbody)
 proto.update(run_id='v2-empirical-shared-asof-partial-week8-20261030-v1',registered_at_utc=now().isoformat(),
  code_sha256=sha(__file__),query_cells=len(queries),query_membership_sha256=hashlib.sha256(qbody).hexdigest(),
  history_cutoff=a.asof_utc,scope='NEW partialweek originalempiricalcontrols atsameasofasnewfamilies; elapsedfirstgameexcluded; not exactT90snapshot',
  old_capture_preserved=True,partial_week=True,elapsed_game_queries_excluded=156,source_information_gain='eligible2026_07_NE_CHI at7dayboundary, not puremodelchangeversusoldcaptures')
 save(pub/'FROZEN_PROTOCOL.json',proto);ph=sha(pub/'FROZEN_PROTOCOL.json')
 rows,_,_=load_source(a.source_root,hproto);groups={}
 for arm in emp.ARMS:
  g=collections.defaultdict(list)
  for r in rows:
   if r['season']<fit_floor(arm) or r['available']>=origin.timestamp():continue
   for t in proto['targets']:
    if r['position'] not in proto['history_positions_by_target'][t] or r['values'][t] is None:continue
    item=(r['available'],(r['game_id'],r['player_id']),r['values'][t])
    g[(t,r['position'],r['player_id'])].append(item);g[(t,r['position'],None)].append(item)
  groups[arm]={k:emp.Series(v) for k,v in g.items()}
 output=[];started=now()
 for q in queries:
  for arm in emp.ARMS:
   own=groups[arm].get((q['target'],q['position'],q['player_id']));s=own.at(origin.timestamp()) if own else (0,None,None,None);own_n=s[0];fallback='none'
   if not s[0]:
    prior=groups[arm].get((q['target'],q['position'],None));s=prior.at(origin.timestamp()) if prior else (0,None,None,None);fallback='position_empirical' if s[0] else 'constant_zero'
   products=[('event_probability',s[1])] if q['target']=='anytime_td' else [('empirical_mean',s[1]),('lower_median',s[2])]
   for product,value in products:
    issued=now();blocked=q['blocked_reason']
    if issued>=utc(q['kickoff_utc'])-__import__('datetime').timedelta(minutes=90):blocked=blocked or 'T90_DEADLINE_CLOSED'
    output.append(dict(q,run_id=proto['run_id'],history_regime=arm,product=product,prediction=None if blocked else value if s[0] else 0.,
     status='ABSTAIN' if blocked else 'ISSUED_SHADOW',abstention_reason=blocked,fallback=None if blocked else fallback,
     own_n=None if blocked else own_n,used_n=None if blocked else s[0],latest_training_available_utc=datetime.fromtimestamp(s[3],timezone.utc).isoformat() if s[3] is not None and not blocked else None,
     feature_cutoff_utc=origin.isoformat(),issued_at_utc=issued.isoformat(),actual_horizon_seconds=(utc(q['kickoff_utc'])-issued).total_seconds(),
     owner_cutoff_status='BEFORE_OWNER_INPUT_CUTOFF',protocol_sha256=ph))
 body=canonical(dict(schema=CAPTURE_VERSION,rows=output));blob=gzip.compress(body,mtime=0);file=private/'shadow-forecasts.json.gz'
 with file.open('xb') as f:f.write(blob);f.flush();os.fsync(f.fileno())
 persisted=now()
 if any(persisted>=utc(q['kickoff_utc'])-__import__('datetime').timedelta(minutes=90) for q in queries):raise ValueError('persistence after open deadline')
 if gzip.decompress(file.read_bytes())!=body:raise ValueError('readback mismatch')
 receipt=dict(version=CAPTURE_VERSION,run_id=proto['run_id'],protocol_sha256=ph,query_membership_sha256=proto['query_membership_sha256'],
  private_forecast_sha256=sha(file),private_uncompressed_sha256=hashlib.sha256(body).hexdigest(),private_forecast_bytes=len(blob),
  actual_feature_cutoff_utc=origin.isoformat(),actual_inference_started_at=started.isoformat(),actual_persistence_completed_at=persisted.isoformat(),
  forecast_output_rows=len(output),issued_shadow_rows=sum(r['status']=='ISSUED_SHADOW' for r in output),abstention_rows=sum(r['status']=='ABSTAIN' for r in output),
  query_cells=len(queries),unique_games=len({q['game_id'] for q in queries}),partial_week=True,first_game_excluded=True,
  before_deadlines=True,not_actual_T90_snapshot=True,new_optimization_fits=0,actual_week8_outcomes_read=0,official_capture=False,website_published=False)
 save(pub/'CAPTURE_RECEIPT.json',receipt);print(json.dumps(receipt))
if __name__=='__main__':main()
