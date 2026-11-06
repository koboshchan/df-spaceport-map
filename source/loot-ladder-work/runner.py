import subprocess,json,time,os
from pathlib import Path
w=Path('E:/df-v24-build-20261106/loot-ladder-work')
(w/'process.json').write_text(json.dumps(dict(pid=os.getpid(),parent=os.getppid(),start=time.time())))
env=os.environ.copy()
for k,sub in [('TEMP','temp'),('TMP','temp'),('BLENDER_USER_CONFIG','blender-config'),('BLENDER_USER_SCRIPTS','blender-scripts'),('BLENDER_USER_DATAFILES','blender-data')]:
 p=w/sub;p.mkdir(exist_ok=True);env[k]=str(p)
with (w/'loot.log').open('a',encoding='utf8') as log:
 p=subprocess.Popen(['E:/spaceport-manifest-task/blender-4.4.3-windows-x64/blender.exe','-b','--factory-startup','-t','4','--python',str(w/'convert_loot.py')],stdout=log,stderr=subprocess.STDOUT,env=env)
 (w/'blender-process.json').write_text(json.dumps(dict(pid=p.pid,parent=os.getpid(),start=time.time())))
 rc=p.wait()
(w/'exit.json').write_text(json.dumps(dict(exitCode=rc,end=time.time())))
