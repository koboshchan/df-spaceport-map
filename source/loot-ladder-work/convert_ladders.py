import bpy,json,hashlib,sys,time,traceback,struct
from pathlib import Path
from mathutils import Matrix
R=Path('E:/df-v24-build-20261106'); W=R/'loot-ladder-work'; S=Path('E:/df-extract-20261105/meshes'); O=R/'content/kat/models/df_v24'
W.mkdir(parents=True,exist_ok=True);O.mkdir(parents=True,exist_ok=True)
H='<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:modeldoc36:version{972dada4-b828-45a4-bb93-7795cf0585da} -->\n'
def ident(s,p):return p+hashlib.sha256(s.encode()).hexdigest()[:16]
def q(s):return json.dumps(s,ensure_ascii=False)
material_map=json.loads((R/'material-work/material-map.json').read_text(encoding='utf8'))
rows=json.loads(Path('E:/df-extract-20261105/placements/validation/door-ladder-audit/ladder-solid-collision-manifest.json').read_text())['rows']
placements=[]
for row in rows:
 mid=ident(row['actor'],'lc_')
 bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
 boxes=row['sourceCollisionBoxes']
 center=[sum(b['worldCornersCS2'][0][k] for b in boxes)/len(boxes) for k in range(3)]
 vertices=[];faces=[]
 for box in boxes:
  corners=box['worldCornersCS2'];base=len(vertices);vertices += [[v[k]-center[k] for k in range(3)]for v in corners]
  # Corner order is product(x,y,z), outward facing six quads. Keep each disconnected OBB exact.
  for f in [(0,1,3,2),(4,6,7,5),(0,4,5,1),(2,3,7,6),(0,2,6,4),(1,5,7,3)]:faces.append(tuple(base+i for i in f))
 mesh=bpy.data.meshes.new(mid);mesh.from_pydata(vertices,[],faces);mesh.update()
 ob=bpy.data.objects.new(mid,mesh);bpy.context.collection.objects.link(ob);ob.select_set(True);bpy.context.view_layer.objects.active=ob
 mat=bpy.data.materials.new('ladder_source_obb');mesh.materials.append(mat)
 used={'ladder_source_obb':'__source_obb_nodraw__'}
 material_map['__source_obb_nodraw__']='materials/tools/toolsnodraw.vmat'
 bpy.ops.export_scene.fbx(filepath=str(O/(mid+'.fbx')),global_scale=1.0,apply_unit_scale=False,apply_scale_options='FBX_SCALE_ALL',axis_forward='-X',axis_up='Z',use_space_transform=False,bake_space_transform=False,use_selection=True,object_types={'MESH'},use_mesh_modifiers=False,use_mesh_modifiers_render=False,bake_anim=False,add_leaf_bones=False,use_custom_props=False,use_triangles=True,use_tspace=False,mesh_smooth_type='FACE',path_mode='STRIP',embed_textures=False)
 remaps=',\n'.join('{ from = '+q(k)+' to = '+q(material_map[used[k]].removeprefix('kat/'))+' }' for k in used)
 text=H+'{ rootNode = { _class = "RootNode" children = [ { _class = "RenderMeshList" children = [ { _class = "RenderMeshFile" name = "mesh" filename = '+q('models/df_v24/'+mid+'.fbx')+' import_scale = 1.0 import_filter = { exclude_by_default = false exception_list = [] } } ] }, { _class = "MaterialGroupList" children = [ { _class = "DefaultMaterialGroup" name = "default" remaps = [ '+remaps+' ] use_global_default = false global_default_material = "" } ] }, { _class = "PhysicsShapeList" children = [ { _class = "PhysicsMeshFromRender" parent_bone = "" surface_prop = "default" collision_prop = "default" tool_material = "" renderMeshList = [] } ] leave_body_collision_unmodified = false } ] model_archetype = "" primary_associated_entity = "" anim_graph_name = "" document_sub_type = "ModelDocSubType_None" } }'
 (O/(mid+'.vmdl')).write_text(text,encoding='utf8')
 result=dict(id=mid,objectPath=row['actor']+'#sourceOBB',model='models/df_v24/'+mid+'.vmdl',sourceBoxes=len(boxes),vertices=len(vertices),polygons=len(faces),collisionMode='exact closed box surfaces from source simple collision OBBs; native compiled/runtime verification pending',source='ladder-solid-collision-manifest.json',centerCS2=center)
 (W/(mid+'.json')).write_text(json.dumps(result,indent=2))
 with (W/'ladder-models.jsonl').open('a') as f:f.write(json.dumps(result)+'\n')
 placements.append(dict(objectPath=result['objectPath'],actor=row['actor'],webID=row['webID'],model=result['model'],matrixCS2=[[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]],positionCS2=center,bakedCS2LocalTransform=True,collisionEnabled=True,sourceBoxCount=len(boxes),sourceOBBs=boxes))
(W/'ladder-collision-placements.jsonl').write_text(''.join(json.dumps(v)+'\n'for v in placements))
(W/'ladder-conversion-done.json').write_text(json.dumps(dict(ladders=len(rows),sourceBoxes=sum(len(v['sourceCollisionBoxes'])for v in rows),preservedOBBGeometry=True,compiledPhysicsVerified=False)))
