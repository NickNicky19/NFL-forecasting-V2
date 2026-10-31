"""Compress public-safe coverage projections losslessly; retain local originals."""
import collections,csv,gzip,hashlib,json,shutil,time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/championship-20261030f/coverage'


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    start=time.monotonic();manifest=json.loads((OUT/'COVERAGE_MANIFEST.json').read_bytes())
    for name,expected in manifest['source_manifests_sha256'].items():assert sha(ROOT/name)==expected, name
    data=json.loads((OUT/'COVERAGE_GRID.json').read_bytes());columns=data['columns'];rows=[dict(zip(columns,r))for r in data['rows']]
    assert len(rows)==manifest['rows']and len({r['coverage_id']for r in rows})==len(rows)
    with(OUT/'COVERAGE_GRID.csv').open()as f:
        for x,y in zip(csv.DictReader(f),rows,strict=True):
            for k in columns:
                value=y[k]
                assert(json.loads(x[k])==value if isinstance(value,(list,dict))else x[k]==(''if value is None else str(value))),(y['coverage_id'],k)
    current=json.loads((ROOT/'reports/continuation-20261030d/current-ranking-v2/current-valid-results/CURRENT_MANIFEST.json').read_bytes())
    idspec=current['selected_ids'];assert sha(ROOT/idspec['path'])==idspec['sha256'];valid=set(json.loads((ROOT/idspec['path']).read_bytes()))
    sourceids={i for r in rows if r['unit_kind']=='scientific_evaluation_cell'for i in r['source_records']if i.startswith('TEST-')};assert sourceids<=valid
    scientific=[r for r in rows if r['unit_kind']=='scientific_evaluation_cell']
    assert all(r['procedure_id'].startswith('server-retained-')for r in scientific if r['status']=='NOT_APPLICABLE')
    assert all(not r.get('supported_n_values')or any(float(n)>0 for n in r['supported_n_values'])for r in scientific if r['status']=='COMPLETED_VALID')
    strict=[r for r in scientific if r['status']=='FIT_REQUIRED'and r['season']==2026];assert len(strict)==147 and all(r['procedure_id'].startswith('hgb-direct-history-controls-v1:')and r['feature_memory_policy']=='EVALUATION_SEASON_ONLY_NFL_INFORMATION'for r in strict)
    missing_old=[r for r in scientific if r['status']=='FIT_REQUIRED'and r['season']<2026];assert len(missing_old)==13248 and all('position-defense'in r['procedure_id']for r in missing_old)
    empirical=[r for r in scientific if r['procedure_id']=='empirical-player-history-control-v1'];assert all(r['feature_memory_policy']=='PER_ARM_OUTCOME_HISTORY_NO_PREDICTOR_FEATURE_MEMORY_RETROSPECTIVE_POSITION'for r in empirical)
    counts=collections.Counter(r['unit_kind']for r in rows);assert counts['unresolved_legacy_request_reference']==5408 and counts['requested_pathway']==60 and counts['fit_origin_reference']==27344
    delivery=[];ignores=[]
    for folder in(OUT,OUT.parent/'coverage-draft-v3'):
        for name in('COVERAGE_GRID.json','COVERAGE_GRID.csv'):
            source=folder/name;target=folder/(name+'.gz')
            with source.open('rb')as src,target.open('xb')as dst:
                with gzip.GzipFile(fileobj=dst,mode='wb',mtime=0,compresslevel=6)as gz:shutil.copyfileobj(src,gz)
            digest=hashlib.sha256()
            with gzip.open(target,'rb')as gz:
                while block:=gz.read(1048576):digest.update(block)
            assert digest.hexdigest()==sha(source)
            ignores.append('/'+source.relative_to(ROOT).as_posix())
            if folder==OUT:delivery.append(dict(path=target.relative_to(ROOT).as_posix(),sha256=sha(target),bytes=target.stat().st_size,encoding='gzip',decompressed_sha256=sha(source),decompressed_bytes=source.stat().st_size))
    manifest.update(delivery=delivery,json_encoding='column names plus row arrays; dict(zip(columns,row))',local_uncompressed_originals_preserved=True,
       selected_ID_binding=dict(path=idspec['path'],sha256=idspec['sha256']),request_registry_boundary='REQUEST_METHOD_CROSSWALK is not a consumed input. Root retains its additive latest requests separately; old5408 grid/pathway60 sources remain explicitly hash-bound.',
       verification_receipt='reports/championship-20261030f/coverage/COVERAGE_CHECKER_RECEIPT.json')
    (OUT/'COVERAGE_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
    ignore=ROOT/'.gitignore';prior=ignore.read_text();extra=[x for x in ignores if x not in prior.splitlines()]
    if extra:ignore.write_text(prior+'\n# Retain exact local coverage originals; publish lossless gzip projections.\n'+'\n'.join(extra)+'\n')
    text=(OUT/'README.md').read_text().replace('(COVERAGE_GRID.csv)','(COVERAGE_GRID.csv.gz)').replace('(COVERAGE_GRID.json)','(COVERAGE_GRID.json.gz)')
    text+='\nPublic delivery uses gzip for the CSV and column-encoded JSON. Exact uncompressed originals remain local; manifest hashes verify decompression equality. Decode JSON rows with dict(zip(columns, row)). No private source records or storage locators are included. The invalidated drafts and software failure remain preserved with their findings.\n'
    (OUT/'README.md').write_text(text)
    receipt=dict(state='PASS_SOURCE_BINDINGS_CSV_JSON_VALUES_CURRENT_IDS_AND_CLASSIFICATION',scope='Executor-written readback; independent review recorded separately.',source_manifest_sha256=sha(OUT/'COVERAGE_MANIFEST.json'),source_grid_sha256=sha(OUT/'COVERAGE_GRID.json'),rows=len(rows),unique_coverage_ids=len(rows),scientific_source_test_ids=len(sourceids),unit_counts=dict(counts),
      original_strict_HGB_FIT_REQUIRED=147,older_D1_D2_output_cells_FIT_REQUIRED=13248,old_reference_rows=5408,C_origin_or_output_rows=25277,requested_pathways=60,
      CSV_JSON_every_value_equal=True,gzip_decompressed_hashes_equal=True,local_originals_preserved=True,new_fits=0,new_forecasts=0,new_grades=0,wall_seconds=time.monotonic()-start,code_sha256=sha(Path(__file__)))
    (OUT/'COVERAGE_CHECKER_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt))


if __name__=='__main__':main()
