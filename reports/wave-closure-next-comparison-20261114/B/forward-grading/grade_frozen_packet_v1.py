"""Append final-outcome grades to a frozen conditional numerical packet.

This is an offline adapter through existing count-law and numeric scorers. It
does not fetch offers, train a model, infer an absent statistic, or issue picks.
FTN-dependent derivatives: CC-BY-SA-4.0, FTN Data via nflverse. Qualified weekly
statistical derivatives: nflverse, CC-BY-4.0. Raw corroborating responses stay
owner-local; the public receipt contains their hashes and source URLs only.
"""
from __future__ import annotations

import argparse
import collections
import csv
import datetime as dt
import gzip
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from nfl_v2 import scoring
from nfl_v2.distribution_laws import Law

EVENT = '401873052'
GAME = '2026_10_WAS_NYG'
BASE = ROOT/'reports/information-first-20261112-01/B/current-conditional-shadow-v1'
EXPECTED_PACKET = 'f9889584338bf7b85f5de3889fbc78f73fee97e2052faea7cc91a28fb203c7bb'
TEAMS = {'WAS':'28', 'NYG':'19'}
VERSION = 'B_FTN_CONDITIONAL_FORWARD_GRADE_20261114_v1'


def read(path):
    body = Path(path).read_bytes()
    return json.loads(gzip.decompress(body) if str(path).endswith('.gz') else body)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',',':')).encode()).hexdigest()


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def write(path, value):
    path = Path(path)
    if path.exists():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')


def integer(value):
    if value is None or isinstance(value, bool):
        raise ValueError('Explicit integer statistic required')
    result = float(value)
    if not math.isfinite(result) or result < 0 or int(result) != result:
        raise ValueError('Invalid credited count')
    return int(result)


def core_values(payload, category):
    selected = [r for r in payload['splits']['categories'] if r['name'] == category]
    if len(selected) != 1:
        raise ValueError('Absent/ambiguous statistic category')
    result = collections.defaultdict(list)
    for field in selected[0]['stats']:
        result[field['name']].append(field)
    return result


def explicit(values, name):
    if len(values[name]) != 1:
        raise ValueError('Absent/ambiguous explicit statistic')
    return integer(values[name][0]['value'])


def restore(parameters):
    assert parameters['kind'] == 'leaf_mixture'
    return Law('mixture', support=parameters['support'], weights=parameters['weights'],
        prior=Law(**parameters['prior']), mixture=parameters['mixture'])


def independent_law_check(parameters, observed):
    support = np.asarray(parameters['support'], float)
    weights = np.asarray(parameters['weights'], float)
    assert np.all(np.diff(support)>0) and np.all(support>=0) and np.all(weights>=0)
    assert abs(float(weights.sum())-1) < 1e-12
    b = float(parameters['mixture']); q = float(parameters['prior']['q'])
    assert parameters['prior']['kind'] == 'geometric' and 0 <= q < 1
    mean = (1-b)*float(support@weights)+b*q/(1-q)
    mass = (1-b)*float(weights[support==observed].sum())+b*(1-q)*q**observed
    # Discrete CRPS has an exact geometric upper tail beyond max(y,support).
    limit = max(int(observed),int(support[-1]))
    cdfs = [(1-b)*float(weights[support<=k].sum())+b*(1-q**(k+1)) for k in range(limit+1)]
    crps = sum((v-int(observed<=k))**2 for k,v in enumerate(cdfs))
    crps += b*b*q**(2*(limit+2))/(1-q*q)
    return dict(mean=mean, pmf=mass, NLL=-math.log(mass), CRPS=crps)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cache', type=Path, required=True)
    ap.add_argument('--identity', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    packet_path = BASE/'FORECAST_ONLY_PACKET.json.gz'
    before = sha(packet_path)
    assert before == EXPECTED_PACKET
    packet = read(packet_path)
    capsule_path = BASE/'COMPLETE_LAW_CAPSULE_V1.json.gz'
    capsule = read(capsule_path)
    assert capsule['original_packet_sha256'] == before
    assert packet['original_pregame_forecast'] is True
    assert packet['original_actual_line_selection'] is False
    assert packet['forecast_issued_UTC'] == '2026-11-13T00:09:55.109350+00:00'
    assert len(packet['forecasts']) == 10
    inputs = [packet_path, capsule_path, BASE/'FROZEN_PROTOCOL.json', args.identity]
    receipts = []
    for path in sorted(args.cache.glob('*.receipt.json')):
        receipt = read(path)
        original = args.cache/path.name.removesuffix('.receipt.json')
        assert sha(original) == receipt['sha256']
        receipts.append(receipt)
    assert sum(r['bytes'] for r in receipts) < 20*1024*1024
    finality = read(args.cache/'EVENT_STATUS.json')
    assert finality['type']['completed'] is True and finality['type']['state']=='post'
    assert '/events/'+EVENT+'/competitions/'+EVENT+'/status?' in finality['$ref']
    summary = read(args.cache/'EVENT_SUMMARY.json')
    assert summary['header']['id'] == EVENT
    assert summary['header']['competitions'][0]['status']['type']['completed'] is True
    assert dt.datetime.fromisoformat(summary['header']['competitions'][0]['date'].replace('Z','+00:00')) == dt.datetime.fromisoformat(packet['target_kickoff_UTC'])
    with gzip.open(args.identity, 'rt') as handle:
        identities = list(csv.DictReader(handle))
    idmap = collections.defaultdict(set)
    for row in identities:
        if row.get('gsis_id') and row.get('espn_id'):
            idmap[row['gsis_id']].add(row['espn_id'])
    with (args.cache/'STATS_PLAYER_WEEK_2026.csv').open(newline='') as handle:
        stats = list(csv.DictReader(handle))
    queries = read(BASE/'CURRENT_QUERIES.json')['queries']
    labels = []
    for query in queries:
        gsis = query['player_id']
        assert len(idmap[gsis]) == 1
        espn = next(iter(idmap[gsis])); tid = TEAMS[query['team']]
        weekly = [r for r in stats if r['player_id']==gsis and r['season']=='2026' and r['week']=='10' and r['season_type']=='REG']
        label = dict(game_id=GAME, season=2026, week=10, player_id=gsis,
            team=query['team'],opponent=query['opponent'],
            frozen_source_status=query['source_status'], source_status_not_reinterpreted=True,
            appearance=None,actual_completions=None,actual_attempts=None,
            actual_stat_presence='NOT_QUALIFIED',label_state=None)
        if query['source_status'] == 'IR':
            # No forecast was issued. Neither absence nor HTTP404 proves DNP.
            assert not weekly
            label.update(label_state='FROZEN_IR_FORECAST_UNAVAILABLE',
                actual_stat_presence='ABSENT;NO_ZERO_OR_DNP_INFERENCE',
                excluded_from_conditional_forecast_scoring=True)
            labels.append(label)
            continue
        roster = read(args.cache/('ATHLETE_'+espn+'.json'))
        expected = '/events/'+EVENT+'/competitions/'+EVENT+'/competitors/'+tid+'/roster/'+espn+'?'
        assert expected in roster['$ref'] and str(roster['playerId'])==espn
        assert '/athletes/'+espn+'?' in roster['athlete']['$ref']
        if roster['didNotPlay'] is True:
            assert not weekly
            label.update(appearance=False,label_state='EXPLICIT_GAME_ROSTER_DID_NOT_PLAY',
                actual_stat_presence='ABSENT;CONDITIONAL_TARGET_UNDEFINED_NOT_ZERO',
                excluded_from_conditional_forecast_scoring=True)
            labels.append(label)
            continue
        assert roster['didNotPlay'] is False and len(weekly)==1
        weekly = weekly[0]
        assert (weekly['game_id'],weekly['team'],weekly['opponent_team'],weekly['position']) == (GAME,query['team'],query['opponent'],'QB')
        source = read(args.cache/('STAT_'+espn+'.json'))
        expected = '/events/'+EVENT+'/competitions/'+EVENT+'/competitors/'+tid+'/roster/'+espn+'/statistics/0?'
        assert expected in source['$ref'] and '/athletes/'+espn+'?' in source['athlete']['$ref']
        values = core_values(source, 'passing')
        completed,attempts = explicit(values,'completions'),explicit(values,'passingAttempts')
        assert (completed,attempts)==(integer(weekly['completions']),integer(weekly['attempts']))
        assert completed <= attempts
        if attempts == 0:
            # This observed played-zero is independently supported by real rushes.
            rushing = core_values(source,'rushing')
            assert explicit(rushing,'rushingAttempts') == integer(weekly['carries']) > 0
        label.update(appearance=True,actual_completions=completed,actual_attempts=attempts,
            actual_stat_presence='EXPLICIT_NFLVERSE_AND_ESPN_PASSING_COUNTS_AGREE',
            label_state='QUALIFIED_PLAYED_ZERO' if completed==0 else 'QUALIFIED_PLAYED_COUNT',
            excluded_from_conditional_forecast_scoring=False)
        labels.append(label)
    by = {r['player_id']:r for r in labels}
    laws = {(r['player_id'],r['method']):r for r in capsule['forecasts']}
    graded = []; assertions = 0
    for forecast in packet['forecasts']:
        label = by[forecast['player_id']]
        row = dict(player_id=forecast['player_id'],game_id=GAME,season=2026,week=10,
            method=forecast['method'],procedure_id=forecast['procedure_id'],target='pass_cmp',
            output_state=forecast['output_state'],mean=forecast['mean'],lower_median=forecast['lower_median'],
            appearance=label['appearance'],label_state=label['label_state'],
            actual=label['actual_completions'], forecast_issued_UTC=packet['forecast_issued_UTC'],
            selected_side=None,actual_offer=None,venue_settlement=None,graded=False,
            fallback=forecast.get('fallback'), law_score=None)
        if forecast['output_state']=='CONDITIONAL_FORECAST' and label['appearance'] is True:
            original_law = laws[forecast['player_id'],forecast['method']]
            assert original_law['mean']==forecast['mean'] and original_law['lower_median']==forecast['lower_median']
            law = restore(original_law['law']); manual = independent_law_check(original_law['law'],row['actual'])
            assert abs(law.mean-forecast['mean']) < 1e-12
            assert law.quantile(.5)==forecast['lower_median']
            assert abs(-law.logpmf(row['actual'])-manual['NLL']) < 1e-12
            assert abs(law.crps(row['actual'])-manual['CRPS']) < 1e-10
            assertions += 4
            row.update(graded=True,law_score=dict(NLL=manual['NLL'],CRPS=manual['CRPS'],
                actual_mass=manual['pmf'],q05=law.quantile(.05),q95=law.quantile(.95),
                interval90_covered=law.quantile(.05)<=row['actual']<=law.quantile(.95)))
        graded.append(row)
    assert len(graded)==10 and sum(r['graded']for r in graded)==6
    scores = []
    for arm in ['B0','B2']:
        rr = [r for r in graded if r['method']==arm]
        good = [r for r in rr if r['graded']]
        assert len(good)==3
        for product in ['mean','lower_median']:
            result = scoring.point_metrics([r[product]for r in good],[r['actual']for r in good],'pass_cmp')
            precision = {}
            for name in ['exact_rate','abs_lt_1','abs_le_1','abs_lt_5','abs_le_5','abs_lt_10','abs_le_10']:
                if name=='exact_rate':hits=sum(r[product]==r['actual']for r in good)
                else:
                    _,op,k=name.split('_')
                    hits=sum(abs(r[product]-r['actual'])<int(k) if op=='lt' else abs(r[product]-r['actual'])<=int(k) for r in good)
                precision[name]=dict(numerator=hits,denominator=3,rate=hits/3)
            scores.append(dict(result,record_kind='forecast_evaluation_view',
                record_id='B-FORWARD-CMP-'+digest([VERSION,arm,product])[:24],
                procedure_id=good[0]['procedure_id'],product_id=product,target='pass_cmp',
                season=2026,week=10,evaluation_seasons=[2026],evaluation_weeks=[10],
                period='full_game',season_type='REG',statistic_period='full_game',overtime=True,
                population='ORIGINAL_LATE_PREGAME_CONDITIONAL_OWNER_PUBLISHED_QB_CANDIDATES',position='QB',
                history_regime='H-RECENT',horizon_id='LATE_PREGAME_ACTUAL_ISSUE_20261113T000955Z',
                evidence='GENUINE_PREGAME_CONDITIONAL_FORECAST_ONLY;CURRENT_FINAL_STAT_GRADING',
                source_vintage='HistoricalFTNinputsretaincurrent-vintage7dayreconstruction;actualforecastissueandfinaloutcomeobservationclocksbound',
                evaluation_panel_id=VERSION,forecast_rows=4,outer_query_rows=5,
                unavailable_forecasts=1,IR_unavailable_rows=1,DNP_rows=1,
                unknown_issued_forecast_participation=0,unknown_unavailable_query_participation=1,
                technical_unavailable=0,admitted_abstentions=0,
                fallback_view='FULL_CONDITIONAL_SYSTEM_WITH_UNAVAILABLE_AND_NONAPPEARANCE_RETAINED',
                fallback_rows=0,scored_fallback_rows=0,unique_games=1,unique_players=3,
                unique_player_games=3,precision_counts=precision,
                query_membership_sha256=digest(sorted([r['game_id'],r['player_id'],'pass_cmp']for r in good)),
                outer_query_membership_sha256=digest(sorted([r['game_id'],r['player_id'],'pass_cmp']for r in rr)),
                null_reason=None,NLL=float(np.mean([r['law_score']['NLL']for r in good])),infinite_NLL=0,
                CRPS=float(np.mean([r['law_score']['CRPS']for r in good])),
                NLL_scope='Same full completion count law; shared between mean/median views; no line-specific probability score',
                law_score_shared_id=VERSION+':'+arm+':COUNT_LAW',
                law_interval90_covered=sum(r['law_score']['interval90_covered']for r in good),
                law_interval90_denominator=3,
                O_U_results=None,O_U_null_reason='NO_ACTUAL_LINE_OR_SELECTED_SIDE_IN_FROZEN_PACKET',
                uncertainty='ONE_GAME_CLUSTER;NO_INFERENTIAL_INTERVAL_OR_SUPERIORITY_CLAIM',
                original_forecast_issued_UTC=packet['forecast_issued_UTC'],graded_at_UTC=now(),
                primary_product_qualification='ONE_NUMERICAL_FORWARD_WEEK_ONLY;NO_OFFERED_LINE_OR_PRIMARY_PROMOTION',
                license='FTN-dependentderivedscoresCC-BY-SA-4.0;FTNData via nflverse;qualifiedweeklystatisticalderivativesCC-BY-4.0'))
    assert sha(packet_path)==before
    write(out/'SCORES.json',scores)
    write(out/'DERIVED_LABELS_V1.json',dict(id=VERSION+':LABELS',rows=labels,
        definition='OfficialQBfull-gamecompletionsconditionalonphysicalappearance;explicit0requiresindependentpassingcountpresence',
        raw_responses_published=False,source_tier='CURRENT_FINAL_RECHECK_NOT_ORIGINAL_PUBLICATION_VINTAGE',
        rights='QualifiedNFLversestatisticalderivativesCC-BY-4.0;ESPNcorroborationhashes/URLs only.'))
    write(out/'GRADED_FORECASTS_V1.json',dict(id=VERSION+':FROZEN_FORECAST_GRADE',rows=graded,
        original_packet_sha256=before,forecast_changed=False,new_lines_attached=0,new_sides=0,
        license='FTN-dependentderivedpredictions/scoresCC-BY-SA-4.0;FTNData via nflverse'))
    failures = [read(p) for p in sorted(args.cache.glob('*.failure.json'))]
    write(out/'SOURCE_AND_GRADING_RECEIPT_V1.json',dict(id=VERSION,state='SIX_CONDITIONAL_FORECASTS_GRADED;DNP_AND_IR_UNAVAILABLE_PRESERVED',
        observed_UTC=now(),frozen_packet_sha256=before,packet_unchanged=True,
        frozen_protocol_sha256=sha(BASE/'FROZEN_PROTOCOL.json'),law_capsule_sha256=sha(capsule_path),
        actual_issue_UTC=packet['forecast_issued_UTC'],actual_local_persisted_UTC=read(BASE/'CAPTURE_RECEIPT_V1.json')['actual_persisted_UTC'],
        prior_remote_capture_UTC=read(BASE/'REMOTE_CAPTURE_READBACK_V1.json')['readback_completed_UTC'],
        kickoff_UTC=packet['target_kickoff_UTC'],original_expiry_UTC=packet['expiry_UTC'],
        source_generated_UTC=packet['source']['generated_UTC'],source_received_UTC=packet['source']['received_UTC'],
        source_age_and_role_limits_preserved=True,
        source_members=receipts,identity_source_sha256=sha(args.identity),
        source_successes=len(receipts),source_failures=failures,HTTP_attempts=len(receipts)+len(failures),
        raw_source_bytes=sum(r['bytes']for r in receipts),max_raw_source_budget_bytes=20*1024*1024,
        new_current_source_poll_loops=0,new_collector_or_scheduler=0,
        unique_source_candidates=5,issued_conditional_forecasts=8,query_product_records=10,
        actual_appeared_players=3,scored_forecast_rows=6,explicit_DNP_players=1,DNP_forecasts=2,
        frozen_IR_unavailable_players=1,IR_unavailable_records=2,unknown_issued_forecast_participation=0,
        unknown_IR_query_actual_participation=1,played_zero_completions=1,
        played_zero_basis='NFLverseexplicitCMP0/ATT0 andESPNexplicitpassingCMP0/ATT0 agree;bothreport2creditedrushes andexactgamerosterdidNotPlay=false. Notzero inferredfromparticipation.',
        DNP_basis='ExactESPNevent/team/athleteroster explicitlydidNotPlay=true; no numeric0 assigned.',
        IR_basis='PreserveoriginalsourceIR/nooutput; missingweeklyrecord andHTTP404 donotestablishactualDNP orstatzero.',
        source_ref_and_stat_assertions='ExactstableGSIS→ESPNbridge;canonicalgame/season/week/team/opponent;full-gamepassingcategory;no fuzzynamejoin',
        independent_law_assertions=assertions,manual_CRPS='DiscreteCDFsquared-error sum plus exactunboundedgeometrictail',
        grader_sha256=sha(ROOT/'nfl_v2/scoring.py'),law_sha256=sha(ROOT/'nfl_v2/distribution_laws.py'),adapter_sha256=sha(Path(__file__)),
        canonical_score_views=4,new_NFL_game_outcomes_for_this_packet=1,new_numerical_season_weeks=1,
        new_actual_line_weeks=0,new_actual_line_selections=0,new_fits=0,new_forecasts=0,
        original_site_changes=0,C_admission='NOT_OBSERVED_LOCAL_NOT_C_ADMITTED',
        limitations=['Onegame/threeplayedQBs;notindependentgames or evidenceofgeneralimprovement.',
                    'ActualNFLverseandESPNdataarecurrentfinalvintages,notindependentupstreamlineages guaranteed.',
                    'ESPNactive=falsepostgameisnotusedaspregamehealth or appearance.',
                    'No marketline, selectedside,settlement,confidencecalibration or90%claim.']))
    print(json.dumps(dict(state='GRADED',views=4,played_players=3,DNP_players=1,IR_unavailable_players=1,
        metrics=[{k:r[k]for k in ['procedure_id','product_id','n','mae','mse','bias','NLL','CRPS']}for r in scores])))


if __name__ == '__main__':
    main()
