import pathlib,json,hashlib,subprocess,os,datetime,traceback,re,struct
from srctools.vpk import VPK
W=pathlib.Path('E:/df-v25-build-20261106/ladder-stage');R=pathlib.Path('E:/df-v24-build-20261106');W.mkdir(exist_ok=True)
def save(n,v):(W/n).write_text(json.dumps(v,indent=2),encoding='utf8')
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 save('audit-process.json',dict(pid=os.getpid(),startedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),liveUntouched=True))
 models=[json.loads(l) for l in (R/'loot-ladder-work/ladder-models.jsonl').read_text().splitlines()]
 packs=[VPK(p)for p in (R/'ready/maps').glob('*.vpk')]
 report=[];extract=W/'packed';extract.mkdir(exist_ok=True)
 for row in models:
  key=row['model']+'_c';matches=[]
  for v in packs:
   if key in v:
    b=v[key].read();p=extract/pathlib.Path(key).name;p.write_bytes(b)
    matches.append(dict(pack=str(v.path),sha256=sha(b),bytes=len(b),CRC=v[key].verify(),extracted=str(p)))
  loose=R/'game/kat'/key
  row['compiledPacked']=matches;row['looseSHA']=sha(loose.read_bytes()) if loose.exists() else None
  report.append(row)
 save('compiled-model-closure.json',report)
 manifest={str(extract/pathlib.Path(x['model']+'_c').name):str(W/(x['id']+'.physbin'))for x in models}
 save('compiled-phys-read-manifest.json',manifest)
 reader='E:/spaceport-kat-rebuild-20261105/partition-full/phys-reader/bin/Release/net10.0/Reader.dll'
 with (W/'compiled-phys-reader.log').open('w') as log:subprocess.run(['dotnet',reader,'--manifest',str(W/'compiled-phys-read-manifest.json')],stdout=log,stderr=subprocess.STDOUT,check=True)
 phys=[]
 for row in models:
  b=(W/(row['id']+'.physbin')).read_bytes();magic,n=struct.unpack_from('<II',b);off=8;nv=nt=0
  for _ in range(n):
   a,c=struct.unpack_from('<II',b,off);off+=8+a*12+c*12;nv+=a;nt+=c
  phys.append(dict(id=row['id'],sourceBoxes=row['sourceBoxes'],meshCount=n,vertices=nv,triangles=nt,bytes=len(b),sha256=sha(b)))
 save('compiled-phys-counts.json',phys)
 entities=[]
 for v in packs:
  for key in v.filenames():
   if key.endswith('.vents_c'):
    b=v[key].read();p=extract/(pathlib.Path(str(v.path)).stem+'-'+pathlib.Path(key).name);p.write_bytes(b)
    result=subprocess.run(['dotnet',reader,'--entities',str(p)],capture_output=True,text=True,check=True);dest=p.with_suffix('.txt');dest.write_text(result.stdout,encoding='utf8')
    entities.append(dict(pack=str(v.path),path=key,extracted=str(p),dump=str(dest),sha256=sha(b),ladderTermCount=result.stdout.lower().count('ladder'),lcRefs=result.stdout.count('lc_')))
 save('compiled-entity-dumps.json',entities)
 save('audit-exit.json',dict(success=True,models=len(models),sourceBoxes=sum(r['sourceBoxes']for r in models),compiledTriangles=sum(r['triangles']for r in phys),liveUntouched=True))
if __name__=='__main__':
 try:main()
 except BaseException:save('audit-exit.json',dict(success=False,traceback=traceback.format_exc()));raise
