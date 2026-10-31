"""Independently verify report winners/maxima and their source-row bindings."""
import collections,functools,hashlib,json,math,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];H=Path(__file__).resolve().parent.parent
def read(p):return json.loads(p.read_bytes())
@functools.lru_cache(maxsize=32)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
@functools.lru_cache(maxsize=5)
def source(p):return read(ROOT/p)
def close(a,b):
    if a is None or b is None:assert a is b
    else:assert math.isclose(a,b,abs_tol=1e-12,rel_tol=1e-12),(a,b)
def main():
    decisions=read(H/'CATEGORY_DECISIONS.json');finite=read(ROOT/'reports/completion-20261031g/roster/finite-v2/CURRENT_METHOD_COMPARISONS.json');p1=read(H/'probability/w5-w7-cumulative-v1/SCORES.json');p2=read(H/'probability/w5-w7-primary-p2-v1/SCORES.json');proper=[r for r in p1 if r['record_kind']=='prop_threshold_probability_evaluation'];byid={r['record_id']:r for r in proper};bindings=0;maxima=0;native=0;tables=0
    def walk(z):
        nonlocal bindings
        if isinstance(z,list):
            for v in z:walk(v)
        if isinstance(z,dict):
            for name in ('source_binding','report_source_binding'):
                if name in z:
                    b=z[name];assert sha(ROOT/b['source_artifact'])==b['source_sha256'];r=source(b['source_artifact'])[b['source_row_index']];assert b['record_id']==r.get('record_id',r.get('source_test_id'));bindings+=1
            for v in z.values():walk(v)
    walk(decisions)
    for c in decisions:
        cat=c['category'];metric='brier'if cat=='anytime_td'else'mae';rr=[r for r in finite if r['target']==cat and r['state']=='COMPLETED_VALID'and r.get(metric)is not None];best=min(r[metric]for r in rr);close(c['native_winner_loss'],best)
        expected={(r['procedure_id'],r['history_regime'],r['product_id'])for r in rr if math.isclose(r[metric],best,abs_tol=1e-12,rel_tol=0)};actual={(r['procedure_id'],r['history_regime'],r['product_id'])for r in c['native_winners']};assert actual==expected,(cat,expected,actual);native+=len(actual)
        for rule,allrows in [('P1',p1),('P2',p2)]:
            for side in ('over','under','Combined'):
                candidates=[r for r in allrows if r['record_kind']=='prop_selection_evaluation'and r['target']==cat and r['side']==side and r['n']>0]
                current=c['raw_selected_side_maxima'][rule][side]
                if not candidates:assert not current;continue
                rate=max(r['selection_metrics']['hit_rate']for r in candidates);expected={r['record_id']for r in candidates if math.isclose(r['selection_metrics']['hit_rate'],rate,abs_tol=1e-12,rel_tol=0)};assert {r['source_binding']['record_id']for r in current}==expected
                index={r['record_id']:r for r in candidates}
                for s in current:
                    r=index[s['source_binding']['record_id']];m=r['selection_metrics'];assert(s['wins'],s['losses'],s['decided'],s['selected'],s['eligible_opportunities'])==(m['WIN'],m['LOSS'],r['n'],r['forecast_rows'],m['selection_pool_count']);close(s['hit_rate'],m['hit_rate']);close(s['coverage'],m['selection_coverage']);assert s['status_counts']==m['status_counts'];assert s['fallback_rows']==r.get('fallback_rows');maxima+=1
        eligible=[r for r in proper if r['target']==cat and r['reference_id']=='candidate'and r['fallback_view']=='FULL'and r['n']>0]
        if eligible:
            value=min(r['brier']for r in eligible);assert{r['record_id']for r in c['raw_own_mask_probability_minima']}=={r['record_id']for r in eligible if math.isclose(r['brier'],value,abs_tol=1e-12,rel_tol=0)}
        else:assert not c['raw_own_mask_probability_minima']
        for field in ('matched_H_MULTI_probability','strict_current_probability'):
            for r in c[field]:
                s=byid[r['source_record_id']];close(r['candidate_brier'],s['brier']);assert r['n']==s['n'];key=(s['target'],s['matched_candidate_procedure_id'],s['history_regime'],s['fallback_view'])
                for ref,label in [('B0','neutral'),('B1','earlier_prevalence')]:
                    q=[x for x in proper if (x['target'],x['matched_candidate_procedure_id'],x['history_regime'],x['fallback_view'])==key and x['reference_id']==ref];assert len(q)==1;close(r[label+'_brier'],q[0]['brier']);assert q[0]['membership_sha256']==s['membership_sha256']
                tables+=1
        assert c['actual_new_H_deployment']is False
    assert len(decisions)==12
    text=(H/'FULL_CATEGORY_CHAMPIONSHIP_REPORT.md').read_text();required=['42/43','Weeks 1–4','0.255654','0.242276','0.25','partial-label','UNKNOWN','09:59 CDT','1,093,747,658','no qualifying offer/selection contract','147 unrun','V2.1']
    for token in required:assert token in text,token
    assert not any(c['owner_review_package'].get(k)for c in decisions for k in ('deployed','merged','served_values_verified'))
    report=dict(state='PASS_INDEPENDENT_FINAL_CATEGORY_REPORT_WINNERS_MAXIMA_SOURCE_BINDINGS_AND_LIMITS',category_rows=12,native_tied_output_views=native,raw_selected_side_maxima_including_ties=maxima,source_row_bindings=bindings,matched_reference_table_rows=tables,report_sha256=sha(H/'FULL_CATEGORY_CHAMPIONSHIP_REPORT.md'),category_JSON_sha256=sha(H/'CATEGORY_DECISIONS.json'),category_CSV_sha256=sha(H/'CATEGORY_DECISIONS.csv'),comparison_artifacts_sha256=sha(H/'COMPARISON_ARTIFACTS.md'),limits_checked=['PartialW5-W7offersnotfullseason; originalvsreconstructionseparate.','Rawtinyprior-onlymaximaretainedwithcoverage; noreleaseclaimfromthesemaxima.','Qualifiedpartialchart; unavailableactualchart/AToffers.','Seven-weeknativepanelandolder-seasonreversalsremainseparate.','NoobservednewHdeployment; elapsedownerwindow; schedulerabsencecauseunknown.'],new_fits=0,new_inference=0,new_grades=0)
    with (H/'independent/FINAL_CATEGORY_REPORT_INDEPENDENT_REVIEW.json').open('x')as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps(report))
if __name__=='__main__':main()
