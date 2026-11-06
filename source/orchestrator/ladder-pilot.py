import pathlib,json,hashlib,subprocess,os,datetime,traceback
R=pathlib.Path('E:/df-v25-build-20261106/orchestrator/ladder-pilot');S=pathlib.Path('E:/df-v25-build-20261106/ladder-stage');I=pathlib.Path('E:/SteamLibrary/steamapps/common/Counter-Strike Global Offensive')
R.mkdir(parents=True,exist_ok=True)
def save(n,x):(R/n).write_text(json.dumps(x,indent=2))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
try:
 freeze=S/'pilot-FROZEN.json';assert sha(freeze)=='dd51cb20a568565476451fe4c37f5da7e8eeef1e472f4a79182cd4144db4c352'
 f=json.loads(freeze.read_text());assert f['frozen'];assert all(sha(S/n)==v['sha256'] for n,v in f['files'].items());(R/'frozen-receipt.json').write_bytes(freeze.read_bytes())
 m=json.loads((S/'pilot-input-manifest.json').read_text());src=pathlib.Path(m['input']);assert sha(src)==m['sha256']
 assert 'resourcecompiler.exe' not in subprocess.run(['tasklist','/FO','CSV','/NH'],capture_output=True,text=True).stdout.lower(),'RC already active'
 C=R/'content/kat';G=R/'game/kat';(C/'maps').mkdir(parents=True,exist_ok=True);G.mkdir(parents=True,exist_ok=True)
 p=C/'maps'/src.name;p.write_bytes(src.read_bytes());assert sha(p)==m['sha256']
 # Independent isolated mount uses only stock installed resources, never live/v24 content.
 stock=(pathlib.Path('E:/df-v24-build-20261106/game/kat/gameinfo.gi')).read_text()
 stock=stock # Relative kat/csgo/core resolve only within isolated game root; stock mounts are junctions.
 (G/'gameinfo.gi').write_text(stock)
 for n in ['pilot-input-manifest.json','pilot-dependency-closure.json','pilot-orientation-entry-topout.json']:(R/('frozen-'+n)).write_bytes((S/n).read_bytes())
 e=os.environ.copy()
 for k in ['TEMP','TMP','LOCALAPPDATA','APPDATA','USERPROFILE','HOME']:
  d=R/('env-'+k.lower());d.mkdir(exist_ok=True);e[k]=str(d)
 cmd=[str(I/'game/bin/win64/resourcecompiler.exe'),'-i',str(p),'-game',str(G),'-nop4','-fshallow','-world','-entities','-phys','-nobakedlighting']
 with (R/'compiler.log').open('w') as log:
  q=subprocess.Popen(cmd,cwd=R,env=e,stdout=log,stderr=subprocess.STDOUT);save('process.json',{'pid':q.pid,'wrapperPID':os.getpid(),'command':cmd,'sourceSHA256':sha(p),'runtimeVerified':False});rc=q.wait()
 save('exit.json',{'exitCode':rc,'outputs':[{'path':str(f),'bytes':f.stat().st_size,'sha256':sha(f)} for f in G.rglob('*') if f.is_file()],'runtimeVerified':False})
except BaseException:
 save('failure.json',{'error':traceback.format_exc()});raise
