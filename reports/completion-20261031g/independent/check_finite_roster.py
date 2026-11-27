"""Check finite current recipe coverage against canonical source IDs, not labels."""
import argparse,csv,hashlib,importlib.util,json,math
from collections import Counter
from pathlib import Path
from datetime import datetime,timezone

spec=importlib.util.spec_from_file_location('independent_numeric',Path(__file__).resolve().parents[2]/'championship-20261030f/independent/check_numerical_pairs.py');ind=importlib.util.module_from_spec(spec);spec.loader.exec_module(ind)
def read(p):return json.loads(p.read_bytes())
def key(r):return ind.model(dict(r,target=r.get('target',r.get('category'))))


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();root=a.repo_root;public=root/'reports/completion-20261031g/roster/finite-v2';receipt=read(public/'ROSTER_RECONCILIATION_RECEIPT.json');rows=read(public/'CURRENT_METHOD_COMPARISONS.json');manifest=root/receipt['source_manifest']['path'];assert ind.sha(manifest)==receipt['source_manifest']['sha256'];m=read(manifest);source={}
    for binding in m['csv_parts']:
        file=root/binding['path'];assert ind.sha(file)==binding['sha256']
        with file.open()as f:
            for r in csv.DictReader(f):
                if r['season']!='2026'or r['week']not in('','ALL')or r['population']!='primary'or r['position']not in('','ALL')or r['fallback_view']not in('','ALL')or r['cohort_id']or json.loads(r['evaluation_weeks'])!=list(range(1,8)):continue
                if r['evidence']!='NEW_EXPERIMENT'and r['source_artifact']!='reports/continuation-20261030/chart-grid-precision-correction-v1/SCORES.json':continue
                kk=key(r);assert kk not in source;source[kk]=r
    fixed=[r for r in rows if r['procedure_kind']=='FIXED_FORECAST_RECIPE'];policies=[r for r in rows if r['procedure_kind']!='FIXED_FORECAST_RECIPE'];assert len(fixed)==641 and len(policies)==36
    completed=missing=0;ids=set();unknown=[];policysource=read(root/'reports/championship-20261030f/category-selector-v2/SCORES.json');policyby={r['record_id']:r for r in policysource}
    for r in fixed:
        s=source.get(key(r))
        if r['state']=='COMPLETED_VALID':
            assert s is not None and r['source_test_id']==s['test_id']and int(s['n'])==r['n'];ids.add(r['source_test_id']);completed+=1
            for metric in('mae','mse','brier','bias','p90_abs','p95_abs','max_abs'):
                val=s.get(metric)
                if val in(None,''):assert r.get(metric)is None
                else:assert math.isclose(r[metric],float(val),abs_tol=1e-10,rel_tol=1e-10)
            expected=json.loads(s['precision_counts']or'{}')
            for name,(num,den)in expected.items():assert r['precision_counts'][name]['numerator']==num and r['precision_counts'][name]['denominator']==den
        else:
            missing+=1;assert s is None and r['n']is None and r['source_test_id']is None and r['missing_reason'];assert r['state']=='FIT_REQUIRED'and r['history_regime']=='H-CURRENT'and r['procedure_id'].startswith('hgb-direct-history-controls-v1:')and'strict-current'in r['procedure_id'];unknown.append(dict(target=r['target'],procedure_id=r['procedure_id'],product_id=r['product_id']))
    for r in policies:
        s=policyby[r['source_test_id']];assert r['state']=='COMPLETED_VALID';assert r['n']==s['n']and r.get('mae')==s.get('mae')and r.get('brier')==s.get('brier')
    assert completed==receipt['current_fixed_completed']==620 and missing==21 and len(ids)==620
    roster=read(public/'FINITE_IMPLEMENTED_PROCEDURE_ROSTER.json');mechanisms=[r for r in roster if r['unit_kind']=='FIXED_DISTINCT_SCIENTIFIC_MECHANISM'];assert len(mechanisms)==11
    assert receipt['legacy_labels']==234 and receipt['raw_implemented_procedure_strings']==29 and receipt['normalized_fixed_recipe_procedure_strings']==25
    report=dict(state='PASS_INDEPENDENT_FINITE_ROSTER_CANONICAL_IDS_AND_EXACT_MISSING_CELLS',at=datetime.now(timezone.utc).isoformat(),roster_receipt_sha256=ind.sha(public/'ROSTER_RECONCILIATION_RECEIPT.json'),current_table_sha256=ind.sha(public/'CURRENT_METHOD_COMPARISONS.json'),fixed_recipe_output_cells=641,complete_current_cells=620,genuinely_unrun_strict_HGB_recipe_output_cells=21,corresponding_origin_opportunities=147,separate_original_composite_target_products=36,scientific_mechanisms=11,raw_implemented_procedure_strings=29,normalized_strings=25,legacy_labels_not_treated_as_scientific_methods=234,missing_cells=unknown,new_fits=0,new_scores=0,new_forecasts=0,scope='Finite implemented V2 library plus separately listed unresolved legacy references; not every method ever tested. Draftv1 false126gaps superseded, original score bytes unchanged.')
    with a.output.open('x')as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps({k:report[k]for k in('state','complete_current_cells','genuinely_unrun_strict_HGB_recipe_output_cells','scientific_mechanisms')}))


if __name__=='__main__':main()
