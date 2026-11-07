"""Project public aggregate/owner receipt evidence; never fit or publish a feed."""
import collections
import datetime as dt
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports/post-wave-5w-v1'
SCRATCH = Path('/workspace/scratch/post-wave-owner-readback')


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def save(name, obj):
    p = OUT / name
    with p.open('x') as f:
        json.dump(obj, f, indent=2, allow_nan=False)
        f.write('\n')


def main():
    source = Path('/workspace/scratch/postwave-C-A-W1W7-aggregates.json.gz')
    expected = '2787e1a0559caf73a2bc0c6749bc70c7612e9bf5b8bc6ed41f3062e5e404e4f6'
    assert sha(source) == expected
    rows = json.loads(gzip.decompress(source.read_bytes()))
    proc = 'f8607aa99a94c7c1c9ab5c89599e07eba9b15527749b092b225f368032881e83'
    r = next(r for r in rows if r['category'] == 'pass_td' and proc in r['procedure_id'])
    weeks = []
    for w in r['week_rows']:
        ow, ol, uw, ul = [int(w[k]) for k in ('over_wins', 'over_losses', 'under_wins', 'under_losses')]
        n = ow + ol + uw + ul
        assert n == int(w['decided']) and ow + uw == int(w['correct'])
        weeks.append(dict(season=2026, week=int(w['week']), eligible=int(w['opportunities']),
                          OVER=dict(wins=ow, losses=ol, decided=ow+ol),
                          UNDER=dict(wins=uw, losses=ul, decided=uw+ul),
                          COMBINED=dict(wins=ow+uw, losses=ol+ul, decided=n),
                          offered_MAE=float(w['MAE_offered']), source_row=w))
    for side in ('OVER', 'UNDER', 'COMBINED'):
        for k in ('wins', 'losses', 'decided'):
            assert sum(w[side][k] for w in weeks) == r[side][k]
    distinct = sorted({(w['season'], w['week']) for w in weeks if w['COMBINED']['decided']})
    weighted_mae = sum(w['offered_MAE']*w['COMBINED']['decided'] for w in weeks)/r['COMBINED']['decided']
    receipt = json.loads(Path('/workspace/scratch/postwave-owner-comment-6642441018.json').read_text())
    reads = json.loads((OUT/'ACTUAL_OWNER_AND_C_HANDOFF_READS.json').read_text())
    save('COUNT_A_FIVE_WEEK_AND_DELIVERY_WITNESS.json', dict(
        kind='B_INDEPENDENT_PUBLIC_AGGREGATE_WEEK_ARITHMETIC_AND_DELIVERY_WITNESS',
        evaluated_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
        product_id='pass_td__COUNT_A_MEAN', procedure_sha256=proc,
        canonical_procedure_id=r['procedure_id'], output='CORRECTED_MEAN_POINT',
        selection_policy='SAVED_MEAN_POINT_VERSUS_ACTUAL_LINE_P1;NOT_SITE_CROSS_CATEGORY_TOP12',
        role_scope='QB_PASSING', history=r['history'],
        aggregate_source=dict(repository='NickNicky19/NFL-forecasting-NGS-C',
            commit=reads['C_ref'], path='reports/abc-championship/continuation-v2/A_W1_W7_ARCHIVED_SCORES.json.gz', sha256=expected),
        receipt=dict(url=receipt['html_url'], created_at=receipt['created_at'], updated_at=receipt['updated_at'],
                     no_superseding_receipt_observed=reads['results']['production-supersessions']),
        reported_scores={s:r[s] for s in ('OVER','UNDER','COMBINED')},
        eligible=r['eligible'], games=r['games'], week_rows=weeks,
        distinct_scored_week_pairs=distinct, distinct_scored_weeks=len(distinct),
        five_week_floor='MET_FOR_THIS_REPORTED_EXACT_POINT_DIRECTION_PRODUCT;NOT_PRODUCER_ADMISSION',
        recomputed_offered_MAE=weighted_mae,
        original_selected_pool_controls=dict(always_under_wins=r['OVER']['losses']+r['UNDER']['wins'],
            always_over_wins=r['OVER']['wins']+r['UNDER']['losses'], denominator=r['COMBINED']['decided']),
        strongest_reported_learner=dict(id='A_LEAF_CDF_MEDIAN', wins=85, decided=142,
            count_a_extra_wins=2, uncertainty='Reported game interval crosses zero; raw rows not independently accessed by B'),
        source_evidence=r['scope'], quote_timing=r['quote_timing'], settlement=r['settlement'],
        current_public_route=dict(repository='NickNicky19/NFL-forecasting', ref='lab-state',
            head=reads['results']['lab-tree']['head'],
            requested_path='state/public/weekly-adaptive-v1/2026-W09',
            complete_tree_inspected=not reads['results']['lab-tree']['truncated'],
            actual_public_week_directories=reads['results']['lab-tree']['public_week_directories'],
            state='CURRENT_WEEK_PUBLICATION_NOT_PRESENT_AT_INSPECTED_HEAD;NOT_PROOF_MODEL_MISSING'),
        stored_output_contract=dict(point='Corrected intended mean including registered mean-corrector',
            legacy_point='Mixed fallback; not corrected mean product', mean='NaN in retained packet; not consumable',
            bare_predict='Insufficient; must apply exact stored mean-corrector and distinguish prior-MEAN/incumbent fallback'),
        artifact_bindings=dict(CELL_zip_sha256='5f55367c9f3389dbbe713b1aa95e691e77602cde99bf8e5ff657554a2d5a6a36',
            MODEL_joblib_sha256='4d277e3e3986d712a86d9a55019e35f2e5b5c58d6f4f411af0a0abc65da1b62d',
            access='A_APPROVED_ROUTE_ONLY;NOT_RESTORED_OR_DESERIALIZED_BY_B'),
        delivery_state='OWNER_RECEIPT_VERIFIED;NEW_EXACT_CURRENT_PRODUCT_EXPORT_AND_ACK_NOT_VERIFIED',
        exact_next_owner_action='A registered producer restores the exact existing model/features/environment/mean-corrector under its approved route; proves retained-case/current-query parity; publishes permitted derived current-week output with real clocks, role/eligibility/side/rank/fallback/expiry bindings; original-site owner validates and acknowledges product admission. No duplicate fit by B.',
        limits=['Seven reported scored weeks do not establish full W1-W8 coverage, authenticated quote timing, profitability or a scientific superiority claim.',
                'The historical offered subset reports zero fallback; production prior-MEAN/incumbent fallback parity remains separate.',
                'These weeks cannot qualify a new repair, selector, probability law or live cross-category Top12 policy.',
                'Exact restoration preserves qualification; a materially changed recipe gets its own evidence.'],
        new_fits=0, new_inference=0, new_NFL_observations=0))
    # Complete the nested capture projection, preserving the original V1 witness.
    b = SCRATCH/'git-data__current-classic__2026__w09__bbbb32867fb5150bbed7eea14b3aa95ee42269a0302911369dde3b430cb525c0.json.gz'
    wrapper = json.loads(gzip.decompress(b.read_bytes())); cap = wrapper['payload']
    board = json.loads((SCRATCH/'git-output__data__week.json').read_bytes())
    ranking = json.loads((SCRATCH/'git-output__data__weekly-selected-rankings__5ed15062d2bdef11db823d9f15a3f5a002e857c76fa5ea7b457e8d1ef8ad9ac2.json').read_bytes())
    picks = ranking['picks']['over']+ranking['picks']['under']
    parse=lambda x:dt.datetime.fromisoformat(x.replace('Z','+00:00'))
    assert len(picks)==24 and all(parse(p['selected_at'])<parse(p['kickoff_utc']) for p in picks)
    assert len({(p['game_id'],p['player_id'],p['key'],p['line'],p['direction']) for p in picks})==24
    assert cap['input_sha256']==sha(SCRATCH/'git-output__data__week.json')
    assert all(parse(cap['captured_at'])<parse(g['kickoff']) for g in board['games'])
    save('OWNER_CAPTURE_QUALIFICATION_V2.json', dict(
        kind='NESTED_CAPTURE_METADATA_COMPLETION_FROM_SAME_RETAINED_BYTES',
        evaluated_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
        previous_witness=dict(path='OWNER_CAPTURE_READBACK.json', sha256=sha(OUT/'OWNER_CAPTURE_READBACK.json')),
        production_commit='af8bc14abe4a4148a3f84e6c131775923b5300f4',
        capture_id='bbbb32867fb5150bbed7eea14b3aa95ee42269a0302911369dde3b430cb525c0',
        physical_capture_sha256=sha(b), payload_sha256=wrapper['payload_sha256'],
        capture_metadata={k:cap[k] for k in ('schema_version','model','captured_at','forecast_generated_at','code_commit','input_sha256','evidence_label')},
        capture_rows=len(cap['rows']), published_board_games=len(board['games']),
        first_game_kickoff=min(g['kickoff'] for g in board['games']),
        actual_pregame_capture_clock_checks='PASS_ALL_PUBLISHED_BOARD_GAMES_AND_24_SAVED_TOP_PICKS',
        top_picks=dict(over=len(ranking['picks']['over']), under=len(ranking['picks']['under']), total=24,
            games=len({p['game_id'] for p in picks}),
            products=dict(collections.Counter(p['product'] for p in picks)),
            sources=dict(collections.Counter(p['forecast_source'] for p in picks))),
        original_site_persistence='2026-11-04T21:03:44Z',
        updater_run=dict(id=41912247259, state='COMPLETED_SUCCESS;INDEPENDENT_GITHUB_API_READ',
                         completed_at='2026-11-04T21:04:50Z'),
        next_nominal_configured_capture='2026-11-05T14:06:00Z;NOT_YET_EXECUTED_AT_THIS_WITNESS',
        selected_research_rows=0, new_B_capture=0, new_B_model_inference=0,
        limits=['Original schema local-publication label preserved; subsequent Git persistence and served-byte equality witnessed separately.',
                'Actual source publication/quote freshness and bookmaker rules remain unverified.',
                'Configured next schedule is not an execution; B has not dispatched or changed it.']))
    print(json.dumps(dict(count_a_scored_weeks=len(distinct), count_a_decided=r['COMBINED']['decided'],
        count_a_MAE=weighted_mae, capture_rows=len(cap['rows']), top_picks=len(picks))))


if __name__ == '__main__':
    main()
