#!/usr/bin/env python3
"""Source-bound role coverage and staged2021 extension design; never fit."""
import argparse,collections,csv,json,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2 import hgb_control as s,empirical_benchmark as e,chart_sources as chart

def main(a):
 p=json.loads((a.output/'FROZEN_PROTOCOL.json').read_text());receipt=json.loads((a.output/'SOURCE_QUALIFICATION.json').read_text());rawfile=a.cache/'stats_player_week_2021.csv';licensefile=a.cache/'LICENSE.md'
 if s.sha(rawfile)!=receipt['stats_source_sha256']or not licensefile.read_text().startswith('Attribution 4.0 International'):raise ValueError('source/license binding')
 contract=json.loads(a.role_protocol.read_text())['source_role_contract'];rows=[];counts=collections.defaultdict(collections.Counter);games=collections.defaultdict(set);signed=collections.Counter();chartstatus=collections.Counter()
 with rawfile.open()as f:
  for raw in csv.DictReader(f):
   if raw['season']!='2021'or raw['season_type']!='REG'or raw['position']not in s.POSITIONS:continue
   needed=set(e.MAP.values())|set(e.PHYSICAL_COUNTS)|set(e.PHYSICAL_YARDS)|{'rushing_tds','receiving_tds'};values={k:e.numeric(raw[k])for k in needed};played=any(e.valid_count(values[k])and values[k]>0 for k in e.PHYSICAL_COUNTS)or any(values[k]is not None and values[k]!=0 for k in e.PHYSICAL_YARDS)
   for target in s.TARGETS:
    for pop in('primary','extended'):
     if raw['position']not in contract.get(pop,{}).get(target,[]):continue
     k=target,pop;counts[k]['source_rows']+=1;value=e.target_value(target,values)if played else None;counts[k]['supported_ordinary_label']+=value is not None;counts[k]['unknown_appearance_or_label']+=value is None;counts[k]['negative_signed_yardage']+=value is not None and value<0;games[k].add(raw['game_id'])
   rarezero=chart._integer(raw.get('fumble_recovery_tds'))==chart._integer(raw.get('special_teams_tds'))==0
   chartstatus['all_QB_RB_WR_TE']+=1;chartstatus['physical_appearance']+=played;chartstatus['physical_and_both_supersets_zero_potential_only']+=played and rarezero;chartstatus['physical_positive_or_unknown_supersets']+=played and not rarezero
 for(k,pop),counter in sorted(counts.items()):rows.append(dict(target=k,population=pop,positions=contract[pop][k],games=len(games[k,pop]),**dict(counter),fit_admission='PENDING_OFFHOST_RESTORATION_AND_INDEPENDENT_SOURCE_REVIEW'))
 rows.append(dict(target='nick-chart-ppr-v1',population='primary',positions=list(s.POSITIONS),games=272,source_rows=5866,supported_ordinary_label=None,unknown_appearance_or_label=5866,negative_signed_yardage=None,fit_admission='BLOCKED_2021_PRODUCER_RDS_PARITY_AND_RARE_ZERO_CONTRACT'))
 s.immutable_json(a.output/'ROLE_TARGET_COVERAGE.json',dict(source_stats_sha256=s.sha(rawfile),source_role_contract_sha256=s.sha(a.role_protocol),chart_diagnostics=dict(chartstatus),rows=rows,chart_values_not_derived=True,new_fit_calls=0,new_forecasts=0))
 e.write_csv(a.output/'ROLE_TARGET_COVERAGE.csv',rows)
 s.immutable_json(a.output/'LICENSE_QUALIFICATION_UPDATE.json',dict(state='PRIMARY_LICENSE_RETRIEVED_CC_BY_4_0',source_protocol_sha256=s.sha(a.output/'FROZEN_PROTOCOL.json'),license_url='https://raw.githubusercontent.com/nflverse/nflverse-data/master/LICENSE.md',license_sha256=s.sha(licensefile),initial_wrong_LICENSE_path_404_retained=True,basic_stats_only=True,restricted_PFR_FTN_NGS_snaps_not_admitted=True,offhost_restoration_pending=True,fit_admitted=False))
 oldquery=json.loads((a.base_private/'frozen-queries.json').read_text());football=[q for q in oldquery if q['target']!='nick-chart-ppr-v1'];old=json.loads((a.base_public/'FROZEN_PROTOCOL.json').read_text())
 design=dict(state='SEPARATELY_REGISTERED_STAGED_DESIGN_NO_FITS',registered_at=s.now(),version='v2-2022-eval-2021-source-extension-design-v1',new_source_sha256=s.sha(rawfile),old2022_source_protocol_sha256=s.sha(a.base_public/'FROZEN_PROTOCOL.json'),old2022_scores_sha256=s.sha(a.base_public/'SCORES.json'),old2022_frozen_membership_sha256=s.sha(a.base_private/'frozen-queries.json'),fixed_football_queries=len(football),fixed_chart_queries=len(oldquery)-len(football),evaluation_season=2022,evaluation_weeks=list(range(1,19)),labels='Same2022participant labels/queries asoldsourcefloor2022controls; no freshstatisticalholdoutclaim',chronology='Weeklyfit earlier labels usingconservativekickoff+7days; historicaltrainfeatures atownkickoff;pergamequeryrefresh; currentvintage2021source, not authentic historicalissuance',policies=[dict(id='E1-CURRENT-MEM2021',fit_floor=2022,feature_memory_floor=2021,meaning='current-seasonfittingwitholderfeaturememory'),dict(id='E1-RECENT2021-MEM2021',fit_floor=2021,feature_memory_floor=2021,meaning='Exactrequested2021pluseligible2022fitlabels;common2021memory'),dict(id='E1-MULTI-EXPAND2022-MEM2021',fit_floor=2022,feature_memory_floor=2021,model_alias_of='E1-CURRENT-MEM2021',meaning='Expandingfrom2022fitting unchangeddefinition; commonfeaturememoryseparate'),dict(id='OLD-STRICT2022-MEM2022',fit_floor=2022,feature_memory_floor=2022,model_reuse='Hash-boundexisting2022modelswhere exactrecipe/frame matches; referencewholeinformationpolicy, notcleanfitwindow')],fit_feature_separation='DoNOTappend2021fitrowswhilegivingthemempty2022-floorfeatures andcallitusablehistory. AllnewE1corearms sharequalified2021memory; preservedold2022-memorycontrols formseparatefeature-memoryablation. Settingshistoricallyexposed.',counts=dict(ordinary_method_target_slots_per_origin=61,ordinary_RECENT_requested_cells=1098,chart_RECENT_requested_cells=54,logical_ordinary_core_cells=3294,maximum_new_unique_ordinary_fit_opportunities=2196,aliases_not_fits=1098),chart='54chartRECENTcells blockedby2021target/sourcequalification; associatednewMEM2021chartcontrols alsoawaitvalid2021featurevalues. Old2022floorchartCURRENT/MULTI/STRICTandproxyretained. This doesnotblock11ordinarytargets.',prerequisites=['Root-confirmedapprovedprivateoffhostsourcebytesandrestoration','Independent2021basicstatsscheduleidentity/licensequalification','Newfiniteexecutiongrid/budgetsandsoftware/prefitreview','2021chartRDS/producerparity+newsourcezero policyonlyforchart'],no_fit_budget_allocated=True,new_fit_calls=0,new_forecasts=0,old_controls_modified=False)
 s.immutable_json(a.output/'EXTENSION_DESIGN_NO_FITS.json',design)
 print(json.dumps(dict(ordinary_target_population_views=len(rows)-1,chart_status=dict(chartstatus),fixed_football_queries=len(football),fit_admitted=False)))
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in('cache','output','role-protocol','base-public','base-private'):p.add_argument('--'+n,type=Path,required=True)
 main(p.parse_args())
