"""Presentation-only checks against already independently verified source scores."""
import argparse,collections,hashlib,json,re
from datetime import datetime,timezone
from pathlib import Path
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(repo,out):
    qualification=load(out/'SOURCE_CLOCK_AND_ATTRIBUTION_QUALIFICATION_V3.json');annotations={b['source']:{n['record_id']:n for n in load(repo/b['annotations'])['rows']}for b in qualification['bindings']};checks=[]
    pairs=[('SCORES','WEEKLY_AND_CUMULATIVE_SIDE_TABLE_V2'),('COMMON_COHORT_SCORES','COMMON_COHORT_SCORES_SIDE_TABLE_V2'),('MATCHED_SELECTED_CONTROL_SCORES','MATCHED_SELECTED_CONTROL_SCORES_SIDE_TABLE_V2'),('POLICY_COHORT_SCORES','POLICY_COHORT_SCORES_SIDE_TABLE_V2')]
    for source,table in pairs:
        path=out/(source+'.json');rows=[r for r in load(path)if r['record_kind']=='prop_selection_evaluation'];tt=load(out/(table+'.json'));groups=collections.defaultdict(dict)
        for r in rows:
            key=r['procedure_id'],r['target'],str(r['week']),r['strategy'],r['cohort_id'],r['evaluation_panel_id'];assert r['side']not in groups[key];groups[key][r['side']]=r
        assert len(groups)==len(tt);seen=set();sourcepath=str(path.relative_to(repo))
        for t in tt:
            key=t['procedure_id'],t['target'],str(t['week']),t['selection_rule'],t['cohort'],t['evaluation_panel_id'];assert key not in seen;seen.add(key);g=groups[key];combined=g['Combined'];m=combined['selection_metrics'];note=annotations[sourcepath][combined['record_id']]
            assert t['actual_weeks']==combined['evaluation_weeks']and t['source_artifact']==sourcepath and t['original_scores_unchanged'];assert t['horizon']==note['source_horizon_qualification']['horizon_id']and t['source_vintage']==note['source_vintage']
            for side,label in [('over','over'),('under','under'),('Combined','combined')]:
                r=g[side];mm=r['selection_metrics'];assert(t[label+'_selected'],t[label+'_wins'],t[label+'_losses'],t[label+'_decided'],t[label+'_hit_rate'])==(r['forecast_rows'],mm['WIN'],mm['LOSS'],r['n'],mm['hit_rate']);assert t[label+'_unknown']==mm['status_counts'].get('UNKNOWN_PARTICIPATION',0)
            for k in('selected','wins','losses','decided','unknown'):assert t['combined_'+k]==t['over_'+k]+t['under_'+k]
            assert t['eligible']==m['selection_pool_count']and t['selected']==combined['forecast_rows']and t['unavailable']==m['technical_unavailable']and t['abstained']==m['admitted_rule_abstentions'];assert t['fallback_issued']==m['fallback_issued']and t['fallback_unknown']==m['fallback_status_unknown']
            assert t['games']==combined['unique_games']and t['unique_player_games']==combined['unique_player_games']and t['numeric_error']is None
            for k,v in [('push','PUSH'),('void','VOID'),('pending','PENDING'),('missing_actual','MISSING_ACTUAL'),('unresolved_contract','UNRESOLVED_CONTRACT')]:assert t[k]==m['status_counts'].get(v,0)
            assert t['venue_settlement']=='UNVERIFIED_SEPARATE_STATE'
        assert seen==set(groups);checks.append(dict(source=source+'.json',source_sha256=sha(path),table=table+'.json',table_sha256=sha(out/(table+'.json')),triads_checked=len(tt),weekly_and_cumulative_keys_distinct=True))
    assert checks[0]['triads_checked']==132 and sum(c['triads_checked']for c in checks)==2604
    handoff=load(out/'C_INTAKE_AND_REVIEW_HANDOFF_FINAL_V3.json')
    for b in handoff['bindings']:assert sha(repo/b['path'])==b['sha256']
    assert handoff['state_axes']['C_admitted']=='NOT_OBSERVED'and handoff['state_axes']['C_received']=='NOT_OBSERVED'and handoff['state_axes']['new_B1_capture']is False and handoff['state_axes']['owner_admitted']is False
    report=out/'B_PREDICTIVE_IMPROVEMENT_REPORT.md';text=report.read_text()
    for needle in ('results-index-v5/README.md','INDEPENDENT_SOURCE_CLOCK_AND_INDEX_PROJECTION_V4.json','WEEKLY_AND_CUMULATIVE_SIDE_TABLE_V2.csv','Do **not recommend a production switch from this repair**','not newly C-admitted','53.12%','zero picks','not demonstrably enforced'):assert needle in text
    assert '53.13%'not in text
    for target in re.findall(r'\]\(([^)]+)\)',text):
        if '://'not in target:assert(report.parent/target.split('#')[0]).exists(),target
    prior=out/'B_PREDICTIVE_IMPROVEMENT_REPORT_PRE_HORIZON_EXPOSURE_V3.md';assert prior.exists()
    result=dict(state='PASS_FINAL_READABLE_REPORT_AND_SIDE_TABLE_BINDINGS',at_utc=datetime.now(timezone.utc).isoformat(),verification_code_sha256=sha(Path(__file__)),report_sha256=sha(report),handoff_sha256=sha(out/'C_INTAKE_AND_REVIEW_HANDOFF_FINAL_V3.json'),all_handoff_bound_bytes_verified=True,presentation_tables=checks,side_triads_checked=2604,primary_weekly_cumulative_triads=132,source_scores_not_recomputed=True,no_new_fits=True,no_new_grades=True,no_new_NFL_observations=True,recommendation='Do not switch this repair; C admission and new B1 capture not observed. Prior independently eligible owner policy remains unchanged.',limits=['This is a presentation and binding audit against source scores already independently checked; it adds no accuracy evidence.','Actual rec weeks2-3 and PT week8 remain separate partial source panels, not a complete W1-W8 record.','Handoff preparation is not actual C receipt/admission or production capture. No browser-consumption or profitability claim.'])
    (out/'INDEPENDENT_FINAL_READABLE_AND_SIDE_TABLES_V1.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('repo',type=Path);p.add_argument('out',type=Path);a=p.parse_args();run(a.repo.resolve(),a.out.resolve())
