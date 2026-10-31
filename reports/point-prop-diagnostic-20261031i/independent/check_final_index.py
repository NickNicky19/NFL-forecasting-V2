"""Read-only append-index and source/CSV parity verifier."""
import argparse,collections,csv,gzip,hashlib,json,math
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
OLD=ROOT/'reports/baselines-coverage-20261031h/results-index-v1/INDEX_MANIFEST.json'
def read(p):return json.loads(p.read_bytes())
def sha(p):
    h=hashlib.sha256()
    with p.open('rb')as f:
        for block in iter(lambda:f.read(1048576),b''):h.update(block)
    return h.hexdigest()
def open_text(p):return gzip.open(p,'rt',newline='')if p.suffix=='.gz'else p.open(newline='')
def num(x):return None if x in('',None)else float(x)
def close(a,b):
    if a is None or b is None:assert a is b,(a,b)
    else:assert math.isclose(float(a),float(b),abs_tol=1e-10,rel_tol=1e-11),(a,b)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--manifest',type=Path,required=True);ap.add_argument('--receipt',type=Path,required=True);a=ap.parse_args();m=read(a.manifest);old=read(OLD);assert m['shards'][:len(old['shards'])]==old['shards'];assert m['csv_parts'][:len(old['csv_parts'])]==old['csv_parts'];oldfiles=0
    for z in old['shards']+old['csv_parts']:
        f=ROOT/z['path'];assert f.stat().st_size==z['bytes']and sha(f)==z['sha256'];oldfiles+=1
    testids=set();new={};source_cache={};kinds=collections.Counter();precision_views=0;indexrecords=0
    for j,z in enumerate(m['shards']):
        f=ROOT/z['path'];assert f.stat().st_size==z['bytes']and sha(f)==z['sha256'];raw=gzip.decompress(f.read_bytes())if z.get('compression')=='gzip'else f.read_bytes()
        if z.get('compression')=='gzip':assert len(raw)==z['uncompressed_bytes']and hashlib.sha256(raw).hexdigest()==z['uncompressed_sha256']
        rows=json.loads(raw);assert len(rows)==z['records'];indexrecords+=len(rows)
        for r in rows:
            assert r['test_id']not in testids;testids.add(r['test_id'])
            if j<len(old['shards']):continue
            new[r['test_id']]=r;kinds[r['kind']]+=1;source=r['source_artifact'];digest=r['source_artifact_sha256']
            if source not in source_cache:
                p=ROOT/source;assert sha(p)==digest;values=read(p);source_cache[source]={v.get('record_id'):v for v in values}if isinstance(values,list)else values
            if r['kind']=='software_verification':continue
            src=source_cache[source][r['source_record_id']];assert r['source_aggregate_fields']==src;assert r['n']==src['n'];assert r['procedure_id']==src['procedure_id']and r['category']==src['target']and r['history_regime']==src['history_regime']and r['product_id']==src['product_id']
            for k in('mae','mse','rmse','bias','max_abs','brier'):
                if k in src:close(r['metrics'].get(k),src[k])
            if 'precision_counts'in src:
                pre=r['precision_metrics'];assert pre is not None,(r['test_id'],'nested-only precision not exposed')
                for name,v in src['precision_counts'].items():
                    q=pre[name];assert q['denominator']==v['denominator']==r['n']
                    if r['n']:assert q['numerator']==v['numerator']
                    else:assert q['numerator']in(None,0)
                    close(q['rate'],v['rate'])
                precision_views+=1
            if r['kind']=='prop_selection_evaluation':
                assert r['source_vintage']!='SERVER_BOUND_ORIGINAL_THRESHOLDS_AND_POINTS;CURRENT_VINTAGE_QUALIFIED_LABELS';assert 'reporting_metadata_provenance'in r
                if r['category']in('pass_yd','pass_cmp'):assert len(r['diagnostic_context_coverage'])>0
    assert indexrecords==m['record_count']and len(new)==m['record_count']-old['record_count'];assert sum(z['rows']for z in m['csv_parts'])==m['record_count'];seen_csv=set();header=None
    for z in m['csv_parts'][len(old['csv_parts']):]:
        f=ROOT/z['path'];assert f.stat().st_size==z['bytes']and sha(f)==z['sha256'];count=0
        with open_text(f)as g:
            rr=csv.DictReader(g)
            if header is None:header=rr.fieldnames
            else:assert rr.fieldnames==header
            for c in rr:
                count+=1;tid=c['test_id'];assert tid not in seen_csv;seen_csv.add(tid);r=new[tid];assert c['source_artifact']==r['source_artifact']and c['source_artifact_sha256']==r['source_artifact_sha256'];assert(c['procedure_id']or None)==r.get('procedure_id')and(c['category']or None)==r.get('category');close(num(c['n']),r['n'])
                for k in('mae','mse','rmse','bias','max_abs','brier'):close(num(c[k]),(r.get('metrics')or{}).get(k))
                for name,v in(r.get('precision_metrics')or{}).items():
                    if name=='decided_pick_hit_rate':continue
                    close(num(c[name+'_rate']),v['rate']);close(num(c[name+'_numerator']),v['numerator']);close(num(c[name+'_denominator']),v['denominator'])
                comparison=r.get('reporting_comparison')or{}
                if comparison.get('status')=='PAIRED_RETAINED_ROWS':
                    close(num(c['paired_candidate_error']),comparison['candidate_error']);close(num(c['comparator_error']),comparison['comparator_error']);close(num(c['paired_n']),comparison['paired_n']);delta=comparison['candidate_error']-comparison['comparator_error'];close(num(c['absolute_error_change']),delta);close(num(c['relative_error_change']),delta/comparison['comparator_error']if comparison['comparator_error']else None)
        assert count==z['rows']
    assert seen_csv==set(new)
    defaultpath=HERE.parent/'historical-startup/DEFAULT_CURRENT_STARTUP_VIEW.json';default=read(defaultpath);mappingpath=ROOT/default['scoring_replacements'];mapping=read(mappingpath);assert sha(mappingpath)==default['scoring_replacements_sha256'];assert sha(ROOT/default['base_source'])==default['base_sha256']and sha(ROOT/default['correction_source'])==default['correction_sha256'];assert default['base_rows']==default['default_rows']==3936 and default['new_scoring_versions']==18 and default['other_original_rows_unchanged']==3918
    supersessionpath=HERE.parent/'CURRENT_STARTUP_INDEX_SUPERSESSION_MAP_V3.json';supermap=read(supersessionpath);assert supermap['source_replacement_mapping_sha256']==sha(mappingpath);assert len(supermap['rows'])==18;oldids=set();replacementids=set()
    for z in supermap['rows']:
        x=new[z['source_test_id']];y=new[z['replacement_test_id']];assert x['source_record_id']==z['source_record_id']and y['source_record_id']==z['replacement_record_id'];assert x['score_version_state']=='SUPERSEDED_PRECISION_SCORING_ONLY'and x['replacement_test_id']==y['test_id'];assert x['source_artifact']==default['base_source']and y['source_artifact']==default['correction_source'];assert x['metrics']==y['metrics']and x['n']==y['n'];oldids.add(x['test_id']);replacementids.add(y['test_id'])
    active=[r for tid,r in new.items()if(r['source_artifact']==default['base_source']and tid not in oldids)or tid in replacementids];assert len(active)==3936 and len({(r['category'],r['procedure_id'],r['history_regime'],r['product_id'],r['week'],r['fallback_view'])for r in active})==3936
    startup_comparisons=active_comparisons=0
    for tid,r in new.items():
        q=r.get('reporting_comparison')or{}
        if '/historical-startup/'not in r['source_artifact']or q.get('status')!='PAIRED_RETAINED_ROWS':continue
        src=r['source_aggregate_fields'];ref=source_cache[q['comparator_source_artifact']][q['comparator_record_id']];assert src['membership_sha256']==ref['membership_sha256']==q['membership_sha256'];assert src['source_outcome_index_sha256']==ref['source_outcome_index_sha256'];assert src['n']==ref['n']==q['paired_n'];close(q['candidate_error'],src[q['metric']]);close(q['comparator_error'],ref[q['metric']]);startup_comparisons+=1;active_comparisons+=tid not in oldids
    assert startup_comparisons==4614 and active_comparisons==4608
    out=dict(state='PASS_IMMUTABLE_H_PREFIX_NEW_SOURCES_NESTED_PRECISION_CSV_AND_CURRENT_DEFAULT',manifest_sha256=sha(a.manifest),records=m['record_count'],JSON_shards=len(m['shards']),CSV_parts=len(m['csv_parts']),unchanged_H_records=old['record_count'],unchanged_H_JSON_shards=len(old['shards']),unchanged_H_CSV_parts=len(old['csv_parts']),old_files_rehashed=oldfiles,new_records=len(new),new_kinds=dict(kinds),new_source_arrays=len(source_cache),nested_precision_views_verified=precision_views,new_records_and_CSV_cells_verified=True,current_startup_default_views=len(active),superseded_precision_records=18,startup_audit_comparisons=4614,startup_default_comparisons=4608,default_startup_manifest_sha256=sha(defaultpath),supersession_map_sha256=sha(supersessionpath),limits=['This verifies retained bytes, identities, counts and index projections. Source truth and numerical/settlement math have separately scoped independent receipts.','Original superseded precision versions remain in the audit; exactly18 replacements enter the current startup default.'],new_fits=0,new_inference=0,new_scores=0)
    with a.receipt.open('x')as f:json.dump(out,f,indent=2);f.write('\n')
    print(json.dumps(out))
if __name__=='__main__':main()
