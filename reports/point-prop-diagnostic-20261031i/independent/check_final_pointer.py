"""Final read-only pointer, source-binding and literal-table check."""
import hashlib,json,re
from pathlib import Path
HERE=Path(__file__).resolve().parent;BASE=HERE.parent;ROOT=HERE.parents[2]
TARGETS={'pass_yd','pass_td','pass_cmp','pass_att','pass_int','rush_yd','rush_att','rec','rec_yd','rush_rec_yd','nick-chart-ppr-v1','anytime_td'}
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rows(text):return[l for l in text.splitlines()if l.startswith('|')and len(l.split('|'))>2 and l.split('|')[1].strip()in TARGETS]
def main():
    pointerpath=ROOT/'registries/CURRENT_RESULTS_INDEX.json';pointer=read(pointerpath);bindings=[]
    for name,value in pointer.items():
        if isinstance(value,dict)and'path'in value and'sha256'in value:
            p=ROOT/value['path'];assert sha(p)==value['sha256'];bindings.append(dict(pointer_field=name,path=value['path'],sha256=value['sha256']))
    assert len(bindings)==18 and pointer['manifest']=='reports/point-prop-diagnostic-20261031i/results-index-v3/INDEX_MANIFEST.json';indexpath=ROOT/pointer['manifest'];indexreview=read(HERE/'FINAL_INDEX_V3_INDEPENDENT_REVIEW.json');assert sha(indexpath)==indexreview['manifest_sha256'];assert pointer['readable_checkpoint']=='reports/point-prop-diagnostic-20261031i/FULL_CATEGORY_CHAMPIONSHIP_REPORT.md';assert pointer['startup_scoring_versions']['sha256']==indexreview['default_startup_manifest_sha256']
    bpath=BASE/'REPORT_SOURCE_BINDINGS_I_V1.json';bound=read(bpath);assert len(bound['documents'])==2 and len(bound['source_artifacts'])==29
    for z in bound['documents']+bound['source_artifacts']:
        p=ROOT/z['path'];assert p.stat().st_size==z['bytes']and sha(p)==z['sha256']
    reportpath=ROOT/pointer['readable_checkpoint'];report=reportpath.read_text();answers=(BASE/'ANSWERS_01_TO_14_ADDENDUM.md').read_text();assert'DRAFT'not in report[:800]and'DRAFT'not in answers[:800];assert len(re.findall(r'^## Q\d+\.',answers,re.M))==14
    h=(ROOT/'reports/baselines-coverage-20261031h/DIRECT_CATEGORY_TABLES_PRESENTATION_V1.md').read_text();old_a=rows(h.split('**TABLE A')[1].split('**TABLE B')[0]);old_b=rows(h.split('**TABLE B')[1]);a=rows(report.split('**TABLE A')[1].split('## Retained current numerical')[0]);b=rows(report.split('**TABLE B')[1].split('## Older seasons')[0]);assert len(a)==len(old_a)==12 and a==old_a;assert len(b)==len(old_b)==13 and b==old_b
    for year in(2026,2025,2024,2023,2022):
        section=report.split('### '+str(year)+':')[1].split('\n### ')[0];section=section.split('\n## ')[0];source=BASE/'historical-startup'/('current-2026-v2/README.md'if year==2026 else'v1/'+str(year)+'/README.md');rr=rows(source.read_text());assert len(rr)==12 and rows(section)[:12]==rr
    links=0
    for text,path in((report,reportpath),(answers,BASE/'ANSWERS_01_TO_14_ADDENDUM.md')):
        for target in re.findall(r'\]\(([^)]+)\)',text):
            target=target.strip('<>')
            if'://'in target or target.startswith('#'):continue
            p=(path.parent/target.split('#')[0]).resolve();assert p.exists(),target;links+=1
    gridpath=BASE/'historical-startup/v1/OLDER_D1_D2_EXACT_CELL_GRID.json';grid=read(gridpath);current=read(ROOT/'reports/completion-20261031g/roster/finite-v2/CURRENT_METHOD_COMPARISONS.json');key=lambda r:(r['target'],r['procedure_id'].removesuffix(':common-feature-memory'),r['history_regime'],r['product_id']);sourcekeys={key(r)for r in current if'qualified-position-defense-information-wave-v1:'in r['procedure_id']and r['state']=='COMPLETED_VALID'};assert len(sourcekeys)==184 and{(r['season'],key(r))for r in grid}=={(y,k)for y in range(2022,2026)for k in sourcekeys};assert sum(r['state']=='SOURCE_EXTENSION_AND_FIT_REQUIRED'for r in grid)==46 and all(not r['retained_older_forecasts']and not r['exact_earlier_model_available']for r in grid)
    out=dict(state='PASS_FINAL_POINTER_REPORT_TABLES_SOURCES_AND_BOUNDED_RELEASE_CLAIMS',pointer_sha256=sha(pointerpath),checker_sha256=sha(Path(__file__)),index_manifest_sha256=sha(indexpath),final_report_sha256=sha(reportpath),fourteen_answers_sha256=sha(BASE/'ANSWERS_01_TO_14_ADDENDUM.md'),report_source_binding_sha256=sha(bpath),pointer_hash_bindings=bindings,report_bound_source_files=29,report_bound_documents=2,retained_original_category_rows=12,numerical_leader_own_selection_rows=13,literal_startup_category_tables=5,local_report_answer_links_checked=links,older_D1_D2_exact_cells_checked=736,older_D1_D2_2022_RECENT_source_extension_cells=46,scope=['Retained original selections, retrospective point/direction diagnostics and prospective captures remain separate.','Current startupW1–4/W5–7 and olderW1–4/W5–18 remain separate; own learned is not common-learned overlap.','No earlier original-pick/timing-qualified offer panel or full rare-component chart target was authenticated by I.','Numerical leaders can lose on qualified offer masks; no inverted policy, probability from points or verified return is inferred.','Prepared owner policy is not admitted/deployed; exact operational recovery, source, inference, fallback, wire/runtime, rollback and owner requirements remain.'],publication_status='Local reviewable bytes verified; GitHub commit/push and readback remain primary executor work.',new_fits=0,new_inference=0,new_scores=0,new_forecasts=0,production_mutations=0)
    with(HERE/'FINAL_POINTER_AND_REPORT_REVIEW.json').open('x')as f:json.dump(out,f,indent=2);f.write('\n')
    print(json.dumps({k:out[k]for k in('state','pointer_sha256','index_manifest_sha256','final_report_sha256','local_report_answer_links_checked')}))
if __name__=='__main__':main()
