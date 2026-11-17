"""Independent arithmetic and exact early-panel reuse, without A private rows.

FTN-dependent public aggregate derivatives: CC-BY-SA-4.0, FTN Data via
nflverse. This checks published totals, not private row or fit parity.
"""
import argparse,csv,gzip,hashlib,json,math
from datetime import datetime,timezone
from pathlib import Path

EXPECTED='fcd9d4c0fe6181dc5ebe5119031460615e57f3bbbb04a968b0139098e8970ad0'

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--old-export-root',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();body=a.source.read_bytes();assert hashlib.sha256(body).hexdigest()==EXPECTED
    x=json.loads(gzip.decompress(body));checks=0
    def ck(v):
        nonlocal checks
        assert v
        checks+=1
    groups={}
    for r in x['summaries']:
        for side in ['OVER','UNDER','COMBINED']:
            z=r[side];n=z['decided']
            if n:
                ck(z['wins']+z['losses']==n);ck(abs(z['rate']-z['wins']/n)<1e-14)
            else:ck(z['wins']is None and z['losses']is None and z['rate']is None)
        ck(r['COMBINED']['decided']==r['OVER']['decided']+r['UNDER']['decided'])
        ck(r['COMBINED']['selected']==r['OVER']['selected']+r['UNDER']['selected'])
        if r['COMBINED']['decided']:
            ck(r['COMBINED']['wins']==sum(r[s]['wins']or 0 for s in ['OVER','UNDER']))
        groups[r['candidate_id'],r['view'],r['week_view']]=r
    for cid in x['candidate_ids']:
        for view in ['FULL_A_EARLY_BOARD','COMMON_ALL_THREE_B_ARMS','QUALIFIED_TEAM_ALIAS_SUBGROUP']:
            total=groups[cid,view,'ALL'];weekly=[groups[cid,view,w]for w in range(1,5)]
            for side in ['OVER','UNDER','COMBINED']:
                for key in ['selected','decided','wins','losses']:
                    ck((total[side][key]or 0)==sum(r[side][key]or 0 for r in weekly))
            for key in ['eligible','unavailable','abstentions','player_games']:
                ck(total[key]==sum(r[key]for r in weekly))
            n=total['numerical']['scored']
            if n:
                for key in ['MAE','MSE','bias']:
                    ck(abs(total['numerical'][key]-sum(r['numerical'][key]*r['numerical']['scored']for r in weekly)/n)<1e-11)
            events=total['probability']['events']
            if events:
                for key in ['Brier','three_state_log_loss']:
                    ck(abs(total['probability'][key]-sum(r['probability'][key]*r['probability']['events']for r in weekly)/events)<1e-12)
            for week in range(5,10):
                r=groups[cid,view,week];ck(r['eligible']==0 and r['COMBINED']['decided']==0)
    paired_checked=0
    for r in x['paired']:
        left=groups[r['left'],r['view'],'ALL'];right=groups[r['right'],r['view'],'ALL'];n=r['common_decided']
        if n:
            ck(r['left_wins']==left['COMBINED']['wins']);ck(r['right_wins']==right['COMBINED']['wins'])
            ck(abs(r['accuracy_change']-(r['left_wins']-r['right_wins'])/n)<1e-14)
            ck(abs(r['left_wins']-r['right_wins'])<=r['side_disagreements']<=n)
        if r['common_numerical']:
            ck(abs(r['MAE_change']-(left['numerical']['MAE']-right['numerical']['MAE']))<1e-11)
        if r['common_law_events']:
            ck(abs(r['Brier_change']-(left['probability']['Brier']-right['probability']['Brier']))<1e-12)
        paired_checked+=1
    old=[];old_files=[]
    for path in sorted(a.old_export_root.glob('ANNUAL_ACTUAL_W1_W5_*.csv')):
        raw=path.read_bytes();old_files.append(dict(name=path.name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
        old+=list(csv.DictReader(raw.decode().splitlines()))
    om={(r['candidate_id'],int(r['week_view'])):r for r in old if r['view']=='FULL_A_BOARD'and r['week_view']in ['1','2','3','4']}
    reuse=[]
    for (cid,view,week),r in groups.items():
        if view!='FULL_A_EARLY_BOARD'or week not in [1,2,3,4]:continue
        prior=cid
        if cid.startswith('B-FTN'):
            if ':B0::'in cid or ':B1::'in cid:prior='B-QB-OPPORTUNITY-PROFILE-INCREMENT-v1:R3::'+cid.split('::')[-1]
            else:continue
        z=om.get((prior,week))
        if z is None:continue
        ck(r['eligible_mask_sha256']==z['eligible_mask_sha256']);ck(r['eligible']==int(z['eligible']));ck(r['games']==int(z['games']))
        for side in ['over','under','combined']:
            p=r[side.upper()];n=int(z[side+'_decided'])
            ck(p['decided']==n)
            if n:
                ck(p['wins']==int(z[side+'_wins'])and p['losses']==int(z[side+'_losses']))
            else:ck(p['wins']is None and p['losses']is None and z[side+'_wins']==''and z[side+'_losses']=='')
        reuse.append(dict(candidate=cid,prior_candidate=prior,week=week,mask_sha256=r['eligible_mask_sha256'],own_side_totals_match=True))
    ck(len(reuse)==64)
    eligible=[r for r in x['summaries']if r['view']=='FULL_A_EARLY_BOARD'and r['week_view']in ['ALL',1,2,3,4]]
    out=dict(id='B_A84_PUBLIC_RECEIPT_AND_EARLY_SOURCE_REUSE_VERIFICATION_v1',verified_UTC=datetime.now(timezone.utc).isoformat(),state='PASS_PUBLIC_AGGREGATE_ARITHMETIC_AND_BOUND_WEEKLY_SOURCE_REUSE',source_sha256=EXPECTED,source_commit='5a41d2bac6027e0ac1b5a2744d52f8ec5e93c47e',checks=checks,summary_cells_checked=len(x['summaries']),paired_arithmetic_cells_checked=paired_checked,candidate_count=19,offers=84,games=48,actual_weeks=[1,2,3,4],new_fits=0,new_inference=0,new_original_picks=0,source_week_inventory=x['A_early_source_inventory'],A_procedure_provenance=x['A_product_provenance'],A_source_bindings=x['A_source_bindings'],private_membership_commitments={k:x[k]for k in ['full_A_mask_sha256','common_B_mask_sha256','membership_sha256','strict_team_text_common_mask_sha256']},private_vectors_commitment=x['private_vectors'],old_weekly_files=old_files,old_exact_weekly_reuse_checks=reuse,older_B_weekly_available=sorted({cid for cid,w in om if cid.startswith('B-')}),old_early_masks={str(w):next(r['eligible_mask_sha256']for r in x['summaries']if r['view']=='FULL_A_EARLY_BOARD'and r['week_view']==w)for w in range(1,5)},records=eligible,limits=['Independent verification of public arithmetic and source/mask/procedure commitments, not protected private rows, raw FTN, model fitting, bootstrap reproduction or original publication clocks.','A fallback flags are blank/unspecified for retained controls; do not relabel as learned-only.','A earlier and later source evidence are not yet newly combined by this verification. Root must freeze the source/roster policy first.','64 old/new checks include exact B1 aliases, not64 independent experiments.','Existing48 R0-R3 early weekly output cells can be reused; target/recipe aliases require exact owner binding.','Over-event AUC/reliability across sources require raw compatible rank/bin information; do not average sourceAUCs.'],code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    if a.out.exists():raise FileExistsError(a.out)
    a.out.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items()if k in ['state','checks','offers','games','summary_cells_checked','paired_arithmetic_cells_checked']}))

if __name__=='__main__':main()
