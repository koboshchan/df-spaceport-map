import bpy,json,hashlib
from pathlib import Path
from mathutils import Matrix,Vector
R=Path('E:/df-v24-build-20261106');W=R/'geometry-work';O=R/'content/kat/models/df_v24'
rows=json.loads((R/'component-work/precision-affine-bake-requests.json').read_text(encoding='utf8'))
models={x['objectPath']:x for x in [json.loads(l) for l in (W/'models.jsonl').read_text(encoding='utf8').splitlines()]}
out=[]
for row in rows:
 ident=row['objectPath']+'#'+str(row.get('instanceIndex'))
 mid='a_'+hashlib.sha256(ident.encode()).hexdigest()[:16]
 b=models[row['meshObjectPath']]
 bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
 bpy.ops.import_scene.fbx(filepath=str(O/(b['id']+'.fbx')),use_anim=False)
 obs=[ob for ob in bpy.context.scene.objects if ob.type=='MESH']
 linear=Matrix([r[:3] for r in row['matrixCS2'][:3]])@Matrix.Diagonal(Vector((1/0.36,-1/0.36,1/0.36)))
 det=linear.determinant();assert abs(det)>1e-15,('singular source',ident,det)
 maxerr=0.0
 for ob in obs:
  # Importer's FBX metadata rotation is intentionally not baked into source local vertex frame.
  for v in ob.data.vertices:
   original=v.co.copy();v.co=linear@original
   source=Vector((original.x/0.36,-original.y/0.36,original.z/0.36))
   expected=Matrix([r[:3] for r in row['matrixCS2'][:3]])@source
   maxerr=max(maxerr,(v.co-expected).length)
  if det<0:
   import bmesh
   bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.reverse_faces(bm,faces=list(bm.faces));bm.to_mesh(ob.data);bm.free()
  ob.data.update();ob.matrix_world=Matrix.Identity(4);ob.select_set(True)
 bpy.ops.export_scene.fbx(filepath=str(O/(mid+'.fbx')),global_scale=1,apply_unit_scale=False,apply_scale_options='FBX_SCALE_ALL',axis_forward='-X',axis_up='Z',use_space_transform=False,bake_space_transform=False,use_selection=True,object_types={'MESH'},use_mesh_modifiers=False,bake_anim=False,add_leaf_bones=False,use_triangles=True,mesh_smooth_type='FACE',path_mode='STRIP')
 text=(O/(b['id']+'.vmdl')).read_text(encoding='utf8').replace(b['id']+'.fbx',mid+'.fbx')
 (O/(mid+'.vmdl')).write_text(text,encoding='utf8')
 entry={'objectPath':row['objectPath'],'instanceIndex':row.get('instanceIndex'),'meshObjectPath':row['meshObjectPath'],'model':'models/df_v24/'+mid+'.vmdl','id':mid,'positionCS2':row['positionCS2'],'origin':row['positionCS2'],'angles':[0,0,0],'scale':[1,1,1],'bakedCS2LocalTransform':True,'collisionEnabled':row['collisionEnabled'],'linearDeterminant':det,'windingReversed':det<0,'maxLinearCheckError':maxerr,'bakeReason':row['bakeReason'],'localLinearMatrix':[list(v) for v in linear]}
 out.append(entry)
 (W/(mid+'.json')).write_text(json.dumps(entry,ensure_ascii=False,indent=2),encoding='utf8')
 print('AFFINE_DONE',mid,maxerr,flush=True)
 for bank in [bpy.data.meshes,bpy.data.materials]:
  for x in list(bank):
   if x.users==0:bank.remove(x)
(W/'precision-affine-models.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf8')
print('AFFINE_COMPLETE',len(out),flush=True)
