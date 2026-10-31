"""Saved-row metadata/law admissibility audit; no model execution or scoring."""
from __future__ import annotations
import argparse,bisect,collections,csv,gzip,hashlib,json,math,resource,sys,time
from datetime import datetime,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2.shared_subgroups import packet_rows,canonical,sha,now,write
from nfl_v2.identity import unique_gsis_bridge
from nfl_v2.week8_shadow import schedules
from tools.numerical_championship import normalize,csvwrite
VERSION='v2-rolling-known-target-time-admission-20261031g-v1'
T='2026-10-23T17:49:53Z'
F='reports/championship-20261030f/offer-expansion/full-pool-v1/FROZEN_PROTOCOL.json'
PUB={'hgb':'reports/continuation-20261029/hgb-history-v1','laws':'reports/continuation-20261030/distribution-wave-v2','count':'reports/continuation-20261030/count-ablation-wave-v1','c02':'reports/continuation-20261030b/ordered-information-ablation-v1','defense':'reports/continuation-20261030c/qualified-defense-information-v1'}

def epoch(v):
 if v in(None,''):return None
 try:return float(v)
 except(ValueError,TypeError):return datetime.fromisoformat(v.replace('Z','+00:00')).timestamp()
def prepare(a):
 if a.output.exists()or a.private_output.exists():raise ValueError('fresh outputs required')
 a.output.mkdir(parents=True);a.private_output.mkdir(parents=True)
 f=json.loads(a.metadata_receipt.read_bytes());np=json.loads((a.root/'reports/championship-20261030f/numerical-v2/FROZEN_PROTOCOL.json').read_bytes());raw=next(x for x in np['sources']if x['season']==2026)
 for path,want in[(a.metadata,f['metadata_sha256']),(a.source_root/'games.csv',f['source_schedule_sha256']),(a.source_root/'roster-week8-identity-2026.csv.gz',f['identity_bridge_sha256'])]:
  if sha(path)!=want:raise ValueError('bound metadata/identity/schedule changed')
 history_sources=json.loads((a.root/'reports/continuation-20261029/hgb-history-v1/FROZEN_PROTOCOL.json').read_bytes())['source_ids']
 for h in history_sources:
  if sha(a.source_root/h['name'])!=h['sha256']:raise ValueError('historical context source changed')
 fits=[]
 for source,pub in PUB.items():
  for path in sorted((a.root/pub).glob('*-FIT.json')):
   if path.name.startswith(f'W{a.week:02}-'):fits.append(dict(source_id=source,path=path.relative_to(a.root).as_posix(),sha256=sha(path)))
 p=dict(version=VERSION,state='FROZEN_BEFORE_NEW_METADATA_COMPARISON_OR_DIRECTION_OUTCOMES',registered_at=now(),code_sha256=sha(__file__),decision_time='PER_OFFER_AUTHENTIC_SERVER_SOURCE_CLOCK',decision_time_mode='PER_OFFER_CAPTURE',evaluation_week=a.week,panel_id=a.panel_id,parent_offer_protocol=a.metadata_receipt.relative_to(a.root).as_posix(),parent_offer_protocol_sha256=sha(a.metadata_receipt),metadata_sha256=sha(a.metadata),identity_sha256=sha(a.source_root/'roster-week8-identity-2026.csv.gz'),schedule_sha256=sha(a.source_root/'games.csv'),raw_sources=raw,fit_receipts=fits,history_context_sources=history_sources,forecast_population='Original primary and extended saved rows; full462 offer universe preserved, missing method/query support remains unavailable',
  contracts={'clock_age':'Original querycutoff age at currentclock changes if evaluated earlier; require reconstruction unless no model/age consumed.', 'known_target_time':'NEW retrospective policy: availability mask usesdecisiont; age is relative to foreknown scheduled targetkickoff. If no consumed record arrives between t and savedquerycutoff and training/prior/transforms are eligible, the savedvector/law remains identical. Not original issuance.','c02':'All explicit lag age/value/missing columns dropped; mean3/n3/mean8/n8+position constant between eligible source arrivals.','context':'Exact retained pregame offer position corroborates saved query position; fixed schedule identifies foreknown kickoff. Current-vintage bridge disclosed. D1/D2team/defense additionally requires earlier eligible team carryforward matching saved context or authenticated snapshot team. Retrospective participantpanel/qualifiedretained-context tier, not purefootballonly or full exanteforecastpopulation.','strict':'Require every consumed source/fit/prior latest timestamp strictly<t; nominalfitcutoff may be later only when maxconsumedtraininglabel/features<t proves identical earlier eligibility prefix under registered all-earlier-target-row selection and fixedseed/parameters; this is a NEW earlier-origin reconstruction, not original issuance; calibration/selector absent in fixed recipes. Never substitute actual target outcomes for inputs.','fallback':'HGB/empirical query-updated target-history prefix requires latestfallback/targethistory<t. Law fallback prior fixed atweeklyfit; routing source availability required for coldstart.','probability':'Quantiles/CRPS/zero_mass/leaf_ids alone do not identify a CDF. Parametric/fallback law parameters can qualify; learned leaf law requires saved support/weights or separate qualified model-histogram extraction. No point-to-probability fabrication.'},
  exposure='All F/2026W1-7 labels previously exposed; audit uses metadata and saved-law parameters only and computes no new wins/losses/probabilities. A separate frozen selectioncomparison is required before grading.',selection_future='P1unrounded savedpoint versus original retainedline; P2onlyfullyrecoveredconditional-law probabilities and unchangednonvoidcontract; no prices/ROI. No decisions scored in this audit.',
  budget=dict(max_wall_seconds=180,max_CPU_seconds=240,max_RSS_bytes=1073741824,max_private_bytes=8388608,max_rows=2500000,max_threads=1),new_fits=0,new_inference=0,new_scores=0,Week8_outcomes_read=0)
 write(a.output/'FROZEN_PROTOCOL.json',p);print(json.dumps(dict(state=p['state'],sha256=sha(a.output/'FROZEN_PROTOCOL.json'),fit_metadata_receipts=len(fits))))
def run(a):
 p=json.loads((a.output/'FROZEN_PROTOCOL.json').read_bytes());start,cpu=time.monotonic(),time.process_time();t=None
 if p['code_sha256']!=sha(__file__):raise ValueError('sealed executor changed')
 meta=json.loads(gzip.decompress(a.metadata.read_bytes()))['rows'];games=schedules(a.source_root/'games.csv');offers={};unmapped=0
 for r in meta:
  r['category']=r['target'];g=games.get(r['game_id']);q=(r['game_id'],r['player_id'],r['target'])
  if not g or r.get('identity_state')!='EXACT_SCHEDULE_AND_STABLE_ID_BRIDGE':raise ValueError('qualified stable identity required')
  if q in offers:raise ValueError('duplicate canonical offer')
  dt=epoch(r['source_server_clock'])
  if epoch(r['kickoff'])!=g['kickoff']or dt>g['kickoff']-5400:raise ValueError('source clock/horizon mismatch')
  offers[q]=r
 t=max(epoch(r['source_server_clock'])for r in meta)
 # Earlier eligible identity/team metadata, never target-game outcomes.
 histories=collections.defaultdict(list)
 for y in range(2022,2027):
  with(a.source_root/f'stats_player_week_{y}.csv').open()as f:
   for r in csv.DictReader(f):
    if r['season_type']!='REG'or(y==2026 and int(r['week'])>7):continue
    g=games.get(r['game_id'])
    if g and g['kickoff']+7*86400<t:histories[r['player_id']].append((g['kickoff']+7*86400,r['position'],r['team']))
 for vals in histories.values():vals.sort()
 fits={}
 for b in p['fit_receipts']:
  path=a.root/b['path']
  if sha(path)!=b['sha256']:raise ValueError('fit metadata changed')
  fits[b['source_id'],path.name[:-9]]=dict(json.loads(path.read_bytes()),public_receipt=b['path'])
 records=[];count=0;seen=set()
 for binding in p['raw_sources']['members']:
  source=binding['source_id'];file=a.private_root/binding['member']
  if source=='chart':continue
  if source=='hgb'and not Path(binding['member']).name.startswith(f'W{a.week:02}-'):continue
  if sha(file)!=binding['sha256']:raise ValueError('saved input changed')
  it=packet_rows(file)if binding['kind']=='packet'else csv.DictReader(gzip.open(file,'rt'))
  for index,r in enumerate(it):
   count+=1
   if count%10000==0:
    if count>2500000 or time.monotonic()-start>180 or time.process_time()-cpu>240 or resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>1073741824:raise RuntimeError('bounded metadata audit limit')
   if int(r.get('season',2026))!=2026 or int(r['week'])!=a.week:continue
   q=(r['game_id'],r['player_id'],r['target'])
   if q not in offers:continue
   norm=normalize(dict(r,population='primary'),source,2026)
   if norm is None:continue
   k,_=norm;target,proc,arm,product=k;o=offers[q];t=epoch(o['source_server_clock']);unit=(q,proc,arm,product)
   if unit in seen:raise ValueError('duplicate saved recipe/offer')
   seen.add(unit);reasons=[];latest=epoch(r.get('latest_feature_available'));fallback=r.get('fallback');slot=r.get('fit_slot')
   if source=='count':slot=f'W{a.week:02}-{target}-{r["policy_id"]}-{r["procedure_family_id"]}'
   fit=fits.get((source,slot))if slot else None
   if source!='empirical'and fit is None:reasons.append('FIT_METADATA_REQUIRED')
   ft=epoch(fit.get('fit_cutoff_utc',fit.get('training_label_fit_cutoff_utc')))if fit else None
   fitlatest=[epoch(fit.get(x))for x in('latest_training_label_available','latest_training_feature_available','latest_training_consumed_feature_available')]if fit else[]
   if fit and(ft is None or any(v is not None and v>=t for v in fitlatest)):reasons.append('FIT_TRAINING_OR_PRIOR_AFTER_DECISION')
   if o.get('position')!=r.get('position'):reasons.append('PREGAME_POSITION_PARITY_REQUIRED')
   if r.get('prediction')in(None,''):reasons.append('PREDICTION_UNAVAILABLE')
   cutoff=epoch(r.get('cutoff',r.get('cutoff_epoch_utc')));kick=epoch(o['kickoff'])
   if cutoff!=kick:reasons.append('SAVED_QUERY_CUTOFF_NOT_BOUND_TARGET_KICKOFF')
   if source=='empirical':
    consumed=epoch(r.get('latest_training_available_epoch_utc'));policy='TARGET_HISTORY_PREFIX'
    if consumed is not None and consumed>=t:reasons.append('TARGET_HISTORY_AFTER_DECISION')
   elif fallback not in(None,'none')and source=='hgb':
    consumed=epoch(r.get('latest_fallback_available'));policy='QUERY_UPDATED_EMPIRICAL_FALLBACK'
    if consumed is not None and consumed>=t:reasons.append('FALLBACK_AFTER_DECISION')
   elif fallback not in(None,'none')and source=='count':
    consumed=None;policy='COUNT_FALLBACK_FLAT_MISSING_LAST_CONSUMED';reasons.append('COUNT_FALLBACK_CHUNK_TIMING_REQUIRED')
   else:
    consumed=latest;policy='C02_SOURCE_INTERVAL_INVARIANT'if source=='c02'else'KNOWN_TARGET_TIME_SAVED_VECTOR'
    if latest is not None and latest>=t:reasons.append('QUERY_SOURCE_AFTER_DECISION')
   if source=='defense':
    hist=[h for h in histories.get(r['player_id'],[])if h[0]<t];last=hist[-1]if hist else None;team=r.get('team');defense=r.get('defense');g=games[r['game_id']];preteam=o.get('team');preteam='LA'if preteam=='LAR'else preteam
    if (preteam!=team and(not last or last[2]!=team))or team not in(g['home'],g['away'])or defense!=(g['away']if team==g['home']else g['home']):reasons.append('PREGAME_TEAM_DEFENSE_CONTEXT_REQUIRED')
   law=r.get('law_reference');law=json.loads(law)if isinstance(law,str)and law else law or{};params=law.get('fallback_prior',law.get('parametric'));fullparams=isinstance(params,dict)and params.get('kind')in('zero','bernoulli','geometric','poisson','signed');hasleaf='leaf_ids'in law
   point_state='ELIGIBLE_NEW_RETROSPECTIVE_SAVED_VECTOR'if not reasons else'INELIGIBLE_OR_DEPENDENCY'
   p2='ELIGIBLE_COMPLETE_SAVED_PARAMETRIC_LAW'if not reasons and fullparams else'COMPLETE_LAW_BUT_TIMING_OR_CONTEXT_BLOCKED'if fullparams else'LEARNED_LEAF_WEIGHTS_SUPPORT_REQUIRE_RECOVERY_EXTRACTION'if hasleaf else'NO_AUTHENTICATED_DISTRIBUTION'
   records.append(dict(offer_safe_id=hashlib.sha256(canonical([q,o['source_row_index']])).hexdigest(),source_row_index=o['source_row_index'],procedure_id=proc,history_regime=arm,product_id=product,target=target,population=r['population'],position=r['position'],source_id=source,source_member=binding['member'],source_member_sha256=binding['sha256'],source_row_index_in_member=index,query_cutoff=cutoff,foreknown_target_kickoff=kick,decision_time=o['source_server_clock'],nominal_fit_after_decision=bool(ft is not None and ft>=t),nominal_fit_reuse_rule='Identicalearliertrainingprefixprovedfrommaxconsumedlabel/features andoriginalall-eligible-target-rowfitrule; fixedseed/parameters, no newfit',latest_consumed_available=consumed,latest_feature_available=latest,fit_cutoff=ft,fit_receipt=fit.get('public_receipt')if fit else None,fallback=fallback,p1_state=point_state,p2_state=p2,reasons=reasons,feature_contract=policy,original_issuance=False,full_law_parameters_retained=fullparams,leaf_ids_without_weights=hasleaf))
 groups=collections.defaultdict(list)
 for r in records:groups[r['target'],r['procedure_id'],r['history_regime'],r['product_id']].append(r)
 summary=[]
 for k,rr in sorted(groups.items()):
  target,proc,arm,product=k;universe=sum(o['category']==target for o in meta);eligible=[r for r in rr if r['p1_state']=='ELIGIBLE_NEW_RETROSPECTIVE_SAVED_VECTOR'];p2=[r for r in rr if r['p2_state']=='ELIGIBLE_COMPLETE_SAVED_PARAMETRIC_LAW']
  summary.append(dict(target=target,procedure_id=proc,history_regime=arm,product_id=product,season=2026,week=a.week,decision_time='PER_OFFER_AUTHENTIC_SERVER_SOURCE_CLOCK',evidence='NEW_RETROSPECTIVE_KNOWN_TARGET_TIME_RECONSTRUCTION_METADATA_ADMISSION',eligible_offer_universe=universe,saved_query_rows=len(rr),missing_saved_query_rows=universe-len(rr),P1_admissible=len(eligible),P1_unavailable_or_timing_context_blocked=universe-len(eligible),P2_complete_law_admissible=len(p2),P2_missing_or_blocked=universe-len(p2),P1_eligible_mask_sha256=hashlib.sha256(canonical(sorted(r['offer_safe_id']for r in eligible))).hexdigest(),P2_eligible_mask_sha256=hashlib.sha256(canonical(sorted(r['offer_safe_id']for r in p2))).hexdigest(),reason_counts=dict(collections.Counter(reason for r in rr for reason in r['reasons'])),P2_state_counts=dict(collections.Counter(r['p2_state']for r in rr)),feature_contracts=sorted({r['feature_contract']for r in rr}),selection_performance=None,performance_missing_reason='METADATA_ADMISSION_ONLY_NO_NEW_SELECTION_GRADES',source_vintage='current-vintage football reconstruction; inherited7d assumption; pregame retained position/schedule context; neveroriginalmodelissuance'))
 mask=gzip.compress(canonical(dict(rows=records)),mtime=0)
 if len(mask)>8388608:raise ValueError('private derivative retention bound')
 with(a.private_output/'ADMISSIBILITY_MASK.json.gz').open('xb')as f:f.write(mask)
 write(a.output/'THRESHOLD_ADMISSIBILITY.json',summary);csvwrite(a.output/'THRESHOLD_ADMISSIBILITY.csv',summary);receipt=dict(state='COMPLETE_METADATA_AND_SAVED_LAW_ADMISSION_AUDIT_NOT_SCORED',at=now(),protocol_sha256=sha(a.output/'FROZEN_PROTOCOL.json'),summary_sha256=sha(a.output/'THRESHOLD_ADMISSIBILITY.json'),mask_sha256=hashlib.sha256(mask).hexdigest(),mask_bytes=len(mask),offer_universe=len(meta),unmapped_identity_rows=unmapped,matched_recipe_offer_rows=len(records),P1_admissible_recipe_offer_views=sum(r['P1_admissible']for r in summary),P2_admissible_recipe_offer_views=sum(r['P2_complete_law_admissible']for r in summary),raw_rows_scanned=count,new_fits=0,new_inference=0,new_scores=0,Week8_outcomes_read=0,resources=dict(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024));write(a.output/'RUN_RECEIPT.json',receipt);print(json.dumps(receipt))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=('prepare','run'));p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--output',type=Path,required=True);p.add_argument('--private-output',type=Path,required=True);p.add_argument('--private-root',type=Path,required=True);p.add_argument('--metadata',type=Path,required=True);p.add_argument('--source-root',type=Path,required=True);p.add_argument('--metadata-receipt',type=Path,required=True);p.add_argument('--week',type=int,choices=(6,7),required=True);p.add_argument('--panel-id',required=True);a=p.parse_args();a.metadata_receipt=a.metadata_receipt.resolve();prepare(a)if a.action=='prepare'else run(a)
