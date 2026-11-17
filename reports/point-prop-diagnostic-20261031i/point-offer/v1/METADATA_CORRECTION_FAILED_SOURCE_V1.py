"""Version the two focal OWN denominators; no metrics or score bytes change."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2.shared_subgroups import canonical,now,sha,write
from tools.numerical_championship import csvwrite


def main(a):
    out=a.output.resolve();source=out/'SCORES.json';source_sha=sha(source);vintage=out/'CURRENT_REPORTING_ANNOTATIONS_I_V1.json';vintage_sha=sha(vintage)
    old=out/'CONTEXT_COVERAGE_EXTENSION_V1.json';rows=json.loads(old.read_bytes());before=json.loads(old.read_bytes());changes=[]
    expected={66:('pass_cmp','v2-qualified-position-defense-information-wave-v1:D1',76),102:('pass_yd','hgb-direct-history-controls-v1:absolute_error_point',80)}
    for i,(target,proc,n) in expected.items():
        r=rows[i]
        if (r['target'],r['procedure_id'],r['context'],r['available_point_forecasts'],r['context_outer_opportunities'])!=(target,proc,'OWN_DECISION_ELIGIBLE_FULL_SYSTEM',n,n):raise ValueError('expected original metadata does not match')
        previous=dict(r);r.update(context_outer_opportunities=84,context_unavailable_forecasts=84-n,context_coverage=n/84,interpretation='OWN alias uses all84sourceoffers. Canonical record retains the first-emitted conditional-view denominator; its prediction, loss and state counts are unchanged. Use this context denominator for full-source coverage.')
        changes.append(dict(context_row_index=i,record_id=r['record_id'],before=previous,after=dict(r)))
    if [i for i,(a,b) in enumerate(zip(before,rows)) if a!=b]!=[66,102]:raise ValueError('unexpected context change')
    new=out/'CONTEXT_COVERAGE_EXTENSION_V2.json';write(new,rows)
    oldtable=out/'MATCHED_FOCAL_SCORECARD.json';table=json.loads(oldtable.read_bytes());originaltable=json.loads(oldtable.read_bytes());tablechanges=[]
    for r in table:
        if any(r['record_id']==x['record_id'] for x in changes):
            previous=dict(r);r.update(full_source_outer_offers=84,own_unavailable_forecasts=84-r['own_forecast_rows']);tablechanges.append(dict(record_id=r['record_id'],before_outer=previous['full_source_outer_offers'],after_outer=84,before_unavailable=previous['own_unavailable_forecasts'],after_unavailable=r['own_unavailable_forecasts']))
    if len(tablechanges)!=2:raise ValueError('two and only two machine rows required')
    allowed={'full_source_outer_offers','own_unavailable_forecasts'}
    for a,b in zip(originaltable,table):
        if any(a[k]!=b[k] for k in a if k not in allowed):raise ValueError('machine score value changed')
    write(out/'MATCHED_FOCAL_SCORECARD_V2.json',table);csvwrite(out/'MATCHED_FOCAL_SCORECARD_V2.csv',table)
    default=out/'DEFAULT_DIAGNOSTIC_VIEW.json';backup=out/'DEFAULT_DIAGNOSTIC_VIEW_V1_SUPERSEDED.json';backup.write_bytes(default.read_bytes());view=json.loads(default.read_bytes());view.update(schema='v2-I-source-bound-diagnostic-default-view-v2',context_coverage_extension=new.relative_to(a.root).as_posix(),context_coverage_extension_sha256=sha(new),require_context_specific_coverage=True,matched_focal_scorecard=(out/'MATCHED_FOCAL_SCORECARD_V2.json').relative_to(a.root).as_posix(),matched_focal_scorecard_sha256=sha(out/'MATCHED_FOCAL_SCORECARD_V2.json'))
    default.write_bytes(canonical(view))
    readme=out/'README.md';readmeold=out/'README_CONTEXT_COVERAGE_V1_SUPERSEDED.md';readmeold.write_bytes(readme.read_bytes());text=readme.read_text()
    for oldtext,newtext in [('D1 Leaf-CDF v1 / H-MULTI / lower_median | 76/76/76 |','D1 Leaf-CDF v1 / H-MULTI / lower_median | 76/76/84 |'),('HGB direct L1 v1 / H-MULTI / absolute_error_point | 80/80/80 |','HGB direct L1 v1 / H-MULTI / absolute_error_point | 80/80/84 |')]:
        if text.count(oldtext)!=1:raise ValueError('expected one focal readable row')
        text=text.replace(oldtext,newtext)
    text=text.replace('(MATCHED_FOCAL_SCORECARD.csv)','(MATCHED_FOCAL_SCORECARD_V2.csv)').replace('(CONTEXT_COVERAGE_EXTENSION_V1.json)','(CONTEXT_COVERAGE_EXTENSION_V2.json)')
    text=text.replace('A common-mask alias can reuse a full-source canonical score because its points/losses are identical; the[context coverage extension](CONTEXT_COVERAGE_EXTENSION_V2.json) supplies the conditional denominator separately. The full-source unavailable count must not disappear when showing a paired overlap.','A canonical record can retain its first-emitted conditional-view denominator because identical point/loss masks are deduplicated. The[context coverage extensionV2](CONTEXT_COVERAGE_EXTENSION_V2.json) supplies each view’s own denominator, including84for both focal OWNviews. Canonical100%conditional support must not be presented as complete outer-offer coverage. Error and selected-state counts are unchanged.')
    readme.write_text(text)
    if sha(source)!=source_sha or sha(vintage)!=vintage_sha:raise ValueError('immutable scores or vintage annotations changed')
    write(out/'CONTEXT_COVERAGE_CORRECTION_RECEIPT_V2.json',dict(at=now(),state='METADATA_ONLY_TWO_OWN_CONTEXT_DENOMINATORS_CORRECTED',code_sha256=sha(__file__),source_score_sha256=source_sha,vintage_annotations_sha256=vintage_sha,old_context_path=old.relative_to(a.root).as_posix(),old_context_sha256=sha(old),new_context_path=new.relative_to(a.root).as_posix(),new_context_sha256=sha(new),context_changes=changes,machine_table_changes=tablechanges,default_view_sha256=sha(default),old_default_view_sha256=sha(backup),readme_sha256=sha(readme),old_readme_sha256=sha(readmeold),new_scores=0,new_metrics=0,new_grades=0,new_model_inference=0,canonical_scores_changed=False))
    print(json.dumps(dict(context_corrections=len(changes),machine_metadata_corrections=len(tablechanges),new_context_sha256=sha(new),default_sha256=sha(default),readme_sha256=sha(readme),scores_unchanged=sha(source)==source_sha,vintage_annotations_unchanged=sha(vintage)==vintage_sha)))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--output',type=Path,required=True);main(p.parse_args())
