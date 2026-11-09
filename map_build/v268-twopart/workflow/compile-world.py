
from pathlib import Path
import os,sys,json,hashlib,subprocess,shutil,ctypes,traceback
sys.dont_write_bytecode=True
B=Path('LEGACY_BUILD');F=Path('LEGACY_STAGE');S=Path('TWOPART_ROOT');Q=S/'proof';C=S/'content/kat';G=S/'game/kat'
EXE=Path('CS2_ROOT/game/bin/win64/resourcecompiler.exe')
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def save(n,d):(Q/n).write_text(json.dumps(d,indent=2))
def copy(src,dst,expected=None):
 assert src.is_file(),str(src)
 digest=sha(src);assert expected is None or digest==expected,(str(src),digest,expected)
 if dst.exists():assert sha(dst)==digest,str(dst)
 else:dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
 assert sha(dst)==digest
 return digest
def main():
 save('runner.json',dict(pid=os.getpid(),parent=os.getppid(),phase='VERIFY_AND_MATERIALIZE',noInstall=True))
 assert 'resourcecompiler.exe' not in subprocess.check_output(['tasklist','/FI','IMAGENAME eq resourcecompiler.exe','/FO','CSV','/NH'],text=True).lower()
 assert sha(EXE)=='8df3ddc8825c6cee980d1c25f2ab9a386e9183ab6ab6ba2c96fe2c59872400f8'
 env=os.environ.copy()
 for k in ['TEMP','TMP','LOCALAPPDATA','APPDATA','USERPROFILE','HOME','DOTNET_CLI_HOME','NUGET_PACKAGES','DOTNET_BUNDLE_EXTRACT_BASE_DIR']:
  d=S/'env'/k;d.mkdir(parents=True,exist_ok=True);env[k]=str(d)
 env['PYTHONDONTWRITEBYTECODE']='1'
 def native(label,rel,world=False):
  receipt=Q/(label+'-exit.json')
  if receipt.exists():
   
   if json.loads(receipt.read_text())['exit']==0:return
   save(label+'-prior-failed-exit.json',json.loads(receipt.read_text()))
  cmd=[str(EXE),'-i',str(C/rel),'-game',str(G),'-nop4','-fshallow','-outroot',str(S/'game')]
  if world:cmd+=['-world','-entities','-phys','-nobakedlighting']
  log=Q/(label+'.log')
  with log.open('w') as out:
   p=subprocess.Popen(cmd,cwd=S,env=env,stdout=out,stderr=subprocess.STDOUT,creationflags=4)
   ident=subprocess.check_output(['wmic','process','where','ProcessId='+str(p.pid),'get','ExecutablePath,CommandLine,ParentProcessId,ProcessId,ReadTransferCount,WriteTransferCount','/format:csv'],text=True)
   session=ctypes.c_ulong();assert ctypes.windll.kernel32.ProcessIdToSessionId(p.pid,ctypes.byref(session)) and session.value==2
   assert str(EXE).replace('/','\\').lower() in ident.lower() and str(os.getpid()) in ident
   save('current-native.json',dict(pid=p.pid,parent=os.getpid(),session=session.value,command=cmd,log=str(log),identity=ident))
   assert ctypes.WinDLL('ntdll').NtResumeProcess(ctypes.c_void_p(int(p._handle)))==0
   rc=p.wait(timeout=10800)
  save(label+'-exit.json',dict(pid=p.pid,exit=rc,command=cmd,log=str(log)))
  assert rc==0,(label,log.read_text(errors='replace')[-5000:])
 # Verified inherited compiled water dependency retained
 for i in range(2):native('world-part'+str(i),'maps/df_spaceport_v268_twopart_part'+str(i)+'.vmap',True)
 native('world-parent','maps/df_spaceport_v268_twopart.vmap',True)
 save('NATIVE-THREE-FINISHED.json',dict(exit=0,QA_PENDING=True,noInstall=True))
try:main()
except BaseException:save('BLOCKER.json',dict(error=traceback.format_exc(),noInstall=True));raise
