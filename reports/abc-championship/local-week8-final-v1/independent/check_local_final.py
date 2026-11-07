"""Independent B-local saved-offer finality/label/threshold/count verifier."""
import argparse,collections,csv,datetime,gzip,hashlib,json,math,re
from pathlib import Path
from decimal import Decimal
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def canon(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def key(r):return r['game_id'],r['player_id']or r['source_player_id'],r['target']
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--private-root',type=Path,required=True);ap.add_argument('--prior-private-root',type=Path,required=True);a=ap.parse_args();p=a.private_root;old=a.prior_private_root;pub=HERE.parent;protocol=read(pub/'FROZEN_LOCAL_PROTOCOL.json');receipt=read(pub/'RUN_RECEIPT.json')
 assert protocol['before_new_scores']and protocol['at_utc']<receipt['at_utc']
 for r in protocol['source_receipts']:assert sha(p/'source-labels'/r['name'])==r['sha256']
 games={r['game_id']:r for r in csv.DictReader((p/'source-labels/games.csv').open())if(r['season'],r['game_type'],r['week'])==('2026','REG','8')};events={e['id']:e for e in read(p/'source-labels/espn.json')['events']};assert len(games)==14
 iso=lambda v:datetime.datetime.fromisoformat(v.replace('Z','+00:00'))
 for g,r in games.items():
  e=events[r['espn']];assert e['status']['type']['completed']and e['status']['type']['state']=='post';assert {c['homeAway']:Decimal(c['score'])for c in e['competitions'][0]['competitors']}=={'home':Decimal(r['home_score']),'away':Decimal(r['away_score'])}
 stats={};fields={'pass_yd':'passing_yards','pass_td':'passing_tds','pass_cmp':'completions','pass_att':'attempts','pass_int':'passing_interceptions','rush_yd':'rushing_yards','rush_att':'carries','rec':'receptions','rec_yd':'receiving_yards'}
 for r in csv.DictReader((p/'source-labels/stats.csv').open()):
  if(r['season'],r['week'],r['season_type'])!=('2026','8','REG'):continue
  k=r['game_id'],r['player_id'];assert k not in stats;assert {r['team'],r['opponent_team']}=={games[k[0]]['home_team'],games[k[0]]['away_team']};stats[k]=r
 def number(v):return Decimal(str(v))if v not in('',None)else None
 def label(r):
  s=stats.get((r['game_id'],r['player_id']));played=s is not None and any((number(s.get(f))or 0)>0 for f in('attempts','carries','targets','receptions','punt_returns','kickoff_returns'))
  if not played:return None,'UNKNOWN'
  if r['target']in fields:v=number(s[fields[r['target']]])
  else:
   assert r['target']=='rush_rec_yd';v1,v2=number(s['rushing_yards']),number(s['receiving_yards']);v=None if None in(v1,v2)else v1+v2
  return v,'VERIFIED_PLAYED_POSITIVE_PHYSICAL'
 joined=readgz(old/'ORIGINAL_JOINED_ROWS_V1.json.gz')['rows'];original={key(r):r for r in joined if r['panel']=='ORIGINAL_PROVIDER_T90'};assert len(original)==661
 prior=readgz(old/'ORIGINAL_AND_TOP_GRADED_ROWS_V1.json.gz')['rows'];priororiginal={key(r):r for r in prior if r['panel']=='ORIGINAL_PROVIDER_T90'and r['strategy']=='original'}
 capture=readgz(old/'CAPTURED_LIBRARY_P1_ROWS_V1.json.gz')['rows'];metafile=ROOT/'reports/week8-grading-20261102l/comparable-products-v3/SCORES.json';meta={r['method_key']:r for r in read(metafile)};source=collections.defaultdict(dict)
 for r in capture:
  if r['method_key']in meta:source[r['method_key']][key(r)]=r
 masks={}
 for t in fields.keys()|{'rush_rec_yd'}:masks[t]=set.intersection(*[{k for k in v}for m,v in source.items()if meta[m]['target']==t])
 assert {t:len(v)for t,v in masks.items()}==receipt['common_offer_counts'];assert all(len(masks[t])==26 for t in('pass_yd','pass_td','pass_cmp','pass_att','pass_int'))
 path=p/'LOCAL_GRADED_ROWS.json.gz';assert sha(path)==receipt['private_sha256'];rows=readgz(path)['rows'];byg=collections.defaultdict(list);observed={};worked={};zero=0;corrections=[]
 for r in rows:
  k=key(r);assert k in original;v,part=label(r);assert number(r['actual'])==v and r['participation']==part and r['outcome_state']=='final'
  m=r.get('method_key');strategy=r['strategy'];base=source[m][k]if m else original[k];assert r['line']==base['line']and r['prediction']==base['prediction']and r['raw_prediction']==base['raw_prediction']and r['source_head']==base['source_head']and r['source_server_clock']==base['source_server_clock']
  assert iso(r['source_server_clock'])<=iso(r['kickoff'])-datetime.timedelta(minutes=90)
  point=r['raw_prediction']if strategy=='SAVED_RAW_PROJECTION_DIRECTION_RETAINED_PRECISION'else r['prediction'];side=r['side']if strategy=='original'else'over'if strategy=='alwaysOver'else'under'if strategy=='alwaysUnder'else None if point is None else'over'if number(point)>number(r['line'])else'under'if number(point)<number(r['line'])else None
  state='ABSTAIN'if side is None else'UNKNOWN_PARTICIPATION'if part=='UNKNOWN'else'MISSING_ACTUAL'if v is None else'PUSH'if v==number(r['line'])else'WIN'if(v>number(r['line']))==(side=='over')else'LOSS'
  assert r['selected_side']==side and r['statistical_state']==state and r['net_return']is None;byg[m,strategy].append(r);zero+=v==0 and state in('WIN','LOSS')
  if m:assert k in masks[r['target']]
  elif strategy=='original':
   observed[k]=r
   if state in('WIN','LOSS')and state not in worked:worked[state]=r
   o=priororiginal[k]
   if o['outcome_state']=='final'and(number(o['actual'])!=v or o['statistical_state']!=state):corrections.append({'target':r['target'],'old_actual':o['actual'],'new_actual':r['actual'],'old_grade':o['statistical_state'],'new_grade':state})
 assert len(observed)==661 and all(len({key(r)for r in v})==len(v)for v in byg.values())
 scores=read(pub/'SCORES.json');triads={};statekeys=('WIN','LOSS','PUSH','UNKNOWN_PARTICIPATION','MISSING_ACTUAL','PENDING','VOID','UNRESOLVED_CONTRACT')
 for s in scores:
  m=s.get('method_key');strategy='SAVED_ADJUSTED_POINT_DIRECTION_RETAINED_PRECISION'if s['strategy']=='P1'else s['strategy'];rr=[r for r in byg[m,strategy]if r['target']==s['target']]
  if s['evaluation_panel_id']=='B_LOCAL_W8_COMMON_OFFER_CONTROLS_V2':rr=[r for r in rr if key(r)in masks.get(r['target'],set())]
  chosen=[r for r in rr if r['selected_side']and(s['side']=='Combined'or r['selected_side']==s['side'])];c=collections.Counter(r['statistical_state']for r in chosen);n=c['WIN']+c['LOSS'];sm=s['selection_metrics'];assert(s['n'],s['forecast_rows'],sm['WIN'],sm['LOSS'])==(n,len(chosen),c['WIN'],c['LOSS']);assert sm['status_counts']=={k:c[k]for k in statekeys};assert sm['hit_rate']==(c['WIN']/n if n else None);assert sm['selection_pool_count']==len(rr)and sm['selection_coverage']==(len(chosen)/len(rr)if rr else None);assert s['query_membership_sha256']==hashlib.sha256(canon(sorted(r['source_row_index']for r in chosen))).hexdigest();assert s['shared_benchmark_status']=='LOCAL_NOT_C_ADMITTED';assert sm['returns']['ROI']is None
  triads.setdefault((s['evaluation_panel_id'],s['procedure_id'],s['target'],s['strategy']),{})[s['side']]=s
 for ss in triads.values():
  o,u,c=(ss[k]for k in('over','under','Combined'));assert c['n']==o['n']+u['n']and c['forecast_rows']==o['forecast_rows']+u['forecast_rows'];assert all(c['selection_metrics']['status_counts'][k]==o['selection_metrics']['status_counts'][k]+u['selection_metrics']['status_counts'][k]for k in statekeys)
 # Full original counts use the actual originally selected side, retaining unknowns.
 cnt=collections.Counter(r['statistical_state']for r in observed.values()if r['selected_side']);over=collections.Counter(r['statistical_state']for r in observed.values()if r['selected_side']=='over');under=collections.Counter(r['statistical_state']for r in observed.values()if r['selected_side']=='under')
 example=p/'independent-verification';example.mkdir(exist_ok=True);ep=example/'LOCAL_ORIGINAL_WIN_LOSS.json';ep.write_text(json.dumps(worked,indent=2)+'\n')
 result={'state':'PASS_INDEPENDENT_B_LOCAL_FINAL_WEEK8_NOT_C_ADMITTED','at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'LOCAL_NOT_C_ADMITTED; no canonical C protocol or ABC scorer parity established','protocol_sha256':sha(pub/'FROZEN_LOCAL_PROTOCOL.json'),'source_score_sha256':sha(pub/'SCORES.json'),'source_private_grade_sha256':sha(path),'source_capture_metadata_sha256':sha(metafile),'source_receipt_sha256':sha(pub/'RUN_RECEIPT.json'),'final_games':14,'NFLverse_ESPN_final_score_equalities':14,'old661offer_source_side_line_forecast_versions_unchanged':True,'raw_label_identity_and_crossing_checks':len(rows),'side_views_checked':len(scores),'side_triads_checked':len(triads),'common_offer_counts':receipt['common_offer_counts'],'original_combined':dict(cnt),'original_over':dict(over),'original_under':dict(under),'previously_final_original_label_or_grade_corrections':len(corrections),'previously_final_correction_details_aggregate_safe':corrections,'played_zero_decided_view_rows':zero,'private_win_loss_examples_sha256':sha(ep),'private_examples_retention':'LOCAL_ONLY','uncertainty':'One exposed week, dependent games. No proof of general best method or profitable bets. Prices/book settlement unqualified. Common local admitted masks are separate from full661offer coverage and C admission.','new_fits_inference_forecasts_or_external_source_acquisitions':0,'old_L_sources_modified':False,'checker_sha256':sha(Path(__file__))}
 (HERE/'INDEPENDENT_LOCAL_FINAL_REVIEW_V1.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k]for k in('state','raw_label_identity_and_crossing_checks','side_views_checked','side_triads_checked','original_combined','previously_final_original_label_or_grade_corrections')}))
def readgz(p):return json.loads(gzip.decompress(p.read_bytes()))
if __name__=='__main__':main()
