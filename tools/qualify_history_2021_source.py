#!/usr/bin/env python3
"""Read-only public2021 qualification, never fit or modify2022-start controls."""
import argparse,collections,csv,hashlib,json,math,re,sys,time,urllib.request
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2 import hgb_control as s,empirical_benchmark as e,chart_sources as chart
URLS={
 'stats_player_week_2021.csv':'https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_2021.csv',
 'stats_player_week_2021.rds':'https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_2021.rds',
 'LICENSE':'https://raw.githubusercontent.com/nflverse/nflverse-data/master/LICENSE',
 'README.md':'https://raw.githubusercontent.com/nflverse/nflverse-data/master/README.md'}
def prepare(a):
 a.output.mkdir(parents=True);a.cache.mkdir(parents=True)
 p=dict(version='v2-2021-separate-source-qualification-v1',registered_at=s.now(),code_sha256=s.sha(__file__),urls=URLS,cached_schedule_sha256=s.sha(a.schedule),scope='2021REGoffensivestatistics/GSIS/historicalroles/scheduleandcomponentavailability; no2026Week8roworoutcome decode',existing_controls='2022sourcefloorand2022RECENTproxyimmutable; this extension is not a retroactivechange orfitadmission',chart='2021notinexistingchartsourcewhitelist; directfields/supersetzeroscountedonlyasqualificationdiagnostics, no chartlabelzeroinference untilnewproducer/RDSparityandpolicyreview',budget=dict(max_download_bytes=20971520,max_file_bytes=12582912,wall_seconds=120,request_timeout_seconds=30,max_rows=30000),storage='Localimmutablecacheonly; rootmustapproveandverifyprivateoffhostrestorationbeforefitadmission;noupload',new_fits=0,new_forecasts=0)
 s.immutable_json(a.output/'FROZEN_PROTOCOL.json',p);return p

def run(a):
 p=json.loads((a.output/'FROZEN_PROTOCOL.json').read_text());start=time.monotonic();receipts=[];total=0
 if p['code_sha256']!=s.sha(__file__)or p['cached_schedule_sha256']!=s.sha(a.schedule):raise ValueError('source/code binding')
 for name,url in p['urls'].items():
  if time.monotonic()-start>120:raise RuntimeError('timebudget')
  began=s.now()
  try:
   with urllib.request.urlopen(url,timeout=30)as response:
    blob=response.read(12582913);status=response.status;modified=response.headers.get('Last-Modified');mime=response.headers.get('Content-Type')
   if len(blob)>12582912 or total+len(blob)>20971520:raise RuntimeError('downloadsizebudget')
   with(a.cache/name).open('xb')as f:f.write(blob)
   total+=len(blob);receipts.append(dict(name=name,url=url,status=status,bytes=len(blob),sha256=s.sha(a.cache/name),retrieved_started_at=began,retrieved_completed_at=s.now(),last_modified=modified,content_type=mime))
  except Exception as exc:receipts.append(dict(name=name,url=url,status='FAILED',reason=type(exc).__name__+':'+str(exc)[:200]))
 s.immutable_json(a.output/'ACQUISITION_RECEIPTS.json',receipts)
 if not(a.cache/'stats_player_week_2021.csv').exists():raise RuntimeError('2021csvnotrestored')
 schedules={}
 with a.schedule.open()as f:
  for r in csv.DictReader(f):
   if r['season']=='2021'and r['game_type']=='REG':schedules[r['game_id']]=r
 counts=collections.Counter();roles=collections.Counter();targets=collections.Counter();components=collections.Counter();games=set();seen=set();needed=set(e.MAP.values())|set(e.PHYSICAL_COUNTS)|set(e.PHYSICAL_YARDS)|{'rushing_tds','receiving_tds'};schema=None
 with(a.cache/'stats_player_week_2021.csv').open()as f:
  reader=csv.DictReader(f);schema=reader.fieldnames
  missing=sorted(needed-set(schema))
  if missing:raise ValueError('basicfieldsabsent '+str(missing))
  for raw in reader:
   counts['source_rows']+=1
   if counts['source_rows']>30000:raise RuntimeError('rowbudget')
   if raw['season_type']!='REG'or raw['season']!='2021':continue
   counts['REG_rows_all_positions']+=1
   if raw['position']not in s.POSITIONS:continue
   counts['REG_QB_RB_WR_TE_rows']+=1;roles[raw['position']]+=1
   if not re.fullmatch(r'00-\d{7}',raw['player_id']):counts['invalid_GSIS']+=1;continue
   ident=(raw['game_id'],raw['player_id'])
   if ident in seen:counts['duplicate_player_game']+=1;continue
   seen.add(ident);game=schedules.get(raw['game_id'])
   if not game:counts['missing_schedule']+=1;continue
   if int(raw['week'])!=int(game['week'])or(raw['team'],raw['opponent_team'])not in((game['home_team'],game['away_team']),(game['away_team'],game['home_team'])):counts['schedule_team_week_conflict']+=1;continue
   games.add(raw['game_id']);values={k:e.numeric(raw[k])for k in needed};played=any(e.valid_count(values[k])and values[k]>0 for k in e.PHYSICAL_COUNTS)or any(values[k]is not None and values[k]!=0 for k in e.PHYSICAL_YARDS)
   counts['physical_appearance_supported'if played else'appearance_unknown']+=1
   for target in s.TARGETS:
    value=e.target_value(target,values)if played else None;targets[target+'_supported']+=value is not None;targets[target+'_missing']+=value is None
   for component,field in chart.FIELDS.items():components[component+'_explicit_valid']+=chart._integer(raw.get(field),signed=component in chart.SIGNED_YARDS)is not None
   fr=chart._integer(raw.get('fumble_recovery_tds'));sr=chart._integer(raw.get('special_teams_tds'));components['both_rare_supersets_explicit_zero']+=fr==sr==0;components['rare_superset_positive_or_missing']+=not(fr==sr==0)
 report=dict(state='LOCAL_SOURCE_QUALIFICATION_NO_FIT_ADMISSION',actual_completed_at=s.now(),protocol_sha256=s.sha(a.output/'FROZEN_PROTOCOL.json'),stats_source_sha256=s.sha(a.cache/'stats_player_week_2021.csv'),cached_schedule_sha256=s.sha(a.schedule),source_counts=dict(counts),historical_roles=dict(roles),schedule_REG_games=len(schedules),player_rows_bound_games=len(games),missing_schedule_games=sorted(set(schedules)-games),target_coverage=dict(targets),target_coverage_denominator='Allsource2021REGQB/RB/WR/TEstatisticalrows with exactGSIS/schedulebinding; physicalappearanceconditions eachordinarylabel; notexanteofferedpopulation',chart_component_availability=dict(components),chart_target=dict(status='BLOCKED_NEW2021_PRODUCER_PARITY_AND_ZERO_POLICY_NOT_QUALIFIED',supported_labels=0,missing_labels=counts['REG_QB_RB_WR_TE_rows'],reason='Existing2022–26sourcewhitelistimmutable;2021schemafields and RDScompanionbytes do not authenticate2021rarecredits orzero contract bythemselves'),license=dict(source='nflverse-data basicstats; currentretainedLICENSE/README bytes',data_use='Qualificationonly; basicstatsCCBY4 attribution required; no PFR/FTN/NGS/snapdataadmission',license_present=(a.cache/'LICENSE').exists(),README_present=(a.cache/'README.md').exists()),private_storage='Localretained; NOT_OFFHOST_RESTORED; rootcapacity/admissionpending',source_vintage='Current-vintage2021reconstruction; retrievaltime is not historicalavailability',new_fit_calls=0,new_forecasts=0,CURRENT_2026_Week8_outcomes_read=0,resource=dict(wall_seconds=time.monotonic()-start,download_bytes=total))
 s.immutable_json(a.output/'SOURCE_QUALIFICATION.json',report);return report
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=('prepare','run'))
 for n in('cache','schedule','output'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();print(json.dumps(prepare(a)if a.action=='prepare'else run(a)))
