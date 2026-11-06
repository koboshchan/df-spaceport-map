import pathlib,json,hashlib,subprocess
from srctools.vpk import VPK
W=pathlib.Path('E:/df-v25-build-20261106/ladder-stage/native-compiled-audit');W.mkdir(exist_ok=True)
P=pathlib.Path('E:/df-v25-build-20261106/orchestrator/ladder-pilot')
v=VPK(P/'game/kat/maps/df_v25_native_ladder_pilot.vpk');rows=[]
cli='E:/spaceport-kat-rebuild-20261105/vrf/Source2Viewer-CLI.exe'
for key in v.filenames():
 b=v[key].read();assert v[key].verify();row=dict(resource=key,bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),CRCVerified=True)
 if any(key.endswith(x)for x in ['world_physics.vmdl_c','.vwnod_c','.vwrld_c']):
  p=W/pathlib.Path(key).name;p.write_bytes(b)
  result=subprocess.run([cli,'-i',str(p),'-a'],capture_output=True,text=True,check=True);p.with_suffix('.dump.txt').write_text(result.stdout,encoding='utf8');row['dump']=str(p.with_suffix('.dump.txt'))
 rows.append(row)
(W/'vpk-resource-closure.json').write_text(json.dumps(rows,indent=2))
for name in ['process.json','exit.json','compiler.log']:
 (W/('central-'+name)).write_bytes((P/name).read_bytes())
print(json.dumps(rows,indent=2))
