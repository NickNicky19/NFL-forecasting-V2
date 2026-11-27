"""B-only product/week evidence contribution for C's shared qualification table.

Reads retained results; never infers scored weeks from a training interval or
an aggregate's declared date span. Counts are product views, not model families.
"""
import argparse
import collections
import csv
import hashlib
import json
import sys
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools.build_test_index_v3 import decode_shard
from tools import abc_b_c_bound_replay as a


def integer(value):
    if isinstance(value,bool):return None
    try:
        n=int(value)
        return n if float(value)==n else None
    except (TypeError,ValueError,OverflowError):return None


def explicit_scored_week(row):
    """Require one evidenced origin week and resolved scored support."""
    source=row.get('source_aggregate_fields')or{}
    week=integer(row.get('week'))
    if week is None:week=integer(source.get('week'))
    year=integer(row.get('season'))
    years=row.get('seasons')or source.get('evaluation_seasons')or[]
    if year is None and len(years)==1:year=integer(years[0])
    n=row.get('n');n=n if isinstance(n,int)and not isinstance(n,bool)else 0
    s=row.get('selection_metrics')or{}
    push=s.get('PUSH',0)or 0
    support=n+push if row.get('kind')=='prop_selection_evaluation'else n
    if year is None or week is None or not 1<=week<=18:return None,'NO_EXPLICIT_SINGLE_SCORED_WEEK'
    if support<=0:return (year,week),'NO_RESOLVED_SCORED_OUTCOME'
    return (year,week),'EXPLICIT_WEEK_WITH_RESOLVED_SCORED_SUPPORT'


def identity(row):
    s=row.get('source_aggregate_fields')or{}
    return dict(procedure_id=row.get('procedure_id'),category=row.get('category'),
        product_id=row.get('product_id'),history=row.get('history_regime'),
        information_policy=s.get('information_policy'),feature_memory=row.get('feature_memory_policy')or s.get('feature_memory_policy'),
        strict_current_information=s.get('strict_current_information'),
        population=row.get('population'),position=row.get('position'),
        fallback_view=row.get('fallback_view'),selection_rule=row.get('strategy'),
        selected_side_view=row.get('side'),K=row.get('K'),rank_scope=row.get('rank_scope'),
        horizon=row.get('horizon'),source_vintage=row.get('source_vintage'),
        code_version=s.get('code_sha256'),config_version=s.get('config_sha256'))


def run(out):
    start=time.monotonic();out.mkdir(parents=True,exist_ok=False)
    pointer=a.load(ROOT/'registries/CURRENT_RESULTS_INDEX.json');manifest=a.load(ROOT/pointer['manifest'])
    groups={};excluded=collections.Counter();records_seen=0
    def consume(r):
        nonlocal records_seen
        records_seen+=1;s=r.get('source_aggregate_fields')or{}
        if r.get('kind')=='software_verification':excluded['SOFTWARE_NOT_NFL_WEEKS']+=1;return
        if r.get('kind')=='right_and_wrong_prediction_diagnostic'or s.get('diagnostic_only'):
            excluded['DIAGNOSTIC_NOT_PRIMARY_PRODUCT']+=1;return
        state=r.get('score_version_state')or s.get('score_version_state')or''
        if 'INVALIDATED'in state or'SUPERSEDED'in state:excluded['INVALID_OR_SUPERSEDED']+=1;return
        cohort=r.get('cohort_id')or s.get('cohort_id')
        if cohort not in (None,'ALL','FULL_SOURCE_OFFER_BOARD_WITH_MISSING_FORECASTS_RETAINED'):
            excluded['SUBGROUP_VIEW_NOT_PRIMARY_UNIVERSE']+=1;return
        if r.get('fallback_view')not in (None,'full_system','fullsystem','all','full'):
            excluded['CONDITIONAL_LEARNED_OR_OVERLAP_VIEW']+=1;return
        ident=identity(r);key=json.dumps(ident,sort_keys=True,separators=(',',':'));g=groups.setdefault(key,dict(identity=ident,weekly={},declared=set(),attempted=set(),aggregate_only=0,evidence=set(),sources=set(),records=0))
        g['records']+=1;g['evidence'].add(str(r.get('evidence')));g['sources'].add(r['source_artifact'])
        years=r.get('seasons')or[];weeks=r.get('weeks')or[]
        if len(years)==1 and integer(years[0])is not None:
            g['declared'].update((integer(years[0]),w)for v in weeks if(w:=integer(v))is not None and 1<=w<=18)
        yw,status=explicit_scored_week(r)
        if yw is not None:g['attempted'].add(yw)
        if status!='EXPLICIT_WEEK_WITH_RESOLVED_SCORED_SUPPORT':
            if status=='NO_EXPLICIT_SINGLE_SCORED_WEEK':g['aggregate_only']+=1
            return
        n=r['n'];old=g['weekly'].get(yw)
        # Fixed outcome-completeness rule, never chosen by wins/error: largest
        # supported valid weekly view; deterministic source/ID tie.
        order=(n,r['source_artifact'],r['test_id'])
        if old is None or order>old['order']:
            g['weekly'][yw]=dict(order=order,n=n,source_artifact=r['source_artifact'],source_sha256=r['source_artifact_sha256'],test_id=r['test_id'],evidence=r.get('evidence'),wins=(r.get('selection_metrics')or{}).get('WIN'),losses=(r.get('selection_metrics')or{}).get('LOSS'),pushes=(r.get('selection_metrics')or{}).get('PUSH'),games=r.get('games'),primary_metric=r.get('primary_metric'),primary_error=r.get('primary_error'))
    for shard in manifest['shards']:
        for row in decode_shard(ROOT,shard):consume(row)
    # New exact policies have not entered the older accepted index yet. Use
    # its already-scored weekly rows, preserving procedure/product identity.
    from nfl_v2.result_index import evaluation
    newsource=ROOT/'reports/post-wave-5w-v1/b-confidence-ordering-v1/context-ranker-v1/SCORES.json'
    for row in a.load(newsource):
        rr=evaluation(row,str(newsource.relative_to(ROOT)),year_record=dict(evaluation_seasons=row['evaluation_seasons'],evaluation_weeks=row['evaluation_weeks']));rr['source_aggregate_fields']=row;rr['source_artifact_sha256']=a.sha(newsource);rr['horizon']=row['horizon_id'];consume(rr)
    records=[]
    for key,g in sorted(groups.items()):
        weeks=sorted(g['weekly']);verified=[w for w in weeks if not str(g['weekly'][w]['evidence']).startswith(('REPORTED','UNKNOWN','None'))]
        status='FIVE_WEEK_MINIMUM_MET'if len(verified)>=5 else'REPORTED_FIVE_WEEKS_ONLY_NOT_INDEPENDENTLY_VERIFIED'if len(weeks)>=5 else'BELOW_FIVE_EXPLICIT_SCORED_WEEKS'
        seasons={}
        for year in sorted({y for y,w in weeks}):
            ww=[w for y,w in weeks if y==year];seasons[str(year)]=dict(weeks=ww,scored_week_count=len(ww),supported_cases=sum(g['weekly'][year,w]['n']for w in ww),definition='SUM_OF_SELECTED_CANONICAL_WEEK_SUPPORT_COUNTS;NOT_GLOBAL_UNIQUE_NFL_OBSERVATIONS',test_ids=[g['weekly'][year,w]['test_id']for w in ww])
        ident=g['identity'];contract_known=bool(ident['procedure_id']and ident['product_id']and(ident['population']is not None or ident['horizon']is not None))
        records.append(dict(qualification_id='B5W-'+hashlib.sha256(key.encode()).hexdigest()[:20],**ident,
            scored_season_weeks=weeks,scored_week_count=len(weeks),verified_scored_season_weeks=verified,verified_scored_week_count=len(verified),minimum_week_floor_status=status,
            typed_contract_scope='SCORE_IDENTITY_PRESENT;OWNER_CODE_ROLE_SOURCE_CONTINUITY_STILL_REQUIRES_ADMISSION'if contract_known else'PRODUCT_OR_ROLE_CONTRACT_UNVERIFIED_DO_NOT_PROMOTE',
            attempted_zero_or_unresolved_weeks=sorted(g['attempted']-set(weeks)),declared_but_not_individually_verified_weeks=sorted(g['declared']-set(weeks)),
            aggregate_only_views_not_used_as_week_proof=g['aggregate_only'],per_season=seasons,
            source_artifacts=sorted(g['sources']),evidence_levels=sorted(g['evidence']),raw_score_views=g['records'],
            operational_export_status='NOT_ESTABLISHED_BY_WEEK_COUNT;SEE_EXISTING_BOUND_ADAPTER_RETENTION_CONSUMER_HANDOFF',primary_replacement_admitted=False,
            strongest_comparator='RETAINED_SOURCE_SPECIFIC_COMPARISONS_REQUIRED;NO_UNMATCHED_GLOBAL_RANKING_FROM_THIS_INVENTORY',
            qualification_limit='Week floor only. Exact source/target/origin/role/output/policy continuity, support, coverage, strongest matched controls and operational admission remain. Historical weeks do not establish current-season validation; zero-selection weeks do not transfer from base products.'))
    a.save(out/'B_PRODUCT_WEEK_QUALIFICATION.json',records)
    csvpath=out/'B_PRODUCT_WEEK_QUALIFICATION.csv'
    with csvpath.open('w',newline='')as f:
        writer=csv.DictWriter(f,fieldnames=list(records[0]));writer.writeheader();writer.writerows({k:json.dumps(v,separators=(',',':'))if isinstance(v,(dict,list))else v for k,v in r.items()}for r in records)
    receipt=dict(scope='B_ONLY_EVIDENCE_CONTRIBUTION_NOT_C_SHARED_MASTER',adopted_revision='POST-WAVE-5W-v1',source_manifest=pointer['manifest'],source_manifest_sha256=a.sha(ROOT/pointer['manifest']),source_record_count=manifest['record_count'],extra_new_policy_score_rows=len(a.load(newsource)),records_inspected=records_seen,product_views=len(records),distinct_procedure_ids=len({r['procedure_id']for r in records}),floor_states=dict(collections.Counter(r['minimum_week_floor_status']for r in records)),excluded_view_counts=dict(excluded),new_fits=0,new_inference=0,new_forecasts=0,new_NFL_observations=0,wall_seconds=time.monotonic()-start,coverage_boundary='Explicit per-week positive score support only; aggregate date spans are not counted. Some completed historical aggregate tests need retained-row/week proof, not repeated fits.',does_not_claim_deployment_or_full_championship=True)
    a.save(out/'RUN_RECEIPT.json',receipt);print(json.dumps(receipt))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('out',type=Path);args=p.parse_args();run(args.out)
