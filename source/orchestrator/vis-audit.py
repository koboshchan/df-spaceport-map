import pathlib,json,hashlib,subprocess,datetime,traceback
from srctools.vpk import VPK
R=pathlib.Path('E:/df-v24-build-20261106');W=R/'visibility-crash-audit';W.mkdir(exist_ok=True)
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def save(n,x):(W/n).write_text(json.dumps(x,indent=2))
save('started.json',{'utc':now(),'readOnlyInputs':True,'noLiveAccess':True})
try:
 rows=[]
 for stem in ['df_spaceport_v24']+['df_spaceport_v24_part'+str(i) for i in range(6)]:
  p=R/'game/kat/maps'/(stem+'.vpk');v=VPK(p);D=W/stem;D.mkdir(exist_ok=True);entries=[]
  for key in v.filenames():
   e=v[key];r={'key':key,'bytes':e.size}
   if any(s in key.lower() for s in ['visibility','occlusion']) or key.endswith(('.vwrld_c','.vents_c','.vvis_c','.vwnod_c')):
    b=e.read();assert e.verify();r.update(sha256=hashlib.sha256(b).hexdigest(),CRCVerified=True)
    # Avoid dumping large render node meshes; list nodes, decode world/entity/visibility metadata.
    if not key.endswith('.vwnod_c'):
     o=D/pathlib.Path(key).name;o.write_bytes(b)
     q=subprocess.run(['E:/spaceport-kat-rebuild-20261105/vrf/Source2Viewer-CLI.exe','-i',str(o),'-a'],capture_output=True,text=True)
     o.with_suffix('.dump.txt').write_text(q.stdout+'\nSTDERR\n'+q.stderr,encoding='utf8');r.update(parserExit=q.returncode,dump=str(o.with_suffix('.dump.txt')))
   entries.append(r)
  receipt=R/'compile-work'/(stem+'-process.json')
  rows.append({'map':stem,'archive':str(p),'archiveSHA256':hashlib.sha256(p.read_bytes()).hexdigest(),'compileProcessReceipt':json.loads(receipt.read_text()) if receipt.exists() else None,'entries':entries})
  save('inventory.json',rows)
 save('exit.json',{'exitCode':0,'utc':now()})
except:save('failure.json',{'utc':now(),'error':traceback.format_exc()});raise
