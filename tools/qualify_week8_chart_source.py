"""Extend the existing partial chart-label source contract to one fresh W8 release."""
import argparse,hashlib,json,sys,warnings
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import pandas as pd


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main(private,public,reader):
    sys.path.insert(0,str(reader));import rdata
    csv=private/'source-labels/fresh-player-stats-2026.csv';rds=csv.with_suffix('.rds')
    protocol=public/'CHART_WEEK8_SOURCE_EXTENSION_PROTOCOL_V1.json';p=json.loads(protocol.read_bytes());assert sha(csv)==p['source_csv_sha256']
    warnings.simplefilter('ignore',UserWarning)
    parsed=rdata.parser.parse_file(rds);attrs=rdata.conversion.convert(parsed.object.attributes);frame=rdata.conversion.convert(parsed)
    assert [str(x)for x in attrs['nflfastR_version']]==['6.0.0'] and not bool(attrs.get('custom_pbp',False))
    data=pd.read_csv(csv,dtype=str,keep_default_na=False,low_memory=False);assert frame.shape==data.shape and list(frame)==list(data)
    compared=0;maxdiff=0.
    for col in frame:
        a=frame[col].reset_index(drop=True);b=data[col].reset_index(drop=True)
        if pd.api.types.is_numeric_dtype(a.dtype):
            aa=pd.to_numeric(a,errors='coerce');bb=pd.to_numeric(b,errors='coerce');assert np.array_equal(pd.isna(aa),pd.isna(bb)),col
            valid=~pd.isna(aa);av=np.asarray(aa[valid],dtype=float);bv=np.asarray(bb[valid],dtype=float)
            assert np.allclose(av,bv,rtol=1e-12,atol=1e-12),col
            if len(av):maxdiff=max(maxdiff,float(np.max(np.abs(av-bv))))
        else:assert a.fillna('').astype(str).tolist()==b.fillna('').astype(str).tolist(),col
        compared+=len(a)
    receipt=dict(state='ADMITTED_CURRENT_VINTAGE_PARTIAL_CHART_LABEL_SOURCE_WEEK8_ONLY',policy_id='v2-nick-chart-ppr-week8-explicit-superset-zero-extension-v1',
        registered_protocol_sha256=sha(protocol),completed_at_utc=datetime.now(timezone.utc).isoformat(),csv_sha256=sha(csv),rds_sha256=sha(rds),
        producer_version=[str(x)for x in attrs['nflfastR_version']],source_timestamp=[str(x)for x in attrs['nflverse_timestamp']],
        custom_pbp_attribute_present='custom_pbp'in attrs,rows=len(frame),columns=len(frame.columns),all_cells_compared=compared,all_csv_cells_match=True,max_numeric_difference=maxdiff,
        supported_season=2026,supported_weeks=[8],parent_policy=p['parent_policy'],parent_policy_sha256=p['parent_policy_sha256'],
        old_immutable_whitelist_changed=False,completeness_tier='Provider version/completeness contract; not independent official rare-event census. Exact finality/identity/appearance additionally required. Positive/unknown supersets stay missing.',
        formula='Reuse existing chart primitive mapping, exact scoring.chart_points_exact and signed0.02grid. Ordinary reception excludes2ptcatch; unique fumbles_lost_total counted once.',new_fits=0,new_forecasts=0,chart_loss_values_examined=0,code_sha256=sha(Path(__file__)))
    with(public/'CHART_WEEK8_SOURCE_ADMISSION_V1.json').open('x')as f:json.dump(receipt,f,indent=2);f.write('\n')
    print(json.dumps({k:receipt[k]for k in('state','producer_version','all_cells_compared','max_numeric_difference')}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--private-root',type=Path,required=True);p.add_argument('--public-root',type=Path,required=True);p.add_argument('--reader-root',type=Path,required=True);a=p.parse_args();main(a.private_root,a.public_root,a.reader_root)
