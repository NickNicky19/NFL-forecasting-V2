"""Append new owner-local QB score versions to the established registries."""
import collections,csv,gzip,hashlib,io,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools import build_test_index_v3 as index
from tools.check_analysis_index_coverage import read_bound
from tools.score_player_context_wave import VERSION,ctx

BASE=Path('reports/player-context-matchup-01/B')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):Path(p).write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def read(p):return json.loads(Path(p).read_bytes())
def binding(p,body):
    data=gzip.compress(body,compresslevel=9,mtime=0);Path(p).write_bytes(data)
    return dict(path=str(Path(p).relative_to(ROOT)),sha256=hashlib.sha256(data).hexdigest(),bytes=len(data),compression='gzip',
                uncompressed_bytes=len(body),uncompressed_sha256=hashlib.sha256(body).hexdigest())
def fullname(value):
    if value in('E0','E1','E2','E3','P1','P2','P3','COMMON_EXPOSURE'):return ctx.VERSION+':'+value
    if value in('F1','F2'):return 'B-QB-CHARTED-CATCHABILITY-CONTEXT-v1:'+value
    return value
def history(value):
    if value in('ALWAYS_OVER','ALWAYS_UNDER','NEUTRAL_HALFPOINT'):return 'NOT_APPLICABLE_CONSTANT_CONTROL'
    if value in('SAVED_RAW','SAVED_ADJUSTED'):return 'UNKNOWN_ARCHIVED_SOURCE_PROCEDURE'
    return 'H-RECENT'

def main():
    ptr=ROOT/'registries/CURRENT_RESULTS_INDEX.json';pointer=read(ptr);previous=pointer['manifest'];reg=ROOT/'registries/RESULT_ARTIFACTS.json';registry=read(reg)
    sources=['qb-scores-v1','qb-charting-scores-v1','component-and-controls-v1']
    for name in sources:
        artifact=str(BASE/name/'SCORES.json')
        if any(r['artifact']==artifact for r in registry):raise ValueError('New wave already registered; do not duplicate')
        item=dict(artifact=artifact,state='SCORED',kind='QB_CONTEXT_OWNER_LOCAL_CHRONOLOGICAL_RECONSTRUCTION_AND_SAVED_ROW_EVALUATION',
            version_note='2025full/2026W1-8numeric; actual-lineW5-8fourweeks only. New exact recipes/localnotCadmitted. No originalissuance;component/rightwrongviewsnonprimary. Alllosses/oldermetadata retained.')
        if name=='qb-scores-v1':item['reporting_annotations']=str(BASE/name/'SOURCE_PERIOD_HISTORY_METADATA_ANNOTATIONS_V2.json')
        registry.append(item)
    save(reg,registry)
    out=str(BASE/'results-index-v1');result=index.write(previous=previous,output=out,reuse_prior_csv=True,compressed_delivery=True)
    pointer['previous_checkpoint']=previous;pointer['manifest']=out+'/INDEX_MANIFEST.json';pointer['readable_checkpoint']=str(BASE/'B_PLAYER_CONTEXT_MATCHUP_REPORT.md')
    pointer['player_context_matchup']=dict(report=pointer['readable_checkpoint'],protocol=str(BASE/'qb-wave-v1/FROZEN_PROTOCOL.json'),
        charting_protocol=str(BASE/'qb-charting-wave-v1/FROZEN_PROTOCOL.json'),scope='Local2025full+2026W1-8numeric,QBcmp/attempts; W5-8actual-offerdiagnostics,4weeks. Not full12categorychampionship. Existingfixednative/default projection unchanged.',
        qualification='Exact numerical duration assessed separately; allnewdirection/probability/TopKofferproducts lack fifth offeredweek, noneCadmittedorproductionpromoted.')
    # Normalize new paired analysis rows into the existing schema, retaining the
    # original pair files and exact source-row links. No re-scoring here.
    normalized=[]
    for name in sources:
        path=BASE/name/'PAIRED_COMPARISONS.json';body=(ROOT/path).read_bytes()
        for i,r in enumerate(json.loads(body)):
            candidate=fullname(r['candidate']);control=fullname(r['control']);product=r.get('product',r.get('policy','EXACT_LINE_DIRECTION'))
            contrast=candidate+'_MINUS_'+control
            normalized.append(dict(r,procedure_id=candidate,comparator_procedure_id=control,product_id=product,comparator_product_id=r.get('control_policy',product),
                target=r['target'],population='RETROSPECTIVE_QB_SAME_MATCHED_PLAYER_GAME_CONTRACT',season=r['season'],history_regime=history(candidate),comparator_history_regime=history(control),
                contrast=contrast,metric='MAE'if r['kind']=='NUMERICAL_PAIRED_MAE'else'SELECTION_LOSS_RATE',fallback_view=r.get('scope','COMMON_SELECTED'),
                policy_id=r.get('policy'),position='QB',cohort_id=str(r.get('window','ALL')),
                history_limit='Earlier-only frozen procedure; current/revised sources and quote-time uncertainty. Not an original pick or unexposed holdout.',
                original_pair_source=str(path),original_pair_source_sha256=hashlib.sha256(body).hexdigest(),original_pair_row_index=i))
    newpath=ROOT/BASE/'INDEX_BOUND_PAIRED_ANALYSIS.json';save(newpath,normalized);relative=str(newpath.relative_to(ROOT));sourcehash=sha(newpath)
    old_binding=pointer['derived_comparison_manifest'];prior=json.loads(read_bound(old_binding));old=json.loads(read_bound(prior['records_json']));ar=ROOT/'registries/ANALYSIS_ARTIFACTS.json';analysis_registry=read(ar);assert analysis_registry==prior['inputs']
    projected=[]
    for i,r in enumerate(normalized):
        z={k:None for k in old[0]}
        z.update(analysis_id='PAIR-'+hashlib.sha256(json.dumps([relative,i,r['procedure_id'],r['comparator_procedure_id'],r['product_id'],r['cohort_id']],separators=(',',':')).encode()).hexdigest()[:20],kind='DERIVED_PAIRED_LOSS_ANALYSIS',
            state='PAIRED_LOSS_SCORED'if r['n']else'NO_SUPPORTED_PAIRED_ROWS',procedure_id=r['procedure_id'],product_id=r['product_id'],target=r['target'],population=r['population'],season=r['season'],history_regime=r['history_regime'],
            policy_id=r['policy_id'],contrast=r['contrast'],view=r['fallback_view'],cohort_id=r['cohort_id'],position=r['position'],metric=r['metric'],n=r['n'],candidate_error=r.get('candidate_error'),comparator_error=r.get('comparator_error'),
            absolute_error_change=r.get('delta'),relative_error_change=r.get('relative_error_change'),membership_sha256=r.get('membership_sha256'),week_clusters=r.get('week_clusters'),week_interval=r.get('week_interval'),week_interval_status=r.get('week_interval_status'),game_cluster_se=r.get('game_cluster_sensitivity_se'),
            history_status=r['history_limit'],precision_status='Selectiondenominators/nativeprecisionseparatelybound; derivedcontrastsaddnoNFLobservations.',source_artifact=relative,source_artifact_sha256=sourcehash,source_row_index=i,new_fits=0,new_forecasts=0,new_NFL_observations=0,
            candidate_history_regime=r['history_regime'],comparator_history_regime=r['comparator_history_regime'],comparator_procedure_id=r['comparator_procedure_id'],comparator_product_id=r['comparator_product_id'])
        projected.append(z)
    merged=old+projected;assert len({r['analysis_id']for r in merged})==len(merged)
    dest=ROOT/BASE/'paired-analysis-index-v1';dest.mkdir(exist_ok=False)
    rb=binding(dest/'PAIRED_ANALYSES.json.gz',(json.dumps(merged,separators=(',',':'),allow_nan=False)+'\n').encode());buffer=io.StringIO(newline='');writer=csv.DictWriter(buffer,fieldnames=list(merged[0]));writer.writeheader()
    for r in merged:writer.writerow({k:json.dumps(v,separators=(',',':'))if isinstance(v,(dict,list))else v for k,v in r.items()})
    cb=binding(dest/'PAIRED_ANALYSES.csv.gz',buffer.getvalue().encode());analysis_registry.append(dict(artifact=relative,sha256=sourcehash,rows=len(normalized),state='DERIVED_PAIRED_ANALYSIS_SCORED_WITH_EMPTY_STATES_RETAINED',new_univariate_forecast_views=0))
    manifest=dict(prior,inputs=analysis_registry,record_count=len(merged),status_counts=dict(collections.Counter(r['state']for r in merged)),records_json=rb,records_csv=cb,previous_manifest=old_binding,old_records_preserved=len(old),new_records=len(projected));mp=dest/'ANALYSIS_MANIFEST.json';save(mp,manifest);save(ar,analysis_registry)
    pointer['derived_comparison_manifest']=dict(path=str(mp.relative_to(ROOT)),sha256=sha(mp));save(ptr,pointer)
    print(json.dumps(dict(index=result,new_pairs=len(projected),old_pairs=len(old),all_pairs=len(merged))))
if __name__=='__main__':main()
