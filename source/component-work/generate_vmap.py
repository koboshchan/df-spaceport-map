"""DF v24 child VMAP generator. No old geometry is copied. Run detached by executor."""
import argparse,ast,copy,hashlib,io,json,math,re,sys,uuid
from pathlib import Path
import numpy as np
from srctools.dmx import Element,Attribute,ValueType
REF=Path('E:/spaceport-kat-rebuild-20261105/generate_vmap.py')
tree=ast.parse(REF.read_text(encoding='utf8'))
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('parse','walk','cls')],type_ignores=[]),'reference-dmx-functions','exec'))
def decompose(C):
 m=np.array(C,dtype=float);a=m[:3,:3];s=np.linalg.norm(a,axis=0)
 if not np.isfinite(m).all():raise ValueError('nonfinite matrix')
 if min(s)<1e-10:raise ValueError('authored zero scale')
 R=a/s
 if np.linalg.det(R)<0:s[0]*=-1;R[:,0]*=-1
 shear=float(np.max(np.abs(R.T@R-np.eye(3))))
 if shear>1e-4:raise ValueError('source shear needs exact baked model '+str(shear))
 pitch=math.atan2(-R[2,0],math.hypot(R[0,0],R[1,0]))
 if math.hypot(R[0,0],R[1,0])>1e-8:yaw=math.atan2(R[1,0],R[0,0]);roll=math.atan2(R[2,1],R[2,2])
 else:yaw=math.atan2(-R[0,1],R[1,1]);roll=0.
 cp,sp,cy,sy,cr,sr=math.cos(pitch),math.sin(pitch),math.cos(yaw),math.sin(yaw),math.cos(roll),math.sin(roll)
 rr=np.array([[cy*cp,cy*sp*sr-sy*cr,cy*sp*cr+sy*sr],[sy*cp,sy*sp*sr+cy*cr,sy*sp*cr-cy*sr],[-sp,cp*sr,cp*cr]])
 err=float(np.max(np.abs(rr*s-a)))
 if err>1e-4*max(1,float(np.max(np.abs(a)))):raise ValueError('recompose failed '+str(err))
 return m[:3,3].tolist(),np.degrees([pitch,yaw,roll]).tolist(),s.tolist(),shear,err
def entity(c,n,i):
 e=Element(n,'CMapEntity');e.uuid=uuid.uuid5(uuid.NAMESPACE_URL,'df-v24/'+n)
 e['nodeID']=4000000+i;e['origin']=Attribute.vec3('origin',[0,0,0]);e['angles']=Attribute.angle('angles',[0,0,0]);e['scales']=Attribute.vec3('scales',[1,1,1]);e['children']=Attribute.array('children',ValueType.ELEMENT,[])
 ep=Element('entity_properties','EditGameClassProps');ep['classname']=c;ep['targetname']=n;e['entity_properties']=ep;e['connectionsData']=Attribute.array('connectionsData',ValueType.ELEMENT,[]);return e
def generate(args):
 src=Path(args.rows);text=src.read_text(encoding='utf-8-sig')
 rows=json.loads(text) if text.lstrip().startswith('[') else [json.loads(l) for l in text.splitlines() if l.strip()]
 models={x['objectPath']:x for x in (json.loads(l) for l in Path(args.models).open(encoding='utf-8-sig'))}
 root=parse(Path(args.template).read_text(encoding='utf8'));world=root['world'].val_elem
 # Strong strip, no geometry/entities/light/brush children from old map.
 stripped=sum(1 for _ in walk(world));world['children']=Attribute.array('children',ValueType.ELEMENT,[])
 # Preserve CMapRootElement structural metadata required by native map builder.
 # CVisibilityMgr may reference original scene geometry independently of world.
 # Remove its element references, not the manager/schema itself.
 if 'visbility' in root:
  visibility=root['visbility'].val_elem
  for field in list(visibility.keys()):
   attr=visibility[field]
   if attr.type==ValueType.ELEMENT:
    if not attr.is_array:raise ValueError('unexpected scalar visibility reference '+field)
    visibility[field]=Attribute.array(attr.name,ValueType.ELEMENT,[])
 # Preserve empty structural roots without permitting hidden old scene payload.
 for field in ('m_referencedmeshsnapshots','nodeinstancedata'):
  if field in root:root[field]=Attribute.array(root[field].name,ValueType.ELEMENT,[])
 props=[];fail=[];zero=[];maxshear=0;maxerr=0
 # Geometry exporter bakes Blender glTF Y-up to Z-up; imported model local is UE(X,-Y,Z)*.36.
 B=np.eye(4);B[:3,:3]=np.diag([1.,-1.,1.])/.36
 for i,row in enumerate(rows):
  op=row['objectPath'];model=row.get('model') or models.get(row['meshObjectPath'],{}).get('model')
  if not model:fail.append(dict(objectPath=op,reason='model index missing',mesh=row['meshObjectPath']));continue
  if not re.fullmatch(r'models/df_v24/[A-Za-z0-9_]+\.vmdl',model):raise ValueError('unsafe/nonDF model '+model)
  if row.get('requiresSourceDeformation') and not row.get('sourceDeformedModel'):
   fail.append(dict(objectPath=op,reason='spline requires source deformation not base rope placement'));continue
  C=np.array(row['matrixCS2'])@B
  if row.get('sourceDeformedModel'):model=row['sourceDeformedModel']
  if row.get('bakedCS2LocalTransform'):
   C=np.eye(4);C[:3,3]=row['positionCS2']
  if row.get('worldBakedCS2') or row.get('worldBaked'):
   C=np.eye(4)
  try:pos,ang,scales,shear,err=decompose(C)
  except ValueError as exc:
   if 'zero scale' in str(exc):
    zero.append(dict(objectPath=op,reason='source-authored collapsed geometry emits no visible/colliding prop',sourceMatrix=row['matrixCS2']));continue
   fail.append(dict(objectPath=op,reason=str(exc)));continue
  maxshear=max(maxshear,shear);maxerr=max(maxerr,err)
  e=entity('prop_static','df_'+hashlib.sha256((op+'#'+str(row.get('instanceIndex'))).encode()).hexdigest()[:20],i)
  e['origin']=Attribute.vec3('origin',pos);e['angles']=Attribute.angle('angles',ang);e['scales']=Attribute.vec3('scales',scales)
  ep=e['entity_properties'].val_elem
  for n,v in dict(model=model,classname='prop_static',solid='6' if row.get('collisionEnabled',True) else '0',disableshadows='0',baketoworld='false',disablemerging='false',materialoverride='').items():ep[n]=v
  props.append(e)
 props.append(entity('info_spawngroup_landmark','df_v24_origin',len(rows)))
 dst=Path(args.outmap);dst.parent.mkdir(parents=True,exist_ok=True)
 receipt=dict(rows=len(rows),generatedProps=len(props)-1,failures=fail,authoredZeroScaleSuppressed=zero,maxShear=maxshear,maxRecomposeError=maxerr,oldWorldElementsStripped=stripped,modelBasis='Imported FBX local UE(X,-Y,Z)*.36; diag(1,-1,1)/.36 confirmed compiledRC Dock679vertex proof',templateOnlyNoOldGeometry=True,sourceRows=str(src))
 dst.with_suffix('.report.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
 if fail:raise ValueError(str(len(fail))+' exact geometry/transform failures; see report; no VMAP written')
 world['children']=Attribute.array('children',ValueType.ELEMENT,props)
 b=io.BytesIO();root.export_kv2(b,fmt_name='vmap',fmt_ver=40,unicode='silent',flat=True)
 t=re.sub(r'"string"\s+"__U64__([^"]+)"',r'"uint64" "\1"',b.getvalue().decode()).replace('encoding keyvalues2 1 format vmap 40','encoding keyvalues2 4 format vmap 40')
 if 'models/kat_spaceport/' in t:raise ValueError('old geometry reference leaked')
 check=parse(t);assert sum(cls(e)=='prop_static' for e in walk(check))==len(props)-1
 dst.write_text(t,encoding='utf8');print(json.dumps(receipt))
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--rows',required=True);a.add_argument('--outmap',required=True);a.add_argument('--models',default='E:/df-v24-build-20261106/geometry-work/models.jsonl');a.add_argument('--template',default='E:/spaceport-kat-rebuild-20261105/fixed-build/content/kat/maps/kat_phys_q001.vmap');generate(a.parse_args())
