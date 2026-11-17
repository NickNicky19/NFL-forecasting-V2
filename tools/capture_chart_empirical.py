#!/usr/bin/env python3
"""One immutable arithmetic chart shadow from frozen qualified earlier labels."""
from __future__ import annotations
import argparse,collections,gzip,hashlib,json,math,os,resource,sys,time
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from nfl_v2 import empirical_benchmark as empirical,hgb_control as source
VERSION='v2-qualified-partial-chart-empirical-shadow-v1';TARGET='nick-chart-ppr-v1'
def now():return datetime.now(timezone.utc).isoformat()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def immutable(p,x):
 with p.open('xb') as f:f.write(canonical(x));f.flush();os.fsync(f.fileno())
p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['prepare','capture'])
for k in ['public-root','private-root','chart-private','source-root']:p.add_argument('--'+k,type=Path,required=True)
a=p.parse_args();a.public_root.mkdir(parents=True,exist_ok=True);a.private_root.mkdir(parents=True,exist_ok=True)
if a.command=='prepare':
 q=json.loads((a.chart_private/'frozen-queries.json').read_text())['week8'];expected=len(q)*6
 protocol=dict(version=VERSION,state='FROZEN_BEFORE_NEW_SHADOW_INFERENCE',registered_at_utc=now(),code_sha256=sha(Path(__file__)),qualified_label_sha256=sha(a.chart_private/'qualified-chart-labels.json.gz'),frozen_query_packet_sha256=sha(a.chart_private/'frozen-queries.json'),schedule_sha256=sha(a.source_root/'games.csv'),fixed_feature_origin_utc='2026-10-30T00:27:36.688096+00:00',target=TARGET,query_cells=len(q),expected_output_views=expected,formula='Earlierqualifiedchartscore*50 divided50;arm current2026/recent2025+/multi2022+;ownsamepositionalleligiblemean/lowerempiricalmedian;otherwisepositionmean/median;noNFLlabelsconstant0',strict_current='exactaliasH-CURRENT; noolderfootballlabels/features/priors or trainedcomponent; noextraindependentmodel',availability='sourcekickoff+7days strictlybeforefixedasof; onlyREG2022–25or2026W1–7 source-qualified chartlabels; current-vintage reconstructedavailability',future='same434frozenplayergamequeryunion;actualnewissue/persistbeforeT90;blockedboardcontextsABSTAIN; no newsourceacquisition orWeek8labels',output_contract='numericmean/medianpoints only; no authenticatednumericCDF/probability/EV',budget=dict(wall_seconds=60,cpu_seconds=60,max_peak_memory_bytes=268435456,max_output_views=3000,max_output_bytes=4194304,new_optimizer_fits=0),official_capture=False,website_published=False)
 immutable(a.public_root/'EMPIRICAL_FUTURE_PROTOCOL.json',protocol);print(json.dumps(protocol,indent=2));raise SystemExit
start,cpu=time.monotonic(),time.process_time();protocol=json.loads((a.public_root/'EMPIRICAL_FUTURE_PROTOCOL.json').read_text())
for file,key in [(Path(__file__),'code_sha256'),(a.chart_private/'qualified-chart-labels.json.gz','qualified_label_sha256'),(a.chart_private/'frozen-queries.json','frozen_query_packet_sha256'),(a.source_root/'games.csv','schedule_sha256')]:
 if sha(file)!=protocol[key]:raise ValueError('changedfrozeninput:'+key)
if protocol['expected_output_views']>protocol['budget']['max_output_views']:raise RuntimeError('OUTPUT_PREFLIGHT')
cutoff=source.utc(protocol['fixed_feature_origin_utc']).timestamp();immutable(a.public_root/'EMPIRICAL_FUTURE_EXECUTION.json',dict(version=VERSION,actual_started_at=now(),protocol_sha256=sha(a.public_root/'EMPIRICAL_FUTURE_PROTOCOL.json'),new_fits=0))
games=source.schedules(a.source_root/'games.csv');labels=json.loads(gzip.decompress((a.chart_private/'qualified-chart-labels.json.gz').read_bytes()))['rows'];query=json.loads((a.chart_private/'frozen-queries.json').read_text())['week8'];lookup={}
for arm,floor in [('H-CURRENT',2026),('H-RECENT',2025),('H-MULTI',2022)]:
 groups=collections.defaultdict(list)
 for r in labels:
  value=r['label']['points_times_50'];game=games[r['game_id']]
  if r['season']<floor or value is None or game['kickoff']+7*86400>=cutoff:continue
  item=(game['kickoff']+7*86400,(r['game_id'],r['player_id']),value);groups[(r['position'],r['player_id'])].append(item);groups[(r['position'],None)].append(item)
 lookup[arm]={k:empirical.Series(v) for k,v in groups.items()}
rows=[];generated=now()
for q in query:
 reason=q['blocked_reason'] or ('UNQUALIFIED_POSITION' if q.get('position') not in source.POSITIONS else None)
 if datetime.now(timezone.utc)>=source.utc(q['owner_input_cutoff_utc']):reason=reason or 'T90_CLOSED_BEFORE_ISSUANCE'
 for arm in ('H-CURRENT','H-RECENT','H-MULTI'):
  summary=(0,None,None,None);fallback=None
  if not reason:
   series=lookup[arm].get((q['position'],q['player_id']));summary=series.at(cutoff) if series else summary;fallback='none'
   if not summary[0]:
    series=lookup[arm].get((q['position'],None));summary=series.at(cutoff) if series else summary;fallback='position_empirical' if summary[0] else 'constant_zero'
  for product,i in [('mean',1),('lower_median',2)]:
   rows.append(dict(q,season=2026,week=8,population='original_pregame_feed_union',target=TARGET,run_id=VERSION,procedure_id='v2-qualified-partial-chart-direct-wave-v1:empirical',family='empirical_chart_history_control',history_regime=arm,information_policy='ARM_LIMITED_TARGET_HISTORY',strict_current_alias='H-CURRENT' if arm=='H-CURRENT' else None,product_id=product,prediction=None if reason else summary[i]/50 if summary[0] else 0.,actual=None,actual_status='PENDING_FUTURE',fallback=fallback,fallback_source_n=summary[0],latest_training_label_available=summary[3],cutoff=cutoff,actual_generated_at=generated,issued_at_utc=generated,status='ABSTAIN' if reason else 'FORECASTED',abstention_reason=reason,actual_horizon_seconds=source.utc(q['kickoff_utc']).timestamp()-source.utc(generated).timestamp(),owner_cutoff_status='BEFORE_OWNER_INPUT_CUTOFF' if not reason else 'NOT_ISSUED'))
if len(rows)!=protocol['expected_output_views']:raise ValueError('queryviewcount')
body=gzip.compress(canonical(dict(schema=VERSION,rows=rows)),mtime=0)
if len(body)>protocol['budget']['max_output_bytes']:raise RuntimeError('BYTE_BUDGET')
path=a.private_root/'WEEK8_CHART_EMPIRICAL_SHADOWS.json.gz'
with path.open('xb') as f:f.write(body);f.flush();os.fsync(f.fileno())
persisted=now();allbefore=all(source.utc(persisted)<source.utc(r['owner_input_cutoff_utc']) for r in rows if r['prediction'] is not None)
if not allbefore:raise RuntimeError('PERSISTENCE_AFTER_T90_INVALID')
assert time.monotonic()-start<=60 and time.process_time()-cpu<=60 and resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<=protocol['budget']['max_peak_memory_bytes']
receipt=dict(version=VERSION,state='CAPTURED_OPEN_T90_LOCAL_READBACK_OFFHOST_PENDING',protocol_sha256=sha(a.public_root/'EMPIRICAL_FUTURE_PROTOCOL.json'),actual_generated_at=generated,actual_persistence_completed_at=persisted,packet=dict(artifact_id='ART-CHART-'+sha(path),bundle_name=path.name,bytes=len(body),sha256=sha(path)),query_cells=len(query),games=len({r['game_id'] for r in rows}),output_views=len(rows),issued=sum(r['prediction'] is not None for r in rows),abstained=sum(r['prediction'] is None for r in rows),all_before_T90_persistence=allbefore,actuals_read=0,new_fits=0,resource=dict(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024),official_capture=False,website_published=False)
immutable(a.public_root/'EMPIRICAL_FUTURE_CAPTURE_RECEIPT.json',receipt);print(json.dumps(receipt,indent=2))
