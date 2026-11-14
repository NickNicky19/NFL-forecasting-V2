import ast,unittest
from pathlib import Path
from unittest.mock import patch
from nfl_v2 import seasonal_rolling_v2 as base,seasonal_rolling_continuation as cont
class ContinuationTests(unittest.TestCase):
 def test_same_scientific_contract(self):
  for year in (2022,2023,2024,2025):self.assertEqual(base.policies(year),cont.policies(year))
  self.assertEqual(base.TARGETS,cont.TARGETS)
  for target in base.TARGETS:
   self.assertEqual(base.methods(target),cont.methods(target))
   for method in base.methods(target):self.assertEqual(base.products(method,target),cont.products(method,target))
 def test_broken_progress_does_not_raise(self):
  tree=ast.parse(Path(cont.__file__).read_text());nodes=[n for n in ast.walk(tree) if isinstance(n,ast.Try) and any(isinstance(h.type,ast.Name) and h.type.id=='BrokenPipeError' for h in n.handlers)]
  self.assertEqual(len(nodes),1)
  code=compile(ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[])),'progress-fixture','exec')
  import json,time
  with patch('builtins.print',side_effect=BrokenPipeError):exec(code,dict(json=json,time=time,year=2023,week=17,fitcalls=0,retained=0,output_count=0,start=time.monotonic()))
if __name__=='__main__':unittest.main()
