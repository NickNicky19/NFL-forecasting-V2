import io,math,unittest
from nfl_v2 import seasonal_rolling_v2 as s
from nfl_v2 import hgb_control as source
from nfl_v2.scoring import point_metrics
class SeasonalTests(unittest.TestCase):
    def test_relative_windows_and_exact_aliases(self):
        self.assertEqual(s.policies(2025)['H-RECENT-COMMON'],('H-RECENT',2024,2022))
        self.assertEqual(s.policies(2024)['H-CURRENT-STRICT'],('H-CURRENT',2024,2024))
        self.assertEqual(len({s.alias_policy(2022,p) for p in s.policies(2022)}),1)
        self.assertEqual(s.alias_policy(2023,'H-MULTI-COMMON'),'H-RECENT-COMMON')
    def test_full_balanced_grid(self):
        self.assertEqual(len(s.TARGETS),12);self.assertEqual(sum(len(s.methods(t)) for t in s.TARGETS),64)
        self.assertEqual(18*4*64,4608);self.assertEqual(s.methods(s.chart.TARGET),['leaf','glm_law','c02'])
    def test_current_is_fitting_when_memory_older(self):
        rows=[dict(player_id='x',season=y,available=a,kickoff=a-10,game_id=str(y),values={'rec':v}) for y,a,v in ((2022,20,9),(2025,40,2))]
        common=source.FeatureHistory(rows);strict=source.FeatureHistory([r for r in rows if r['season']==2025])
        self.assertEqual(common.get('x','WR','rec',40)[0][0],9)
        self.assertTrue(math.isnan(strict.get('x','WR','rec',40)[0][0]))
    def test_meter_math_independent_point_function(self):
        m=s.Meter()
        for i,(p,y) in enumerate(((2,1),(-1,3),(4,4))):m.add(dict(prediction=p,actual=y,target='rush_yd',product_id='mean',actual_grid=None,fallback='none',game_id=str(i),week=1))
        a=m.result();b=point_metrics([2,-1,4],[1,3,4],'rush_yd')
        for k in ('mae','mse','rmse','bias','p90_abs','p95_abs','max_abs','exact_rate','abs_lt_1','abs_le_1'):self.assertAlmostEqual(a[k],b[k])
    def test_chart_exact_grid_boundary_and_missing(self):
        m=s.Meter();m.add(dict(prediction=4.8,actual=9.8,actual_grid=490,target=s.chart.TARGET,product_id='lower_median',fallback='none',game_id='a',week=8));m.add(dict(prediction=0.,actual=None,target=s.chart.TARGET,product_id='lower_median',fallback='cold_start_role_prior',game_id='b',week=8))
        r=m.result();self.assertEqual(r['n'],1);self.assertEqual(r['forecast_rows'],2);self.assertEqual(r['abs_lt_5'],0);self.assertEqual(r['abs_le_5'],1)
    def test_infinite_probability_logloss_not_clipped(self):
        m=s.Meter();m.add(dict(prediction=0.,actual=1.,target='anytime_td',product_id='event_probability',fallback='constant_zero',game_id='a',week=1));r=m.result();self.assertEqual(r['log_loss'],'Infinity');self.assertEqual(r['brier'],1.)
    def test_chart_means_are_not_forced_to_grid(self):
        m=s.Meter();m.add(dict(prediction=.333,actual=0.,target=s.chart.TARGET,product_id='mean',actual_grid=0,fallback='none',game_id='a',week=1));self.assertEqual(m.result()['mae'],.333)
    def test_streaming_budget_rejects_before_actual_bytes(self):
        raw=io.BytesIO();stream=s.CheckedStream(raw,lambda:5);stream.write(b'abcd')
        with self.assertRaises(RuntimeError):stream.write(b'ef')
        self.assertEqual(raw.getvalue(),b'abcd')
if __name__=='__main__':unittest.main()
