from pathlib import Path
import subprocess,os,json,time
w=Path('E:/df-v24-build-20261106/loot-ladder-work')
env=os.environ.copy();env['TEMP']=env['TMP']=str(w/'temp');env['DOTNET_CLI_HOME']=str(w/'dotnet-home');env['DOTNET_CLI_TELEMETRY_OPTOUT']='1'
commands=[['C:/Program Files/dotnet/dotnet.exe','build',str(w/'ExtensionSampler/ExtensionSampler.csproj'),'-c','Release','-o',str(w/'extension-sampler-bin'),'--nologo'],['C:/Program Files/dotnet/dotnet.exe',str(w/'extension-sampler-bin/ExtensionSampler.dll'),str(w/'extension-samples'),str(w/'extension-pairs.json')]]
with (w/'extension-sampler.log').open('a',encoding='utf8') as log:
 for cmd in commands:
  p=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,env=env)
  (w/'extension-sampler-process.json').write_text(json.dumps(dict(pid=p.pid,parent=os.getpid(),command=cmd,time=time.time())))
  rc=p.wait()
  if rc:break
(w/'extension-sampler-exit.json').write_text(json.dumps(dict(exitCode=rc,time=time.time())))
