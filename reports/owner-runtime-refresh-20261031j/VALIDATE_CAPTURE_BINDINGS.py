"""Metadata validation, target coverage and immutable selection-version overlap only."""
import argparse,collections,datetime,gzip,hashlib,importlib.util,json,pathlib,urllib.request
ROOT=pathlib.Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('jhelper',ROOT/'READ_ONLY_SOURCE_AUDIT.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def sha(b):return hashlib.sha256(b).hexdigest()
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def props(t,a=0):return {k:(a,b)for k,a,b in m.entries(t,a)}
def scalar(t,p,k):a,b=p[k];return json.loads(t[a:b])
def selections(t):
 p=props(t);out=[]
 for side,a,b in m.entries(t,p['picks'][0]):
  for aa,bb in m.elements(t,a):
   r=props(t,aa);out.append({'identity':tuple(scalar(t,r,k)for k in ['game_id','player_id','key']),'line_raw':t[r['line'][0]:r['line'][1]],'direction':scalar(t,r,'direction'),'side_bucket':side,'category':scalar(t,r,'key'),'model_version':scalar(t,r,'model_version'),'forecast_source':scalar(t,r,'forecast_source'),'selected_at':scalar(t,r,'selected_at'),'kickoff':scalar(t,r,'kickoff_utc'),'line_from':scalar(t,r,'line_from'),'all_required_present':all(k in r and t[r[k][0]:r[k][1]] not in ['null','""']for k in ['game_id','player_id','key','line','line_from','direction','selected_at','kickoff_utc'])})
 return out
def main(cache):
 b=(cache/'classic-receipt.json.gz').read_bytes();t=gzip.decompress(b).decode();top=props(t);pa,pb=top['payload'];p=props(t,pa);payload_hash=scalar(t,top,'payload_sha256');contract_hash=scalar(t,p,'execution_contract_sha256');input_hash=scalar(t,p,'input_sha256');mode=scalar(t,p,'mode')
 identity=sha(canonical(dict(data=input_hash,execution=contract_hash,mode=mode)))
 selected=(cache/'selected-payload.json').read_text();rows=selections(selected);keys=[r['identity']for r in rows];contracts=[(*r['identity'],r['line_raw'])for r in rows]
 result={'schema':'owner-runtime-source-binding-and-capture-validation-v1','observed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'classic':{'gzip_byte_sha256':sha(b),'payload_declared_sha256':payload_hash,'payload_raw_canonical_sha256':sha(t[pa:pb].encode()),'payload_hash_equal':payload_hash==sha(t[pa:pb].encode()),'execution_contract_hash_equal':contract_hash==sha(t[p['execution_contract'][0]:p['execution_contract'][1]].encode()),'capture_identity_computed':identity,'capture_identity_path_stem':'fb080a82123f6641ca2b9bae217ecac25b56196cfced64bd4b3e0698e04da575','capture_identity_equal':identity=='fb080a82123f6641ca2b9bae217ecac25b56196cfced64bd4b3e0698e04da575'},'selected':{'classification':'ORIGINAL_RECORDED_PLAYER_OFFER_DIRECTION_SELECTION_VERSION; sportsbook settlement and actual quote-time executability unestablished','strategy':'Owner selected-projection-gap-classic-v1; top12perSIDE acrosseligibleplayeroffers,24combined; not our research P2probabilitydirection rule','records':len(rows),'over_records':sum(r['side_bucket']=='over'for r in rows),'under_records':sum(r['side_bucket']=='under'for r in rows),'all_required_identity_line_direction_clocks_present':all(r['all_required_present']for r in rows),'unique_player_offer_identity':len(set(keys)),'unique_player_offer_line_contracts':len(set(contracts)),'duplicate_same_contract_count':len(contracts)-len(set(contracts)),'all_selected_before_kickoff':all(datetime.datetime.fromisoformat(r['selected_at'].replace('Z','+00:00'))<datetime.datetime.fromisoformat(r['kickoff'].replace('Z','+00:00'))for r in rows),'side_bucket_matches_recorded_direction':all(r['side_bucket']==r['direction']for r in rows),'by_category_side':dict(collections.Counter(r['category']+'|'+r['side_bucket']for r in rows)),'line_source_counts':dict(collections.Counter(r['line_from']for r in rows)),'points_or_prices_not_decoded':True}}
 # Exact earlier public version, never substituted for missing historical odds.
 oldhead='1ec93e068a91abd51c990937d1019e4a831694b4';base=f'https://raw.githubusercontent.com/NickNicky19/nicks-expert-nfl-picks/{oldhead}/output/data/'
 def get(url,name):
  with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'NFL-V2-readonly-owner-runtime-audit'}),timeout=45)as r:body=r.read(131073)
  if len(body)>131072:raise ValueError('old selected version bound')
  (cache/name).write_bytes(body);return body
 oldpointer=get(base+'weekly-selected-rankings.json','previous-selected-pointer.json');op=json.loads(oldpointer);oldbody=get(base+op['path'],'previous-selected-payload.json');oldrows=selections(oldbody.decode());oldmap={(*r['identity'],r['line_raw']):r for r in oldrows};newmap={(*r['identity'],r['line_raw']):r for r in rows};common=oldmap.keys()&newmap.keys()
 result['selection_version_overlap']={'old_commit':oldhead,'old_pointer_sha256':sha(oldpointer),'old_payload_sha256':sha(oldbody),'old_payload_declared_sha256':op['sha256'],'old_payload_hash_equal':sha(oldbody)==op['sha256'],'old_rows':len(oldrows),'new_rows':len(rows),'same_player_category_line_contracts':len(common),'same_contract_same_direction':sum(oldmap[k]['direction']==newmap[k]['direction']for k in common),'same_contract_direction_changes':sum(oldmap[k]['direction']!=newmap[k]['direction']for k in common),'new_only_contracts':len(newmap.keys()-oldmap.keys()),'old_only_contracts':len(oldmap.keys()-newmap.keys()),'interpretation':'New persistence/version is not a new independentNFLsample. Preserve both immutable versions; grading/selection-assignment rule not altered here.','new_private_cache_bytes':len(oldpointer)+len(oldbody)}
 path=ROOT/'CAPTURE_VALIDATION_AND_SELECTION_OVERLAP.json'
 if path.exists():raise ValueError('preserve existing validation')
 path.write_text(json.dumps(result,sort_keys=True,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--cache',type=pathlib.Path,required=True);a=p.parse_args();main(a.cache)
