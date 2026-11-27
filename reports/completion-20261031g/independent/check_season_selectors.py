"""Independent policy-choice arithmetic from bound earlier weekly score rows."""
import argparse
from collections import defaultdict,Counter
from datetime import datetime,timezone
import csv,hashlib,importlib.util,json,math
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np

spec=importlib.util.spec_from_file_location('independent_numeric',Path(__file__).resolve().parents[2]/'championship-20261030f/independent/check_numerical_pairs.py');ind=importlib.util.module_from_spec(spec);spec.loader.exec_module(ind)
sha,canon=ind.sha,ind.canonical
def read(p):return json.loads(p.read_bytes())
def close(a,b):assert math.isclose(a,b,abs_tol=2e-10,rel_tol=2e-10),(a,b)
def key(r):
    target,p,h,v=ind.model(r);return target,p,v
def stable(k):return'|'.join(k)
def weighted(weekly,k,weeks):
    rows=[weekly[stable(k)][str(w)]for w in weeks];return math.fsum(int(r['n'])*float(r['brier'if k[0]=='anytime_td'else'mae'])for r in rows),sum(int(r['n'])for r in rows)
def choose(keys,terms):
    values={}
    for k in keys:
        vals=[weighted(weekly,k,weeks)for weekly,weeks in terms];values[k]=math.fsum(v for v,n in vals)/sum(n for v,n in vals)
    best=min(values.values());return min((k for k,v in values.items()if abs(v-best)<=1e-12),key=stable)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',type=Path,required=True);ap.add_argument('--schedule',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();base=a.repo_root/'reports/completion-20261031g/season-selector';reports=[]
    with a.schedule.open()as f:schedule=list(csv.DictReader(f))
    for folder in('2025','2024-resume-v2','2023'):
        out=base/folder;p=read(out/'FROZEN_PROTOCOL.json');receipt=read(out/'RUN_RECEIPT.json');assert sha(out/'FROZEN_PROTOCOL.json')==receipt['protocol_sha256']and sha(out/'SCORES.json')==receipt['score_sha256']and sha(out/'EXACT_MASK_ADMISSION.json')==receipt['mask_sha256'];assert sha(a.schedule)==p['schedule_sha256'];year=p['evaluation_season'];assert p['prior_season']==year-1
        roster={tuple(k)for k in p['roster']};assert len(roster)==120;source_rows={}
        for binding in p['source_aggregates']:
            file=a.repo_root/binding['path'];assert sha(file)==binding['sha256']
            for raw in read(file):
                if raw.get('history_regime')!='H-MULTI'or raw.get('population')!='primary'or raw.get('position')not in(None,'','ALL')or raw.get('fallback_view')not in(None,'','ALL')or raw.get('cohort_id')or not isinstance(raw.get('week'),int)or not 1<=raw['week']<=18:continue
                if 'season-2025-v1' in binding['path']and'qb-rb-specialization'in raw['procedure_id']:continue
                k=key(raw)
                if k in roster:source_rows[int(raw['season']),k,raw['week']]=dict(raw,source_artifact=binding['path'])
        for y,which in((year-1,'weekly_prior'),(year,'weekly_current')):
            for k in roster:
                for w in range(1,19):assert p[which][stable(k)][str(w)]==source_rows[y,k,w]
        clocks=defaultdict(list)
        for r in schedule:
            if r['game_type']=='REG'and int(r['season'])in(year-1,year)and 1<=int(r['week'])<=18:
                clock=datetime.fromisoformat(r['gameday']+'T'+r['gametime']).replace(tzinfo=ZoneInfo('America/New_York')).timestamp();clocks[int(r['season']),int(r['week'])].append(clock)
        for(y,w),values in clocks.items():assert p['origins'][f'{y}-{w}']==min(values)and p['week_score_available'][f'{y}-{w}']==max(values)+604800
        masks=read(out/'EXACT_MASK_ADMISSION.json');assert len(masks)==4320;group=defaultdict(set)
        for r in masks:group[r['season'],r['target'],r['week']].add((r['query_sha256'],r['support_sha256'],r['label_values_sha256'],r['query_n'],r['supported_n']))
        assert len(group)==432 and all(len(values)==1 for values in group.values())
        decisions={(r['target'],r['policy'],r['week']):r for r in read(out/'DECISIONS.json')};scores={(r['target'],r['procedure_id'].rsplit(':',1)[1]):r for r in read(out/'SCORES.json')};bytarget=defaultdict(list)
        for k in roster:bytarget[k[0]].append(k)
        weekly={};policies=p['policies']
        for target,keys in bytarget.items():
            baseline=next(k for k in keys if ':ordered_leaf_cdf'in k[1]and k[2]==('event_probability'if target=='anytime_td'else'lower_median'))
            for policy in policies:
                picked=[]
                for w in range(1,19):
                    eligible=[u for u in range(1,w)if max(clocks[year,u])+604800<min(clocks[year,w])]
                    if policy==policies[0]:chosen=choose(keys,[(p['weekly_prior'],range(1,19))])
                    elif policy==policies[1]:chosen=choose(keys,[(p['weekly_current'],eligible)])if eligible else baseline
                    else:chosen=choose(keys,[(p['weekly_prior'],range(1,19)),(p['weekly_current'],eligible)])
                    d=decisions[target,policy,w];assert(d['chosen_procedure_id'],d['chosen_product_id'])==chosen[1:];assert d['eligible_current_score_weeks']==eligible and d['fit_origin_unix']==min(clocks[year,w]);assert d['startup']==(policy==policies[1]and not eligible);r=p['weekly_current'][stable(chosen)][str(w)];close(d['loss'],float(r['brier'if target=='anytime_td'else'mae']));picked.append(r)
                n=sum(int(r['n'])for r in picked);total=math.fsum(int(r['n'])*float(r['brier'if target=='anytime_td'else'mae'])for r in picked);score=scores[target,policy];assert score['n']==n;close(score['brier'if target=='anytime_td'else'mae'],total/n);assert score['fallback_rows']==sum(int(r.get('fallback_rows')or 0)for r in picked);precision=defaultdict(lambda:[0,0])
                for r in picked:
                    for name,v in r.get('precision_counts',{}).items():
                        num,den=v if isinstance(v,list)else(v['numerator'],v['denominator']);precision[name][0]+=num;precision[name][1]+=den
                for name,v in score['precision_counts'].items():assert(v['numerator'],v['denominator'])==tuple(precision[name])
                weekly[target,policy]=picked
        paired=read(out/'PAIRED_COMPARISONS.json');assert len(paired)==24
        for r in paired:
            target,policy=r['target'],r['policy'];picked=weekly[target,policy];control=weekly[target,policies[0]];sums=[int(v['n'])*(float(v['brier'if target=='anytime_td'else'mae'])-float(control[i]['brier'if target=='anytime_td'else'mae']))for i,v in enumerate(picked)];counts=[int(v['n'])for v in picked];close(r['delta'],math.fsum(sums)/sum(counts));draw=np.random.Generator(np.random.PCG64(1703)).integers(18,size=(500,18));weights=np.array([np.bincount(v,minlength=18)for v in draw]);sample=(weights@np.array(sums))/(weights@np.array(counts));bounds=np.percentile(sample,[2.5,97.5],method='linear')
            for expected,actual in zip(bounds,r['week_interval']):close(expected,actual)
        counts=Counter('WIN'if r['delta']<0 else'LOSS'if r['delta']>0 else'TIE'for r in paired if r['policy']==policies[1]);carry=next(r for r in paired if r['target']=='rush_att'and r['policy']==policies[1]);reports.append(dict(season=year,protocol_sha256=receipt['protocol_sha256'],score_sha256=receipt['score_sha256'],recipes=120,weekly_source_aggregate_cells_verified=4320,hashed_query_support_label_value_admissions_checked=len(masks),choices_verified=len(decisions),score_views_verified=len(scores),paired_week_bootstraps_verified=len(paired),current_score_memory_vs_fixed_prior=dict(counts),carry_paired_delta=carry['delta'],carry_week_interval=carry['week_interval']))
    # Recompute the generic pure choice rule on every frozen2026 decision too.
    f=read(a.repo_root/'reports/championship-20261030f/category-selector-v2/FROZEN_PROTOCOL.json');dec=read(a.repo_root/'reports/championship-20261030f/category-selector-v2/DECISIONS.json');ks=defaultdict(list)
    for k in f['roster']:ks[k[0]].append(tuple(k))
    for r in dec:
        keys=ks[r['target']];eligible=r['current_score_weeks_available'];basekey=next(k for k in keys if ':ordered_leaf_cdf'in k[1]and k[2]==('event_probability'if k[0]=='anytime_td'else'lower_median'))
        if r['policy_id']=='FROZEN_2025_BEST':chosen=choose(keys,[(f['weekly2025'],range(1,19))])
        elif r['policy_id']=='EARLIER_AVAILABLE_2026_SCORE_MEMORY':chosen=choose(keys,[(f['weekly2026'],eligible)])if eligible else basekey
        else:chosen=choose(keys,[(f['weekly2025'],range(1,19)),(f['weekly2026'],eligible)])
        assert chosen[1:]==(r['chosen_procedure_id'],r['chosen_product_id'])
    report=dict(state='PASS_INDEPENDENT_SEASON_RELATIVE_SELECTOR_SOURCE_AGGREGATES_CHOICES_AND_UNCERTAINTY',at=datetime.now(timezone.utc).isoformat(),seasons=reports,F2026_choice_lineage_parity=252,new_fits=0,new_inference=0,new_forecasts=0,new_NFL_observations=0,scope='Allnew choices/weighted metrics/precision and24whole-week comparisons perseason independently recomputed from hash-bound source weekly aggregates. Every published mask hash and its across-recipe equality checked; this check does not rescan all raw model predictions. Prior F independent receipts document raw-row numerical/selector replay coverage.',limits=['Current-score memory selects historically trained H-MULTI recipes; not strictcurrent NFL information.','All seasons exposed reconstructed evidence, never original issued policy or fresh holdout.','Source/current score availability uses inherited last-kickoff+7day assumption.'])
    with a.output.open('x')as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps(report))


if __name__=='__main__':main()
