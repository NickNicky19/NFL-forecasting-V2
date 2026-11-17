"""Read-only public-contract census before championship result verification."""
import argparse
import collections
import datetime
import hashlib
import json
from pathlib import Path


def main():
    p=argparse.ArgumentParser();p.add_argument('--repo-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    root=args.repo_root;bindings=[]
    def read(relative,expected=None):
        path=root/relative;body=path.read_bytes();digest=hashlib.sha256(body).hexdigest()
        if expected is not None:assert digest==expected,relative
        bindings.append(dict(artifact=relative,sha256=digest));return json.loads(body)
    pointer=read('registries/CURRENT_RESULTS_INDEX.json')
    numerical=read(pointer['default_score_version_manifest']['path'],pointer['default_score_version_manifest']['sha256'])
    ranks=read(pointer['procedure_rankings']['path'],pointer['procedure_rankings']['sha256'])
    top=read(pointer['top_five_rankings']['path'],pointer['top_five_rankings']['sha256'])
    prop=read(pointer['prop_scoreboard']['path'],pointer['prop_scoreboard']['sha256'])
    pool=read('reports/prop-grading-20261030e/evidence-inventory/SOURCE_THRESHOLD_PRESENCE_CENSUS.json')
    side=read(prop['source_scores']['path'],prop['source_scores']['sha256'])
    full=pool['eligible_original_source_rows'];providers=pool['provider_labelled_finite_threshold_rows'];generated=pool['site_generated_finite_threshold_rows']
    assert full==providers+generated==1419
    assert providers==462 and generated==957
    assert sum(x['n']for x in pool['cross_states']if x['original_side_present'])==285
    assert sum(x['n']for x in pool['cross_states']if x['line_from']in('dk','sleeper')and not x['original_side_present'])==177
    assert numerical['selected_evaluation_views']==124630
    assert len(ranks)==237 and len(top)==170
    assert all(r['season']==2026 and r['n']>0 and r['population']=='primary'for r in ranks)
    counts=collections.Counter(r['ranking_product']for r in ranks)
    assert len({r['category']for r in ranks})==12
    assert len(side)==prop['audit_views']==7440
    assert sum(not r['season_alias_of_week_view']for r in side)==prop['default_views']==3720
    receipt=dict(state='PASS_SCOPED_EXISTING_COVERAGE_CONTRACT_PREFLIGHT',checked_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        bindings=bindings,numeric_procedure_product_representatives=len(ranks),numeric_product_counts=dict(counts),
        target_count=12,numeric_default_version_views=numerical['selected_evaluation_views'],full_provider_labelled_pool=providers,
        original_selected=285,original_no_selection_in_provider_pool=177,site_generated_pool_separate=generated,
        original_side_views=len(side),default_weekly_views=prop['default_views'],season_alias_views_excluded=prop['aliases_retained_not_pooled'],
        limitations=['Numeric panels are current-vintage participant reconstructions with registered horizons; not authenticated offered-line probabilities.',
            '2022 RECENT remains a source-limited proxy; complete prior-season claims must use exact procedures, not similarly named base models.',
            'D1/D2 older-season evaluations remain absent; current observed leaders and season-tested readiness are separate.',
            '462 provider-labelled thresholds have unverified quote clocks, prices and venue rules; not an authenticated priced-offer universe.',
            'Original 285 recorded choices, prospective captures, new retrospective choices and generated thresholds remain distinct.',
            'This is a bounded preflight of the located current bindings, not a lifetime all-method completeness claim.'],
        new_fits=0,new_inference=0,new_forecasts=0,new_NFL_outcomes_decoded=0)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x')as f:json.dump(receipt,f,indent=2);f.write('\n')
    print(json.dumps({k:receipt[k]for k in ('state','numeric_procedure_product_representatives','full_provider_labelled_pool','new_fits')}))


if __name__=='__main__':main()
