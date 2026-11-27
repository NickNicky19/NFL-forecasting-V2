"""Read-only archive/part/readback arithmetic; explicit private roots required."""
import argparse, collections, hashlib, json, resource, tarfile, time
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
NAMES=('SEASON_2025_V1','SEASON_2024_V2','SEASON_2023_COMPLETE','SEASON_2022_V2','DEFENSE_AND_REPLAYS','SMALL_REPLAYS','ORIGINAL_CODE','STRICT_HGB_FUTURE')

def hashed(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
    return h.hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--companion-root',type=Path,required=True);p.add_argument('--archive-root',type=Path,required=True)
    args=p.parse_args();start,cpu=time.monotonic(),time.process_time();rows=[];checks=collections.Counter();metadata_hashes={}
    for name in NAMES:
        path=args.companion_root/(name+'_ARCHIVE_METADATA.json');d=json.loads(path.read_bytes());metadata_hashes[d['artifact_id']]=hashed(path)
        total=0;whole=hashlib.sha256();part_names=[]
        for part in d['parts']:
            original=args.archive_root/part['name'];assert original.stat().st_size==part['bytes']
            h=hashlib.sha256()
            with original.open('rb') as f:
                for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk);whole.update(chunk)
            assert h.hexdigest()==part['sha256'];checks['local_part_byte_hashes']+=1;total+=part['bytes'];part_names.append(part['name'])
        assert total==d['archive_bytes'] and whole.hexdigest()==d['archive_sha256'];checks['concatenated_complete_archive_hashes']+=1
        uploaded=set();readback=set()
        up=args.companion_root/(name+'_PRIVATE_UPLOADS.json')
        if up.exists():
            us=json.loads(up.read_bytes());assert len(us)==len(d['parts'])
            uploaded={x.get('part',x.get('name')) for x in us if x['status'].startswith('UPLOADED')}
            assert uploaded<=set(part_names);checks['successful_upload_map_entries']+=len(uploaded)
            down=args.companion_root/(name+('_PRIVATE_PARTIAL_DOWNLOADS.json' if name=='SEASON_2024_V2' else '_PRIVATE_DOWNLOADS.json'))
            downloads=json.loads(down.read_bytes());by_name={x['part']:x for x in downloads};assert set(by_name)==uploaded
            by_meta={x['name']:x for x in d['parts']}
            for upload in us:
                n=upload.get('part',upload.get('name'))
                if n not in uploaded:continue
                x=by_name[n];upload_id=upload.get('id')or upload['response']['id']
                assert x['status']=='DOWNLOADED' and x['unshared'] and x['id']==upload_id
                actual=Path(x['workspace_path']);expected=by_meta[n]
                assert actual.stat().st_size==expected['bytes'] and hashed(actual)==expected['sha256']
                readback.add(n);checks['fresh_downloaded_part_byte_hashes']+=1
        elif name in ('ORIGINAL_CODE','STRICT_HGB_FUTURE'):
            downloads=json.loads((args.companion_root/(name+'_PRIVATE_DOWNLOADS.json')).read_bytes());assert len(downloads)==1
            actual=Path(downloads[0]['workspace_path']);assert downloads[0]['status']=='DOWNLOADED' and downloads[0]['unshared']
            assert actual.stat().st_size==total and hashed(actual)==d['archive_sha256'];uploaded=set(part_names);readback=set(part_names);checks['fresh_downloaded_part_byte_hashes']+=1
        absent=[i for i,part in enumerate(d['parts'])if part['name']not in uploaded]
        rows.append(dict(artifact_id=d['artifact_id'],archive_bytes=total,archive_sha256=d['archive_sha256'],expected_parts=len(part_names),
            successful_upload_parts=len(uploaded),fresh_readback_parts=len(readback),fresh_readback_bytes=sum(x['bytes']for x in d['parts']if x['name']in readback),
            missing_part_indices=absent,missing_part_bytes=sum(d['parts'][i]['bytes']for i in absent),
            evidence_status='SUCCESSFUL_UPLOAD_AND_FRESH_READBACK_MAPS'if uploaded else'NO_SUCCESS_RECEIPT_IN_INSPECTED_COMPANION_SCOPE',
            complete_remote_restore_established=len(readback)==len(part_names)))
    by_id={r['artifact_id']:r for r in rows};missing_ids=('V2-PRIVATE-SEASON-2024-V2','V2-PRIVATE-SEASON-2023-COMPLETE-V1','V2-PRIVATE-SEASON-2022-V2','V2-PRIVATE-DEFENSE-AND-REPLAYS-V1')
    s24=by_id[missing_ids[0]];assert s24['missing_part_indices']==[7,*range(11,22)] and s24['missing_part_bytes']==251658240
    minimum=sum(by_id[k]['missing_part_bytes']for k in missing_ids);parts=sum(len(by_id[k]['missing_part_indices'])for k in missing_ids)
    assert minimum==997471189 and parts==48
    maps=[]
    for stem in ('small-replays-20261030c','defense-and-replays-v1','original-code-20261030c'):
        with tarfile.open(args.archive_root/('v2-private-'+stem+'.tar.gz'),'r:gz') as t:
            manifest=json.load(t.extractfile('__V2_PRIVATE_MEMBERS__.json'))
        maps.append({x['name']:(x['bytes'],x['sha256'])for x in manifest['members']})
    small,defense,code=maps;shared={k:v for k,v in small.items()if defense.get(k)==v}
    assert len(small)==10 and len(shared)==3
    learned=json.loads((args.companion_root/'LEARNED_MASK_CODE_ARCHIVE_METADATA.json').read_bytes())
    with tarfile.open(args.archive_root/'v2-private-learned-mask-original-code-v1.tar.gz','r:gz')as t:
        learned_manifest=json.load(t.extractfile('__V2_PRIVATE_MEMBERS__.json'))
    assert all(any(value==(x['bytes'],x['sha256'])for value in code.values())for x in learned_manifest['members'])
    result=dict(state='PASS_EXACT_ARCHIVE_CAPACITY_AND_RETAINED_READBACK_AUDIT',rows=rows,source_metadata_sha256_by_artifact=metadata_hashes,
        minimum_remaining_four_data_archive_bytes=minimum,minimum_remaining_four_data_archive_parts=parts,
        remaining_all_five_registered_archives_bytes=minimum+by_id['V2-PRIVATE-SMALL-REPLAYS-20261030C']['missing_part_bytes'],
        remaining_all_five_registered_archives_parts=parts+1,small_replay_archive_exact_data_members_already_in_defense=3,small_replay_extra_metadata_members=7,
        learned_mask_original_code_already_covered_by_restored_original_code=True,
        limitation='Counts prove the inspected receipt/map and local bytes. No remote listing, new download/upload, deletion, permission or sharing change was performed. Missing means no successful upload receipt in inspected scope; quota cause is separately reported by provider receipt. Four data archives omit the optional separate metadata/replay archive; complete registered archive set is the larger total.',
        checks=dict(checks),new_fits=0,new_forecasts=0,current2026_week8_outcomes_read=0,
        resource=dict(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024))
    (HERE/'ARCHIVE_CAPACITY_INDEPENDENT_REVIEW.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

if __name__=='__main__':main()
