"""Reuse accepted CSV parts and publish only newly appended typed prop rows.

Public aggregate delivery only. No grading, source outcomes, fits or deletion.
"""
import csv,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
D=ROOT/'reports/prop-grading-20261030e'


def sha(path):
    h=hashlib.sha256()
    with path.open('rb')as f:
        for body in iter(lambda:f.read(1024*1024),b''):h.update(body)
    return h.hexdigest()


def binding(path,rows):
    return dict(path=path.relative_to(ROOT).as_posix(),rows=rows,bytes=path.stat().st_size,sha256=sha(path))


def main():
    source=D/'results-index-v3/INDEX_MANIFEST.json';prior=ROOT/'reports/continuation-20261030c/results-index/INDEX_MANIFEST.json'
    m=json.loads(source.read_text());old=json.loads(prior.read_text());out=D/'compact-results-index'
    if out.exists():raise ValueError('fresh immutable delivery directory required')
    out.mkdir();(out/'categories').mkdir();cursor=0;new_count=0;files={};writers={};counts={}
    path=out/'PROP_RESULTS_INDEX.csv';handle=None;writer=None
    try:
        for part in m['csv_parts']:
            end=cursor+part['rows']
            if end<=old['record_count']:cursor=end;continue
            body=ROOT/part['path']
            if sha(body)!=part['sha256']:raise ValueError('source CSV changed')
            with body.open(newline='')as f:
                reader=csv.DictReader(f)
                for row in reader:
                    if row['kind']!='prop_selection_evaluation':continue
                    if writer is None:
                        handle=path.open('w',newline='');writer=csv.DictWriter(handle,fieldnames=reader.fieldnames);writer.writeheader()
                    writer.writerow(row);new_count+=1;target=row['category']
                    if target not in writers:
                        q=out/'categories'/(target+'.csv');files[target]=q.open('w',newline='');writers[target]=csv.DictWriter(files[target],fieldnames=reader.fieldnames);writers[target].writeheader();counts[target]=0
                    writers[target].writerow(row);counts[target]+=1
            cursor=end
    finally:
        if handle:handle.close()
        for f in files.values():f.close()
    if new_count!=m['record_count']-old['record_count']:raise ValueError('new prop CSV coverage mismatch')
    m['csv_parts']=old['csv_parts']+[binding(path,new_count)]
    if sum(p['rows']for p in m['csv_parts'])!=m['record_count']:raise ValueError('CSV total mismatch')
    m['new_product_category_csv_parts']=[binding(out/'categories'/(t+'.csv'),n)for t,n in sorted(counts.items())]
    m['csv_header_policy']='Accepted numeric CSV headers remain unchanged. New prop CSV has additional typed columns. Match common columns by name; union headers when combining products. JSON shards are authoritative and unchanged.'
    m['delivery_projection']=dict(source_manifest=source.relative_to(ROOT).as_posix(),source_sha256=sha(source),
        previous_csv_parts_reused=len(old['csv_parts']),new_typed_prop_rows=new_count,new_grades=0,new_fits=0,
        code_sha256=sha(Path(__file__)))
    (out/'INDEX_MANIFEST.json').write_text(json.dumps(m,indent=2)+'\n')
    (out/'README.md').write_text('# Permanent result index: shared history and typed prop results\n\n'
        f"{m['record_count']:,} audit records: all {old['record_count']:,} prior records/shards retained plus {new_count:,} new selection evaluation views. No new forecasts or independent NFL observations.\n\n"
        '[New prop results with counts/errors/accuracy](PROP_RESULTS_INDEX.csv) · [JSON/source manifest](INDEX_MANIFEST.json) · [Accepted numerical/history CSVs](../../continuation-20261030c/results-index/CSV_FILES.md) · [Readable side tables](../ALL_METHODS_CATEGORY_SIDE_TABLES.md).\n\n'
        'The JSON shards and source score artifacts are identical to the verified typed index v3. Accepted historical CSV parts are referenced directly. The new prop CSV includes selected side, strategy, eligible and selected counts, wins/losses, accuracy numerator/denominator, error rate, separate statistical/book states, K/cohort/time/alias fields and uncertainty/provenance links.\n\n'
        'CSV column sets extend by product: combine by column name, retaining missing fields, rather than appending rows under another product header. Season aliases and overlapping cohorts are not additional observations. The current prop view filters weekly records; original pilot and all source versions remain in the audit.\n\n'
        'Derived full-CSV drafts remain locally preserved; their hashes/headers are catalogued in ../DRAFT_DELIVERY_INVENTORY.json. Their complete scientific JSON rows remain published. No raw restricted evidence is published or newly claimed restored.\n')
    inventory=[]
    for directory in ('results-index','results-index-v2','results-index-v3'):
        base=D/directory
        for p in sorted(base.rglob('*.csv')):
            with p.open(newline='')as f:header=next(csv.reader(f))
            inventory.append(dict(path=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=sha(p),header=header,
                status='REDUNDANT_DERIVED_CSV_LOCAL_BYTES_PRESERVED;SCIENTIFIC_JSON_AND_CURRENT_DELIVERY_PUBLIC'))
        (base/'DRAFT_STATUS.md').write_text('# Preserved index projection\n\nOriginal JSON manifests and appended records remain retained here. Redundant derived CSV delivery files and original draft Markdown remain locally preserved and are not republished. Use the [current shared delivery](../compact-results-index/README.md). Source score rows and hashes are unchanged; CSV hashes and headers appear in ../DRAFT_DELIVERY_INVENTORY.json. This is not a private-evidence restoration claim.\n')
    (D/'DRAFT_DELIVERY_INVENTORY.json').write_text(json.dumps(dict(state='LOCAL_DUPLICATE_DELIVERY_PRESERVED_SCIENTIFIC_JSON_PUBLIC',files=inventory,
        bytes=sum(r['bytes']for r in inventory),deleted_files=0,new_grades=0,new_fits=0),indent=2)+'\n')
    print(json.dumps(dict(state='PASS_SHARED_CSV_DELIVERY',audit_records=m['record_count'],reused_csv_parts=len(old['csv_parts']),new_prop_rows=new_count,deleted_files=0,new_grades=0)))


if __name__=='__main__':main()
