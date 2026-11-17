"""Transport-only scoring wrapper: paired aggregates are gzip from first write.

Reuses the exact frozen scorer/grade/selection functions, models and protocol.
Keeps the8MiB output cap. No prediction/grade or comparison policy changes.
The executed original v1 failure and lossless repaired outputs remain retained;
this wrapper is provided for clean later reproduction, not rerun in this wave.
"""
import hashlib,importlib.util,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'tools/score_qb_pass_mix_information.py'
FROZEN_SHA='40266e58b2a678ab03679e426b1c68c6b35daa3dc58725991ecbd3342935eb7f'

def install_transport(module):
    original_load=module.load_evaluator
    def load():
        ev,design=original_load();original_write=ev.write
        def write(path,body):
            p=Path(path)
            if p.name=='PAIRED_COMPARISONS_V1.json':p=p.with_suffix('.json.gz')
            return original_write(p,body)
        ev.write=write
        return ev,design
    module.load_evaluator=load

if __name__=='__main__':
    if hashlib.sha256(SOURCE.read_bytes()).hexdigest()!=FROZEN_SHA:
        raise ValueError('Frozen scoring source changed; no silent transport upgrade')
    sys.path.insert(0,str(ROOT))
    spec=importlib.util.spec_from_file_location('SKILL_FROZEN_SCORE_TRANSPORT',SOURCE)
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    install_transport(module)
    from threadpoolctl import threadpool_limits
    with threadpool_limits(limits=2):module.main()
