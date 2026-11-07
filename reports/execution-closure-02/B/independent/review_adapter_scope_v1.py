"""Metadata-only independent scope audit; never deserialize a fitted model."""
import argparse, gzip, hashlib, json
from datetime import datetime, timezone
from pathlib import Path

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', type=Path, required=True)
    ap.add_argument('--private-root', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    base = a.repo/'reports/continuation-20261030c/qualified-defense-information-v1'
    scores = json.loads((base/'SCORES.json').read_bytes())
    products = []
    fits = []
    for target, group in [('pass_td','D1'),('pass_cmp','D1'),('rec_yd','D2')]:
        selected = [r for r in scores if r.get('target') == target
                    and r.get('information_group') == group
                    and r.get('policy_id') == 'H-MULTI-COMMON'
                    and r.get('product_id') == 'lower_median'
                    and r.get('population') == 'primary'
                    and r.get('position') == 'ALL'
                    and r.get('fallback_view') == 'ALL']
        weeks = [r for r in selected if isinstance(r['week'], int)]
        assert sorted(r['week'] for r in weeks) == list(range(1,8))
        aggregate = next(r for r in selected if r['week'] == 'ALL')
        assert sum(r['n'] for r in weeks) == aggregate['n']
        products.append(dict(target=target, procedure_id=aggregate['procedure_id'],
          history='H-MULTI', policy_id='H-MULTI-COMMON', product='lower_median',
          numerical_weeks=[r['week'] for r in weeks], n=aggregate['n'],
          forecast_rows=aggregate['forecast_rows'], fallback_rows=aggregate['fallback_rows'],
          mae=aggregate['mae'], numerical_floor='SEVEN_SCORED_WEEKS_NOT_OPERATIONAL_ADMISSION',
          vintage='CURRENT_REVISED_SOURCE_KICKOFF_PLUS_7D_AVAILABILITY_ASSUMPTION',
          actual_line_panels=[dict(weeks=[5,6,7],
             source='PROVIDER_LABELLED_RETAINED_BOARD',
             horizon='PER_OFFER_SOURCE_CLOCK_T90_QUALIFIED_KNOWN_TARGET_TIME',
             identity_suffix='known-target-time-v1',
             limitation='One W5 game absent; retained kickoff query vector must pass consumed-source cutoff audit'),
             dict(weeks=[8],source='SAVED_EARLY_B_FORECAST_VS_RETAINED_T90_THRESHOLD',
                  limitation='Separate earlier forecast product, not a simultaneous weekly Top Picks policy')]
             + ([dict(weeks=[2,3],source='C_PINNACLE_LAST_RECORDED_PREKICK',
                  limitation='Kickoff reconstruction; distinct timing/evidence panel, not 5-week extension of W5-W7')]
                if target == 'rec_yd' else [])))
        for week in range(1,8):
            slot = f'W{week:02}-{target}-H-MULTI-COMMON-{group}'
            fp = base/(slot+'-FIT.json')
            rp = base/(slot+'-FORECAST.json')
            fit, receipt = json.loads(fp.read_bytes()), json.loads(rp.read_bytes())
            # Byte hashes only. No pickle/object/model deserialization occurs.
            checks = {}
            for name, binding in [('model',fit['model']),('query',fit['query_features']),('prediction',receipt['packet'])]:
                path = a.private_root/binding['bundle_name']
                checks[name] = sha(path) == binding['sha256'] and path.stat().st_size == binding['bytes']
            assert all(checks.values()), slot
            query = json.loads(gzip.decompress((a.private_root/fit['query_features']['bundle_name']).read_bytes()))
            widths = sorted({len(r['features']) for r in query})
            assert widths == [len(fit['feature_columns'])]
            assert all(r['latest_consumed_feature_available'] is None
                       or r['latest_consumed_feature_available'] < r['query']['cutoff'] for r in query)
            fits.append(dict(slot=slot,fit_receipt=str(fp.relative_to(a.repo)),
                fit_receipt_sha256=sha(fp),forecast_receipt_sha256=sha(rp),
                model_sha256=fit['model']['sha256'],query_sha256=fit['query_features']['sha256'],
                prediction_sha256=receipt['packet']['sha256'],source_bytes_verified=checks,
                feature_columns=fit['feature_columns'],query_count=len(query),raw_feature_widths=widths,
                expected_imputed_width=2*len(fit['feature_columns']),
                consumed_source_before_query_cutoff=True,
                actual_source_publication_authenticated=False))
    bindings = {}
    for rel in ['docs/continuations/EXECUTION_CLOSURE_02_RESEARCH.txt',
                'reports/abc-championship/EXPORT_INDEX.json',
                'reports/post-wave-5w-v1/B-product-week-qualification-v3/B_PRODUCT_WEEK_QUALIFICATION.json.gz',
                'reports/post-wave-5w-v1/B_CATEGORY_PRODUCT_QUALIFICATION_SUMMARY.json',
                'nfl_v2/qualified_defense_wave.py','nfl_v2/qualified_defense_inputs.py',
                'nfl_v2/qualified_defense.py','nfl_v2/distribution_wave_v2.py',
                'tools/audit_saved_threshold_admissibility.py']:
        bindings[rel] = sha(a.repo/rel)
    result = dict(state='INDEPENDENT_READ_ONLY_SCOPE_REVIEW_COMPLETE_NO_RUNTIME_PARITY_CLAIM',
      at_utc=datetime.now(timezone.utc).isoformat(),source_bindings=bindings,
      products=products,restored_model_query_forecast_bindings=fits,
      existing_closed_checks=[
        'W1-W7 numerical scores, startup/fallback and exact recipe retained',
        'W5-W7 known-target-time saved-vector source/fit/context admission and threshold grading',
        'D1 completion W5-W7 query/model dimensions and stored split-index inspection; no predict/apply',
        'Saved leaf-ID PMF/CDF/typed-summary replay; no model runtime inference',
        'Scalar intercept/gate and contextual ranker tests completed, adverse results retained'],
      genuinely_missing_b_owned_check=dict(
        name='TRUSTED_RESTORED_21_MODEL_OUTPUT_FEATURE_ORDER_BATCH_SINGLE_CONSUMED_SOURCE_PARITY',
        minimum_dependencies='Exact 21 FIT/model/query/FORECAST bindings above, source CSVs and games bound by original protocol, original source/helper code, priors and fallback rules',
        steps=['Before inference freeze trusted provenance, source members, budget and retention',
          'Recreate exact ordered own+defense feature vectors including missingness and actual consumed game IDs',
          'Confirm raw D1=24/D2=29 and imputed D1=48/D2=58 with stored training-only design; reject reordered columns',
          'Batch versus single-row and reordered-query equivalence; mean and lower-median against retained packets',
          'Preserve per-position same-arm priors and startup/zero-history fallback after model prediction',
          'Check target outcomes/future rows cannot alter earlier consumed features; distinguish assumed availability from publication clocks'],
        does_not_authorize='No refit, recipe repair, new historical issuance, threshold rescore or website selector replay'),
      reporting_findings=[
        'Old category summary short D1/D2 aliases miss existing full-ID seven-week qualification witnesses. Correct metadata by explicit alias mapping, do not refit.',
        'Numerical seven-week proof does not give an actual-line or Top Picks policy five-week qualification.',
        'Do not concatenate W2-W3 Pinnacle kickoff, W5-W7 provider-clock replay and early W8 capture into one exact qualified product.',
        'Full historical participant board differs from the actual ex-ante offer board. Preserve unavailable and originally unselected offers.',
        'Supply public-safe manifests and permitted deterministic owner-local outputs; restricted models/rows cannot be moved publicly through an export index.',
        'Owner updater Chromium timeout before inference/capture is an owner runtime failure, not demonstrated model arithmetic defect. B must not dispatch a replacement.'],
      runtime_model_calls=0, fits=0, selection_replays=0, new_scoring=0,
      scope='Metadata/hash/retained aggregate inspection only; runtime parity remains for separately frozen B execution. Website owner alone owns full-board Top Picks replay.')
    a.output.parent.mkdir(parents=True,exist_ok=True)
    if a.output.exists(): raise FileExistsError(a.output)
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(state=result['state'],model_bindings=len(fits),products=len(products),output_sha256=sha(a.output))))

if __name__ == '__main__': main()
