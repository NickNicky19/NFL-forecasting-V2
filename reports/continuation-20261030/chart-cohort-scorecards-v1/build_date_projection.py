"""Retained chart-row date coverage only; no new fit/forecast/outcome."""
import collections,csv,gzip,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from nfl_v2.chart_cohorts import canonical,identity

def build(public_root,private_root,chart_private):
    public_root,private_root,chart_private=map(Path,(public_root,private_root,chart_private))
    member={tuple(r['key']):r for r in json.loads(gzip.decompress((private_root/'memberships.json.gz').read_bytes()))}
    records=[];learned=collections.defaultdict(dict)
    with gzip.open(chart_private/'all-chart-predictions.csv.gz','rt',newline='')as h:
        for r in csv.DictReader(h):
            if r['season']!='2026'or int(r['week'])>7:continue
            r['week']=int(r['week']);r['actual']=None if r['actual']==''else float(r['actual']);r['prediction']=None if r['prediction']==''else float(r['prediction']);records.append(r)
            k=r['procedure_id'],r['product_id'],r['target'],r['population'];values=learned[k].setdefault(r['history_regime'],set())
            if r['fallback']=='none'and r['actual']is not None and r['prediction']is not None:values.add(identity(r))
    core=('H-CURRENT','H-RECENT','H-MULTI');three={k:set.intersection(*(a.get(x,set())for x in core))for k,a in learned.items()};shared=set.intersection(*(s for a in learned.values()for s in a.values()))
    groups=collections.defaultdict(lambda:dict(forecast=set(),actual=set(),offered=0,scored=0))
    for r in records:
        k=r['procedure_id'],r['product_id'],r['target'],r['population'];key=identity(r);views=['full_system']
        if r['fallback']=='none':views.append('own_learned_only')
        if key in three[k]:views.append('three_history_learned_overlap')
        if key in shared:views.append('all_competitor_learned_overlap')
        for cohort in member[key]['cohorts']:
            for view in views:
                g=groups[(*k,r['history_regime'],cohort,view)];g['forecast'].add(r['week']);g['offered']+=1
                if r['actual']is not None and r['prediction']is not None:g['actual'].add(r['week']);g['scored']+=1
    source=public_root/'SCORES.json';scores=json.loads(source.read_bytes());output=[];different=0
    dims=('procedure_id','product_id','target','population','history_regime','cohort_id','fallback_view')
    for i,s in enumerate(scores):
        g=groups.pop(tuple(s[k]for k in dims))
        if g['offered']!=s['forecast_rows']or g['scored']!=s['n']:raise ValueError('chartviewdatecountmismatch')
        actual=sorted(g['actual']);different+=actual!=s['evaluation_weeks']
        output.append(dict(source_row_index=i,evaluation_seasons=[2026],evaluation_weeks=actual,actual_scored_weeks=actual,forecast_query_weeks=sorted(g['forecast']),registered_panel_weeks=list(range(1,8)),dimensions={k:s[k]for k in dims}))
    if groups:raise ValueError('ungroupeddateviews')
    result=dict(source_score_artifact=source.resolve().relative_to(ROOT).as_posix(),source_score_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),source_row_unit='zero-based index in immutable sourceSCORES.json',date_definition='Actualsupportedchartoutcomeweeks versus allforecastqueryweeks; registeredpanelW1-W7doesnotimplyeverylearnedsubsetcoversallweeks',views_where_registered_score_query_weeks_differ_from_supported_outcome_weeks=different,rows=output)
    with(public_root/'SCORE_DATE_PROJECTION.json').open('xb')as h:h.write(canonical(result))
    return dict(date_views=len(output),query_vs_actual_week_differences=different,source_score_sha256=result['source_score_sha256'])

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser()
    for arg in('public-root','private-root','chart-private'):p.add_argument('--'+arg,type=Path,required=True)
    print(json.dumps(build(**vars(p.parse_args()))))
