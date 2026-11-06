import pathlib,ast,copy,json,io,re,uuid,hashlib,numpy as np
from srctools.dmx import Element,Attribute,ValueType
W=pathlib.Path('E:/df-v25-build-20261106/ladder-stage/world-collision-candidate')
P=pathlib.Path('E:/spaceport-kat-rebuild-20261105/generate_vmap.py');tree=ast.parse(P.read_text());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name in ['parse','walk','cls']],type_ignores=[]),'helper','exec'))
r=parse(pathlib.Path('E:/spaceport-kat-rebuild-20261105/fixed-build/content/kat/maps/kat_phys_q001.vmap').read_text())
template=next(x for x in walk(r)if x.type=='CMapMesh');d=template['meshData'].val_elem
pos=next(x for x in walk(d)if x.type=='CDmePolygonMeshDataStream'and x.name=='position:0');verts=np.array([list(x)for x in pos['data'].iter_vec3()]);lo=verts.min(0);hi=verts.max(0);unit=(verts-lo)/(hi-lo)*2-1
ev=list(d['edgeVertexIndices'].iter_int());en=list(d['edgeNextIndices'].iter_int());fe=list(d['faceEdgeIndices'].iter_int());faces=[]
for start in fe:
 inds=[];i=start
 while i not in inds:inds.append(i);i=en[i]
 faces.append([ev[i]for i in inds])
source=pathlib.Path('E:/df-extract-20261105/placements/validation/door-ladder-audit/ladder-solid-collision-manifest.json');j=json.loads(source.read_text())
children=[];receipt=[]
for row in j['rows']:
 for bi,box in enumerate(row['sourceCollisionBoxes']):
  k=len(children);m=copy.deepcopy(template)
  for x in walk(m):x.uuid=uuid.uuid5(uuid.NAMESPACE_URL,'v25-solid-ladder/'+str(k)+'/'+str(x.uuid))
  m['nodeID']=5200000+k;m['name']='df_solid_'+row['webID']+'_'+str(bi);m['origin']=Attribute.vec3('origin',[0,0,0]);m['angles']=Attribute.angle('angles',[0,0,0]);m['scales']=Attribute.vec3('scales',[1,1,1]);m['physicsType']='default'
  C=np.array(box['matrixCS2']);ext=np.array(box['halfExtentsLocalUEcm']);oriented=unit.copy()
  if np.linalg.det(C[:3,:3])<0:oriented[:,0]*=-1
  world=(oriented*ext)@C[:3,:3].T+C[:3,3]
  expected=np.array(box['worldCornersCS2']);error=max(min(np.linalg.norm(v-e)for e in expected)for v in world);assert error<1e-7
  d=m['meshData'].val_elem;ps=next(x for x in walk(d)if x.type=='CDmePolygonMeshDataStream'and x.name=='position:0');ps['data']=Attribute.array('data',ValueType.VEC3,world.tolist())
  normals=[]
  for face in faces:
   a,b,c=world[face[:3]];n=np.cross(b-a,c-a);n/=np.linalg.norm(n);assert n@(world[face].mean(0)-world.mean(0))>0;normals.append(n)
  d['materials']=Attribute.array('materials',ValueType.STRING,['materials/tools/toolsnodraw.vmat'])
  for stream in d['faceData'].val_elem['streams'].iter_elem():
   if stream.name=='materialindex:0':stream['data']=Attribute.array('data',ValueType.INTEGER,[0]*6)
  nf=next(x for x in walk(d)if x.type=='CDmePolygonMeshDataStream'and x.name=='normal:0');ni=list(d['edgeVertexDataIndices'].iter_int());ef=list(d['edgeFaceIndices'].iter_int());nn=[[0,0,1]for _ in range(24)]
  for edge,idx in enumerate(ni):nn[idx]=normals[ef[edge]].tolist()
  nf['data']=Attribute.array('data',ValueType.VEC3,nn);children.append(m)
  receipt.append(dict(webID=row['webID'],actor=row['actor'],component=box['component'],instanceIndex=box['instanceIndex'],boxIndex=box['boxIndex'],nodeID=5200000+k,sourceCornersErrorMax=error,bounds=dict(min=world.min(0).tolist(),max=world.max(0).tolist()),vertices=world.tolist(),outwardWindingAllSix=True))
assert len(children)==536
r['world'].val_elem['children']=Attribute.array('children',ValueType.ELEMENT,children)
for name in ['visbility']:
 if name in r:
  for key in list(r[name].val_elem):
   a=r[name].val_elem[key]
   if a.type==ValueType.ELEMENT and a.is_array:r[name].val_elem[key]=Attribute.array(a.name,ValueType.ELEMENT,[])
for name in ['m_referencedmeshsnapshots','nodeinstancedata']:
 if name in r:r[name]=Attribute.array(name,ValueType.ELEMENT,[])
b=io.BytesIO();r.export_kv2(b,fmt_name='vmap',fmt_ver=40,unicode='silent',flat=True);text=re.sub(r'"string"\s+"__U64__([^"]+)"',r'"uint64" "\1"',b.getvalue().decode()).replace('encoding keyvalues2 1 format vmap 40','encoding keyvalues2 4 format vmap 40')
dest=W/'df_v25_ladder_solids_candidate.vmap';dest.write_text(text,encoding='utf8');assert sum(x.type=='CMapMesh'for x in walk(parse(text)))==536
(W/'solid-world-boxes-proposal.json').write_text(json.dumps(dict(source=str(source),sourceSHA256=hashlib.sha256(source.read_bytes()).hexdigest(),input=str(dest),sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),boxCount=536,sourceActors=10,sourceEquivalentGeometry=True,material='materials/tools/toolsnodraw.vmat',purpose='alternative world-physics route; replaces collision-only lc static-props when promoted, never duplicate both',nativeClimbSeparateFrozenPilotUnchanged=True,compiledAccepted=False,runtimeAccepted=False,boxes=receipt),indent=2))
print(json.dumps(dict(input=str(dest),sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),boxCount=len(receipt),maxSourceCornersError=max(q['sourceCornersErrorMax']for q in receipt))))
