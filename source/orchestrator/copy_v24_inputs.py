import pathlib,json,subprocess,hashlib,datetime,traceback,os
S=pathlib.Path("E:/df-v24-build-20261106");D=pathlib.Path("E:/df-v25-build-20261106");W=D/"orchestrator"
def save(n,x):(W/n).write_text(json.dumps(x,indent=2),encoding="utf8")
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
try:
 save("copy-process.json",{"pid":os.getpid(),"startedUTC":now(),"source":str(S),"destination":str(D),"compileStarted":False})
 results=[]
 for name in ["content","geometry-work","component-work","loot-ladder-work"]:
  with (W/("copy-"+name+".log")).open("w") as log:
   p=subprocess.run(["robocopy",str(S/name),str(D/name),"/E","/COPY:DAT","/DCOPY:DAT","/R:1","/W:1","/XJ","/NP"],stdout=log,stderr=subprocess.STDOUT)
  assert p.returncode<8,(name,p.returncode)
  files=[];bad=[]
  for src in sorted((S/name).rglob("*")):
   if not src.is_file():continue
   dst=D/name/src.relative_to(S/name)
   a=hashlib.sha256(src.read_bytes()).hexdigest()
   b=hashlib.sha256(dst.read_bytes()).hexdigest() if dst.is_file() else None
   files.append({"path":str(src.relative_to(S)),"bytes":src.stat().st_size,"sha256":a})
   if a!=b:bad.append(str(src))
  save("copy-"+name+"-verified.json",{"files":files,"mismatches":bad,"success":not bad})
  assert not bad,bad[:10]
  results.append({"directory":name,"files":len(files),"verified":True})
 # Material owner owns material-work; preserve originals separately and never write owned stage.
 for name in ["material-work","compile-work"]:
  target=D/"orchestrator"/("v24-"+name+"-reference")
  with (W/("copy-reference-"+name+".log")).open("w") as log:
   p=subprocess.run(["robocopy",str(S/name),str(target),"/E","/COPY:DAT","/R:1","/W:1","/XJ","/NP"],stdout=log,stderr=subprocess.STDOUT)
  assert p.returncode<8,(name,p.returncode)
 src=S/"install-work/20261106T144857Z/recreate/v25-readonly-handoff/spawn32-validated-source.json"
 dst=W/src.name;dst.write_bytes(src.read_bytes());sp=json.loads(dst.read_text(encoding="utf-8-sig"))
 assert sp["T"]==16 and sp["CT"]==16 and sp["unique"]==32 and sp["allEnabled"]
 save("copy-ready.json",{"success":True,"finishedUTC":now(),"directories":results,"spawn32sha256":hashlib.sha256(dst.read_bytes()).hexdigest(),"spawn32":str(dst),"referenceScriptsNOTExecutableUntilRebased":True,"v24Untouched":True,"compiledGameNotCopied":True})
except:
 save("copy-failure.json",{"finishedUTC":now(),"traceback":traceback.format_exc()});raise
