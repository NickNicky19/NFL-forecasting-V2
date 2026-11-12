"""Normalize already scored public records, never player/offer grades."""
import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

STEM='reports/abc-championship/profile-timing-closure-and-confirm-01'
REF='d7c8bc619eb7aed93df8259822eb08488d837005'
PANELS=('ANNUAL_NAMED_NJ','SITE_RECORDED_DK_JURISDICTION_UNKNOWN')


def load_rows(folder,prefix):
    result=[]
    for p in sorted(folder.glob(prefix+'*.csv')):result.extend(csv.DictReader(p.open(newline='')))
    return result


def decoded(value):
    if value in ('',None):return None
    try:return json.loads(value)
    except json.JSONDecodeError:return value


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--cache',type=Path,required=True);a=ap.parse_args()
    out=Path(__file__).resolve().parent;cache=a.cache/STEM;created=datetime.now(timezone.utc).isoformat()
    all_primary=[];coverage=[];comparisons=[];leaders=[]
    for category,folder,view,prefix in [('pass_cmp','b-timing-public-v1','FULL_A_BOARD','B-QB-ALIGNED-FRESHNESS-v1:'),('rec','c04-public-v1','FULL_A733','C-RECEIVING-ALIGNED-TIMING-v1::')]:
        summaries=load_rows(cache/folder,'ALL_NEW_TIMING_WEEKLY')+load_rows(cache/folder,'RETAINED_CONTROLS')
        pairs=load_rows(cache/folder,'ALL_NEW_TIMING_MATCHED')
        relevant=[r for r in summaries if r['view']==view and r['source_panel']=='ANNUAL_NAMED_NJ' and r['week_view']=='ALL']
        ids=sorted({r['candidate_id']for r in summaries if r['candidate_id'].startswith(prefix)})
        for r in relevant:
            z={k:decoded(v) for k,v in r.items()}
            z.update(A_ref=REF,source_score_state='COMPLETED_OWNER_LOCAL;PUBLIC_ARITHMETIC_INDEPENDENTLY_VERIFIED',
                exact_book_or_venue='ANNUAL_NAMED_NJ owner source label; exact raw book/quote keys not independently inspectable from public aggregates',
                forecast_origin='HISTORICAL_ORIGIN_CURRENT_REVISED_RECONSTRUCTION_NOT_ORIGINAL_ISSUANCE',
                source_clock='QUOTE_AND_DECISION_TIMING_UNVERIFIED',actual_offer_weeks=[1,2,3,4,5],new_scored_NFL_weeks=0,
                private_identity_grade_model_clock_verification='UNKNOWN',live_use='NOT_ESTABLISHED_BY_THIS_RECORD',
                probability_typing='Explicit saved B law score; not inferred from displayed point' if category=='pass_cmp' else 'NOT_PROVIDED_TYPED_POINTS_ONLY')
            all_primary.append(z)
        best=max(int(r['combined_wins'])/int(r['combined_decided']) for r in relevant if int(r['combined_decided']))
        winners=[r for r in relevant if int(r['combined_decided']) and int(r['combined_wins'])/int(r['combined_decided'])==best]
        leaders.append(dict(category=category,panel='ANNUAL_NAMED_NJ_W1_W5',highest_observed_comparable_procedures=[r['candidate_id']for r in winners],combined_wins=int(winners[0]['combined_wins']),decided=int(winners[0]['combined_decided']),rate=best,
            operational_recommendation='NO_QUALIFIED_NEW_TIMING_REPLACEMENT;retain stronger compatible controls for owner review',
            interpretation='Scoped leader among34/30 published products, not a universal champion or authorized constant-side/live switch'))
        for candidate in ids:
            for panel in PANELS:
                for week in range(1,9):
                    matches=[r for r in summaries if r['candidate_id']==candidate and r['view']==view and r['source_panel']==panel and r['week_view']==str(week)]
                    assert len(matches)<=1
                    r={k:decoded(v)for k,v in matches[0].items()} if matches else None
                    n=r['eligible']if r else 0
                    state=('COMPLETED_REAL_LINE_TIMING_UNVERIFIED' if panel==PANELS[0] and n else
                           'COMPLETED_INTERNAL_OR_UNQUALIFIED_SITE_THRESHOLD_DIAGNOSTIC' if panel==PANELS[1] and n else
                           'NO_ROWS_IN_THIS_BOUND_SOURCE_PANEL;NOT_GLOBAL_SOURCE_ABSENCE')
                    coverage.append(dict(category=category,procedure_id=candidate,season=2026,week=week,source_panel=panel,view=view,
                        state=state,source_owner='A',book_or_venue=('Named annual NJ source, raw quote keys not public'if panel==PANELS[0]else'Recorded DK site/jurisdiction-unknown threshold; not qualified authentic offer'),
                        exact_procedure_saved_output_export_exists=True,original_issuance=False,chronology='Owner historical-origin/current-vintage reconstruction; no independent fit reproduction',
                        actual_offer_duration_week=bool(panel==PANELS[0]and n),
                        observed_bound_counts=r,requested_universe_count=None if not n else n,
                        missing_requirement=None if n else 'A actual annual threshold absent from bound source; qualify another exact-compatible retained panel without synthetic lines or source conflation',
                        other_B_panel=('B existing PropLine W5-W8 exact products remain separately valid subject to their own contract; no A/B W5 denominator sum' if category=='pass_cmp'and week>=5 else None)))
        for r in pairs:
            if r['view']!=view or r['source_panel']!='ANNUAL_NAMED_NJ':continue
            left,right=r['left'],r['right']
            if not(left.startswith(prefix)and(right.startswith(prefix)or right in [w['candidate_id']for w in winners]or right in ('ALWAYS_OVER','ALWAYS_UNDER'))):continue
            z={k:decoded(v)for k,v in r.items()};change=int(r['left_wins'])-int(r['right_wins']);dis=int(r['side_disagreements'])
            z.update(candidate_correct_control_wrong=(dis+change)//2,control_correct_candidate_wrong=(dis-change)//2,
                interval_status='OWNER_REPORTED_NOT_INDEPENDENTLY_RESAMPLED',private_mask_membership='UNKNOWN_TO_B;published_hash/arithmetic checked',new_NFL_observations=0)
            comparisons.append(z)
    summary=dict(id='B-ACKNOWLEDGED-A-EXACT-TIMING-JOIN-RECORDS-v1',created_UTC=created,A_ref=REF,
        report=dict(path=STEM+'/EXECUTED_TIMING_CONFIRM_V1.md',sha256='78f94e59be7c7f3cfcdc65107b2aeb10bf1212969f7dd118c194cd553174b938'),
        scope='Public aggregate projection only, not another common grader/consolidated master ranking',annual_records=all_primary,scoped_observed_leaders=leaders,selected_paired_records=comparisons,
        qualification=dict(B_F0_F3='All exact mean/lower-median/P2 products nowfive A annual scored2026weeks1-5 under quote-time-unverified tier. Earlier four-week-only statement is superseded for duration, not authenticated issuance.',C04='All exact point products nowfive A annual weeks1-5; C probability native2week panel remains unchanged.',supremacy='Five weeks is a duration floor, not superiority/support/current-query/production admission.'),
        W5_overlap=json.loads((cache/'EXECUTION_SUMMARY_V1.json').read_text())['W5_overlap'],
        nonpooled_week_union=dict(category='pass_cmp',A_annual=[1,2,3,4,5],B_native=[5,6,7,8],distinct_week_labels=[1,2,3,4,5,6,7,8],pooled_record='NOT_ESTABLISHED',reason='Different source/book/horizon and unexported normalized W5 membership/outcome-version reconciliation. More procedure coverage adds no new games.'),
        added_procedure_coverage=dict(B_F2_F3='A source now coversW1-5; earlierownednativeW5-8remainsseparate. Fournewdistinctpriorweeklabels1-4, no newNFLgames.',C04_F2_F3_points='A annualW1-5extendsnativepointW2-3; threeadditionaldistinctweeklabels1,4,5. No probabilityweektransfer.',F0_F1_aliases='Output-preservingoldR0/R2orC03R1/R2witnessreuse;no extraindependentlearnerorcalendarweek.'),
        new_fits=0,new_inference=0,new_owner_local_joins=0,new_grades=0,new_scientific_score_views=0)
    (out/'ACKNOWLEDGED_EXACT_JOIN_RECORDS_V1.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    (out/'WEEKLY_SOURCE_COVERAGE_V1.json').write_text(json.dumps(dict(id='B-A-EXACT-TIMING-W1-W8-SOURCE-COVERAGE-v1',created_UTC=created,scope='Two exact categories, owner-A join source panels, all20new typed products; not fullall12championship',records=coverage,new_games=0,new_scored_weeks=0),indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(annual_records=len(all_primary),weekly_source_cells=len(coverage),selected_pairs=len(comparisons),leaders=leaders)))


if __name__=='__main__':main()
