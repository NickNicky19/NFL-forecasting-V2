"""Bounded static/independent arithmetic review of the supplied starter.

Never imports/executes archive code, builds a simulator or writes raw cases.
The provided canonical outcomes remain grading-only; no new source truths.
"""
from __future__ import annotations
import argparse,ast,collections,datetime,hashlib,json,math,pathlib,resource,time,zipfile
from decimal import Decimal
ROOT=pathlib.Path(__file__).resolve().parents[1];OUT=ROOT/'reports/shared-game-sim-01/B'
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def finite(v):return type(v)in(int,float)and math.isfinite(v)
def pointside(point,line,margin=0):
 if not finite(point)or not finite(line):return None
 return 'over'if point-line>margin else'under'if point-line < -margin else None
STATES=('hit','miss','push','dnp','unresolved')
def result(side,actual,line,unknown):
 if actual is None:return unknown
 y,l=Decimal(str(actual)),Decimal(str(line))
 return 'push'if y==l else'hit'if (y>l)==(side=='over')else'miss'
def tally(rows,arm,margin):
 sides={'over':[],'under':[]};unavailable=abstain=0
 for r in rows:
  if not finite(r[arm]):unavailable+=1;continue
  side=pointside(r[arm],r['line'],margin)
  if side is None:abstain+=1;continue
  sides[side].append(result(side,r['actual'],r['line'],r['outcome_status']))
 def counts(values):
  c=collections.Counter(values)
  if set(c)-set(STATES):raise ValueError('Undefined suppliedcanonicalstate')
  out={key:c[key]for key in STATES};n=c['hit']+c['miss'];return dict(out,n_decided=n,pct=round(100*c['hit']/n,1)if n else None)
 out=counts(sides['over']+sides['under']);out.update(eligible=len(rows),selected=sum(len(v)for v in sides.values()),unavailable=unavailable,abstained=abstain,selected_coverage=sum(len(v)for v in sides.values())/len(rows)if rows else None,over=counts(sides['over']),under=counts(sides['under']));return out

def main():
 p=argparse.ArgumentParser();p.add_argument('--zip',type=pathlib.Path,required=True);a=p.parse_args();cpu=time.process_time();wall=time.monotonic();zipbytes=a.zip.read_bytes();zipsha=hashlib.sha256(zipbytes).hexdigest()
 if zipsha!='afcd4cfc52685657f969a80651831b075f9351ef298dda0a0553791f7444b365':raise ValueError('Different suppliedZIP; do notsilentlyreplace')
 with zipfile.ZipFile(a.zip)as z:
  infos=z.infolist()
  if len(infos)!=29 or sum(i.file_size for i in infos)>10485760:raise ValueError('Boundedoriginalarchiveinventory')
  if any(pathlib.PurePosixPath(i.filename).is_absolute()or'..'in pathlib.PurePosixPath(i.filename).parts for i in infos):raise ValueError('Unsafearchivepath')
  manifest=json.loads(z.read('SHA256SUMS.json'));checks=[]
  for name,expected in manifest.items():
   body=z.read(name)
   if len(body)!=expected['bytes']or hashlib.sha256(body).hexdigest()!=expected['sha256']:raise ValueError('Deliveredbodyhash mismatch '+name)
   checks.append(dict(member=name,bytes=len(body),sha256=expected['sha256'],state='PASS_DELIVERED_CURRENT_BYTES'))
  bindings=json.loads(z.read('SOURCE_BINDINGS.json'));lf=[]
  for r in bindings:
   if r.get('original_source_sha256'):
    body=z.read(r['local_path'])
    if body[-1:]!=b'\n'or hashlib.sha256(body[:-1]).hexdigest()!=r['original_source_sha256']:raise ValueError('One-LFsource restoration mismatch')
    lf.append({'member':r['local_path'],'state':'PASS_REMOVE_EXACTLY_ONE_ADDED_LF','source_sha256':r['original_source_sha256']})
  queries=[json.loads(x)for x in z.read('queries/evaluation_cases_ungraded.jsonl').splitlines()];outcomes=[json.loads(x)for x in z.read('grading_only/outcomes.jsonl').splitlines()];original=json.loads(z.read('comparison/category_rows.json'));supplied=json.loads(z.read('comparison/category_results.json'))
  tree=ast.parse(z.read('comparison/pull/scoring.py'));categories=next(ast.literal_eval(node.value)for node in tree.body if isinstance(node,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='CATEGORIES'for t in node.targets));inputmanifest=json.loads(z.read('comparison/input_manifest.json'));missinglegacy=[name for name in inputmanifest if 'comparison/'+name not in z.namelist()]
 if len(queries)!=3474 or len(outcomes)!=3474:raise ValueError('Full3474outerframe')
 qmap={r['case_id']:r for r in queries};omap={r['case_id']:r for r in outcomes}
 if len(qmap)!=3474 or set(qmap)!=set(omap):raise ValueError('CaseIDs notunique/bijective')
 allowed={'case_id','source_revision','season','week','game_id','player_id','category','line','venue','name','position','point_source','saved_raw_point','saved_adjusted_point','provider_first_point','saved_lean','forecast_issuance_authentication','quote_clock_authentication','scope'}
 if any(set(q)!=allowed for q in queries):raise ValueError('Different queryfieldallowlist')
 if any(q['source_revision']!='f15790bc1396e532eb0f6991f8e05dbf6a66fb2d'or q['season']!=2026 or q['week']not in range(4,10)for q in queries):raise ValueError('Frameversion/season/week')
 def key(q):return(q['week'],str(q['game_id']),str(q['player_id']),q['category'],q['line'],q['venue'])
 lookup={}
 for cat,rows in original.items():
  for r in rows:
   k=(r['week'],str(r['game_id']),str(r['pid']),cat,r['line'],r['venue'])
   if k in lookup:raise ValueError('Duplicate originalcasekey')
   lookup[k]=r
 if len(lookup)!=3474 or {key(q)for q in queries}!=set(lookup):raise ValueError('Query/originalrowidentityset mismatch')
 for q in queries:
  r=lookup[key(q)];o=omap[q['case_id']];expected=q['saved_raw_point']if q['point_source']=='model'and finite(q['saved_raw_point'])else q['saved_adjusted_point']
  if q['provider_first_point']!=expected:raise ValueError('W1fallback changed')
  if(q['saved_raw_point'],q['saved_adjusted_point'],q['provider_first_point'],q['point_source'],q['position'])!=(r['raw'],r['incumbent'],r['provider_first'],r['source'],r['pos']):raise ValueError('Typedforecastfield mismatch')
  if(o['actual'],o['extraction_status_for_over_query'])!=(r['actual'],r['outcome_status']):raise ValueError('Canonicaloutcome linkage changed')
 metrics=[];cells=[];arithmeticchecks=0
 for cat,rows in original.items():
  for window,rr in [('ALL',rows)]+[(str(w),[r for r in rows if r['week']==w])for w in range(4,10)]:
   expected=supplied['categories'][cat]['combined'if window=='ALL'else'weekly']
   if window!='ALL':expected=expected[window]
   common=[r for r in rr if finite(r['incumbent'])and finite(r['provider_first'])]
   for arm,label in [('incumbent','W0_SAVED_ADJ_STRICT_POINT'),('provider_first','W1_LITERAL_MODEL_PROJ_ELSE_ADJ')]:
    got=tally(common,arm,0);wanted=expected['strict_common_forecast_mask'][arm]
    if got!=wanted:raise ValueError('Independentstrictarithmetic mismatch '+cat+'/'+window+'/'+arm)
    arithmeticchecks+=1;metrics.append(dict(category=cat,window=window,method=label,evidence='PROVIDED_CANONICAL_ROW_REPLAY;TIMING_UNAUTHENTICATED;NOT_NEW_FORECAST_TEST',games=len({r['game_id']for r in rr}),player_games=len({(r['game_id'],r['pid'])for r in rr}),unknown_outcomes=sum(r['actual']is None for r in rr),**got))
    gotmargin=tally(rr,arm,categories[cat]['lean'])
    if gotmargin!=expected['own_margin_policies'][arm]:raise ValueError('Independentmarginarithmetic mismatch '+cat+'/'+window+'/'+arm)
    arithmeticchecks+=1
   if window!='ALL':cells.append({'category':cat,'week':int(window),'eligible':len(rr),'known':sum(r['actual']is not None for r in rr),'unknown':sum(r['actual']is None for r in rr),'games':len({r['game_id']for r in rr}),'state':'PASS_BOTH_STRICT_AND_REGISTERED_MARGIN_SOURCE_ARITHMETIC'})
 if len(cells)!=60 or len(supplied['parity'])!=60 or not all(r['passed']and r['saved_side_mismatches']==0 for r in supplied['parity']):raise ValueError('Suppliedsaved60cellparity notintact')
 weekly=[]
 for w in range(4,10):
  rr=[q for q in queries if q['week']==w];weekly.append({'week':w,'cases':len(rr),'games':len({q['game_id']for q in rr}),'player_games':len({(q['game_id'],q['player_id'])for q in rr}),'unknown_outcomes':sum(omap[q['case_id']]['actual']is None for q in rr),'venues':dict(collections.Counter(q['venue']for q in rr))})
 report={'id':'B-SHARED-GAME-SIM-STARTER-FRAME-REVIEW-v3','UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'state':'PASS_PROVIDED_FRAME_INTEGRITY_AND_CANONICAL_ROW_ARITHMETIC;SIMULATOR_NOT_TESTED','source_zip':{'supplied_filename':'NFL_Simulator_Comparison_Starter_2026-11-21.zip','bytes':len(zipbytes),'sha256':zipsha,'members':29,'delivered_current_hash_checks':checks,'decoded_total_bytes':sum(i.file_size for i in infos),'archive_source_LF_checks':lf,'legacy_manifest_missing_members':missinglegacy,'missing_member_scope':'Originalanalysisprovenancereferencescategory_run_output andpaired_strict_uncertainty absentfromdeliveredbundle; currentSHA256SUMS set28membersallpasses, noinventedbodiesorcorruptionclaim.'},'source_revision':'f15790bc1396e532eb0f6991f8e05dbf6a66fb2d','full_frame':{'cases':3474,'unique_case_ids':len(qmap),'categories':list(original),'games':len({q['game_id']for q in queries}),'player_games':len({(q['game_id'],q['player_id'])for q in queries}),'unknown_outcomes':sum(o['actual']is None for o in outcomes),'venues':dict(collections.Counter(q['venue']for q in queries)),'point_source_flags':dict(collections.Counter(q['point_source']for q in queries)),'case_membership_sha256':digest(sorted(qmap)),'role_by_category':{cat:dict(collections.Counter(q['position']for q in queries if q['category']==cat))for cat in original},'identity_namespace':'All3474gameandplayerIDsare numericwebsite/ESPNnamespace; not automaticallyBcanonicalNFL/GSIS. Usequalifiedexplicitbridge, nevernames.'},'weekly':weekly,'query_boundary':{'actual_query_keys':sorted(allowed),'outcome_keys':sorted(set().union(*(set(o)for o in outcomes))),'no_outcome_columns_in_query_view':True,'target_postgame_statistics_forecast_admitted':False,'not_a_worker_leakage_PASS':'ActualC forecastworker+fullteammatecontext+seed/design/predictionmutationnotreceived/executed. Queryviewfieldseparation alonecannotpassit.','source_clocks':'Retainedarchive/quotetimingunauthenticated. No re-observation clockbackdating.','missing_required_engine_components':'ZIPqueryview lacks explicitteam/opponent/fullteammateuniverse andearlierpace/opportunity/eventtrainingmatrix. AdditionaldeclaredadmittedCinputs mayfillthese; nooptionalinjury/alignmentgateinvented.'},'baseline_contract':{'W0':'Literal saved_adjusted_point=archiveadj strictpointdirection','W1':'saved_raw_point=archiveprojiffpoint_source=modelandfinite;otherwiseW0adjustedfallback','no_blanket_multiplier_removal':True,'probability_products':'W0/W1pointonly; nop_over/EVfromgap','selectors':'Registeredcategorymargin/TopPicks areseparatefromstrictdirection; sourcegradeisstatisticalcrossingnotqualifiedvenuesettlement','source_hint':'model sourceflagdoesnotindependentlyauthenticateproviderorigin/availability; Cdeclaresadmittedproviderfieldsemantics.'},'verification':{'independent_Strict_and_margin_aggregate_checks':arithmeticchecks,'weekly_category_cells':60,'saved60grade_parity_flags':'Retainedauthorchecksalltrue; BindependentDecimaldirections/gradesandaggregateownmargin/strictcountsagree onprovidedcanonicalrows.','re_audited_original_NFL_outcome_truth':False,'new_candidate_grades':0,'new_simulation_trajectories':0,'new_fits':0,'code_from_ZIP_executed':False,'unknown_policy':'464unknownstayunknown; extractionstatusforOverisnotselectedsidegrade; no DNP/zero/voidinference.'},'engine_admission':'C ownsengine/inputREADYclassification; thisframeauditdoesnotestablishREADY_STATEFUL/READY_BOX_SCORE orcurrentpregamedelivery.','CPU_seconds':time.process_time()-cpu,'wall_seconds':time.monotonic()-wall,'peak_RSS_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'accounting':'Existingreporting/verificationmetadataonly; launcher/import/exit/orchestrationtailsunmetered; noclosedscientificbudgettransfer.'}
 OUT.mkdir(parents=True,exist_ok=True)
 for name,body in [('STARTER_FRAME_REVIEW_V3.json',report),('BASELINE_SOURCE_ARITHMETIC_V1.json',{'state':'INDEPENDENT_EXISTING_CANONICAL_SOURCE_ROW_REPLAY_NOT_NEW_SCIENTIFIC_COMPARISON','metrics':metrics,'cells':cells,'new_NFL_observations':0,'unknowns_preserved':True})]:
  path=OUT/name
  if path.exists():raise FileExistsError(path.name)
  path.write_text(json.dumps(body,indent=2,allow_nan=False)+'\n')
 print(json.dumps({'state':report['state'],'cases':3474,'known':3474-report['full_frame']['unknown_outcomes'],'unknown':report['full_frame']['unknown_outcomes'],'category_week_cells':60,'arithmeticchecks':arithmeticchecks,'CPU':report['CPU_seconds']}))
if __name__=='__main__':main()
