import json,numpy as np
from pathlib import Path
from io_scene_fbx import parse_fbx
w=Path('E:/df-v24-build-20261106/loot-ladder-work');root=Path('E:/df-v24-build-20261106/content/kat')
reports=[]
for line in(w/'ladder-collision-placements.jsonl').read_text(encoding='utf8').splitlines():
 row=json.loads(line);p=root/row['model'].replace('.vmdl','.fbx');tree,ver=parse_fbx.parse(str(p))
 def find(node,id):
  return [node]if node.id==id else sum((find(x,id)for x in node.elems),[])
 arrays=find(tree,b'Vertices');assert len(arrays)==1
 got=np.array(arrays[0].props[0]).reshape(-1,3)
 want=np.array([[v[k]-row['positionCS2'][k]for k in range(3)]for b in row['sourceOBBs']for v in b['worldCornersCS2']])
 assert got.shape==want.shape
 err=float(np.abs(got-want).max())
 reports.append(dict(model=row['model'],sourceBoxCount=row['sourceBoxCount'],vertices=len(got),maxRawFBXLocalError=err,rawFBXBounds=[got.min(0).tolist(),got.max(0).tolist()],expectedBounds=[want.min(0).tolist(),want.max(0).tolist()],identityBasisVerified=err<.001))
(w/'ladder-fbx-local-basis-proof.json').write_text(json.dumps(dict(allPass=all(v['identityBasisVerified']for v in reports),rows=reports),indent=2))
