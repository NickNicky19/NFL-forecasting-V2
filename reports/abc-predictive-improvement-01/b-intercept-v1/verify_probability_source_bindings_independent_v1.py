"""Verify cached probability/ancillary-point bindings to retained producer rows."""
import argparse,gzip,hashlib,json,sys
from datetime import datetime
from pathlib import Path


def read(p):return json.loads(gzip.decompress(p.read_bytes())if p.suffix=='.gz'else p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def stamp(s):return datetime.fromisoformat(s.replace('Z','+00:00')).timestamp()

def run(repo,evidence,private,out):
    binding=read(out/'CURRENT_EXECUTION_BINDING.json');data=read(private/binding['inputs']);historical=0
    specs={5:('reports/baselines-coverage-20261031h/actual-method-w5/complete-leaf-law-v1','baselines-coverage-20261031h-w5-complete-leaf-law-v1'),6:('reports/completion-20261031g/roster/w6-complete-leaf-law-v1','completion-20261031g-w6-complete-leaf-law-v1'),7:('reports/completion-20261031g/roster/w7-complete-leaf-law-v1','completion-20261031g-w7-complete-leaf-law-v1')}
    for week,phase in[(5,'baseline_selection_rows'),(6,'calibration'),(7,'gate_oof')]:
        public,folder=specs[week];scores=read(repo/public/'SCORES.json');meta=next(s for s in scores if s['target']=='pass_td'and s.get('side')=='Combined'and s['procedure_id']=='v2-c02-explicit-lag-block-removal-leaf-cdf-v1:known-target-time-v1'and s['history_regime']=='H-MULTI');raw=read(evidence/folder/'GRADED_COMPLETE_LEAF_LAWS.json.gz')['graded'][meta['method_id']];byindex={str(r['source_row_index']):r for r in raw}
        for r in data['pass_td'][phase]:
            q=byindex[r['offer_id'].split(':',1)[1]]
            for k in('game_id','player_id','line','actual','probabilities','decision_time','kickoff','participation'):assert r[k]==q[k]
            historical+=1
    original=read(evidence/'week8-grading-20261102l/WEEK8_ORIGINAL_LAW_THRESHOLD_ROWS_V2.json.gz')['rows'];procedure='v2-c02-future-ordered-control-shadow-v1:c02_explicit_lag_block_removed:common-feature-memory';law={(r['game_id'],r['player_id'],float(r['line'])):r for r in original if r['target']=='pass_td'and r['procedure_id']==procedure and r['history_regime']=='H-MULTI'};final=[r for r in read(evidence/'abc-b-20261103/LOCAL_GRADED_ROWS.json.gz')['rows']if r.get('panel')=='ORIGINAL_PROVIDER_T90'and r.get('strategy')=='original'and r['target']=='pass_td'];actuals={(r['game_id'],r['player_id'],float(r['line'])):r for r in final}
    # Existing path/manifest helper supplies only already-approved local capture locations.
    # Every actual packet's bytes/hash and mean value are checked independently below.
    sys.path.insert(0,str(repo));from tools.grade_week8_captured_library import packet_specs
    mean={};sources=set()
    for spec in packet_specs(evidence/'week8-grading-20261102l',repo/'reports/week8-grading-20261102l'):
        if spec['capture_version']!='C02':continue
        p=spec['source_path'];assert sha(p)==spec['source_sha256'];sources.add(spec['source_sha256'])
        for r in read(p)['rows']:
            if r['target']=='pass_td'and r.get('product_id')=='mean'and r['procedure_id']==procedure and r['history_regime']=='H-MULTI':mean[r['game_id'],r['player_id'],spec['source_sha256']]=r['prediction']
    captured=0;missing=0
    for r in data['pass_td']['evaluation']:
        key=r['game_id'],r['player_id'],r['line'];q=actuals[key]
        for k in('actual','participation','decision_time','kickoff'):assert r[k]==q[k]
        old=law.get(key)
        if old is None:assert r['probabilities']is None and r['prediction']is None;missing+=1
        else:
            assert r['probabilities']==old['probabilities'];assert r['prediction']==mean[old['game_id'],old['player_id'],old['source_forecast_sha256']]
            assert stamp(old['forecast_issued_at'])<=r['decision_epoch']and stamp(old['forecast_persistence_at'])<=r['decision_epoch']<stamp(r['kickoff']);captured+=1
    assert historical==84 and captured==26 and missing==2
    result=dict(state='PASS_EXACT_RETAINED_PROBABILITY_AND_POINT_BINDINGS',input_sha256=binding['input_sha256'],historical_C02_rows_verified=84,historical_weeks=[5,6,7],original_Week8_C02_law_rows_verified=26,original_Week8_means_verified=26,original_capture_packet_hashes=sorted(sources),original_Week8_inference_and_persistence_before_decision_checks=26,missing_Thursday_capture_rows_preserved=2,Week8_current_final_label_joins_verified=28,no_model_inference_or_fitting=True,limits=['Historical known-target-time and original early captured query policies remain a declared transfer; matching retained bytes does not authenticate quote executability or historic source vintages.','Ancillary captured means are original B0 means, not means derived from repaired threshold products.'])
    (out/'INDEPENDENT_PROBABILITY_SOURCE_BINDINGS_V1.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('repo',type=Path);p.add_argument('evidence',type=Path);p.add_argument('private',type=Path);p.add_argument('out',type=Path);a=p.parse_args();run(a.repo,a.evidence,a.private,a.out)
