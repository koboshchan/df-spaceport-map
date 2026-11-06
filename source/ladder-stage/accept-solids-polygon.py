import pathlib,json,re,numpy as np
from shapely.geometry import Polygon,box
from shapely.ops import unary_union
W=pathlib.Path('E:/df-v25-build-20261106/ladder-stage/solids-compiled-audit')
s=(W/'world_physics.dump.txt').read_text();b=s.split('m_meshes =',1)[1].split('m_compounds =',1)[0]
def arr(name,dtype):return np.frombuffer(bytes.fromhex(re.search(name+r' =\s*#\[([^]]*)\]',b,re.S)[1]),dtype=dtype)
v=arr('m_Vertices','<f4').reshape(-1,3);t=v[arr('m_Triangles','<i4').reshape(-1,3)];a=t[:,0];n=np.cross(t[:,1]-a,t[:,2]-a);n/=np.linalg.norm(n,axis=1)[:,None]
j=json.loads(pathlib.Path('E:/df-extract-20261105/placements/validation/door-ladder-audit/ladder-solid-collision-manifest.json').read_text());result=[];reverse=np.zeros(len(t),bool)
for row in j['rows']:
 for bi,q in enumerate(row['sourceCollisionBoxes']):
  C=np.array(q['matrixCS2']);A=C[:3,:3];e=np.array(q['halfExtentsLocalUEcm']);local=(t-C[:3,3])@np.linalg.inv(A).T
  for axis in range(3):
   others=[k for k in range(3)if k!=axis];rect=box(-e[others[0]],-e[others[1]],e[others[0]],e[others[1]])
   for sign in [-1,1]:
    normal=np.linalg.inv(A).T[:,axis]*sign;normal/=np.linalg.norm(normal)
    candidates=np.where(np.all(abs(local[:,:,axis]-sign*e[axis])<.06,axis=1)&((n@normal)>.999))[0];polys=[]
    for ix in candidates:
     poly=Polygon(local[ix][:,others])
     if poly.is_valid:polys.append(poly)
     if np.all(abs(local[ix])<=e+.06):reverse[ix]=True
    union=unary_union(polys)if polys else Polygon()
    # Roundoff-aware inward erosion .001UEcm avoids classifying single-float edge jitter as missing.
    target=rect.buffer(-.001,join_style=2);covered=union.buffer(.001,join_style=2).covers(target)
    result.append(dict(webID=row['webID'],boxIndex=bi,axis=axis,sign=sign,expectedAreaLocal=float(rect.area),intersectionArea=float(union.intersection(rect).area),uncoveredArea=float(rect.difference(union).area),coveredWithFloatTolerance=bool(covered)))
r=dict(polygonUnionSurfaceAcceptance=all(x['coveredWithFloatTolerance']for x in result),sourceFaces=len(result),passedFaces=sum(x['coveredWithFloatTolerance']for x in result),compiledTriangles=len(t),reverseAllTriangleVerticesWithinSourceFaces=int(reverse.sum()),reversePass=bool(reverse.all()),floatToleranceUEcm=.001,method='Shapely exact coplanar triangle union covers each source rectangle, including float tolerance; reverse all THREE triangle vertices fit corresponding OBB face')
(W/'polygon-union-per-face.json').write_text(json.dumps(result,indent=2));(W/'polygon-union-acceptance.json').write_text(json.dumps(r,indent=2))
print(json.dumps(r))
