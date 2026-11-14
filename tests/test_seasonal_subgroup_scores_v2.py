import unittest
from nfl_v2 import seasonal_subgroup_scores_v2 as s

class SeasonalSubgroupV2Tests(unittest.TestCase):
 def row(self,year=2025,arm='H-MULTI',week=18,strict=False):
  return dict(game_id=f'{year}_{week:02}_A_B',player_id='fixture',target='rush_att',population='primary',position='RB',history_regime=arm,procedure_id=s.C02+(':strict-current-inputs'if strict else':common-feature-memory'),product_id='lower_median',policy_id=arm+('-STRICT'if strict else'-COMMON'),information_policy='STRICT-CURRENT'if strict else'COMMON-2022-MEMORY',season=year,week=week,prediction=1.,actual=0.,fallback='none',distribution_summary=dict(crps=1.,nll=0.,infinite_nll=False,interval90_width=1,interval90_covered=True,zero_mass=.5))
 def test_historical_week18_admitted_and_current2026_rejected(self):
  raw={k:str(v)for k,v in self.row().items()if k not in('distribution_summary',)};raw['family']='ordered_leaf_cdf';raw['distribution_summary']='';r=s.normalize(raw,2025,{});self.assertEqual(r['week'],18)
  raw['season']='2026'
  with self.assertRaises(ValueError):s.normalize(raw,2025,{})
 def test_same_season_reference_excludes_c02(self):
  common=dict(week='ALL',position='ALL',fallback_view='ALL',population='primary',target='rush_att',n=10,product_id='squared_error_mean',policy_id='H-MULTI-COMMON',history_regime='H-MULTI',mae=2,mse=5)
  rows=[dict(common,procedure_id='hgb-direct-history-controls-v1:squared_error_mean:common-feature-memory'),dict(common,procedure_id=s.C02+':common-feature-memory',mae=.1,mse=.01)]
  refs=s.same_season_specs(rows);self.assertTrue(refs);self.assertFalse(any(x['procedure_id'].startswith(s.C02)for x in refs));self.assertEqual(refs[0]['prior_full_error'],2)
 def test_year_ids_differ_and_week18_coverage_retained(self):
  ids=[]
  for year in(2024,2025):
   r=self.row(year);old=dict(r,procedure_id='v2-distribution-controls-reconstruction-v2:ordered_leaf_cdf:common-feature-memory');m={s.identity(r):dict(cohorts=['all','top10'])};out,*_=s.evaluate([r],[old],m,'fixture',[],year);full=next(x for x in out if x['cohort_id']=='all'and x['fallback_view']=='full_system');ids.append(full['record_id']);self.assertEqual(full['season'],year);self.assertEqual(full['evaluation_weeks'],[18])
  self.assertNotEqual(*ids)
 def test_18_week_bootstrap_is_present(self):
  rows=[self.row(week=w)for w in range(1,19)];controls={s.identity(r):dict(r,prediction=0.,procedure_id='control')for r in rows};p=s.paired(rows,controls,'mae');self.assertEqual(p['uncertainty']['week_clusters'],18);self.assertEqual(p['uncertainty']['week_interval'],[1.,1.]);self.assertEqual(p['uncertainty']['bootstrap_replicates'],500)
 def test_strict_never_receives_missing_threecore_cells(self):
  r=self.row(strict=True,arm='H-CURRENT');old=dict(r,procedure_id='v2-distribution-controls-reconstruction-v2:ordered_leaf_cdf:strict-current-inputs');out,*_=s.evaluate([r],[old],{s.identity(r):dict(cohorts=['all'])},'fixture',[],2025);self.assertFalse(any(x['fallback_view']=='three_core_history_learned_overlap'for x in out))
 def test_fixed_alias_preserves_hgb_point_contract(self):
  spec=dict(target='rush_att',purpose='display_point',procedure_id='hgb-direct-history-controls-v1:squared_error_mean',product_id='squared_error_mean');r=s.alias_fixed(spec);self.assertEqual(r['product_id'],'squared_error_mean');self.assertTrue(r['procedure_id'].endswith(':common-feature-memory'))
 def test_streamed_encoding_matches_canonical_bytes(self):
  import tempfile,json
  from pathlib import Path
  value={'z':'signed−value','rows':[{'x':1,'y':[None,2.5]},{'x':0,'y':[]}]}
  with tempfile.TemporaryDirectory()as d:
   p=Path(d)/'a.json';s.stream_json(p,value);self.assertEqual(p.read_bytes(),s.canonical(value));self.assertEqual(json.loads(p.read_bytes()),value)
 def test_same_season_global_reference_is_stronger_than_weak_family(self):
  common=dict(week='ALL',position='ALL',fallback_view='ALL',population='primary',target='pass_yd',n=10,product_id='mean',policy_id='H-MULTI-COMMON',history_regime='H-MULTI',mae=2,mse=5,CRPS=1)
  rows=[dict(common,procedure_id='v2-distribution-controls-reconstruction-v2:ordered_leaf_cdf:common-feature-memory'),dict(common,procedure_id='hgb-direct-history-controls-v1:squared_error_mean:common-feature-memory',mae=1,mse=4,CRPS=None)]
  refs=s.same_season_specs(rows);point=[r for r in refs if r['purpose']=='display_point'];self.assertEqual(len(point),1);self.assertIn('hgb-direct',point[0]['procedure_id']);self.assertEqual(point[0]['prior_full_error'],1)
if __name__=='__main__':unittest.main()
