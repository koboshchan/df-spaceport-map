from pathlib import Path
import sys,json,hashlib,re,struct,subprocess,ast,traceback,os,collections
sys.dont_write_bytecode=True
S=Path('TWOPART_ROOT');Q=S/'proof';G=S/'game/kat'
def save(n,d):(Q/n).write_text(json.dumps(d,indent=2))
def sha(p):
 with p.open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def field(b,k):
 m=re.search('"'+re.escape(k)+'" "[^"]+" "([^"]*)"',b);return m[1]if m else None
def value(b,k):
 m=re.search(r'^'+re.escape(k)+r'\s+(.+)$',b,re.M);return m[1].strip().strip('"')if m else None
def vec(s):return [float(x)for x in s.strip('[] ').replace(',',' ').split()]
def exact(a,b):return len(a)==len(b)and all(struct.pack('f',x)==struct.pack('f',y)for x,y in zip(a,b))
try:
 assert (Q/'THREE-COMPILED.json').exists()
 sys.path.insert(0,'PARENT_BUILD/packqa/python-deps')
 from srctools.vpk import VPK
 src=Path('REBUILD_ROOT/next_partition_lib.py')
 tree=ast.parse(src.read_text());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name in ['blocks','refs']],type_ignores=[]),str(src),'exec'))
 manifest={}
 for top in ['models','materials','panorama','scripts','particles','resource']:
  base=G/top
  if base.exists():
   for p in base.rglob('*'):
    if p.is_file()and p.name.endswith('_c'):manifest[p.relative_to(G).as_posix()]=str(p)
 save('assets-manifest.json',manifest)
 env=os.environ.copy()
 for k in ['TEMP','TMP','LOCALAPPDATA','APPDATA','USERPROFILE','HOME','DOTNET_CLI_HOME','NUGET_PACKAGES','DOTNET_BUNDLE_EXTRACT_BASE_DIR']:
  d=Q/'env'/k;d.mkdir(parents=True,exist_ok=True);env[k]=str(d)
 ready=S/'ready/maps';ready.mkdir(parents=True,exist_ok=True)
 names=['df_spaceport_v268_twopart','df_spaceport_v268_twopart_part0','df_spaceport_v268_twopart_part1']
 for i,name in enumerate(names):
  src=G/'maps'/(name+'.vpk');assert src.exists()
  if (ready/src.name).exists():continue
  if i:
   shutilcopy=__import__('shutil').copy2;shutilcopy(src,ready/src.name)
  else:
   cmd=['dotnet','REBUILD_ROOT/fixed-build/pack-tool/bin/Release/net10.0/Pack.dll',str(src),str(Q/'assets-manifest.json'),str(ready/src.name)]
   with(Q/'pack.log').open('w')as f:
    p=subprocess.Popen(cmd,cwd=S,env=env,stdout=f,stderr=subprocess.STDOUT);save('package-process.json',dict(pid=p.pid,command=cmd));assert p.wait(timeout=1800)==0
 packages=[];worldphys=[];allrefs=set();providers=set();modelproof=[];allobs=[];partclasses={}
 reader='REBUILD_ROOT/partition-full/phys-reader/bin/Release/net10.0/Reader.dll'
 for i,name in enumerate(names):
  p=ready/(name+'.vpk');v=VPK(p);resources=list(v.filenames())
  assert sum(n.endswith('.vwrld_c')for n in resources)==1
  es=[n for n in resources if n.endswith('.vents_c')];assert len(es)==1
  ep=Q/(name+'.vents_c');ep.write_bytes(v[es[0]].read())
  r=subprocess.run(['dotnet',reader,'--entities',str(ep)],capture_output=True,text=True,env=env);assert r.returncode==0,r.stderr
  text=r.stdout;(Q/(name+'-entities.txt')).write_text(text)
  obs=[b for b in re.split(r'====\d+====',text)if value(b,'classname')]
  cls=collections.Counter(value(b,'classname')for b in obs);partclasses[name]=dict(cls);allobs+=obs
  assert cls['prop_dynamic']==0 and cls['prop_dynamic_override']==0 and cls['prop_static']==0
  if i==0:assert cls['trigger_hurt']==1847 and cls['info_player_terrorist']==16 and cls['info_player_counterterrorist']==16 and cls['info_spawngroup_load_unload']==2
  else:assert not cls['trigger_hurt']and not cls['info_player_terrorist']and not cls['info_player_counterterrorist']and not cls['env_sky']
  for n in resources:
   assert v[n].verify(),n
   providers.add(n.lower());data=v[n].read()
   if n.endswith('_c'):allrefs.update(x.lower()if x.endswith('_c')else x.lower()+'_c'for x in refs(data))
   if n.endswith('/world_physics.vmdl_c'):
    bs=blocks(data);size=len(bs.get('PHYS',b''));assert (0<size<536870912)or(i==0 and 'PHYS'not in bs),(name,size)
    worldphys.append(dict(map=name,resource=n,serializedBytes=size,margin512MiB=536870912-size,margin450MiB=450*1024**2-size,sha256=hashlib.sha256(data).hexdigest()))
   if not n.startswith('maps/')and n in manifest:
    assert hashlib.sha256(data).hexdigest()==sha(Path(manifest[n])),n
    if n.startswith('models/')and n.endswith('.vmdl_c'):
     bs=blocks(data)
     if 'PHYS'in bs:modelproof.append(dict(resource=n,PHYSBytes=len(bs['PHYS']),sha256=hashlib.sha256(data).hexdigest()))
  packages.append(dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p),CRC=True,resources=len(resources)))
 assert len(worldphys)==3
 missing=allrefs-providers;stock={}
 for k in ['core','csgo']:
  for p in (S/'game'/k).glob('*dir.vpk'):
   for n in VPK(p).filenames():
    if n.lower()in missing:stock[n.lower()]=str(p)
 missing=sorted(missing-set(stock));expected=['maps/'+n+'/world_visibility.vvis_c'for n in names]
 unexpected=[x for x in missing if x not in expected]
 save('closure.json',dict(missing=missing,unexpected=unexpected,stock=stock,fullClosurePass=not missing));assert not unexpected
 source=S/'content/kat/maps/df_spaceport_v268_twopart.vmap';bmap={}
 for m in re.finditer(r'^"([^"]+)"\s*\n\{(.*?)^\}',source.read_text(),re.M|re.S):
  k,b=m.groups();bmap[field(b,'id')]=(k,m.group())
 expectedtr=[];sp=[]
 for u,(k,b)in bmap.items():
  if k!='CMapEntity':continue
  pb=bmap[field(b,'entity_properties')][1];cl=field(pb,'classname')
  if cl=='trigger_hurt':expectedtr.append((u,'[PR#]'+field(pb,'targetname'),field(b,'nodeID')))
  if cl in ['info_player_terrorist','info_player_counterterrorist']:sp.append((u,b,pb,cl))
 got=[b for b in allobs if value(b,'classname')=='trigger_hurt']
 actual=sorted((value(b,'hammeruniqueid')or value(b,'hammerid'),value(b,'targetname'))for b in got)
 baseline=json.loads(Path('PARENT_BUILD/scopeqa/compiled-trigger-observed.json').read_text())['rows']
 assert len(expectedtr)==len(got)==1847
 assert actual==sorted((str(b['id']),b['targetname'])for b in baseline)
 for u,name,node in expectedtr:assert(node,name)in actual
 compiledsp=[b for b in allobs if value(b,'classname')in ['info_player_terrorist','info_player_counterterrorist']]
 assert len(compiledsp)==len(sp)==32
 for u,b,pb,cl in sp:
  matches=[c for c in compiledsp if value(c,'targetname')=='[PR#]'+field(pb,'targetname')];assert len(matches)==1
  c=matches[0];assert value(c,'classname')==cl
  for key in ['origin','angles','scales']:assert exact(vec(field(b,key)),vec(value(c,key))),(u,key)
 assert sum(value(b,'classname')=='info_spawngroup_load_unload'for b in allobs)==2
 loadernames=[value(b,'mapname')for b in allobs if value(b,'classname')=='info_spawngroup_load_unload']
 assert all(any(name in (x or '')for x in loadernames)for name in names[1:]),loadernames
 save('WORLD-PHYS-receipt.json',dict(blocks=worldphys,total=sum(r['serializedBytes']for r in worldphys),measuredNative=True))
 save('COMPILED-ENTITY-COUNTS.json',dict(perMap=partclasses,total=sum(sum(c.values())for c in partclasses.values()),triggers1847Exact=True,native32Float32Exact=True,zeroDynamic=True,loaders=loadernames))
 save('MODEL-PHYS-proof.json',modelproof)
 save('PACKAGE-QA-COMPLETE.json',dict(packages=packages,CRC=True,assetSHA=True,compiledScope=True,allWORLDunder512MiB=True,fullClosurePass=not missing,expectedNoBakedVisibilityMissing=missing,noInstall=True,runtimeUnverified=True))
except BaseException:save('QA-BLOCKER.json',dict(error=traceback.format_exc(),noInstall=True));raise
