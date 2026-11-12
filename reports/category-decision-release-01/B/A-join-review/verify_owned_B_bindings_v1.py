"""Verify A's consumed B forecast bytes against existing owned Git artifacts."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
STEM='reports/abc-championship/profile-timing-closure-and-confirm-01'


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--cache',type=Path,required=True);a=ap.parse_args()
    go=a.cache/STEM/'B_TIMING_COMPLETION_SCORING_GO_V1.json';p=json.loads(go.read_text())
    records=[]
    for group in ('B_forecast_refs','B_retained_forecast_refs'):
        for r in p[group]:
            path=r.get('path','reports/profile-increment-closure-next-02/B/aligned-wave-v1/predictions/'+r['id'])
            body=(ROOT/path).read_bytes();actual=hashlib.sha256(body).hexdigest()
            assert actual==r['sha256'] and len(body)==r['bytes'],(group,r['id'])
            records.append(dict(group=group,path=path,week=r['week'],sha256=actual,bytes=len(body)))
    proto=p['B_protocol_binding'];body=(ROOT/proto['path']).read_bytes();assert hashlib.sha256(body).hexdigest()==proto['sha256']
    output=dict(id='B-A-TIMING-CONSUMED-B-BYTES-IDENTITY-v1',verified_UTC=datetime.now(timezone.utc).isoformat(),A_ref='d7c8bc619eb7aed93df8259822eb08488d837005',A_GO_sha256=hashlib.sha256(go.read_bytes()).hexdigest(),status='PASS_EXACT_OWNED_B_BYTES',forecast_packets_verified=len(records),records=records,protocol_binding=proto,scientific_producer=p['B_scientific_producer_commit'],public_rights=p['B_public_rights'],scope='New8F0-F3weeklypacketsand8oldR0-R3controlpackets exactlymatchownedretainedbytes;notproofAjoinusedcorrectprivateplayer/offerkeys.',new_fits=0,new_inference=0,new_grades=0,new_NFL_observations=0,models_deserialized=0)
    out=Path(__file__).resolve().parent/'B_OWNED_SOURCE_BINDING_REVIEW_V1.json';assert not out.exists();out.write_text(json.dumps(output,indent=2)+'\n');print(json.dumps(dict(status=output['status'],forecast_packets=len(records),bytes=sum(r['bytes']for r in records))))


if __name__=='__main__':main()
