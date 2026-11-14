#!/usr/bin/env python3
"""Create/verify private companion archives; never upload or publish raw rows.

All locations are explicit CLI arguments. Output archives/manifests must be
outside the public repository. Reports contain safe IDs, counts and hashes.
"""
import argparse,hashlib,io,json,re,tarfile,time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MEMBER='__V2_PRIVATE_MEMBERS__.json'


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb')as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()


def pack(source,archive,artifact_id,part_bytes=20*1024*1024):
    source=Path(source).resolve();archive=Path(archive).resolve()
    if archive.is_relative_to(ROOT)or archive.exists():raise ValueError('fresh private archive outside public Git required')
    if not re.fullmatch(r'V2-[A-Z0-9_-]+',artifact_id):raise ValueError('public-safe artifact ID required')
    if not 0<part_bytes<=32*1024*1024:raise ValueError('parts must fit private restoration transport limit')
    rows=[];start=time.monotonic()
    for p in sorted(source.rglob('*')):
        if p.is_symlink():raise ValueError('symlinks not admitted to private evidence bundle')
        if p.is_file():rows.append(dict(name=p.relative_to(source).as_posix(),bytes=p.stat().st_size,sha256=digest(p)))
    if not rows or any(r['name']==MEMBER for r in rows):raise ValueError('empty source or reserved manifest name')
    member_bytes=(json.dumps(dict(artifact_id=artifact_id,members=rows),indent=2)+'\n').encode()
    with archive.open('xb')as output:
        with tarfile.open(fileobj=output,mode='w:gz',compresslevel=1)as tar:
            for r in rows:tar.add(source/r['name'],arcname=r['name'],recursive=False)
            info=tarfile.TarInfo(MEMBER);info.size=len(member_bytes);tar.addfile(info,io.BytesIO(member_bytes))
    parts=[]
    with archive.open('rb')as f:
        for i,b in enumerate(iter(lambda:f.read(part_bytes),b'')):
            p=archive.with_name(archive.name.removesuffix('.tar.gz')+'.part'+str(i).zfill(3))
            with p.open('xb')as target:target.write(b)
            parts.append(dict(name=p.name,bytes=len(b),sha256=hashlib.sha256(b).hexdigest()))
    return dict(artifact_id=artifact_id,archive_bytes=archive.stat().st_size,archive_sha256=digest(archive),inner_files=len(rows)+1,inner_bytes=sum(r['bytes']for r in rows)+len(member_bytes),parts=parts,archive_wall_seconds=time.monotonic()-start,manifest_member=MEMBER)


def verify(metadata,downloads,joined):
    meta=json.loads(Path(metadata).read_text());downloads=json.loads(Path(downloads).read_text());joined=Path(joined)
    if joined.resolve().is_relative_to(ROOT)or joined.exists():raise ValueError('fresh private restoration outside public Git required')
    if len(downloads)!=len(meta['parts']):raise ValueError('restoration part census mismatch')
    h=hashlib.sha256();total=0
    with joined.open('xb')as target:
        for expected,actual in zip(meta['parts'],downloads):
            if actual['status']!='DOWNLOADED'or actual.get('unshared')is not True:raise ValueError('private download/visibility missing')
            b=Path(actual['workspace_path']).read_bytes()
            if len(b)!=expected['bytes']or hashlib.sha256(b).hexdigest()!=expected['sha256']:raise ValueError('part bytes mismatch')
            target.write(b);h.update(b);total+=len(b)
    if total!=meta['archive_bytes']or h.hexdigest()!=meta['archive_sha256']:raise ValueError('archive bytes mismatch')
    with tarfile.open(joined)as f:
        manifest=json.load(f.extractfile(meta['manifest_member']))
        for r in manifest['members']:
            b=f.extractfile(r['name']).read()
            if len(b)!=r['bytes']or hashlib.sha256(b).hexdigest()!=r['sha256']:raise ValueError('inner evidence bytes mismatch')
    return dict(artifact_id=meta['artifact_id'],status='FRESH_PRIVATE_RESTORE_ALL_PARTS_AND_INNER_FILES_VERIFIED',archive_bytes=total,archive_sha256=h.hexdigest(),parts=len(downloads),inner_file_checks=len(manifest['members']),manifest_file_extra=1,visibility='allpartsmetadataunshared',private_locator_published=False)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['pack','verify']);p.add_argument('--source',type=Path);p.add_argument('--archive',type=Path);p.add_argument('--artifact-id');p.add_argument('--metadata',type=Path,required=True);p.add_argument('--downloads',type=Path);p.add_argument('--joined',type=Path);p.add_argument('--report',type=Path)
    a=p.parse_args()
    if a.command=='pack':
        result=pack(a.source,a.archive,a.artifact_id)
        with a.metadata.open('x')as f:json.dump(result,f,indent=2);f.write('\n')
    else:
        result=verify(a.metadata,a.downloads,a.joined)
        if a.report:
            with a.report.open('x')as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in result.items()if k!='parts'}))
