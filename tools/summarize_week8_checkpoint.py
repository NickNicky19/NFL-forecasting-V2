"""Project retained Week8 scores, coverage and private right/wrong details."""
from __future__ import annotations
import argparse,collections,csv,gzip,hashlib,json,math,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools import grade_saved_week8 as core,grade_week8_captured_library as library
from nfl_v2 import scoring,full_provider_prop_replay as shared
from nfl_v2.shared_subgroups import packet_rows
from nfl_v2.paired_uncertainty import paired_losses
from nfl_v2.recorded_prop_grading import canonical


def summary(private,public):
    start=time.monotonic();out=public/'checkpoint-summary-v1';out.mkdir(exist_ok=False)
    num=core.read(public/'comparable-products-v3/SCORES.json');ownnum=core.read(public/'captured-library-v2/SCORES.json');lawnum=core.read(public/'saved-laws-v2/SCORES.json')
    table=core.read(public/'original-v1/SIDE_TABLE.json');allgrades=json.loads(gzip.decompress((private/'ORIGINAL_AND_TOP_GRADED_ROWS_V1.json.gz').read_bytes()))['rows']
    originals=[r for r in table if r['panel']=='ORIGINAL_PROVIDER_T90'and r['cohort']=='ALL'and r['strategy']=='original'];core.save(out/'TABLE_A_ORIGINAL_CATEGORY.json',originals);core.write_csv(out/'TABLE_A_ORIGINAL_CATEGORY.csv',originals)
    primary=core.read(public/'original-v1/SAVED_LIST_VERSION_CENSUS.json')['primary'];tops=[r for r in table if r['panel']==primary['panel']];core.save(out/'TABLE_B_PRIMARY_TOP_CATEGORY.json',tops);core.write_csv(out/'TABLE_B_PRIMARY_TOP_CATEGORY.csv',tops)
    offers=[r for r in json.loads(gzip.decompress((private/'ORIGINAL_JOINED_ROWS_V1.json.gz').read_bytes()))['rows']if r['panel']=='ORIGINAL_PROVIDER_T90'];bytarget={t:[r for r in offers if r['target']==t]for t in scoring.TARGETS};offerkeys={library.key(r)for r in offers}
    primarycaps=set(core.read(public/'captured-library-v2/COMMON_PANEL_DEFINITION.json')['primary_captures'])
    groupkeys=collections.defaultdict(dict);commonsets=collections.defaultdict(list);leaderids=set();winners={};allwins=[]
    for target in scoring.TARGETS:
        rr=[r for r in num if r['target']==target and r['n']];metric='brier'if target=='anytime_td'else'mae';best=min(r[metric]for r in rr);ww=[r for r in rr if math.isclose(r[metric],best,rel_tol=0,abs_tol=1e-12)]
        # Stable source order selects only a display representative. All exact
        # tied rows remain separate in the published ties table and rankings.
        winners[target]=ww;leaderids.update(r['method_key']for r in ww);allwins.extend(ww)
    for r in packet_rows(private/'CAPTURED_LIBRARY_NUMERIC_ROWS_V1.json.gz'):
        g=library.group(r);mid=library.view_id(g);k=library.key(r)
        if k in offerkeys:groupkeys[mid][k]=(bool(r['original_forecast_issued']),bool(r['T90_eligible']),r['fallback'])
    common={}
    for r in num:
        mid=r['method_key'];valid={k for k,v in groupkeys[mid].items()if v[0]and v[1]}
        # The numerical common panel contains only supported final keys; the
        # retained P1 rows below supply its offered intersection exactly.
        if r['capture_version']in primarycaps:commonsets[r['target']].append(valid)
    native_common={t:set.intersection(*sets)for t,sets in commonsets.items()if sets}
    # Same-key controls are projections of already graded original rows, not
    # new forecasts or changes to the original weekly record.
    p1=core.read(public/'comparable-products-v3/SELECTION_SCORES.json');p1keys=collections.defaultdict(set)
    for r in packet_rows(private/'CAPTURED_LIBRARY_P1_ROWS_V1.json.gz'):
        if r['capture_version']in primarycaps and r['outcome_state']=='final'and r['actual']is not None and library.key(r)in native_common.get(r['target'],set()):p1keys[r['target']].add(library.key(r))
    for t in p1keys:common[t]=p1keys[t]
    controls=[]
    for strategy in shared.STRATEGIES:
        rr=[r for r in allgrades if r['panel']=='ORIGINAL_PROVIDER_T90'and r['strategy']==strategy and library.key(r)in common.get(r['target'],set())]
        controls.extend(core.aggregate(rr,panel='EXACT_SHARED_OFFER_KEY_CONTROLS_V1',method='WEBSITE_CONTROL:'+strategy,track='A_ORIGINAL'if strategy=='original'else'B_REPLAY',strategy=strategy,pool=rr))
    core.save(out/'CONTROL_SCORES.json',controls);ct=core.wide(controls);core.save(out/'CONTROL_SIDE_TABLE.json',ct);core.write_csv(out/'CONTROL_SIDE_TABLE.csv',ct)
    method_rows={r['method_key']:r for r in ownnum};coverage=[]
    for mid,points in sorted(groupkeys.items()):
        m=method_rows[mid];outer=bytarget[m['target']];issued=sum(v[0]and v[1]for v in points.values());selected=sum(v[0]and v[1]for v in points.values())
        coverage.append(dict(method_key=mid,capture_version=m['capture_version'],procedure_id=m['procedure_id'],history_regime=m['history_regime'],product_id=m['product_id'],target=m['target'],
            outer_provider_offer_rows=len(outer),outer_final_rows=sum(r['outcome_state']=='final'for r in outer),outer_pending_rows=sum(r['outcome_state']=='pending'for r in outer),
            query_and_offer_identity_present=len(points),issued_T90_forecasts_on_offers=issued,missing_query_opportunities=len(outer)-len(points),captured_query_unissued_rows=sum(not v[0]for v in points.values()),captured_issued_late_for_T90_rows=sum(v[0]and not v[1]for v in points.values()),
            unavailable_against_outer=len(outer)-issued,forecast_coverage_over_outer=issued/len(outer)if outer else None,coverage_scope='Full retained provider-labelled outer offers including Thursday/pending/unknown; P1score selection_coverage is separately conditional on admitted forecasts.',
            known_fallback_forecasts=sum(v[0]and v[1]and v[2]not in(None,False,'none','NONE','UNKNOWN_NOT_RETAINED')for v in points.values()),fallback_unknown_forecasts=sum(v[0]and v[1]and v[2]=='UNKNOWN_NOT_RETAINED'for v in points.values())))
    core.save(out/'OUTER_FORECAST_COVERAGE.json',coverage);core.write_csv(out/'OUTER_FORECAST_COVERAGE.csv',coverage)
    ownside=core.read(public/'captured-library-v2/SELECTION_SIDE_TABLE.json');commonside=core.read(public/'comparable-products-v3/SELECTION_SIDE_TABLE.json');lawside=core.read(public/'saved-laws-v2/SELECTION_SIDE_TABLE.json')
    side_by_mid={r['procedure_id'].rsplit(':',1)[-1]:r for r in commonside};cov_by_mid={r['method_key']:r for r in coverage};combined=[]
    for target,ww in winners.items():
        for w in ww:
            mid=w['method_key'];s=side_by_mid.get(mid)
            combined.append(dict(numeric=w,selection=s,outer_forecast_coverage=cov_by_mid.get(mid),tie_count=len(ww),selection_unavailable_reason=None if s else'NO_COMPATIBLE_RETAINED_THRESHOLD: exactchart/anytimeevent markets not established'))
    core.save(out/'TABLE_C_NUMERICAL_LEADERS_OWN_SELECTIONS.json',combined)
    core.save(out/'NUMERICAL_TIES.json',allwins);core.write_csv(out/'NUMERICAL_TIES.csv',allwins)
    selection_leaders=[]
    for scope,rows in [('COMMON_P1',commonside),('OWN_POOL_P1',ownside),('OWN_LAW_P2',lawside)]:
        for target in scoring.TARGETS:
            rr=[r for r in rows if r['target']==target]
            for side in('over','under','combined'):
                valid=[r for r in rr if r[side+'_decided']]
                if not valid:continue
                mx=max(r[side+'_hit_rate']for r in valid)
                for row in valid:
                    if math.isclose(row[side+'_hit_rate'],mx,rel_tol=0,abs_tol=1e-12):selection_leaders.append(dict(scope=scope,selected_side_product=side,**row))
    core.save(out/'SEPARATE_OBSERVED_SELECTION_MAXIMA.json',selection_leaders);core.write_csv(out/'SEPARATE_OBSERVED_SELECTION_MAXIMA.csv',selection_leaders)
    prob=[]
    for target in core.ORDINARY:
        rr=[r for r in lawnum if r['target']==target and r['reference']=='FOOTBALL_ORIGINAL_LAW'and r['evaluation_panel_id'].endswith(':HALF_POINT_NO_PUSH')and r['n']]
        minimum=min(r['brier']for r in rr)
        for r in rr:
            if math.isclose(r['brier'],minimum,rel_tol=0,abs_tol=1e-12):
                refs=[x for x in lawnum if x['method_key']==r['method_key']and x['evaluation_panel_id']==r['evaluation_panel_id']and x['reference']!='FOOTBALL_ORIGINAL_LAW'];prob.append(dict(winner=r,matched_references=refs))
    core.save(out/'THRESHOLD_PROBABILITY_LEADERS_AND_BASELINES.json',prob)
    # Shared numerical rows for every tied leader versus the eligible early
    # adaptive incumbent, preserving different clocks rather than a pure fit claim.
    wanted=leaderids|{r['method_key']for r in num if r['capture_version']=='WEBSITE_ADAPTIVE_ORIGINAL_3907'};points=collections.defaultdict(dict)
    for r in packet_rows(private/'CAPTURED_LIBRARY_NUMERIC_ROWS_V1.json.gz'):
        mid=library.view_id(library.group(r))
        if mid in wanted and r['error']is not None and r['T90_eligible']:points[mid][library.key(r)]=r
    comparisons=[]
    for target,ww in winners.items():
        inc=next((r for r in num if r['target']==target and r['capture_version']=='WEBSITE_ADAPTIVE_ORIGINAL_3907'),None)
        if not inc:continue
        for w in ww:
            aa=points[w['method_key']];bb=points[inc['method_key']];keys=sorted(set(aa)&set(bb));metric='SQUARED_BINARY_ERROR_BRIER'if target=='anytime_td'else'ABSOLUTE_ERROR'
            la=[aa[k]['error']**2 if target=='anytime_td'else abs(aa[k]['error'])for k in keys];lb=[bb[k]['error']**2 if target=='anytime_td'else abs(bb[k]['error'])for k in keys]
            comparisons.append(dict(target=target,candidate_method_key=w['method_key'],incumbent_method_key=inc['method_key'],metric=metric,**paired_losses(la,lb,[8]*len(keys),[k[0]for k in keys]),scope='All shared qualified final T90eligible player-games for this pair; distinct original source/update clocks; no verified website-serving or pure same-information learner claim.'))
    core.save(out/'LEADERS_VS_EARLY_ADAPTIVE_SHARED_NUMERICAL.json',comparisons);core.write_csv(out/'LEADERS_VS_EARLY_ADAPTIVE_SHARED_NUMERICAL.csv',comparisons)
    # Detailed scorecard stays private. All four right/wrong buckets and true
    # errors/gaps are retained; postgame diagnosis never becomes a predictor.
    dest=private/'WEEK8_RIGHT_AND_WRONG_DETAILS_V1.csv.gz';counts=collections.Counter();n=0
    fields=['case_id','track','capture','procedure','history','product','game_id','player_id','target','forecast','line','selected_side','actual','grade','forecast_minus_line','actual_minus_line','forecast_minus_actual','decision_time','forecast_issue_time','source_retention_time','evidence_tier','fallback','cause']
    with gzip.open(dest,'xt',newline='')as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        streams=[('ORIGINAL_AND_SAVED_CONTROLS',iter(allgrades)),('RESEARCH_P1',packet_rows(private/'CAPTURED_LIBRARY_P1_ROWS_V1.json.gz'))]
        for track,rr in streams:
            for r in rr:
                if r['selected_side']not in('over','under'):continue
                pred=r.get('prediction');line=r['line'];actual=r.get('actual');grade=r['statistical_state'];bucket=(r['target'],track,r['selected_side'],grade);counts[bucket]+=1;n+=1
                ident=[track,r.get('panel'),r.get('capture_version'),r.get('method_key'),r.get('strategy'),r['game_id'],r['source_player_id'],r['target'],line,r['selected_side']]
                exact=lambda a,b:str(scoring.exact_decimal(a)-scoring.exact_decimal(b))if core.finite(a)and core.finite(b)else None
                writer.writerow(dict(case_id='W8-CASE-'+hashlib.sha256(canonical(ident)).hexdigest()[:24],track=track,capture=r.get('capture_version',r.get('panel')),procedure=r.get('procedure_id',r.get('forecast_method',r.get('strategy'))),history=r.get('history_regime'),product=r.get('product_id'),game_id=r['game_id'],player_id=r['player_id']or r['source_player_id'],target=r['target'],forecast=pred,line=line,selected_side=r['selected_side'],actual=actual,grade=grade,
                    forecast_minus_line=exact(pred,line),actual_minus_line=exact(actual,line),forecast_minus_actual=exact(pred,actual),decision_time=r.get('decision_time'),forecast_issue_time=r.get('forecast_issued_at'),source_retention_time=r.get('source_server_clock'),evidence_tier='ORIGINAL_RECORDED_SELECTION'if track.startswith('ORIGINAL')and r['strategy']=='original'else'RETROSPECTIVE_RULE_REPLAY_OF_SAVED_PREGAME_FORECAST_AT_RETAINED_LINE',fallback=r.get('fallback'),cause='UNRESOLVED; descriptive threshold/numerical pattern only; no untested bias correction or inversion.'))
    core.save(out/'RIGHT_AND_WRONG_SAFE_MANIFEST.json',dict(artifact_id='L-W8-PRIVATE-DETAILED-ORIGINAL-AND-P1-SCORECARD',sha256=core.sha(dest),bytes=dest.stat().st_size,rows=n,visibility='PRIVATE_COMPANION_LOCAL_READBACK_VERIFIED_OFFHOST_PENDING',private_locator=None,
        fields=fields,views_are_not_independent_picks=True,all_original_top_versions_kept_separate=True,bucket_counts=[dict(target=k[0],track=k[1],selected_side=k[2],grade=k[3],rows=v)for k,v in sorted(counts.items())],
        source_age_and_consumed_inputs='Original forecasts/capture receipts remain authoritative; saved grade rows lack complete consumed feature vectors/availability clocks. No invented exposure decomposition for direct forecasts.',new_fits=0,new_inference=0,new_forecasts=0))
    core.save(out/'RUN_RECEIPT.json',dict(state='CATEGORY_SUMMARY_COVERAGE_CONTROLS_AND_DETAILS_PROJECTED',at_utc=core.now(),seconds=time.monotonic()-start,all_original_categories=len(originals),same_key_control_views=len(controls),outer_coverage_views=len(coverage),numerical_tied_leader_views=len(combined),separate_observed_selection_maxima=len(selection_leaders),new_fits=0,new_inference=0,new_forecasts=0,code_sha256=core.sha(__file__)))
    print(json.dumps(dict(state='SUMMARY_PROJECTED',original_selected=sum(r['combined_selected']for r in originals),decided=sum(r['combined_decided']for r in originals),detail_rows=n,seconds=time.monotonic()-start)))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--private-root',type=Path,required=True);p.add_argument('--public-root',type=Path,required=True);a=p.parse_args();summary(a.private_root,a.public_root)
