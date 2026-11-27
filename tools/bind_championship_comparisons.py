"""Attach already verified paired comparisons to permanent-index records.

No source score rows, forecasts, masks or scientific results change.
"""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'reports/championship-20261030f'
def dump(path,obj):path.write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    bindings={}
    for year in (2026,2025,2024,2023,2022):
        d=BASE/'numerical-v2'/str(year);scores=json.loads((d/'SCORES.json').read_text());pairs={r['comparison_id']:r for r in json.loads((d/'PAIRED_COMPARISONS.json').read_text())}
        mates={(r['comparison_id'],r['role']):r for r in scores};rows=[]
        for i,r in enumerate(scores):
            pair=pairs[r['comparison_id']];candidate=r['role']=='candidate';other=mates[(r['comparison_id'],'comparator'if candidate else'candidate')];a=pair.get('candidate_error'if candidate else'comparator_error');b=pair.get('comparator_error'if candidate else'candidate_error');delta=pair['delta'];delta=delta if candidate or delta is None else-delta
            interval=pair['game_normal95_sensitivity'];interval=interval if candidate or interval is None else[-interval[1],-interval[0]]
            wk=pair['week_interval'];wk=wk if candidate or wk is None else[-wk[1],-wk[0]]
            rows.append(dict(source_row_index=i,comparison=dict(status='PAIRED_RETAINED_ROWS' if pair['n'] and isinstance(a,(float,int)) and isinstance(b,(float,int)) else 'UNESTABLISHED',reason=pair['status'],comparator_procedure_id=other['procedure_id'],comparator_history_regime=other['history_regime'],comparator_product_id=other['product_id'],metric=pair['metric'],candidate_error=a,comparator_error=b,absolute_error_change=delta,relative_error_change=delta/b if delta is not None and isinstance(b,(float,int))and b>0 else None,paired_n=pair['n'],membership_sha256=pair['membership_sha256'],uncertainty=dict(week_clusters=pair['week_clusters'],game_clusters=pair['game_clusters'],week_interval=wk,week_interval_status=pair.get('week_interval_status','NO_SUPPORTED_PAIRED_ROWS'),game_normal95_sensitivity=interval,selection_limit=pair['selection_limit']),source_comparison_id=pair['comparison_id'],cutoff_policy='Same retained matched row cutoff; current-vintage assumedseven-dayavailability',comparison_scope=pair['purpose'])))
        p=d/'COMPARISON_ANNOTATIONS.json';dump(p,dict(identity='source_row_index',source_score_sha256=sha(d/'SCORES.json'),paired_source_sha256=sha(d/'PAIRED_COMPARISONS.json'),rows=rows));bindings[str((d/'SCORES.json').relative_to(ROOT))]=str(p.relative_to(ROOT))
    d=BASE/'category-selector-v2';scores=json.loads((d/'SCORES.json').read_text());pairs={(r['target'],r['policy']):r for r in json.loads((d/'POLICY_PAIRED_COMPARISONS.json').read_text())};bytarget={r['target']:r for r in scores if r['procedure_id'].endswith(':FROZEN_2025_BEST')};rows=[]
    masks=json.loads((d/'EXACT_MASK_ADMISSION.json').read_text());membership={}
    for target in bytarget:
        cells={(m['week'],m['support_sha256'],m['label_values_sha256'])for m in masks if m['season']==2026 and m['target']==target}
        membership[target]=hashlib.sha256(json.dumps(sorted(cells),separators=(',',':')).encode()).hexdigest()
    for i,r in enumerate(scores):
        policy=r['procedure_id'].split(':')[-1];base=bytarget[r['target']];metric='brier'if r['target']=='anytime_td'else'mae';a=r.get(metric);b=base.get(metric);p=pairs.get((r['target'],policy));rows.append(dict(source_row_index=i,comparison=dict(status='PAIRED_RETAINED_ROWS',membership_sha256=membership[r['target']],comparator_procedure_id=base['procedure_id'],comparator_history_regime='H-MULTI',comparator_product_id=base['product_id'],metric=metric,candidate_error=a,comparator_error=b,absolute_error_change=a-b,relative_error_change=(a-b)/b if b>0 else None,paired_n=r['n'],uncertainty=dict(week_clusters=7,week_interval=None,week_interval_status='INSUFFICIENT_WEEK_CLUSTERS',game_interval_status='NOT_ESTIMATED_FROM_AGGREGATE_ONLY_WEEKLY_SCORES'),comparison_scope='Earlier-only chronological selection policy; exposed history, not fresh issuance')))
    p=d/'COMPARISON_ANNOTATIONS.json';dump(p,dict(identity='source_row_index',source_score_sha256=sha(d/'SCORES.json'),rows=rows));bindings[str((d/'SCORES.json').relative_to(ROOT))]=str(p.relative_to(ROOT))
    path=ROOT/'registries/RESULT_ARTIFACTS.json';reg=json.loads(path.read_text())
    for r in reg:
        if r['artifact']in bindings:r['comparison_annotations']=bindings[r['artifact']]
    dump(path,reg);print(json.dumps(dict(annotated_views=1356,source_scores_changed=0,new_grades=0)))
if __name__=='__main__':main()
