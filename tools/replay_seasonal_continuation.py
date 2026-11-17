#!/usr/bin/env python3
"""Zero-fit complete score revision from hash-bound completed weekly packets."""
import argparse,collections,csv,gzip,io,json,os,resource,shutil,time,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2 import seasonal_rolling_v2 as s

def main():
 p=argparse.ArgumentParser()
 for n in ('base-public','base-private','continuation-public','continuation-private','public','private'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();pub,priv=a.public,a.private;protocolfile=pub/'FROZEN_PROTOCOL.json';plan=json.loads(protocolfile.read_text());start,cpu=time.monotonic(),time.process_time()
 if plan['code_sha256']!=s.sha(__file__):raise ValueError('replay code binding')
 sources=[(a.base_public,a.base_private),(a.continuation_public,a.continuation_private)];receipts=[];packets=[];boundweeks=set();modelrefs={};queries=json.loads((a.base_private/'frozen-queries.json').read_text())
 for i,(sp,sr) in enumerate(sources):
  receipt=json.loads((sp/'RUN_RECEIPT.json').read_text());receipts.append(receipt)
  if s.sha(sp/'RUN_RECEIPT.json')!=plan['sources'][i]['receipt_sha256'] or s.sha(sp/'SCORES.json')!=plan['sources'][i]['scores_sha256']:raise ValueError('source receipt/score hash')
  for week in receipt['completed_weeks']:
   if week in boundweeks:raise ValueError('duplicate week')
   boundweeks.add(week);wr=json.loads((sp/f'WEEK-{week:02}-RECEIPT.json').read_text());packet=sr/wr['packet']['bundle_name']
   if s.sha(packet)!=wr['packet']['sha256']:raise ValueError('week hash')
   packets.append((week,packet))
  for fit in sp.glob('*-FIT.json'):
   obj=json.loads(fit.read_text());m=obj.get('model')
   if m:
    old=modelrefs.get(m['bundle_name'])
    if old and old!=m['sha256']:raise ValueError('conflicting model')
    if s.sha(sr/m['bundle_name'])!=m['sha256']:raise ValueError('model hash')
    modelrefs[m['bundle_name']]=m['sha256']
   shutil.copyfile(fit,pub/fit.name)
  for sub in ('models','query-features'):
   for f in (sr/sub).glob('*'):
    dest=priv/sub/f.name;dest.parent.mkdir(exist_ok=True)
    if dest.exists():raise ValueError('duplicate archive member')
    os.link(f,dest)
 if boundweeks!=set(range(1,19)):raise ValueError('all18 completedweeks required')
 if s.sha(a.base_private/'QUALIFIED_QUERY_LABELS.json.gz')!=plan['labels_sha256']:raise ValueError('original qualified label binding')
 (priv/'predictions').mkdir();os.link(a.base_private/'frozen-queries.json',priv/'frozen-queries.json');os.link(a.base_private/'QUALIFIED_QUERY_LABELS.json.gz',priv/'QUALIFIED_QUERY_LABELS.json.gz')
 baseline=a.base_private/'predictions/EMPIRICAL_REPLAY.csv.gz'
 if s.sha(baseline)!=plan['baseline_sha256'] or s.sha(a.base_private/'frozen-queries.json')!=plan['frozen_queries_sha256']:raise ValueError('frozen baseline/query hash')
 packets.append((0,baseline));meters=collections.defaultdict(s.Meter);rows=empirical=0
 for week,f in packets:os.link(f,priv/'predictions'/f.name)
 with gzip.open(priv/'predictions.csv.gz','wt',newline='') as dst:
  writer=csv.DictWriter(dst,fieldnames=s.FIELDS);writer.writeheader()
  for week,file in sorted(packets):
   with gzip.open(file,'rt') as handle:
    for raw in csv.DictReader(handle):
     if int(raw['season'])!=2023 or week and int(raw['week'])!=week:raise ValueError('packet calendar')
     writer.writerow(raw);rows+=1;empirical+=not bool(week)
     r=dict(raw);r['actual']=s.emp.numeric(raw['actual']);r['actual_grid']=s.emp.numeric(raw['actual_grid']);r['prediction']=s.emp.numeric(raw['prediction']);r['week']=int(raw['week']);r['distribution_summary']=json.loads(raw['distribution_summary']) if raw['distribution_summary'] else None
     dims=tuple(r[k] for k in ('procedure_id','family','target','policy_id','history_regime','product_id','population'))
     for w,pos,view in [('ALL','ALL','ALL'),(str(r['week']),'ALL','ALL'),('ALL',r['position'],'ALL')]+([('ALL','ALL','LEARNED_ONLY')] if r['fallback']=='none' else []):meters[dims+(w,pos,view)].add(r)
     if rows%1000==0 and (time.monotonic()-start>600 or time.process_time()-cpu>900):raise RuntimeError('REPLAY_TIME_BUDGET')
 scores=[]
 for dims,m in sorted(meters.items()):
  proc,family,target,policy,arm,product,pop,week,pos,view=dims
  scores.append(dict(procedure_id=proc,procedure_family_id=family,target=target,history_regime=arm,policy_id=policy,product_id=product,population=pop,season=2023,evaluation_seasons=[2023],week=int(week) if week.isdigit() else week,position=pos,fallback_view=view,evaluation_panel_id=plan['run_id'],period='REG',record_kind='NEW_EXPERIMENT_CURRENT_VINTAGE_PARTICIPANT_DIAGNOSTIC',evidence='NEW_EXPERIMENT',source_vintage='current-vintage; seven-day availability assumption',feature_memory_policy='2022common or evaluationyearstrict; seepolicy_id',cohort_limit=plan['cohort'],**m.result()))
 s.write(pub/'SCORES.json',scores);s.emp.write_csv(pub/'SCORES.csv',scores)
 grid=[]
 for sp,sr in sources:grid += [r for r in json.loads((sp/'GRID_STATUS.json').read_text()) if not r['state'].startswith('NOT_RUN')]
 if len(grid)!=4608:raise ValueError('completegrid')
 s.write(pub/'GRID_STATUS.json',grid);s.write(pub/'FAILURES.json',[])
 r=dict(receipts[0]);r.update(version=plan['version'],run_id=plan['run_id'],state='COMPLETE_REPLAY_OF_RETAINED_WEEKLY_PACKETS',actual_completed_at=s.now(),protocol_sha256=s.sha(protocolfile),completed_weeks=sorted(boundweeks),actual_fit_calls=sum(r['actual_fit_calls'] for r in receipts),new_fit_calls=0,retained_models=len(modelrefs),failed_fits=sum(r['failed_fits'] for r in receipts),identical_policy_alias_cells=sum(r['identical_policy_alias_cells'] for r in receipts),completed_cells=len(grid),score_views=len(scores),forecast_output_views=rows,retained_empirical_output_views=empirical,private_flat=dict(bundle_name='predictions.csv.gz',sha256=s.sha(priv/'predictions.csv.gz'),bytes=(priv/'predictions.csv.gz').stat().st_size),private_output_bytes=sum(f.stat().st_size for f in priv.rglob('*') if f.is_file()),resource=dict(wall_seconds=sum(r['resource']['wall_seconds'] for r in receipts),cpu_seconds=sum(r['resource']['cpu_seconds'] for r in receipts),peak_rss_bytes=max(r['resource']['peak_rss_bytes'] for r in receipts),max_threads=2),zero_fit_replay_resource=dict(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu),source_run_receipts=plan['sources'],model_logical_aliases='Hardlinked immutable original fitted bytes; zero new models/refits in replay',CURRENT_2026_Week8_outcomes_read=0)
 s.write(pub/'RUN_RECEIPT.json',r);print(json.dumps(r))
if __name__=='__main__':main()
