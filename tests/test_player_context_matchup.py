import copy
import json
import unittest

import numpy as np

from nfl_v2.player_context_matchup import (ContextHistory, CountLaw, CompletionModel,
    export_forest, restored_forest_law, exact_probabilities)
from nfl_v2.distribution_wave_v2 import FittedLawModel
from nfl_v2.distribution_laws import prior
from nfl_v2.player_context_typed_adapter_v2 import restore_completion


def row(i,player='fictional-qb',attempts=20,completions=12,available=None):
    a=[0]*25;c=[0]*25;a[i%25]=attempts;c[i%25]=completions
    return dict(game_id='fictional-'+str(i),player_id=player,season=2025,week=i+1,
        team='AA',opponent='BB',kickoff=i*604800.,available=i*604800.+604800. if available is None else available,
        attempts=attempts,completions=completions,official_attempts=attempts,official_completions=completions,
        context_attempts=a,context_completions=c,physical_participation=True,target_parity=True,
        field_context={k:dict(mean=10.,n=attempts)for k in ['ydstogo','yardline_100','game_seconds_remaining','score_differential']})


class PlayerContextTests(unittest.TestCase):
    def test_future_and_target_outcomes_do_not_change_earlier_features(self):
        rows=[row(i)for i in range(12)];q=dict(rows[8]);h=ContextHistory(rows)
        expected=h.direct_features(q,'E3');other=copy.deepcopy(rows)
        for r in other[8:]:
            r['context_completions']=[v//2 for v in r['context_completions']]
            r['completions']=sum(r['context_completions']);r['official_completions']=r['completions']
        np.testing.assert_array_equal(expected,ContextHistory(other).direct_features(q,'E3'))
        self.assertLess(h.describe(q)['latest_source_available'],q['kickoff'])

    def test_recent_history_is_game_order_after_availability_admission(self):
        rows=[row(i,attempts=v,completions=0)for i,v in enumerate([100,10,20,30])]
        rows[0]['available']=5*604800.
        h=ContextHistory(rows,window=3);selected=h.player_rows('fictional-qb',6*604800.)
        self.assertEqual([r['attempts']for r in selected],[10,20,30])

    def test_unknown_context_and_team_games_keep_denominators(self):
        rows=[row(0),row(0,player='fictional-backup',attempts=3,completions=1),row(1)]
        h=ContextHistory(rows);q=dict(row(4));d=h.describe(q)
        self.assertAlmostEqual(sum(d['mix']),1.)
        self.assertEqual(d['opponent_games'],2)
        self.assertEqual(sum(d['opponent_context_n']),43)

    def test_thinned_count_laws_have_exact_boundaries_and_coherence(self):
        a=CountLaw(30,8);c=CountLaw(18,8)
        self.assertLessEqual(c.mean,a.mean)
        self.assertLessEqual(c.quantile(.5),a.quantile(.5))
        previous=1.
        for line in [-.5,0,1.5,19.5,20,40.5]:
            p=exact_probabilities(c,line)
            self.assertAlmostEqual(sum(p.values()),1.)
            self.assertGreaterEqual(p['over'],0.)
            self.assertLessEqual(p['over'],previous);previous=p['over']
            if line%1:self.assertEqual(p['push'],0.)
        self.assertEqual(exact_probabilities(CountLaw(0,8),.5),dict(over=0.,under=1.,push=0.))

    def test_typed_forest_restoration_matches_fitted_points_and_law(self):
        x=np.arange(180,dtype=float).reshape(90,2);x[1,0]=np.nan
        y=np.asarray([i%7 for i in range(90)],float);p=prior(y,'pass_cmp')
        model=FittedLawModel('ordered_leaf_cdf','pass_cmp').fit(x,y,['QB']*len(y))
        saved=export_forest(model)
        original=model.predict(x[[1,40]],['QB','QB'],{'QB':p})
        for point,(law,_)in zip(x[[1,40]],original):
            restored=restored_forest_law(saved,point,p)
            self.assertAlmostEqual(restored.mean,law.mean,places=12)
            self.assertEqual(restored.quantile(.5),law.quantile(.5))
            for threshold in [0,1,3,8]:self.assertAlmostEqual(restored.cdf(threshold),law.cdf(threshold),places=12)

    def test_conditional_model_restoration_is_exact(self):
        rows=[row(i)for i in range(12)];h=ContextHistory(rows)
        model=CompletionModel(True,80).fit(rows[:8],h)
        restored=CompletionModel.restore(model.payload())
        np.testing.assert_array_equal(model.probabilities(rows[-1],h),restored.probabilities(rows[-1],h))

    def test_portable_adapter_rejects_semantics_from_json_key_order(self):
        rows=[row(i,player='fictional-'+str(i%2)) for i in range(16)]
        for i,r in enumerate(rows):
            r['team']='AA'if i%3 else'CC';r['opponent']='BB'if i%4 else'DD'
        h=ContextHistory(rows);model=CompletionModel(True,20).fit(rows[:12],h)
        payload=json.loads(json.dumps(model.payload(),sort_keys=True))
        restored=restore_completion(payload,producer_version='B-player-context-matchup-01-v1')
        np.testing.assert_array_equal(model.probabilities(rows[-1],h),restored.probabilities(rows[-1],h))
        with self.assertRaises(ValueError):restore_completion(payload,producer_version='unbound-other-version')


if __name__=='__main__':unittest.main()
