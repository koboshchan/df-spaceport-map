import bpy,json,hashlib,sys,time,traceback,struct
from pathlib import Path
from mathutils import Matrix
R=Path('E:/df-v24-build-20261106'); W=R/'geometry-work'; S=Path('E:/df-extract-20261105/meshes'); O=R/'content/kat/models/df_v24'
W.mkdir(parents=True,exist_ok=True);O.mkdir(parents=True,exist_ok=True)
H='<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:modeldoc36:version{972dada4-b828-45a4-bb93-7795cf0585da} -->\n'
def ident(s,p):return p+hashlib.sha256(s.encode()).hexdigest()[:16]
def q(s):return json.dumps(s,ensure_ascii=False)
material_map=json.loads((R/'material-work/material-map.json').read_text(encoding='utf8'))
records={}
for root in [S]+[S/'parallel'/('shard-'+str(i)) for i in range(8)]:
 for line in (root/'exports.jsonl').read_text(encoding='utf8').splitlines():
  x=json.loads(line)
  if x.get('objectPath') in records:assert records[x['objectPath']]['outputs']==x['outputs']
  records[x['objectPath']]=x
(W/'source-inventory.json').write_text(json.dumps({'roots':9,'records':len(records),'basis':'Blender glTF import UE(X,-Y,Z)/100; local Ãƒâ€”36; preserve winding','modelId':'m_+sha256(exact objectPath)[:16]','materialId':'mat_+sha256(exact material objectPath)[:16]'},indent=2))
rows=list(records.values())
rows.sort(key=lambda x:(0 if x['name']=='SM_H_Building_FutureTech_Dock_03b' else 1,x['objectPath']))
if '--pilot' in sys.argv:rows=rows[:1]
for x in rows:
 mid=ident(x['objectPath'],'m_');receipt=W/(mid+'.json')
 if receipt.exists():continue
 try:
  bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
  for bank in [bpy.data.meshes,bpy.data.materials]:
   for data in list(bank):
    if data.users==0:bank.remove(data)
  p=S/x['outputs'][0]['relative'];assert p.exists(),str(p)
  raw=p.read_bytes(); jl=struct.unpack_from('<I',raw,12)[0]; gj=json.loads(raw[20:20+jl])
  primitive_mats=[pr.get('material') for me in gj['meshes'] for pr in me['primitives']]
  assert len(primitive_mats)==len(x['sections']),(len(primitive_mats),len(x['sections']))
  tokenrefs={};gmatrefs={}
  for gi,section in zip(primitive_mats,x['sections']):
   slots=[v for v in x['slots'] if v['index']==section['MaterialIndex']]
   assert len(slots)==1,section
   mat=slots[0]['material']
   if not mat:raise ValueError('EXPLICIT_UNRESOLVED_SOURCE_MATERIAL slot '+str(section['MaterialIndex']))
   assert gi is not None,'primitive has no source material'
   if gi in gmatrefs:assert gmatrefs[gi]==mat,'GLB material reused across distinct source identities'
   gmatrefs[gi]=mat
   token=ident(mat,'mat_');tokenrefs[token]=mat;gj['materials'][gi]['name']=token
  jb=json.dumps(gj,separators=(',',':')).encode();jb+=b' '*((-len(jb))%4)
  tail=raw[20+jl:];new=struct.pack('<III',0x46546c67,2,20+len(jb)+len(tail))+struct.pack('<II',len(jb),0x4e4f534a)+jb+tail
  tmp=W/'temp'/(mid+'.glb');tmp.write_bytes(new)
  bpy.ops.import_scene.gltf(filepath=str(tmp))
  used={};obs=[]
  for ob in list(bpy.context.scene.objects):
   if ob.type!='MESH':continue
   obs.append(ob);ob.data.transform(Matrix.Scale(36,4)@ob.matrix_world);ob.matrix_world=Matrix.Identity(4)
   for slot in ob.material_slots:
    if not slot.material:continue
    token=slot.material.name.split('.')[0]
    assert token in tokenrefs,token
    slot.material.name=token;used[token]=tokenrefs[token]
   ob.select_set(True)
  assert obs
  verts=sum(len(ob.data.vertices) for ob in obs);faces=sum(len(ob.data.polygons) for ob in obs)
  mn=[min(v.co[k] for ob in obs for v in ob.data.vertices) for k in range(3)]
  mx=[max(v.co[k] for ob in obs for v in ob.data.vertices) for k in range(3)]
  bpy.ops.export_scene.fbx(filepath=str(O/(mid+'.fbx')),global_scale=1.0,apply_unit_scale=False,apply_scale_options='FBX_SCALE_ALL',axis_forward='-X',axis_up='Z',use_space_transform=False,bake_space_transform=False,use_selection=True,object_types={'MESH'},use_mesh_modifiers=False,use_mesh_modifiers_render=False,bake_anim=False,add_leaf_bones=False,use_custom_props=False,use_triangles=True,use_tspace=False,mesh_smooth_type='FACE',path_mode='STRIP',embed_textures=False)
  remaps=',\n'.join('{ from = '+q(k)+' to = '+q(material_map[used[k]].removeprefix('kat/'))+' }' for k in used)
  text=H+'{ rootNode = { _class = "RootNode" children = [ { _class = "RenderMeshList" children = [ { _class = "RenderMeshFile" name = "mesh" filename = '+q('models/df_v24/'+mid+'.fbx')+' import_scale = 1.0 import_filter = { exclude_by_default = false exception_list = [] } } ] }, { _class = "MaterialGroupList" children = [ { _class = "DefaultMaterialGroup" name = "default" remaps = [ '+remaps+' ] use_global_default = false global_default_material = "" } ] }, { _class = "PhysicsShapeList" children = [ { _class = "PhysicsMeshFromRender" parent_bone = "" surface_prop = "default" collision_prop = "default" tool_material = "" renderMeshList = [] } ] leave_body_collision_unmodified = false } ] model_archetype = "" primary_associated_entity = "" anim_graph_name = "" document_sub_type = "ModelDocSubType_None" } }'
  (O/(mid+'.vmdl')).write_text(text,encoding='utf8')
  result={'id':mid,'objectPath':x['objectPath'],'source':str(p),'sourceSHA256':x['outputs'][0]['sha256'],'model':'models/df_v24/'+mid+'.vmdl','materials':used,'vertices':verts,'polygons':faces,'bounds':[mn,mx],'collisionMode':'render-triangle candidate; component policy must select collision before final map','basis':'local imported glTF Ãƒâ€”36, no reflection or winding change'}
  receipt.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
  with (W/'models.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(result,ensure_ascii=False)+'\n')
  print('DONE',mid,x['name'],verts,faces,flush=True)
 except Exception:
  with (W/'errors.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps({'objectPath':x['objectPath'],'error':traceback.format_exc()})+'\n')
  traceback.print_exc()
(W/('pilot-done.json' if '--pilot' in sys.argv else 'conversion-done.json')).write_text(json.dumps({'requested':len(rows),'completedReceipts':len(list(W.glob('m_*.json'))),'time':time.time()}))
