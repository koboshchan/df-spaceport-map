from pathlib import Path
import subprocess,os,json,time
w=Path('E:/df-v24-build-20261106/loot-ladder-work')
env=os.environ.copy();env['TEMP']=env['TMP']=str(w/'temp');env['DOTNET_CLI_HOME']=str(w/'dotnet-home');env['DOTNET_CLI_TELEMETRY_OPTOUT']='1'
commands=[['C:/Program Files/dotnet/dotnet.exe','build',str(w/'DecalPixels/DecalPixels.csproj'),'-c','Release','-o',str(w/'decal-pixels-bin'),'--nologo'],['C:/Program Files/dotnet/dotnet.exe',str(w/'decal-pixels-bin/DecalPixels.dll'),str(w/'decal-pixels'),str(w/'decal-targets.json')]]
with (w/'decal-pixels.log').open('a',encoding='utf8') as log:
 for cmd in commands:
  p=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,env=env)
  (w/'decal-pixels-process.json').write_text(json.dumps(dict(pid=p.pid,parent=os.getpid(),command=cmd,time=time.time())))
  rc=p.wait()
  if rc==0 and 'build' in cmd:
   import shutil
   for dll in Path('E:/df-extract-20261105/tools/LootDump/bin/Release/net10.0').glob('*.dll'):
    if not (w/'decal-pixels-bin'/dll.name).exists():shutil.copy2(dll,w/'decal-pixels-bin'/dll.name)
  if rc:break
(w/'decal-pixels-exit.json').write_text(json.dumps(dict(exitCode=rc,time=time.time())))
