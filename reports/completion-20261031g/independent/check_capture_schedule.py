"""Replay the census schedule check at its retained actual verification clock."""
import argparse,csv,hashlib,json
from datetime import datetime,timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
p=argparse.ArgumentParser();p.add_argument('--schedule',type=Path,required=True);p.add_argument('--review',type=Path,required=True);a=p.parse_args();r=json.loads(a.review.read_bytes())['schedule_recheck'];assert hashlib.sha256(a.schedule.read_bytes()).hexdigest()==r['source_sha256'];at=datetime.fromisoformat(r['asof_utc']);games=[]
with a.schedule.open()as f:
 for z in csv.DictReader(f):
  if z['season']=='2026'and z['game_type']=='REG'and z['week']=='8':games.append(datetime.fromisoformat(z['gameday']+'T'+z['gametime']).replace(tzinfo=ZoneInfo('America/New_York')).astimezone(ZoneInfo('UTC')))
future=[t for t in games if t>at];deadline=min(future)-timedelta(minutes=90);assert len(games)==r['week8_games']and len(future)==r['remaining_games'];assert deadline.isoformat()==r['earliest_remaining_T90_utc']and deadline.astimezone(ZoneInfo('America/Chicago')).isoformat()==r['earliest_remaining_T90_Chicago'];print(json.dumps(dict(state='PASS_RETAINED_SCHEDULE_ASOF_REPLAY',games=len(games),remaining=len(future),next_T90=deadline.isoformat())))
