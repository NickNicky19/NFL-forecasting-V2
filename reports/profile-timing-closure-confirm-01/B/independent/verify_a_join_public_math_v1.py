"""Independent aggregate arithmetic only; private row/clock parity is unknown."""
import csv,hashlib,json,math
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];OUT=Path(__file__).resolve().parent
CACHE=Path('/workspace/research-evidence/profile-timing-closure-confirm-01/A-receipts')
STEM='reports/abc-championship/profile-increment-to-release-01/closure-next-02'
A=CACHE/STEM;COMMIT='375caf0f9b51e39e7df553421fa27ded8701d428'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_bytes())
def rows(folder,pattern):return[r for p in sorted((A/folder).glob(pattern))for r in csv.DictReader(p.open(newline=''))]
def num(v):return None if v in(None,'')else Decimal(str(v))
checks=0;largest=Decimal(0)
def eq(a,b,tol='0.00000000001'):
 global checks,largest
 checks+=1;a,b=num(a),num(b)
 if a is None or b is None:assert a is b,(a,b);return
 d=abs(a-b);largest=max(largest,d);assert d<=Decimal(tol),(a,b,d)
def rate(w,n,r):eq(Decimal(w)/Decimal(n)if int(n)else None,r)
def n(r,k):
 value=r[k]
 if value==''and k.endswith(('_wins','_losses')):
  side=k.rsplit('_',1)[0]
  # Empty aggregate buckets have an explicit zero decisive denominator.
  # This never fills an unknown player statistic, and their rates stay null.
  assert r.get(side+'_decided')=='0',(k,r)
  return 0
 return int(value)
download=read(CACHE/'DOWNLOAD_MANIFEST.json')
for r in download:
 p=CACHE/r['path'];assert sha(p)==r['sha256']and p.stat().st_size==r['bytes']
table_files=[]
for folder,manifest in(('b-completion-public-v2','MANIFEST.json'),('c03-public-v1','MANIFEST_V1.json')):
 d=read(A/folder/manifest)
 for r in d['files']:
  p=A/folder/r['path'];assert sha(p)==r['sha256']and p.stat().st_size==r['bytes'];eq(len(list(csv.DictReader(p.open(newline='')))),r['rows']);table_files.append(dict(path=f'{STEM}/{folder}/{r["path"]}',sha256=sha(p),bytes=p.stat().st_size))
brows=[]
for pat in('ANNUAL_ACTUAL*.csv','MIXED_DIAGNOSTIC*.csv','SITE_DIAGNOSTIC*.csv','ALIAS_COVERAGE*.csv','PRESERVED_V1*.csv'):brows+=rows('b-completion-public-v2',pat)
for r in brows:
 eq(n(r,'over_wins')+n(r,'over_losses'),r['over_decided']);eq(n(r,'under_wins')+n(r,'under_losses'),r['under_decided'])
 for field in('wins','losses','decided'):eq(n(r,'over_'+field)+n(r,'under_'+field),r['combined_'+field])
 for side in('over','under','combined'):rate(r[side+'_wins'],r[side+'_decided'],r[side+'_rate'])
 eq(n(r,'selected')+n(r,'unavailable')+n(r,'abstained'),r['eligible'])
 eq(n(r,'combined_decided')+sum(n(r,k)for k in('UNKNOWN_PARTICIPATION','MISSING_ACTUAL','DNP','PENDING','PUSH')),r['selected'])
 assert all(n(r,k)==0 for k in('UNKNOWN_PARTICIPATION','MISSING_ACTUAL','DNP','PENDING','PUSH'))
 eq(r['bookmaker_settlement_unresolved_selected'],r['selected'])
 for metric in('numeric_MAE','numeric_MSE'):
  if n(r,'numeric_scored')==0:assert num(r[metric])is None
 if n(r,'numeric_scored'):
  assert num(r['numeric_MAE'])**2<=num(r['numeric_MSE'])+Decimal('1e-10')
 if r['candidate_id'].endswith('::P2'):eq(r['numeric_scored'],0)
 if not n(r,'law_events'):assert num(r['law_Brier'])is None
 else:assert num(r['law_Brier'])>=0;eq(r['law_neutral_binary_half_Brier'],'.25')
 retained=json.loads(r['retained_threshold_weeks']);diagnostic=json.loads(r['diagnostic_weeks'])
 assert set(retained)<=set(range(1,6))and set(diagnostic)<=set(range(1,8))
 assert(r['five_week_duration_only']=='True')==(len(set(retained))>=5)
 assert r['source_timing']=='UNVERIFIED_RECONSTRUCTION_NOT_ORIGINAL_ISSUANCE'
bfull={(r['source_panel'],r['candidate_id'],r['week_view']):r for r in brows if r['view']=='FULL_A_BOARD'}
assert len(bfull)==374
count_fields=['eligible','selected','unavailable','abstained','over_wins','over_losses','over_decided','under_wins','under_losses','under_decided','combined_wins','combined_losses','combined_decided','numeric_scored','law_events']
def combine(total,parts,counter_fields,numericprefix):
 for f in counter_fields:eq(sum(n(r,f)for r in parts),n(total,f))
 for suffix,den in(('MAE','scored'),('MSE','scored'),('bias','scored')):
  f=numericprefix+suffix;nf=numericprefix+den
  if n(total,nf):eq(sum(Decimal(r[nf])*num(r[f])for r in parts if n(r,nf))/Decimal(total[nf]),total[f])
for candidate in sorted({r['candidate_id']for r in bfull.values()}):
 for panel in('ALL','ANNUAL_NAMED_NJ','SITE_RECORDED_DK_JURISDICTION_UNKNOWN'):
  total=bfull[panel,candidate,'ALL'];weekly=[r for(p,c,w),r in bfull.items()if(p,c)==(panel,candidate)and w!='ALL']
  combine(total,weekly,count_fields,'numeric_')
  if n(total,'law_events'):
   for f in('law_Brier','law_three_state_log_loss'):eq(sum(Decimal(r['law_events'])*num(r[f])for r in weekly if n(r,'law_events'))/Decimal(total['law_events']),total[f])
 combine(bfull['ALL',candidate,'ALL'],[bfull[p,candidate,'ALL']for p in('ANNUAL_NAMED_NJ','SITE_RECORDED_DK_JURISDICTION_UNKNOWN')],count_fields,'numeric_')
 alias=[r for r in brows if r['candidate_id']==candidate and r['view']!='FULL_A_BOARD']
 for panel in('ALL','ANNUAL_NAMED_NJ','SITE_RECORDED_DK_JURISDICTION_UNKNOWN'):
  parts=[r for r in alias if r['source_panel']==panel];assert len(parts)==2
  combine(bfull[panel,candidate,'ALL'],parts,count_fields,'numeric_')
for panel in('ALL','ANNUAL_NAMED_NJ','SITE_RECORDED_DK_JURISDICTION_UNKNOWN'):
 for arm in('R0','R1','R2','R3'):
  prefix='B-QB-OPPORTUNITY-PROFILE-INCREMENT-v1:'+arm
  for suffix in('over_wins','over_losses','under_wins','under_losses','combined_decided','decided_mask_sha256'):
   assert bfull[panel,prefix+'::lower_median','ALL'][suffix]==bfull[panel,prefix+'::P2','ALL'][suffix]
bpairs=rows('b-completion-public-v2','MATCHED*.csv')
for r in bpairs:
 a,b=bfull[r['source_panel'],r['left'],'ALL'],bfull[r['source_panel'],r['right'],'ALL'];den=n(r,'common_decided')
 eq(r['left_wins'],a['combined_wins']);eq(r['right_wins'],b['combined_wins']);eq((Decimal(r['left_wins'])-Decimal(r['right_wins']))/den,r['accuracy_change'])
 gap=abs(n(r,'left_wins')-n(r,'right_wins'));dis=n(r,'side_disagreements');assert gap<=dis<=den and(dis-gap)%2==0
 if n(r,'common_numerical'):eq(num(a['numeric_MAE'])-num(b['numeric_MAE']),r['MAE_change'])
 if n(r,'common_law_events'):eq(num(a['law_Brier'])-num(b['law_Brier']),r['Brier_change'])
bins=rows('b-completion-public-v2','FIXED*.csv');bg=defaultdict(list)
for r in bins:
 bg[r['source_panel'],r['candidate_id']].append(r);eq(Decimal(r['count'])*Decimal(r['observed_Over']),round(Decimal(r['count'])*Decimal(r['observed_Over'])))
for(panel,candidate),rr in bg.items():
 eq(sum(n(r,'count')for r in rr),bfull[panel,candidate,'ALL']['law_events'])
 eq(sum(Decimal(r['count'])*Decimal(r['observed_Over'])for r in rr),bfull[panel,'ALWAYS_OVER','ALL']['combined_wins'])
cumulative=rows('c03-public-v1','CUMULATIVE*.csv');weekly=rows('c03-public-v1','WEEKLY*.csv');crows=cumulative+weekly
for r in crows:
 for side in('over','under','combined'):
  eq(n(r,side+'_wins')+n(r,side+'_losses'),r[side+'_decided']);rate(r[side+'_wins'],r[side+'_decided'],r[side+'_rate'])
 for f in('selected','wins','losses','decided'):eq(n(r,'over_'+f)+n(r,'under_'+f),n(r,'combined_'+f))
 eq(r['selected'],r['combined_selected']);eq(n(r,'selected')+n(r,'unavailable')+n(r,'abstained'),r['eligible'])
 eq(n(r,'combined_decided')+sum(n(r,k)for k in('unknown_participation','missing_actual','pending','DNP','push')),r['selected'])
 assert r['probabilities']=='N/A_SAVED_POINTS_ONLY'
 if n(r,'numerical_scored'):
  assert num(r['numerical_MAE'])**2<=num(r['numerical_MSE'])+Decimal('1e-10')
  if num(r['numerical_RMSE'])is not None:eq(float(num(r['numerical_MSE']))**.5,r['numerical_RMSE'])
 else:assert num(r['numerical_MAE'])is None
 assert set(json.loads(r['actual_retained_threshold_weeks']))<=set(range(1,6))
 assert set(json.loads(r['all_graded_weeks']))<=set(range(1,8))
cfull={(r['view'],r['source_panel'],r['procedure']):r for r in cumulative}
newids=sorted({r['procedure']for r in weekly});assert len(newids)==6
ccount=['eligible','selected','unavailable','abstained','unknown_participation','missing_actual','pending','DNP','push','over_selected','over_wins','over_losses','over_decided','under_selected','under_wins','under_losses','under_decided','combined_selected','combined_wins','combined_losses','combined_decided','numerical_scored']
for proc in newids:
 for view in('FULL_A733','FIXED_C667'):
  for panel in('ALL','ANNUAL_NAMED_NJ','SITE_RECORDED_DK_JURISDICTION_UNKNOWN'):
   total=cfull[view,panel,proc];parts=[r for r in weekly if(r['view'],r['source_panel'],r['procedure'])==(view,panel,proc)];assert len(parts)==7;combine(total,parts,ccount,'numerical_')
  combine(cfull[view,'ALL',proc],[cfull[view,p,proc]for p in('ANNUAL_NAMED_NJ','SITE_RECORDED_DK_JURISDICTION_UNKNOWN')],ccount,'numerical_')
 for row in(cfull['FULL_A733','ALL',proc],):eq(row['eligible'],733);eq(row['selected'],678);eq(row['unavailable'],55);eq(row['unknown_participation'],11);eq(row['combined_decided'],667)
cpairs=rows('c03-public-v1','MATCHED*.csv')
for r in cpairs:
 a,b=cfull[r['view'],r['source_panel'],r['left']],cfull[r['view'],r['source_panel'],r['right']]
 eq(r['left_wins'],a['combined_wins']);eq(r['right_wins'],b['combined_wins']);eq(n(r,'left_wins')-n(r,'right_wins'),r['win_change'])
 gap=abs(n(r,'left_wins')-n(r,'right_wins'));dis=n(r,'side_disagreements');assert gap<=dis<=n(r,'common_decided')and(dis-gap)%2==0
 if n(r,'common_numerical'):eq(num(a['numerical_MAE'])-num(b['numerical_MAE']),r['MAE_change'])
 else:assert num(r['MAE_change'])is None
# Bind A's exact consumed public B bytes to this owner's unchanged sources.
protocol=read(A/'B_COMPLETION_SCORING_GO_V2.json')
for r in protocol['B_forecast_refs']:assert sha(ROOT/r['path'])==r['sha256']and(ROOT/r['path']).stat().st_size==r['bytes']
receipt=dict(id='B-INDEPENDENT-A-JOIN-PUBLIC-ARITHMETIC-v1',A_commit=COMMIT,status='PASS_IN_PUBLIC_AGGREGATE_SCOPE',downloaded_files_verified=len(download),CSV_manifests_verified=len(table_files),checks=checks,largest_decimal_rounding_difference=str(largest),B_summary_rows=len(brows),B_matched_pair_rows=len(bpairs),B_reliability_bin_rows=len(bins),C_summary_rows=len(crows),C_matched_pair_rows=len(cpairs),B_exact_owned_forecast_packets_verified=len(protocol['B_forecast_refs']),source_files=table_files,source_receipts={p:sha(A/p)for p in('B_COMPLETION_OWNER_RECEIPT_V2.json','B_COMPLETION_SCORING_GO_V2.json','C03_RECEPTION_EXECUTION_RECEIPT_V1.json')},new_fits=0,new_inference=0,new_source_acquisition=0,new_NFL_observations=0,verdicts=dict(public_arithmetic='PASS',public_packet_identity_and_product_bindings='PASS_FOR_8_B_OWNED_FORECAST_PACKETS',private_join_identity_raw_line_grades_quote_clocks='UNKNOWN_NOT_IN_PUBLIC_EXPORT',independent_bootstrap_reproduction='UNKNOWN_NO_PRIVATE_CLUSTER_ROWS; no intervals rerun',original_issue_current_capture_consumer_or_C_admission='NOT_ESTABLISHED_BY_THIS_REVIEW'),limits=['External B verification is of public arithmetic and exact Bforecastbytes. Aauthor-separated rawDecimal/lawchecks are ownerreceipts, not private-row inspection byB.','AnnualW1-5 actualthresholds retain unverifiedquoteclocks; siteW6-7 isunqualified-offer diagnostic, noA W8rows.','C03 usespointoutputs only; localP2model labels are not BprobabilitypolicyP2.','Bmedian/P2 identicalsideviews and aliases are not independentlearners/observations; alloverlappingviews mustnotbepooled twice.','New48h F2/F3 procedures were not present in this oldR0-R3 join; source/mathreceipt cannotconfer their fifthofferweek.'])
dest=OUT/'A_JOIN_PUBLIC_ARITHMETIC_REVIEW_V1.json';assert not dest.exists();dest.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({k:v for k,v in receipt.items()if k not in('source_files','source_receipts')},indent=2))
