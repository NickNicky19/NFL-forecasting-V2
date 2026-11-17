"""One optional, conditional-appearance research capture; no recommendation.

FTN-dependent models and outputs: CC-BY-SA-4.0, FTN Data via nflverse.
The native owner feed supplies a limited candidate association, not starter,
health, complete-roster or authenticated individual-offer evidence.
"""
import argparse
import hashlib
import json
import os
import resource
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nfl_v2 import player_context_matchup as ctx
from nfl_v2 import qb_opportunity_increment as inc
from nfl_v2 import qb_ftn_information as info
from nfl_v2.passing_opportunity_profiles import OpportunityHistory
from nfl_v2.distribution_laws import prior
from nfl_v2.distribution_wave_v2 import FittedLawModel
from tools.run_player_context_wave import read, write, sha, now

BASE = ROOT/'reports/information-first-20261112-01/B'
WAVE = BASE/'completion-wave-v1'
OUT = BASE/'current-conditional-shadow-v1'
VERSION = 'B-FTN-COMPLETION-CONDITIONAL-APPEARANCE-SHADOW-v1'


def stamp(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('action', choices=['prepare', 'issue'])
    ap.add_argument('--queries', type=Path)
    args = ap.parse_args()
    if args.action == 'prepare':
        if args.queries is None:
            ap.error('--queries required for preparation')
        queries = read(args.queries)
        assessment = BASE/'peer-periods/CURRENT_NATIVE_MINIMUM_QUERY_ASSESSMENT_V1.json'
        source = read(assessment)
        assert len(queries['queries']) == 5
        OUT.mkdir(exist_ok=False)
        write(OUT/'CURRENT_QUERIES.json', queries)
        write(OUT/'FROZEN_PROTOCOL.json', dict(
            id=VERSION, registered_UTC=now(), state='FROZEN_BEFORE_TWO_OPTIONAL_CURRENT_FITS',
            owner='B', source_contract='OWNER_PUBLISHED_CURRENT_QB_CANDIDATES-v1',
            scope='Conditional-on-appearance forecast-only scenario; NOT C06 admission, expected starters, guaranteed participation, complete roster, actual-line picks or primary replacement.',
            historical_recipe='B-FTN-BALL-QUALITY-COMPLETION-v1:B0/B2 fixed settings/history; no new selection or settings search.',
            source=source['owner_feed'], assessment_sha256=sha(assessment),
            queries_sha256=sha(OUT/'CURRENT_QUERIES.json'),
            code_sha256={str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__), ROOT/'nfl_v2/qb_ftn_information.py']},
            source_limits='Published event/team/QB associations only; upstream event state copied at21:45, not observed anew at feed retrieval. Individual effective transaction, active/healthy status and starter status unknown. Do not renew a stale C06 guard or claim its1800s guard passed.',
            source_age_policy='This independent minimal-source conditional research packet records published and observed clocks explicitly; no active-role or current-offer admission is made.',
            target_kickoff_UTC='2026-11-13T01:15:00+00:00',
            issue_deadline_UTC='2026-11-13T01:10:00+00:00',
            expiry_UTC='2026-11-13T01:15:00+00:00',
            horizon='Late pregame conditional scenario, later than T-90; not inheritance of a T-90 product record.',
            feature_cutoff='Actual prefit issue operation time, separate from target kickoff; strict historical available<cutoff. Existing7day reconstruction retained; no W9 eligible before firstW10 kickoff.',
            opportunity_requirement='W8-complete retained opportunity history sufficient before01:15UTC: earliestW9 kickoff+7days=01:15UTC and strict< excludes it.',
            population='Retain all5 native-listed QB records:4 missing-status conditional candidates,1 explicitIR unavailable record. No outcome or eventual starter admission.',
            output='Typed standalone completion mean, lower median and normalized count law conditional on physical appearance; no market line, selected side, confidence, EV or Top Picks.',
            fallback='Incomplete FTN source uses exact B0; IR yields explicit unavailable record, not zero. Sparse own history retains declared shared prior/history.',
            budget=dict(max_new_fits=2, max_threads=2, max_RSS_bytes=2147483648, wall_seconds=180, cpu_seconds=240),
            release='Research shadow only; no original-site writes, primary switch, scheduler, source guard change or new feed collector.',
            future_grade='Append qualified official count/participation version after finality; unknown individual statistics remain unknown. Forecast-only, no O/U record.',
            license='CC-BY-SA-4.0 forFTN-dependent derivatives;FTN Data via nflverse; underlying public stats separately attributed.'))
        print(json.dumps(dict(state='FROZEN', queries=5)))
        return
    p = read(OUT/'FROZEN_PROTOCOL.json')
    for name, h in p['code_sha256'].items():
        assert sha(ROOT/name) == h
    assert sha(OUT/'CURRENT_QUERIES.json') == p['queries_sha256']
    started = now(); cutoff = stamp(started)
    assert cutoff < stamp(p['issue_deadline_UTC'])
    cpu = time.process_time(); wall = time.monotonic()
    rows = ctx.load_inputs(WAVE/'QB_CONTEXT_W1_W9_INPUTS_V1.json.gz')
    history = ctx.ContextHistory(rows, 8, 20)
    quality = info.QBFTNInformation(history, read(BASE/'source-qualification/FTN_BALL_QUALITY_QB_GAME_INPUTS_V1.json.gz'))
    source_path = ROOT/'reports/profile-increment-to-release-01/B/source-profiles/PASSING_OPPORTUNITY_GAME_INPUTS_V2.json.gz'
    opportunity = read(source_path)
    op = OpportunityHistory(opportunity['team_games'], opportunity['QB_games'])
    assert not any(q['season'] == 2026 and q['week'] >= 9 and q['available'] < cutoff for q in rows)
    features = {(r['game_id'],r['player_id']):r for r in read(WAVE/'FEATURE_INPUTS_V1.json.gz')}
    train = [q for q in rows if q['season'] >= 2025 and q['physical_participation'] and q['target_parity'] and q['available'] < cutoff]
    y = np.asarray([q['official_completions'] for q in train]); pr = prior(y, 'pass_cmp')
    queries = read(OUT/'CURRENT_QUERIES.json')['queries']
    output = []; models = {}
    with threadpool_limits(limits=2):
        for arm in ['B0','B2']:
            x = np.asarray([features[q['game_id'],q['player_id']]['B0_features'] +
                            ([] if arm == 'B0' else features[q['game_id'],q['player_id']]['B2_appended']) for q in train], float)
            fit_started = now()
            model = FittedLawModel('ordered_leaf_cdf','pass_cmp').fit(x,y,['QB']*len(train))
            payload = ctx.export_forest(model); models[arm] = payload
            model_path = OUT/'fits'/(arm+'.json.gz')
            write(model_path, dict(model=payload, fit_started_UTC=fit_started, fit_completed_UTC=now(),
                training_rows=len(train), latest_training_label=max(q['available'] for q in train),
                training_membership_sha256=hashlib.sha256(json.dumps([(q['game_id'],q['player_id']) for q in train]).encode()).hexdigest(),
                information_cutoff_UTC=started, target_kickoff_UTC=p['target_kickoff_UTC'], feature_count=x.shape[1], new_fits=1))
            for record in queries:
                base = dict(record, method=arm, procedure_id=VERSION+':'+arm,
                    target='pass_cmp', target_outcome=None, feature_cutoff_UTC=started,
                    conditional_on='physical appearance under declared historical QB panel',
                    expected_starter='UNKNOWN_NOT_INFERRED', probability_of_appearance=None,
                    model_sha256=sha(model_path), actual_offer=None, selected_side=None,
                    per_pick_confidence=None, release_status='RESEARCH_FORECAST_ONLY_NOT_ADMITTED')
                if record['source_status'] == 'IR':
                    output.append(dict(base, output_state='UNAVAILABLE_EXPLICIT_SOURCE_IR', mean=None, lower_median=None, law=None))
                    continue
                q = dict(record, kickoff=cutoff)
                d = quality.describe(q)
                z = np.concatenate([history.direct_features(q,'E3'),inc.appended_features(op.feature_groups(q),'R3')])
                fallback = arm == 'B2' and not d['complete_required_charting']
                if arm == 'B2' and not fallback:
                    z = np.concatenate([z, info.feature_values(d,'B2')])
                law = ctx.restored_forest_law(models['B0'] if fallback else payload,z,pr)
                output.append(dict(base, output_state='CONDITIONAL_FORECAST', mean=law.mean, lower_median=law.quantile(.5),
                    law=law.parameters(), fallback='B0_INCOMPLETE_FTN_SOURCE' if fallback else 'none',
                    FTN_information=d, latest_history=history.describe(q), features=z.tolist()))
    issued = now(); assert stamp(issued) < stamp(p['issue_deadline_UTC'])
    packet = dict(id=VERSION, forecast_issued_UTC=issued, feature_cutoff_UTC=started,
        durable_local_persistence_requested_UTC=now(), target_kickoff_UTC=p['target_kickoff_UTC'], expiry_UTC=p['expiry_UTC'],
        source=p['source'], source_contract=p['source_contract'], source_limit=p['source_limits'],
        original_pregame_forecast=True, original_actual_line_selection=False, forecasts=output,
        normalized_count_law_not_role_probability=True, no_website_change=True,
        protocol_sha256=sha(OUT/'FROZEN_PROTOCOL.json'),
        parent_historical_protocol_sha256=sha(WAVE/'FROZEN_PROTOCOL.json'),
        historical_inputs_sha256=sha(WAVE/'QB_CONTEXT_W1_W9_INPUTS_V1.json.gz'),
        opportunity_inputs_sha256=sha(source_path), license=p['license'])
    write(OUT/'FORECAST_ONLY_PACKET.json.gz', packet)
    with (OUT/'FORECAST_ONLY_PACKET.json.gz').open('rb') as stream:
        os.fsync(stream.fileno())
    receipt = dict(state='LOCAL_DURABLE_FORECAST_ONLY_SHADOW', actual_persisted_UTC=now(),
        packet_sha256=sha(OUT/'FORECAST_ONLY_PACKET.json.gz'), new_fits=2, eligible_basic_records=5,
        conditional_forecasts=8, unavailable_IR_records=2, actual_lines=0, selected_sides=0,
        source_age_seconds_at_issue=stamp(issued)-stamp(p['source']['generated_UTC']),
        latest_eligible_training_label=max(q['available'] for q in train),
        current_vintage_historical_inputs=True, retained_seven_day_policy=True,
        CPU_seconds=time.process_time()-cpu, wall_seconds=time.monotonic()-wall,
        peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
        publication_and_remote_readback='PENDING_SEPARATE_RECEIPT', original_site_admission=False)
    assert receipt['wall_seconds'] < p['budget']['wall_seconds']
    assert receipt['CPU_seconds'] < p['budget']['cpu_seconds']
    assert receipt['peak_RSS_bytes'] < p['budget']['max_RSS_bytes']
    write(OUT/'CAPTURE_RECEIPT_V1.json',receipt)
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
