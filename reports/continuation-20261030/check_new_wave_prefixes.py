"""Independent raw prefix/training-membership checks; no fitting or new labels."""
from collections import defaultdict,Counter
from datetime import datetime
from decimal import Decimal
from functools import lru_cache
import bisect,csv,gzip,hashlib,json,math,sys
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'reports/verification'))
from check_empirical_diagnostic import ACTION_COUNTS,ACTION_YARDS,count,num,value

def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def clock(x):return datetime.fromisoformat(x.replace('Z','+00:00')).timestamp()
def load(source,p):
    for d in p['source_ids']:assert sha(source/d['name'])==d['sha256']
    games={}
    with (source/'games.csv').open()as f:
        for r in csv.DictReader(f):
            year=int(r['season']);week=int(r['week'])
            if r['game_type']!='REG'or year not in range(2022,2027)or(year==2026 and week>8):continue
            dt=datetime.fromisoformat(r['gameday']+'T'+r['gametime']).replace(tzinfo=ZoneInfo('America/New_York'))
            games[r['game_id']]=dict(kickoff=dt.timestamp(),year=year,week=week)
    rows=[];history=defaultdict(list)
    for year in range(2022,2027):
        with (source/f'stats_player_week_{year}.csv').open()as f:
            for r in csv.DictReader(f):
                if r['season_type']!='REG'or int(r['season'])!=year or(year==2026 and int(r['week'])>7)or r['position']not in('QB','RB','WR','TE'):continue
                played=any(count(num(r[k]))and num(r[k])>0 for k in ACTION_COUNTS)or any(num(r[k])not in(None,0)for k in ACTION_YARDS)
                k=games[r['game_id']]['kickoff'];ys={t:value(t,r)if played else None for t in ('pass_yd','pass_td','pass_cmp','pass_att','pass_int','rush_yd','rush_att','rec','rec_yd','rush_rec_yd','anytime_td')}
                if played and num(r['fumble_recovery_tds'])==num(r['special_teams_tds'])==0:
                    fields={'passing_yards':'.04','passing_tds':'4','passing_interceptions':'-1','rushing_yards':'.1','rushing_tds':'6','receptions':'1','receiving_yards':'.1','receiving_tds':'6','fumbles_lost_total':'-1','passing_2pt_conversions':'2','rushing_2pt_conversions':'2','receiving_2pt_conversions':'2'}
                    vals=[num(r[f])for f in fields]
                    ys['nick-chart-ppr-v1']=int(sum(num(r[f])*Decimal(w)for f,w in fields.items())*50)if all(v is not None for v in vals)else None
                else:ys['nick-chart-ppr-v1']=None
                row=dict(player_id=r['player_id'],position=r['position'],game_id=r['game_id'],season=year,kickoff=k,available=k+7*86400,values=ys)
                rows.append(row);history[r['player_id']].append(row)
    for rs in history.values():rs.sort(key=lambda r:(r['available'],r['kickoff'],r['game_id']))
    return rows,history,games

def audit(public,private,source):
    p=json.loads((public/'FROZEN_PROTOCOL.json').read_text());run=json.loads((public/'RUN_RECEIPT.json').read_text());rows,history,games=load(source,p)
    chart='chart-wave'in public.name;counts=Counter();models=0
    @lru_cache(None)
    def feature(player,position,target,cutoff,floor):
        rs=[r for r in history.get(player,[])if r['season']>=floor and r['available']<cutoff][-8:];result=[]
        for w in (3,8):
            ys=[r['values'][target]for r in rs[-w:]if r['values'][target]is not None]
            result.extend([float(sum(ys)/len(ys))if ys else None,float(len(ys))])
        for i in range(1,5):
            r=rs[-i]if len(rs)>=i else None;y=r['values'][target]if r else None
            result.extend([float(y)if y is not None else None,(cutoff-r['kickoff'])/86400 if r else None,float(y is None)])
        result.extend(float(position==v)for v in('QB','RB','WR','TE'))
        return result,rs[-1]['available']if rs else None
    def packet_path(d):
        base=private.with_name('distribution-wave-v1')if d.get('reused_from')else private
        name=d.get('bundle_name',d.get('name'));path=base/name;assert sha(path)==d['sha256'];return path
    checked_features=set()
    for fitfile in sorted(public.glob('*-FIT.json')):
        fit=json.loads(fitfile.read_text());floor=fit['feature_floor'];target=fit['target'];cutoff=clock(fit['fit_cutoff_utc']);policy=p['policies'][fit['policy_id']];fitfloor=policy['fit_floor']
        roles={'QB','RB'}if'rush-att-qb-rb-specialization'in fit['family']else set(('QB','RB','WR','TE'))if chart else set(p['source_role_contract']['primary'][target]+p['source_role_contract']['extended'].get(target,[]))
        eligible=[r for r in rows if r['position']in roles and r['values'][target]is not None and r['season']>=max(floor,fitfloor)and r['available']<cutoff]
        assert len(eligible)==fit['training_n'];assert sorted({r['season']for r in eligible})==fit['training_seasons']
        assert hashlib.sha256(canonical([(r['game_id'],r['player_id'])for r in eligible])).hexdigest()==fit['training_membership_sha256']
        assert max((r['available']for r in eligible),default=None)==fit['latest_training_label_available'];counts['training_membership_clock_checks']+=4
        # Every training-row feature cutoff is its own game, not fit/query origin.
        latest=max((feature(r['player_id'],r['position'],target,r['kickoff'],floor)[1]for r in eligible if feature(r['player_id'],r['position'],target,r['kickoff'],floor)[1]is not None),default=None)
        assert latest==fit['latest_training_feature_available'];counts['training_feature_clock_checks']+=1
        if floor==2026:assert all(r['season']==2026 for r in eligible)
        d=fit['query_features'];path=packet_path(d)
        if d['sha256']not in checked_features:
            checked_features.add(d['sha256']);entries=json.loads(gzip.decompress(path.read_bytes()))
            for e in entries:
                q=e['query']
                if q.get('blocked_reason')and'count-ablation'in public.name:expected=[None]*20;latest=None
                else:expected,latest=feature(q['player_id'],q['position'],target,q['cutoff'],floor)
                for a,b in zip(expected,e['features']):
                    assert(a is None and b is None)or(a is not None and b is not None and math.isclose(a,b,rel_tol=3e-13,abs_tol=3e-10)),(fit['slot'],a,b)
                    counts['raw_query_feature_values_checked']+=1
                assert latest==e['latest_feature_available'];assert latest is None or latest<q['cutoff'];counts['raw_query_prefix_clocks_checked']+=1
        if fit['model']:
            packet_path(fit['model']);models+=1
    return dict(status='PASS_RAW_SOURCE_FEATURE_FLOORS_AND_ALL_TRAINING_MEMBERSHIPS',protocol_sha256=sha(public/'FROZEN_PROTOCOL.json'),run_receipt_sha256=sha(public/'RUN_RECEIPT.json'),counts=dict(counts),models_hash_verified=models,distinct_feature_packets=len(checked_features),strict_current_limit='2026-only outcomes/features/priors/transforms perregisteredsoftwarepolicy; fixed settings earlierresearch-exposed and retrospectiveidentity/sourcevintage retained',new_fits=0,new_forecasts=0,week8_outcomes_read=0)

if __name__=='__main__':
    result=audit(Path(sys.argv[1]),Path(sys.argv[2]),Path(sys.argv[3]));name='CHART'if'chart-wave'in sys.argv[1]else'DISTRIBUTION'if'distribution-'in sys.argv[1]else'COUNT_ABLATION'
    out=Path(__file__).parent/(name+'_INDEPENDENT_PREFIX_REVIEW.json');out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
