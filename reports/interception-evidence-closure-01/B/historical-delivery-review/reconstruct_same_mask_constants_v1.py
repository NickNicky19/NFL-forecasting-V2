"""Invert decided statistical crossings on an unchanged selected mask.

No raw NFL rows, model, grader or market-price/settlement assumption is used.
An exact same-line, no-push decided record suffices for constant-side arithmetic.
"""
import argparse
import hashlib
import json
from decimal import Decimal
from pathlib import Path


def reconstruct(name, sides, *, selected, unknown, pushes, dnp, period, key):
    ow, ol, on = [int(sides['over'][v]) for v in ('wins', 'losses', 'decided')]
    uw, ul, un = [int(sides['under'][v]) for v in ('wins', 'losses', 'decided')]
    assert ow + ol == on and uw + ul == un
    assert unknown == pushes == dnp == 0
    assert selected == on + un > 0
    n = on + un
    def record(w,l):
        return dict(wins=w,losses=l,decided=w+l,rate=float(Decimal(w)/Decimal(w+l)) if w+l else None)
    def constant(side):
        # If the candidate chose the opposite side, no-push correct/incorrect
        # outcomes invert. Same selected player/game/line mask is retained.
        wins, losses = (ow+ul, ol+uw) if side == 'over' else (uw+ol, ul+ow)
        candidate_only, control_only = (uw,ul) if side == 'over' else (ow,ol)
        own_sides = dict(over=record(wins,losses) if side=='over' else record(0,0),
                         under=record(wins,losses) if side=='under' else record(0,0))
        return dict(control='ALWAYS_'+side.upper(),own_sides=own_sides,combined=record(wins,losses),
                    candidate_only_wins=candidate_only,control_only_wins=control_only,
                    side_disagreements=candidate_only+control_only,
                    candidate_minus_control_wins=ow+uw-wins,
                    candidate_minus_control_rate=float(Decimal(ow+uw-wins)/Decimal(n)))
    return dict(procedure=name,procedure_key=key,period=period,
                mask='UNCHANGED_CANDIDATE_SELECTED_DECIDED_EXACT_LINE_CASES',selected=selected,
                unknown=unknown,pushes=pushes,DNP=dnp,
                candidate_own_sides={s:record(sides[s]['wins'],sides[s]['losses'])for s in ('over','under')},
                candidate_combined=record(ow+uw,ol+ul),controls=[constant('over'),constant('under')])


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--review-dir',type=Path,required=True)
    ap.add_argument('--source-cache',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();source=a.review_dir/'INDEPENDENT_METHOD_ARITHMETIC_V1.json'
    data=json.loads(source.read_text());annual=data['Top6_periods'][0]
    assert annual['period']=='ANNUAL_W1_5'
    c=annual['combined'];assert (c['wins'],c['losses'],c['decided'])==(23,7,30)
    rows=[reconstruct('BACKFIELD_CDF::FOOTBALL::P2_EXACT_LINE::TOP_6_PER_CATEGORY_WEEK',annual['own_sides'],
                      selected=30,unknown=c['unresolved'],pushes=c['push'],dnp=c['DNP'],
                      period=dict(season=2026,weeks=annual['weeks']),key='03987dde683658f5cabc4f4a0407b459e42e8f3861730ea3612e40bba53fc4f2')]
    for r in data['retained_CMP_records']:
        sides={s:{v:int(r[s+'_'+v])for v in ('wins','losses','decided')}for s in ('over','under')}
        assert int(r['eligible_or_opportunities'])==int(r['combined_decided'])==88
        assert int(r['abstain'])==int(r['unavailable'])==int(r['unknown'])==0
        assert int(r['combined_wins'])+int(r['combined_losses'])==88
        z=reconstruct(r['method']+'::'+r['output'],sides,selected=88,unknown=0,pushes=0,dnp=0,
                      period=dict(season=2026,weeks=[1,2,3,4,5]),key=r['key_sha256'])
        assert z['controls'][0]['combined']['wins']==int(r['always_over_own_decided'])==48
        assert z['controls'][1]['combined']['wins']==int(r['always_under_own_decided'])==40
        rows.append(z)
    contribution=a.source_cache/'reports/abc-championship/category-decision-release-01/A_CATEGORY_PRODUCT_CONTRIBUTION_V1.json'
    cmp=next(r for r in json.loads(contribution.read_text())['rows']if r['category']=='pass_cmp')
    pair=cmp['registered_learned_pairs'][0]
    assert pair['common_decided']==88 and pair['left_wins']==pair['right_wins']==52
    assert pair['side_disagreements']==8
    assert pair['decided_mask_sha256']==pair['numerical_mask_sha256']
    # On a common binary decided mask, equal wins and eight opposite choices
    # imply four unique wins each. Owner-reported mask/count premise retained.
    left_only=(pair['side_disagreements']+pair['left_wins']-pair['right_wins'])//2
    right_only=pair['side_disagreements']-left_only
    assert left_only==right_only==4
    result=dict(id='B-SAME-SELECTED-MASK-CONSTANT-ARITHMETIC-v1',
        state='PASS_EXACT_AGGREGATE_RECONSTRUCTION_NO_NFL_REGRADE',
        derivation='AlwaysOver W=OverW+UnderL; L=OverL+UnderW. AlwaysUnder W=UnderW+OverL; L=UnderL+OverW. Valid only on the identical decided exact-line mask with no pushes/unknowns.',
        premise='Bound owner aggregate counts and reported identical mask. This calculation independently verifies arithmetic, not private identities, raw outcomes or actual quote clocks.',
        records=rows,
        CatBoost_HGB_samecase=dict(left=pair['left'],right=pair['right'],decided=88,
            left_wins=52,right_wins=52,side_disagreements=8,left_only_wins=4,right_only_wins=4,
            mask_sha256=pair['decided_mask_sha256'],mask_membership_independently_obtained=False),
        new_fits=0,new_model_inference=0,new_picks=0,new_NFL_games_or_weeks=0,new_NFL_outcome_grades=0,
        allowed_claim='Statistical crossing diagnostic on frozen selected cases; useful same-mask constant controls are now known.',
        prohibited_claim='No invented opposite-side offered market, price, bookmaker settlement, wager, EV or primary qualification.',
        remaining_unknown=['Private selected-player/game/line membership and raw-label parity',
                           'Strong learned competitors on the same Backfield-selected30 cases',
                           'Game/week clustered paired uncertainty without case-to-cluster membership',
                           'Decision-time availability and original issuance'],
        supersedes_scope='Earlier not-verified same-selected30 strong-control-rows statement still applies to raw/learned controls. Constant-side arithmetic no longer unknown.',
        bindings=[dict(path=str(source.relative_to(a.review_dir)),sha256=hashlib.sha256(source.read_bytes()).hexdigest()),
                  dict(repository='NickNicky19/NFL-forecasting',ref='b7461fb7a79f89bec179b8c2e59f1b8e2e9ced31',
                       path='reports/abc-championship/category-decision-release-01/A_CATEGORY_PRODUCT_CONTRIBUTION_V1.json',
                       sha256=hashlib.sha256(contribution.read_bytes()).hexdigest())])
    a.out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'state':result['state'],'Backfield_candidate':23,'Backfield_same_mask_AlwaysUnder':21,
                      'Backfield_same_mask_AlwaysOver':9,'selected_decided':30,'new_NFL_periods':0}))


if __name__=='__main__':main()
