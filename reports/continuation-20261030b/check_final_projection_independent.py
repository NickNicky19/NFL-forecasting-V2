"""One read-only final index, history-sidecar and checkpoint-count audit.

No NFL fits or forecast generation. No Week8 labels are acquired or decoded.
"""
import argparse
from collections import Counter,defaultdict
import csv,gzip,hashlib,json,math,subprocess,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'reports/continuation-20261030b'
sys.path.insert(0,str(ROOT))
PRECISION=('exact_rate','abs_lt_1','abs_le_1','abs_lt_5','abs_le_5','abs_lt_10','abs_le_10')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def close(a,b):
    assert(a is None and b in(None,''))or(b is None and a in(None,''))or(a not in(None,'')and b not in(None,'')and math.isclose(float(a),float(b),rel_tol=5e-11,abs_tol=5e-11)),(a,b)
def ident(r):return tuple(r[k]for k in('game_id','player_id','target','population'))
def value(v):return v if v is not None else ''

def history_review(private):
    pub=OUT/'ordered-information-ablation-v1';h=json.loads((pub/'HISTORY_PAIRED.json').read_text());run=json.loads((pub/'RUN_RECEIPT.json').read_text());path=private/'ordered-information-ablation-v1'/run['private_prediction_packet']['name'];assert sha(path)==run['private_prediction_packet']['sha256'];records=json.loads(gzip.decompress(path.read_bytes()))['rows'];bygroup=defaultdict(lambda:defaultdict(dict));checks=Counter()
    assert h['source_score_sha256']==sha(pub/'SCORES.json')and h['source_protocol_sha256']==sha(pub/'FROZEN_PROTOCOL.json')
    for r in records:bygroup[(r['target'],r['population'],r['product_id'])][r['policy_id']][ident(r)]=r
    panels={}
    for group,policies in bygroup.items():
        full=set(next(iter(policies.values())))
        assert all(set(rows)==full for rows in policies.values())
        supported={k for k in full if policies['H-CURRENT-COMMON'][k]['actual']is not None}
        assert all({k for k,r in rows.items()if r['actual']is not None}==supported for rows in policies.values())
        assert all(len({rows[k]['actual']for rows in policies.values()})==1 for k in full)
        core=set.intersection(*[{k for k,r in policies[p].items()if r['actual']is not None and r['fallback']=='none'}for p in('H-CURRENT-COMMON','H-RECENT-COMMON','H-MULTI-COMMON')])
        strict={k for k in supported if policies['H-CURRENT-COMMON'][k]['fallback']==policies['H-CURRENT-STRICT'][k]['fallback']=='none'}
        panels[group]=(full,supported,core,strict)
    for panel in h['panels']:
        g=panel['target'],panel['population'],panel['product_id'];full,supported,core,strict=panels[g]
        for field,n in [('frozen_query_n',len(full)),('supported_full_n',len(supported)),('three_core_learned_common_n',len(core)),('strict_current_pair_learned_n',len(strict))]:assert panel[field]==n;checks['panel_denominator_and_hash_checks']+=1
        assert panel['full_membership_sha256']==hashlib.sha256(canonical(sorted(supported))).hexdigest();assert panel['three_core_learned_membership_sha256']==hashlib.sha256(canonical(sorted(core))).hexdigest();checks['panel_denominator_and_hash_checks']+=2
    for r in h['fallback_decomposition']:
        g=r['target'],r['population'],r['product_id'];rows=bygroup[g][r['policy_id']];selected=[v for v in rows.values()if v['actual']is not None];fallback=[v for v in selected if v['fallback']!='none'];learned=[v for v in selected if v['fallback']=='none'];loss=lambda a:(a['prediction']-a['actual'])**2 if r['target']=='anytime_td'else abs(a['prediction']-a['actual']);fs,ls=math.fsum(map(loss,fallback)),math.fsum(map(loss,learned));n=len(selected)
        counts=dict(forecast_query_n=len(rows),supported_n=n,missing_actual_n=len(rows)-n,fallback_forecast_n=sum(v['fallback']!='none'for v in rows.values()),fallback_supported_n=len(fallback),learned_supported_n=len(learned))
        for field,v in counts.items():assert r[field]==v;checks['fallback_decomposition_checks']+=1
        metrics=dict(full_error=(fs+ls)/n if n else None,fallback_loss_sum=fs,learned_loss_sum=ls,total_loss_sum=fs+ls,fallback_error=fs/len(fallback)if fallback else None,own_learned_error=ls/len(learned)if learned else None,fallback_contribution_to_full_error=fs/n if n else None,learned_contribution_to_full_error=ls/n if n else None)
        for field,v in metrics.items():close(r[field],v);checks['fallback_decomposition_checks']+=1
    for r in h['paired_contrasts']:
        g=r['target'],r['population'],r['product_id'];full,supported,core,strict=panels[g];keys=supported if r['view']=='full_system'else core if r['view']=='three_core_learned_common'else strict;candidate=bygroup[g][r['candidate_policy_id']];control=bygroup[g][r['comparator_policy_id']];loss=lambda a:(a['prediction']-a['actual'])**2 if r['target']=='anytime_td'else abs(a['prediction']-a['actual']);a=[loss(candidate[k])for k in keys];b=[loss(control[k])for k in keys];diff=[x-y for x,y in zip(a,b)];n=len(keys);delta=math.fsum(diff)/n if n else None;ca=math.fsum(a)/n if n else None;cb=math.fsum(b)/n if n else None
        assert r['paired_n']==n;assert r['membership_sha256']==hashlib.sha256(canonical(sorted(keys))).hexdigest();checks['paired_history_checks']+=2
        for field,v in [('candidate_error',ca),('comparator_error',cb),('error_delta',delta),('relative_error_delta',delta/cb if cb else None)]:close(r[field],v);checks['paired_history_checks']+=1
        games,weeks=defaultdict(list),defaultdict(list)
        for k,d in zip(keys,diff):games[candidate[k]['game_id']].append(d);weeks[candidate[k]['week']].append(d)
        assert r['unique_games']==len(games)and r['week_clusters']==len(weeks)and r['week_interval']is None
        se=math.sqrt(len(games)/(len(games)-1)*math.fsum((math.fsum(v)-len(v)*delta)**2 for v in games.values())/n**2)if len(games)>=8 else None;close(r['game_cluster_sensitivity_se'],se)
        for week,ds in weeks.items():close(r['weekly_paired_delta'][str(week)],math.fsum(ds)/len(ds));checks['paired_history_checks']+=1
        checks['paired_history_checks']+=4
    return dict(status='PASS',panels=len(h['panels']),fallback_views=len(h['fallback_decomposition']),paired_views=len(h['paired_contrasts']),checks=dict(checks),sidecar_sha256=sha(pub/'HISTORY_PAIRED.json'))

def carry_annotations(private):
    pub=OUT/'carry-strong-control-comparison-v1';a=json.loads((pub/'COMPARISON_ANNOTATIONS.json').read_text());scores=json.loads((pub/'SCORES.json').read_text());assert a['source_score_sha256']==sha(pub/'SCORES.json');rows=json.loads(gzip.decompress((private/'carry-strong-control-comparison-v1/CARRY_CONTROL_ROWS.json.gz').read_bytes()))['methods'];models={name:{ident(r):r for r in rs}for name,rs in rows.items()};shared=set.intersection(*[{k for k,r in rs.items()if r['actual']is not None and r['fallback']=='none'}for rs in models.values()]);checks=0
    for entry,s in zip(a['rows'],scores):
        assert entry['source_record_id']==s['record_id'];name=s['record_id'].split(':')[1];view=s['fallback_view'];selected=[r for k,r in models[name].items()if r['population']==s['population']and r['actual']is not None and(view=='full_system'or view=='own_learned_only'and r['fallback']=='none'or view=='fallback_only'and r['fallback']!='none'or view=='all_five_learned_overlap'and k in shared)];comparison=entry['comparison']
        assert len(selected)==s['n']
        if not selected:assert comparison['status']=='UNESTABLISHED';continue
        ca=math.fsum(abs(r['prediction']-r['actual'])for r in selected)/len(selected);cb=math.fsum(abs(models['prior_best_mean'][ident(r)]['prediction']-r['actual'])for r in selected)/len(selected);close(comparison['candidate_error'],ca);close(comparison['comparator_error'],cb);close(comparison['absolute_error_delta'],ca-cb);close(comparison['relative_error_delta'],(ca-cb)/cb if cb else None);assert comparison['membership_sha256']==hashlib.sha256(canonical(sorted(ident(r)for r in selected))).hexdigest();checks+=5
    return dict(status='PASS',views=len(scores),paired=sum(x['comparison']['status']=='PAIRED_RETAINED_ROWS'for x in a['rows']),checks=checks)

def verify(private):
    manifest_path=OUT/'results-index/INDEX_MANIFEST.json';m=json.loads(manifest_path.read_text());prior_path=ROOT/'reports/continuation-20261030/results-index/INDEX_MANIFEST.json';prior=json.loads(prior_path.read_text());assert prior['record_count']==45706;assert len(prior['shards'])==24;assert m['shards'][:24]==prior['shards'];assert m['record_count']==47397
    result=subprocess.run(['git','diff','--exit-code','HEAD','--','reports/continuation-20261029','reports/continuation-20261030'],cwd=ROOT,capture_output=True,text=True);assert result.returncode==0 and not result.stdout
    pointer=json.loads((ROOT/'registries/CURRENT_RESULTS_INDEX.json').read_text());assert pointer['manifest']==str(manifest_path.relative_to(ROOT))
    for spec in m['input_manifests']:assert sha(ROOT/spec['source_artifact'])==spec['sha256']
    ids=set();kinds=Counter();source_counts=Counter();new=[];expected_csv={};precision_checks=0
    for part in m['shards']:
        path=ROOT/part['path'];assert sha(path)==part['sha256']and path.stat().st_size==part['bytes']and path.stat().st_size<=m['max_shard_bytes'];rows=json.loads(path.read_text());assert len(rows)==part['records']
        for r in rows:
            assert r['test_id']not in ids;ids.add(r['test_id']);kinds[r['kind']]+=1;source_counts[r['source_artifact']]+=1
            if part not in prior['shards']:new.append(r)
            source=r.get('source_aggregate_fields')or{};annotation=r.get('reporting_comparison')or source.get('comparison');fields={}
            for precision,v in(r.get('precision_metrics')or{}).items():
                if v['rate']is not None:
                    assert v['denominator']==r['n']and 0<=v['rate']<=1
                    if v['numerator']is not None:close(v['rate'],v['numerator']/v['denominator']);precision_checks+=1
            if r['kind']=='software_verification':
                assert r['n']is r['games']is r['metrics']is None and r['nfl_accuracy_from_software_tests']is None
                fields.update(comparison_status='NOT_APPLICABLE_SOFTWARE',absolute_error_change=None,relative_error_change=None)
            elif annotation and annotation.get('status')=='PAIRED_RETAINED_ROWS':
                ca,cb=annotation['candidate_error'],annotation['comparator_error'];assert annotation['paired_n']==r['n'];close(ca,r['metrics'][annotation['metric']]);assert annotation['membership_sha256'];fields.update(comparison_status='SCORING_CORRECTION_NOT_PREDICTIVE_GAIN'if source.get('correction_kind')else'PAIRED_RETAINED_ROWS',absolute_error_change=ca-cb,relative_error_change=(ca-cb)/cb if cb else None,comparator_error=cb,paired_n=r['n'],comparison_membership_sha256=annotation['membership_sha256'])
            else:fields.update(comparison_status='UNESTABLISHED',absolute_error_change=None,relative_error_change=None)
            denominator=r.get('forecast_or_offered_rows');fallback=r.get('fallback_rows');fields['fallback_rate']=fallback/denominator if fallback is not None and denominator and 0<=fallback<=denominator else None
            fields['category']=r.get('category');fields['kind']=r['kind'];fields['source_artifact']=r['source_artifact'];fields['source_artifact_sha256']=r.get('source_artifact_sha256');fields['n']=r.get('n');fields['primary_error']=r.get('primary_error');fields['target_source']=source;fields['precision']=r.get('precision_metrics')or{};expected_csv[r['test_id']]=fields
    assert len(ids)==m['record_count']and dict(kinds)==m['by_kind'];assert len(new)==1691
    # New index source records remain exact copies of the immutable canonical rows.
    bysource=defaultdict(list)
    for r in new:
        assert sha(ROOT/r['source_artifact'])==r['source_artifact_sha256'];bysource[r['source_artifact']].append(r)
    for artifact,rs in bysource.items():
        if rs[0]['kind']=='software_verification':continue
        raw=json.loads((ROOT/artifact).read_text());assert Counter(canonical(x)for x in raw)==Counter(canonical(r['source_aggregate_fields'])for r in rs)
    headers=None;csv_ids=set();csv_checks=0;website_paired=0
    for part in m['csv_parts']:
        path=ROOT/part['path'];assert sha(path)==part['sha256']and path.stat().st_size==part['bytes'];n=0
        with path.open(newline='')as handle:
            reader=csv.DictReader(handle)
            if headers is None:headers=reader.fieldnames
            assert headers==reader.fieldnames
            for row in reader:
                assert row['test_id']not in csv_ids;csv_ids.add(row['test_id']);e=expected_csv[row['test_id']]
                for field in('comparison_status','kind','source_artifact','source_artifact_sha256'):
                    assert row[field]==value(e[field]);csv_checks+=1
                for field in('n','primary_error','absolute_error_change','relative_error_change','fallback_rate'):
                    close(row[field],e[field]);csv_checks+=1
                for field in('comparator_error','paired_n'):
                    if field in e:close(row[field],e[field]);csv_checks+=1
                if 'comparison_membership_sha256'in e:assert row['comparison_membership_sha256']==e['comparison_membership_sha256'];csv_checks+=1
                for precision,v in e['precision'].items():
                    for suffix,field in [('rate','rate'),('numerator','numerator'),('denominator','denominator')]:close(row[precision+'_'+suffix],v[field]);csv_checks+=1
                if row['source_artifact'].endswith('website-reference-replay-v1/SCORES.json')and row['comparison_status']=='PAIRED_RETAINED_ROWS':
                    assert 'UNMATCHED_INFORMATION_CUTOFFS'in row['cutoff'];assert row['live_website_comparison_status']=='UNESTABLISHED';assert row['prediction_or_scoring_change']!='scoring_correction';website_paired+=1
                if e['relative_error_change']is None:assert row['relative_error_missing_reason']
                n+=1
        assert n==part['rows']
    assert csv_ids==ids and website_paired==20
    category_ids=set()
    for path in(OUT/'results-index/categories').glob('*.csv'):
        with path.open(newline='')as handle:
            for row in csv.DictReader(handle):assert row['test_id']not in category_ids;category_ids.add(row['test_id'])
    assert category_ids=={k for k,v in expected_csv.items()if v['kind']!='software_verification'}
    # Independently exercise zero-control relative-change guard without NFL samples.
    from nfl_v2.comparison_reporting import error_change
    zero=error_change(2.,0.);assert zero['absolute_error_change']==2.0 and zero['relative_error_change']is None and zero['relative_error_missing_reason']=='zero_comparator_error_denominator'
    counts=json.loads((OUT/'CHECKPOINT_COUNTS.json').read_text());a=json.loads((OUT/'availability-wave-v1/CUMULATIVE_RESOURCE_RECEIPT.json').read_text());ab=json.loads((OUT/'availability-wave-v1/AB-RUN_RECEIPT.json').read_text());c=json.loads((OUT/'availability-wave-v1/C-RUN_RECEIPT.json').read_text());historical=json.loads((OUT/'ordered-information-ablation-v1/RUN_RECEIPT.json').read_text());future=json.loads((OUT/'c02-future-shadow-v1/RUN_RECEIPT.json').read_text())
    assert counts['new_nfl_fit_calls']==c['actual_fit_calls']+historical['actual_fit_calls']+future['actual_fit_calls']==425
    assert counts['future_output_views']==ab['output_views']+c['output_views']+future['output_views']==134269
    assert counts['future_issued']==ab['issued']+c['issued']+future['issued']==133869
    assert counts['future_abstained']==ab['abstained']+c['abstained']+future['abstained']==400
    assert counts['main_univariate_score_views']==40+40+historical['score_views']==1688
    for field,value_ in [('availability_active_wall_seconds',a['actual_cumulative_active_wall_seconds']),('availability_cpu_seconds',a['actual_cumulative_active_cpu_seconds']),('C02_historical_wall_seconds',historical['resource']['wall_seconds']),('C02_historical_cpu_seconds',historical['resource']['cpu_seconds']),('C02_future_wall_seconds',future['resource']['wall_seconds']),('C02_future_cpu_seconds',future['resource']['cpu_seconds'])]:close(counts['actual_run_resource'][field],value_)
    return dict(status='PASS_FINAL_IMMUTABLE_INDEX_COMPARISONS_HISTORY_AND_COUNTS',record_count=len(ids),evaluation_views=len(category_ids),software_receipts=kinds['software_verification'],immutable_prior_shards=24,immutable_prior_records=45706,new_records=len(new),all_input_manifest_hashes=len(m['input_manifests']),csv_rows=len(csv_ids),csv_field_checks=csv_checks,precision_rate_denominator_checks=precision_checks,website_paired_outcome_views_explicitly_unmatched_cutoff=website_paired,old_checkpoint_git_diff='UNCHANGED',category_report='CATEGORY_PROJECTION_INDEPENDENT_REVIEW.json',carry_annotations=carry_annotations(private),paired_history=history_review(private),checkpoint_resources='EXACT_RECEIPT_FIELDS_MATCH',manifest_sha256=sha(manifest_path),new_fits=0,new_forecasts=0,week8_outcomes_read=0)
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--private-root',type=Path,required=True);args=parser.parse_args();r=verify(args.private_root);OUT.joinpath('FINAL_PROJECTION_INDEPENDENT_REVIEW.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
