import pathlib,json,subprocess,hashlib
from srctools.vpk import VPK
W=pathlib.Path('E:/df-v25-build-20261106/ladder-stage');R=pathlib.Path('E:/df-v24-build-20261106');cli='E:/spaceport-kat-rebuild-20261105/vrf/Source2Viewer-CLI.exe';rows=[]
for archive in (R/'ready/maps').glob('*.vpk'):
 v=VPK(archive)
 for key in v.filenames():
  if not key.endswith('.vwnod_c'):continue
  b=v[key].read();p=W/'packed'/(archive.stem+'-'+pathlib.Path(key).name);p.write_bytes(b)
  s=subprocess.run([cli,'-i',str(p),'-a'],capture_output=True,text=True,check=True).stdout
  dump=p.with_suffix('.txt');dump.write_text(s,encoding='utf8');rows.append(dict(pack=str(archive),key=key,sha256=hashlib.sha256(b).hexdigest(),dump=str(dump),lcRefs=s.count('lc_')))
(W/'compiled-worldnodes.json').write_text(json.dumps(rows,indent=2))
