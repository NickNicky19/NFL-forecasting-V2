"""Bind B's local continuation and existing export sources; no scorer execution."""
import json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];B=ROOT/'reports/abc-championship';P=B/'local-week8-final-v1'
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def main():
 pointer=ROOT/'registries/CURRENT_RESULTS_INDEX.json';d=read(pointer);d['previous_checkpoint']=d['manifest'];d['manifest']='reports/abc-championship/results-index-v1/INDEX_MANIFEST.json';d['abc_B_adoption']={'path':'reports/abc-championship/ADOPTED_ASSIGNMENT_V2.json','sha256':sha(B/'ADOPTED_ASSIGNMENT_V2.json')};d['abc_status']='B_LOCAL_NOT_PINNED_NOT_C_ADMITTED';save(pointer,d)
 rows=read(P/'SIDE_TABLE.json');original=[r for r in rows if r['panel']=='B_LOCAL_W8_FIXED_ORIGINAL_SOURCE_FINAL_LABELS_V2'and r['strategy']=='original'];meta={r['method_key']:r for r in read(ROOT/'reports/week8-grading-20261102l/comparable-products-v3/SCORES.json')};leaders=read(P/'COMBINED_LEADERS.json')
 for r in leaders:r['recipe_binding']=meta.get(r['procedure_id'].rsplit(':',1)[-1],{'history_regime':'FIXED_DIRECTION_CONTROL','product_id':r['strategy']})
 save(P/'COMBINED_LEADERS_WITH_BINDINGS.json',leaders)
 def result(r,s):return f"{r[s+'_wins']}–{r[s+'_losses']}/{r[s+'_decided']} ({100*r[s+'_hit_rate']:.2f}%)"if r[s+'_decided']else'N/A'
 text='''# Session B local results and A/B/C export entrypoint

C owns the shared contract, scorer, admissions and consolidated report. B has adopted the direct user assignment through ADOPTED_ASSIGNMENT_V2.json; its exact hash is in EXPORT_INDEX.json. This normalized adoption record is not a byte-for-byte hash of the chat message. No C protocol has yet been pinned, so no common-championship parity is claimed.

New executed local result: all14 Week8 games final. Original selections205W/210L =205/415 (49.40%),12participation unknown,0pending. The old194/386 snapshot is preserved. Twenty-nine newly decided Monday selections add11wins/18losses; no prior-final original labels or grades changed. Fullboard661,427selected. Source quotes are provider-labelled, with unknown quote-update times and unverified book settlement/prices. No profit or EV claim.

The primary local comparison uses unchanged complete saved point-direction procedures, not MAE finalists. Common T90-compatible offers include13games and26passing offers, with Thursday's different horizon preserved separately. This wave regrades direction only; old numerical and probability products remain separate and are not claimed rescored. No new fit/inference/forecast.

|Category|OriginalOver W-L/n|OriginalUnder W-L/n|Combined W-L/n|Unknown|
|---|---|---|---|---:|
'''
 for r in original:text+=f"|{r['target']}|{result(r,'over')}|{result(r,'under')}|{result(r,'combined')}|{r['unknown']}|\n"
 text+='\nLocal combined maxima, with all ties retained as output views rather than independent learners:\n\n|Category|Procedure/history/output|Over|Under|Combined|Eligible/selected|\n|---|---|---|---|---|---|\n'
 for r in leaders:
  m=r['recipe_binding'];text+=f"|{r['target']}|{r['procedure_id']} / {m.get('history_regime')} / {m.get('product_id')}|{result(r,'over')}|{result(r,'under')}|{result(r,'combined')}|{r['eligible']}/{r['combined_selected']}|\n"
 text+='''
Chart-PPR and rushing-or-receiving anytimeTD have no compatible retained offered thresholds: N/A, not0% accuracy. All sides/coverage/unknowns/game counts/uncertainty are in [SIDE_TABLE.csv](local-week8-final-v1/SIDE_TABLE.csv). One exposed week is insufficient for independent week-cluster uncertainty; the existing game-bootstrap sensitivity is not multiplicity-adjusted. Sparse/technical failures remain in the full outer coverage infrastructure; no law is fabricated or treated as confidence abstention.

Independent raw-source review verified81,365grade rows,4,404side views and1,468side triads. On26matched offers the prior passing-yard numerical leader has P1 15/26, versus raw12/26/adjusted11/26/constant13/26. The completion leader has13/26, losing to raw14/26 and alwaysUnder17/26. These are selection results, not new MAE results or proof of current served improvement. Private rows are local-readback retained; approved offhost recovery remains pending.

Discovery scope: C canonical CURRENT_PROTOCOL.json and README returned404. Complete trees at main2d684f22, selected-reliability-v8 469e8dc8 and week8-results-v9 b6a95b13 were inspected; existing local C protocols were found but no ABC/common equivalent pointer. A's default EXPORT_INDEX also404. This bounded search does not establish future/global absence or delivery to A/C.

Next shared action: C publishes its existing canonical pointer or one explicit equivalent mapping, bound scorer/schema/roster/opportunity/outcome manifests and compliant admission route. B then verifies actual bytes, pins versions and independently checks matched cases. B's restricted archives remain protected; C's GitHub-only rule is not waived. Public aggregates cannot establish paired cross-session superiority. Where transfers are prohibited, B can assess owner-local scoring against C's exact opportunity manifest, with verification limits.

Period status: E1 remainsPARTIAL, not fullW1–8: originalW5–7covers42/43games; W8fixed local source now14final games; W1–4andoneW5game earlier-offer/original gaps remain. E2–E7 older numerical rolling evidence exists but exact-recipe/offer cells and common masks remain source-specific; no unmatched micro-pool or season-balanced winner is claimed. E8 genuine later captures remain separate. Existing18-mechanism roster and3205cell grid are referenced in the export index, not replaced by a new incompatible registry. Proposed/unimplemented pathways remain in the original sixty-pathway backlog.

Existing147strict-HGB/736olderD1D2 output-cell, scheduled-window and2021RECENT dependencies remain; large-fit recovery gate unchanged. Historical numerical testing does not require original picks or lines. Current recovery is not reverified or silently cleared by this run. No external messages, duplicate jobs, schedulers, wagers, merge or production changes. Existing owner provisional policy does not require an MAE win or a new universal waiting period; own operational/source/retention checks still apply. No admission or release recommendation is inferred from these exposed maxima.
'''
 (B/'README.md').write_text(text)
 save(B/'C_DISCOVERY_V1.json',dict(state='CANONICAL_CONTRACT_NOT_LOCATED',canonical_paths=['reports/abc-championship/CURRENT_PROTOCOL.json','reports/abc-championship/README.md'],HTTP=404,inspected_commits=['2d684f22830b817669ecf89f46eb6fdcace8335b','469e8dc8f6e7a8f2fb9db1e280631c68ff80e569','b6a95b133b3aec8d601b412e4d724f69d3353c2c'],trees_truncated=False,A_default_export_HTTP=404,scope='Bounded actual search; localCprotocols not automatically canonical.',next_action='C publish pointer/equivalent mapping and exact opportunity/scorer/admission contracts.',external_messages=0))
 start=ROOT/'START_HERE.md';start.write_text('**Session B A/B/C adoption and new local Week8 final-game results:** [entrypoint](reports/abc-championship/README.md). Original205/415 (49.40%),12unknown,14gamesfinal. C owns shared championship; no C contract/parity yet. Prior snapshots remain unchanged.\n\n'+start.read_text())
 with(ROOT/'TASK_LEDGER.md').open('a')as f:f.write('\n## ABC v2 November3 — B local continuation\nC owns commoncontract/scorer/admissions. B adoptionhash/exportindex; Ccanonicalpaths absentwithinexactrecordedsearch. NewlocalW8:14final,205W210L12unknownoriginal,29newdecidedMondaycases,allpriorfinaloriginalgradesunchanged.4404newsideviews,0newfits/inference. Independent81365row/1468triadcheckPASS. NotfullW1–8orCparity. Existing18mechanism/3205cellroster reused; alloldbudgets/failures/recovery gates/ownerjobs preserved. NextC publishboundcontract/opportunities, B verifiesbytes andownerlocaladmissionwhereprivate transfer prohibited. Externalmessages0.\n')
if __name__=='__main__':main()
