"""Independently join and score retained Week7 reference; no fits/acquisition."""
import csv,gzip,hashlib,json,math,resource,sys,time
from collections import Counter,defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];HERE=ROOT/'reports/continuation-20261030c';sys.path.insert(0,str(HERE))
from review_paths import companion_root,source_root
from check_season_scores_independent import load_truth,sha,close
from check_defense_features_independent import canonical,epoch
from check_shared_subgroups_independent import packet
def metrics(rs,prediction='prediction'):
 errors=[r[prediction]-r['actual']for r in rs];a=sorted(map(abs,errors));n=len(a);quant=lambda p:(lambda x:a[math.floor(x)]+(a[math.ceil(x)]-a[math.floor(x)])*(x-math.floor(x)))((n-1)*p);mse=math.fsum(e*e for e in errors)/n
 return dict(n=n,mae=math.fsum(a)/n,mse=mse,rmse=math.sqrt(mse),bias=math.fsum(errors)/n,p90_abs=quant(.9),p95_abs=quant(.95),max_abs=a[-1],exact_rate=sum(e==0 for e in errors)/n,**{f'abs_{op}_{v}':sum(z<v if op=='lt'else z<=v for z in a)/n for op in('lt','le')for v in(1,5,10)})
def verify(source,private):
 start,cpu=time.monotonic(),time.process_time();pub=HERE/'server-retained-R0-v1';p=json.loads((HERE/'SERVER_R0_REFERENCE_PROTOCOL.json').read_text());run=json.loads((pub/'RUN_RECEIPT.json').read_text());proof=json.loads((HERE/'SERVER_R0_PROOF_INDEPENDENT_READBACK.json').read_text());assert proof['run']['created_at']==p['proven_retained_by_utc']and proof['run']['head_sha']==p['server_source_head'];assert proof['source_blob']['sha']==p['source_blob']['sha']and proof['source_blob']['size']==47600 and not proof['tree_truncated'];assert proof['tree_sha']==proof['run']['head_tree'];qprotocol=json.loads((ROOT/'reports/continuation-20261030/distribution-wave-v2/FROZEN_PROTOCOL.json').read_text());raw,lookup,games=load_truth(source,qprotocol,2026);c=Counter();bridge=defaultdict(set)
 assert sha(source/'roster-week8-identity-2026.csv.gz')==run['identity_bridge_sha256']
 with gzip.open(source/'roster-week8-identity-2026.csv.gz','rt',newline='')as f:
  for r in csv.DictReader(f):
   if r['season']=='2026'and int(r['week'])<=7 and r['sleeper_id']and r['gsis_id']:bridge[r['sleeper_id']].add(r['gsis_id'])
 assert all(len(v)==1 for v in bridge.values());bridge={k:next(iter(v))for k,v in bridge.items()};clock=epoch(p['proven_retained_by_utc']);byespn={}
 # ESPN identity is metadata only; actuallabels came from the capped loader.
 with(source/'games.csv').open()as f:
  for r in csv.DictReader(f):
   if r['game_type']=='REG'and r['season']=='2026'and r['week']=='7':byespn[str(r['espn'])]=r['game_id']
 path=private.parent/'website-reference-probe-v1'/Path(p['source_blob']['path']).name;b=path.read_bytes();assert len(b)==p['source_blob']['size']and sha(path)==p['gzip_sha256'];assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==p['source_blob']['sha'];body=json.loads(gzip.decompress(b));payload=body['payload'];assert hashlib.sha256(canonical(payload)).hexdigest()==p['payload_sha256'];savedpath=private/'RETAINED_AND_MATCHED.json.gz';assert sha(savedpath)==run['private_rows_sha256'];saved=json.loads(gzip.decompress(savedpath.read_bytes()));reference={};excluded=set();seen=set()
 for r in payload['rows']:
  assert(r['season'],r['week'])==(2026,7);game=byespn[str(r['game_id'])];g=games[game];assert epoch(r['kickoff'])==g['kickoff']
  if g['kickoff']-5400<=clock:excluded.add(game);continue
  player=bridge.get(str(r['player_id']));a=lookup.get((game,player));target=r['category'];key=(game,player,target)
  if player is not None:assert key not in seen
  seen.add(key);population='primary'if r['position']in qprotocol['source_role_contract']['primary'].get(target,[])else'extended'
  for product,field in(('website_point','adjusted_projection'),('provider_point','raw_projection')):
   pred=r.get(field);status='TARGET_CONTRACT_NOT_COMPARABLE'if target not in('pass_yd','pass_td','pass_cmp','pass_att','pass_int','rush_yd','rush_att','rec','rec_yd','rush_rec_yd','anytime_td')else'UNLINKED_ID'if player is None else'APPEARANCE_UNKNOWN'if a is None or all(v is None for t,v in a['values'].items()if t!='nick-chart-ppr-v1')else'POSITION_MISMATCH'if a['position']!=r['position']else'SUPPORTED'
   if status=='SUPPORTED'and not(isinstance(pred,(int,float))and math.isfinite(pred)):status='EXPLICIT_FORECAST_UNAVAILABLE'
   y=a['values'][target]if status=='SUPPORTED'else None
   if status=='SUPPORTED'and y is None:status='MISSING_ACTUAL'
   reference[game,player,target,product]=dict(game_id=game,player_id=player,target=target,population=population,position=r['position'],product_id=product,prediction=pred,actual=y,status=status,recorded_capture=payload['captured_at'],server_retained_by=p['proven_retained_by_utc'])
 assert len(reference)==len(saved['rows'])==run['retained_views']
 for r in saved['rows']:assert reference[r['game_id'],r['player_id'],r['target'],r['product_id']]==r;c['original_forecast_identity_value_status_joins']+=1
 assert sorted(excluded)==run['excluded_unproven_games']==['2026_07_NE_CHI'];assert len({r['game_id']for r in saved['rows']})==run['eligible_games']==13
 top=ROOT/'reports/continuation-20261030b/TOP5_BY_CATEGORY_PRODUCT.json';assert sha(top)==run['fixed_V2_choices_sha256'];leaders={r['target']:r for r in json.loads(top.read_text())if r['rank']==1 and r['ranking_product']=='display_point'};candidates={};bindings=[]
 def admit(r,procedure=None):
  if str(r.get('season'))!='2026'or str(r.get('week'))!='7':return
  lead=leaders.get(r['target']);prod=r.get('product_id',r.get('objective',r.get('product')));proc=procedure or r.get('procedure_id')
  if not lead or proc!=lead['procedure_id']or prod!=lead['product']or r['history_regime']!=lead['history_regime']or r['prediction']in('',None):return
  if r['actual']in('',None)and not proc.startswith('v2-c02-'):return
  k=r['game_id'],r['player_id'],r['target'],r['population'];assert k not in candidates;candidates[k]=dict(prediction=float(r['prediction']),actual=None if r['actual']in('',None)else float(r['actual']),fallback=r.get('fallback'))
 base=private.parent
 for path in sorted((base/'hgb-history-v1/prediction-chunks').glob('W07-*.json.gz')):
  bindings.append(dict(source_id='hgb-W07-'+path.name,sha256=sha(path)))
  for r in json.loads(gzip.decompress(path.read_bytes()))['rows']:admit(r,'hgb-direct-history-controls-v1:'+r['objective'])
 for name in('distribution-wave-v2/all-predictions.csv.gz','empirical-history-diagnostic-v1/predictions.csv.gz'):
  path=base/name;bindings.append(dict(source_id=name,sha256=sha(path)))
  with gzip.open(path,'rt',newline='')as f:
   for r in csv.DictReader(f):admit(r,'empirical-player-history-control-v1'if name.startswith('empirical')else None)
 path=base/'ordered-information-ablation-v1/ALL_PREDICTIONS.json.gz';bindings.append(dict(source_id='c02-original-historical-packet',sha256=sha(path)))
 for r in packet(path):admit(r)
 for r in saved['candidates']:
  k=tuple(r['key']);assert candidates[k]['prediction']==float(r['prediction']);close(candidates[k]['actual'],r['actual']);c['frozen_leader_source_candidate_joins']+=1
 groups=defaultdict(list)
 for r in saved['rows']:
  if r['target']in('pass_yd','pass_td','pass_cmp','pass_att','pass_int','rush_yd','rush_att','rec','rec_yd','rush_rec_yd'):groups[r['target'],r['population'],r['product_id']].append(r)
 score_index={};examples=[]
 for s in json.loads((pub/'SCORES.json').read_text()):
  reference_product=s['comparison']['comparator_product_id']if 'comparison'in s else s['product_id'];score_index[s['target'],s['population'],reference_product,'candidate'if'comparison'in s else'reference']=s
 for dims,rs in groups.items():
  scored=[r for r in rs if r['status']=='SUPPORTED']
  if not scored:continue
  s=score_index[*dims,'reference'];expected=metrics(scored)
  for k,v in expected.items():close(s[k],v);c['independent_reference_metric_fields']+=1
  assert s['forecast_rows']==len(rs)
  paired=[dict(r,candidate_prediction=candidates[r['game_id'],r['player_id'],r['target'],r['population']]['prediction'])for r in scored if(r['game_id'],r['player_id'],r['target'],r['population'])in candidates];cs=score_index[*dims,'candidate'];am,bm=metrics(paired,'candidate_prediction'),metrics(paired);membership=hashlib.sha256(canonical(sorted((r['game_id'],r['player_id'],r['target'],r['population'])for r in paired))).hexdigest();assert membership==cs['comparison']['membership_sha256'];assert len(paired)==cs['comparison']['paired_n'];close(cs['comparison']['candidate_error'],am['mae']);close(cs['comparison']['comparator_error'],bm['mae'])
  for k,v in am.items():close(cs[k],v);c['independent_candidate_metric_fields']+=1
  for d in json.loads((pub/'PAIRED_COMPARISONS.json').read_text()):
   if(d['target'],d['population'],d['reference_product'])==dims:close(d['delta_mae'],am['mae']-bm['mae']);close(d['relative_error_change'],(am['mae']-bm['mae'])/bm['mae']if bm['mae']else None);c['paired_native_deltas_and_zero_denominator_guards']+=1
  if dims[2]=='website_point':examples.append(dict(target=dims[0],n=len(paired),reference_mae=bm['mae'],candidate_mae=am['mae'],delta_mae=am['mae']-bm['mae']))
 return dict(state='PASS_INDEPENDENT_SERVER_RETENTION_BOUND_AND_SAVED_ROW_REFERENCE_REPLAY',protocol_sha256=sha(HERE/'SERVER_R0_REFERENCE_PROTOCOL.json'),source_score_sha256=sha(pub/'SCORES.json'),checks=dict(c),eligible_games=13,reference_views=len(reference),supported_views=sum(r['status']=='SUPPORTED'for r in reference.values()),score_views=len(score_index),candidate_source_bindings=bindings,website_reference_examples=examples,limitations='ServercreatedrunheadandexactGittree/blobprovebytesretainedbyOct23 17:49:53. EarlierinternalOct22clock/providerinputvintageunverified. Differenthorizon/information, exposedfixedV2choices; nottodaysselectedwebsite, no samecutoffimprovementorROIclaim. Oneweekinsufficientclusters. fptsnotchart; unavailableTDprobabilitiesnotinvented.',resource=dict(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024),new_fits=0,new_forecasts=0,current2026_week8_outcomes_read=0)
if __name__=='__main__':
 r=verify(source_root(),companion_root()/'server-retained-R0-v1');(HERE/'SERVER_R0_INDEPENDENT_REVIEW.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items()if k!='candidate_source_bindings'}))
