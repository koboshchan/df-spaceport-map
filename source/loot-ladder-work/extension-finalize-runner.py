import subprocess,json,time,os
from pathlib import Path
w=Path('E:/df-v24-build-20261106/loot-ladder-work')
(w/'extension-finalize-process.json').write_text(json.dumps(dict(pid=os.getpid(),parent=os.getppid(),start=time.time())))
env=os.environ.copy()
for k,sub in [('TEMP','temp'),('TMP','temp'),('BLENDER_USER_CONFIG','blender-config'),('BLENDER_USER_SCRIPTS','blender-scripts'),('BLENDER_USER_DATAFILES','blender-data')]:
 p=w/sub;p.mkdir(exist_ok=True);env[k]=str(p)
with (w/'extension-finalize.log').open('a',encoding='utf8') as log:
 commands=[['E:/spaceport-kat-rebuild-20261105/material-venv/Scripts/python.exe',str(w/'bake_extension_states.py')],['E:/spaceport-manifest-task/blender-4.4.3-windows-x64/blender.exe','-b','--factory-startup','-t','4','--python',str(w/'convert_extension.py')]]
 for cmd in commands:
  p=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,env=env)
  rc=p.wait()
  if rc:break
 if rc==0:
  rc=subprocess.run(['E:/spaceport-kat-rebuild-20261105/material-venv/Scripts/python.exe',str(w/'finalize_placements.py')],stdout=log,stderr=subprocess.STDOUT,env=env).returncode
(w/'extension-finalize-exit.json').write_text(json.dumps(dict(exitCode=rc,end=time.time())))
