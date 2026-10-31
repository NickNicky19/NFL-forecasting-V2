"""Current W1–4/W5–7 readables from sealed retained-score aggregates."""
import argparse,collections,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2.shared_subgroups import sha,now,write
from tools.numerical_championship import proc_id,product_id,csvwrite


def main(a):
    out=a.output.resolve();scores=json.loads((out/'SCORES.json').read_bytes());by=collections.defaultdict(list)
    for i,r in enumerate(scores):
        if r['fallback_view']=='FULL_SYSTEM':by[r['target'],r['history_regime'],r['window_id']].append((i,r))
    wide=[];periods=('W1_W4_STARTUP','W5_W7_LATER')
    for target in sorted({r['target'] for r in scores}):
        product='event_probability' if target=='anytime_td' else 'lower_median';metric='brier' if target=='anytime_td' else 'mae';row=dict(season=2026,target=target,metric=metric,exemplar='Fixed existing Leaf-CDF control, not a new startup winner',source_score_artifact=(out/'SCORES.json').relative_to(a.root).as_posix(),source_score_sha256=sha(out/'SCORES.json'))
        for arm in('H-CURRENT','H-RECENT','H-MULTI'):
            for window in periods:
                choices=by[target,arm,window];i,r=next(x for x in choices if x[1]['procedure_id'].endswith(':ordered_leaf_cdf') and x[1]['product_id']==product);prefix=arm+'_'+window
                for field,value in dict(procedure_id=r['procedure_id'],product_id=product,n=r['n'],forecast_rows=r['forecast_rows'],error=r[metric],bias=r['bias'],fallback_rows=r['fallback_rows'],fallback_rate=r['fallback_rate'],record_id=r['record_id'],source_row_index=i).items():row[prefix+'_'+field]=value
                baseline=next((b for _,b in choices if b['procedure_id']=='empirical-player-history-control-v1' and b['product_id']==product),None)
                if baseline:
                    match=r['n']==baseline['n'] and r['membership_sha256']==baseline['membership_sha256'];be=baseline[metric];row[prefix+'_empirical_error']=be;row[prefix+'_empirical_record_id']=baseline['record_id'];row[prefix+'_baseline_full_mask_match']=match;row[prefix+'_baseline_relative_skill']=1-r[metric]/be if match and be not in(None,0) else None
        for window in periods:
            i,r=next(x for x in by[target,'H-CURRENT',window] if x[1]['procedure_id'].endswith(':ordered_leaf_cdf:strict-current-inputs') and x[1]['product_id']==product)
            for field,value in dict(procedure_id=r['procedure_id'],n=r['n'],forecast_rows=r['forecast_rows'],error=r[metric],fallback_rows=r['fallback_rows'],record_id=r['record_id']).items():row['STRICT_CURRENT_'+window+'_'+field]=value
        wide.append(row)
    write(out/'LEAF_STARTUP_COMPARISON.json',wide);csvwrite(out/'LEAF_STARTUP_COMPARISON.csv',wide)
    lines=['# Fixed2026W1–7: numerical startup and later-week comparison','','The missing startup aggregation is now executed for**620valid fixed recipe/history/output cells plus36previously frozen category-selection policy outputs**. All656original full-period n/issued/MAE/MSE/bias checks pass;21original strict-HGBrecipe/output cells(147origins)remain unrun. These are new W1–4andW5–7views of existing forecasts, not new fits or backtests. Historical offer/selection gaps do not block this numerical product.','','| Category | CURRENT W1–4 | RECENT W1–4 | MULTI W1–4 | CURRENT W5–7 | RECENT W5–7 | MULTI W5–7 | Strict-current early / later |','|---|---|---|---|---|---|---|---|']
    for r in wide:
        vals=[]
        for window in periods:
            for arm in('H-CURRENT','H-RECENT','H-MULTI'):
                pre=arm+'_'+window;vals.append(f"{r[pre+'_error']:.6f}; n={r[pre+'_n']}; fallback={r[pre+'_fallback_rows']}/{r[pre+'_forecast_rows']}")
        lines.append('| '+r['target']+' | '+' | '.join(vals)+f" | {r['STRICT_CURRENT_W1_W4_STARTUP_error']:.6f} / {r['STRICT_CURRENT_W5_W7_LATER_error']:.6f} |")
    lines += ['', 'The fixed Leaf exemplar reports native MAE, except anytime-TD Brier. Its exact procedure, empirical same-history reference, exact full-system mask match and baseline-relative skill are in the machine table; it is not a selected winner. Mean/median views share learners. Partial chart labels remain qualified research, not a complete rare-event or website-fantasy contract.', '', 'Passing yards illustrates the same2026target games: CURRENT Leaf MAE107.191781inW1–4(n146,114/146issued fallbacks)versusMULTI67.061644(5/146fallbacks). W5–7is68.104167versus66.333333(n96,onefallback each). Completions CURRENT10.952055→5.562500versusMULTI5.383562→5.562500. Anytime-TD CURRENT Brier0.174400→0.149063versusMULTI0.144586→0.144963. These full-system differences include startup behavior; they do not isolate a common-learned history effect.', '', 'CURRENT fitting with older feature memory, RECENT, MULTI and strict-current information retain their original meanings. Own LEARNED_ONLY/FALLBACK_ONLY views are disjoint partitions, not matched learned populations across histories. Existing checkpointD common-history-mask results remain byreference. Selector partitions describe the underlying forecast model’s fallback, not whether its earlier score memory was empty; the252original decisions were copied, never recomputed or chosen from these startup results.', '', 'The full fixed panel remains107regular-season games and the original2026W1–7target. W5–7is not an18-week historical window. No2026Week8label was fetched, converted or graded; no forecast was regenerated. Exact source/outcome masks, games/players, precision and max errors are retained. P90/P95were not recomputed; weekly quantiles cannot be pooled.', '', '**Precision scope:** the3chart-selector outputs require a narrow versioned precision correction because their destination policy product bypassed exact underlying median-grid tolerance handling. Native MAE/MSE/bias/n conclusions remain valid. Use the root’s source-bound precision correction/default index when available; do not interpret this as a changed forecast or predictive gain.', '', '[Every startup/origin view](STARTUP_NUMERICAL_RESULTS.csv) · [Canonical original scoring version](SCORES.json) · [Frozen source/620+36roster and decisions](FROZEN_PROTOCOL.json) · [656full-period parity checks/resource receipt](RUN_RECEIPT.json).']
    (out/'README.md').write_text('\n'.join(lines)+'\n')
    older=out.parent/'v1';oldinventory=older/'CURRENT_STARTUP_COVERAGE_INVENTORY.json';old=json.loads(oldinventory.read_bytes());new=[];lookup=collections.defaultdict(list)
    for i,r in enumerate(scores):lookup[r['target'],r['procedure_id'],r['history_regime'],r['product_id']].append(dict(source_row_index=i,record_id=r['record_id'],window_id=r['window_id'],fallback_view=r['fallback_view']))
    for r in old:
        k=(r['target'],proc_id(r['procedure_id']),r['history_regime'],product_id(r['product_id']));updated=dict(r)
        if r['current_fullperiod_state']=='COMPLETED_VALID':
            if len(lookup[k])!=6:raise ValueError('current inventory does not map to six completed startup views')
            updated.update(current_startup_state='COMPLETED_VALID_SAVED_ROW_AGGREGATION',startup_source_artifact=(out/'SCORES.json').relative_to(a.root).as_posix(),startup_source_sha256=sha(out/'SCORES.json'),startup_score_rows=lookup[k],next_action='Use source-bound current numerical startup views; own learned/fallback semantics and chart-selector precision correction remain explicit')
        new.append(updated)
    write(older/'CURRENT_STARTUP_COVERAGE_INVENTORY_V2.json',new);csvwrite(older/'CURRENT_STARTUP_COVERAGE_INVENTORY_V2.csv',new)
    readme=older/'README.md';(older/'README_BEFORE_CURRENT_STARTUP_COMPLETION.md').write_bytes(readme.read_bytes());text=readme.read_text();text=text.replace('Exact current W1–4/W5–7startup aggregation remains replayable where rows exist; this older-season checkpoint does not claim to have executed it.','A separate current-year adapter now completes W1–4/W5–7 aggregation for620fixed recipes plus36frozen policies, with all656full-period native parity checks passing. The21strict-HGBoutput cells remain unrun. [Current twelve-category results](../current-2026-v2/README.md).');text=text.replace('(CURRENT_STARTUP_COVERAGE_INVENTORY.csv)','(CURRENT_STARTUP_COVERAGE_INVENTORY_V2.csv)');readme.write_text(text)
    write(out/'REPORT_RECEIPT.json',dict(at=now(),code_sha256=sha(__file__),source_score_sha256=sha(out/'SCORES.json'),category_summary_rows=len(wide),updated_current_inventory_rows=len(new),completed_current_cells=sum(r['current_startup_state']=='COMPLETED_VALID_SAVED_ROW_AGGREGATION' for r in new),preserved_FIT_REQUIRED_cells=sum(r['current_startup_state']=='FIT_REQUIRED' for r in new),new_scores=0,new_fits=0,new_inference=0))
    print(json.dumps(dict(current_summary_rows=len(wide),completed_inventory_cells=sum(r['current_startup_state']=='COMPLETED_VALID_SAVED_ROW_AGGREGATION' for r in new),still_fit_required=sum(r['current_startup_state']=='FIT_REQUIRED' for r in new))))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--output',type=Path,required=True);main(p.parse_args())
