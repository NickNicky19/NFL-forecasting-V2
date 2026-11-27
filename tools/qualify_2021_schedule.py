#!/usr/bin/env python3
"""Verify cached2021 schedule completion without decoding later outcomes."""
import argparse,csv,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2 import hgb_control as s,empirical_benchmark as e
p=argparse.ArgumentParser();p.add_argument('--schedule',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();checked=0;invalid=[]
with a.schedule.open()as f:
 for r in csv.DictReader(f):
  if r['season']!='2021'or r['game_type']!='REG':continue
  checked+=1;home,away,result,total=[e.numeric(r[k])for k in('home_score','away_score','result','total')]
  if not(e.valid_count(home)and e.valid_count(away)and result==home-away and total==home+away):invalid.append(r['game_id'])
s.immutable_json(a.output/'SCHEDULE_FINALITY_QUALIFICATION.json',dict(code_sha256=s.sha(__file__),source_schedule_sha256=s.sha(a.schedule),season=2021,REG_games_checked=checked,complete_score_result_total_identity=checked-len(invalid),unqualified_games=invalid,scope='Current-vintagecachedproviderfullgamecompletion consistency;2021onlynumericdecode, nothistoricalpublicationtimeproof',CURRENT_2026_Week8_outcomes_read=0,new_fit_calls=0,new_forecasts=0))
print(json.dumps(dict(games=checked,unqualified=len(invalid))))
