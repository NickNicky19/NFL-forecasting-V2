"""One-time read-only source snapshots for the saved Week8 grading checkpoint.

No forecast execution, collector schedule, API key, market acquisition or write
to either upstream repository. Private source bodies never enter public output.
"""
from __future__ import annotations
import argparse, concurrent.futures, hashlib, json, threading, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

PRODUCTION = 'NickNicky19/nicks-expert-nfl-picks'
PIN = 'ea2ce5f57146112bb4b5ccebcf8544b181192f50'
HEADS = ['e336bf7a68c32267c3c3eec48892aeadcd03a90e',
         'dbf4a05de77e3abcd497125fa0cb0479ac4c327a',
         '911a81a31f822de58e0f9c04ded070f8c9752670',
         '0f615dd95fb6684ffe84ccd978a49e620ed6ba6c', PIN]


def now(): return datetime.now(timezone.utc).isoformat()
def sha(body): return hashlib.sha256(body).hexdigest()


def sources(root, mode):
    if mode == 'metadata':
        result = []
        for head in HEADS:
            result.append((f'board-{head}.json', f'https://raw.githubusercontent.com/{PRODUCTION}/{head}/output/data/archive/2026_w08.json'))
        for group, name, prefix in [('selected','selected_directory.json','output/data/weekly-selected-rankings'),
                                    ('classic','classic_directory.json','data/current-classic/2026/w08')]:
            for row in json.loads((root/name).read_bytes()):
                if row['name'].endswith('.receipt.json'): continue
                result.append((group+'-'+row['name'],f'https://raw.githubusercontent.com/{PRODUCTION}/{PIN}/{prefix}/{row["name"]}'))
        for head in HEADS:
            for kind in ('weekly-adaptive-overlay','weekly-selected-rankings'):
                result.append((f'{kind}-pointer-{head}.json',f'https://raw.githubusercontent.com/{PRODUCTION}/{head}/output/data/{kind}.json'))
        return result
    return [
        ('fresh-player-stats-2026.csv','https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_2026.csv'),
        ('fresh-games.csv','https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv'),
        ('espn-week8-scoreboard.json','https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates=20261029-20261102&limit=1000'),
    ]


def main(root, mode):
    output=root/('source-'+mode);output.mkdir(exist_ok=False)
    start=time.monotonic();total=0;lock=threading.Lock()
    def fetch(item):
        nonlocal total
        name,url=item;started=now()
        try:
            with urlopen(Request(url,headers={'User-Agent':'NFL-forecasting-V2-readonly-grading/1'}),timeout=30)as response:
                data=response.read(20*1024*1024+1)
                if len(data)>20*1024*1024:raise ValueError('per-source byte budget exceeded')
                metadata={k:response.headers.get(k)for k in('Date','Last-Modified','ETag','Content-Type','Content-Length')}
                status=response.status
            with lock:
                total+=len(data)
                if total>64*1024*1024:raise ValueError('source wave byte budget exceeded')
            with(output/name).open('xb')as handle:handle.write(data)
            return dict(name=name,url=url,state='RETRIEVED',HTTP_status=status,bytes=len(data),sha256=sha(data),started_at_utc=started,observed_at_utc=now(),headers=metadata)
        except Exception as exc:
            return dict(name=name,url=url,state='FAILED_NOT_ZERO_OR_ABSENT',started_at_utc=started,observed_at_utc=now(),error_type=type(exc).__name__,error=str(exc)[:250])
    with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:receipts=list(pool.map(fetch,sources(root,mode)))
    receipt=dict(mode=mode,completed_at_utc=now(),requests=len(receipts),bytes=total,wall_seconds=time.monotonic()-start,receipts=receipts,new_fits=0,new_inference=0,upstream_writes=0)
    with(root/f'ACQUISITION_{mode.upper()}_V1.json').open('x')as handle:json.dump(receipt,handle,indent=2);handle.write('\n')
    print(json.dumps(dict(mode=mode,requests=len(receipts),bytes=total,states={state:sum(r['state']==state for r in receipts)for state in{r['state']for r in receipts}},wall_seconds=receipt['wall_seconds'])))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--private-root',type=Path,required=True);parser.add_argument('--mode',choices=['metadata','labels'],required=True)
    args=parser.parse_args();main(args.private_root,args.mode)
