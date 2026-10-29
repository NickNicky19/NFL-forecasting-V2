import math
import pickle
import unittest

import numpy as np
from threadpoolctl import threadpool_limits

from nfl_v2.hgb_control import (FEATURES, PARAMS, FeatureHistory, fit_floor,
                                make_estimator, project_point, train_indices)


def row(game, kickoff, available, value, season=2025):
    return dict(game_id=game,player_id='00-0012345',position='QB',season=season,
                kickoff=kickoff,available=available,values={'pass_yd':value})


class HGBControlTests(unittest.TestCase):
    def test_strict_available_clock_and_target_game_exclusion(self):
        history=FeatureHistory([row('old',10,17,10),row('target',20,27,9999)])
        before,m=history.get('00-0012345','QB','pass_yd',17)
        self.assertEqual(before[1],0);self.assertIsNone(m)
        after,m=history.get('00-0012345','QB','pass_yd',20)
        self.assertEqual(after[:4],[10,1.,10,1.]);self.assertEqual(m,17)
        self.assertEqual(after[4],10)

    def test_missing_slots_preserved_and_older_feature_memory_not_filtered_by_arm(self):
        history=FeatureHistory([row('older',1,8,-5,2022),row('missing',2,9,None,2026)])
        values,m=history.get('00-0012345','QB','pass_yd',10)
        self.assertEqual(values[:4],[-5,1.,-5,1.])
        self.assertTrue(math.isnan(values[4]));self.assertEqual(values[6],1.)
        self.assertEqual(values[7],-5);self.assertEqual(m,9)

    def test_training_floor_and_availability_are_separate_from_features(self):
        rows=[row('2022',1,8,1,2022),row('2025',2,9,2,2025),row('2026',3,10,3,2026),row('later',4,11,4,2026)]
        self.assertEqual(train_indices(rows,11,fit_floor('H-CURRENT')).tolist(),[2])
        self.assertEqual(train_indices(rows,11,fit_floor('H-RECENT')).tolist(),[1,2])
        self.assertEqual(train_indices(rows,11,fit_floor('H-MULTI')).tolist(),[0,1,2])

    def test_no_new_player_encoding_or_position_transform(self):
        values,m=FeatureHistory([]).get('00-0099999','TE','pass_yd',10)
        self.assertEqual(len(values),len(FEATURES));self.assertEqual(values[-4:],[0.,0.,0.,1.])
        self.assertTrue(math.isnan(values[0]));self.assertEqual(values[1],0.)

    def test_fixed_params_and_support_projection(self):
        self.assertFalse(PARAMS['early_stopping']);self.assertEqual(PARAMS['max_iter'],64)
        self.assertEqual(PARAMS['random_state'],1701)
        self.assertEqual(project_point('pass_int',-.01),0.)
        self.assertEqual(project_point('rush_yd',-5),-5.)
        with self.assertRaises(ValueError):project_point('rec',math.nan)

    def test_fictional_estimator_api_and_pickle_replay(self):
        # Three synthetic fits are software checks, never NFL experiments.
        x=np.arange(1600,dtype=float).reshape(80,20)/100
        with threadpool_limits(limits=2):
            for target,objective,y in [('pass_yd','absolute_error_point',np.arange(80,dtype=float)),
                                       ('pass_yd','squared_error_mean',np.arange(80,dtype=float)),
                                       ('anytime_td','log_loss_probability',np.asarray([0,1]*40))]:
                model=make_estimator(target,objective).fit(x,y)
                restored=pickle.loads(pickle.dumps(model,protocol=5))
                self.assertTrue(np.array_equal(model.predict(x),restored.predict(x)))
                if target=='anytime_td':
                    probs=model.predict_proba(x);self.assertTrue(np.all((probs>=0)&(probs<=1)))
                    self.assertTrue(np.allclose(probs.sum(axis=1),1))


if __name__=='__main__':unittest.main()
