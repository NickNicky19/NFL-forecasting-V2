"""Lexical metadata projection: unknown scalar values are never decoded."""
import collections,gzip,hashlib,json,math
from datetime import datetime,timezone
from pathlib import Path
MISSING=object()
ALLOWED={'captured_at','forecast_generated_at','code_commit','engine_sha256','schema_version','payload_sha256','season','week','game_id','player_id','category','position','kickoff','lean','line','line_from','price','probability','source_timestamps_verified','top_over','top_under','over','under'}
FORBIDDEN_CONTAINERS={'actual','actuals','outcome','outcomes','labels','stats','statistics','results','st','finals'}
class Project:
 def __init__(self,s):self.s=s;self.i=0;self.skipped=0
 def ws(self):
  while self.i<len(self.s)and self.s[self.i].isspace():self.i+=1
 def string(self):
  start=self.i;self.i+=1
  while self.i<len(self.s):
   if self.s[self.i]=='\\':self.i+=2;continue
   if self.s[self.i]=='"':self.i+=1;return self.s[start:self.i]
   self.i+=1
  raise ValueError('unterminatedstring')
 def value(self,key=None,path=()):
  self.ws();c=self.s[self.i]
  if c=='{':
   self.i+=1;out={};self.ws()
   if self.s[self.i]=='}':self.i+=1;return out
   while True:
    self.ws();k=json.loads(self.string());self.ws();assert self.s[self.i]==':';self.i+=1;v=self.value(k,path+(k,))
    if v is not MISSING:out[k]=v
    self.ws();c=self.s[self.i];self.i+=1
    if c=='}':break
    assert c==','
   return out
  if c=='[':
   self.i+=1;out=[];self.ws()
   if self.s[self.i]==']':self.i+=1;return out
   while True:
    v=self.value(key,path+('[]',))
    if v is not MISSING:out.append(v)
    self.ws();c=self.s[self.i];self.i+=1
    if c==']':break
    assert c==','
   return out
  if c=='"':token=self.string()
  else:
   start=self.i
   while self.i<len(self.s)and self.s[self.i]not in ',]} \r\n\t':self.i+=1
   token=self.s[start:self.i]
  if key in ALLOWED and not any(p.lower() in FORBIDDEN_CONTAINERS for p in path[:-1]):return json.loads(token)
  self.skipped+=1;return MISSING


def project_metadata(raw_text):
    scanner=Project(raw_text)
    result=scanner.value()
    return result, scanner.skipped

def object_spans_in_array(text,array_key):
    """Yield raw object spans; a caller must metadata-filter before value decode."""
    import re
    match=re.search(r'"'+re.escape(array_key)+r'"\s*:\s*\[',text)
    if match is None: raise ValueError("array key absent")
    i=match.end(); n=len(text)
    while True:
        while i<n and text[i] in " \r\n\t,": i+=1
        if text[i]=="]": return
        if text[i]!="{": raise ValueError("expected object array member")
        start=i; depth=0; quoted=False; escaped=False
        while i<n:
            c=text[i]
            if quoted:
                if escaped: escaped=False
                elif c=="\\": escaped=True
                elif c=='"': quoted=False
            elif c=='"': quoted=True
            elif c=="{": depth+=1
            elif c=="}":
                depth-=1
                if depth==0:
                    i+=1
                    yield text[start:i]
                    break
            i+=1
        else: raise ValueError("unterminated object array")
