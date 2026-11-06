import pathlib,json,hashlib,importlib.util,io,re,uuid,collections,math
from srctools.dmx import Attribute,ValueType,Element
R=pathlib.Path("E:/df-v25-build-20261106");O=R/"orchestrator"
spec=importlib.util.spec_from_file_location("source_gen",R/"component-work/generate_vmap.py");g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
def ent(c,n,i):
 e=g.entity(c,n,i);e.uuid=uuid.uuid5(uuid.NAMESPACE_URL,"df-v25/"+n);return e
def props(e,values):
 for k,v in values.items():e["entity_properties"].val_elem[k]=str(v)
 return e
src=O/"spawn32-validated-source.json";assert hashlib.sha256(src.read_bytes()).hexdigest()=="2c47aaf9337f89e2ad85ae5a6042d148d785eee9b9f59f1f902d177c1906d54c"
sp=json.loads(src.read_text());assert sp["T"]==16 and sp["CT"]==16 and sp["unique"]==32 and sp["allEnabled"]
root=g.parse((R/"content/kat/maps/df_spaceport_v24.vmap").read_text(encoding="utf8"));world=root["world"].val_elem
parts=sorted((R/"content/kat/maps").glob("df_spaceport_v24_part*.vmap"));assert len(parts)==6
nodes=[ent("info_spawngroup_landmark","df_v25_origin",0)]
auto=props(ent("logic_auto","df_v25_load_children",1),{"spawnflags":1});connections=[]
for i,p in enumerate(parts):
 name="df_v25_child"+str(i);nodes.append(props(ent("info_spawngroup_load_unload",name,2+i),{"mapname":p.stem.replace("v24","v25"),"landmark":"df_v25_origin","autoactivate":1,"timeoutInterval":0}))
 con=Element("load_child"+str(i),"DmeConnectionData")
 for k,v in {"outputName":"OnMapSpawn","targetType":7,"targetName":name,"inputName":"StartSpawnGroupLoad","overrideParam":"","delay":0.0,"timesToFire":-1}.items():con[k]=v
 connections.append(con)
auto["connectionsData"]=Attribute.array("connectionsData",ValueType.ELEMENT,connections);nodes.append(auto)
sun=props(ent("light_environment","df_v25_sun",100000),{"brightness":3,"directlight":3,"skytexture":"df_v25_sky","castshadows":1,"enabled":1,"clientSideEntity":1,"baked_light_indexing":1});sun["angles"]=Attribute.angle("angles",[-45,135,0]);nodes.append(sun)
nodes.append(props(ent("env_sky","df_v25_sky",100100),{"skyname":"materials/skybox/sky_de_nuke.vmat","tint_color":"255 255 255","brightnessscale":"1.0"}))
seen=set();teams=collections.Counter()
for i,row in enumerate(sp["spawns"]):
 assert row["Enabled"] and row["groundReceipt"]["accepted"] and row["groundReceipt"]["clear"]
 pos=row["position"];assert tuple(pos) not in seen;seen.add(tuple(pos));teams[row["team"]]+=1
 e=props(ent(row["classname"],"df_v25_spawn"+str(i),100101+i),{"enabled":1,"priority":row["Priority"]});e["origin"]=Attribute.vec3("origin",pos);e["angles"]=Attribute.angle("angles",row.get("angles",[0,0,0]));nodes.append(e)
assert teams=={"T":16,"CT":16}
minxy=min(math.hypot(a[0]-b[0],a[1]-b[1]) for i,a in enumerate(seen) for j,b in enumerate(seen) if i<j);assert minxy>=64-1e-6
world["children"]=Attribute.array("children",ValueType.ELEMENT,nodes)
buf=io.BytesIO();root.export_kv2(buf,fmt_name="vmap",fmt_ver=40,unicode="silent",flat=True)
text=re.sub(r'"string"\s+"__U64__([^"]+)"',r'"uint64" "\1"',buf.getvalue().decode()).replace("encoding keyvalues2 1 format vmap 40","encoding keyvalues2 4 format vmap 40")
dst=O/"df_spaceport_v25-parent-candidate.vmap";dst.write_text(text,encoding="utf8")
parsed=g.parse(text);children=parsed["world"].val_elem["children"].iter_elem();counts=collections.Counter(x["entity_properties"].val_elem["classname"].val_str for x in children)
assert counts["env_sky"]==1 and counts["info_player_terrorist"]==16 and counts["info_player_counterterrorist"]==16 and counts["info_spawngroup_load_unload"]==6
receipt={"success":True,"candidate":str(dst),"SHA256":hashlib.sha256(dst.read_bytes()).hexdigest(),"counts":dict(counts),"spawnSnapshotSHA256":hashlib.sha256(src.read_bytes()).hexdigest(),"minXY":minxy,"exactPositions":True,"childNamesRebased":True,"sourceOnlyNotCompiled":True,"skySemanticMerge":True,"childVMAPsNotYetRebased":True,"bakeUnverified":True}
(O/"parent-candidate-verified.json").write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt))
