import pathlib,json,struct,subprocess,hashlib,traceback,datetime
import numpy as np
from srctools.vpk import VPK
W=pathlib.Path('E:/df-v25-build-20261106/ladder-stage');reader='E:/spaceport-kat-rebuild-20261105/partition-full/phys-reader/bin/Release/net10.0/Reader.dll'
def meshes(path):
 b=pathlib.Path(path).read_bytes();magic,count=struct.unpack_from('<II',b);assert magic==0x3150484B;off=8
 for _ in range(count):
  nv,nt=struct.unpack_from('<II',b,off);off+=8
  v=np.frombuffer(b,dtype='<f4',count=nv*3,offset=off).reshape(-1,3);off+=nv*12
  ix=np.frombuffer(b,dtype='<i4',count=nt*3,offset=off).reshape(-1,3);off+=nt*12
  yield v,ix
def keys(t):
 # permutation-independent 0.01-unit signatures, tolerant baked float jitter assessed separately
 return {tuple(sorted(tuple(int(q)for q in p)for p in tri))for tri in np.rint(t*100).astype(np.int64)}
def run():
 rows=json.loads((W/'compiled-worldnode-ladder-transforms.json').read_text());result=[]
 for archive in pathlib.Path('E:/df-v24-build-20261106/ready/maps').glob('*.vpk'):
  rr=[r for r in rows if r['worldnode']==archive.stem+'-n0.txt']
  if not rr:continue
  vpk=VPK(archive);key='maps/'+archive.stem+'/world_physics.vmdl_c';b=vpk[key].read();p=W/'world-audit-current.vmdl_c';p.write_bytes(b);sha=hashlib.sha256(b).hexdigest();del b
  output=W/'world-audit-current.physbin';manifest=W/'world-audit-current-manifest.json';manifest.write_text(json.dumps({str(p):str(output)}))
  with (W/'world-physics-reader.log').open('a')as log:subprocess.run(['dotnet',reader,'--manifest',str(manifest)],stdout=log,stderr=subprocess.STDOUT,check=True)
  targets=[]
  for r in rr:
   model=pathlib.Path(r['model']).stem;C=np.array(r['matrix']);t=np.concatenate([v[ix]for v,ix in meshes(W/(model+'.physbin'))]);t=t@C[:3,:3].T+C[:3,3]
   targets.append(dict(row=r,triangles=t,expectedKeys=keys(t),found=set(),candidates=0))
  for verts,ix in meshes(output):
   for target in targets:
    t=target['triangles'];lo=t.reshape(-1,3).min(0)-.02;hi=t.reshape(-1,3).max(0)+.02
    mask=np.all((verts>=lo)&(verts<=hi),axis=1);keep=np.all(mask[ix],axis=1)
    selected=verts[ix[keep]];target['candidates']+=len(selected);target['found']|=keys(selected)
  for t in targets:
   result.append(dict(model=t['row']['model'],worldPack=str(archive),worldPHYSsha256=sha,sourceExpectedTriangles=len(t['triangles']),uniqueExpected=len(t['expectedKeys']),worldMatchingTriangleKeys=len(t['expectedKeys']&t['found']),worldBBoxCandidates=t['candidates'],quantizationUnits=.01,runtimeProof=False))
  (W/'compiled-world-physics-ladder-triangle-matches.json').write_text(json.dumps(result,indent=2))
  p.unlink();output.unlink()
 (W/'world-audit-exit.json').write_text(json.dumps(dict(success=True,result=result)))
try:run()
except BaseException:(W/'world-audit-exit.json').write_text(json.dumps(dict(success=False,traceback=traceback.format_exc())));raise
