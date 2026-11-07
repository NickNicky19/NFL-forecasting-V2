"""Independent B-only week-count arithmetic and bound source witnesses."""
import argparse,collections,csv,gzip,hashlib,json,math
from datetime import datetime,timezone
from pathlib import Path
def load(p):
    b=p.read_bytes();return json.loads(gzip.decompress(b)if p.suffix=='.gz'else b)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def positive_week(r):
    s=r.get('source_aggregate_fields')or{};w=r.get('week');y=r.get('season')
    def integer(v):
        if isinstance(v,bool):return None
        try:return int(v)if float(v)==int(v)else None
        except(TypeError,ValueError,OverflowError):return None
    w=integer(w)if integer(w)is not None else integer(s.get('week'));years=r.get('seasons')or s.get('evaluation_seasons')or[];y=integer(y)if integer(y)is not None else integer(years[0])if len(years)==1 else None;n=r.get('n');n=n if type(n)is int else 0;push=(r.get('selection_metrics')or{}).get('PUSH',0)or 0
    return(y,w)if y is not None and w is not None and 1<=w<=18 and n+(push if r.get('kind')=='prop_selection_evaluation'else 0)>0 else None
def run(repo,out):
    receipt=load(out/'RUN_RECEIPT.json');path=out/receipt['delivery']['json_path'];body=gzip.decompress(path.read_bytes());assert sha(path)==receipt['delivery']['json_sha256']and hashlib.sha256(body).hexdigest()==receipt['delivery']['json_uncompressed_sha256'];records=json.loads(body);assert len(records)==receipt['product_views']==41404
    fields=['procedure_id','category','product_id','history','information_policy','feature_memory','strict_current_information','population','position','fallback_view','selection_rule','selected_side_view','K','rank_scope','horizon','source_vintage','code_version','config_version'];seen=set();states=collections.Counter();testidset=set()
    for r in records:
        key=json.dumps({k:r[k]for k in fields},sort_keys=True,separators=(',',':'));assert r['qualification_id']=='B5W-'+hashlib.sha256(key.encode()).hexdigest()[:20]and key not in seen;seen.add(key)
        weeks=[tuple(x)for x in r['scored_season_weeks']];verified=[tuple(x)for x in r['verified_scored_season_weeks']];assert weeks==sorted(set(weeks))and verified==sorted(set(verified))and set(verified)<=set(weeks)and len(weeks)==r['scored_week_count']and len(verified)==r['verified_scored_week_count'];assert all(2022<=y<=2026 and 1<=w<=18 for y,w in weeks)
        union=[]
        for year,s in r['per_season'].items():
            assert s['weeks']==sorted(set(s['weeks']))and len(s['weeks'])==s['scored_week_count']==len(s['test_ids'])and s['supported_cases']>0;union.extend((int(year),w)for w in s['weeks']);testidset.update(s['test_ids'])
        witness_ids=[i for z in r['per_season'].values()for i in z['test_ids']];assert len(witness_ids)==len(set(witness_ids))
        assert sorted(union)==weeks and not(set(map(tuple,r['attempted_zero_or_unresolved_weeks']))&set(weeks))
        state=r['minimum_week_floor_status'];states[state]+=1
        if state=='FIVE_WEEK_MINIMUM_MET':assert len(verified)>=5
        elif state=='BELOW_FIVE_EXPLICIT_SCORED_WEEKS':assert len(weeks)<5
        elif state=='UNESTABLISHED_AGGREGATE_ONLY_WEEK_SUPPORT_PROOF_REQUIRED':assert r['aggregate_only_views_not_used_as_week_proof']>0 and len(verified)<5
        else:assert state=='REPORTED_FIVE_WEEKS_ONLY_NOT_INDEPENDENTLY_VERIFIED'and len(weeks)>=5 and len(verified)<5
        assert r['primary_replacement_admitted']is False and 'not establish current-season validation'in r['qualification_limit']
    assert dict(states)==receipt['floor_states']and states['FIVE_WEEK_MINIMUM_MET']==1596 and len({r['procedure_id']for r in records})==receipt['distinct_procedure_id_strings_NOT_method_family_count']==4242
    # CSV and JSON carry identical individual product views, without duplicated periods.
    csvpath=out/receipt['delivery']['csv_path'];assert sha(csvpath)==receipt['delivery']['csv_sha256']
    with gzip.open(csvpath,'rt',newline='')as f:
        count=0;reader=csv.DictReader(f)
        for a,b in zip(records,reader):
            for k,v in a.items():assert b[k]==(json.dumps(v,separators=(',',':'))if isinstance(v,(list,dict))else''if v is None else str(v))
            count+=1
        assert count==len(records)and next(reader,None)is None
    # Freeze representative witness types by recipe/period, not observed accuracy.
    def first(pred):return next(r for r in records if pred(r))
    samples=[first(lambda r:r['scored_week_count']==7 and r['category']=='pass_yd'and r['procedure_id']=='hgb-direct-history-controls-v1:absolute_error_point'and r['history']=='H-CURRENT'and r['position']=='ALL'),first(lambda r:r['scored_week_count']==7 and r['category']=='pass_yd'and'ordered_leaf_cdf:strict-current-inputs'in r['procedure_id']and r['position']=='ALL'),first(lambda r:r['scored_week_count']==72 and r['category']=='pass_yd'and r['procedure_id']=='empirical-player-history-control-v1'and r['product_id']=='lower_median'and r['history']=='H-CURRENT'and r['position']=='ALL'),first(lambda r:r['scored_week_count']==72 and r['category']=='pass_yd'and'hgb-direct-history-controls-v1:absolute_error_point'in r['procedure_id']and r['history']=='H-CURRENT'and r['position']=='ALL')]
    wanted={tid for r in samples for s in r['per_season'].values()for tid in s['test_ids']};found={};manifestpath=repo/receipt['source_manifest'];manifest=load(manifestpath);assert sha(manifestpath)==receipt['source_manifest_sha256']and manifest['record_count']==receipt['source_record_count']==602201;scanned=0
    for part in manifest['shards']:
        p=repo/part['path'];assert p.stat().st_size==part['bytes']and sha(p)==part['sha256'];raw=gzip.decompress(p.read_bytes())if part.get('compression')=='gzip'else p.read_bytes();rr=json.loads(raw);assert len(rr)==part['records']
        for r in rr:
            if r['test_id']in wanted:
                assert r['test_id']not in found;found[r['test_id']]=r
        scanned+=1
        if scanned%100==0:print(json.dumps(dict(progress_shards=scanned,representative_week_witnesses_found=len(found),required=len(wanted))),flush=True)
        if wanted==found.keys():break
    assert wanted==found.keys();witness=[]
    for q in samples:
        for year,s in q['per_season'].items():
            rr=[found[k]for k in s['test_ids']];assert sorted(positive_week(r)for r in rr)==[(int(year),w)for w in s['weeks']];assert sum(r['n']for r in rr)==s['supported_cases']
            for r in rr:
                assert r['procedure_id']==q['procedure_id']and r['category']==q['category']and r['product_id']==q['product_id']and r['history_regime']==q['history']and r['population']==q['population']and r['position']==q['position']and r['fallback_view']==q['fallback_view'];assert not r.get('season_alias_of_week_view')and 'INVALIDATED'not in str(r.get('score_version_state'))and 'SUPERSEDED'not in str(r.get('score_version_state'))
        witness.append(dict(qualification_id=q['qualification_id'],procedure=q['procedure_id'],category=q['category'],product=q['product_id'],history=q['history'],explicit_scored_weeks=q['scored_week_count'],seasons={year:dict(weeks=s['weeks'],n=s['supported_cases'])for year,s in q['per_season'].items()}))
    # New exact policies can only receive their own explicit positive weeks.
    newpath=repo/receipt['new_policy_source']['path'];new=load(newpath);assert sha(newpath)==receipt['new_policy_source']['sha256']and len(new)==816;newq=[r for r in records if'POST-WAVE-5W-CORRECTNESS-RANK'in str(r['procedure_id'])];zero=0;fullsystem=[]
    for r in newq:
        source=[s for s in new if s['procedure_id']==r['procedure_id']and s['target']==r['category']and s['strategy']==r['selection_rule']and s['side']==r['selected_side_view']and s['cohort_id']=='ALL'];weeks=set()
        for s in source:
            w=s['week'];support=s['n']+s['selection_metrics'].get('PUSH',0)
            if type(w)is int and support>0:weeks.add((s['season'],w))
        assert weeks==set(map(tuple,r['scored_season_weeks']))and r['minimum_week_floor_status']=='BELOW_FIVE_EXPLICIT_SCORED_WEEKS'
        if r['selection_rule']=='FIXED_090':assert not weeks;zero+=1
        if r['selected_side_view']=='Combined'and r['selection_rule']=='MATCHED50'and'::MATCHED_'not in r['procedure_id']:fullsystem.append(dict(procedure=r['procedure_id'],actual_weeks=r['scored_season_weeks'],week_count=r['scored_week_count']))
    assert zero>0 and len(fullsystem)==4
    for r in records:assert not any('COMMON_LEARNED_RANKER_OUTPUT_ROWS'in str(x)for x in[r.get('selection_rule'),r.get('fallback_view')])
    result=dict(state='PASS_B_ONLY_PRODUCT_WEEK_COUNTS_AND_REPRESENTATIVE_SOURCE_WITNESSES',at_utc=datetime.now(timezone.utc).isoformat(),verification_code_sha256=sha(Path(__file__)),qualification_receipt_sha256=sha(out/'RUN_RECEIPT.json'),qualification_compressed_sha256=sha(path),all_product_view_internal_and_CSV_rows_checked=len(records),count_floor_product_views=1596,duplicate_week_witness_ids_within_product=0,distinct_procedure_ID_strings_not_families=4242,historical_and_current_seasons_kept_separate=True,representative_bound_weekly_index_rows_checked=len(found),immutable_index_shards_read=scanned,representative_7_and_72_week_witnesses=witness,new_exact_policy_fullsystem=fullsystem,new_zero90_side_product_views_checked=zero,extra_new_score_rows=816,new_fits=0,new_inference=0,new_scores=0,limits=['1596 is a count of typed product/side/history/role views meeting a retained-score week-count floor, not1596independent methods or an owner/scientific admission.','Full602201source-index rows were not re-audited numerically; all41404contribution rows received internal/set/count/CSV checks, with158representative exact weekly index witnesses and all newpolicy weeksets independently checked.','Previously reported evidence is not NFL label verification; code/source/role continuity and strongest-control/operational criteria remain separate.','Aggregate-only date spans and base-method training history do not add policy weeks. Fullsystem newranker has2rec/1PTweeks; actual learnedoutputhas1each per separate independent mask receipt; empty90policies have0.','No shared A/B/C master or new scoring pipeline created; this is a B-only verification contribution.'])
    (out/'INDEPENDENT_B_PRODUCT_WEEK_QUALIFICATION_V1.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('repo',type=Path);p.add_argument('out',type=Path);a=p.parse_args();run(a.repo,a.out)
