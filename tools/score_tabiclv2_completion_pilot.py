"""Map frozen direct-event outputs to the existing C grader and M2 policies."""
import argparse,collections,copy,gzip,hashlib,importlib.util,json,math,pathlib,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
BASE=ROOT/'reports/predictive-value-next-01/B/execution-authorization-02';OUT=BASE/'evaluation-v1'
def module(path,name):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def write(name,d):
 p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():raise FileExistsError(p.name)
 b=(json.dumps(d,indent=2,allow_nan=False)+'\n').encode();p.write_bytes(gzip.compress(b,mtime=0)if p.suffix=='.gz'else b)
def main():
 p=argparse.ArgumentParser();p.add_argument('--grades',type=pathlib.Path,required=True);p.add_argument('--scorer',type=pathlib.Path,required=True);p.add_argument('--interval',type=pathlib.Path,required=True);a=p.parse_args();start=time.process_time()
 if sha(a.grades)!='dbdbf73a23fea1d7d8c90fde666163853f492b0e9686ae068b829b2bc2816a39':raise ValueError('Frozen exact native rows')
 adapter=module(ROOT/'reports/w1w9-comparison-closure-01/B/common-intake/COMMON_SCORER_PARITY_ADAPTER_V1.py','TABICL_PINNED_C_ADAPTER');status,summary,_=adapter.load_common_functions(a.scorer,a.interval)
 ev=module(ROOT/'reports/targeted-accuracy-w1w9-01/B/evaluation/score_m2_v1.py','TABICL_FROZEN_POLICIES')
 source=json.loads(gzip.decompress(a.grades.read_bytes()))['rows'];base=[r for r in source if r['model_key']=='B0'and r['policy']=='P1_MEAN'];law=[r for r in source if r['model_key']=='B0'and r['policy']=='P2_STATISTICAL_LAW'];lawmap={ev.key(r):r for r in law};pred={}
 for path in sorted((BASE/'predictions').glob('2026-W??.json')):
  body=json.loads(path.read_text())
  for row in body['rows']:
   if row['ordinal']in pred:raise ValueError('No duplicate ordinal forecasts')
   pred[row['ordinal']]=row
 if len(base)!=142:raise ValueError('Exact outer board142')
 frames={}
 for method,field in [('TABICLV2','candidate_p_over'),('LOGISTIC','ordinary_p_over')]:
  frame=[]
  for i,original in enumerate(base):
   r=dict(original,method=method,procedure_id='B-TABICLV2-CMP-DIRECT-PILOT-v1:'+method,point=None,probs=None,selected_side=None,status='UNAVAILABLE_FORECAST',available=False,unavailable_reason='W8_W9_NOT_EXECUTED_COST_GATE',fallback=None,attribution='unavailable',target='pass_cmp')
   if r['week']in(5,6):
    b=lawmap[ev.key(r)];r.update(probs=copy.deepcopy(b['probs']),selected_side=b['selected_side'],status='READY',available=True,unavailable_reason=None,fallback='REGISTERED_B0_LAW_STARTUP',attribution='fallback')
   elif i in pred:
    row=pred[i]
    if row['week']!=r['week']:raise ValueError('Ordinal/week identity mismatch')
    value=row[field]
    if not math.isfinite(value)or not 0<=value<=1:raise ValueError('Invalid event probability')
    r.update(probs={'over':value,'under':1-value,'push':0.},selected_side='OVER'if value>.5 else'UNDER'if value<.5 else'ABSTAIN',status='READY'if value!=.5 else'ABSTAIN',available=True,unavailable_reason=None,attribution='learned')
   r['status']=status(r);frame.append(r)
  frames[method]=frame
 for name,key,policy in [('B0_LAW','B0','P2_STATISTICAL_LAW'),('B2_LAW','B2','P2_STATISTICAL_LAW'),('B0_MEAN','B0','P1_MEAN'),('SAVED_ADJUSTED','SAVED_ADJUSTED','REGISTERED_DIRECTION'),('ALWAYS_OVER','ALWAYS_OVER','REGISTERED_DIRECTION'),('ALWAYS_UNDER','ALWAYS_UNDER','REGISTERED_DIRECTION'),('EARLIER_LINE_PREVALENCE','EARLIER_LINE_PREVALENCE','REGISTERED_DIRECTION')]:
  rr=[dict(r,method=name,target='pass_cmp',attribution='reference')for r in source if r['model_key']==key and r['policy']==policy]
  if len(rr)!=142:raise ValueError('Missing unchanged control '+name)
  if name not in('B0_LAW','B2_LAW'):
   for r in rr:r['probs']=None
  frames[name]=rr
 tables=[];scores=[];pairs=[];memberships=[];ownlists=[]
 def table(method,policy,scope,week,rr,mode='RAW'):
  out=summary(rr);selected=[r for r in rr if r['selected_side']in('OVER','UNDER')];decided=[r for r in selected if r['status']in('WIN','LOSS')];prob=ev.probstats(rr,'probs'if mode=='RAW'else'calibrated_probs');prob['typing']='HALFPOINT_OVER_BERNOULLI;NOT_COUNT_CDF'
  out.update(method=method,model_key=method,procedure_id=rr[0]['procedure_id']if rr else method,policy=policy,scope=scope,window=str(week),week_view=str(week),category='pass_cmp',target='pass_cmp',season=2026,actual_weeks=sorted({r['week']for r in decided}),represented_weeks=sorted({r['week']for r in rr}),scheduled_week_domain=[5,6,7,8,9],missing_actual_line_weeks=[1,2,3,4],selected=len(selected),decided=len(decided),available=sum(r['available']for r in rr),unknown=sum(r['status']in('MISSING_ACTUAL','UNKNOWN_PARTICIPATION')for r in selected),fallback_selected=sum(r['attribution']=='fallback'for r in selected),attribution=dict(collections.Counter(r['attribution']for r in rr)),fallback_states=dict(collections.Counter(str(r.get('fallback'))for r in rr)),probability=prob,numerical=None,record_kind='actual_offer_direction_evaluation',evidence_tier='TIER_B_RETAINED_ACTUAL_SOURCE_LINES;QUOTE_CLOCK_UNKNOWN;MAIN_ALT_UNCLASSIFIED;CURRENT_VINTAGE7DAY;EXPOSED',population='CONDITIONAL_QUALIFIED_PLAYED_STAT_ROW_QB_NATIVE142',evaluation_panel_id='B_TABICLV2_NATIVE142:'+scope,primary_admission='LOCAL_NOT_C_ADMITTED_SHADOW_ONLY;PARTIAL_LEARNED_W7',selected_by_week={str(w):sum(r['week']==w for r in selected)for w in range(5,10)},selected_unique_players=len({r['player_id']for r in selected}),selected_unique_player_games=len({ev.key(r)for r in selected}),membership_sha256=ev.digest(sorted(ev.key(r)for r in rr)))
  out['record_id']='B-TABICL-DIR-'+ev.digest([method,policy,scope,str(week)])[:24];tables.append(out);scores.append(out)
  if prob['events']:
   scores.append(dict(record_id='B-TABICL-PROB-'+ev.digest([method,policy,scope,str(week),mode])[:24],record_kind='prop_threshold_probability_evaluation',method=method,procedure_id=out['procedure_id'],category='pass_cmp',target='pass_cmp',season=2026,week_view=str(week),actual_weeks=out['actual_weeks'],evaluation_panel_id=out['evaluation_panel_id'],n=prob['events'],eligible=len(rr),available=out['available'],brier=prob['strict_binary_Over_Brier'],log_loss=prob['log_loss'],reliability=prob,evidence_tier=out['evidence_tier'],probability_conditioning='MODELED_APPEARANCE',probability_score_contract='HALF_MULTICLASS_BRIER_OVER_UNDER_PUSH_V1',primary_admission=out['primary_admission'],population=out['population'],calibration_mode=mode,uncertainty=out['uncertainty'],games=out['games']))
  return out
 learnedkeys={ev.key(r)for r in frames['TABICLV2']if r['attribution']=='learned'and r['available']};commonkeys={ev.key(r)for r in frames['TABICLV2']if r['available']}
 scopes=[('FULL_SYSTEM142',lambda r:True),('FALLBACK_W5_6',lambda r:r['week']in(5,6)),('LEARNED_COMMON_W7',lambda r:ev.key(r)in learnedkeys),('COMMON_AVAILABLE',lambda r:ev.key(r)in commonkeys)]
 for method,rr in frames.items():
  for scope,mask in scopes:
   frame=[r for r in rr if mask(r)];table(method,'BROAD_DIRECTION',scope,'ALL',frame)
   if scope=='FULL_SYSTEM142':
    for w in range(5,10):table(method,'BROAD_DIRECTION',scope,w,[r for r in frame if r['week']==w])
 for method in('TABICLV2','LOGISTIC','B0_LAW','B2_LAW'):
  rows=frames[method];cal=[]
  for w in range(5,10):
   origin=min(ev.dt(r['kickoff'])for r in rows if r['week']==w);cal.extend(r for r in ev.calibrated(rows,origin)if r['week']==w)
  policies=[]
  for n,d,name in [(1,1,'COVERAGE_100'),(1,2,'COVERAGE_50'),(1,4,'COVERAGE_25'),(1,10,'COVERAGE_10')]:policies.append((name,rows,set().union(*(ev.choose_fraction([r for r in rows if r['week']==w],n,d)for w in range(5,10)))))
  for k in(6,10,20):
   for pool in('Combined','OVER','UNDER'):policies.append((f'TOP_{k}_{pool}',rows,set().union(*(ev.choose_top([r for r in rows if r['week']==w],k,pool)for w in range(5,10)))))
  for threshold in(.75,.8,.9):
   for mode,frame in [('RAW',rows),('CALIBRATED_RELIABILITY',cal)]:policies.append((f'THRESHOLD_{int(threshold*100)}_{mode}',frame,{ev.key(r)for r in frame if r['available']and r['selected_side']in('OVER','UNDER')and(r['probs'][r['selected_side'].lower()]if mode=='RAW'else r['calibrated_selected_confidence'])>=threshold}))
  for name,rr,chosen in policies:
   frame=ev.apply_selection(rr,chosen);memberships.append(dict(method=method,policy=name,selected=len(chosen),selected_sha256=ev.digest(sorted(chosen))))
   mode='CALIBRATED_RELIABILITY'if name.endswith('CALIBRATED_RELIABILITY')else'RAW'
   for w in ['ALL',5,6,7,8,9]:table(method,name,'FULL_SYSTEM142',w,frame if w=='ALL'else[r for r in frame if r['week']==w],mode)
   for control in('LOGISTIC','B0_LAW','B2_LAW','B0_MEAN','ALWAYS_OVER','ALWAYS_UNDER'):
    cmap={ev.key(r):r for r in frames[control]};left=[r for r in frame if r['selected_side']in('OVER','UNDER')and r['status']in('WIN','LOSS')];matched=[(r,cmap[ev.key(r)])for r in left if cmap[ev.key(r)]['status']in('WIN','LOSS')]
    if matched:pairs.append(dict(candidate=method,control=control,policy=name,scope='SAME_CANDIDATE_SELECTED_CASES',decided=len(matched),candidate_wins=sum(r['status']=='WIN'for r,s in matched),control_wins=sum(s['status']=='WIN'for r,s in matched),win_difference=sum((r['status']=='WIN')-(s['status']=='WIN')for r,s in matched),side_disagreements=sum(r['selected_side']!=s['selected_side']for r,s in matched)))
 write('RAW_TABLES_V1.json.gz',tables);write('SCORES.json',scores);write('PAIRED_V1.json',pairs);write('MEMBERSHIP_COMMITMENTS_V1.json',memberships)
 # Own-list comparisons: same registered capacity/policy, distinct chosen cases.
 for policy in{r['policy']for r in tables if r['scope']=='FULL_SYSTEM142'}:
  rows={r['method']:r for r in tables if r['policy']==policy and r['scope']=='FULL_SYSTEM142'and r['window']=='ALL'}
  for control in('LOGISTIC','B0_LAW','B2_LAW'):
   if 'TABICLV2'in rows and control in rows:ownlists.append(dict(policy=policy,candidate='TABICLV2',control=control,candidate_own=rows['TABICLV2']['COMBINED'],control_own=rows[control]['COMBINED'],candidate_selected=rows['TABICLV2']['selected'],control_selected=rows[control]['selected'],candidate_unavailable=rows['TABICLV2']['unavailable'],control_unavailable=rows[control]['unavailable'],scope='OWN_LIST_DESCRIPTIVE_NOT_PAIRED_EFFECT;technicalcoverage_differs;matchedcases_separate'))
 write('OWN_LIST_COMPARISONS_V1.json',ownlists);write('RUN_RECEIPT_V1.json',dict(state='EXECUTED_PARTIAL_W7_LEARNED_W5_6_REFERENCE;W8_9_NOT_EXECUTED_COST_GATE',tables=len(tables),canonical_views=len(scores),pairs=len(pairs),actual_new_forecast_rows=56,new_learned_player_games=len(learnedkeys),fallback_rows=56,outer_rows=142,missing_inference_rows=142-len(commonkeys),new_NFL_observations=0,new_fits_here=0,C_scorer_sha256=sha(a.scorer),C_interval_sha256=sha(a.interval),source_grade_sha256=sha(a.grades),CPU_seconds=time.process_time()-start))
 print(json.dumps({'state':'COMMON_SCORER_PARTIAL_GRADES_WRITTEN','views':len(scores),'learned_rows':len(learnedkeys),'CPU':time.process_time()-start}))
if __name__=='__main__':main()
