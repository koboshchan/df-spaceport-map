"""Lossless ordered JSONL chunks. Standard library only."""
import argparse,hashlib,json
from pathlib import Path
LIMIT=50*1024*1024
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def split(source,directory,limit=LIMIT):
 source=Path(source); directory=Path(directory)
 if not 0<limit<=LIMIT:raise ValueError('chunk cap must be <=50MiB')
 directory.mkdir(parents=True,exist_ok=False)
 parts=[];out=None;whole=hashlib.sha256();size=0
 try:
  with source.open('rb') as inp:
   for line in inp:
    json.loads(line)
    if len(line)>limit:raise ValueError('JSONL line exceeds chunk limit')
    if out is None or parts[-1]['bytes']+len(line)>limit:
     if out:out.close()
     name=f'part-{len(parts):04}.jsonl';out=(directory/name).open('xb')
     parts.append({'name':name,'bytes':0})
    out.write(line);parts[-1]['bytes']+=len(line);size+=len(line);whole.update(line)
 finally:
  if out:out.close()
 for part in parts:part['sha256']=sha(directory/part['name'])
 manifest={'schema':1,'bytes':size,'sha256':whole.hexdigest(),'parts':parts}
 (directory/'reassembly.json').write_text(json.dumps(manifest,indent=2)+'\n')
 return manifest
def join(directory,destination):
 directory=Path(directory);destination=Path(destination)
 m=json.loads((directory/'reassembly.json').read_text())
 # Verify every input before writing any output.
 for part in m['parts']:
  p=directory/part['name']
  if Path(part['name']).name!=part['name'] or p.is_symlink():raise ValueError('unsafe part')
  if p.stat().st_size!=part['bytes'] or sha(p)!=part['sha256']:raise ValueError('chunk checksum mismatch')
 with destination.open('xb') as out:
  for part in m['parts']:
   with (directory/part['name']).open('rb') as f:
    for b in iter(lambda:f.read(1048576),b''):out.write(b)
 if destination.stat().st_size!=m['bytes'] or sha(destination)!=m['sha256']:raise ValueError('reassembly checksum mismatch')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['split','join']);p.add_argument('source');p.add_argument('destination');a=p.parse_args()
 (split if a.action=='split' else join)(a.source,a.destination)
