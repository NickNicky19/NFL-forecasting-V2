import unittest,gzip,json,tempfile
from pathlib import Path
from nfl_v2.pregame_views import PriorWorkload,memberships,evaluate,identity,read_predictions


class PregameViewTests(unittest.TestCase):
    def test_strict_cutoff_missing_slots_and_opportunity_units(self):
        rows=[dict(player_id='p',game_id=str(i),available=i,workload={'attempts':i,'carries':None if i==3 else i,'targets':2}) for i in range(1,6)]
        history=PriorWorkload(rows)
        view=history.at('p','rush_att',5)
        self.assertEqual(view['history_slots'],3)
        self.assertEqual(view['supported_slots'],2)
        self.assertEqual(view['mean'],3.)
        self.assertEqual(view['latest_available'],4)
        self.assertEqual(history.at('p','rec_yd',5)['mean'],2.)
        self.assertEqual(history.at('new','rush_att',5)['mean'],None)

    def test_top_membership_has_no_outcome_or_competitor_dependence(self):
        rows=[dict(player_id=f'p{i:02}',game_id='old',available=1,workload={'attempts':0,'carries':30-i,'targets':0}) for i in range(25)]
        queries=[dict(player_id=f'p{i:02}',game_id='next',target='rush_att',population='primary',week=1,actual=-1000*i) for i in range(25)]
        a,_=memberships(queries,PriorWorkload(rows),{1:2})
        b,_=memberships([dict(q,actual=999999) for q in reversed(queries)],PriorWorkload(rows),{1:2})
        self.assertEqual(a,b)
        for group,n in [('top10',10),('top15',15),('top20',20),('rank1_10',10),('rank11_15',5),('rank16_20',5),('rank21plus',5)]:
            self.assertEqual(sum(group in m['cohorts'] for m in a.values()),n)

    def test_history_learned_overlap_and_fallback_contribution(self):
        query=dict(player_id='p',game_id='next',target='rush_att',population='primary',week=1)
        member={identity(query):dict(cohorts=['all'])};records=[]
        for arm in ('H-CURRENT','H-RECENT','H-MULTI'):
            records.append(dict(query,family='fictional',procedure_id='fictional',product_id='point',history_regime=arm,prediction=1.,actual=3.,fallback='none' if arm!='H-CURRENT' else 'constant_zero'))
        result=evaluate(records,member,'fixture')
        self.assertEqual(sum(r['fallback_view']=='three_history_learned_overlap' for r in result),0)
        current=next(r for r in result if r['history_regime']=='H-CURRENT')
        self.assertEqual(current['n'],1);self.assertEqual(current['scored_fallback_rows'],1);self.assertEqual(current['mae'],2.)
        self.assertEqual(sum(r['fallback_view']=='own_learned_only' for r in result),2)

    def test_ties_use_stable_identity_and_unknowns_remain_unranked(self):
        queries=[dict(player_id=p,game_id='next',target='rush_att',population='primary',week=1) for p in ('z','b','a')]
        history=PriorWorkload([dict(player_id=p,game_id='old',available=1,workload={'carries':2}) for p in ('a','b')])
        m,_=memberships(queries,history,{1:2})
        self.assertEqual(m[identity(queries[2])]['rank'],1)
        self.assertEqual(m[identity(queries[1])]['rank'],2)
        self.assertIn('unranked',m[identity(queries[0])]['cohorts'])

    def test_missing_player_ids_keep_separate_blocked_query_keys(self):
        rows=[dict(player_id=None,query_id='q'+str(i),game_id='future',target='rec',population='exante',week=8) for i in (1,2)]
        m,_=memberships(rows,PriorWorkload([]),{8:5})
        self.assertEqual(len(m),2)
        self.assertTrue(all(v['rank'] is None for v in m.values()))

    def test_original_hgb_wrapped_chunks_and_future_exclusion(self):
        row=dict(game_id='fixture',player_id='p',position='RB',target='rush_att',population='primary',week=1,
                 history_regime='H-CURRENT',objective='absolute_error_point',prediction=1,actual=2,fallback='none')
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)
            for w in (1,8):
                with gzip.open(p/f'W{w:02}-fixture.json.gz','wt') as f:json.dump(dict(schema='fixture',rows=[dict(row,week=w)]),f)
            result=list(read_predictions('hgb',p))
            self.assertEqual(len(result),1);self.assertEqual(result[0]['week'],1)

    def test_future_view_budget_fails_before_emitting_partial_scores(self):
        q=dict(player_id='p',game_id='next',target='rush_att',population='primary',week=1)
        rows=[dict(q,family='fictional',procedure_id='x',product_id='point',history_regime='H-CURRENT',prediction=1.,actual=2.,fallback='none')]
        with self.assertRaisesRegex(ValueError,'budget'):
            evaluate(rows,{identity(q):dict(cohorts=['all','top10'])},'fixture',max_views=1)
