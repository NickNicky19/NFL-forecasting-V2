"""Projection of existing B evidence; no fitting, inference, grading or ranker."""
from pathlib import Path
import collections, csv, hashlib, json, time
from datetime import datetime, timezone

ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).resolve().parent
CAT=('pass_yd','pass_td','pass_cmp','pass_att','pass_int','rush_yd','rush_att','rec','rec_yd','rush_rec_yd','anytime_td','nick-chart-ppr-v1')
bindings={}
def read(p):
    p=Path(p);body=(ROOT/p).read_bytes();bindings[str(p)]={'path':str(p),'sha256':hashlib.sha256(body).hexdigest(),'bytes':len(body)}
    return json.loads(body)
def save(name,x):
    p=OUT/name
    if p.exists():raise FileExistsError(name)
    p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def sides(rows,r):
    fields=('procedure_id','history_regime','product_id','target','cohort_id','K','rank_scope','week')
    z={str(x['side']):x for x in rows if all(x.get(k)==r.get(k)for k in fields)and x.get('record_kind')=='prop_selection_evaluation'}
    out={}
    for side in ('over','under','Combined'):
        x=z.get(side)
        if x:
            s=x['selection_metrics'];d=s['denominators']['decided'];out[side]={'wins':s['WIN'],'losses':s['LOSS'],'decided':d,'rate':s['WIN']/d if d else None}
    return out
def projection(r,rows,path):
    s=r['selection_metrics'];d=s['denominators']['decided'];return dict(category=r['target'],procedure_id=r['procedure_id'],history=r.get('history_regime'),product=r['product_id'],policy=r.get('decision_rule',r.get('strategy')),weeks=r.get('evaluation_weeks'),sides=sides(rows,r),eligible=s.get('selection_pool_count'),available=s.get('admitted_forecast_opportunities',s.get('eligible_rank_pool_n')),selected=r.get('forecast_rows'),unknown=s.get('denominators',{}).get('unresolved'),unavailable=s.get('unavailable_forecast_opportunities',s.get('technical_unavailable')),fallback=s.get('selected_side_fallback_count',s.get('fallback_issued')),fallback_scope=r.get('fallback_count_scope',s.get('fallback_scope','Not separately supplied in this cumulative record')),games=r.get('unique_games'),player_games=r.get('unique_player_games'),uncertainty=s.get('game_uncertainty'),source=dict(path=path,record_id=r['record_id']),source_records=r.get('source_records',[]),new_observations=0)

def main():
    start=time.process_time();OUT.mkdir(parents=True,exist_ok=True)
    ptr=read('registries/CURRENT_RESULTS_INDEX.json');manifest=read(ptr['manifest']);reg=read('registries/RESULT_ARTIFACTS.json')
    census=read('reports/completion-20261031g/roster/finite-v2/ROSTER_RECONCILIATION_RECEIPT.json')
    native=read(ptr['procedure_rankings']['path']);dur=read('reports/execution-closure-02/B/B_CATEGORY_PRODUCT_QUALIFICATION_CORRECTION_V2.json')
    catdec=read('reports/baselines-coverage-20261031h/CATEGORY_DECISIONS.json');catalog=read('reports/METHOD_YEAR_INVENTORY.json')
    p1path='reports/baselines-coverage-20261031h/probability/w5-w7-cumulative-v1/SCORES.json';p2path='reports/baselines-coverage-20261031h/probability/w5-w7-primary-p2-v1/SCORES.json'
    p1=read(p1path);p2=read(p2path);pools=[(p1path,p1),(p2path,p2)]
    scope=[];coverage=[];weekrefs=collections.defaultdict(list);leaders=[];all_candidates=[]
    for path,rows in pools:
        chosen=[r for r in rows if r.get('record_kind')=='prop_selection_evaluation'and r.get('side')=='Combined'and r.get('cohort_id')=='ALL'and r.get('K')is None]
        for r in chosen:
            z=projection(r,rows,path);z['panel']='B_NATIVE_ROLLING_W5_W7';all_candidates.append(z)
            for ref in r.get('source_records',[]):weekrefs[ref['source_artifact']].append((z,ref))
        for cat in CAT:
            rr=[r for r in chosen if r['target']==cat and r['selection_metrics']['denominators']['decided']]
            if rr:
                best=max(r['selection_metrics']['WIN']/r['selection_metrics']['denominators']['decided']for r in rr)
                for r in rr:
                    if r['selection_metrics']['WIN']/r['selection_metrics']['denominators']['decided']==best:
                        z=projection(r,rows,path);z.update(panel='B_NATIVE_ROLLING_W5_W7',kind='RAW_OBSERVED_OWN_POOL_MAXIMUM_NOT_RELEASE_RECOMMENDATION');leaders.append(z)
    # Resolve only already published aggregate rows; no private outcomes read.
    for path,refs in weekrefs.items():
        rows=read(path)
        for parent,ref in refs:
            r=rows[ref['source_row_index']]
            assert r['record_id']==ref['record_id']
            s=r['selection_metrics'];w=int(r.get('week')or r['evaluation_weeks'][0]);d=s['denominators']['decided']
            coverage.append(dict(panel='B_NATIVE_ROLLING_W5_W7',category=parent['category'],procedure_id=parent['procedure_id'],history=parent['history'],product=parent['product'],policy=parent['policy'],season=2026,week=w,state='SCORED_EXISTING_DIRECTION'if d else'ATTEMPTED_NO_DECIDED_OUTCOMES',eligible=s.get('selection_pool_count'),available=s.get('admitted_forecast_opportunities'),selected=r.get('forecast_rows'),decided=d,wins=s['WIN'],losses=s['LOSS'],unknown=s['denominators'].get('unresolved'),fallback=s.get('fallback_issued',r.get('fallback_rows')),games=r.get('unique_games'),player_games=r.get('unique_player_games'),source_artifact=path,record_id=r['record_id'],offer_timing='SOURCE_SERVER_RETENTION_BEFORE_T90;BOOK_QUOTE_VINTAGE_UNAUTHENTICATED',forecast_chronology='KNOWN_TARGET_TIME_SAVED_VECTOR_RECONSTRUCTION;NOT_ORIGINAL_ISSUE',horizon=r.get('horizon_id')))
    for parent in all_candidates:
        for w in (1,2,3,4,8):coverage.append(dict(panel='B_NATIVE_ROLLING_W5_W7',category=parent['category'],procedure_id=parent['procedure_id'],history=parent['history'],product=parent['product'],policy=parent['policy'],season=2026,week=w,state='MISSING_IN_THIS_EXACT_SOURCE_PANEL_NOT_GLOBAL_ABSENCE',eligible=None,available=None,selected=None,decided=None,wins=None,losses=None,unknown=None,fallback=None,games=None,player_games=None,source_artifact=parent['source']['path'],record_id=None,offer_timing='NOT_PROVIDED_BY_THIS_PANEL',forecast_chronology='DO_NOT_BORROW_OTHER_POLICY_OR_SOURCE',horizon=None))
    cb=read('reports/abc-championship/continuation-20261103-v4/B_OWN_POOL_COMBINED_LEADERS.json')
    for r in cb:
        z=dict(r);z['kind']='PUBLISHED_BROAD_C_BOARD_REPRESENTATIVE;RAW_TINY_MAXIMA_SEPARATE';leaders.append(z)
    law=read('reports/abc-championship/leaf-law-continuation-20261104-v2/SIDE_TABLE.json')
    # Include all law-product source/week cells, not just the strongest headline.
    for r in law:
        suffix=r['panel'].rsplit('_',1)[-1]
        if suffix not in ('2','3'):continue
        coverage.append(dict(panel='C_PINNACLE_W2_W3_RETAINED_LEAF_LAW',category=r['target'],procedure_id=r['procedure_id'],history=None,product='EXPLICIT_RETAINED_LEAF_LAW',policy=r['strategy'],season=2026,week=int(suffix),state='SCORED_EXISTING_DIRECTION',eligible=r['eligible'],available=r['combined_selected'],selected=r['combined_selected'],decided=r['combined_decided'],wins=r['combined_wins'],losses=r['combined_losses'],unknown=r['unknown'],fallback=None,games=r['unique_games'],player_games=None,source_artifact='reports/abc-championship/leaf-law-continuation-20261104-v2/SIDE_TABLE.json',record_id=None,offer_timing='TIMING_UNVERIFIED_ACTUAL_PINNACLE_LINES',forecast_chronology='KICKOFF_RECONSTRUCTION_VS_LAST_RECORDED_PREKICK_CLOSE',horizon='KICKOFF_RECONSTRUCTION_VS_LAST_RECORDED_PREKICK_CLOSE'))
    modernpaths=['reports/player-context-matchup-01/B/scores-v1/SCORES.json','reports/profile-increment-to-release-01/B/opportunity-scores-v1/SCORES.json','reports/profile-increment-closure-next-02/B/aligned-scores-v1/SCORES.json']
    modern=[]
    for path in modernpaths:
        if not(ROOT/path).exists():continue
        rows=read(path)
        for r in rows:
            if r.get('record_kind')!='prop_selection_evaluation'or r.get('side')!='Combined'or r.get('cohort_id')!='ALL'or r.get('K')is not None:continue
            z=projection(r,rows,path);z['panel']=r.get('evaluation_panel_id');modern.append(z)
            if isinstance(r.get('week'),int):
                s=r['selection_metrics'];d=s['denominators']['decided'];coverage.append(dict(panel=r.get('evaluation_panel_id'),category=r['target'],procedure_id=r['procedure_id'],history=r.get('history_regime'),product=r['product_id'],policy=r.get('strategy'),season=r['season'],week=r['week'],state='SCORED_EXISTING_DIRECTION'if d else'ATTEMPTED_NO_DECIDED_OUTCOMES',eligible=s.get('selection_pool_count'),available=s.get('eligible_rank_pool_n'),selected=r.get('forecast_rows'),decided=d,wins=s['WIN'],losses=s['LOSS'],unknown=s['denominators'].get('unresolved'),fallback=s.get('fallback_issued'),games=r.get('unique_games'),player_games=r.get('unique_player_games'),source_artifact=path,record_id=r['record_id'],offer_timing='TIMING_UNVERIFIED_ACTUAL_LINE_DIAGNOSTIC',forecast_chronology='CURRENT_REVISED_HISTORICAL_ORIGIN_RECONSTRUCTION',horizon=r.get('horizon_id')))
    for cat in CAT:
        d=next(r for r in catdec if r['category']==cat);nr=[r for r in native if r['category']==cat and r.get('rank')==1];duration=next(r for r in dur['categories']if r['category']==cat)
        scope.append(dict(category=cat,native_numerical_or_event_leaders=nr,native_duration=duration,old_primary_own_pool_direction_maxima=[r for r in leaders if r.get('category',r.get('target'))==cat],offered_status=d['offered_threshold_status'],own_current_direction_decision='NO_B_PRIMARY_DIRECTION_RELEASE_ESTABLISHED_IN_THIS_LOCAL_INDEX;C_COORDINATES_NEW_A_JOIN_AND_OTHER_OWNERS',current_state='B_FROZEN_SHADOW_ONLY_NO_ORIGINAL_SITE_ADMISSION',operational_package=next(r for r in read_cache_packages if r['category']==cat)if False else d['owner_review_package'],remaining=d['remaining_dependency'],scope_limit='Numerical/event leaders and raw own-pool maxima are not global category O/U winners. New A exact-five-week joins are reviewed separately by assigned owner/reviewer.'))
    save('B_TWELVE_CATEGORY_EXISTING_EVIDENCE_V1.json',dict(id='B-CATEGORY-DECISION-EXISTING-EVIDENCE-v1',created_UTC=datetime.now(timezone.utc).isoformat(),B_only_contribution_to_C=True,categories=scope,modern_direction_records=modern,source_notes={'W5_W7':'Own server-retained provider-labelled source before T90; original book quote clocks and sportsbook settlement unestablished. Foreknown-target-time reconstruction is a distinct complete eligibility/feature policy.','C_W2_W3':'Exact Pinnacle source sample; quote timing unverified; same base families do not prove identical earlier-executable policy.','new_A_joins':'Executed per new assignment; independently reviewed elsewhere. Do not reuse stale old four-week status as final five-week determination.'},new_scores=0,new_fits=0))
    save('B_W1_W8_SOURCE_PROCEDURE_COVERAGE_V1.json',dict(id='B-CATEGORY-SOURCE-PROCEDURE-WEEK-COVERAGE-v1',cells=coverage,cells_count=len(coverage),scope='Existing explicit primary products and source strata, not every lifetime/private contender; missing cells in one source are not global absence',new_NFL_observations=0,new_scores=0))
    with (OUT/'B_W1_W8_SOURCE_PROCEDURE_COVERAGE_V1.csv').open('w',newline='')as f:
        fields=list(coverage[0]);writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(coverage)
    save('INVENTORY_REVIEW_SCOPE_V1.json',dict(id='B-FINITE-REGISTERED-INVENTORY-REVIEW-SCOPE-v1',created_UTC=datetime.now(timezone.utc).isoformat(),registered_scored_artifacts=len(reg),indexed_views=manifest['record_count'],native_held_aware_rank_rows=len(native),manifest_bindings_enumerated=len(manifest['input_manifests']),legacy_method_year_records=len(catalog),source_bound_finite_census={k:census[k]for k in ('at','known_scientific_mechanisms','raw_implemented_procedure_strings','normalized_fixed_recipe_procedure_strings','current_procedure_strings','finite_recipe_period_cells','current_fixed_completed','lifetime_census_complete')},current_review=dict(cumulative_primary_source_rows=len(p1)+len(p2),exact_primary_direction_candidates=len(all_candidates),C_board_published_broad_representatives=len(cb),C_retained_law_views=len(law),modern_records_projected=len(modern),coverage_cells=len(coverage)),not_claimed='Every test ever / all private rows / exhaustive rescoring of613572views / new universal ranking',source_bindings=list(bindings.values()),CPU_seconds=time.process_time()-start,new_fits=0,new_inference=0,new_grades=0,new_score_views=0))
    print(json.dumps(dict(categories=len(scope),coverage_cells=len(coverage),sources=len(bindings),CPU_seconds=time.process_time()-start)))

if __name__=='__main__':main()
