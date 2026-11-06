import pathlib,ast,copy,json,io,re,uuid,hashlib,numpy as np
from srctools.dmx import Element,Attribute,ValueType
W=pathlib.Path('E:/df-v25-build-20261106/ladder-stage/full-v25-handoff');P=pathlib.Path('E:/spaceport-kat-rebuild-20261105/generate_vmap.py')
tree=ast.parse(P.read_text());exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name in ['parse','walk','cls']],type_ignores=[]),'helper','exec'))
r=parse(pathlib.Path('E:/spaceport-kat-rebuild-20261105/fixed-build/content/kat/maps/kat_phys_q001.vmap').read_text())
template=next(x for x in walk(r)if x.type=='CMapMesh')
d=template['meshData'].val_elem
pos=next(x for x in walk(d)if x.type=='CDmePolygonMeshDataStream'and x.name=='position:0')
verts=np.array([list(x)for x in pos['data'].iter_vec3()]);lo=verts.min(0);hi=verts.max(0);unit=(verts-lo)/(hi-lo)*2-1
ev=list(d['edgeVertexIndices'].iter_int());en=list(d['edgeNextIndices'].iter_int());fe=list(d['faceEdgeIndices'].iter_int());faces=[]
for start in fe:
 inds=[];i=start
 while i not in inds:inds.append(i);i=en[i]
 faces.append([ev[i]for i in inds])
j=json.loads(pathlib.Path('E:/df-extract-20261105/placements/validation/door-ladder-audit/ladder-implementation-manifest.json').read_text())
children=[];receipt=[]
for k,row in enumerate(j['rows']):
 m=copy.deepcopy(template)
 for x in walk(m):x.uuid=uuid.uuid5(uuid.NAMESPACE_URL,'v25-ladder/'+str(k)+'/'+str(x.uuid))
 m['nodeID']=5100000+k;m['name']='df_native_front_'+str(row['webID']);m['origin']=Attribute.vec3('origin',[0,0,0]);m['angles']=Attribute.angle('angles',[0,0,0]);m['scales']=Attribute.vec3('scales',[1,1,1]);m['physicsType']='default'
 f=row['frontOnlyClimbVolume'];C=np.array(f['matrixCS2']);ext=np.array([f['halfExtentsLocalUEcm'][a]for a in 'XYZ'])
 # Thin 1-unit sheet from source rung plane, entirely within source front volume.
 ext[1]=0.5/np.linalg.norm(C[:3,1]);C[:3,3]-=np.array(row['intendedFrontNormalCS2'])*(f['halfExtentsLocalUEcm']['Y']*np.linalg.norm(C[:3,1])-0.5)
 oriented=unit.copy()
 if np.linalg.det(C[:3,:3])<0:oriented[:,0]*=-1
 world=(oriented*ext)@C[:3,:3].T+C[:3,3]
 d=m['meshData'].val_elem;ps=next(x for x in walk(d)if x.type=='CDmePolygonMeshDataStream'and x.name=='position:0');ps['data']=Attribute.array('data',ValueType.VEC3,world.tolist())
 normals=[]
 for face in faces:
  a,b,c=world[face[:3]];n=np.cross(b-a,c-a);n/=np.linalg.norm(n)
  assert n@(world[face].mean(0)-world.mean(0))>0,'inverted mesh winding'
  normals.append(n)
 front=int(np.argmax(np.array(normals)@np.array(row['intendedFrontNormalCS2'])))
 assert normals[front]@np.array(row['intendedFrontNormalCS2'])>.999
 d['materials']=Attribute.array('materials',ValueType.STRING,['materials/tools/toolsinvisibleladder.vmat','materials/tools/toolsnodraw.vmat'])
 fd=d['faceData'].val_elem
 for stream in fd['streams'].iter_elem():
  if stream.name=='materialindex:0':stream['data']=Attribute.array('data',ValueType.INTEGER,[0 if i==front else 1 for i in range(6)])
 # Correct per-corner normals from transformed topology.
 nf=next(x for x in walk(d)if x.type=='CDmePolygonMeshDataStream'and x.name=='normal:0')
 ni=list(d['edgeVertexDataIndices'].iter_int());ef=list(d['edgeFaceIndices'].iter_int());nn=[[0,0,1]for _ in range(24)]
 for edge,idx in enumerate(ni):nn[idx]=normals[ef[edge]].tolist()
 nf['data']=Attribute.array('data',ValueType.VEC3,nn)
 children.append(m);receipt.append(dict(sourceID=row['sourceID'],webID=row['webID'],frontFace=front,frontNormal=normals[front].tolist(),vertices=world.tolist(),thicknessCS2=1,sourceClimbVolume=f,endpoints={n:v['positionCS2']for n,v in row['endpoints'].items()},clearanceEvidence=row['clearanceEvidence'],runtimeVerified=False,sideBackTopBottomMaterial='materials/tools/toolsnodraw.vmat'))
# Isolated pilot only one ladder, no unrelated world content.
r['world'].val_elem['children']=Attribute.array('children',ValueType.ELEMENT,children)
for name in ['visbility']:
 if name in r:
  for key in list(r[name].val_elem):
   a=r[name].val_elem[key]
   if a.type==ValueType.ELEMENT and a.is_array:r[name].val_elem[key]=Attribute.array(a.name,ValueType.ELEMENT,[])
for name in ['m_referencedmeshsnapshots','nodeinstancedata']:
 if name in r:r[name]=Attribute.array(name,ValueType.ELEMENT,[])
b=io.BytesIO();r.export_kv2(b,fmt_name='vmap',fmt_ver=40,unicode='silent',flat=True)
text=re.sub(r'"string"\s+"__U64__([^"]+)"',r'"uint64" "\1"',b.getvalue().decode()).replace('encoding keyvalues2 1 format vmap 40','encoding keyvalues2 4 format vmap 40')
dest=W/'df_v25_native_ladders_all10.vmap';dest.write_text(text,encoding='utf8')
assert sum(x.type=='CMapMesh'for x in walk(parse(text)))==10
(W/'native-ladder-geometry-proposal.json').write_text(json.dumps(receipt,indent=2))
(W/'pilot-input-manifest.json').write_text(json.dumps(dict(input=str(dest),sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),sourceLadder=receipt[0]['sourceID'],nativeFrontOnlyFace=True,wholeMapPromotionApproved=False,runtimeVerified=False,dependencies=['materials/tools/toolsinvisibleladder.vmat','materials/tools/toolsnodraw.vmat'],proposal='central copies VMAP to isolated content/kat/maps; RC -i INPUT -game ISOLATED_GAME -nop4 -fshallow -world -entities -phys -nobakedlighting; central sole RC owner',acceptance=['compiled world physics has ladder front surface only','side/back/top/bottom no ladder flag','player hull bottom approach/topout and rear rejection runtime later','preserve all 536 solid boxes separately; no broad rear clip']),indent=2))
print((W/'pilot-input-manifest.json').read_text())
