"""Aggregate capture metadata from saved bytes without decoding prediction/outcome values."""
import argparse,collections,datetime,gzip,hashlib,importlib.util,json,pathlib

ROOT=pathlib.Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('readonly_source',ROOT/'READ_ONLY_SOURCE_AUDIT.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
SAFE={'category','product','method_id','model_version','prediction_functional','procedure_version','horizon','issued_at','persistence_completed_at','first_prepared_at','kickoff_utc','kickoff','source_cutoff_utc','source_policy_sha256','valid_until_utc','game_id','season','week','source_timestamps_verified','forecast_source','direction','selected_at','key','model','schema_version','captured_at','code_commit','evidence_label','forecast_generated_at','execution_contract_sha256','input_sha256','engine_sha256','normalized_stats_cache','original_shadow_model','original_shadow_procedure','original_shadow_source','capture_schema','grading_version','packaged_at','prepared_at','registration_id','publication_review_sha256','canonical_board_sha256','board_contract_sha256','website_source_sha','state','policy_sha256','version','meaning','fallback','unavailable','top_n','categories','minimum_games','minimum_projected_ppr','minimum_score','minimum_snap_share','projection_line_ratio','tie_order'}
def props(t,a=0):return {k:(x,y)for k,x,y in helper.entries(t,a)}
def project(t,a=0):
    out={}
    for k,x,y in helper.entries(t,a):
        if k in SAFE and t[x] not in '{[':out[k]=json.loads(t[x:y])
        elif k in SAFE and t[x]=='[':out[k]=json.loads(t[x:y])
    return out
def sha(b):return hashlib.sha256(b).hexdigest()
def counter(rows,fields):
    group=collections.defaultdict(list)
    for row in rows:group[tuple(str(row.get(k,'UNSPECIFIED'))for k in fields)].append(row)
    out=[]
    for key,rs in sorted(group.items()):
        out.append({**dict(zip(fields,key)),'rows':len(rs),'unique_games':len({r.get('game_id')for r in rs if r.get('game_id')}),'first_kickoff':min([r.get('kickoff_utc',r.get('kickoff'))for r in rs if r.get('kickoff_utc',r.get('kickoff'))],default=None),'last_kickoff':max([r.get('kickoff_utc',r.get('kickoff'))for r in rs if r.get('kickoff_utc',r.get('kickoff'))],default=None)})
    return out
def clocks(rows):
    result={}
    for k in ['issued_at','persistence_completed_at','first_prepared_at','source_cutoff_utc','valid_until_utc','selected_at']:
        vs=[r[k]for r in rows if r.get(k)];result[k]={'nonnull':len(vs),'min':min(vs)if vs else None,'max':max(vs)if vs else None}
    return result
def write(name,data):
    p=ROOT/name
    if p.exists():raise ValueError('immutable metadata projection already exists')
    p.write_text(json.dumps(data,sort_keys=True,indent=2)+'\n')
def main(cache):
    at=datetime.datetime.now(datetime.timezone.utc);classic=gzip.decompress((cache/'classic-receipt.json.gz').read_bytes()).decode();root=props(classic);pa,pb=root['payload'];p=props(classic,pa);metadata=project(classic,pa)
    metadata['execution_contract']=project(classic,p['execution_contract'][0]);metadata['engine_files']=json.loads(classic[p['engine_files'][0]:p['engine_files'][1]])
    ca,cb=p['rows'];classicrows=[project(classic,a)for a,b in helper.elements(classic,ca)]
    excluded_n=len(list(helper.elements(classic,p['excluded_started_or_late_games'][0])))
    overlay=(cache/'payload.json').read_text();p=props(overlay);overlaymeta=project(overlay);oa,ob=p['rows'];overlayrows=[project(overlay,a)for a,b in helper.elements(overlay,oa)]
    fallback={k:json.loads(overlay[a:b])for k,a,b in helper.entries(overlay,p['fallback_counts'][0])}
    frozen_n=len(list(helper.elements(overlay,p['frozen_rows'][0])))
    def iso(x):return datetime.datetime.fromisoformat(x.replace('Z','+00:00'))
    def future(r):return iso(r.get('kickoff_utc',r.get('kickoff'))) > at
    classicfuture=[r for r in classicrows if future(r)];overlayfuture=[r for r in overlayrows if future(r)];overlayelapsed=[r for r in overlayrows if not future(r)]
    selected=(cache/'selected-payload.json').read_text();p=props(selected);selectedmeta=project(selected);policy_a=p['policy'][0];selectedmeta['policy']=project(selected,policy_a);selectedmeta['fallback_counts']={k:json.loads(selected[a:b])for k,a,b in helper.entries(selected,p['fallback_counts'][0])};picks=[]
    for side,a,b in helper.entries(selected,p['picks'][0]):
        for aa,bb in helper.elements(selected,a):
            row=project(selected,aa);row['side_bucket']=side;key=row.get('key');row['category']=key[-1]if isinstance(key,list)and key else 'KEY_NOT_LIST';picks.append(row)
    result={'schema':'owner-runtime-qualified-capture-metadata-v1','observed_at':at.isoformat(),'outcome_scalar_values_decoded_by_this_projection':False,'scope_incident':'Earlier unfiltered connector diff has possible scalar exposure; see ACQUISITION_SCOPE_INCIDENT.json. This projection adds no value decoding.','classic':{'metadata':metadata,'rows':len(classicrows),'future_rows':len(classicfuture),'future_games':len({r['game_id']for r in classicfuture}),'excluded_started_or_late_games_count':excluded_n,'first_future_kickoff':min(r['kickoff']for r in classicfuture),'by_category':counter(classicrows,['category']),'source_timestamps_verified_counts':dict(collections.Counter(str(r.get('source_timestamps_verified','MISSING'))for r in classicrows))},'adaptive':{'metadata':overlaymeta,'rows':len(overlayrows),'future_rows':len(overlayfuture),'future_games':len({r['game_id']for r in overlayfuture}),'elapsed_rows':len(overlayelapsed),'elapsed_games':len({r['game_id']for r in overlayelapsed}),'frozen_rows':frozen_n,'fallback_counts':fallback,'clock_ranges':clocks(overlayrows),'by_category_procedure_product_horizon':counter(overlayrows,['category','method_id','product','model_version','procedure_version','prediction_functional','horizon']),'future_by_category_procedure_product_horizon':counter(overlayfuture,['category','method_id','product','model_version','procedure_version','prediction_functional','horizon'])},'selected':{'metadata':selectedmeta,'rows':len(picks),'future_rows':sum(future(r)for r in picks),'clock_ranges':clocks(picks),'by_side_source_model_product':counter(picks,['side_bucket','forecast_source','model_version','product']),'by_category':counter(picks,['category'])},'source_hashes':{name:sha((cache/name).read_bytes())for name in ['classic-receipt.json.gz','payload.json','selected-payload.json']},'new_fits':0,'new_model_inference':0,'new_forecasts':0,'new_grades':0}
    write('QUALIFIED_CAPTURE_AND_SERVED_METADATA.json',result);print(json.dumps({'classic_rows':len(classicrows),'classic_future_games':result['classic']['future_games'],'adaptive_rows':len(overlayrows),'adaptive_future_rows':len(overlayfuture),'selected_rows':len(picks),'new_grades':0}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--cache',type=pathlib.Path,required=True);a=p.parse_args();main(a.cache)
