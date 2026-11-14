"""Read-only strict-2026 legacy completion source/feature preflight; no fit/load.

Derived statistical inputs: nflverse/nflfastR, CC-BY-4.0. Old unsafe model
serialization is not decoded; safe JSON parameters require separate root GO.
"""
import argparse,collections,csv,gzip,hashlib,json,math,re,sys
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT))
from nfl_v2 import hgb_control as source
from nfl_v2 import empirical_benchmark as empirical
from nfl_v2 import ordered_information_ablation as c02
from nfl_v2 import distribution_wave_v2 as dist
BASE=Path(__file__).resolve().parent

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def clean(x):
 if isinstance(x,dict):return{k:clean(v)for k,v in x.items()}
 if isinstance(x,(list,tuple,np.ndarray)):return[clean(v)for v in x]
 if isinstance(x,np.generic):return clean(x.item())
 if isinstance(x,float)and not math.isfinite(x):return None
 return x
def save(p,x):
 if p.exists():raise FileExistsError(p)
 body=(json.dumps(clean(x),separators=(',',':'),allow_nan=False)+'\n').encode();p.write_bytes(gzip.compress(body,mtime=0)if p.suffix=='.gz'else body)
def read(p):
 raw=p.read_bytes();return json.loads(gzip.decompress(raw)if p.suffix=='.gz'else raw)
def public(p):return dict(path=p.relative_to(ROOT).as_posix(),bytes=p.stat().st_size,sha256=sha(p))
def load_file(path,games,weeks):
 needed=set(empirical.MAP.values())|set(empirical.PHYSICAL_COUNTS)|set(empirical.PHYSICAL_YARDS)|{'rushing_tds','receiving_tds'};rows=[];seen=set()
 with path.open()as f:
  reader=csv.DictReader(f);assert needed<=set(reader.fieldnames)
  for r in reader:
   if r['season_type']!='REG'or int(r['season'])!=2026 or int(r['week'])not in weeks:continue
   if r['position']not in source.POSITIONS or not re.fullmatch(r'00-\d{7}',r['player_id']):continue
   g=games[r['game_id']];assert g['season']==2026 and g['week']==int(r['week'])
   assert(r['team'],r['opponent_team'])in[(g['home'],g['away']),(g['away'],g['home'])]
   key=r['game_id'],r['player_id'];assert key not in seen;seen.add(key)
   v={k:empirical.numeric(r[k])for k in needed}
   played=any(empirical.valid_count(v[k])and v[k]>0 for k in empirical.PHYSICAL_COUNTS)or any(v[k]is not None and v[k]!=0 for k in empirical.PHYSICAL_YARDS)
   value=empirical.target_value('pass_cmp',v)if played else None
   rows.append(dict(season=2026,week=int(r['week']),game_id=r['game_id'],player_id=r['player_id'],position=r['position'],team=r['team'],opponent=r['opponent_team'],kickoff=g['kickoff'],available=g['kickoff']+7*86400,played=played,values={'pass_cmp':value}))
 return rows

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--old-source',type=Path,required=True);ap.add_argument('--later-stats',type=Path,required=True);ap.add_argument('--private',type=Path,required=True);a=ap.parse_args()
 oldp=ROOT/'reports/continuation-20261030/distribution-wave-v2/FROZEN_PROTOCOL.json';old=read(oldp)
 for name in ['stats_player_week_2026.csv','games.csv']:
  expected=next(x for x in old['source_ids']if x['name']==name);assert sha(a.old_source/name)==expected['sha256']
 assert sha(a.later_stats)=='164bbcb46f4bf93c06a17c0f2497a06c17bbaf543d1e352ee6b85410febf884a'
 assert sha(Path(source.__file__))==old['source_loader_sha256']
 assert sha(Path(dist.__file__))==old['code_sha256']
 cp=ROOT/'reports/continuation-20261030b/ordered-information-ablation-v1/FROZEN_PROTOCOL.json';c=read(cp);assert sha(Path(c02.__file__))==c['code_sha256']
 games=source.schedules(a.old_source/'games.csv')
 # Preserve the old helper's intentional W8 scope. Append W9 solely in this
 # new continuation with the same retained aware schedule conversion.
 with (a.old_source/'games.csv').open()as f:
  for r in csv.DictReader(f):
   if(r['season'],r['game_type'],r['week'])!=('2026','REG','9'):continue
   assert r['gametime'] and r['game_id']not in games
   kickoff=datetime.fromisoformat(r['gameday']+'T'+r['gametime']).replace(tzinfo=ZoneInfo('America/New_York')).timestamp()
   games[r['game_id']]=dict(game_id=r['game_id'],espn=r['espn'],season=2026,week=9,kickoff=kickoff,kickoff_utc=datetime.fromtimestamp(kickoff,timezone.utc).isoformat(),home=r['home_team'],away=r['away_team'])
 prior=load_file(a.old_source/'stats_player_week_2026.csv',games,set(range(1,8)));later=load_file(a.later_stats,games,{8,9});allrows=prior+later
 assert len({(r['game_id'],r['player_id'])for r in allrows})==len(allrows)
 history=source.FeatureHistory(allrows);counts=collections.Counter();maxdiff=0.;paritybindings=[]
 for kind,folder in [('directGLM','distribution-wave-v2'),('C02','ordered-information-ablation-v1')]:
  for week in range(1,8):
   p=a.private/folder/'query-features'/f'W{week:02}-pass_cmp-H-CURRENT-STRICT.json.gz';payload=read(p)
   # Check the original public receipt binds these decoded feature bytes.
   fit=ROOT/('reports/continuation-20261030/distribution-wave-v2'if kind=='directGLM'else'reports/continuation-20261030b/ordered-information-ablation-v1')/(f'W{week:02}-pass_cmp-H-CURRENT-STRICT-regularized_glm_law-FIT.json'if kind=='directGLM'else f'W{week:02}-pass_cmp-H-CURRENT-STRICT-FIT.json')
   receipt=read(fit);assert sha(p)==receipt['query_features']['sha256']
   for r in payload:
    q=r['query'];v,m=history.get(q['player_id'],q['position'],'pass_cmp',q['cutoff']);v=c02.project(v)if kind=='C02'else v
    expected=np.asarray(r['features'],float);v=np.asarray(v,float);assert np.allclose(v,expected,rtol=0,atol=1e-10,equal_nan=True)
    good=np.isfinite(v)&np.isfinite(expected);maxdiff=max(maxdiff,float(np.abs(v[good]-expected[good]).max(initial=0)))
    assert m==r['latest_feature_available'];counts[kind]+=1
   paritybindings.append(dict(kind=kind,week=week,rows=len(payload),feature_packet_sha256=sha(p),fit_receipt=public(fit)))
 # Only the target QB identities' own histories are needed, including any
 # earlier non-QB role rows for those same players; training remains QB-only.
 qsource=ROOT/'reports/information-first-20261112-01/B/completion-wave-v1/QB_CONTEXT_W1_W9_INPUTS_V1.json.gz';qrows=read(qsource)
 queries=[dict(game_id=q['game_id'],player_id=q['player_id'],position='QB',team=q['team'],opponent=q['opponent'],season=2026,week=q['week'],kickoff=q['kickoff'],cutoff=q['kickoff'],population='RETROSPECTIVE_QB_QUERY_UNIVERSE_NOT_PREGAME_ROSTER')for q in qrows if q['season']==2026 and q['week']in{8,9}]
 ids={r['player_id']for r in allrows if r['position']=='QB'}|{q['player_id']for q in queries};inputs=[r for r in allrows if r['player_id']in ids]
 for q in queries:assert games[q['game_id']]['kickoff']==q['kickoff']
 trainplans=[]
 for week in [8,9]:
  origin=min(g['kickoff']for g in games.values()if g['season']==2026 and g['week']==week)
  tr=[r for r in inputs if r['position']=='QB'and r['values']['pass_cmp']is not None and r['available']<origin]
  assert len(tr)>=60
  trainplans.append(dict(week=week,origin_epoch=origin,origin_UTC=datetime.fromtimestamp(origin,timezone.utc).isoformat(),training_rows=len(tr),latest_training_label_available=max(r['available']for r in tr),training_membership_sha256=hashlib.sha256(source.canonical([(r['game_id'],r['player_id'])for r in tr])).hexdigest(),queries=sum(q['week']==week for q in queries),trained_roles=['QB']))
 save(BASE/'STRICT_2026_COMPLETION_INPUTS_V1.json.gz',dict(rows=inputs,queries=queries,source='FrozenoldW1-7pluscurrentvintageW8-9only; no revisedold-weeksubstitution',license='CC-BY-4.0nflverse/nflfastR'))
 save(BASE/'FEATURE_PARITY_AND_PREFLIGHT_V1.json',dict(id='B_LEGACY_COMPLETION_STRICT_2026_PREFLIGHT_v1',at_UTC=datetime.now(timezone.utc).isoformat(),state='SOURCE_AND_FEATURE_PREFLIGHT_PASS_NO_FITS;ROOT_GO_AND_RETENTION_SCOPE_REQUIRED',original_protocols=[public(oldp),public(cp)],source_bindings=[dict(name='Frozen2026W1-7CSV',sha256=sha(a.old_source/'stats_player_week_2026.csv')),dict(name='Later2026CSV_W8W9_APPEND_ONLY',sha256=sha(a.later_stats)),dict(name='FrozenGameSchedule',sha256=sha(a.old_source/'games.csv'))],old_2026_source_rows_preserved=len(prior),appended_2026_source_rows=len(later),source_hybrid_vintage_explicit=True,old_query_feature_parity=dict(checked_by_kind=dict(counts),max_finite_difference=maxdiff,all_latest_source_clocks_equal=True,bindings=paritybindings),inputs=public(BASE/'STRICT_2026_COMPLETION_INPUTS_V1.json.gz'),feature_order=dict(GLM=list(source.FEATURES),C02=list(c02.KEEP_NAMES)),frozen_settings=dict(forest=dist.FOREST,GLM=dist.GLM,prior='EarlierQB-onlysameoriginempiricalgeometricprior; C02mixture95/5',transform='Originaltrain-onlymedian/missingflags; GLMstandardizationfitonlyoneligibletraining'),origin_plan=trainplans,max_new_fits=4,new_fits=0,source_HTTP_attempts=0,model_loading='No pickle/unsafeoldmodeldeserialization. Oldpicklemodelsnotused. NewfitswouldexporttypedJSONandverifyrestorationbeforeinference.',historical_policy='Strict2026labels/features/priors/transforms; available=kickoff+7days strict<; weekly earliest kickoff; historicalquerykickoffleftlimit. Not original W8currentissue/time or source-clockauthentication.',old_W8_scope='OriginalpartialliveW8model cutoffafterThursdaykickoff; do not reusefor earlierThu. Preserve originalcurrentissue; newweek8historicalreplay is separatelyversioned.',recovery_scope='Globalexpandedlarge-fitgateforold2022-2024seasonalarchivesremainsclosed. ThispreflightconsumesonlyplainCSV2026andhash-verifiedsafeJSONfeaturepackets; nooldseasonalfit/source/modelconsumed. Rootmustexplicitlyconfirmthisbounded4fitcurrent-onlyscopeisauthorized; otherwiseRECOVERY_BLOCKED.',privacy='No private source locators/rawfeeds/offerrowsincluded',rights='Derived2026statisticalfeaturesCC-BY-4.0nflverse/nflfastR; noFTNvalueblockused'))
 print(json.dumps(dict(state='PREFLIGHT_PASS_NO_FITS',parity_rows=dict(counts),maxdiff=maxdiff,source_rows=len(inputs),queries=len(queries),origin_plan=trainplans)))
if __name__=='__main__':main()
