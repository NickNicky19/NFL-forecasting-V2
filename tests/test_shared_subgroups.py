import gzip,json,tempfile,unittest
from pathlib import Path
from nfl_v2 import shared_subgroups as s

class SharedSubgroupTests(unittest.TestCase):
 def row(self,p='p',arm='H-MULTI',strict=False,actual=0.,prediction=0.,fallback='none',target='rush_att',product='lower_median'):
  return dict(game_id='2026_01_A_B',player_id=p,target=target,population='primary',position='RB',history_regime=arm,procedure_id=s.C02+(':strict-current-inputs'if strict else':common-feature-memory'),product_id=product,policy_id=arm+('-STRICT'if strict else'-COMMON'),information_policy='STRICT-CURRENT'if strict else'COMMON-2022-MEMORY',season=2026,week=1,prediction=prediction,actual=actual,fallback=fallback,distribution_summary=dict(crps=abs(prediction-actual)if actual is not None else None,nll=0.,infinite_nll=False,interval90_width=1,interval90_covered=True,zero_mass=1.))
 def controls(self,rs):
  return [dict(r,procedure_id='v2-distribution-controls-reconstruction-v2:ordered_leaf_cdf:'+('strict-current-inputs'if 'strict-current' in r['procedure_id']else'common-feature-memory'))for r in rs]
 def test_stream_packet_does_not_lose_rows(self):
  with tempfile.TemporaryDirectory()as d:
   p=Path(d)/'p.gz';rows=[dict(i=i,pad='x'*50000)for i in range(5)];p.write_bytes(gzip.compress(json.dumps(dict(schema='fixture',rows=rows)).encode()));self.assertEqual(list(s.packet_rows(p)),rows)
 def test_filter_future_before_decoding_actual(self):
  self.assertIsNone(s.normalize(dict(season=2026,week=8,actual='INVALID'), 'fixture'))
 def test_shared_membership_and_fallback_mask(self):
  rs=[self.row(arm=a)for a in s.CORE]+[self.row(strict=True,arm='H-CURRENT',fallback='startup')]
  m={s.identity(rs[0]):dict(cohorts=['all','top10','workload_zero'])}
  out,c,dates,shared=s.evaluate(rs,self.controls(rs),m,'fixture',[])
  self.assertEqual(shared['rush_att:primary'],0)
  self.assertFalse(any(r['fallback_view']=='three_core_history_learned_overlap'and 'strict-current' in r['procedure_id']for r in out))
  self.assertEqual(sum(r['cohort_id']=='top10'and r['fallback_view']=='full_system'for r in out),4)
 def test_mismatched_outcome_rejected(self):
  r=self.row();o=self.controls([r]);o[0]['actual']=1
  with self.assertRaisesRegex(ValueError,'label/role'):s.evaluate([r],o,{s.identity(r):dict(cohorts=['all'])},'fixture',[])
 def test_duplicate_prediction_rejected(self):
  r=self.row()
  with self.assertRaisesRegex(ValueError,'duplicate candidate'):s.evaluate([r,r],self.controls([r]),{s.identity(r):dict(cohorts=['all'])},'fixture',[])
 def test_missing_actual_kept_in_coverage(self):
  r=self.row(actual=None);m=s.metrics([r],'rush_att','lower_median');self.assertEqual(m['forecast_rows'],1);self.assertEqual(m['n'],0);self.assertIsNone(m['mae']);self.assertEqual(m['missing_actual_n'],1)
 def test_chart_exact_grid_and_signed_values(self):
  r=self.row(actual=-1.02,prediction=-.02,target=s.CHART)
  m=s.metrics([r],s.CHART,'lower_median');self.assertEqual(m['abs_lt_1'],0);self.assertEqual(m['abs_le_1'],1);self.assertEqual(m['precision_counts_exact_grid']['abs_le_1']['numerator'],1)
 def test_mean_not_rounded_to_chart_grid(self):
  r=self.row(actual=1.,prediction=.9999,target=s.CHART,product='mean');m=s.metrics([r],s.CHART,'mean');self.assertNotIn('precision_counts_exact_grid',m);self.assertAlmostEqual(m['mae'],.0001)
 def test_paired_delta_sign_and_zero_denominator(self):
  a=self.row(prediction=1);b=dict(a,prediction=0,procedure_id='control');r=s.paired([a],{s.identity(b):b},'mae');self.assertEqual(r['absolute_error_delta'],1);self.assertIsNone(r['relative_error_delta']);self.assertEqual(r['paired_n'],1)
 def test_fallback_contribution_adds_to_full_error(self):
  a=self.row(prediction=2,fallback='startup');b=self.row('other',prediction=4);r=s.metrics([a,b],'rush_att','lower_median');d=r['fallback_decomposition'];self.assertEqual(d['fallback_contribution']+d['learned_contribution'],r['mae'])
 def test_infinite_law_score_not_dropped(self):
  r=self.row();r['distribution_summary'].update(nll=None,infinite_nll=True);m=s.metrics([r],'rush_att','lower_median');self.assertIsNone(m['NLL']);self.assertEqual(m['NLL_state'],'INFINITE');self.assertEqual(m['infinite_NLL'],1)

if __name__=='__main__':unittest.main()
