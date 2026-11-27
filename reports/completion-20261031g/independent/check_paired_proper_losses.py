"""Independent pairing, loss arithmetic and game-cluster sensitivity calculations."""
import argparse,collections,functools,importlib.util,json,math
from pathlib import Path
sp=importlib.util.spec_from_file_location('q',Path(__file__).with_name('check_w7_methods.py'));q=importlib.util.module_from_spec(sp);sp.loader.exec_module(q)
read,zipped,sha,canon,close=q.read,q.zipped,q.sha,q.canon,q.close

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--private',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();pub=a.root/'reports/completion-20261031g/roster/paired-probability-v1';proto=read(pub/'FROZEN_PROTOCOL.json');receipt=read(pub/'RUN_RECEIPT.json');assert sha(pub/'FROZEN_PROTOCOL.json')==receipt['source_sha256'];data=collections.defaultdict(dict)
 for b in proto['source_members']:assert sha(a.private/b['logical_member'])==b['sha256']
 for w in(6,7):
  for family,base,gn,fn in [('GLM',f'completion-20261031g-w{w}-rolling-method-comparison-v1','GRADED_METHOD_ROWS.json.gz','FROZEN_SELECTIONS_AND_K.json.gz'),('LEAF',f'completion-20261031g-w{w}-complete-leaf-law-v1','GRADED_COMPLETE_LEAF_LAWS.json.gz','FROZEN_LAW_DIRECTIONS_K.json.gz')]:
   g=zipped(a.private/base/gn);f=zipped(a.private/base/fn);tagkeys={}
   for tag,pl in f['plans'].items():
    t,proc,h=pl['recipe'][:3]
    if family=='GLM'and(pl['rule']!='P2'or'regularized_glm_law'not in proc):continue
    fam='GLM'if family=='GLM'else'C02'if'c02'in proc else'BASE_LEAF';tagkeys[tag]=(t,h,'strict'in proc,fam)
   for row in g['probability_rows']if family=='GLM'else g['proper_losses']:
    tag=row['method_id']
    if tag not in tagkeys:continue
    idx=row['source_row_index'];r=next(x for x in g['graded'][tag]if x['source_row_index']==idx);key=tagkeys[tag];ll=row['categorical_log_loss']if family=='GLM'else row['log_loss'];brier=row['half3class_brier']if family=='GLM'else row['brier'];assert(w,idx)not in data[key];data[key][w,idx]=dict(brier=brier,log_loss=float('inf')if ll=='Infinity'else ll,game=r['game_id'],identity=(r['game_id'],r['player_id'],r['target'],str(r['line']),r['actual']))
 rows=read(pub/'PAIRED_PROBABILITY_COMPARISONS.json');wins=collections.Counter();examples=[]
 for r in rows:
  k=(r['target'],r['history_regime'],r['strict_current_information'],r['candidate_family']);ck=k[:3]+('GLM',);weeks=set(r['evaluation_weeks']);aa={q:v for q,v in data[k].items()if q[0]in weeks};bb={q:v for q,v in data[ck].items()if q[0]in weeks};assert aa.keys()==bb.keys();keys=sorted(aa);assert len(keys)==r['n']==r['candidate_own_n']==r['comparator_own_n'];assert all(aa[k]['identity']==bb[k]['identity']for k in keys);assert r['common_loss_mask_is_both_full_masks'];assert r['membership_sha256']==__import__('hashlib').sha256(canon([[k,aa[k]['identity']]for k in keys])).hexdigest();metric=r['metric'];x=[aa[k][metric]for k in keys];y=[bb[k][metric]for k in keys];assert all(math.isfinite(z)for z in x+y);n=len(x);delta=math.fsum(u-v for u,v in zip(x,y))/n;ca=math.fsum(x)/n;cb=math.fsum(y)/n;close(r['candidate_error'],ca);close(r['comparator_error'],cb);close(r['delta'],delta);close(r['relative_error_change'],delta/cb if cb else None);assert r['candidate_infinite_rows']==r['comparator_infinite_rows']==0
  games=collections.defaultdict(list);byweek=collections.defaultdict(list)
  for k,u,v in zip(keys,x,y):games[aa[k]['game']].append(u-v);byweek[k[0]].append(u-v)
  G=len(games);assert r['game_clusters']==G and r['week_clusters']==len(byweek);se=math.sqrt(G/(G-1)*math.fsum((math.fsum(z)-delta*len(z))**2 for z in games.values()))/n if G>=8 else None;close(r['game_cluster_sensitivity_se'],se);close(r['game_normal95_sensitivity'],[delta-1.96*se,delta+1.96*se]if se is not None else None);assert r['week_interval']is None and r['week_interval_status']=='INSUFFICIENT_WEEK_CLUSTERS'
  for w,z in byweek.items():assert r['weekly_paired_sums_counts'][str(w)]['n']==len(z);close(r['weekly_paired_sums_counts'][str(w)]['loss_difference_sum'],math.fsum(z))
  wins[(metric,'gain'if delta<0 else'loss'if delta>0 else'tie')]+=1
  if r['target']in('pass_att','pass_int')and r['candidate_family']=='BASE_LEAF'and r['history_regime']=='H-MULTI'and not r['strict_current_information']and r['evaluation_weeks']==[6,7]and metric=='brier':examples.append({k:r[k]for k in('target','candidate_error','comparator_error','delta','n','game_normal95_sensitivity','week_interval_status')})
 @functools.lru_cache(maxsize=4)
 def bound(path,h):
  pp=a.root/path;assert sha(pp)==h;return read(pp)
 byid={r['comparison_id']:r for r in rows};ann=read(pub/'PROPER_SCORE_COMPARISON_ANNOTATIONS.json')
 for z in ann:
  m=z['comparison'];r=byid[m['comparison_id']];s=bound(z['source_artifact'],z['source_artifact_sha256'])[z['source_row_index']];c=m['comparator_source'];t=bound(c['source_artifact'],c['source_artifact_sha256'])[c['source_row_index']];assert s['record_id']==z['record_id']and t['record_id']==c['record_id'];assert m['comparator_procedure_id']==t['procedure_id']and m['comparator_product_id']==t['product_id']and m['comparator_history_regime']==t['history_regime'];assert m['paired_n']==r['n'];close(m['candidate_error'],r['candidate_error']);close(m['comparator_error'],r['comparator_error']);close(m['absolute_error_change'],r['delta'])
 assert len(rows)==480 and len(ann)==160
 report=dict(state='PASS_INDEPENDENT_PAIRED_ACTUAL_LINE_PROPER_LOSSES_AND_SENSITIVITY',comparisons=len(rows),source_bound_annotations=len(ann),all_full_support_masks_identical=True,examples=examples,comparison_directions={f'{m}:{k}':n for(m,k),n in wins.items()},two_exposed_weeks_insufficient_for_week_uncertainty=True,new_fits=0,new_inference=0,new_grades=0,scope='All pairedidentities, fullmasks, cachedlosses, means/relativechanges, gameclusterSE/normal95sensitivity and annotation comparators; lawvectors/losses independently recomputed in priorreceipts.')
 with a.output.open('x')as f:json.dump(report,f,indent=2);f.write('\n')
 print(json.dumps(report))
if __name__=='__main__':main()
