"""Read-only owner-local offer iterator/inventory; no grading or inference.

Import iter_offers for a root-owned adapter. CLI writes safe counts/hashes only;
it never exports retained lines/player records to public Git.
"""
import argparse,collections,gzip,hashlib,json
from pathlib import Path
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):
 body=p.read_bytes();return json.loads(gzip.decompress(body)if p.suffix=='.gz'else body)
def iter_offers(path,week):
 for row in read(path)['rows']:
  if row.get('target')not in('pass_cmp','pass_att'):continue
  if week==8 and not(row.get('panel')=='ORIGINAL_PROVIDER_T90'and row.get('strategy')=='original'and not row.get('method_key')):continue
  if row.get('season')!=2026 or int(row['week'])!=week:raise ValueError('Unexpected source season/week')
  if row.get('position')!='QB':raise ValueError('Separate non-QB population required')
  yield row
def identity(row):
 # Ordinals are deliberately excluded: same offer can have different indices
 # in source board, model packet and existing grading projections.
 return tuple(str(row[k])if k=='line'else row.get(k)for k in('game_id','player_id','target','line','line_from','source_head','source_server_clock'))
def main():
 ap=argparse.ArgumentParser()
 for week in range(5,9):ap.add_argument('--week'+str(week),type=Path,required=True)
 ap.add_argument('--derived-inputs',type=Path,required=True);ap.add_argument('--manifest-output',type=Path,required=True);a=ap.parse_args()
 new=read(a.derived_inputs);by={(r['game_id'],r['player_id']):r for r in new};assert len(by)==len(new)
 reports=[];allkeys=set();playergames=set();counts=collections.Counter()
 for week in range(5,9):
  path=getattr(a,'week'+str(week));rows=list(iter_offers(path,week));keys=[identity(r)for r in rows];assert len(keys)==len(set(keys))
  label=collections.Counter();missing_team=0
  for r,k in zip(rows,keys):
   assert r['player_id']and r['line']is not None
   allkeys.add((week,)+k);playergames.add((r['game_id'],r['player_id']))
   q=by.get((r['game_id'],r['player_id']))
   if q is None:label['NEW_QUERY_MISSING']+=1;continue
   field='official_completions'if r['target']=='pass_cmp'else'official_attempts'
   if r.get('actual')is None or not q.get('physical_participation'):label['UNRESOLVED_LABEL_SCOPE']+=1
   elif q[field]==r['actual']:label['EXACT_NUMERIC_LABEL_MATCH']+=1
   else:label['LABEL_REVISION_OR_CONTRACT_DIFFERENCE']+=1
   missing_team+=r.get('team')is None
  report=dict(week=week,source_id='B_RETAINED_2026_W'+str(week)+'_QB_OFFERS',source_bytes=path.stat().st_size,source_sha256=sha(path),
    records=len(rows),category_counts=dict(collections.Counter(r['target']for r in rows)),games=len({r['game_id']for r in rows}),
    label_states=dict(collections.Counter(r['label_state']for r in rows)),new_panel_label_join=dict(label),
    source_rows_without_team_field=missing_team,all_rows_have_source_server_clock=all(r.get('source_server_clock')for r in rows),
    offer_identity_sha256=hashlib.sha256(json.dumps(sorted(keys),separators=(',',':')).encode()).hexdigest(),
    scope='Inventory/label compatibility only, not new model timing admission or threshold scores.')
  reports.append(report);counts.update(label)
 result=dict(state='READ_ONLY_QB_OFFER_INVENTORY_AND_LABEL_JOIN',weeks=reports,
   unique_offers=len(allkeys),unique_player_games=len(playergames),new_panel_label_join=dict(counts),
   new_derived_input_sha256=sha(a.derived_inputs),
   no_quote_prices_assumed=True,point_or_probability_selection_not_computed=True,
   new_grades=0,model_calls=0,source_collections=0,restricted_row_exports=0,
   cutoff_rule='Root must separately qualify fit, transform, prior and consumed-feature eligibility at retained quote-decision t; target-time ages may qualify only under the existing known-target-time reconstruction contract. Do not pair an unqualified kickoff output with an earlier quote.',
   missing_periods='No W1-W4 offer evidence added. W5 covers14of15scheduledgames; W6/W7/W8 board source covers14games each. W8 fullboard is separate from old13game captured-method overlap.')
 if a.manifest_output.exists():raise FileExistsError(a.manifest_output)
 a.manifest_output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(state=result['state'],unique_offers=result['unique_offers'],label_join=dict(counts),manifest_sha256=sha(a.manifest_output))))
if __name__=='__main__':main()
