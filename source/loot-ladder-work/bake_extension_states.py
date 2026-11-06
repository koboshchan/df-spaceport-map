import pathlib,json,struct,importlib.util,numpy as np,hashlib,os
R=pathlib.Path('E:/df-extract-20261105/loot-skeletal')
spec=importlib.util.spec_from_file_location('b',R/'bake-static.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
W=pathlib.Path('E:/df-v24-build-20261106/loot-ladder-work');O=W/'extension-samples';D=W/'extension-static';D.mkdir(exist_ok=True)
rows=[]
samples=[json.loads(l) for l in (O/'samples.jsonl').read_text().splitlines()]
for x in samples:
 # Reject wrong skeleton mapping even if partial sampling worked.
 if x['missing']:continue
 pkg=x['mesh']; matches=list((W/'extension-export').glob(pkg[:-7]+'.glb'))
 if len(matches)!=1:
  rows.append(dict(mesh=pkg,status='unresolved-source',matches=[str(p) for p in matches]));continue
 src=matches[0];g,data=b.read(src);nodes={n.get('name'):i for i,n in enumerate(g['nodes'])};allok=True;maxerr=0
 def node(p):
  q=p['rotation'];t=p['translation'];s=p['scale']
  return dict(rotation=[q[0],q[2],q[1],-q[3]],translation=[t[0]*.01,t[2]*.01,t[1]*.01],scale=[s[0],s[2],s[1]])
 for bone in x['bones']:
  if bone['name'] not in nodes:allok=False;break
  i=nodes[bone['name']];err=float(np.max(np.abs(b.local(g['nodes'][i])-b.local(node(bone['rest'])))));maxerr=max(maxerr,err)
  if err>1e-5:allok=False;break
 if not allok:
  rows.append(dict(mesh=pkg,status='unresolved-GLB-rest-basis',maxRestMatrixError=maxerr));continue
 for bone in x['bones']:
  n=g['nodes'][nodes[bone['name']]];n.pop('matrix',None);n.update(node(bone['frames'][0]))
 jb=json.dumps(g,separators=(',',':')).encode();jb+=b' '*((-len(jb))%4);data+=b'\0'*((-len(data))%4)
 stem=pathlib.Path(pkg).stem;temp=O/'posed-skinned'/ (stem+'-'+hashlib.sha256(x['animation'].encode()).hexdigest()[:8]+'.glb');temp.parent.mkdir(exist_ok=True)
 temp.write_bytes(struct.pack('<III',0x46546c67,2,28+len(jb)+len(data))+struct.pack('<II',len(jb),0x4e4f534a)+jb+struct.pack('<II',len(data),0x004e4942)+data)
 dst=D/temp.name
 report=b.bake(temp,dst)
 rows.append(dict(mesh=pkg,animation=x['animation'],status='source-idle-frame0-baked',refEqual=x['refEqual'],maxRestMatrixError=maxerr,report=report))
(D/'report.json').write_text(json.dumps(dict(pid=os.getpid(),rows=rows),indent=2))
print(json.dumps([(x['mesh'],x['status']) for x in rows]))
