"""Public aggregate result index. Native errors are never converted to accuracy."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import PurePosixPath

VERSION = 'v2-test-results-index-v1'
DIAGNOSTIC_KIND='NEW_EXPERIMENT_CURRENT_VINTAGE_PARTICIPANT_DIAGNOSTIC'
METRICS = {
    'mae': ('mae','MAE'), 'mse': ('mse','MSE'), 'rmse': ('rmse','RMSE'),
    'bias': ('bias',), 'p90_abs': ('p90_abs','p90'), 'p95_abs': ('p95_abs','p95'),
    'max_abs': ('max_abs','max_error'), 'brier': ('brier','Brier'),
    'log_loss': ('log_loss',), 'nll': ('NLL','nll'), 'crps': ('CRPS','crps'),
}
PRECISION = {'exact_rate': ('exact_rate',), 'abs_lt_1': ('abs_lt_1','error_strict_lt1'),
    'abs_le_1': ('abs_le_1','error_inclusive_le1'), 'abs_lt_5': ('abs_lt_5',),
    'abs_le_5': ('abs_le_5',), 'abs_lt_10': ('abs_lt_10',), 'abs_le_10': ('abs_le_10',)}
DEFINITIONS = {
    'selection_loss_rate': 'losses/(wins+losses) for the declared selected-side threshold panel; decided statistical crossing error, not MAE or profit',
    'mae': 'mean(abs(prediction - actual)); native target units; lower is better',
    'mse': 'mean((prediction - actual)^2); squared target units; lower is better',
    'rmse': 'sqrt(MSE); native target units; lower is better',
    'bias': 'mean(prediction - actual); signed native target units',
    'p90_abs': '90th percentile absolute error; source interpolation retained',
    'p95_abs': '95th percentile absolute error; source interpolation retained',
    'max_abs': 'maximum absolute error; native target units',
    'brier': 'mean((event_probability - binary_actual)^2); lower is better, compare prevalence baseline',
    'log_loss': 'mean(-log(probability assigned to observed binary event)); no percent accuracy conversion',
    'nll': 'source-reported negative log score; inspect source support/normalization before comparison',
    'crps': 'source-reported proper distribution score; inspect support and score definition',
}


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)


def safe_artifact(path):
    if not isinstance(path,str) or not path:raise ValueError('public repository-relative artifact required')
    p=PurePosixPath(path)
    if not isinstance(path,str) or p.is_absolute() or '..' in p.parts or '\\' in path or ':' in path:
        raise ValueError('public repository-relative artifact required')
    return path


def number(value):
    return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value)


def pick(mapping,keys):
    for key in keys:
        if key in mapping and mapping[key] is not None:return mapping[key],key
    return None,None


def count(mapping,keys):
    value,key=pick(mapping,keys)
    if value is None:return None,None
    if not number(value) or value<0 or int(value)!=value:
        raise ValueError('invalid declared sample count')
    return int(value),key


def precision_metric(rate,n,name,*,probability=False):
    rule='abs(prediction - actual) == 0' if name=='exact_rate' else (
        'abs(prediction - actual) '+('<=' if '_le_' in name else '<')+' '+name.rsplit('_',1)[1])
    result=dict(rate=rate,numerator=None,denominator=n,definition=rule,
        kind='probability_residual_precision_not_binary_accuracy' if probability else 'numeric_point_precision_accuracy',
        numerator_provenance=None,missing_reason=None)
    if rate is None:
        result['missing_reason']='precision_rate_not_reported';return result
    if not number(rate) or not 0<=rate<=1:raise ValueError('invalid precision rate')
    if n is None or n==0:
        result['missing_reason']='source_denominator_missing_or_zero';return result
    hits=rate*n;rounded=round(hits)
    if not math.isclose(hits,rounded,rel_tol=0,abs_tol=1e-7):
        result['missing_reason']='reported_rate_times_n_does_not_recover_integer_numerator'
    else:
        result['numerator']=rounded
        result['numerator_provenance']='derived_from_source_rate_times_declared_n; not a fresh row count'
    return result


def evaluation(row,artifact,*,year_record=None,source_link=None):
    if row.get('record_kind')=='prop_selection_evaluation':
        return prop_selection_evaluation(row,artifact,year_record=year_record,source_link=source_link)
    safe_artifact(artifact)
    coverage=row.get('coverage',{})
    if not isinstance(coverage,dict):raise ValueError('coverage must be aggregate object')
    n,n_field=count(row,('n',))
    if n is None:n,n_field=count(coverage,('scored_rows','scored','n','rows','paired','supported_played_outcomes'))
    games,games_field=count(row,('unique_games',))
    if games is None:games,games_field=count(coverage,('scored_games','distinct_scored_games','unique_games','games'))
    offered,offered_field=count(row,('forecast_rows',))
    if offered is None:offered,offered_field=count(coverage,('offered_rows','offered','population_rows','planned','forecast'))
    fallback,fallback_field=count(row,('fallback_rows',))
    if fallback is None:fallback,fallback_field=count(coverage,('fallback_rows','fallback_offered','fallback'))
    scored_fallback,scored_fallback_field=count(row,('scored_fallback_rows',))
    if scored_fallback is None:
        scored_fallback,scored_fallback_field=count(coverage,('scored_fallback_rows','fallback_scored','scored_fallbacks'))
    metrics={};missing={};metric_source={};metric_status={}
    for name,aliases in METRICS.items():
        value,key=pick(row,aliases)
        if name in {'log_loss','nll'} and (value=='Infinity' or (isinstance(value,float) and value==math.inf)):
            metrics[name]=None;metric_source[name]=key
            metric_status[name]='positive_infinite_loss'
            missing[name]='infinite_loss_retained_explicitly; not zero or missing success';continue
        if value is not None and not number(value):raise ValueError('nonfinite/invalid metric requires explicit failure record')
        if value is not None and name not in {'bias','nll'} and value<0:raise ValueError('negative nonnegative loss')
        metrics[name]=value;metric_source[name]=key
        missing[name]=None if value is not None else 'metric_null_or_not_reported_in_source'
        metric_status[name]='finite' if value is not None else 'not_reported_or_null'
    target=row.get('target');probability=target=='anytime_td'
    precision={name:precision_metric(pick(row,aliases)[0],n,name,probability=probability)
               for name,aliases in PRECISION.items() if pick(row,aliases)[0] is not None}
    any_precision=bool(precision)
    years=(year_record or {}).get('evaluation_seasons') or ([row['season']] if 'season' in row else None)
    weeks=(year_record or {}).get('evaluation_weeks') or ([row['week']] if 'week' in row else None)
    procedure=row.get('procedure_id',row.get('procedure_label'))
    identity=dict(source_record_id=row.get('record_id'),source_pointer=row.get('source_pointer'),
        procedure_id=procedure,category=target,product_id=row.get('product_id'),
        evaluation_panel_id=row.get('evaluation_panel_id'),population=row.get('population'),
        period=row.get('period'),season=row.get('season'),week=row.get('week'),
        position=row.get('position'),fallback_view=row.get('fallback_view'),
        history_regime=row.get('history_regime','UNKNOWN_NOT_H_CLASSIFIED'))
    if not all(identity[k] for k in ('procedure_id','category','product_id','evaluation_panel_id')):
        raise ValueError('method/category/product/panel identities required')
    # New optional diagnostic dimensions must not rename previously indexed views.
    hash_identity={k:v for k,v in identity.items() if k not in {'position','fallback_view'} or v is not None}
    test_id='TEST-'+hashlib.sha256(canonical([artifact,hash_identity]).encode()).hexdigest()[:20]
    unit=('yards' if target in {'pass_yd','rush_yd','rec_yd','rush_rec_yd'} else
          'count' if target in {'pass_td','pass_cmp','pass_att','pass_int','rush_att','rec'} else
          'probability' if probability else 'chart points' if target=='nick-chart-ppr-v1' else 'source-specific points')
    primary='brier' if probability else 'mae'
    return dict(test_id=test_id,index_version=VERSION,kind=row.get('record_kind','forecast_evaluation_view'),**identity,
        seasons=years,weeks=weeks,dates_missing_reason=None if years and weeks else 'exact seasons/weeks not fully reported; inspect linked frozen source',
        evidence=row.get('evidence','UNKNOWN'),n=n,n_source_field=n_field,
        n_missing_reason=None if n is not None else 'scored denominator not reported',
        games=games,games_source_field=games_field,game_count_scope='source-reported; exact scored scope requires source contract',
        games_missing_reason=None if games is not None else 'distinct scored-game count not supplied; requires retained-row census',
        forecast_or_offered_rows=offered,offered_source_field=offered_field,
        coverage_fraction=n/offered if n is not None and offered else None,
        coverage_definition='scored denominator / source-declared offered or forecast rows; not forecast accuracy',
        coverage_source=coverage,fallback_rows=fallback,fallback_source_field=fallback_field,
        scored_fallback_rows=scored_fallback,scored_fallback_source_field=scored_fallback_field,
        fallback_missing_reason=None if fallback is not None else 'fallback count not reported',
        native_units=unit,primary_metric=primary,primary_error=metrics[primary],metrics=metrics,
        metric_source_fields=metric_source,metric_missing_reasons=missing,metric_status=metric_status,
        source_infinite_nll_rows=row.get('infinite_NLL'),
        metric_definition_set=VERSION,metric_provenance_notes={'mse':row.get('MSE_note')},
        precision_metrics=precision or None,
        accuracy_status=('not_applicable_without_registered_binary_decision_rule' if probability else
                         'precision_rates_reported' if any_precision else 'not_reported_no_accuracy_inferred_from_error'),
        accuracy_missing_reason=('probability residual tolerances are not event classification or pick accuracy' if probability else
                                 None if any_precision else 'no exact-match/tolerance rate supplied; MAE cannot become percent accuracy'),
        uncertainty=row.get('uncertainty'),source_artifact=artifact,source_artifact_sha256=None,
        cohort_limit=row.get('cohort_limit'),source_vintage=row.get('source_vintage'),
        procedure_family_id=row.get('procedure_family_id'),feature_memory_policy=row.get('feature_memory_policy'),
        upstream_source_id=row.get('source_id'),upstream_source_link=source_link,
        software_checks=None,nfl_accuracy_from_software_tests=None)


def prop_selection_evaluation(row,artifact,*,year_record=None,source_link=None):
    """Extend the existing registry with actual selection denominators, not MAE."""
    ordinary=dict(row,record_kind='forecast_evaluation_view')
    record=evaluation(ordinary,artifact,year_record=year_record,source_link=source_link)
    stats=dict(row['selection_metrics'])
    wins=stats['wins']if'wins'in stats else stats['WIN']
    losses=stats['losses']if'losses'in stats else stats['LOSS']
    states=stats.get('status_counts',{})
    outer=row.get('forecast_rows')
    complete_states=(isinstance(outer,int)and bool(states)and
        all(isinstance(v,int)and not isinstance(v,bool)and v>=0 for v in states.values())and
        sum(states.values())==outer)
    stats.update(wins=wins,losses=losses)
    for name,state in [('pushes','PUSH'),('voids','VOID'),('pending','PENDING'),
                       ('missing_actual','MISSING_ACTUAL'),('unknown_participation','UNKNOWN_PARTICIPATION'),
                       ('unresolved_contract','UNRESOLVED_CONTRACT')]:
        if name not in stats:stats[name]=states.get(state,stats.get(state,0 if complete_states else None))
    denom=stats.get('denominators',{})
    for name,source in [('eligible_opportunities','outer_rows'),('selected_opportunities','selected'),('abstentions','abstained')]:
        if name not in stats:stats[name]=denom.get(source)
    if 'eligible_rank_pool_n'in stats:
        stats['eligible_opportunities']=stats['eligible_rank_pool_n']
    elif 'selection_pool_count'in stats:
        stats['eligible_opportunities']=stats['selection_pool_count']
    stats['source_pool_opportunities']=stats.get('selection_pool_count',denom.get('outer_rows'))
    if stats.get('abstentions')is None:
        stats['abstentions']=stats.get('abstentions_outside_selected_partition')
    if stats.get('selected_opportunities')is None and complete_states:
        stats['selected_opportunities']=outer-denom.get('abstained',states.get('ABSTAIN',0))
    eligible=stats.get('eligible_opportunities')
    stats['selection_coverage']=stats.get('selected_opportunities')/eligible if eligible and stats.get('selected_opportunities')is not None else None
    book_states=stats.get('bookmaker_settlement_status_counts',{})
    stats['book_settlement_status_counts']=book_states or None
    if any(isinstance(v,bool)or not isinstance(v,int)or v<0 for v in(wins,losses)):
        raise ValueError('nonnegative integer selection counts required')
    n=wins+losses
    if row['n']!=n:raise ValueError('decided-pick denominator mismatch')
    loss=losses/n if n else None;hit=wins/n if n else None
    if row.get('selection_loss_rate')!=loss:raise ValueError('selection error rate mismatch')
    record.update(kind='prop_selection_evaluation',primary_metric='selection_loss_rate',primary_error=loss,
        native_units='directional_error_fraction',selection_metrics=stats,
        period=row.get('statistic_period'),season_type=row.get('season_type'),
        statistic_period=row.get('statistic_period'),period_provenance=row.get('period_provenance'),
        side=row.get('side'),strategy=row.get('strategy'),horizon=row.get('horizon',row.get('horizon_id')),
        threshold_provenance=row.get('threshold_provenance',row.get('line_source')),
        selection_evidence=row.get('selection_evidence',
            'RETROSPECTIVE_RULE_REPLAY_ON_ORIGINAL_SELECTION_POOL'if row.get('K')is not None else
            'ORIGINAL_RECORDED_SELECTION'if row.get('strategy')=='original'else'RETROSPECTIVE_RULE_REPLAY'),
        probability_conditioning=row.get('probability_conditioning'),
        accuracy_status='statistical_threshold_crossing_only' if row.get('settlement_verified') is not True else 'verified_settled_selection',
        accuracy_missing_reason=None if n else 'no_decided_supported_selections',
        precision_metrics={'decided_pick_hit_rate':dict(rate=hit,numerator=wins if n else None,denominator=n,
            definition='wins/(wins+losses); pushes/voids/pending/unknown excluded from decided denominator and reported separately',
            kind='selection_direction_accuracy',numerator_provenance='exact_retained_selection_row_count',missing_reason=None if n else 'no_decided_picks')})
    record['metrics']['selection_loss_rate']=loss
    record['metric_status']['selection_loss_rate']='finite'if n else'no_decided_picks'
    record['metric_missing_reasons']['selection_loss_rate']=None if n else'no_decided_picks'
    record['metric_source_fields']['selection_loss_rate']='selection_loss_rate'
    record['metric_definition_set']='v2-prop-selection-score-v1'
    record['cohort_evidence']='RETROSPECTIVE_RECONSTRUCTED_PREGAME_FEATURES'if str(row.get('cohort_id','')).startswith('reconstructed:')else'SAVED_SOURCE_OR_ALL_POOL'
    for field in ('cohort_id','K','rank_scope','time_panel_id','season_alias_of_week_view','alias_of_record_id',
                  'unique_players','unique_player_games','unique_weeks','decided_unique_games',
                  'decided_unique_players','decided_unique_player_games','decided_week_count',
                  'registered_week_count','registered_weeks','selected_week_count','overtime'):
        record[field]=row.get(field)
    if record['unique_weeks']is None:record['unique_weeks']=row.get('decided_week_count')
    return record


def software_receipt(artifact,receipt):
    safe_artifact(artifact)
    checks=receipt.get('tests_run',receipt.get('hand_contract_checks',receipt.get('independent_fictional_checks')))
    if checks is None:raise ValueError('explicit software check count required')
    if not number(checks) or checks<0 or int(checks)!=checks:raise ValueError('invalid software check count')
    return dict(test_id='SOFTWARE-'+hashlib.sha256(artifact.encode()).hexdigest()[:20],index_version=VERSION,
        kind='software_verification',source_artifact=artifact,source_artifact_sha256=None,
        software_checks=int(checks),software_status=receipt.get('status'),
        evidence='SOFTWARE_CHECKS_ONLY',n=None,games=None,metrics=None,precision_metrics=None,
        accuracy_status='not_applicable_software_check',
        accuracy_missing_reason='software correctness checks have no NFL prediction accuracy denominator',
        nfl_accuracy_from_software_tests=None)


def validate_index(records):
    seen=set()
    for r in records:
        if r['test_id'] in seen:raise ValueError('duplicate evaluation identity; do not inflate views')
        seen.add(r['test_id']);safe_artifact(r['source_artifact'])
        if r['kind']=='software_verification':
            if r.get('metrics') is not None or r.get('precision_metrics') is not None or r.get('n') is not None:
                raise ValueError('software check must not claim NFL accuracy')
            continue
        if r['kind'] not in {'forecast_evaluation_view',DIAGNOSTIC_KIND,'prop_selection_evaluation'}:raise ValueError('unknown test kind')
        if r['primary_error']!=r['metrics'][r['primary_metric']]:raise ValueError('primary metric mismatch')
        for p in (r['precision_metrics'] or {}).values():
            if p['numerator'] is not None:
                if not p['denominator'] or not 0<=p['numerator']<=p['denominator']:
                    raise ValueError('invalid precision numerator/denominator')
                if not math.isclose(p['numerator']/p['denominator'],p['rate'],rel_tol=0,abs_tol=1e-9):
                    raise ValueError('precision rate/count mismatch')
    return records


def diagnostic_row(row,season_coverage):
    """Normalize one frozen CSV view without pooling or selecting any procedure."""
    dims=('target','population','history_regime','product','season','week','position','fallback_view')
    if any(not row.get(k) for k in dims):raise ValueError('diagnostic view dimensions required')
    normalized=dict(procedure_id='empirical-player-history-control-v1',target=row['target'],
        product_id=row['product'],evaluation_panel_id='nflverse-observed-stat-row-2022-2026-current-vintage-diagnostic-v1',
        population=row['population'],history_regime=row['history_regime'],position=row['position'],
        fallback_view=row['fallback_view'],period='REG',record_kind=DIAGNOSTIC_KIND,
        evidence='NEW_EXPERIMENT',cohort_limit='retrospective statistical-row/physical-participation cohort; primary rushing QB+RB; extended disjoint, not full exante population',
        source_vintage='current_vintage_reconstruction; kickoff+7day assumed available, not authenticated publication',
        source_pointer='CSV dimensions: '+canonical({k:row[k] for k in dims}))
    for source,dest in [('scored_n','n'),('forecast_queries','forecast_rows'),('fallback_n','fallback_rows')]:
        normalized[dest]=int(row[source])
    if row['season'].isdigit():normalized['season']=int(row['season'])
    if row['week'].isdigit():normalized['week']=int(row['week'])
    for metric in [*METRICS,*PRECISION]:
        if row.get(metric) not in (None,''):normalized[metric]=float(row[metric])
    if int(row.get('infinite_log_losses') or 0):
        normalized['log_loss']='Infinity';normalized['infinite_NLL']=int(row['infinite_log_losses'])
    years=[int(row['season'])] if row['season'].isdigit() else [int(s) for s in season_coverage]
    weeks=([int(row['week'])] if row['week'].isdigit() else
        season_coverage[row['season']] if row['season'].isdigit() else season_coverage)
    return normalized,dict(evaluation_seasons=years,evaluation_weeks=weeks)


def hgb_row(row):
    """New HGB fixed-objective aggregate; no reinterpretation as a law or old run."""
    objectives={'absolute_error_point','squared_error_mean','log_loss_probability'}
    dims=('target','population','history_regime','objective','week','position')
    if any(not row.get(k) for k in dims) or row['objective'] not in objectives:
        raise ValueError('registered HGB aggregate dimensions/objective required')
    if (row['target']=='anytime_td') != (row['objective']=='log_loss_probability'):
        raise ValueError('HGB point/probability objective mismatch')
    normalized=dict(procedure_id='hgb-direct-history-controls-v1:'+row['objective'],
        procedure_family_id='HGB_DIRECT_HISTORY_CONTROL',target=row['target'],product_id=row['objective'],
        evaluation_panel_id='hgb-source-matched-observed-participant-2026-W1-W7-v1',
        population=row['population'],history_regime=row['history_regime'],position=row['position'],
        season=2026,period='REG',record_kind=DIAGNOSTIC_KIND,evidence='NEW_EXPERIMENT',
        cohort_limit='retrospective statistical-row/physical-participation cohort; primary rushing QB+RB, extended disjoint WR+TE; QB passing only',
        source_vintage='current_vintage_reconstruction; kickoff+7day assumed availability; weekly fitting and per-game query features',
        feature_memory_policy='common2022-start earlier available own-target features in all arms; H-CURRENT is current-season fitting, not pure current information',
        source_pointer='HGB CSV/JSON dimensions: '+canonical({k:row[k] for k in dims}))
    for source,dest in [('scored_n','n'),('forecast_queries','forecast_rows'),('fallback_n','fallback_rows')]:
        normalized[dest]=int(row[source])
    if str(row['week']).isdigit():normalized['week']=int(row['week'])
    normalized['coverage']={k:row[k] for k in ('missing_actual_n','constant_zero_n','fallback_rate') if k in row}
    for metric in [*METRICS,*PRECISION]:
        if row.get(metric) not in (None,''):normalized[metric]=float(row[metric])
    if int(row.get('infinite_log_losses') or 0):
        normalized['log_loss']='Infinity';normalized['infinite_NLL']=int(row['infinite_log_losses'])
    return normalized,dict(evaluation_seasons=[2026],evaluation_weeks=[int(row['week'])] if str(row['week']).isdigit() else list(range(1,8)))
