#!/usr/bin/env python3
"""Source-bound coverage and 2022 source-limit annotations; no rescoring."""
import argparse,collections,gzip,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2 import seasonal_rolling as s
p=argparse.ArgumentParser();p.add_argument('--public',type=Path,required=True);p.add_argument('--private',type=Path,required=True);a=p.parse_args();pub,private=a.public,a.private;r=json.loads((pub/'RUN_RECEIPT.json').read_text());packet=private/r['labels']['bundle_name']
if s.sha(packet)!=r['labels']['sha256']:raise ValueError('label packet changed')
labels=json.loads(gzip.decompress(packet.read_bytes()));groups=collections.defaultdict(list)
for q in labels:
 for week in ('ALL',str(q['week'])):groups[q['target'],q['population'],week].append(q)
coverage=[]
for k,rows in sorted(groups.items()):coverage.append(dict(target=k[0],population=k[1],week=k[2],queries=len(rows),supported=sum(q['actual'] is not None for q in rows),missing=sum(q['actual'] is None for q in rows),query_games=len({q['game_id'] for q in rows}),supported_games=len({q['game_id'] for q in rows if q['actual'] is not None}),actual_status_counts=dict(collections.Counter(q['actual_status'] for q in rows))))
s.write(pub/'EVALUATION_COVERAGE.json',coverage);s.emp.write_csv(pub/'EVALUATION_COVERAGE.csv',coverage)
if r['evaluation_season']==2022:
 scores=json.loads((pub/'SCORES.json').read_text());rows=[dict(source_row_index=i,history_regime='H-RECENT',requested_history_status='PARTIAL_SOURCE_LIMITED_AVAILABLE_2022_PROXY',requested_recent_includes_2021=True,actual_fit_source_floor=2022,missing_source='Noqualified2021snapshot/warmstartregistration inthisexpandingfrom2022wave') for i,q in enumerate(scores) if q['history_regime']=='H-RECENT']
 s.write(pub/'RECENT_SOURCE_LIMIT_SCORE_ANNOTATIONS.json',dict(source_score_sha256=s.sha(pub/'SCORES.json'),source_boundary_amendment_sha256=s.sha(pub/'SOURCE_BOUNDARY_AMENDMENT.json'),rows=rows))
 with (pub/'README.md').open('a') as f:f.write('\n**2022 source boundary:** the displayed H-RECENT results are a source-limited 2022-only proxy. The requested preceding-2021 plus earlier-2022 comparison is unsupported by the registered sources and remains incomplete. CURRENT, expanding-from-2022 MULTI and strict-current startup arms intentionally share the same available football data in2022. Identical proxy scores do not show that older history is unhelpful. The separately registered source-boundary amendment and1,152 requested-cell statuses preserve this gap. No pre2022 source is silently introduced.\n')
print(json.dumps(dict(season=r['evaluation_season'],coverage_views=len(coverage),chart=[q for q in coverage if q['target']=='nick-chart-ppr-v1' and q['week']=='ALL'])))
