import os,pathlib,json,hashlib,datetime,traceback
W=pathlib.Path('E:/df-v25-build-20261106');O=W/'orchestrator/promotion-audit';O.mkdir(exist_ok=True)
def save(n,x):(O/n).write_text(json.dumps(x,indent=2))
def h(p):return hashlib.sha256(p.read_bytes()).hexdigest()
links=[];files=[];roots=['E:/df-v25-build-20261106','E:/df-v24-build-20261106/visibility-crash-audit']
for root in roots:
 for d,ds,fs in os.walk(root,followlinks=False):
  for n in ds[:]:
   p=pathlib.Path(d)/n;s=p.lstat()
   if s.st_file_attributes&1024:
    links.append({'path':str(p),'resolved':str(p.resolve()),'reparseTag':s.st_reparse_tag});ds.remove(n)
  for n in fs:
   p=pathlib.Path(d)/n;s=p.lstat()
   if s.st_file_attributes&1024 or s.st_nlink>1:links.append({'path':str(p),'resolved':str(p.resolve()),'hardlinks':s.st_nlink,'fileID':s.st_ino})
   if p.suffix.lower() in ['.py','.ps1','.cmd','.bat','.gi'] and 'material-work' not in str(p) and 'reference' not in str(p):
    files.append({'path':str(p),'resolved':str(p.resolve()),'sha256':h(p),'hardlinks':s.st_nlink})
save('links.json',links);save('script-inventory.json',files)
receipts={}
for p in (W/'orchestrator').glob('*'):
 if p.is_file() and p.suffix in ['.py','.ps1','.json','.log']:
  if p.stat().st_size<2000000:receipts[p.name]=p.read_text(errors='replace')
save('chain-receipts.json',receipts)
save('completed.json',{'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'links':len(links),'scripts':len(files),'noLiveAccess':True})
