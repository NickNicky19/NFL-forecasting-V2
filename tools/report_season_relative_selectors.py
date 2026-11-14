"""Report immutable season-relative selector evaluations without new scoring."""
import csv,hashlib,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'reports/completion-20261031g/season-selector';F=ROOT/'reports/championship-20261030f/category-selector-v2'
POLICIES=('FROZEN_PRIOR_SEASON_BEST','EARLIER_AVAILABLE_CURRENT_SCORE_MEMORY','POOLED_PRIOR_AND_AVAILABLE_CURRENT_MEMORY')
def main():
 rows=[];sources=[]
 for year,name in [(2023,'2023'),(2024,'2024-resume-v2'),(2025,'2025'),(2026,None)]:
  base=OUT/name if name else F;p=base/'SCORES.json';source=json.loads(p.read_text());sources.append(dict(path=p.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
  for r in source:
   old=r['procedure_id'].split(':')[-1];policy={'FROZEN_2025_BEST':POLICIES[0],'EARLIER_AVAILABLE_2026_SCORE_MEMORY':POLICIES[1],'POOLED_2025_AND_AVAILABLE_2026_MEMORY':POLICIES[2]}.get(old,old);metric='brier'if r['target']=='anytime_td'else'mae'
   rows.append(dict(season=year,target=r['target'],policy=policy,n=r['n'],native_loss=r[metric],metric=metric,forecast_rows=r['forecast_rows'],fallback_rows=r['fallback_rows'],weeks=r['evaluation_weeks'],unique_games=r['unique_games'],source=str(p.relative_to(ROOT)),source_record_id=r['record_id'],source_vintage=r['source_vintage']))
 flat=[];lines=['# Earlier-only category selection across seasons','','The registered v2 policy algorithm now has full18-week evaluations in2023,2024and2025, alongside the preserved2026W1–7 replay. All120candidate output recipes share exact query/support/label-value checks in every evaluated week. The generic season-relative choice function reproduces all252previously frozen2026assignments; existing2026scores were not regraded. These are120output recipes across11mechanisms, not120independent learners.','','Current score memory selects among historically trained H-MULTI forecasts; it is not a strict-current-football-information model. Training, feature and label vintages remain current/revised source reconstructions under the registered seven-day rule. Each week’s complete scores qualify only after its LAST scheduled game kickoff+7days is strictly before the next fitting origin. All seasons were previously exposed research.','','| Season | Current-memory wins / losses / ties versus frozen prior | Current carry MAE | Frozen-prior carry MAE |','|---|---|---:|---:|']
 for year in(2023,2024,2025,2026):
  rr=[r for r in rows if r['season']==year];wins=losses=ties=0
  for target in sorted({r['target']for r in rr}):
   by={r['policy']:r for r in rr if r['target']==target};base=by[POLICIES[0]]['native_loss'];cur=by[POLICIES[1]]['native_loss'];pooled=by[POLICIES[2]]['native_loss'];wins+=cur<base-1e-12;losses+=cur>base+1e-12;ties+=abs(cur-base)<=1e-12
   flat.append(dict(season=year,target=target,n=by[POLICIES[0]]['n'],metric=by[POLICIES[0]]['metric'],frozen_prior=base,current_memory=cur,current_delta=cur-base,pooled_memory=pooled,pooled_delta=pooled-base))
  carry=next(r for r in flat if r['season']==year and r['target']=='rush_att');lines.append(f"| {year} | {wins} / {losses} / {ties} | {carry['current_memory']:.6f} | {carry['frozen_prior']:.6f} |")
 lines+=['','The current carry-selector advantage reverses in2025 and2024. In2023 it wins substantially against the frozen2022 choice; the expanding-from2022 startup of that prior score panel is part of this result. No pre2022training is introduced. The2022full frozen-prior policy has no registered2021score panel and remains not applicable under this exact complete-prior-roster rule; source2021statistics alone would not manufacture original2021forecasts.','','| Season | Category | n | Frozen prior | Current memory | Delta | Pooled memory | Delta |','|---|---|---:|---:|---:|---:|---:|---:|']
 for r in flat:lines.append(f"| {r['season']} | {r['target']} | {r['n']} | {r['frozen_prior']:.6f} | {r['current_memory']:.6f} | {r['current_delta']:+.6f} | {r['pooled_memory']:.6f} | {r['pooled_delta']:+.6f} |")
 lines+=['','Each older-year directory retains the frozen roster,648choices,4320exact-mask comparisons,36native-score views and paired whole-week bootstrap intervals. Current2026has seven week clusters and retains its insufficient-cluster flag. Full-system fallback contributions stay visible; no new joint common-learned policy claim is inferred from separate per-method fallback rates.','','Micro averages below sum n×loss over exactly2023,2024,2025 and divide by their summed n; season-balanced values equally weight those three complete seasons. Current2026W1–7 is never pooled into them. These descriptive aggregates are not new independent NFL observations.','']
 aggregate=[]
 for target in sorted({r['target']for r in rows}):
  for policy in POLICIES:
   rr=[r for r in rows if r['season']in(2023,2024,2025)and r['target']==target and r['policy']==policy];n=sum(r['n']for r in rr);aggregate.append(dict(target=target,policy=policy,seasons=[2023,2024,2025],n=n,pooled_micro=math.fsum(r['n']*r['native_loss']for r in rr)/n,season_balanced=math.fsum(r['native_loss']for r in rr)/3,current2026_separate=next(r['native_loss']for r in rows if r['season']==2026 and r['target']==target and r['policy']==policy)))
 for name,data in [('ALL_SEASON_POLICY_RESULTS',rows),('POLICY_SEASON_COMPARISON',flat),('COMPLETE_SEASON_AGGREGATES',aggregate)]:
  (OUT/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')
  with(OUT/(name+'.csv')).open('w',newline='')as f:
   w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows({k:json.dumps(v)if isinstance(v,(dict,list))else v for k,v in r.items()}for r in data)
 (OUT/'README.md').write_text('\n'.join(lines)+'\n');(OUT/'SUMMARY_RECEIPT.json').write_text(json.dumps(dict(state='COMPLETE_SOURCE_BOUND_REPORT_NO_NEW_SCORES',new_full_season_evaluations=[2023,2024,2025],new_score_views=108,source_scores=sources,unchanged2026=True,new_fits=0,new_inference=0),indent=2)+'\n')
 print(json.dumps(dict(season_policy_rows=len(rows),new_score_views=108,new_fits=0)))
if __name__=='__main__':main()
