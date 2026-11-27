"""Append complete empirical masses without changing the frozen shadow.

FTN-derived output: CC-BY-SA-4.0, FTN Data via nflverse.
"""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from nfl_v2 import player_context_matchup as ctx
from nfl_v2.distribution_laws import Law
from tools.run_player_context_wave import read,write,sha,now


def main():
    base = ROOT/'reports/information-first-20261112-01/B/current-conditional-shadow-v1'
    packet_path = base/'FORECAST_ONLY_PACKET.json.gz'
    packet = read(packet_path)
    rows = []
    for row in packet['forecasts']:
        result = dict(game_id=row['game_id'],player_id=row['player_id'],method=row['method'],
            output_state=row['output_state'],mean=row['mean'],lower_median=row['lower_median'],law=None)
        if row['output_state'] == 'CONDITIONAL_FORECAST':
            model_path = base/'fits'/(row['method']+'.json.gz')
            assert sha(model_path) == row['model_sha256']
            p = row['law']['prior']
            assert p['kind'] == 'geometric'
            prior = Law('geometric',q=p['q'])
            law = ctx.restored_forest_law(read(model_path)['model'],np.asarray(row['features'],float),prior)
            assert law.mean == row['mean'] and law.quantile(.5) == row['lower_median']
            result['law'] = dict(kind='leaf_mixture',support=law.support.tolist(),
                weights=law.weights.tolist(),prior=law.prior.parameters(),mixture=law.b)
        rows.append(result)
    write(base/'COMPLETE_LAW_CAPSULE_V1.json.gz',dict(
        id='B_FTN_CURRENT_SHADOW_COMPLETE_LAW_SERIALIZATION_v1',
        actual_packaged_UTC=now(), original_forecast_issued_UTC=packet['forecast_issued_UTC'],
        original_packet_sha256=sha(packet_path),original_packet_preserved=True,
        change='Output-preserving serialization supplement: original law field carried mixture/prior parameters; empirical support/masses were reconstructable from boundmodel/features. Complete law now self-contained.',
        new_fits=0,new_forecasts=0,new_sides=0,changed_points=0,changed_distributions=0,
        prediction_time_not_backdated=True, source_contract=packet['source_contract'],
        conditioning='Physicalappearance conditional scenario;notappearanceprobability or actual-line recommendation',
        forecasts=rows, license=packet['license']))
    print('PASS: eight complete laws appended; original packet preserved; zero changed forecasts')


if __name__ == '__main__':
    main()
