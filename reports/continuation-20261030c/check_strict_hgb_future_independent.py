"""Replay immutable strict-current future HGB inference, without fitting/labels."""
import gzip,hashlib,json,math,pickle,resource,sys,time
from collections import Counter,defaultdict
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2];HERE=ROOT/'reports/continuation-20261030c';sys.path.insert(0,str(HERE));sys.path.insert(0,str(ROOT))
from review_paths import companion_root,source_root
from check_season_scores_independent import load_truth,sha,close,COUNTS
from check_season_features_independent import OwnOnly
from check_defense_features_independent import compare,canonical,epoch,unzip
def verify():
 start,cpu=time.monotonic(),time.process_time();pub=HERE/'strict-hgb-future-v1';private=companion_root()/'strict-hgb-future-v1';p=json.loads((pub/'FROZEN_PROTOCOL.json').read_text());run=json.loads((pub/'RUN_RECEIPT.json').read_text());reg=json.loads((pub/'EXECUTION_REGISTRATION.json').read_text());assert run['protocol_sha256']==sha(pub/'FROZEN_PROTOCOL.json');assert reg['independent_prefit_sha256']==sha(HERE/'STRICT_HGB_FUTURE_PREFIT_INDEPENDENT_REVIEW.json');assert reg['actual_started_at']<run['actual_completed_at'];assert sha(ROOT/'nfl_v2/strict_hgb_future.py')==p['code_sha256'];allrows,lookup,games=load_truth(source_root(),p,2026);rows=[r for r in allrows if r['season']==2026];own=OwnOnly(rows);asof=epoch(p['fixed_asof_utc']);c=Counter();features={};modeln=0;views={};actualmaxweek=0
 for name,h in p['helper_sha256'].items():assert sha(ROOT/'nfl_v2'/name)==h
 finalpath=private/run['packet']['bundle_name'];assert sha(finalpath)==run['packet']['sha256'];final=unzip(finalpath)['rows'];assert len(final)==run['output_views']==3193
 for r in final:
  assert r['actual']is None and r['actual_status']=='PENDING_FUTURE';k=r['query_id'],r['product_id'];assert k not in views;views[k]=r
 from threadpoolctl import threadpool_limits
 with threadpool_limits(limits=2):
  for ff in sorted(pub.glob('*-FIT.json')):
   fit=json.loads(ff.read_text());target=fit['target'];objective=fit['objective'];roles=set(p['source_role_contract']['primary'][target])|set(p['source_role_contract']['extended'].get(target,[]));train=[r for r in rows if r['position']in roles and r['values'][target]is not None and r['available']<asof];assert fit['feature_floor']==2026 and fit['fit_cutoff_utc']==p['fixed_asof_utc'];assert fit['training_n']==len(train)and fit['training_seasons']==[2026];assert fit['training_membership_sha256']==hashlib.sha256(canonical([(r['game_id'],r['player_id'])for r in train])).hexdigest();assert fit['latest_training_label_available']==max(r['available']for r in train)
   maxima=[]
   for r in train:
    _,m=own.own(r['player_id'],r['position'],target,r['kickoff'],2026);assert m is None or m<r['kickoff'];maxima.extend([]if m is None else[m]);actualmaxweek=max(actualmaxweek,r['week']);c['source_training_row_prefixes']+=1
   close(fit['latest_training_feature_available'],max(maxima,default=None));c['exact_strict_training_membership_and_clock_receipts']+=1;fd=fit['query_features'];path=private/fd['bundle_name'];assert sha(path)==fd['sha256'];entries=unzip(path)
   if target not in features:
    for e in entries:
     q=e['query'];v,m=own.own(q['player_id'],q['position'],target,asof,2026);compare(e['features'],v,c);close(e['latest_feature_available'],m);assert q['actual']is None;c['independent_current_only_query_prefixes']+=1
    features[target]=entries
   md=fit['model'];path=private/md['bundle_name'];assert sha(path)==md['sha256'];model=pickle.loads(gzip.decompress(path.read_bytes()));modeln+=1;params=model.get_params()
   for k,v in p['recipe']['HGB'].items():assert params[k]==v
   assert model.n_iter_==64;c['frozen_model_hash_and_parameter_checks']+=1;fr=json.loads((pub/(fit['slot']+'-FORECAST.json')).read_text());cp=private/fr['packet']['bundle_name'];assert sha(cp)==fr['packet']['sha256'];chunk=unzip(cp)['rows'];assert len(chunk)==len(entries);matrix=np.asarray([[math.nan if v is None else v for v in e['features']]for e in entries]);good=[i for i,e in enumerate(entries)if not e['query'].get('blocked_reason')and e['query']['position']in('QB','RB','WR','TE')];predicted=model.predict_proba(matrix[good])[:,list(model.classes_).index(1.)]if target=='anytime_td'else model.predict(matrix[good]);predictions=dict(zip(good,predicted))
   for i,(e,r)in enumerate(zip(entries,chunk)):
    assert r==views[r['query_id'],r['product_id']]and r['product_id']==objective and r['actual']is None;assert r['feature_cutoff_utc']==p['fixed_asof_utc'];assert epoch(r['actual_generated_at'])>=epoch(fit['actual_fit_completed_at'])and epoch(fr['actual_persistence_completed_at'])>=epoch(r['actual_generated_at'])
    if i not in predictions:assert r['prediction']is None and r['status']=='ABSTAIN';c['blocked_abstention_views']+=1;continue
    value=float(predictions[i]);value=max(0.,value)if target in COUNTS else value;close(r['prediction'],value);assert r['fallback']=='none'and r['status']=='STAGED_RESEARCH_SHADOW';assert epoch(r['issued_at_utc'])<epoch(r['owner_input_cutoff_utc']);assert epoch(fr['actual_persistence_completed_at'])<epoch(r['owner_input_cutoff_utc']);assert epoch(run['actual_completed_at'])<epoch(r['owner_input_cutoff_utc']);close(r['actual_horizon_seconds'],epoch(r['kickoff_utc'])-epoch(r['issued_at_utc']));assert r['latest_feature_available']is None or r['latest_feature_available']<asof;c['independently_replayed_issued_views']+=1
 assert c['independently_replayed_issued_views']==run['issued']==3183 and c['blocked_abstention_views']==run['abstained']==10;assert modeln==run['actual_fit_calls']==run['retained_models']==21 and run['failed_fits']==0 and run['score_views']==0;grid=json.loads((pub/'GRID_STATUS.json').read_text());assert len(grid)==21 and all(r['state']=='FITTED_RETAINED'and r['forecast_state']=='PERSISTED'for r in grid)
 return dict(state='PASS_STRICT_FUTURE_SOURCE_PREFIX_MODEL_INFERENCE_AND_REAL_CAPTURE_REPLAY',protocol_sha256=sha(pub/'FROZEN_PROTOCOL.json'),source_packet_sha256=sha(finalpath),source_receipt_sha256=sha(pub/'RUN_RECEIPT.json'),checks=dict(c),source_training_seasons=[2026],maximum_eligible_source_training_week=actualmaxweek,actual_completed_at=run['actual_completed_at'],query_cells=1795,query_games=13,issued=3183,abstentions=10,score_views=0,comparison_limit=p['comparison_limit'],durability='Localimmutablecaptureverified; approvedoffhostrestorationmustbequalifiedseparately.',resource=dict(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024),new_fits=0,new_forecasts=0,current2026_week8_outcomes_read=0)
if __name__=='__main__':
 r=verify();(HERE/'STRICT_HGB_FUTURE_INDEPENDENT_REVIEW.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
