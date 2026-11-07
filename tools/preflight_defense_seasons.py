"""Emit finite source-bound D1/D2 readiness metadata; never execute a model."""
from __future__ import annotations
import argparse,csv,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2 import defense_season_preflight as adapter

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb')as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def main(a):
    if len(a.season)!=len(set(a.season)):raise ValueError('duplicate seasons would inflate the planned-cell denominator')
    if a.public.exists():raise ValueError('new immutable dry-run output required')
    a.public.mkdir(parents=True);root=Path(__file__).resolve().parents[1]
    old=json.loads((root/'reports/continuation-20261030c/qualified-defense-information-v1/FROZEN_PROTOCOL.json').read_text())
    grid=[];inputs=[];summaries=[]
    for year in a.season:
        adapter.validate_year(year);version='v1'if year==2025 else'v2'
        protocol=root/f'reports/continuation-20261030c/season-{year}-{version}/FROZEN_PROTOCOL.json';p=json.loads(protocol.read_text());assert p['evaluation_season']==year
        gg=adapter.logical_grid(year,old['targets']);grid.extend(gg)
        for item in p['source_ids']:
            name=item['name']
            if name.startswith('stats_player_week_')and int(name.split('_')[-1].split('.')[0])>year:continue
            actual=a.source_root/name if a.source_root else None
            inputs.append(dict(season=year,name=name,expected_sha256=item['sha256'],present=actual.exists()if actual else None,bytes=actual.stat().st_size if actual and actual.exists()else None,byte_hash_verified=sha(actual)==item['sha256']if actual and actual.exists()else None,source_values_decoded=0))
        summaries.append(dict(season=year,original_season_protocol=protocol.relative_to(root).as_posix(),original_season_protocol_sha256=sha(protocol),original_query_cells=p['query_cells'],original_query_games=p['query_games'],weeks=p['evaluation_weeks'],frozen_query_sha256=p['frozen_queries_sha256'],query_source_hashes=p['query_sources'],nominal_fit_origins_per_window=len(gg)//2,unique_policy_fit_origins_per_window=sum(not r['alias_of_unrun_origin']for r in gg)//2,output_recipe_week_cells_per_window=sum(len(r['output_products'])for r in gg)//2,actual_new_fits=0,actual_new_forecasts=0,actual_closed_season_cells=0))
    with(a.public/'FINITE_FIT_ORIGIN_PLAN.csv').open('x',newline='')as f:
        w=csv.DictWriter(f,fieldnames=list(grid[0]));w.writeheader();w.writerows(dict(r,output_products=json.dumps(r['output_products'],separators=(',',':')))for r in grid)
    files=['nfl_v2/qualified_defense_wave.py','nfl_v2/qualified_defense.py','nfl_v2/qualified_defense_inputs.py','nfl_v2/scheduled_defense.py','nfl_v2/scheduled_defense_wave.py','nfl_v2/seasonal_rolling_v2.py','nfl_v2/distribution_wave_v2.py','nfl_v2/ordered_information_ablation.py','nfl_v2/defense_season_preflight.py','tools/preflight_defense_seasons.py']
    receipt=dict(version=adapter.VERSION,state='DRY_RUN_METADATA_READY_NO_OLDER_SEASON_MODEL_EXECUTION',source_bindings=[dict(path=n,sha256=sha(root/n))for n in files],seasons=summaries,input_byte_checks=inputs,windows=['observed','scheduled'],fit_origin_grid_rows=len(grid),units='Logical fit-origin requests including policy aliases; not actual model fits or NFL samples.',preparation_limit='No private query/features/labels/model packet opened or materialized. Only public source/query metadata and optional raw file byte hashes read.',execution_limit='Old2026runner is not parameterized; this planner and tested feature adapter do not implement/authorize older-season training/scoring. A thin execution integration with existing seasonal loop remains, then exact prefit protocol, independent review, measured bounded pilot, factual retention PASS and separate root sole-worker release.',recovery_gate='UNCHANGED; current missing-only archive recovery not complete',new_fits=0,new_model_inference=0,new_forecasts=0,new_scores=0,new_prepared_private_rows=0,Week8_outcomes_read=0)
    (a.public/'PREFLIGHT_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(dict(state=receipt['state'],seasons=summaries,fit_origin_grid_rows=len(grid),input_files_checked=len(inputs),all_present_hashes_match=all(r['byte_hash_verified']for r in inputs),new_fits=0)))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--season',type=int,action='append',required=True);p.add_argument('--source-root',type=Path);p.add_argument('--public',type=Path,required=True);main(p.parse_args())
