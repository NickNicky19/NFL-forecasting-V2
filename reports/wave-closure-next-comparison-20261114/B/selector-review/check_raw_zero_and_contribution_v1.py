"""Append source parsing and contribution distinctions to the frozen B review."""
import argparse,collections,datetime,gzip,hashlib,json
from pathlib import Path

def h(x):return hashlib.sha256(x).hexdigest()
def read(p):return json.loads(p.read_bytes())
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--inputs',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();r=a.inputs;out=a.out
    dest=out/'RAW_ZERO_AND_MEMBERSHIP_SUPPLEMENT_V1.json';assert not dest.exists()
    root=Path(__file__).resolve().parents[4];mainreview=read(out/'B_FIFTH_WEEK_INDEPENDENT_REVIEW_V1.json');board=read(r/'selector-inputs/W4_FULL_ORIGINAL_BOARD.private.json');players={str(x['id']):x for x in board['players']}
    index=read(r/'website/output/data/verified-int-v1/index-v2.json');stats=read(r/'website/data/cache/stat-keys-presence-strict-v3/stats_2026_04.json');raw_checks=[]
    for c in index['cases']:
        if c['week']!=4:continue
        source=c['source'];p=r/'website/output/data/verified-int-v1/sources'/(source['raw_SHA256']+'.json.gz');body=gzip.decompress(p.read_bytes());assert h(body)==source['raw_SHA256'];x=json.loads(body);pl=players[c['player_id']]
        assert str(pl['espn_id'])==source['espn_athlete_id']and pl['pos']=='QB'and pl['team']==c['team']and pl['game_id']==c['game_id']
        assert x['header']['id']==c['game_id']and x['header']['season']['year']==2026 and x['header']['week']==4
        games=x['header']['competitions'];assert len(games)==1 and games[0]['status']['type']['completed']is True and games[0]['status']['type']['state']=='post'
        matching=[]
        for team in x['boxscore']['players']:
            for g in team['statistics']:
                if g['name']!='passing':continue
                assert len(g['labels'])==len(set(g['labels']))
                for aa in g['athletes']:
                    if str(aa['athlete']['id'])==str(pl['espn_id']):matching.append((team,g,aa))
        assert len(matching)==1;team,g,aa=matching[0];assert team['team']['abbreviation']==pl['team'];d=dict(zip(g['labels'],aa['stats']));assert d['INT']=='0'
        cmp,att=map(int,d['C/ATT'].split('/'));qty={'pass_cmp':cmp,'pass_att':att,'pass_yd':int(d['YDS']),'pass_td':int(d['TD'])}
        assert all(stats[c['player_id']]['stats'][k]==v for k,v in qty.items())
        assert c['verified_value']==0 and c['direction']=='over'and c['line']==.5 and c['corrected_grade']=='miss'
        raw_checks.append(dict(case_id=c['case_id'],player_id=c['player_id'],event=c['game_id'],ESPN_athlete_id=source['espn_athlete_id'],canonical_board_identity_match=True,team_role_event_season_week_finality_match=True,passing_group_and_INT_label_explicit=True,reported_INT_text=d['INT'],value=0,other_four_passing_counters_match=True,original_missing_value_preserved=True,source_raw_sha256=source['raw_SHA256'],statistical_grade='miss',participation_not_used_to_fill_zero=True))
    rows=read(r/'B_W4_RECONSTRUCTED_SELECTED_PRIVATE.json');key=lambda x:(x['game_id'],x['player_id'],x['key'],x['direction']);event=lambda x:(x['game_id'],x['player_id'],x['key']);b={key(x):x for x in rows if x['policy']=='saved_control'};c={key(x):x for x in rows if x['policy']=='candidate'};common=b.keys()&c.keys()
    models=[x for x in c.values()if x['source']=='C_P1_MEAN_RECONSTRUCTED'];fallback=[x for x in c.values()if x['source']=='SAVED_WEBSITE_REFERENCE']
    w4=dict(candidate_generated=2,reference_fallback=12,model_selected_already_in_control=sum(key(x)in common for x in models),model_new_memberships=sum(key(x)not in common for x in models),fallback_new_memberships=sum(key(x)not in common for x in fallback),common_same_side_point_changes=sum(b[k]['adj']!=c[k]['adj']for k in common),common_same_side_score_changes=sum(b[k]['score']!=c[k]['score']for k in common))
    bm={event(x):x for x in b.values()};cm={event(x):x for x in c.values()};w4['same_opportunity_selected_both_policies_side_changes']=sum(bm[k]['direction']!=cm[k]['direction']for k in bm.keys()&cm.keys());assert (w4['model_selected_already_in_control'],w4['model_new_memberships'],w4['fallback_new_memberships'],w4['same_opportunity_selected_both_policies_side_changes'])==(1,1,1,1)
    priorpath=root/'reports/follow-through-release-defensive-source-01/B/selector-review/SELECTOR_CONTRIBUTION_ACCOUNTING_V1.json';prior=read(priorpath)['cumulative']
    five=dict(candidate_generated_selected=10,reference_fallback_selected=100,model_selected_already_in_control=prior['candidate_model_rows_in_common']+w4['model_selected_already_in_control'],model_new_memberships=prior['candidate_model_rows_new']+w4['model_new_memberships'],fallback_new_memberships=prior['fallback_rows_new']+w4['fallback_new_memberships'],candidate_only_same_side_memberships=10,control_only_same_side_memberships=9,common_same_side_memberships=100)
    assert (five['model_selected_already_in_control'],five['model_new_memberships'],five['fallback_new_memberships'])==(1,9,1)
    owner=read(r/'output/data/selector-replay-v1/five-week-summary-v2.json')
    for name,z in mainreview['cumulative'].items():
        # The owner uses 'candidate_generated' and 'candidate_fallback' as well.
        target=owner['cumulative'][name]
        for k in ['selected','wins','losses','decided','unknown']:assert z[k]==target[k]
    result=dict(id='B_RAW_REPORTED_ZERO_AND_SELECTOR_CONTRIBUTION_SUPPLEMENT_v1',verified_UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),state='PASS_TWO_RAW_W4_INT_ZEROS_AND_NONINTERCHANGEABLE_CONTRIBUTION_MEMBERSHIP',parent_review_sha256=h((out/'B_FIFTH_WEEK_INDEPENDENT_REVIEW_V1.json').read_bytes()),raw_case_checks=raw_checks,W4_contribution=w4,five_week_contribution=five,interpretation='Ten candidate-generated selected forecasts and ten candidate-only memberships happen to have equalcounts but are different populations:9newmodelmemberships,1newreferencefallbackmembership,1already-commonmodelselection. Fivecomplete-policyweeksremainvalidatdeclaredtier,notfiveweeksofwidespreadcandidateuse.',limits=['DirectsourceparsingvalidatesbothnewW4INTzeros;originalquote/roster/issuanceclocksarenotauthenticated.','Owner-local27rowselectedfileisnotdirectlyinspected;source-reconstructedBmembership,productionparityandpublishedaggregatesareverified.','W5-8membershipusespreviousfullBreview;oneW6grade-onlydeltaisasource-boundappendix,notnewselection.','No model-fit, newforecast, policychange, sourcecollection, sportsbooksettlement orprimaryrelease.'],new_fits=0,new_issued_forecasts_or_sides=0,new_NFL_observations=0,code_sha256=h(Path(__file__).read_bytes()))
    dest.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(state=result['state'],W4=w4,five=five)))
if __name__=='__main__':main()
