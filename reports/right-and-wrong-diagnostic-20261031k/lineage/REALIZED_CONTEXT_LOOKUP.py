"""Private in-memory descriptive target statistics; never forecast components.

No new NFL source, fit, inference, grading or outcome-dependent selection.
"""
import gzip,json,math,hashlib
from pathlib import Path

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_realized_context(private_root):
    admission=json.loads((HERE/'POSTGAME_CONTEXT_ADMISSION.json').read_text())
    values={}
    for parent in admission['source_bindings']:
        if sha(REPO/parent['receipt_path'])!=parent['receipt_sha256']:
            raise ValueError('qualified actual parent receipt changed')
        ref=parent['query_features'];file=Path(private_root)/'hgb-history-v1'/ref['name']
        if sha(file)!=ref['sha256']:raise ValueError('qualified actual query bytes changed')
        for row in json.loads(gzip.decompress(file.read_bytes())):
            q=row['query']
            if int(q['season'])!=2026 or int(q['week'])!=parent['week']or q['target']!=parent['target']:
                raise ValueError('target query identity mismatch')
            if q['population']!='primary' or q['position']!='QB':continue
            key=(int(q['week']),str(q['game_id']),str(q['player_id']))
            item=values.setdefault(key,{})
            if parent['target'] in item:raise ValueError('duplicate actual namespace')
            actual=q.get('actual');reason=None
            if actual is None:reason='QUALIFIED_PARENT_ACTUAL_MISSING'
            elif isinstance(actual,bool)or not isinstance(actual,(float,int))or not math.isfinite(actual):
                raise ValueError('nonfinite actual')
            elif parent['target']in('pass_att','pass_cmp')and(actual<0 or int(actual)!=actual):
                raise ValueError('invalid official count support')
            item[parent['target']]=dict(actual=actual,missing_reason=reason,source_query_sha256=ref['sha256'])
    result={}
    for key,parts in values.items():
        row={t:parts.get(t,dict(actual=None,missing_reason='NO_EXACT_QUALIFIED_TARGET_QUERY',source_query_sha256=None))for t in('pass_att','pass_cmp','pass_yd')}
        a,c,y=(row[t]['actual']for t in('pass_att','pass_cmp','pass_yd'))
        ratios={}
        for name,num,den in [('realized_completions_per_attempt',c,a),('realized_yards_per_attempt',y,a),('realized_yards_per_completion',y,c)]:
            reason='MISSING_QUALIFIED_COMPONENT'if num is None or den is None else'NONPOSITIVE_DENOMINATOR'if den<=0 else None
            ratios[name]=dict(value=None if reason else num/den,missing_reason=reason)
        result[key]=dict(actual_components=row,realized_ratios=ratios,
            evidence_role='POSTGAME_DESCRIPTIVE_ONLY_NEVER_PREGAME_INPUT_OR_COMPONENT_FORECAST',
            source_vintage='PARENT_CURRENT_VINTAGE_QUALIFIED_OFFICIAL_STAT_RECONSTRUCTION')
    return result


def context_for(row,lookup):
    key=(int(row['week']),str(row['game_id']),str(row['player_id']))
    if key in lookup:return lookup[key],None
    return None,'NO_EXACT_QUALIFIED_PLAYER_GAME_ACTUAL_CONTEXT'
