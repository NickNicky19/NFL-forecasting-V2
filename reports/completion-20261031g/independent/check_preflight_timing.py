"""Read-only G preflight: reuse F proof, storage status and actual feature clocks."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import gzip
import hashlib
import json
import math
from pathlib import Path


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_bytes())
def rows(p):return json.loads(gzip.decompress(p.read_bytes()))
def equal(a,b):
    if a is None or b is None:return a is b
    return math.isclose(a,b,abs_tol=1e-12,rel_tol=1e-12)
def key(q):return tuple(q[k]for k in('game_id','player_id','target','population'))


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',type=Path,required=True);ap.add_argument('--private-root',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();r=a.repo_root;private=a.private_root
    base=r/'reports/championship-20261030f';f=read(base/'offer-expansion/full-pool-v1/FROZEN_PROTOCOL.json');audit=read(base/'independent/FULL_PROVIDER_POOL_INDEPENDENT_REVIEW.json')
    assert sha(base/'offer-expansion/full-pool-v1/SCORES.json')==audit['score_sha256']
    assert sha(base/'offer-expansion/full-pool-v1/SOURCE_SNAPSHOT.py')==f['code_sha256']
    assert sha(r/'nfl_v2/full_provider_prop_replay.py')==f['code_sha256']
    storage=read(r/'reports/prop-grading-20261030e/CURRENT_RECOVERY_STATUS.json');plan=read(r/storage['frozen_missing_only_plan'])
    assert storage['remaining_named_plan_parts']==plan['missing_upload_parts']==53
    assert storage['remaining_named_plan_upload_bytes']==plan['minimum_additional_upload_bytes_for_frozen_plan']==1093747658
    assert sum(v['missing_upload_bytes']for v in plan['archives'])==1093747658
    assert storage['large_fit_recovery_gate_pass']is False and storage['current_available_bytes']is None
    assert storage['connected_profile_matches_approved_folder_owner']is True
    t=datetime.fromisoformat(f['source_clock'].replace('Z','+00:00')).timestamp()
    samples=[('hgb-history-v1','query-features/W07-pass_att.json.gz','latest_feature_available','reports/continuation-20261029/hgb-history-v1/W07-pass_att-H-MULTI-absolute_error_point-FIT.json'),
      ('distribution-wave-v2','query-features/W07-pass_att-H-MULTI-COMMON.json.gz','latest_feature_available','reports/continuation-20261030/distribution-wave-v2/W07-pass_att-H-MULTI-COMMON-regularized_glm_law-FIT.json'),
      ('qualified-defense-information-v1','query-features/W07-pass_att-H-MULTI-COMMON-D1.json.gz','latest_consumed_feature_available','reports/continuation-20261030c/qualified-defense-information-v1/W07-pass_att-H-MULTI-COMMON-D1-FIT.json'),
      ('qualified-defense-information-v1','query-features/W07-pass_att-H-MULTI-COMMON-D2.json.gz','latest_consumed_feature_available','reports/continuation-20261030c/qualified-defense-information-v1/W07-pass_att-H-MULTI-COMMON-D2-FIT.json')]
    timing=[];qmaps={}
    for folder,member,column,fitname in samples:
        packet=private/folder/member;fit=read(r/fitname);assert sha(packet)==fit['query_features']['sha256'];qq=rows(packet);assert len(qq)==31
        clockfields={k:v for k,v in fit.items()if k.startswith('latest_training_')}
        assert all(v is None or v<t for v in clockfields.values())
        assert datetime.fromisoformat(fit['fit_cutoff_utc']).timestamp()<t
        before=sum(q[column]is None or q[column]<t for q in qq)
        timing.append(dict(procedure_group=folder+' '+member.rsplit('-',1)[-1],fit_receipt=fitname,fit_receipt_sha256=sha(r/fitname),feature_packet_logical_member=folder+'/'+member,feature_packet_sha256=sha(packet),query_rows=31,source_availability_only_pass=before,source_availability_only_later=31-before,training_availability_fields=clockfields,final_forecast_admission='NOT_ESTABLISHED_BY_TIMESTAMP_ENVELOPE_ALONE'))
        qmaps[folder,member]={key(q['query']):q for q in qq}
    base_member='query-features/W07-pass_att-H-MULTI-COMMON.json.gz';baseq=qmaps['distribution-wave-v2',base_member]
    cfitname='reports/continuation-20261030b/ordered-information-ablation-v1/W07-pass_att-H-MULTI-COMMON-FIT.json';cfit=read(r/cfitname);cp=private/'ordered-information-ablation-v1/query-features/W07-pass_att-H-MULTI-COMMON.json.gz';assert sha(cp)==cfit['query_features']['sha256'];cq={key(q['query']):q for q in rows(cp)}
    assert set(cq)==set(baseq)
    projected=age_change=known_target_projection=0
    for k,b in baseq.items():
        expected=[b['features'][i]for i in(0,1,2,3,16,17,18,19)];assert all(equal(x,y)for x,y in zip(expected,cq[k]['features']));projected+=1
        if b['latest_feature_available']is not None and b['latest_feature_available']<t:
            delta=(b['query']['cutoff']-t)/86400
            # Current-clock age changes even without new source arrivals.
            if any(v is not None and abs(delta)>1e-12 for v in [b['features'][i]for i in(5,8,11,14)]):age_change+=1
            # The C02 vector has no age; a known-target-time age policy is a separate reconstruction contract.
            assert all(equal(x,y)for x,y in zip(expected,cq[k]['features']));known_target_projection+=1
    joined=rows(private/'championship-20261030f-full-pool-v1/JOINED_ROWS.json.gz')['rows'];forward={key(q):q for q in joined if q['target']=='pass_att'};assert len(forward)==25
    matched=0
    for k,q in forward.items():
        b=baseq[k]['query'];assert b['position']==q['position'];assert b['cutoff']==datetime.fromisoformat(q['kickoff'].replace('Z','+00:00')).timestamp();matched+=1
    report=dict(state='PASS_REUSED_F_HASHES_STORAGE_GATE_AND_REPRESENTATIVE_FEATURE_TIMING',checked_at_utc=datetime.now(timezone.utc).isoformat(),source_score_sha256=audit['score_sha256'],F_regraded=False,F_code_unchanged=True,
      last_storage_status_sha256=sha(r/'reports/prop-grading-20261030e/CURRENT_RECOVERY_STATUS.json'),last_storage_check_at=storage['checked_at_utc'],remaining_original_parts=53,remaining_original_bytes=1093747658,applicable_quota='UNKNOWN_IN_LAST_SUPPORTED_READ',account_owner_match_verified=True,large_fit_recovery_gate='NOT_PASSED',new_uploads=0,
      representative_timing=timing,source_availability_counts_are_not_forecast_admission=True,C02_base_projected_feature_vectors_checked=projected,source_available_queries_with_clock_age_change=age_change,C02_no_age_vectors_on_that_subset=known_target_projection,earlier_retained_threshold_rows_with_exact_known_position_and_target_kickoff=matched,
      known_target_time_contract_assessment='Legitimate NEW retrospective reconstruction if target kickoff and query context are proven known at t; source data gated independently at t; saved vector, model/prior/transformation/fallback chronology proven unchanged. It is not the earlier-current-clock refresh recipe or original issuance. Source availability alone does not prove vector equivalence.',
      next_checks=['Qualify each newly selected immutable snapshot with actual server-bound evidence before outcomes.','Audit exact full-pool intersections, strict source arrival boundaries, known position/team/opponent and fallback inputs.','Check every new score denominator/side/ranking view after the executor produces it.'],new_fits=0,new_inference=0,new_forecasts=0,new_NFL_observations=0,current2026_Week8_outcomes_read=0)
    with a.output.open('x')as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps({k:report[k]for k in('state','C02_base_projected_feature_vectors_checked','source_available_queries_with_clock_age_change','earlier_retained_threshold_rows_with_exact_known_position_and_target_kickoff','large_fit_recovery_gate')}))


if __name__=='__main__':main()
