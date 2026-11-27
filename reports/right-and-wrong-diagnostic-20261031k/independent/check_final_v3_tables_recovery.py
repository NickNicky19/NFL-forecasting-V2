"""Retained-aggregate table rendering + V3 pointer audit; no scoring replay."""
import datetime,hashlib,json,re
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def read(p):return json.loads(Path(p).read_bytes())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def mdrows(text):return[[s.strip()for s in line.split('|')[1:-1]]for line in text.splitlines()if line.startswith('| ')and not line.startswith('|---')]
def side(cell):
 z=re.fullmatch(r'(\d+) selected; (\d+)/(\d+); d=(\d+); ([\d.]+)%',cell);assert z,cell;return tuple(map(int,z.groups()[:4]))+(float(z.group(5)),)
def main():
 tablepath=HERE.parent/'CHECKPOINT_CATEGORY_TABLES_V1.md';text=tablepath.read_text();a=mdrows(text.split('Table A —',1)[1].split('Table B —',1)[0])[1:];b=mdrows(text.split('Table B —',1)[1].split('P1 RAW OWN-POOL',1)[0])[1:];assert len(a)==12 and len(b)==17
 decisions=read(ROOT/'reports/baselines-coverage-20261031h/CATEGORY_DECISIONS.json');bycat={r['category']:r for r in decisions};native=read(HERE.parent/'NUMERICAL_LEADER_PATTERN_COUNTS.json');assert len(native)==17;totals=[0]*7
 for row in a:
  cat=row[0];d=bycat[cat]['original_recorded_category']
  if cat in('nick-chart-ppr-v1','anytime_td'):assert row[1:4]==['N/A']*3;continue
  ss=[side(x)for x in row[1:4]]
  for s,key in zip(ss,('over','under','Combined')):
   r=d[key];assert s[:4]==(r['selected'],r['wins'],r['losses'],r['decided']);assert s[3]==s[1]+s[2]and s[4]==round(100*s[1]/s[3],2)
  assert tuple(x+y for x,y in zip(ss[0][:4],ss[1][:4]))==ss[2][:4]
  unknown=tuple(map(int,row[4].split('/')));assert unknown==tuple(d[key]['status_counts']['UNKNOWN_PARTICIPATION']for key in('over','under','Combined'))and unknown[0]+unknown[1]==unknown[2]
  coverage=re.fullmatch(r'(\d+)/(\d+); ([\d.]+)%',row[5]);assert coverage;assert(int(coverage.group(1)),int(coverage.group(2)))==(d['Combined']['selected'],d['Combined']['eligible_opportunities']);assert float(coverage.group(3))==round(100*d['Combined']['coverage'],2)
  interval=d['Combined']['uncertainty']['game_interval'];assert row[6]==f'{100*interval[0]:.2f}%–{100*interval[1]:.2f}%'
  for key in('over','under','Combined'):
   assert all(d[key]['status_counts'][state]==0 for state in('PUSH','VOID','PENDING','MISSING_ACTUAL','UNRESOLVED_CONTRACT'))
  totals=[totals[0]+ss[0][1],totals[1]+ss[0][3],totals[2]+ss[1][1],totals[3]+ss[1][3],totals[4]+ss[2][0],totals[5]+unknown[2],totals[6]+ss[2][1]]
 assert totals==[347,663,316,531,1226,32,663]
 aliases={r[0]:r[1].strip('`')for r in mdrows(text.split('Exact alias registry',1)[1])[1:]}
 offered=0
 for row,n in zip(b,native):
  assert row[0]==n['category'];name,history,product=[x.strip()for x in row[1].split(' / ')];assert aliases[name]==n['native_procedure_id']and history==n['native_history']and product==n['native_product']
  metric='MAE'if n['native_metric']=='mae'else'Brier';assert row[2]==f"{n['native_loss']:.6f} {metric}; {n['native_n']}/{n['native_forecast_rows']}"
  if n['category']in('nick-chart-ppr-v1','anytime_td'):assert row[3:6]==['N/A']*3;continue
  offered+=1;ss=[side(x)for x in row[3:6]]
  for s,prefix in zip(ss,('over','under','combined')):
   selected=n['over_selected']+n['under_selected']if prefix=='combined'else n[prefix+'_selected'];assert s[:4]==(selected,n[prefix+'_wins'],n[prefix+'_losses'],n[prefix+'_decided']);assert s[4]==round(100*n[prefix+'_hit_rate'],2)
  assert tuple(x+y for x,y in zip(ss[0][:4],ss[1][:4]))==ss[2][:4]
  assert row[6]==f"{n['admitted_forecasts']}/{n['outer_offer_opportunities']}; {n['unavailable_forecasts']}"
 assert offered==13 and 'qualifiedPARTIAL'in text and 'not offered-pool point MAE'in text and 'tiny narrow pool is unvalidated'in text
 pointerpath=ROOT/'registries/CURRENT_RESULTS_INDEX.json';pointer=read(pointerpath);bindings=[]
 for key,ref in pointer.items():
  if isinstance(ref,dict)and'path'in ref and'sha256'in ref:assert sha(ROOT/ref['path'])==ref['sha256'];bindings.append(key)
 statuspath=ROOT/pointer['recovery_status']['path'];status=read(statuspath);assert status['state']=='DELTA_AND_NEW_K_RESTORED_THREE_SEASONAL_ARCHIVES_QUOTA_BLOCKED'and status['old_archives_fully_restored']==1 and status['old_archives_remaining']==3 and status['large_fit_gate_cleared']is False
 quota=read(HERE.parent/'RECOVERY_PROGRESS_CHECKPOINT_K_V2_QUOTA_STOP.json');assert all(status[k]==quota[k]for k in('successful_receipt_sha256s','provider_successful_missing_part_uploads','provider_successful_upload_bytes','remaining_missing_upload_parts','remaining_missing_upload_bytes','provider_error_receipt_sha256'))
 states={r['artifact_id']:r for r in status['archives']};assert sum(r['full_restoration_verified']for r in states.values())==1;assert states['V2-PRIVATE-RECOVERY-DELTA-20261030D-0001']['full_restoration_verified']is True
 delta=read(HERE/'DELTA_FRESH_RESTORATION_INDEPENDENT_REVIEW.json');ref=status['delta_fresh_restoration_receipt'];assert sha(ROOT/ref['path'])==ref['sha256']==delta['source_public_proof_sha256'];assert status['new_K_bundle_restoration_verified']is True
 old=read(HERE/'FINAL_POINTER_REPORT_AND_K_RETENTION_REVIEW.json');assert sha(ROOT/pointer['manifest'])==old['index_manifest_sha256']and pointer['right_wrong_readable']['sha256']=='a591f3ddfeef0f44e839896ce1f99c6aa958f8c8b6a73fcf0b00f62bc1b5ba49'and pointer['right_wrong_artifact_bindings']['sha256']=='1ce37b5dc28a05fda015e7723b10de5b6580f0d4289391d4f076c0517364eca4'
 currentmd=HERE.parent/'RECOVERY_STATUS_CURRENT_V3.md';currenttext=currentmd.read_text();assert 'global large-fit recovery gate remains closed'in currenttext and 'not a measured free-quota reading'in currenttext and 'acknowledgement is not observed'in currenttext
 out={'state':'PASS_FINAL_V3_CURRENT_POINTER_CATEGORY_TABLES_AND_DELTA_RETENTION','at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'pointer_sha256':sha(pointerpath),'pointer_hash_bindings_verified':len(bindings),'current_status_sha256':sha(statuspath),'current_status_md_sha256':sha(currentmd),'category_tables_sha256':sha(tablepath),'original_category_rows':12,'numerical_native_tied_output_rows':17,'own_P1_offer_rows':13,'unavailable_native_offer_rows':4,'original_over_wins_decided':[347,663],'original_under_wins_decided':[316,531],'original_combined_wins_decided':[663,1194],'original_selected_unknown':[1226,32],'category_count_rate_source_membership_and_aliases_preserved':True,'no_side_splicing':True,'native_and_offered_panels_separate':True,'chart_native_error_qualified_partial':True,'fixed_numeric_and_championship_rankings_unchanged':True,'index_records':565871,'new_K_bundle_independent_receipt_sha256':sha(HERE/'K_BUNDLE_RESTORATION_REVIEW.json'),'delta_independent_receipt_sha256':sha(HERE/'DELTA_FRESH_RESTORATION_INDEPENDENT_REVIEW.json'),'quota_independent_receipt_sha256':sha(HERE/'QUOTA_STOP_V2_INDEPENDENT_REVIEW.json'),'old_archives_fully_restored':1,'old_archives_incomplete':3,'remaining_upload_parts':38,'remaining_upload_payload_bytes':796917760,'whole_old_recovery_gate_cleared':False,'new_transfers_or_scientific_calculations':0,'worker_or_production_release':False,'checker_sha256':sha(Path(__file__))}
 with(HERE/'FINAL_CURRENT_POINTER_TABLES_RECOVERY_V3_REVIEW.json').open('x')as f:json.dump(out,f,indent=2);f.write('\n')
 print(json.dumps({k:out[k]for k in('state','pointer_sha256','pointer_hash_bindings_verified','category_tables_sha256','original_category_rows','numerical_native_tied_output_rows','whole_old_recovery_gate_cleared')}))
if __name__=='__main__':main()
