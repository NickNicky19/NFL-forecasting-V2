"""Exact-source byte readback and lexical metadata projection; no outcome scoring."""
import argparse,collections,datetime,gzip,hashlib,json,pathlib,resource,time,urllib.request

ROOT=pathlib.Path(__file__).resolve().parent
CACHE=None
HEAD='305dacad91d593485c94bd9838ccf2d2464d9653'
BASE='https://nicknicky19.github.io/nicks-expert-nfl-picks/'
RAW=f'https://raw.githubusercontent.com/NickNicky19/nicks-expert-nfl-picks/{HEAD}/'

def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def digest(b):return hashlib.sha256(b).hexdigest()
def write(name,x):
    p=ROOT/name
    if p.exists():raise ValueError('preserve existing receipt:'+name)
    p.write_text(json.dumps(x,sort_keys=True,indent=2)+'\n')
def ws(t,i):
    while i<len(t) and t[i].isspace():i+=1
    return i
def string_end(t,i):
    if t[i]!='"':raise ValueError('expected string')
    i+=1
    while i<len(t):
        if t[i]=='\\':i+=2
        elif t[i]=='"':return i+1
        else:i+=1
    raise ValueError('unterminated string')
def value_end(t,i):
    i=ws(t,i)
    if t[i]=='"':return string_end(t,i)
    if t[i] in '[{':
        close='}' if t[i]=='{' else ']';i+=1
        while True:
            i=ws(t,i)
            if t[i]==close:return i+1
            if t[i] in ',:':i+=1;continue
            i=value_end(t,i)
    j=i
    while j<len(t) and t[j] not in ',]} \r\n\t':j+=1
    return j
def entries(t,start=0):
    i=ws(t,start)
    if t[i]!='{':return
    i+=1
    while True:
        i=ws(t,i)
        if t[i]=='}':return
        end=string_end(t,i);key=json.loads(t[i:end]);i=ws(t,end)
        if t[i]!=':':raise ValueError('missing colon')
        start=ws(t,i+1);end=value_end(t,start);yield key,start,end;i=ws(t,end)
        if t[i]==',':i+=1
        elif t[i]!='}':raise ValueError('missing separator')
def elements(t,start):
    i=ws(t,start)
    if t[i]!='[':return
    i+=1
    while True:
        i=ws(t,i)
        if t[i]==']':return
        end=value_end(t,i);yield i,end;i=ws(t,end)
        if t[i]==',':i+=1
        elif t[i]!=']':raise ValueError('missing array separator')

SAFE={'schema_version','schema','state','mode','model','procedure_id','policy_version','version','source_commit','source_sha','source_head','website_source_sha','issued_at','captured_at','first_captured_at','completed_at','published_at','generated_at','created_at','inferred_at','persisted_at','season','week','season_type','capture_rows','rows_count','new_fits','new_predictions','sha256','bytes','path','display_board_sha256','overlay_sha256','current_board_sha256','claim','deployed','public_output_applied','wrapper_source_sha','current_native_sha256','original_native_sha256','paired_pregame_rows','current_only_pregame_rows','original_only_pregame_rows','current_source_sha','input_cutoff','valid_until','forecast_issued_at','forecast_persisted_at','points_model','point_model','grading_version','forecast_version','source','kind','capture_schema'}

def project(t):
    out={};shapes={}
    for key,a,b in entries(t):
        typ='object' if t[a]=='{' else 'array' if t[a]=='[' else 'scalar';shapes[key]=typ
        if key in SAFE and typ=='scalar':out[key]=json.loads(t[a:b])
        if typ=='array':
            spans=list(elements(t,a));shapes[key]={'type':'array','n':len(spans),'first_object_keys':[k for k,_,_ in entries(t,spans[0][0])] if spans and t[spans[0][0]]=='{' else []}
        elif typ=='object':shapes[key]={'type':'object','keys':[k for k,_,_ in entries(t,a)]}
    return {'safe_metadata':out,'structure':shapes}

def main():
    start=time.monotonic();cpu=time.process_time()
    if CACHE.exists():raise ValueError('fresh cache required; inspect prior acquisition before resume')
    CACHE.mkdir(parents=True)
    source=json.loads((ROOT/'PUBLIC_RUN_METADATA.json').read_text());overlay=source['overlay_pointer'];selected=source['selected_pointer']
    requests=[('pointer.json',BASE+'data/weekly-adaptive-overlay.json',True),('payload.json',BASE+overlay['path'],True),('consumer.js',BASE+'weekly-adaptive-overlay.js',False),('app.js',BASE+'app.js',False),('board.json',BASE+'data/week.json',False),('selected-pointer.json',BASE+'data/weekly-selected-rankings.json',True),('selected-payload.json',BASE+'data/'+selected['path'],True),('selected-receipt.json',RAW+'output/data/weekly-selected-rankings/c5349018a5edb4adb6b31f61af314fd819543d43fc749a6bdf95ab19cf36b482.receipt.json',True),('classic-receipt.json.gz',RAW+'data/current-classic/2026/w08/fb080a82123f6641ca2b9bae217ecac25b56196cfced64bd4b3e0698e04da575.json.gz',True)]
    receipts=[];projections={};total=0
    for name,url,decode_metadata in requests:
        begin=now();req=urllib.request.Request(url,headers={'User-Agent':'NFL-V2-readonly-owner-runtime-audit','Cache-Control':'no-cache'})
        with urllib.request.urlopen(req,timeout=45) as response:
            body=response.read(8*1024*1024+1);headers={k.lower():v for k,v in response.headers.items() if k.lower() in ['date','age','etag','last-modified','cache-control','content-length','content-type']};status=response.status
        total+=len(body)
        if len(body)>8*1024*1024 or total>12*1024*1024:raise ValueError('bounded cache capacity')
        (CACHE/name).write_bytes(body)
        row={'kind':name,'url':url,'request_started_utc':begin,'receipt_completed_utc':now(),'status':status,'bytes':len(body),'sha256':digest(body),'HTTP':headers,'row_values_printed':False}
        if decode_metadata:
            unpacked=gzip.decompress(body) if name.endswith('.gz') else body
            projections[name]=project(unpacked.decode('utf-8'));row['metadata_projection']='LEXICAL_ALLOWLIST_ONLY';row['uncompressed_bytes']=len(unpacked);row['uncompressed_sha256']=digest(unpacked)
        else:row['metadata_projection']='BYTE_HASH_ONLY_NO_VALUE_DECODE'
        receipts.append(row)
        if time.monotonic()-start>300:raise ValueError('bounded readback wall budget')
    write('FRESH_BYTE_READBACK.json',{'state':'COMPLETE_READ_ONLY_PUBLIC_SOURCE_READBACK','at':now(),'source_commit':HEAD,'receipts':receipts,'private_raw_cache_bytes':total,'private_cache_durability':'LOCAL_ONLY_READ_ONLY_SOURCE_CACHE; immutable public commit retains source-specific files; no private upload/restoration claim','new_fits':0,'new_model_inference':0,'new_captures':0,'new_grades':0,'board_decoding':'NOT_DECODED; byte hashes only','resource':{'wall_seconds':time.monotonic()-start,'cpu_seconds':time.process_time()-cpu,'peak_RSS_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024}})
    write('METADATA_STRUCTURE.json',projections)
    print(json.dumps({'readbacks':len(receipts),'bytes':total,'output':'FRESH_BYTE_READBACK.json+METADATA_STRUCTURE.json','new_grades':0}))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--cache',type=pathlib.Path,required=True);args=parser.parse_args();CACHE=args.cache;main()
