#!/usr/bin/env python3
"""Bind already-scored seasonal views to a retained fixed empirical control.

No fitting or new forecasts. Identity sets come from the frozen private label
packet; source scores supply independently verified weekly loss sums.
"""
import argparse,collections,gzip,hashlib,json,math,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2 import seasonal_rolling as s

def key(r):return tuple(r.get(k)for k in('target','population','week','position','procedure_id','policy_id','product_id','fallback_view'))
def weekly_aggregate_bootstrap_supported(r):
 return len(r['evaluation_weeks'])>=8 and r['position']=='ALL'

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--public',type=Path,required=True);p.add_argument('--private',type=Path,required=True);p.add_argument('--repair',type=Path);p.add_argument('--replacement',action='store_true');a=p.parse_args();pub=a.public;parent_source=pub/'SCORES.json';parent_rows=json.loads(parent_source.read_text());source=a.repair/'SCORES.json' if a.replacement else parent_source;rows=json.loads(source.read_text()) if a.replacement else parent_rows;output_public=a.repair if a.replacement else pub;receipt=json.loads((pub/'RUN_RECEIPT.json').read_text());labels=a.private/receipt['labels']['bundle_name']
 if s.sha(labels)!=receipt['labels']['sha256']:raise ValueError('frozen labels differ')
 q=json.loads(gzip.decompress(labels.read_bytes()));lookup={key(r):r for r in parent_rows};lookup.update({key(r):r for r in rows});baseline={}
 for r in parent_rows:
  if r['procedure_id']=='empirical-player-history-control-v1'and r['fallback_view']=='ALL':baseline[r['target'],r['population'],r['week'],r['position'],r['history_regime'],r['product_id']]=r
 # Source-freezing repair is a prediction recipe overlay, not an overwrite.
 if a.repair and not a.replacement:
  mapping=json.loads((a.repair/'SUPERSESSION_MAPPING.json').read_text());rr=json.loads((a.repair/'SCORES.json').read_text());overlay={x['source_row_index']:rr[x['replacement_row_index']]for x in mapping['rows']}
 else:overlay={}
 groups=collections.defaultdict(list)
 for r in q:
  if r['actual']is None:continue
  ident=[r[k]for k in('game_id','player_id','target','population')]
  for pos in('ALL',r['position']):groups[r['target'],r['population'],r['week'],pos].append(ident)
 annotations=[];cache={};paired=0;ci_count=0
 for i,r in enumerate(rows):
  missing='A separate retained-row projection is required for this procedure-specific learned/fallback subset.'
  out=dict(status='UNESTABLISHED',reason=missing)
  if r['fallback_view']=='ALL'and r['n']>0:
   weeks=tuple(r['evaluation_weeks']);gkey=(r['target'],r['population'],weeks,r['position'])
   if gkey not in cache:
    ids=sorted(x for w in weeks for x in groups[r['target'],r['population'],w,r['position']]);cache[gkey]=(len(ids),hashlib.sha256(json.dumps(ids,separators=(',',':')).encode()).hexdigest())
   n,member=cache[gkey]
   if n!=r['n']:raise ValueError('source score membership differs from frozen query/actual set')
   product='event_probability'if r['target']=='anytime_td'else'mean';arm='H-RECENT'
   if r['procedure_id']=='empirical-player-history-control-v1'and r['history_regime']==arm and r['product_id']==product:arm='H-CURRENT'
   control=baseline.get((r['target'],r['population'],r['week'],r['position'],arm,product));metric='brier'if r['target']=='anytime_td'else'mae'
   if control and control['n']==n and tuple(control['evaluation_weeks'])==weeks and r.get(metric)is not None and control.get(metric)is not None:
    uncertainty=dict(week_clusters=len(weeks),week_interval=None,week_interval_status='INSUFFICIENT_WEEK_CLUSTERS',selection_limit='Exposeddescriptivecomparison;notselection/multiplicityadjusted',game_cluster_sensitivity_status='notcomputedforthisnewbaselineprojection;independenthistorycontrastsretaintheirseparateexactgameSE')
    if len(weeks)>=8 and not weekly_aggregate_bootstrap_supported(r):
     uncertainty.update(week_interval_status='NOT_COMPUTED_POSITION_WEEK_LOSSES_UNRETAINED',reason='Frozen source retains weeklyALLposition and ALLweekposition views, not their Cartesian product; aggregate paired loss and exact membership remain valid.')
    if weekly_aggregate_bootstrap_supported(r):
     sums=[];counts=[]
     for w in weeks:
      k=list(key(r));k[2]=w;one=lookup.get(tuple(k));base=baseline.get((r['target'],r['population'],w,r['position'],arm,product))
      if not(one and base and one['n']==base['n']):raise ValueError('weekly paired score missing')
      if one['n']:counts.append(one['n']);sums.append((one[metric]-base[metric])*one['n'])
     if sum(counts)!=n:raise ValueError('weekly loss census mismatch')
     delta=sum(sums)/n
     if not math.isclose(delta,r[metric]-control[metric],abs_tol=1e-10,rel_tol=1e-10):raise ValueError('weekly loss aggregation mismatch')
     ix=np.random.default_rng(1703).integers(0,len(counts),size=(500,len(counts)));values=np.asarray(sums)[ix].sum(axis=1)/np.asarray(counts)[ix].sum(axis=1)
     uncertainty.update(week_interval=[float(v)for v in np.quantile(values,[.025,.975],method='linear')],week_interval_status='NOMINAL_PAIRED_WHOLE_WEEK_BOOTSTRAP',replicates=500,seed=1703,rule='sumresampledweeklossdifferences/sumresampledrowcounts');ci_count+=1
    out=dict(status='PAIRED_RETAINED_ROWS',comparator_procedure_id=control['procedure_id'],comparator_history_regime=arm,comparator_product_id=product,metric=metric,candidate_error=r[metric],comparator_error=control[metric],paired_n=n,membership_sha256=member,uncertainty=uncertainty,cutoff_policy='Samefrozenquerykickoff/7dayreconstruction;registeredmodel/fallbackrefreshpoliciesretained',comparison_scope='fixedempiricalpointcontrol;notstrongestlearnedmodel;strongestcontrolsandhistorycontrastsseparate')
    paired+=1
  if i in overlay:out['source_version_limit']='OriginalfallbackrecipeviewretainedbutSUPERSEDED;use176registeredreplacementviewsforcurrentrecipe'
  annotations.append(dict(source_row_index=i,comparison=out))
 output=output_public/'BASELINE_COMPARISON_ANNOTATIONS.json'
 with output.open('x')as f:json.dump(dict(source_score_sha256=s.sha(source),baseline_source_score_sha256=s.sha(parent_source),identity='source_row_index',label_packet_sha256=s.sha(labels),rows=annotations),f,separators=(',',':'));f.write('\n')
 s.write(output_public/'BASELINE_ANNOTATION_RECEIPT.json',dict(state='SOURCE_BOUND_ZERO_FIT_BASELINE_PROJECTION',code_sha256=s.sha(__file__),source_scores_sha256=s.sha(source),annotations=len(rows),paired_views=paired,nominal_week_CIs=ci_count,new_fits=0,new_forecasts=0))
 print(json.dumps(dict(rows=len(rows),paired=paired,week_CIs=ci_count,new_fits=0)))
if __name__=='__main__':main()
