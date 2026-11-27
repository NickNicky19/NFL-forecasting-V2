"""Three authorized representative fits plus saved-law checks; no offer scoring.

Independent stable likelihood/gradient arithmetic, fixed registered settings.
Only aggregate verification is saved, never a duplicate forecast or score file.
"""
import copy
import gzip
import hashlib
import json
import math
import resource
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy import optimize, special, stats
from threadpoolctl import threadpool_limits

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from nfl_v2 import player_context_matchup as ctx, qb_pass_mix_information as skill
from nfl_v2.qb_depth_catchability import DepthHistory
from nfl_v2.qb_depth_catchability_v2 import ConvergedDepthCompletionModel


ROOT = Path.cwd()
BASE = ROOT / 'reports/information-skill-01/B'
OUT = BASE / 'independent/FIT_REPRODUCTION_V1.json'
INPUT = ROOT / 'reports/information-first-20261112-01/B/completion-wave-v1/QB_CONTEXT_W1_W9_INPUTS_V1.json.gz'
CHART = ROOT / 'reports/player-context-completion-decision-01/B/source-depth-v1/FTN_DEPTH_QB_GAME_INPUTS.json.gz'
PARENT = ROOT / 'reports/targeted-accuracy-w1w9-01/B/wave-v1/predictions'


def read(path):
    return json.loads(gzip.decompress(path.read_bytes()))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def clean(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [clean(v) for v in value]
    return value


def digest(value):
    return hashlib.sha256(json.dumps(clean(value), sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def stripped(row):
    return {k: row[k] for k in ('game_id', 'player_id', 'season', 'week', 'team', 'opponent', 'kickoff')}


def main():
    started = time.monotonic()
    cpu = time.process_time()
    if OUT.exists():
        raise RuntimeError('Independent attempt receipt already exists; no implicit retry')
    receipt = dict(id='B-INFORMATION-SKILL-INDEPENDENT-FIT-REPRODUCTION-v1', started_UTC=now(),
                   status='STARTED_BEFORE_INDEPENDENT_OPTIMIZERS',
                   authority='Root bounded allocation: exactly at most3 representative2026W1 fits, CPU90/RSS1GiB, no other origins/retuning.',
                   attempts=[], calls_max=3, CPU_cap_seconds=90, RSS_cap_bytes=1073741824,
                   bootstrap_failure_preserved=dict(error='ModuleNotFoundError: nfl_v2 before main/optimizer entry',
                       repaired='Explicit repository import path; no model/source/objective change', optimizer_calls=0,
                       shell_wall_seconds=0.826167631, CPU_seconds=None, CPU_scope='Not metered; retained as setup overhead'),
                   tolerances=dict(coefficient_absolute=1e-5, prediction_absolute=1e-7,
                                   objective_absolute=1e-6, objective_relative=1e-10),
                   source_inputs={str(p.relative_to(ROOT)): dict(bytes=p.stat().st_size, SHA256=sha(p)) for p in (INPUT, CHART)},
                   code_SHA256={str(p.relative_to(ROOT)): sha(p) for p in (Path(__file__).resolve(), ROOT/'nfl_v2/qb_pass_mix_information.py')},
                   independent_implementation='Separate stable log-likelihood and sum-based gradient; independent conversion/mixer design assembly. Shared qualified history/profile counts and accepted parent numeric builder.',
                   limits=['No private offers or actual-line scoring.', 'Reproduction does not authenticate historical source clocks.',
                           'No new forecast export, selector, model setting or global ledger write.'])

    def resources():
        return dict(CPU_seconds=time.process_time()-cpu, wall_seconds=time.monotonic()-started,
                    peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)

    def save():
        receipt['resource'] = resources()
        OUT.write_text(json.dumps(clean(receipt), indent=2, allow_nan=False)+'\n')

    def check():
        r = resources()
        if r['CPU_seconds'] > 90 or r['peak_RSS_bytes'] > 1073741824:
            raise RuntimeError('Independent reproduction resource cap reached')

    def fit_record(name, objective, beta, settings):
        check()
        if len(receipt['attempts']) >= 3:
            raise RuntimeError('Independent optimizer cap3')
        attempt = dict(attempt=len(receipt['attempts'])+1, slot=name, started_UTC=now(),
                       before_resource=resources(), state='CHARGED_BEFORE_OPTIMIZER',
                       settings=settings, NFL_fit=True)
        receipt['attempts'].append(attempt)
        save()
        fitted = optimize.minimize(objective, beta, jac=True, method='L-BFGS-B', options=settings)
        attempt.update(state='RETURNED', completed_UTC=now(), after_resource=resources(),
                       success=bool(fitted.success), iterations=int(fitted.nit), message=str(fitted.message),
                       objective=float(fitted.fun), finite=bool(np.isfinite(fitted.x).all()))
        save()
        check()
        return fitted, attempt

    save()
    try:
        with threadpool_limits(limits=1):
            rows = ctx.load_inputs(INPUT)
            history = ctx.ContextHistory(rows, 8, 20.)
            chart = DepthHistory(rows, read(CHART), 8, 20.)
            profiles = skill.PassMixHistory(history)
            qs = [r for r in rows if (r['season'], r['week']) == (2026, 1)]
            cutoff = min(q['kickoff'] for q in qs)
            train = history.eligible(cutoff, 2025)
            membership = hashlib.sha256(json.dumps([(r['game_id'], r['player_id']) for r in train]).encode()).hexdigest()
            levels = {field: sorted({r[field] for r in train}) for field in skill.GROUP_ORDER}
            columns = {}; width = len(skill.CONVERSION_FEATURE_ORDER)
            for field in skill.GROUP_ORDER:
                columns[field] = {v: width+i for i, v in enumerate(levels[field])}
                width += len(levels[field])
            parent_numeric = ConvergedDepthCompletionModel(values=True, penalty=20.)

            def independent_values(q):
                d = profiles.describe(q)
                team = np.log((d['team_counts']+20.*d['league_mix']) /
                              (float(np.sum(d['team_counts']))+20.) / d['base_mix'])
                defense = np.log((d['opponent_counts']+100.*d['league_mix']) /
                                 (d['opponent_expected']+100.*d['league_mix']))
                return d, team, defense

            def conversion_matrix(q):
                d, team, defense = independent_values(q)
                numeric = np.vstack([np.r_[parent_numeric.numeric(q, history, chart, j), team[j], defense[j]]
                                     for j in range(25)])
                np.testing.assert_allclose(numeric, skill.AugmentedConversion().matrix(q, history, chart, profiles), atol=1e-14, rtol=0)
                x = np.zeros((25, width)); x[:, :len(skill.CONVERSION_FEATURE_ORDER)] = numeric
                for field in skill.GROUP_ORDER:
                    col = columns[field].get(q[field])
                    if col is not None:
                        x[:, col] = 1.
                return x

            xx, nn, yy = [], [], []
            for row in train:
                x = conversion_matrix(stripped(row))
                for j, (n, c) in enumerate(zip(row['context_attempts'], row['context_completions'])):
                    if n:
                        xx.append(x[j]); nn.append(n); yy.append(c)
            x, n, y = np.asarray(xx), np.asarray(nn), np.asarray(yy)
            penalty = np.r_[np.full(25, 2.), np.full(len(skill.CONVERSION_FEATURE_ORDER)-25, 10.),
                            np.full(width-len(skill.CONVERSION_FEATURE_ORDER), 20.)]

            def conversion_objective(beta):
                eta = x@beta
                loss = -np.sum(y*special.log_expit(eta)+(n-y)*special.log_expit(-eta))
                gradient = np.sum((n*special.expit(eta)-y)[:, None]*x, axis=0)
                return float(loss+.5*np.sum(penalty*beta*beta)), gradient+penalty*beta

            conv_fit, conv_attempt = fit_record('2026-W01-C1', conversion_objective, np.zeros(width),
                                                dict(maxiter=600, ftol=1e-10, gtol=1e-6))
            source_path = BASE/'wave-v1/fits/2026-W01-C1.json.gz'; source = read(source_path)
            restored = skill.AugmentedConversion.restore(source['model'])
            assert source['fit_cutoff'] == cutoff and source['training_membership_sha256'] == membership
            assert restored.levels == levels
            diff = float(np.max(np.abs(conv_fit.x-restored.beta)))
            prediction_diff = max(float(np.max(np.abs(special.expit(conversion_matrix(stripped(q))@conv_fit.x)-
                                                          restored.probabilities(stripped(q), history, chart, profiles)))) for q in qs)
            original_obj = conversion_objective(restored.beta)[0]
            conv_attempt['comparison'] = dict(source_SHA256=sha(source_path), training_membership_match=True,
                training_rows=len(train), coefficient_max_absolute_difference=diff, query_probability_max_absolute_difference=prediction_diff,
                objective_difference=abs(conv_fit.fun-original_obj), independent_success=bool(conv_fit.success),
                tolerance_pass=bool(diff<=1e-5 and prediction_diff<=1e-7 and abs(conv_fit.fun-original_obj)<=1e-6+1e-10*abs(original_obj)),
                consumed_new_value_columns=[])
            conv_attempt['comparison']['consumed_new_value_columns'] = [
                dict(name=skill.CONVERSION_FEATURE_ORDER[j], training_nonzero=int(np.count_nonzero(x[:, j])),
                     value_min=float(x[:, j].min()), value_max=float(x[:, j].max()),
                     source_fitted_coefficient=float(restored.beta[j]), independent_fitted_coefficient=float(conv_fit.x[j]))
                for j in (len(skill.CONVERSION_FEATURE_ORDER)-2, len(skill.CONVERSION_FEATURE_ORDER)-1)]
            save()

            def design(q, enriched):
                d, team, defense = independent_values(q)
                columns = [np.log(d['base_mix']/d['league_mix'])]
                if enriched:
                    columns += [team, defense]
                return np.log(d['base_mix']), np.column_stack(columns)

            for name, enriched in [('R0', False), ('R1', True)]:
                prepared = [design(stripped(r), enriched) for r in train]
                offset = np.asarray([d[0] for d in prepared]); xm = np.asarray([d[1] for d in prepared])
                ym = np.asarray([r['context_attempts'] for r in train], dtype=float); nm = ym.sum(axis=1)
                width_m = 24+xm.shape[2]; pm = np.r_[np.full(24, 20.), np.full(xm.shape[2], 10.)]

                def multinomial_objective(beta):
                    eta = offset+np.r_[beta[:24], 0.]+np.sum(xm*beta[None, None, 24:], axis=2)
                    log_probability = eta-special.logsumexp(eta, axis=1, keepdims=True)
                    residual = nm[:, None]*np.exp(log_probability)-ym
                    loss = -np.sum(ym*log_probability)+.5*np.sum(pm*beta*beta)
                    gradient = np.r_[np.sum(residual[:, :24], axis=0),
                                     np.sum(residual[:, :, None]*xm, axis=(0, 1))]+pm*beta
                    return float(loss), gradient

                fitted, attempt = fit_record('2026-W01-'+name, multinomial_objective, np.zeros(width_m),
                                              dict(maxiter=300, ftol=1e-10, gtol=1e-6))
                source_path = BASE/'wave-v1/fits'/('2026-W01-'+name+'.json.gz'); source = read(source_path)
                restored_mix = skill.CompositionModel.restore(source['model'])
                assert source['fit_cutoff']==cutoff and source['training_membership_sha256']==membership
                pred_diff=0.; scalar_vector_diff=0.
                for q in qs:
                    off, design_x = design(stripped(q), enriched)
                    independent = special.softmax(off+np.r_[fitted.x[:24], 0.]+np.sum(design_x*fitted.x[None, 24:], axis=1))
                    original = restored_mix.probabilities(stripped(q), profiles)
                    pred_diff = max(pred_diff, float(np.max(np.abs(independent-original))))
                    scalar_eta = np.asarray([off[j]+(restored_mix.beta[j] if j<24 else 0.)+
                                             sum(design_x[j, k]*restored_mix.beta[24+k] for k in range(design_x.shape[1]))
                                             for j in range(25)])
                    scalar_vector_diff=max(scalar_vector_diff,float(np.max(np.abs(special.softmax(scalar_eta)-original))))
                original_obj=multinomial_objective(restored_mix.beta)[0]
                diff=float(np.max(np.abs(fitted.x-restored_mix.beta)))
                attempt['comparison']=dict(source_SHA256=sha(source_path), training_membership_match=True,
                    coefficient_max_absolute_difference=diff, query_probability_max_absolute_difference=pred_diff,
                    scalar_vector_max_absolute_difference=scalar_vector_diff, objective_difference=abs(fitted.fun-original_obj),
                    tolerance_pass=bool(diff<=1e-5 and pred_diff<=1e-7 and abs(fitted.fun-original_obj)<=1e-6+1e-10*abs(original_obj)),
                    named_feature_coefficients={field:float(restored_mix.beta[24+j])for j,field in enumerate(restored_mix.feature_order)},
                    consumed_feature_nonzero_counts={field:int(np.count_nonzero(xm[:, :, j]))for j,field in enumerate(restored_mix.feature_order)})
                save()

            parents={}
            for path in sorted(PARENT.glob('2026-*.json.gz')):
                for row in read(path)['rows']:
                    if row['method']=='M2_C2_BIN':
                        parents[row['game_id'],row['player_id']]=row
            count=0; identities=set(); max_mass_error=0.; max_mean_error=0.; max_joint_error=0.; max_push_error=0.
            minima=1.; monotonic=True; attempt_matches=True; law_finite=True
            bindings={}
            for path in sorted((BASE/'wave-v1/predictions').glob('2026-*.json.gz')):
                bindings[str(path.relative_to(ROOT))]=sha(path)
                for row in read(path)['rows']:
                    key=row['game_id'],row['player_id']; identities.add(key);count+=1
                    components=row['components']; a=components['attempt_law']; p=components['integrated_completion_probability']
                    attempt_matches &= a==parents[key]['components']['attempt_law']
                    m=np.asarray(components['predicted_context_mix']); pc=np.asarray(components['conditional_completion_probability'])
                    assert len(m)==len(pc)==25 and np.isfinite(m).all() and np.isfinite(pc).all()
                    assert np.all(m>=0) and np.all((pc>=0)&(pc<=1)) and abs(m.sum()-1.)<1e-10
                    assert abs(float(m@pc)-p)<1e-12
                    mean=a['mean']*p;shape=a['shape'];law=row['law']
                    assert law['shape']==shape and abs(law['mean']-mean)<1e-10
                    max_mean_error=max(max_mean_error,abs(row['mean']-mean))
                    if mean:
                        nbp=shape/(shape+mean); top=int(stats.nbinom.isf(1e-12,shape,nbp)); grid=np.arange(top+1)
                        mass=stats.nbinom.pmf(grid,shape,nbp); cdf=stats.nbinom.cdf(grid,shape,nbp)
                    else:
                        mass=np.asarray([1.]);cdf=np.asarray([1.]);top=0
                    minima=min(minima,float(mass.min()));max_mass_error=max(max_mass_error,abs(float(mass.sum())-1.))
                    monotonic &= bool(np.all(np.diff(cdf)>=-1e-14))
                    law_finite &= bool(np.isfinite(mass).all() and np.isfinite(cdf).all())
                    restored_law=ctx.CountLaw(mean,shape)
                    median=row['lower_median']; event=ctx.exact_probabilities(restored_law,float(median))
                    max_push_error=max(max_push_error,abs(event['push']-restored_law.pmf(median)),abs(sum(event.values())-1.))
                    assert ctx.exact_probabilities(restored_law,median+.5)['push']==0
                    assert restored_law.cdf(-1)==0
                    assert restored_law.cdf(median)>=.5-1e-12
                    if median>0:assert restored_law.cdf(median-1)<.5+1e-12
                    for aa in (0,1,5,35):
                        c=np.arange(aa+1);amass=stats.nbinom.pmf(aa,shape,shape/(shape+a['mean'])) if a['mean'] else float(aa==0)
                        joint=amass*stats.binom.pmf(c,aa,p)
                        max_joint_error=max(max_joint_error,abs(float(joint.sum())-amass))
                        assert np.all(joint>=0) and stats.binom.pmf(aa+1,aa,p)==0
            assert count==1260 and len(identities)==315
            receipt['saved_law_checks']=dict(rows_checked=count, unique_queries=len(identities), all9origins=True,
                parent_attempt_bindings_identical=bool(attempt_matches), finite=bool(law_finite),
                nonnegative_min_mass=minima, max_tail_bounded_mass_error=max_mass_error, CDF_monotone=bool(monotonic),
                max_mean_difference=max_mean_error, max_joint_attempt_mass_error=max_joint_error,
                max_push_or_total_mass_error=max_push_error, threshold_contract='Exact integerpush/halfpoint no push; lower median; no actual offers accessed.',
                coherent_support='Explicit A~NB and C|A~Binomial construction; C>A mass0, attempted marginal mass preserved.',
                numerical_mass_tolerance=2e-11, forecast_file_SHA256=bindings,
                all_passed=bool(attempt_matches and law_finite and monotonic and minima>=0 and max_mass_error<2e-11 and
                                max_mean_error<1e-10 and max_joint_error<1e-12 and max_push_error<1e-12))
            receipt['optimizer_calls']=len(receipt['attempts'])
            receipt['all_fit_comparisons_passed']=all(a['comparison']['tolerance_pass'] and a['success'] for a in receipt['attempts'])
            receipt['all_passed']=receipt['all_fit_comparisons_passed'] and receipt['saved_law_checks']['all_passed']
            receipt['status']='COMPLETE_PASS' if receipt['all_passed'] else 'COMPLETE_WITH_PRESERVED_FAILURE'
            receipt['completed_UTC']=now();save();check()
            print(json.dumps(dict(status=receipt['status'], optimizer_calls=receipt['optimizer_calls'],
                                 fits=[dict(slot=a['slot'],comparison=a['comparison'])for a in receipt['attempts']],
                                 saved_law_checks={k:v for k,v in receipt['saved_law_checks'].items()if k!='forecast_file_SHA256'},
                                 resource=resources()),indent=2))
            if not receipt['all_passed']:
                raise RuntimeError('Independent check failed under predeclared tolerances; no automatic retry')
    except Exception as error:
        receipt['status']='FAILED_PRESERVED_NO_AUTOMATIC_RETRY'
        receipt['error']=str(error);receipt['failed_UTC']=now();save()
        raise


if __name__=='__main__':
    main()
