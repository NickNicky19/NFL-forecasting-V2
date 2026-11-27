"""Source-bound view metadata; never change a forecast, grade or scored loss."""
import hashlib,json
from pathlib import Path

def qualified_rows(path, overlay):
    p=Path(path);body=p.read_bytes();source_hash=hashlib.sha256(body).hexdigest();rows=json.loads(body)
    bindings=[r for r in overlay['sources']if r['source_sha256']==source_hash]
    if len(bindings)!=1:raise ValueError('Exact score source binding required')
    corrections={r['source_row_index']:r for r in bindings[0]['rows']}
    if len(corrections)!=len(bindings[0]['rows']):raise ValueError('Duplicate scope correction')
    for i,row in enumerate(rows):
        if i not in corrections:yield row;continue
        c=corrections[i]
        if c['record_id']!=row['record_id']or c['original_technical_unavailable']!=row.get('technical_unavailable'):
            raise ValueError('Scope source record mismatch')
        outer,inside,excluded=(c[k]for k in('full_system_query_rows','reported_scope_rows','outside_reported_scope'))
        if any(type(x)is not int or x<0 for x in(outer,inside,excluded))or outer!=inside+excluded or row['forecast_rows']!=inside:
            raise ValueError('Scope partition mismatch')
        # The allowed replacement is source availability, not any scored count.
        result=dict(row,technical_unavailable=0,outside_reported_scope=excluded,
            full_system_forecast_coverage=dict(query_rows=outer,available_forecasts=outer,technical_unavailable=0),
            scope_metadata_note='Original template field represented exclusion from this diagnostic/learned/fallback view, not a failed inference. Scores and forecasts unchanged.')
        yield result
