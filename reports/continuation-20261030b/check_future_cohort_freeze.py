"""Bind frozen future memberships to new query namespace without any labels."""
import argparse,gzip,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'reports/continuation-20261030b'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def verify(private):
    freeze_path=OUT/'FUTURE_GRADING_SUBGROUP_FREEZE.json';freeze=json.loads(freeze_path.read_text())
    queries_path=private/'availability-wave-v1/frozen-queries.json';q=json.loads(queries_path.read_text());assert len(q)==2229
    future_query_path=private/'c02-future-shadow-v1/frozen-queries.json';assert future_query_path.read_bytes()==queries_path.read_bytes()
    mapping={'frozen_original_feed':'frozen_exante_feed','frozen_feed_player_union':'frozen_exante_chart_union'}
    members={};counts={};metadata_checks=0
    for spec,directory in zip(freeze['membership_artifacts'],('pregame-cohort-scorecards-v2','chart-cohort-scorecards-v1')):
        path=private/directory/'future-memberships.json.gz';assert sha(path)==spec['sha256']and path.stat().st_size==spec['bytes'];rows=json.loads(gzip.decompress(path.read_bytes()));counts[directory]=len(rows)
        for r in rows:
            k=tuple(r['key']);assert k not in members;members[k]=r
            assert r['latest_available']is None or r['latest_available']<r['ranking_cutoff']
            assert r['rank']is None or isinstance(r['rank'],int)and r['rank']>=1
            metadata_checks+=2
    joined=set();unranked=0;ranked_abstentions=0
    for row in q:
        assert row['week']==8 and row['actual']is None
        k=(row['game_id'],row['player_id'],row['target'],mapping[row['population']]);assert k in members and k not in joined;joined.add(k)
        if row.get('blocked_reason'):
            unranked+=members[k]['rank']is None
            ranked_abstentions+=members[k]['rank']is not None
    assert joined==set(members)and counts=={'pregame-cohort-scorecards-v2':1795,'chart-cohort-scorecards-v1':434}
    # Reuse earlier independent per-row issuance checks; rehash the exact same
    # immutable capture bytes rather than grading or replaying models again.
    captures=[]
    for directory,stage,review_name,hash_field,clock_field,receipt_name in[
        ('availability-wave-v1','AB','AVAILABILITY_AB_INDEPENDENT_REVIEW.json','packet_sha256','persisted_at_utc','AB-RUN_RECEIPT.json'),
        ('availability-wave-v1','C','AVAILABILITY_C_INDEPENDENT_REVIEW.json','C_packet_sha256','C_persisted_at_utc','C-RUN_RECEIPT.json'),
        ('c02-future-shadow-v1','PAIRED_C02','C02_FUTURE_INDEPENDENT_REVIEW.json','packet_sha256','aggregate_persistence_utc','RUN_RECEIPT.json')]:
        receipt_path=OUT/directory/receipt_name;receipt=json.loads(receipt_path.read_text());review_path=OUT/review_name;review=json.loads(review_path.read_text());packet=private/directory/receipt['packet']['bundle_name'];assert sha(packet)==receipt['packet']['sha256']==review[hash_field]
        clock=receipt.get('actual_persistence_completed_at',receipt.get('actual_aggregate_persistence_completed_at'));assert clock==review[clock_field]
        captures.append(dict(stage=stage,packet_sha256=sha(packet),receipt_sha256=sha(receipt_path),independent_issuance_review_sha256=sha(review_path),persistence_utc=clock,all_rows_pre_T90_checked_by_linked_review=True,actuals='ALL_NULL_PENDING'))
    return dict(status='PASS_FROZEN_COHORT_HASHES_AND_ONE_TO_ONE_NAMESPACE_BRIDGE',freeze_sha256=sha(freeze_path),future_query_sha256=sha(queries_path),query_cells=2229,games=len({r['game_id']for r in q}),cohort_rows=counts,all_members_join_exactly_once=True,cohort_metadata_checks=metadata_checks,blocked_queries_unranked=unranked,blocked_queries_with_preserved_historical_rank=ranked_abstentions,abstention_rule='A historical rank never admits a blocked forecast, supplies a zero prediction or creates a scored error; retain abstentions in cohort coverage.',
                required_population_namespace_bridge=mapping,join_contract='Map only the declared population namespace, then exact game_id/player_id/target. All underlying identifiers are already frozen; do not fuzzy-match, use actual performance, or recompute rankings.',
                captures=captures,selection='NONE; all frozen rows retained. Historical-memory cohorts are shared diagnostics, not a pure-current selected forecasting system.',readiness='High-level grading/cohort contract frozen. A schema-specific grader must apply the explicit namespace mapping plus final label/source/appearance admission before grading; no qualified Week8 labels or grades exist here.',new_fits=0,new_forecasts=0,week8_outcomes_read=0)
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--private-root',type=Path,required=True);args=parser.parse_args();r=verify(args.private_root);OUT.joinpath('FUTURE_COHORT_FREEZE_INDEPENDENT_REVIEW.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
