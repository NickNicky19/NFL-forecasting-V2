"""Source-bound prediction repair for the preserved first seasonal wave.

No models are fitted. This changes the fallback recipe on affected rows; it is
not described as a pure scorer correction or a new forecasting improvement.
"""
from __future__ import annotations
import collections,csv,gzip,io,json,math,os,time
from pathlib import Path
import numpy as np
from . import seasonal_rolling as original,seasonal_rolling_v2 as corrected
from .distribution_laws import Law
from .result_index import evaluation

VERSION='v2-seasonal-original-recipe-continuity-repair-v1'
sha=original.sha;now=original.now;write=original.write
REPAIR_FIELDS=original.FIELDS+('source_run_id','source_actual_generated_at','source_model_artifact_id','corrected_at','prediction_version')

def repair_row(row,zero_cell=None):
    r=dict(row);reason=[]
    if 'qb-rb-specialization' in r['procedure_id']:
        r['product_id']='absolute_loss_point'
        if r['fallback']!='none' and r['position'] not in ('QB','RB'):
            r.update(prediction=0.,fallback='constant_zero',fallback_source='constant_zero',fallback_source_n=0);reason.append('ORIGINAL_RA_FALLBACK_POOL_EXCLUDES_WR_TE')
    if zero_cell is not None:
        law=Law(**zero_cell['prior_parameters'][r['position']]);d=law.summary(r['actual']);n=zero_cell['prior_position_sample_counts'][r['position']];fb='cold_start_role_prior' if r['fallback']=='cold_start_role_prior' else 'no_model_role_prior';r.update(prediction=d['mean' if r['product_id']=='event_probability' else r['product_id']],fallback=fb,fallback_source='same_arm_position_prior' if n else 'same_arm_global_prior',fallback_source_n=n or zero_cell['training_n'],distribution_summary=d,law_reference=dict(fallback_prior=law.parameters()),fit_state='QUARANTINED_OLD_GLM_ALL_ZERO_MODEL_USE_REGISTERED_NO_FIT_PRIOR',model_artifact_id=None);reason.append('ORIGINAL_GLM_ALL_ZERO_COUNT_NO_FIT_CONTRACT')
    return r,reason

def prepare(public,private,source_public,source_private):
    public,private,source_public,source_private=map(Path,(public,private,source_public,source_private))
    if public.exists() or private.exists():raise ValueError('new immutable repair required')
    public.mkdir(parents=True);private.mkdir(parents=True);receipt=json.loads((source_public/'RUN_RECEIPT.json').read_text())
    p=dict(version=VERSION,state='FROZEN_BEFORE_REPAIR_PREDICTION_METRICS',registered_at_utc=now(),code_sha256=sha(__file__),original_engine_sha256=sha(original.__file__),corrected_engine_sha256=sha(corrected.__file__),source_run_receipt_sha256=sha(source_public/'RUN_RECEIPT.json'),source_protocol_sha256=sha(source_public/'FROZEN_PROTOCOL.json'),source_score_sha256=sha(source_public/'SCORES.json'),source_prediction_sha256=sha(source_private/'predictions.csv.gz'),source_artifact=(source_public/'SCORES.json').as_posix(),evaluation_season=receipt['evaluation_season'],formula='RA no-model fallback uses onlyQB/RB source rows; unsupportedWR/TE fallback0; originalabsolute_loss_point productalias. GLMlaw allzero-count eligibleframe uses registeredroleprior/no-fit instead ofPoissonfit ifany; auditallcountlawcells first.',scope='Preserve original2025v1 fits/weights/sourceframes/rows/scores/clocks; newreconstructedpredictionversion, not newfit or pure scorerrepair',budget=dict(max_fit_calls=0,wall_seconds=300,cpu_seconds=300,max_private_bytes=268435456,max_threads=1),new_family_count=0,CURRENT_2026_Week8_outcomes_read=0,actual2026_refits=0)
    write(public/'FROZEN_PROTOCOL.json',p);return p

def run(source_root,public,private,source_public,source_private,verifier_receipt):
    public,private,source_public,source_private=map(Path,(public,private,source_public,source_private));p=json.loads((public/'FROZEN_PROTOCOL.json').read_text());v=json.loads(Path(verifier_receipt).read_text())
    if v.get('state')!='PASS_SEASONAL_CONTINUITY_REVIEW' or v.get('repair_protocol_sha256')!=sha(public/'FROZEN_PROTOCOL.json') or sha(__file__)!=p['code_sha256']:raise ValueError('review/frozen repair gate')
    if sha(original.__file__)!=p['original_engine_sha256'] or sha(corrected.__file__)!=p['corrected_engine_sha256']:raise ValueError('repair helper changed')
    for file,key in [(source_public/'RUN_RECEIPT.json','source_run_receipt_sha256'),(source_public/'FROZEN_PROTOCOL.json','source_protocol_sha256'),(source_public/'SCORES.json','source_score_sha256'),(source_private/'predictions.csv.gz','source_prediction_sha256')]:
        if sha(file)!=p[key]:raise ValueError('original bytes changed')
    start,cpu=time.monotonic(),time.process_time();protocol=json.loads((source_public/'FROZEN_PROTOCOL.json').read_text())
    for item in protocol['source_ids']:
        if sha(Path(source_root)/item['name'])!=item['sha256']:raise ValueError('source bytes changed')
    rows,games,counts=original.load_source(source_root,protocol);zero={};audits=[]
    for file in sorted(source_public.glob('*-glm_law-FIT.json')):
        r=json.loads(file.read_text())
        if r['target'] not in original.emp.COUNTS:continue
        floor=original.policies(p['evaluation_season'])[r['policy_id']][1];roles=original.source.allowed_roles(protocol,r['target']);train=[q for q in rows if q['season']>=floor and q['position'] in roles and q['values'][r['target']] is not None and q['available']<r['fit_cutoff']];y=[q['values'][r['target']] for q in train];allzero=len(y)>=40 and all(x==0 for x in y)
        if len(train)!=r['training_n']:raise ValueError('GLM audit training census')
        audits.append(dict(slot=r['slot'],training_n=len(y),all_zero_count_eligible=allzero,original_state=r['state']))
        if allzero and ('FITTED' in r['state'] or 'FAILED' in r['state']):zero[r['slot']]=r
    write(public/'GLM_ALL_ZERO_AUDIT.json',dict(cells=len(audits),affected_cells=len(zero),all_count_law_frames=audits,new_fit_calls=0))
    meters=collections.defaultdict(original.Meter);nrows=changes=numeric=productaliases=0;path=private/'CORRECTED_PREDICTIONS.csv.gz';patches=[]
    zero_pairs={(r['target'],r['policy_id']) for r in zero.values()}
    with path.open('xb') as raw:
     with gzip.GzipFile(fileobj=original.CheckedStream(raw,lambda:p['budget']['max_private_bytes']),mode='wb',mtime=0) as handle:
      text=io.TextIOWrapper(handle,encoding='utf-8',newline='');writer=csv.DictWriter(text,fieldnames=REPAIR_FIELDS,extrasaction='ignore');writer.writeheader()
      with gzip.open(source_private/'predictions.csv.gz','rt') as f:
       for index,r in enumerate(csv.DictReader(f)):
        istra='qb-rb-specialization' in r['procedure_id'];affected_glm='regularized_glm_law' in r['procedure_id'] and (r['target'],r['policy_id']) in zero_pairs
        if not istra and not affected_glm:continue
        old=dict(r);r.update(prediction=float(r['prediction']),actual=None if not r['actual'] else float(r['actual']),actual_grid=None if not r['actual_grid'] else float(r['actual_grid']),week=int(r['week']),season=int(r['season']),distribution_summary=json.loads(r['distribution_summary']) if r['distribution_summary'] else None,law_reference=json.loads(r['law_reference']) if r['law_reference'] else None)
        r,reasons=repair_row(r,zero.get(r.get('fit_slot')));corrected_at=now();r.update(source_run_id=old['run_id'],source_actual_generated_at=old['actual_generated_at'],source_model_artifact_id=old.get('model_artifact_id'),run_id=VERSION+':'+str(p['evaluation_season']),prediction_version=VERSION,corrected_at=corrected_at,actual_generated_at=corrected_at);nrows+=1;productaliases+=old['product_id']!=r['product_id']
        if reasons:
            changes+=1;numeric+=float(old['prediction'])!=r['prediction'];patches.append(dict(source_row_index=index,query_id=r['query_id'],policy_id=r['policy_id'],procedure_id=r['procedure_id'],old_product_id=old['product_id'],new_product_id=r['product_id'],old_prediction=float(old['prediction']),new_prediction=r['prediction'],old_fallback=old['fallback'],new_fallback=r['fallback'],reasons=reasons))
        dims=(r['procedure_id'],r['family'],r['target'],r['policy_id'],r['history_regime'],r['product_id'],r['population'])
        for week,pos,view in [('ALL','ALL','ALL'),(str(r['week']),'ALL','ALL'),('ALL',r['position'],'ALL')]+([('ALL','ALL','LEARNED_ONLY')] if r['fallback']=='none' else []):meters[dims+(week,pos,view)].add(r)
        out=dict(r,distribution_summary='' if not r['distribution_summary'] else json.dumps(r['distribution_summary']),law_reference='' if not r['law_reference'] else json.dumps(r['law_reference']));writer.writerow(out)
        if nrows%1000==0 and (time.monotonic()-start>p['budget']['wall_seconds'] or time.process_time()-cpu>p['budget']['cpu_seconds']):raise RuntimeError('REPAIR_TIME_BUDGET')
      text.flush();text.detach()
    original_scores=json.loads((source_public/'SCORES.json').read_text());scores=[];mapping=[];source_artifact=(source_public/'SCORES.json').as_posix();replacement_artifact=(public/'SCORES.json').as_posix()
    for index,r in enumerate(original_scores):
        if 'qb-rb-specialization' not in r['procedure_id'] and not any(x['target']==r['target'] and x['policy_id']==r['policy_id'] for x in zero.values()):continue
        product='absolute_loss_point' if 'qb-rb-specialization' in r['procedure_id'] else r['product_id'];dims=(r['procedure_id'],r['procedure_family_id'],r['target'],r['policy_id'],r['history_regime'],product,r['population'],str(r['week']),r['position'],r['fallback_view'])
        if dims not in meters:continue
        new=dict(r,product_id=product,evaluation_panel_id=r['evaluation_panel_id']+':continuity-repair-v1',prediction_version=VERSION,source_score_row_index=index,source_score_sha256=p['source_score_sha256'],**meters[dims].result());scores.append(new);mapping.append(dict(source_artifact=source_artifact,source_sha256=p['source_score_sha256'],source_row_index=index,source_test_id=evaluation(r,source_artifact)['test_id'],replacement_artifact=replacement_artifact,replacement_row_index=len(scores)-1,replacement_test_id=evaluation(new,replacement_artifact)['test_id'],state='SUPERSEDED_ORIGINAL_RECIPE_CONTINUITY',scope='Completeaffectedprocedureview; originalscoreandrowbytesretained'))
    write(public/'SCORES.json',scores);original.emp.write_csv(public/'SCORES.csv',scores);write(public/'SUPERSESSION_MAPPING.json',dict(source_score_sha256=p['source_score_sha256'],replacement_score_sha256=sha(public/'SCORES.json'),rows=mapping));patchblob=gzip.compress(original.canonical(patches),mtime=0)
    if path.stat().st_size+len(patchblob)>p['budget']['max_private_bytes']:raise RuntimeError('REPAIR_PRIVATE_BUDGET')
    with (private/'ROW_CORRECTIONS.json.gz').open('xb') as f:f.write(patchblob);f.flush();os.fsync(f.fileno())
    receipt=dict(version=VERSION,state='COMPLETE_NO_REFITS',actual_completed_at=now(),source_prediction_sha256=p['source_prediction_sha256'],source_score_sha256=p['source_score_sha256'],score_views=len(scores),forecast_rows_replayed=nrows,changed_fallback_rows=changes,numerically_changed_predictions=numeric,product_alias_rows=productaliases,GLM_all_zero_audited_cells=len(audits),GLM_all_zero_affected_cells=len(zero),private_flat=dict(bundle_name=path.name,sha256=sha(path),bytes=path.stat().st_size),row_corrections=dict(bundle_name='ROW_CORRECTIONS.json.gz',sha256=sha(private/'ROW_CORRECTIONS.json.gz'),bytes=len(patchblob)),new_fit_calls=0,old_models_refitted=0,CURRENT_2026_Week8_outcomes_read=0,actual2026_refits=0,resource=dict(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,max_threads=1))
    write(public/'RUN_RECEIPT.json',receipt);return receipt
