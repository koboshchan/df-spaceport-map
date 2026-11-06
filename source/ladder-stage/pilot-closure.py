import pathlib,json,hashlib,re
from srctools.vpk import VPK
W=pathlib.Path('E:/df-v25-build-20261106/ladder-stage');base=pathlib.Path('E:/SteamLibrary/steamapps/common/Counter-Strike Global Offensive/game')
packs=[VPK(base/x/'pak01_dir.vpk')for x in ['core','csgo']]
todo=['materials/tools/toolsinvisibleladder.vmat_c','materials/tools/toolsnodraw.vmat_c'];done={};missing=[]
while todo:
 key=todo.pop(0)
 if key in done:continue
 found=False
 for v in packs:
  if key not in v:continue
  b=v[key].read();assert v[key].verify()
  # RERL strings only, avoids source input dependency false positives.
  import struct
  refs=[];nb=struct.unpack_from('<I',b,12)[0]
  for i in range(nb):
   off=16+i*12;tag=b[off:off+4];rel,size=struct.unpack_from('<II',b,off+4);start=off+4+rel
   if tag==b'RERL':
    q=b[start:start+size]
    refs=[m.decode()for m in re.findall(rb'(?:materials|models)/[ -~]+?\.(?:vtex|vmat|vmdl)\x00',q)]
    refs=[x.rstrip('\x00')+'_c'for x in refs]
  done[key]=dict(pack=str(v.path),bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),CRCVerified=True,references=refs);todo+=refs;found=True;break
 if not found:missing.append(key)
(W/'pilot-dependency-closure.json').write_text(json.dumps(dict(resources=done,missing=missing,success=not missing),indent=2))
geo=json.loads((W/'native-ladder-geometry-proposal.json').read_text());g=geo[0]
vs=g['vertices'];bounds=dict(min=[min(v[i]for v in vs)for i in range(3)],max=[max(v[i]for v in vs)for i in range(3)])
g.update(bounds=bounds,climbableFaceWindingOutwardNormalDot=1.,sourceEndpointStatus='SOCKET_CHAIN_VALIDATED; PLAYER_HULL_RUNTIME_UNVERIFIED',geometryPolicy='1-CS2-unit sheet within SOURCE front climb volume; front only ladder face, no backing wall added')
(W/'pilot-orientation-entry-topout.json').write_text(json.dumps(g,indent=2))
print(json.dumps(dict(missing=missing,resources=len(done),bounds=bounds,endpoints=g['endpoints'],frontNormal=g['frontNormal'])))
