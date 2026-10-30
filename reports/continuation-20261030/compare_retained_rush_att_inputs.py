#!/usr/bin/env python3
"""Compare two ORIGINAL retained query/input contracts, never issue forecasts."""
import collections
import gzip
import json
import sys
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from nfl_v2.shadow_grading import canonical,digest,utc


def compare(empirical_private,hgb_private,metadata_root,source_root,output):
    eroot=ROOT/'reports/continuation-20261029/week8-shadow-v2'
    hr=Path(metadata_root);ep=Path(empirical_private);hp=Path(hgb_private)
    ec=json.loads((eroot/'CAPTURE_RECEIPT.json').read_bytes());hc=json.loads((hr/'WEEK8_CAPTURE_RECEIPT.json').read_bytes())
    eprot=json.loads((eroot/'FROZEN_PROTOCOL.json').read_bytes());hprot=json.loads((hr/'FROZEN_PROTOCOL.json').read_bytes())
    eb=(ep/'shadow-forecasts.json.gz').read_bytes();hb=(hp/'WEEK8_SHADOWS.json.gz').read_bytes()
    if digest(eb)!=ec['private_forecast_sha256']or digest(hb)!=hc['packet']['sha256']:raise ValueError('originalcapturehash mismatch')
    eraw,hraw=gzip.decompress(eb),gzip.decompress(hb)
    if digest(eraw)!=ec['private_uncompressed_sha256']or digest(hraw)!=hc['packet']['uncompressed_sha256']:raise ValueError('originalbodyhash mismatch')
    e=[r for r in json.loads(eraw)['rows']if r['target']=='rush_att'];h=[r for r in json.loads(hraw)['rows']if r['target']=='rush_att']
    eq={r['query_id']for r in e};hq={r['query_id']for r in h}
    if eq!=hq:raise ValueError('differentoriginalquerycohorts')
    shared_source={x['name']:x['sha256']for x in ec['source_ids']if x['name']in{x['name']for x in hprot['source_ids']}}
    same_bytes=all(shared_source[s['name']]==s['sha256']for s in hprot['source_ids'])
    # Availability metadata comes from the original schedule, never game outcomes.
    import csv
    from nfl_v2.week8_shadow import schedules
    schedule=Path(source_root)/'games.csv'
    if digest(schedule.read_bytes())!=shared_source['games.csv']:raise ValueError('originalschedulehash mismatch')
    games=schedules(schedule)
    earlier,later=utc(ec['actual_feature_cutoff_utc']).timestamp(),utc(hc['cutoff_utc']).timestamp()
    between=[g['game_id']for g in games.values()if earlier<=g['kickoff']+7*86400<later]
    result=dict(version='v2-retained-RA-input-comparison-v1',completed_at_utc=datetime.now(timezone.utc).isoformat(),
        empirical_capture_sha256=digest(eb),hgb_capture_sha256=digest(hb),shared_source_hashes_match=same_bytes,
        frozen_query_membership_hash_match=ec['query_membership_sha256']==hprot['week8_membership_sha256'],
        matched_query_cells=len(eq),query_positions=dict(collections.Counter(r['position']for r in e if r['history_regime']=='H-CURRENT'and r['product']=='lower_median')),
        empirical_actual_feature_cutoff_utc=ec['actual_feature_cutoff_utc'],hgb_actual_feature_cutoff_utc=hc['cutoff_utc'],
        seconds_between_feature_origins=later-earlier,source_game_availability_boundaries_between_origins=between,
        empirical_admitted_training_roles=eprot['history_positions_by_target']['rush_att'],
        hgb_admitted_training_roles=sorted(set(hprot['source_role_contract']['primary']['rush_att'])|set(hprot['source_role_contract']['extended']['rush_att'])),
        empirical_feature_memory=eprot['feature_memory'],hgb_feature_memory=hprot['feature_memory'],
        update_mechanisms=dict(empirical='Per-player sameposition all eligible observations at one realcommoncurrent origin; lower median/mean; positionfallback; historicaldiagnostic updatespergame',hgb='Weeklycommonfitorigin; same2022-start orderedtargetfeatures perquery; poolednonlinearobjectivelearner; all4rolestraining; fallbackonlywhenunfitted'),
        comparison_limit='Same targetqueries and sourcebytes but different learning/feature/role mechanisms; not identical-information mathematical procedures; no between-origin availability boundary under the registered7dayassumption',
        output_views=[],new_fits=0,new_forecasts=0,week8_outcomes_read=0)
    for family,rows,field in [('empirical',e,'product'),('hgb',h,'objective')]:
        groups=collections.defaultdict(list)
        for r in rows:groups[(r['history_regime'],r[field])].append(r)
        for (arm,product),rs in sorted(groups.items()):
            issued=[r for r in rs if r['prediction']is not None]
            result['output_views'].append(dict(family=family,history_regime=arm,product=product,n=len(issued),zeros=sum(r['prediction']==0 for r in issued),min=min(r['prediction']for r in issued),max=max(r['prediction']for r in issued)))
    with Path(output).open('xb')as handle:handle.write(canonical(result))
    return result


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    for a in ('empirical-private','hgb-private','metadata-root','source-root','output'):p.add_argument('--'+a,type=Path,required=True)
    print(json.dumps(compare(**vars(p.parse_args())),indent=2))
