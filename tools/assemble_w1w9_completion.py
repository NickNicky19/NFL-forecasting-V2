"""Aggregate already-graded, disjoint source masks; never manufacture private rows."""
from __future__ import annotations
import collections, copy, hashlib, json, math, pathlib
import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE = ROOT / 'reports/w1w9-comparison-closure-01/B'
OUT = BASE / 'nine-week-completion'
POLICIES = {'mean':'P1_MEAN','lower_median':'P1_LOWER_MEDIAN','P2':'P2_STATISTICAL_LAW'}
PANEL = 'ABC-W1W9-CMP-ANNUAL1_4-NATIVE5_9-DIAGNOSTIC-v1'

def read(p): return json.loads((BASE/p).read_text())
def write(p,x): p.write_text(json.dumps(x,indent=2,sort_keys=True,allow_nan=False)+'\n')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def num(x): return None if x is None or x == '' else float(x)

def normalize_old(r):
    q = {'week_view':r['week_view'], 'eligible':int(r['eligible']), 'unavailable':int(r['unavailable']),
         'abstentions':int(r['abstained']), 'games':int(r['games']), 'player_games':int(r['player_games'])}
    for s in ('OVER','UNDER','COMBINED'):
        k=s.lower(); d=int(r[k+'_decided']);w=int(r[k+'_wins'] or 0);l=int(r[k+'_losses'] or 0)
        q[s]={'selected':d,'wins':w if d else None,'losses':l if d else None,'decided':d,'rate':w/d if d else None}
    q['numerical']={'scored':int(r['numeric_scored']), **{k:num(r['numeric_'+k]) for k in ('MAE','MSE','bias','max_absolute_error')}}
    q['probability']={'events':int(r['law_events']), **{k:num(r['law_'+k]) for k in ('Brier','three_state_log_loss')}, 'infinite_log_loss_cases':int(r['law_infinite_log_loss_cases'])}
    q['fallback_states']=json.loads(r['source_fallback_flags'])
    q['states']={s:int(r[s]) for s in ('UNKNOWN_PARTICIPATION','MISSING_ACTUAL','DNP','PENDING','PUSH')}
    q['eligible_mask_sha256']=r['eligible_mask_sha256']
    return q

def merge(parts, model, proc, policy, view, board_eligible=None, missing=None):
    q={'model_key':model,'procedure_id':proc,'policy':policy,'week_view':view,
       'evaluation_panel_id':PANEL,'season':2026,'category':'pass_cmp','target':'pass_cmp',
       'record_kind':'actual_offer_direction_evaluation','source_vintage':'CURRENT_VINTAGE_CHRONOLOGICAL_RECONSTRUCTION',
       'evidence_tier':'TIER_B_RETAINED_ACTUAL_SOURCE_LINES;QUOTE_CLOCK_UNKNOWN;MAIN_ALT_UNCLASSIFIED',
       'primary_admission':'LOCAL_B_RECOMMENDATION_NOT_C_ADMITTED_OR_PRODUCTION',
       'aggregation':'DISJOINT_FIXED_WEEK_MASKS;EARLY_PUBLIC_OWNER_AGGREGATES_PLUS_NATIVE_ROW_GRADES'}
    q['eligible']=sum(r['eligible'] for r in parts) if board_eligible is None else board_eligible
    q['available']=sum(r['eligible']-r.get('unavailable',0) for r in parts)
    q['unavailable']=q['eligible']-q['available']
    q['abstentions']=sum(r.get('abstentions',0) for r in parts)
    for s in ('OVER','UNDER','COMBINED'):
        a={k:sum((r[s].get(k) or 0) for r in parts) for k in ('selected','wins','losses','decided')}
        a['rate']=a['wins']/a['decided'] if a['decided'] else None
        if not a['decided']:a['wins']=a['losses']=None
        q[s]=a
    q['selected']=q['COMBINED']['selected'];q['decided']=q['COMBINED']['decided']
    q['unknown']=q['selected']-q['decided']-sum(r.get('states',{}).get('PUSH',0) for r in parts)
    q['games']=sum(r['games'] for r in parts);q['player_games']=sum(r['player_games'] for r in parts)
    q['actual_weeks']=sorted({int(r.get('week_view',r.get('week'))) for r in parts})
    q['distinct_scored_weeks']=[int(r.get('week_view',r.get('week'))) for r in parts if r['COMBINED']['decided']]
    q['nine_week_coverage_status']='NINE_WEEKS_REPRESENTED_PARTIAL_WITHIN_WEEK_BOARD' if q['actual_weeks']==list(range(1,10)) and not q['unavailable'] else 'PARTIAL'
    q['coverage']=q['available']/q['eligible'] if q['eligible'] else None
    q['fallback_states']=dict(sum((collections.Counter(r.get('fallback_states',{})) for r in parts),collections.Counter()))
    q['fallback_interpretation']='Blank source flags mean UNKNOWN attribution, not learned-only. none means recorded no fallback.'
    q['unavailable_reasons']={missing:q['unavailable']} if missing and q['unavailable'] else {}
    nr=[r['numerical'] for r in parts if r.get('numerical',{}).get('scored',0)]
    n=sum(r['scored'] for r in nr)
    q['numerical']={'scored':n,**{k:sum(r['scored']*r[k] for r in nr)/n if n else None for k in ('MAE','MSE','bias')},
                    'max_absolute_error':max((r['max_absolute_error'] for r in nr),default=None),
                    'absolute_error_p90':None,'quantile_missing_reason':'Cannot reconstruct a pooled error quantile from private early aggregates.'}
    if q['numerical']['MSE'] is not None:q['numerical']['RMSE']=math.sqrt(q['numerical']['MSE'])
    pr=[r['probability'] for r in parts if r.get('probability',{}).get('events',0)]
    n=sum(r['events'] for r in pr)
    q['probability']={'events':n,'Brier':sum(r['events']*r['Brier'] for r in pr)/n if n else None,
      'binary_event':'STRICT_Y_GREATER_THAN_LINE;PUSH_IS_NOT_OVER',
      'three_state_log_loss':sum(r['events']*r['three_state_log_loss'] for r in pr)/n if n else None,
      'infinite_log_loss_cases':sum(r.get('infinite_log_loss_cases',0) for r in pr),
      'three_state_Brier':None,'Over_event_AUC':None,
      'missing_metric_reason':'Full-panel three-state Brier and AUC cannot be reconstructed from the early retained sufficient statistics.',
      'conditioning':'Retained modeled-appearance law, qualified PLAYED statistical labels; venue settlement not authenticated.'}
    bins=collections.defaultdict(lambda:[0,0.,0.]); complete_bins=True
    for r in pr:
        if 'reliability_fixed_binsOver' in r:
            for b in r['reliability_fixed_binsOver']:
                if b['n']:
                    a=bins[round(b['lower']*10)];a[0]+=b['n'];a[1]+=b['n']*b['mean_predicted'];a[2]+=b['n']*b['observed_over']
        elif 'reliability_fixed_bins' in r:
            for b in r['reliability_fixed_bins']:
                a=bins[b['bin_index']];a[0]+=b['count'];a[1]+=b['count']*b['predicted_Over'];a[2]+=b['count']*b['observed_Over']
        else:complete_bins=False
    q['probability']['binary_Over_reliability_bins']=[] if not complete_bins else [
      {'lower':k/10,'upper':(k+1)/10,'n':v[0],'mean_predicted':v[1]/v[0],'observed_over':v[2]/v[0]} for k,v in sorted(bins.items()) if v[0]]
    q['probability']['reliability_scope']='BINARY_OVER_EVENT;NOT_SELECTED_SIDE_CONFIDENCE' if complete_bins else 'EARLY_BIN_STATISTICS_NOT_RETAINED_FOR_THIS_PRODUCT'
    q['states']=dict(sum((collections.Counter(r.get('states',{})) for r in parts),collections.Counter()))
    q['source_part_commitments']=[r.get('membership_SHA256',r.get('eligible_mask_sha256')) for r in parts]
    if len(parts)>=6:
        rng=np.random.default_rng(1703); vals=[]
        for _ in range(500):
            ix=rng.integers(0,len(parts),len(parts));den=sum(parts[i]['COMBINED']['decided'] for i in ix)
            if den:vals.append(sum(parts[i]['COMBINED']['wins'] or 0 for i in ix)/den)
        q['uncertainty']={'kind':'WHOLE_WEEK_WEIGHTED_BOOTSTRAP','seed':1703,'draws':500,'week_clusters':len(parts),'low':float(np.quantile(vals,.025)),'high':float(np.quantile(vals,.975)),
                          'limits':'Nominal exposed-development interval; nine limited clusters, repeated candidate selection, no multiplicity adjustment.'}
    else:q['uncertainty']={'kind':'PARTIAL_FEW_WEEK_SCOPE;SEE_SOURCE_RECORDS'}
    q['record_id']='B-W1W9-CMP-'+hashlib.sha256(f'{proc}|{policy}|{view}'.encode()).hexdigest()[:24]
    return q

def main():
    OUT.mkdir(exist_ok=True)
    early=read('receipt-union/A84_PUBLIC_ARITHMETIC_AND_SCOPE_V1.json')['records']
    native=read('native-completion-scoring/NATIVE_TABLES.json')
    r0=read('receipt-union/EXISTING_R0_R3_EARLY_WEEKLY_VIEWS_V1.json')['rows']
    f2=read('receipt-union/EXISTING_F2_EARLY_WEEKLY_VIEWS_V1.json')['records']
    parts_by={};tables=[]
    for model in ('B0','B1','B2','E3','F2','ALWAYS_OVER','ALWAYS_UNDER'):
        outputs=('direction',) if model.startswith('ALWAYS') else tuple(POLICIES)
        for output in outputs:
            policy='REGISTERED_DIRECTION' if output=='direction' else POLICIES[output]
            if model in ('B0','B1','B2'):
                ep=[copy.deepcopy(r) for r in early if r['candidate_id']==f'B-FTN-BALL-QUALITY-COMPLETION-v1:{model}::{output}' and r['week_view']!='ALL']
            elif model=='E3':ep=[normalize_old(r) for r in r0 if r['candidate_id']==f'B-QB-OPPORTUNITY-PROFILE-INCREMENT-v1:R0::{output}']
            elif model=='F2':ep=[dict(copy.deepcopy(r),week_view=str(r['week'])) for r in f2 if r['candidate_id']==f'B-QB-ALIGNED-FRESHNESS-v1:F2::{output}']
            else:ep=[copy.deepcopy(r) for r in early if r['candidate_id']==model and r['week_view']!='ALL']
            lp=[copy.deepcopy(r) for r in native if r['model_key']==model and r['policy']==policy and r['week_view'] in list(map(str,range(5,10)))]
            assert len(ep)==4 and len(lp)==5,(model,output,len(ep),len(lp))
            ep.sort(key=lambda r:int(r['week_view']));lp.sort(key=lambda r:int(r['week_view']))
            proc=lp[0]['procedure_id'];parts=ep+lp;parts_by[(model,policy)]=parts
            tables.append(merge(parts,model,proc,policy,'ALL'))
            tables.extend(merge([r],model,proc,policy,r['week_view']) for r in parts)
            dk=[r for r in native if r['model_key']==model and r['policy']==policy and r['week_view']=='DK_ONLY']
            assert len(dk)==1
            # Annual book names are unbound: this is exclusion of the native Sleeper row, NOT all-DK.
            fake=copy.deepcopy(dk[0]);fake['week_view']='5'
            sensitivity=merge(ep+[fake],model,proc,policy,'ANNUAL_PLUS_NATIVE_DK_ONLY')
            sensitivity['actual_weeks']=list(range(1,10));sensitivity['distinct_scored_weeks']=list(range(1,10))
            sensitivity['uncertainty']={'kind':'SEE_INDEPENDENT_NINE_WEEK_PAIRED_SENSITIVITY;NOT_FIVE_PSEUDO_CLUSTERS'}
            sensitivity['source_scope']='Annual84 book-name-unbound plus native141 DraftKings; excludes only one native Sleeper row.'
            sensitivity['nine_week_coverage_status']='NINE_WEEKS_REPRESENTED_PARTIAL_WITHIN_WEEK_BOARD'
            tables.append(sensitivity)
    # Preserve A early contenders visibly against the complete declared 226-opportunity board.
    for cid in sorted({r['candidate_id'] for r in early if r['candidate_id'].startswith('A::')}):
        ep=[r for r in early if r['candidate_id']==cid and r['week_view']!='ALL']
        tables.append(merge(ep,'A_PARTIAL',cid,'SAVED_POINT_STRICT_LINE','ALL',226,'A_W5_W9_EXACT_FORECASTS_OWNER_LOCAL_NOT_SUPPLIED'))
    allrows=[r for r in tables if r['week_view']=='ALL' and r['nine_week_coverage_status'].startswith('NINE') and not r['model_key'].startswith('ALWAYS')]
    best=max(r['COMBINED']['rate'] for r in allrows)
    leaders=[r for r in allrows if r['COMBINED']['rate']==best and r['model_key']!='B1']
    sides={s:[r for r in allrows if r['model_key']!='B1' and r[s]['decided'] and r[s]['rate']==max(z[s]['rate'] for z in allrows if z[s]['decided'])] for s in ('OVER','UNDER')}
    decision={'id':'B_W1W9_COMPLETION_DECISION_V1','panel':PANEL,'eligible':226,'games':119,'scheduled_games':136,'weeks':list(range(1,10)),
      'highest_observed_complete_compared_products':[{'procedure':r['procedure_id'],'policy':r['policy'],'OVER':r['OVER'],'UNDER':r['UNDER'],'COMBINED':r['COMBINED']} for r in leaders],
      'descriptive_own_side_maxima_no_router':{s:[{'procedure':r['procedure_id'],'policy':r['policy'],'record':r[s]} for r in rs] for s,rs in sides.items()},
      'recommendation':'SHADOW;NO_QUALIFIED_REPLACEMENT_ESTABLISHED',
      'global_ABC_championship_status':'PARTIAL: A strongest early controls lack142 later exact forecasts; C has no admitted completion member; incumbent history unavailable.',
      'target_90_broad_board':'TARGET_NOT_ESTABLISHED','target_90_selective':'TARGET_NOT_ESTABLISHED; early complete selected-membership evidence missing; native frozen policies reported separately.',
      'duration':'Nine diagnostic blocks for exact complete products; not source-clock authentication or automatic operational admission.',
      'same_method_conclusion':'B2 mean112/226 loses to B0 mean119/226; B2 median/law122 beats own B0 median/law117 by5. Not a blanket information improvement.',
      'control_conclusion':'B2 median/law versus AlwaysOver115/226: observed+7, paired interval includes no advantage; no established modeled superiority.',
      'no_new_source_or_games':'Reuse of A84 and native142; additional exact-procedure coverage, not new games or new original pregame selections.',
      'private_scope':'A early public commitments/arithmetic checked; private raw rows/source clocks/models not independently inspected.'}
    write(OUT/'TABLES.json',tables)
    write(OUT/'SCORES.json',[r for r in tables if r['model_key']!='B1'])
    independent=read('receipt-union/INDEPENDENT_COMBINED_FTN_NINE_WEEK_V1.json')
    pairs=copy.deepcopy(independent['paired_week_analyses'])
    leader_parts=parts_by[('B2','P1_LOWER_MEDIAN')]
    for model,policy in [('E3','P1_MEAN'),('E3','P1_LOWER_MEDIAN'),('F2','P1_MEAN'),('F2','P1_LOWER_MEDIAN'),('B0','P1_MEAN')]:
        control=parts_by[(model,policy)]; sums=[]
        for a,b in zip(leader_parts,control):
            assert a['eligible']==b['eligible'] and a['COMBINED']['decided']==b['COMBINED']['decided']
            sums.append({'week':int(a['week_view']),'loss_difference_sum':b['COMBINED']['wins']-a['COMBINED']['wins'],'n':a['COMBINED']['decided']})
        rng=np.random.default_rng(1703);draws=[]
        for _ in range(500):
            ii=rng.integers(0,9,9);draws.append(sum(sums[i]['loss_difference_sum'] for i in ii)/sum(sums[i]['n'] for i in ii))
        cw=sum(r['COMBINED']['wins'] for r in leader_parts);bw=sum(r['COMBINED']['wins'] for r in control)
        pairs.append({'sensitivity':'FIXED226_ALL_SOURCES','left':'B-FTN-BALL-QUALITY-COMPLETION-v1:B2::lower_median',
          'right':control[-1]['procedure_id']+'::'+policy,'n':226,'candidate_wins':cw,'comparator_wins':bw,'accuracy_change':(cw-bw)/226,
          'loss_difference_interval95':[float(np.quantile(draws,.025)),float(np.quantile(draws,.975))],
          'accuracy_difference_interval95':[-float(np.quantile(draws,.975)),-float(np.quantile(draws,.025))],
          'week_clusters':9,'replicates':500,'seed':1703,'weekly_paired_sums_counts':sums,
          'total_disagreements':None,'disagreement_missing_reason':'Early joint side-membership vectors not supplied; exact weekly win differences and same-mask commitments suffice for this paired week accuracy contrast, not row disagreement reconstruction.',
          'game_interval':None,'selection_limit':'Exposed retrospective candidate choice; nominal nine-week interval, no multiplicity adjustment.'})
    write(OUT/'PAIRED_COMPARISONS.json',pairs)
    write(OUT/'DECISION_V1.json',decision)
    write(OUT/'INPUT_BINDINGS_V1.json',{'inputs':{str(p.relative_to(ROOT)):sha(p) for p in [BASE/'receipt-union/A84_PUBLIC_ARITHMETIC_AND_SCOPE_V1.json',BASE/'receipt-union/EXISTING_R0_R3_EARLY_WEEKLY_VIEWS_V1.json',BASE/'receipt-union/EXISTING_F2_EARLY_WEEKLY_VIEWS_V1.json',BASE/'native-completion-scoring/NATIVE_TABLES.json']},'code_sha256':sha(pathlib.Path(__file__)),
      'probability_contract':'Before aggregation, harmonize native Brier to the already-reported A strict-binary-Over Brier; no new predictions or regrades. Three-state logloss identical. Full9 AUC/three-stateBrier/pooled error quantiles unavailable.',
      'score_views':len(tables),'canonical_score_views':sum(r['model_key']!='B1' for r in tables),'no_new_fits':True})
    print(json.dumps({'tables':len(tables),'canonical':sum(r['model_key']!='B1' for r in tables),'leader':decision['highest_observed_complete_compared_products']},indent=2))

if __name__=='__main__':main()
