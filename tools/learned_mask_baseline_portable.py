#!/usr/bin/env python3
"""One-pass retained-row fixed-control comparisons on each learned-only mask."""
import argparse,collections,csv,gzip,hashlib,json,math,resource,sys,time
from array import array
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from threadpoolctl import threadpool_limits
from nfl_v2 import seasonal_rolling_v2 as s
from nfl_v2.paired_uncertainty import paired_losses
BASE=Path('reports/continuation-20261030c');PRIVATE=None # Required explicit --private-root; no private storage location is embedded.
SPECS=[('season-2025-v1','seasonal-rolling-2025-v1'),('season-2024-v2','seasonal-rolling-2024-v2'),('season-2023-complete-replay-v1','seasonal-rolling-2023-complete-replay-v1'),('season-2022-v2','seasonal-rolling-2022-v2'),('season-2025-continuity-repair-v1','seasonal-rolling-2025-continuity-repair-v1')]
OUT=BASE/'learned-mask-baseline-v2'
def key(r):return tuple(r[k] for k in ('procedure_id','target','population','policy_id','product_id'))
def number(x):return None if x in ('',None) else float(x)
def loss(y,p,target):return (p-y)**2 if target=='anytime_td' else abs(p-y)
def membership_hash(indices,baseline):return hashlib.sha256(s.canonical(sorted(baseline[i][0] for i in indices))).hexdigest()
def prepare():
 OUT.mkdir();specs=[]
 for pubname,privname in SPECS:
  pub=BASE/pubname;priv=PRIVATE/privname;r=json.loads((pub/'RUN_RECEIPT.json').read_text());flat=priv/r['private_flat']['bundle_name']
  if s.sha(flat)!=r['private_flat']['sha256']:raise ValueError('flat binding')
  specs.append(dict(public=pubname,private_bundle_id=privname,source_scores_sha256=s.sha(pub/'SCORES.json'),source_flat_sha256=s.sha(flat),source_previous_annotations_sha256=s.sha(pub/'BASELINE_COMPARISON_ANNOTATIONS.json')))
 p=dict(version='v2-learned-mask-fixed-empirical-baseline-v2',registered_at=s.now(),state='FROZEN_BEFORE_RETAINED_NUMERIC_PREDICTION_DECODE',code_sha256=s.sha(__file__),helper_sha256=s.sha('nfl_v2/paired_uncertainty.py'),sources=specs,budget=dict(wall_seconds=155,cpu_seconds=215,max_rss_bytes=1073741824,max_threads=2,max_rows_read=7000000),cohort='Exact own-procedure fallback=none and known actual, existing LEARNED_ONLY ALLweek/ALLposition view; prior fullsystem annotations preserved',comparator='H-RECENT empirical mean, or event probability forTD, on each exact candidate-owned learned mask;2022same source-limitedproxy remains explicit',metrics='Candidate loss verified against existingMAE/Brier andn; baseline nativeMAE/MSE/bias/exact/strict-inclusive1,5,10; meanunroundedchart; paired18weekbootstrap+gameSE frozenhelper; no generic accuracy',identity='Sorted exact hash-bound query_id list SHA256, matching actual/game/target/pop; no rawmembership published',repair='Corrected24148rawrows; parent2025baseline retained unchanged,176replacementSCORES/sourceannotations separate',selection='None; exposed descriptive fixedcomparison, not futurepolicy',position_week_CI='Secondary; previous explicituncomputed reason remains ifnotcompleted',new_fits=0,new_forecasts=0,CURRENT_2026_Week8_outcomes_read=0,v1_failed_receipt_sha256=s.sha(BASE/'learned-mask-baseline-v1/RUN_RECEIPT.json'),amendment='Include empirical candidate-owned learned masks by deferring compact numeric candidates until fixed comparator pool has been retained; no comparator/model/forecast changes; remaining original180wall budget155s after24.58sv1.')
 s.write(OUT/'FROZEN_PROTOCOL.json',p);return p

def run():
 p=json.loads((OUT/'FROZEN_PROTOCOL.json').read_text());start,cpu=time.monotonic(),time.process_time();total=0;results=[];state='COMPLETE';failure=None;cached_baseline=None
 if p['code_sha256']!=s.sha(__file__) or p['helper_sha256']!=s.sha('nfl_v2/paired_uncertainty.py'):raise ValueError('code binding')
 def guard():
  if time.monotonic()-start>155 or time.process_time()-cpu>215:raise RuntimeError('TIME_BUDGET')
  if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>1073741824:raise RuntimeError('RSS_BUDGET')
 with threadpool_limits(limits=2):
  try:
   for (pubname,privname),spec in zip(SPECS,p['sources']):
    guard();pub=BASE/pubname;priv=PRIVATE/privname;receipt=json.loads((pub/'RUN_RECEIPT.json').read_text());flat=priv/receipt['private_flat']['bundle_name'];scores=json.loads((pub/'SCORES.json').read_text());old=json.loads((pub/'BASELINE_COMPARISON_ANNOTATIONS.json').read_text())
    if s.sha(pub/'SCORES.json')!=spec['source_scores_sha256'] or s.sha(flat)!=spec['source_flat_sha256'] or s.sha(pub/'BASELINE_COMPARISON_ANNOTATIONS.json')!=spec['source_previous_annotations_sha256']:raise ValueError('source binding')
    learned={key(r):(i,r) for i,r in enumerate(scores) if r['fallback_view']=='LEARNED_ONLY'};groups={k:dict(a=array('d'),b=array('d'),weeks=array('B'),games=array('H'),members=array('I'),be=array('d'),precision=collections.Counter()) for k in learned};baseline=[];byquery={};gamecodes={};read=0
    isrepair='repair'in pubname
    if isrepair:baseline,byquery=cached_baseline
    pending=[]
    def consume(packet):
      k,qid,actual,pred,game,target,pop,week=packet
      if k not in groups:return
      idx=byquery.get(qid)
      if idx is None:raise ValueError('baseline missing before learned row')
      b=baseline[idx]
      if actual!=b[2] or (game,target,pop)!=b[3:]:raise ValueError('baseline identity/outcome mismatch')
      g=groups[k];g['a'].append(loss(actual,pred,target));g['b'].append(loss(actual,b[1],target));g['be'].append(b[1]-actual);g['weeks'].append(week);g['games'].append(gamecodes.setdefault(game,len(gamecodes)));g['members'].append(idx)
      ae=abs(b[1]-actual)
      for tolerance in (1,5,10):g['precision']['abs_lt_'+str(tolerance)]+=ae<tolerance;g['precision']['abs_le_'+str(tolerance)]+=ae<=tolerance
      g['precision']['exact_rate']+=ae==0
    def learned_packet(raw):
      return (key(raw),raw['query_id'],float(raw['actual']),float(raw['prediction']),raw['game_id'],raw['target'],raw['population'],int(raw['week']))
    with gzip.open(flat,'rt') as f:
     for raw in csv.DictReader(f):
      total+=1;read+=1
      if total%10000==0:
       guard()
       if total>p['budget']['max_rows_read']:raise RuntimeError('ROW_BUDGET')
      if int(raw['season']) not in (2022,2023,2024,2025):raise ValueError('older only')
      if not isrepair and raw['procedure_id']=='empirical-player-history-control-v1':
       wanted='event_probability' if raw['target']=='anytime_td' else 'mean'
       if raw['history_regime']=='H-RECENT' and raw['product_id']==wanted:
        qid=raw['query_id']
        if qid in byquery:raise ValueError('duplicate baseline query')
        byquery[qid]=len(baseline);baseline.append((qid,number(raw['prediction']),number(raw['actual']),raw['game_id'],raw['target'],raw['population']))
       if raw['fallback']=='none' and raw['actual']:pending.append(learned_packet(raw))
       continue
      if pending:
       for packet in pending:consume(packet)
       pending.clear()
      if raw['fallback']=='none' and raw['actual']:consume(learned_packet(raw))
    for packet in pending:consume(packet)
    if pubname=='season-2025-v1':cached_baseline=(baseline,byquery)
    annotations=old['rows'];count=0
    for k,(index,r) in learned.items():
     guard();g=groups[k];n=len(g['a']);metric='brier' if r['target']=='anytime_td' else 'mae';expected=r[metric]
     if n!=r['n'] or not math.isclose(math.fsum(g['a'])/n,expected,rel_tol=1e-10,abs_tol=1e-10):raise ValueError('candidate learned score mismatch '+str(index))
     if len(g['members'])!=len(set(g['members'])):raise ValueError('duplicate candidate-owned query')
     uncertainty=paired_losses(g['a'],g['b'],g['weeks'],g['games']);precision={name:dict(numerator=value,denominator=n,rate=value/n) for name,value in g['precision'].items()};source_limit=annotations[index]['comparison'].get('source_version_limit');comp=dict(status='PAIRED_RETAINED_ROWS',comparator_procedure_id='empirical-player-history-control-v1',comparator_history_regime='H-RECENT',comparator_product_id='event_probability' if r['target']=='anytime_td' else 'mean',metric=metric,candidate_error=expected,comparator_error=math.fsum(g['b'])/n,paired_n=n,membership_sha256=membership_hash(g['members'],baseline),membership_rule='Sorted exact frozen query_id list; candidate fallback=none own mask; source actuals verified equal',view='OWN_LEARNED_ONLY',comparator_subset_mae=math.fsum(map(abs,g['be']))/n,comparator_subset_mse=math.fsum(v*v for v in g['be'])/n,comparator_subset_bias=math.fsum(g['be'])/n,comparator_subset_precision=precision,uncertainty=uncertainty,cutoff_policy='Unchanged retained weekly fit/pergame features and seven-day assumption',comparison_scope='Fixed empirical control restricted to exact candidate-owned learned rows; not common-all-competitor mask or model selection',history_limit='2022H-RECENT is available2022proxy; requested2021component absent' if r['season']==2022 else None)
     if source_limit:comp['source_version_limit']=source_limit
     annotations[index]=dict(source_row_index=index,comparison=comp);count+=1
    target=pub/'BASELINE_COMPARISON_ANNOTATIONS_V2.json';s.write(target,dict(source_score_sha256=spec['source_scores_sha256'],parent_annotations_sha256=spec['source_previous_annotations_sha256'],protocol_sha256=s.sha(OUT/'FROZEN_PROTOCOL.json'),identity='source_row_index',rows=annotations));one=dict(folder=pubname,rows_read=read,annotation_rows=len(annotations),learned_views_completed=count,annotation_sha256=s.sha(target),resource_so_far=dict(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024));results.append(one);s.write(OUT/(pubname+'-RECEIPT.json'),one)
  except Exception as exc:state='PARTIAL_STOPPED';failure=dict(type=type(exc).__name__,reason=str(exc))
 r=dict(state=state,actual_completed_at=s.now(),code_sha256=s.sha(__file__),protocol_sha256=s.sha(OUT/'FROZEN_PROTOCOL.json'),completed_sources=results,remaining_sources=[name for name,_ in SPECS if name not in {r['folder']for r in results}],rows_read=total,learned_views_completed=sum(r['learned_views_completed'] for r in results),resource=dict(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,max_threads=2),failure=failure,new_fit_calls=0,new_forecasts=0,new_NFL_score_views=0,CURRENT_2026_Week8_outcomes_read=0)
 s.write(OUT/'RUN_RECEIPT.json',r);return r
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('action',choices=('prepare','run'));a.add_argument('--private-root',type=Path,required=True);args=a.parse_args();PRIVATE=args.private_root;print(json.dumps(prepare() if args.action=='prepare' else run()))
