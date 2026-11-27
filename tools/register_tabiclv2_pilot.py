"""Register new pilot score views through existing index projection, no rescoring."""
import argparse,gzip,hashlib,json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools import register_targeted_m2 as existing
from tools import build_test_index_v3 as index
from nfl_v2.result_index import evaluation,validate_index
BASE=pathlib.Path('reports/predictive-value-next-01/B/execution-authorization-02');SOURCE=BASE/'evaluation-v1/SCORES.json';PROJECTION=BASE/'INDEX_PROJECTION_V1.json.gz'
def read(p):return json.loads(pathlib.Path(p).read_text())
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--execute',action='store_true');a=p.parse_args();raw=read(ROOT/SOURCE);rows=[]
 for r in raw:
  row=existing.canonical(r)
  if r.get('method')in('TABICLV2','LOGISTIC'):row['history_regime']='EXPANDING_EARLIER_2026_EXACT_OFFERS;ORIGINAL_2022_PLUS_FOOTBALL_HISTORY'+(';PINNED_SYNTHETIC_PRETRAINED_PRIOR'if r['method']=='TABICLV2'else';NO_PRETRAINING')
  row.update(source_vintage='CURRENT_VINTAGE7DAY_RECONSTRUCTION;BOOK_QUOTE_CLOCK_UNKNOWN;MAIN_ALT_UNCLASSIFIED;EXPOSED',primary_admission='SHADOW_RESEARCH_ONLY;THREE_SCORED_SYSTEM_WEEKS_ONE_LEARNED_WEEK;W8_W9_UNEXECUTED')
  validate_index([evaluation(row,str(SOURCE),year_record={k:row[k]for k in('evaluation_seasons','evaluation_weeks')})]);rows.append(row)
 if not a.execute:print(json.dumps({'state':'PREPARED_VALIDATED_NO_CANONICAL_MUTATION','records':len(rows)}));return
 proof=read(ROOT/BASE/'independent/GRADE_AND_SELECTION_CHECK_V1.json')
 if not proof['state'].startswith('PASS'):raise ValueError('Independent grading scope PASS required')
 ptr=ROOT/'registries/CURRENT_RESULTS_INDEX.json';old=read(ptr);regp=ROOT/'registries/RESULT_ARTIFACTS.json';reg=read(regp)
 if any(x['artifact']==str(SOURCE)for x in reg):raise ValueError('No duplicate registration')
 if (ROOT/PROJECTION).exists():raise FileExistsError(PROJECTION)
 (ROOT/PROJECTION).write_bytes(gzip.compress((json.dumps({'source_artifact':str(SOURCE),'source_artifact_sha256':sha(ROOT/SOURCE),'rows':rows},allow_nan=False)+'\n').encode(),mtime=0))
 reg.append({'artifact':str(SOURCE),'state':'SCORED','kind':'TABICLV2_DIRECT_COMPLETION_PARTIAL_PILOT_AND_FROZEN_SELECTION','targeted_m2_index_projection':str(PROJECTION),'version_note':'Existing index projection helper reused only; NOT M2 identity. New classifier/logisticW7 learned28 plusW5-6 B0reference56, W8-9technicalunavailability58 afterprequalityCPUprojectionstop. Samecase strongcontrols/propermetrics/own19selectors; no primaryactivation.'});regp.write_text(json.dumps(reg,indent=2)+'\n')
 index.new_records=existing.projected_records
 result=index.write(previous=old['manifest'],output=str(BASE/'results-index-v1'),reuse_prior_csv=True,compressed_delivery=True)
 manifest=ROOT/BASE/'results-index-v1/INDEX_MANIFEST.json';pointer=dict(old,manifest=str(manifest.relative_to(ROOT)),sha256=sha(manifest),record_count=result['records'],previous=old,latest_scope='TABICLV2_PARTIAL_W7_LEARNED_W5_6_REFERENCE_NO_PRIMARY')
 ptr.write_text(json.dumps(pointer,indent=2)+'\n');(ROOT/BASE/'REGISTRATION_RECEIPT_V1.json').write_text(json.dumps(result|{'source':str(SOURCE),'source_sha256':sha(ROOT/SOURCE),'independent_scope':str(BASE/'independent/GRADE_AND_SELECTION_CHECK_V1.json'),'new_NFL_observations':0,'source_views':len(raw),'no_rescoring':True},indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
