import pathlib,json,hashlib,subprocess,re,struct,traceback
import numpy as np
from srctools.vpk import VPK
W=pathlib.Path('E:/df-v25-build-20261106/ladder-stage/solids-compiled-audit');W.mkdir(exist_ok=True)
P=pathlib.Path('E:/df-v25-build-20261106/orchestrator/ladder-solids-pilot')
def main():
 vpk=VPK(P/'game/kat/maps/df_v25_ladder_solids_candidate.vpk');resources=[]
 for key in vpk.filenames():
  b=vpk[key].read();assert vpk[key].verify();resources.append(dict(resource=key,bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),CRCVerified=True))
  if key.endswith('world_physics.vmdl_c'):(W/'world_physics.vmdl_c').write_bytes(b)
 (W/'vpk-resource-closure.json').write_text(json.dumps(resources,indent=2))
 cli='E:/spaceport-kat-rebuild-20261105/vrf/Source2Viewer-CLI.exe'
 s=subprocess.run([cli,'-i',str(W/'world_physics.vmdl_c'),'-a'],capture_output=True,text=True,check=True).stdout;(W/'world_physics.dump.txt').write_text(s,encoding='utf8')
 part=s.split('m_meshes =',1)[1].split('m_compounds =',1)[0]
 meshes=[]
 for block in re.split(r'm_nCollisionAttributeIndex = ',part)[1:]:
  def arr(name,dtype):
   x=re.search(name+r' =\s*#\[([^]]*)\]',block,re.S)[1];return np.frombuffer(bytes.fromhex(x),dtype=dtype)
  verts=arr('m_Vertices','<f4').reshape(-1,3);idx=arr('m_Triangles','<i4').reshape(-1,3)
  meshes.append(dict(attr=int(block.split()[0]),surface=int(re.search(r'm_nSurfacePropertyIndex = (\d+)',block)[1]),triangles=verts[idx]))
 t=np.concatenate([x['triangles']for x in meshes]);a=t[:,0];u=t[:,1]-a;v=t[:,2]-a;n=np.cross(u,v);norm=np.linalg.norm(n,axis=1);n/=np.maximum(norm[:,None],1e-30)
 # Exact source face rectangles, sampled dense enough to prove separated box surfaces against triangle tessellation.
 src=json.loads(pathlib.Path('E:/df-extract-20261105/placements/validation/door-ladder-audit/ladder-solid-collision-manifest.json').read_text())
 faces=[];boxes=[]
 for row in src['rows']:
  for bi,box in enumerate(row['sourceCollisionBoxes']):
   C=np.array(box['matrixCS2']);e=np.array(box['halfExtentsLocalUEcm']);center=C[:3,3];A=C[:3,:3]
   for axis in range(3):
    other=[k for k in range(3)if k!=axis]
    for sign in [-1,1]:
     normal=np.linalg.inv(A).T[:,axis]*sign;normal/=np.linalg.norm(normal);origin=center+A[:,axis]*e[axis]*sign
     axisU=A[:,other[0]]*e[other[0]];axisV=A[:,other[1]]*e[other[1]]
     points=np.array([origin+axisU*x+axisV*y for x in [-.99,-.5,0,.5,.99]for y in [-.99,-.5,0,.5,.99]])
     cand=np.where((abs((a-origin)@normal)<.02)&((n@normal)>.999))[0]
     covered=np.zeros(len(points),dtype=bool)
     for ii in cand:
      uu=u[ii]@u[ii];uv=u[ii]@v[ii];vv=v[ii]@v[ii];den=uu*vv-uv*uv
      if den<1e-16:continue
      w=points-a[ii];wu=w@u[ii];wv=w@v[ii];ss=(wu*vv-wv*uv)/den;zz=(wv*uu-wu*uv)/den
      covered|=(ss>=-1e-4)&(zz>=-1e-4)&(ss+zz<=1.0001)
     faces.append(dict(actor=row['actor'],webID=row['webID'],boxIndex=bi,component=box['component'],instanceIndex=box['instanceIndex'],axis=axis,sign=sign,origin=origin.tolist(),normal=normal.tolist(),candidateTriangles=len(cand),samples=25,coveredSamples=int(covered.sum()),passSurface=bool(covered.all())))
   boxes.append(dict(webID=row['webID'],boxIndex=bi,allSixFacesPass=all(f['passSurface']for f in faces[-6:])))
 # Reverse proof compiled triangle centroid must lie on a source OBB outward face, within exact face extents.
 cent=t.mean(1);reverse=np.zeros(len(t),bool)
 for row in src['rows']:
  for box in row['sourceCollisionBoxes']:
   C=np.array(box['matrixCS2']);A=C[:3,:3];e=np.array(box['halfExtentsLocalUEcm']);local=(cent-C[:3,3])@np.linalg.inv(A).T
   inbounds=np.all(abs(local)<=e+.06,axis=1)
   for axis in range(3):
    for sign in [-1,1]:
     normal=np.linalg.inv(A).T[:,axis]*sign;normal/=np.linalg.norm(normal)
     reverse|=inbounds&(abs(local[:,axis]-sign*e[axis])<.06)&((n@normal)>.999)
 attrs=s.split('m_collisionAttributes =',1)[1].split('m_debugPartNames',1)[0]
 groupdefault='m_CollisionGroupString = "default"'in attrs;noLadder='"ladder"'not in attrs
 result=dict(compiledAccepted=all(b['allSixFacesPass']for b in boxes)and bool(reverse.all())and groupdefault and noLadder,boxes=536,sourceFaces=len(faces),sourceFacesPassing=sum(f['passSurface']for f in faces),compiledTriangles=len(t),compiledMeshes=[dict(attribute=x['attr'],surface=x['surface'],triangles=len(x['triangles']))for x in meshes],reverseTriangleCentroidsOnSourceOutwardFaces=int(reverse.sum()),defaultCollisionGroup=groupdefault,noLadderOnSolidBoxes=noLadder,surfacePlaneToleranceUnits=.02,sourceLocalBoundsToleranceUEcm=.06,perFaceSamples=25,proofMethod='per source face 5x5 barycentric coverage, plane+normal agreement; reverse compiled triangle centroid within source face extents. Not count-only.',runtimeVerified=False,allResourcesCRCVerified=True)
 (W/'per-source-face-evidence.json').write_text(json.dumps(faces,indent=2));(W/'per-source-box-evidence.json').write_text(json.dumps(boxes,indent=2));(W/'compiled-acceptance.json').write_text(json.dumps(result,indent=2))
 for name in ['process.json','exit.json','compiler.log']:
  if(P/name).exists():(W/('central-'+name)).write_bytes((P/name).read_bytes())
 print(json.dumps(result))
try:main()
except BaseException:(W/'audit-error.json').write_text(traceback.format_exc());raise
