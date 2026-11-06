import sys,json,re
from pathlib import Path
from io_scene_fbx import parse_fbx
R=Path('E:/df-v24-build-20261106');W=R/'geometry-work';O=R/'content/kat/models/df_v24';ST=W/'material-binding-fix-v1'
ST.mkdir(exist_ok=True)
def read(p):
 root,ver=parse_fbx.parse(str(p))
 objects=next(x for x in root.elems if x.id==b'Objects')
 cons=next(x for x in root.elems if x.id==b'Connections')
 mats={};mods={}
 for e in objects.elems:
  if e.id==b'Material':mats[e.props[0]]=e.props[1].split(b'\x00')[0].decode()
  if e.id==b'Model':mods[e.props[0]]=e.props[1].split(b'\x00')[0].decode()
 slots={}
 for c in cons.elems:
  if len(c.props)>=3 and c.props[1] in mats and c.props[2] in mods:
   slots.setdefault(mods[c.props[2]],[]).append(mats[c.props[1]])
 return slots
base={x['objectPath']:x for x in [json.loads(l) for l in (W/'models.jsonl').read_text(encoding='utf8').splitlines()]}
rows=[]
for name in ['exact-affine-models.json','precision-affine-models.json','spline-models.json']:
 rows+=json.loads((W/name).read_text(encoding='utf8'))
audit=[];patch=[]
for row in rows:
 mid=row['id'];p=O/(mid+'.fbx');derived=read(p)
 # source identity from row, or exact component request for spline.
 mesh=row.get('meshObjectPath')
 if mesh is None:
  requests=json.loads((R/'component-work/spline-remediation.json').read_text(encoding='utf8'))
  mesh=next(x['meshObjectPath'] for x in requests if x['objectPath']==row['objectPath'])
 b=base[mesh];original=read(O/(b['id']+'.fbx'))
 assert list(derived)==list(original),(mid,list(derived),list(original))
 text=(O/(mid+'.vmdl')).read_text(encoding='utf8')
 remaps=dict(re.findall(r'from\s*=\s*"([^"]+)"\s+to\s*=\s*"([^"]+)"',text))
 pairs={}
 for node,names in derived.items():
  source=original[node];assert len(source)==len(names),(mid,node)
  for actual,canonical in zip(names,source):
   assert canonical in b['materials'],(mid,canonical)
   assert canonical in remaps,(mid,canonical)
   if actual in pairs:assert pairs[actual]==remaps[canonical]
   pairs[actual]=remaps[canonical]
 missing={a:t for a,t in pairs.items() if remaps.get(a)!=t}
 if missing:
  extra=' '.join('{ from = '+json.dumps(a)+' to = '+json.dumps(t)+' }' for a,t in missing.items())
  text=text.replace('remaps = [','remaps = [ '+extra+' ',1)
  target=ST/(mid+'.vmdl');target.write_text(text,encoding='utf8')
  patch.append({'id':mid,'source':str(O/(mid+'.vmdl')),'staged':str(target),'exactAdditionalRemaps':missing,'derivedFBX':str(p),'originalFBX':str(O/(b['id']+'.fbx'))})
 audit.append({'id':mid,'slotsByNode':derived,'sourceSlotsByNode':original,'missingRemaps':missing})
(ST/'derived-audit.json').write_text(json.dumps(audit,indent=2),encoding='utf8')
(ST/'patch-manifest.json').write_text(json.dumps(patch,indent=2),encoding='utf8')
print('DERIVED',len(rows),'PATCHES',len(patch))
loot=[]
for root in [R/'content/kat/models']:
 for p in root.rglob('*.fbx'):
  if p.stem.startswith(('a_','s_','m_')):continue
  vm=p.with_suffix('.vmdl')
  if not vm.exists():continue
  text=vm.read_text(encoding='utf8');maps=dict(re.findall(r'from\s*=\s*"([^"]+)"\s+to\s*=\s*"([^"]+)"',text))
  bindings=read(p);names=set(n for ns in bindings.values() for n in ns)
  loot.append({'fbx':str(p),'bindings':bindings,'unmapped':sorted(names-set(maps))})
(ST/'other-model-material-audit.json').write_text(json.dumps(loot,indent=2),encoding='utf8')
print('OTHER',len(loot),'UNMAPPED',sum(bool(x['unmapped']) for x in loot))
