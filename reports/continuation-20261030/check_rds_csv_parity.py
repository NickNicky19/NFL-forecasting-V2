"""Decode only pre-kickoff, metadata/digest-qualified RDS companions."""
import hashlib,json,sys,warnings
from pathlib import Path
from datetime import datetime,timezone
import numpy as np
import pandas as pd

def audit(cache,source):
    import rdata
    warnings.simplefilter('ignore',UserWarning)
    receipt=json.loads((cache/'SOURCE_PROBE_RECEIPT.json').read_text());checks=[]
    for desc in receipt['assets']:
        p=cache/desc['source_name'];assert hashlib.sha256(p.read_bytes()).hexdigest()==desc['sha256']
        r=rdata.parser.parse_file(p);attrs=rdata.conversion.convert(r.object.attributes);frame=rdata.conversion.convert(r)
        df=pd.read_csv(source/p.name.replace('.rds','.csv'),dtype=str,keep_default_na=False,low_memory=False)
        assert list(frame.columns)==list(df.columns) and frame.shape==df.shape
        assert not bool(attrs.get('custom_pbp',False))
        compared=0;maxdiff=0.
        for col in frame:
            a=frame[col].reset_index(drop=True);b=df[col].reset_index(drop=True)
            if pd.api.types.is_numeric_dtype(a.dtype):
                an=pd.to_numeric(a,errors='coerce');bn=pd.to_numeric(b,errors='coerce')
                assert np.array_equal(pd.isna(an),pd.isna(bn)),col
                valid=~pd.isna(an);av=np.asarray(an[valid],dtype=float);bv=np.asarray(bn[valid],dtype=float)
                assert np.allclose(av,bv,rtol=1e-12,atol=1e-12),col
                maxdiff=max(maxdiff,float(np.max(np.abs(av-bv))) if len(av) else 0.)
            else:
                aa=a.fillna('').astype(str).tolist();bb=b.fillna('').astype(str).tolist();assert aa==bb,col
            compared+=len(a)
        if '2026' in p.name:assert set(pd.to_numeric(frame['week']))<=set(range(1,8))
        checks.append(dict(source_name=desc['source_name'],rows=len(frame),columns=len(frame.columns),all_cells_compared=compared,max_numeric_difference=maxdiff,
            producer_version=[str(x)for x in attrs['nflfastR_version']],nflverse_type=[str(x)for x in attrs['nflverse_type']],nflverse_timestamp=[str(x)for x in attrs['nflverse_timestamp']],
            custom_pbp_attribute_present='custom_pbp'in attrs,custom_pbp_attribute_value=None,all_csv_cells_match=True))
    return dict(status='HASH_VERIFIED_PRE_WEEK8_RDS_COMPANIONS_MATCH_ALL_FROZEN_CSV_CELLS',checked_at_utc=datetime.now(timezone.utc).isoformat(),source_payload_bytes=receipt['source_payload_bytes'],all_seasons=checks,
        week8_outcomes_read=0,new_fits=0,new_forecasts=0,producer_provenance_limit='Attributes are retained provider claims; absence of custom_pbp marker is not an independent full-game event census. Parity verifies all fields, not only chart.',
        reader_warning='rdata falls back tbl_df/tbl to data.frame constructor; attribute objects inspected separately and complete CSV parity verified')

if __name__=='__main__':
    sys.path.insert(0,sys.argv[3]);result=audit(Path(sys.argv[1]),Path(sys.argv[2]))
    out=Path(__file__).parent/'CHART_RDS_CSV_PARITY.json'
    if out.exists():raise SystemExit('immutable output exists')
    out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
