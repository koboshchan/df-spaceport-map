import subprocess
subprocess.run(['powershell','-NoProfile','-Command','Wait-Process -Id 115868 -ErrorAction SilentlyContinue'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
from pathlib import Path
import subprocess,os,json,time
w=Path('E:/df-v24-build-20261106/geometry-work');env=os.environ.copy()
for key,name in [('TEMP','temp'),('TMP','temp'),('BLENDER_USER_CONFIG','blender-config'),('BLENDER_USER_SCRIPTS','blender-scripts'),('BLENDER_USER_DATAFILES','blender-data'),('PYTHONPYCACHEPREFIX','pycache')]:env[key]=str(w/name)
with (w/'precision-affine.log').open('wb') as log:
 p=subprocess.Popen(['C:/Program Files/Blender Foundation/Blender 4.4/blender.exe','--background','--factory-startup','--disable-autoexec','--python-exit-code','1','--python',str(w/'precision_affine.py')],cwd=w,env=env,stdout=log,stderr=subprocess.STDOUT)
 (w/'precision-affine-process.json').write_text(json.dumps({'pid':p.pid,'start':time.time()}))
 code=p.wait()
 (w/'precision-affine-exit.json').write_text(json.dumps({'pid':p.pid,'exit':code,'end':time.time()}))
 print('EXIT',code)
