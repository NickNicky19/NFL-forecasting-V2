"""Independently aggregate verified cached H losses and canonical weekly P1 counts."""
import argparse,collections,gzip,hashlib,importlib.util,json,math
from pathlib import Path
sp=importlib.util.spec_from_file_location('q',Path(__file__).with_name('check_probability_references.py'));q=importlib.util.module_from_spec(sp);sp.loader.exec_module(q)
read,gz,sha,canon,close=q.read,q.gz,q.sha,q.canon,q.close

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--private',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();pub=a.root/'reports/baselines-coverage-20261031h/probability/w5-w7-cumulative-v1';p=read(pub/'FROZEN_PROTOCOL.json');run=read(pub/'RUN_RECEIPT.json');assert sha(pub/'FROZEN_PROTOCOL.json')==run['protocol_sha256'];assert sha(pub/'SCORES.json')==run['score_sha256'];assert sha(pub/'SOURCE_SNAPSHOT.py')==p['code_sha256'];data=collections.defaultdict(dict);pointfiles=[]
 for b in p['source_bindings']:
  file=a.root/b['path']if b.get('path')else(a.root/b['source_id']/b['member']if b['source_id'].startswith('reports/')else a.private/b['source_id']/b['member']);assert sha(file)==b['sha256']
  if b['kind']=='private_cached_loss':
   for r in gz(file):
    k=(r['target'],r['procedure_id'],r['history_regime']);idx=(r['week'],r['source_row_index']);assert idx not in data[k];data[k][idx]=r
  if b['kind']=='public_primary_point_counts':pointfiles.append(file)
 scores=read(pub/'SCORES.json');proper={};p1=[];examples=[]
 for s in scores:
  if s['record_kind']=='prop_selection_evaluation':p1.append(s);continue
  k=(s['target'],s['matched_candidate_procedure_id'],s['history_regime']);full=[r for _,r in sorted(data[k].items())];rr=[r for r in full if s['fallback_view']=='FULL'or r['origin']==s['fallback_view']];ref=s['reference_id'];n=len(rr);assert s['n']==n and s['forecast_rows']==len(full);assert s['membership_sha256']==hashlib.sha256(canon([[r['week'],r['source_row_index'],r['game'],r['player'],r['target'],r['line'],r['actual']]for r in rr])).hexdigest();assert s['unique_weeks']==len({r['week']for r in rr})and s['unique_games']==len({r['game']for r in rr});ll=[r[ref+'_log_loss']for r in rr];inf=ll.count('Infinity');close(s['brier'],math.fsum(r[ref+'_brier']for r in rr)/n if n else None);close(s['log_loss'],'Infinity'if inf else math.fsum(ll)/n if n else None);assert s['infinite_log_losses']==inf and s['source_prior_rows']==sum(r['origin']=='PRIOR'for r in rr);proper[s['record_id']]=(s,rr)
  if s['target']=='pass_att'and ref=='candidate'and s['fallback_view']=='FULL'and'ordered_leaf_cdf'in s['procedure_id']and(s['history_regime']=='H-MULTI'or s['strict_current_information']):examples.append({k:s[k]for k in('procedure_id','history_regime','strict_current_information','n','brier','unique_games','unique_weeks')})
 diagnostics=read(pub/'CALIBRATION_AND_DISCRIMINATION.json')
 for d in diagnostics:
  s,rr=proper[d['record_id']];ref=s['reference_id'];ac,an=q.auc(rr,ref);close(d['decisive_over_auc'],ac);assert d['decisive_auc_n']==an;bins=collections.defaultdict(list)
  for r in rr:
   for region in q.REGIONS:pr=r[ref+'_probabilities'][region];bins[region,min(9,math.floor(pr*10))].append((pr,int(r['actual_region']==region)))
  assert len(d['calibration_bins'])==len(bins)
  for b in d['calibration_bins']:
   v=bins[b['region'],b['bin']];assert b['n']==len(v);close(b['mean_probability'],math.fsum(x[0]for x in v)/len(v));close(b['actual_frequency'],math.fsum(x[1]for x in v)/len(v));close(b['signed_calibration_error'],b['mean_probability']-b['actual_frequency'])
 pairs=read(pub/'PAIRED_COMPARISONS.json');method_pairs=0;empty=0
 for s in pairs:
  aa=data[s['target'],s['procedure_id'],s['history_regime']]
  if s['comparator']in('B0','B1'):
   rr=[r for _,r in sorted(aa.items())if s['fallback_view']=='FULL'or r['origin']==s['fallback_view']];x=[r['candidate_'+s['metric']]for r in rr];y=[r[s['comparator']+'_'+s['metric']]for r in rr]
  else:
   bb=data[s['target'],s['comparator'],s['history_regime']];keys=sorted(set(aa)&set(bb));assert s['candidate_own_n']==len(aa)and s['comparator_own_n']==len(bb)and s['both_own_masks_equal']==(set(aa)==set(bb));assert all(tuple(aa[k][f]for f in('game','player','target','line','actual'))==tuple(bb[k][f]for f in('game','player','target','line','actual'))for k in keys);keys=[k for k in keys if s['fallback_view']=='FULL'or(s['fallback_view']=='COMMON_LEARNED'and aa[k]['origin']==bb[k]['origin']=='LEARNED')or(s['fallback_view']=='PRIOR_ANY'and(aa[k]['origin']=='PRIOR'or bb[k]['origin']=='PRIOR'))];rr=[aa[k]for k in keys];x=[aa[k]['candidate_'+s['metric']]for k in keys];y=[bb[k]['candidate_'+s['metric']]for k in keys];method_pairs+=1
  n=len(rr);assert s['n']==n
  if not n:assert s['status']=='NO_SUPPORTED_PAIRED_ROWS'and s['delta']is None;empty+=1;continue
  ai=x.count('Infinity');bi=y.count('Infinity');assert s['candidate_infinite_rows']==ai and s['comparator_infinite_rows']==bi;close(s['candidate_error'],'Infinity'if ai else math.fsum(x)/n);close(s['comparator_error'],'Infinity'if bi else math.fsum(y)/n)
  if ai or bi:assert s['status']=='NONFINITE_LOSS_DIFFERENCE_UNDEFINED'and s['delta']is None;continue
  diff=[a-b for a,b in zip(x,y)];delta=math.fsum(diff)/n;close(s['delta'],delta);close(s['relative_error_change'],delta/(math.fsum(y)/n)if math.fsum(y)else None);gg=collections.defaultdict(list)
  for r,d in zip(rr,diff):gg[r['game']].append(d)
  G=len(gg);se=math.sqrt(G/(G-1)*math.fsum((math.fsum(v)-delta*len(v))**2 for v in gg.values()))/n if G>=8 else None;close(s['game_cluster_sensitivity_se'],se);assert s['week_interval']is None and s['week_interval_status']=='INSUFFICIENT_WEEK_CLUSTERS'
 grouped=collections.defaultdict(list);outer={}
 for file in pointfiles:
  for r in read(file):
   if r['record_kind']=='prop_selection_evaluation'and r.get('decision_rule')=='P1'and r.get('K')is None and r['cohort_id']=='ALL':grouped[r['target'],r['procedure_id'],r['history_regime'],r['product_id'],r['side']].append(r);outer[r['target'],r['evaluation_weeks'][0]]=r['selection_metrics']['selection_pool_count']
 trip=collections.defaultdict(dict)
 for s in p1:
  k=(s['target'],s['procedure_id'],s['history_regime'],s['product_id'],s['side']);rr=grouped[k];assert len(set(r['evaluation_weeks'][0]for r in rr))==len(rr);m=s['selection_metrics'];ct=collections.Counter()
  for r in rr:ct.update(r['selection_metrics']['status_counts'])
  n=ct['WIN']+ct['LOSS'];selected=sum(r['forecast_rows']for r in rr);universe=sum(outer[s['target'],w]for w in(5,6,7));assert(s['forecast_rows'],s['n'],m['selection_pool_count'])==(selected,n,universe);assert m['status_counts']==dict(ct);close(m['hit_rate'],ct['WIN']/n if n else None);close(m['selection_coverage'],selected/universe if universe else None);assert m['admitted_forecast_opportunities']==sum(r['selection_metrics']['admitted_forecast_opportunities']for r in rr);assert m['unavailable_forecast_opportunities']==universe-m['admitted_forecast_opportunities'];assert m['admitted_rule_abstentions']==sum(r['selection_metrics']['admitted_rule_abstentions']for r in rr);assert s['unique_players']is None and m['game_uncertainty']['game_interval']is None;trip[k[:4]][s['side']]=[selected,n]+[ct[st]for st in('WIN','LOSS','PUSH','VOID','UNKNOWN_PARTICIPATION','MISSING_ACTUAL','PENDING')]
 for t in trip.values():assert set(t)=={'over','under','Combined'}and t['Combined']==[x+y for x,y in zip(t['over'],t['under'])]
 assert len(scores)==2976 and len(proper)==1242 and len(p1)==1734 and len(pairs)==2136 and method_pairs==480
 report=dict(state='PASS_INDEPENDENT_THREE_WEEK_CACHED_LOSS_PRIMARY_P1_AND_PROPER_PAIR_AGGREGATION',protocol_sha256=run['protocol_sha256'],scores_sha256=run['score_sha256'],source_recipe_offer_rows=sum(len(d)for d in data.values()),proper_score_views=len(proper),calibration_AUC_views=len(diagnostics),primary_P1_side_views=len(p1),primary_P1_side_triplets=len(trip),paired_contrasts=len(pairs),matched_Leaf_C02_GLM_contrasts=method_pairs,empty_comparisons=empty,passing_attempt_examples=examples,new_fits=0,new_inference=0,new_probabilities=0,new_grades=0,limits=['Threeexposedweeks are insufficientforregisteredweekCI; allgameintervals descriptive.','CandidateFULL is supportedqualifiedlossmask; outercoverage and learned/prior contributions separate.','No fixed-Fridayoverlap, matched-controlmaskduplicates, new routing policy or prices included.'])
 with a.output.open('x')as f:json.dump(report,f,indent=2);f.write('\n')
 print(json.dumps(report))
if __name__=='__main__':main()
