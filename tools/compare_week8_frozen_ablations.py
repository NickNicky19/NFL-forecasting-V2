"""Grade paired frozen A/B/C and C02/D1/D2 contrasts from saved errors only."""
import argparse,collections,hashlib,json,math,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools import grade_saved_week8 as core,grade_week8_captured_library as lib
from nfl_v2.shared_subgroups import packet_rows
from nfl_v2.paired_uncertainty import paired_losses


def run(private,public):
    start=time.monotonic();out=public/'frozen-ablation-grading-v1';out.mkdir(exist_ok=False);groups=collections.defaultdict(lambda:collections.defaultdict(dict));source={}
    for r in packet_rows(private/'CAPTURED_LIBRARY_NUMERIC_ROWS_V1.json.gz'):
        if r['capture_version']not in('AVAILABILITY_AB','AVAILABILITY_C','C02','D1_D2'):continue
        g=lib.group(r);mid=lib.view_id(g);source[mid]=r
        if r['error']is None or not r['T90_eligible']:continue
        if r['capture_version'].startswith('AVAILABILITY'):tag=(r['procedure_id'],r['history_regime'],r['product_id'],r['target']);variant=r['availability_arm']
        elif r['capture_version']=='C02':
            variant='C02'if'c02_explicit_lag_block_removed'in r['procedure_id']else'BASE';tag=('C02',r['history_regime'],r['product_id'],r['target'],r['information_policy'])
        else:
            variant='D1'if':D1:'in r['procedure_id']else'D2'if':D2:'in r['procedure_id']else'BASE';tag=('D1_D2',r['history_regime'],r['product_id'],r['target'],r['information_policy'])
        groups[tag][variant][lib.key(r)]=(r['error'],r['game_id'],mid)
    rows=[]
    for tag,parts in sorted(groups.items()):
        contrasts=[('B','A'),('C','B')]if tag[0].startswith('v2-availability')else[('C02','BASE')]if tag[0]=='C02'else[('D1','BASE'),('D2','BASE'),('D2','D1')]
        for cand,comp in contrasts:
            if cand not in parts or comp not in parts:continue
            aa,bb=parts[cand],parts[comp];keys=sorted(set(aa)&set(bb));target=keys[0][-1]if keys else tag[3];square=target=='anytime_td';loss=lambda d,k:d[k][0]**2 if square else abs(d[k][0]);u=paired_losses([loss(aa,k)for k in keys],[loss(bb,k)for k in keys],[8]*len(keys),[k[0]for k in keys])
            rows.append(dict(contrast=cand+'_MINUS_'+comp,recipe=list(tag),target=target,metric='Brier'if square else'MAE',**u,candidate_method_key=aa[keys[0]][2]if keys else None,comparator_method_key=bb[keys[0]][2]if keys else None,
                comparison_contract='AvailabilityB−A: same fitted model, qualified fresher query features; C−B separately registered refit. C02/D1/D2 own registered frozen mechanisms, same earlier control. All current-vintage outcome grading; no new prediction or causal remedy inferred.',
                D_window_contract='FOUR_OBSERVED_POSITION_GROUP_GAMES'if tag[0]=='D1_D2'else None,whole_week_complete=False))
    core.save(out/'PAIRED_FROZEN_CONTRASTS.json',rows);core.write_csv(out/'PAIRED_FROZEN_CONTRASTS.csv',rows)
    core.save(out/'RUN_RECEIPT.json',dict(state='FROZEN_PAIRED_CAPTURE_CONTRASTS_GRADED',at_utc=core.now(),seconds=time.monotonic()-start,contrasts=len(rows),source_rows_sha256=core.sha(private/'CAPTURED_LIBRARY_NUMERIC_ROWS_V1.json.gz'),code_sha256=core.sha(__file__),new_fits=0,new_forecasts=0,new_inference=0,scope='Original frozen Week8 predictions; not historical backtests, confidence selection, or new mechanism search.'))
    print(json.dumps(dict(state='PAIRED_ABLATIONS_GRADED',contrasts=len(rows),seconds=time.monotonic()-start)))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--private-root',type=Path,required=True);p.add_argument('--public-root',type=Path,required=True);a=p.parse_args();run(a.private_root,a.public_root)
