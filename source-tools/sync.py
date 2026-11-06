"""Explicit reviewed source sync. Dry-run by default; never executes Git."""
import argparse,json,os,shutil,hashlib
from pathlib import Path
from jsonl_chunks import split
LIMIT=104857600
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def relative(s):
 p=Path(s)
 if p.is_absolute() or '..' in p.parts or ':' in s or '\\' in s:raise ValueError('unsafe relative path')
 return p
def root(s):
 p=Path(s).resolve()
 if p.drive.upper()!='E:':raise ValueError('runtime roots must be E-only')
 return p
def plan(config,src,dst):
 out=[];seen=set()
 for e in config['entries']:
  a=src/relative(e['source']);b=dst/relative(e['destination'])
  if b in seen:raise ValueError('duplicate destination')
  seen.add(b)
  for p,base in ((a,src),(b,dst)):
   if not p.resolve().is_relative_to(base) or p.is_symlink():raise ValueError('unsafe source/destination')
  low=a.name.lower()
  if low.endswith(('_c','.vpk','.log','.exe','.dll','.zip','.7z','.pak')) or any(x in low for x in ('credential','cookie','aes-key','steamid')):raise ValueError('excluded file')
  st=a.stat()
  if st.st_size!=e['bytes'] or st.st_mtime_ns!=e['mtime_ns']:raise ValueError('source changed '+e['source'])
  if st.st_size>LIMIT and a.suffix.lower()!='.jsonl':raise ValueError('oversized binary model cannot be split')
  target=b.with_name(b.name+'.chunks') if st.st_size>LIMIT else b
  if target.exists():raise ValueError('refusing overwrite '+str(target))
  out.append((a,b,e))
 return out
def main():
 p=argparse.ArgumentParser()
 p.add_argument('--manifest',default=str(Path(__file__).with_name('selection.json')))
 p.add_argument('--source',default=os.getenv('DF_SOURCE_ROOT'))
 p.add_argument('--destination',default=os.getenv('DF_SOURCE_DEST'))
 p.add_argument('--apply',action='store_true')
 a=p.parse_args()
 if not a.source or not a.destination:p.error('explicit E-only roots required')
 rows=plan(json.loads(Path(a.manifest).read_text()),root(a.source),root(a.destination))
 print(json.dumps({'files':len(rows),'bytes':sum(e['bytes'] for _,_,e in rows),'apply':a.apply}))
 if not a.apply:return
 # Verify all inputs before any output writes.
 for src,dst,e in rows:
  if sha(src)!=e['sha256']:raise ValueError('source hash mismatch '+str(src))
 for src,dst,e in rows:
  st=src.stat()
  if st.st_size!=e['bytes'] or st.st_mtime_ns!=e['mtime_ns']:raise ValueError('source changed before copy')
  if e['bytes']>LIMIT:split(src,dst.with_name(dst.name+'.chunks'))
  else:
   dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
   if sha(dst)!=e['sha256']:raise ValueError('copy hash mismatch')
  if src.stat().st_mtime_ns!=e['mtime_ns'] or sha(src)!=e['sha256']:raise ValueError('source changed during copy')
if __name__=='__main__':main()
